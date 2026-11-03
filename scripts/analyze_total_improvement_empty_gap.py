"""Summarize and compare the empty-green development experiment by paired seed."""
from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

from traffic_light.statistics_audit import holm_adjust, paired_summary

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "outputs/total_improvement/empty_gap_development_1800.json"
SUMMARY = ROOT / "outputs/total_improvement/empty_gap_development_1800_metrics.csv"
PAIRED = ROOT / "outputs/total_improvement/empty_gap_development_1800_paired.csv"
REPORT = ROOT / "outputs/total_improvement/empty_gap_development_1800_analysis.md"
COMPARATORS = ("queue_based_improved", "queue_based_legacy", "vehicle_actuated")


def _run_metrics(row: dict) -> dict[str, float]:
    history = row["phase_history"] or []
    yellow_intervals = [
        (float(event["at"]), float(history[index + 1]["at"]))
        for index, event in enumerate(history[:-1])
        if event["color"] == "yellow"
    ]
    yellow_seconds = sum(end - start for start, end in yellow_intervals)
    remaining = int(row["waiting_at_end"]) + int(row["in_service_at_end"])
    duration = float(row["duration_seconds"])
    return {
        "average_wait_seconds": float(row["average_wait_seconds"]),
        "observed_delay_seconds": float(row["observed_delay_seconds"]),
        "average_queue_length": float(row["average_queue_length"]),
        "throughput_per_hour": float(row["throughput_per_hour"]),
        "residual_vehicles": float(remaining),
        "unserved_fraction": remaining / max(1, int(row["vehicles_arrived"])),
        "phase_switches": float(len(yellow_intervals)),
        "yellow_seconds": yellow_seconds,
        "yellow_fraction": yellow_seconds / duration,
        "max_wait_seconds": float(row["max_wait_seconds"]),
        "fairness_index": float(row["fairness_index"]),
    }


def main() -> None:
    payload = json.loads(INPUT.read_text(encoding="utf-8"))
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in payload["runs"]:
        groups[(row["scenario"], row["controller"])].append(row)

    metric_names = tuple(_run_metrics(payload["runs"][0]))
    summary_rows: list[dict] = []
    for (scenario, controller), rows in sorted(groups.items()):
        metrics = [_run_metrics(row) for row in rows]
        record: dict[str, str | int | float] = {
            "scenario": scenario,
            "controller": controller,
            "runs": len(rows),
            "arrival_hashes_unique": len({row["arrival_stream_sha256"] for row in rows}),
        }
        for metric in metric_names:
            values = [item[metric] for item in metrics]
            record[metric] = statistics.mean(values)
            record[f"{metric}_sd"] = statistics.stdev(values) if len(values) > 1 else 0.0
        summary_rows.append(record)
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARY.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary_rows)

    by_key = {
        (row["scenario"], row["controller"], int(row["seed"])): _run_metrics(row)
        for row in payload["runs"]
    }
    paired_rows: list[dict] = []
    for scenario in sorted({row["scenario"] for row in payload["runs"]}):
        family: list[dict] = []
        for gap_controller in (
            "queue_based_empty_gap_0s",
            "queue_based_empty_gap_1s",
            "queue_based_empty_gap_3s",
        ):
            for comparator in COMPARATORS:
                seeds = sorted(
                    seed
                    for (run_scenario, run_controller, seed) in by_key
                    if run_scenario == scenario and run_controller == gap_controller
                )
                differences = [
                    by_key[(scenario, gap_controller, seed)]["average_wait_seconds"]
                    - by_key[(scenario, comparator, seed)]["average_wait_seconds"]
                    for seed in seeds
                ]
                stats = paired_summary(differences)
                family.append(
                    {
                        "scenario": scenario,
                        "candidate": gap_controller,
                        "comparator": comparator,
                        "pairs": stats["n"],
                        "mean_wait_delta_candidate_minus_comparator_seconds": stats["mean"],
                        "relative_wait_delta_pct": (
                            100 * stats["mean"]
                            / statistics.mean(
                                by_key[(scenario, comparator, seed)]["average_wait_seconds"]
                                for seed in seeds
                            )
                        ),
                        "paired_sd_seconds": stats["sd"],
                        "ci95_low_seconds": stats["ci_low"],
                        "ci95_high_seconds": stats["ci_high"],
                        "sign_test_p": stats["sign_p"],
                    }
                )
        adjusted = holm_adjust([float(row["sign_test_p"]) for row in family])
        for row, p_adjusted in zip(family, adjusted, strict=True):
            row["holm_p_within_scenario_9_contrasts"] = p_adjusted
            paired_rows.append(row)
    with PAIRED.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(paired_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(paired_rows)

    lines = [
        "# Анализ empty-green gap-out: development",
        "",
        "Серия носит исследовательский характер; seed 2101–2130 не использовались в предыдущих",
        "матрицах и не являются независимым final-test после просмотра этих результатов.",
        "Положительная парная разность ожидания означает, что candidate хуже comparator.",
        "Поправка Holm применяется к девяти контрастам (3 gap × 3 comparator) внутри каждого",
        "сценария; основные метрики описательны, ожидание — заранее выбранный парный показатель.",
        "",
        "## Сводные показатели",
        "",
        "| Сценарий | Контроллер | Ожидание, с | Очередь, авто | авто/ч | Остаток, авто | Переключения | Жёлтый, с | Макс. ожидание, с |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['scenario']} | {row['controller']} | {row['average_wait_seconds']:.3f} "
            f"| {row['average_queue_length']:.3f} | {row['throughput_per_hour']:.1f} "
            f"| {row['residual_vehicles']:.1f} | {row['phase_switches']:.1f} "
            f"| {row['yellow_seconds']:.1f} | {row['max_wait_seconds']:.1f} |"
        )
    lines.extend(
        [
            "",
            "## Парные contrasts по ожиданию",
            "",
            "| Сценарий | Candidate | Comparator | Δ, с | Относительно, % | 95% CI, с | sign p | Holm p |",
            "|---|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in paired_rows:
        lines.append(
            f"| {row['scenario']} | {row['candidate']} | {row['comparator']} "
            f"| {row['mean_wait_delta_candidate_minus_comparator_seconds']:.3f} "
            f"| {row['relative_wait_delta_pct']:.2f} "
            f"| [{row['ci95_low_seconds']:.3f}, {row['ci95_high_seconds']:.3f}] "
            f"| {row['sign_test_p']:.5f} | {row['holm_p_within_scenario_9_contrasts']:.5f} |"
        )
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(summary_rows)} summary rows and {len(paired_rows)} paired contrasts")


if __name__ == "__main__":
    main()
