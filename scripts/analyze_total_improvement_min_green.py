"""Analyze paired minimum-green dynamics development results."""
from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from traffic_light.queue_audit import max_signal_red_by_phase
from traffic_light.statistics_audit import holm_adjust, paired_summary

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/total_improvement"
STEM = "min_green_dynamics_1800"


def run_metrics(row: dict) -> dict[str, float]:
    history = row.get("phase_history") or []
    yellow = sum(
        float(history[index + 1]["at"]) - float(event["at"])
        for index, event in enumerate(history[:-1])
        if event["color"] == "yellow"
    )
    lane_means = [float(value) for value in row.get("lane_waits", {}).values()]
    residual = int(row["waiting_at_end"]) + int(row["in_service_at_end"])
    red = max_signal_red_by_phase(history, int(row["duration_seconds"]))
    return {
        "average_wait_seconds": float(row["average_wait_seconds"]),
        "max_completed_wait_seconds": float(row["max_wait_seconds"]),
        "average_queue_length": float(row["average_queue_length"]),
        "residual_vehicles": float(residual),
        "throughput_per_hour": float(row["throughput_per_hour"]),
        "fairness_index": float(row["fairness_index"]),
        "max_lane_mean_wait_seconds": max(lane_means, default=0.0),
        "lane_mean_wait_range_seconds": max(lane_means, default=0.0) - min(lane_means, default=0.0),
        "phase_switches": float(sum(event["color"] == "yellow" for event in history)),
        "yellow_fraction": yellow / float(row["duration_seconds"]),
        "max_signal_red_seconds": max(red.values(), default=0.0),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    payload = json.loads((OUT / f"{STEM}.json").read_text(encoding="utf-8"))
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    values: dict[tuple[str, str, int], dict[str, float]] = {}
    for row in payload["runs"]:
        key = (row["scenario"], row["controller"])
        grouped[key].append(row)
        values[(*key, int(row["seed"]))] = run_metrics(row)

    metric_names = tuple(run_metrics(payload["runs"][0]))
    summaries = []
    for (scenario, controller), rows in sorted(grouped.items()):
        summary = {
            "scenario": scenario,
            "controller": controller,
            "runs": len(rows),
            "unique_arrival_hashes": len({row["arrival_stream_sha256"] for row in rows}),
        }
        for metric in metric_names:
            observations = [values[(scenario, controller, int(row["seed"]))][metric] for row in rows]
            summary[metric] = statistics.mean(observations)
            summary[f"{metric}_sd"] = statistics.stdev(observations) if len(observations) > 1 else 0.0
        summaries.append(summary)
    write_csv(OUT / f"{STEM}_metrics.csv", summaries)

    scenarios = sorted({row["scenario"] for row in payload["runs"]})
    controllers = sorted({row["controller"] for row in payload["runs"]})
    contrasts = []
    for scenario in scenarios:
        by_metric: dict[str, list[dict]] = defaultdict(list)
        for first, second in combinations(controllers, 2):
            seeds = sorted(seed for name, policy, seed in values if name == scenario and policy == first)
            for metric in metric_names:
                differences = [
                    values[(scenario, first, seed)][metric]
                    - values[(scenario, second, seed)][metric]
                    for seed in seeds
                ]
                stats = paired_summary(differences)
                by_metric[metric].append({
                    "scenario": scenario,
                    "metric": metric,
                    "controller_a": first,
                    "controller_b": second,
                    "pairs": stats["n"],
                    "mean_delta_a_minus_b": stats["mean"],
                    "paired_sd": stats["sd"],
                    "ci95_low": stats["ci_low"],
                    "ci95_high": stats["ci_high"],
                    "sign_test_p": stats["sign_p"],
                })
        for family in by_metric.values():
            adjusted = holm_adjust([float(item["sign_test_p"]) for item in family])
            for item, p_adj in zip(family, adjusted, strict=True):
                item["holm_p_within_scenario_metric_21_pairs"] = p_adj
                contrasts.append(item)
    contrasts.sort(key=lambda item: (item["scenario"], item["metric"], item["controller_a"], item["controller_b"]))
    write_csv(OUT / f"{STEM}_paired.csv", contrasts)

    chosen = {"queue_based_improved", "queue_based_smooth_min_green_10_18", "queue_based_hysteresis_14_10", "queue_based_persistent_5s", "queue_based_persistent_10s"}
    lines = [
        "# Динамика минимальной зелёной фазы: development screen",
        "",
        "Парная серия: 30 seed (5101–5130), 7 сценариев, горизонт 1800 с; у каждого контроллера одинаковые arrivals в пределах scenario/seed. Это исследовательский development набор, а не независимый final test.",
        "Положительное Δ mean wait означает, что controller A хуже controller B. Holm-коррекция выполняется по 21 паре в каждой семье scenario × metric.",
        "",
        "## Основные варианты",
        "",
        "| Сценарий | Контроллер | Ожидание, с | Очередь | Остаток, авто | Поток/ч | Jain | Переключения | Жёлтый, % |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        if row["controller"] in chosen:
            lines.append(
                f"| {row['scenario']} | {row['controller']} | {row['average_wait_seconds']:.2f} "
                f"| {row['average_queue_length']:.2f} | {row['residual_vehicles']:.1f} "
                f"| {row['throughput_per_hour']:.1f} | {row['fairness_index']:.3f} "
                f"| {row['phase_switches']:.1f} | {100*row['yellow_fraction']:.2f} |"
            )
    lines.extend([
        "",
        "Полные seed-level показатели и парные контрасты находятся в соседних CSV. Максимальный сигнал red рассчитан по истории фаз и не равен времени ожидания автомобиля на red.",
    ])
    (OUT / f"{STEM}_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(summaries)} summaries and {len(contrasts)} paired contrasts")


if __name__ == "__main__":
    main()
