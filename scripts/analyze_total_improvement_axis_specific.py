"""Analyze per-axis congestion control against intersection-total triggering."""
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
STEM = "axis_specific_congestion_1800"


def metrics(row: dict) -> dict[str, float]:
    history = row.get("phase_history") or []
    yellow = sum(
        float(history[index + 1]["at"]) - float(event["at"])
        for index, event in enumerate(history[:-1])
        if event["color"] == "yellow"
    )
    lane_waits = [float(value) for value in row.get("lane_waits", {}).values()]
    reds = max_signal_red_by_phase(history, int(row["duration_seconds"]))
    return {
        "average_wait_seconds": float(row["average_wait_seconds"]),
        "average_queue_length": float(row["average_queue_length"]),
        "residual_vehicles": float(row["waiting_at_end"]) + float(row["in_service_at_end"]),
        "throughput_per_hour": float(row["throughput_per_hour"]),
        "fairness_index": float(row["fairness_index"]),
        "max_lane_mean_wait_seconds": max(lane_waits, default=0.0),
        "phase_switches": float(sum(event["color"] == "yellow" for event in history)),
        "yellow_fraction": yellow / float(row["duration_seconds"]),
        "max_signal_red_seconds": max(reds.values(), default=0.0),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    payload = json.loads((OUT / f"{STEM}.json").read_text(encoding="utf-8"))
    by_policy: dict[tuple[str, str, int], dict] = {}
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in payload["runs"]:
        scenario, controller, seed = row["scenario"], row["controller"], int(row["seed"])
        by_policy[(scenario, controller, seed)] = metrics(row)
        groups[(scenario, controller)].append(row)

    metric_names = tuple(metrics(payload["runs"][0]))
    summaries = []
    for (scenario, controller), runs in sorted(groups.items()):
        item = {"scenario": scenario, "controller": controller, "runs": len(runs)}
        for metric in metric_names:
            values = [by_policy[(scenario, controller, int(row["seed"]))][metric] for row in runs]
            item[metric] = statistics.mean(values)
            item[f"{metric}_sd"] = statistics.stdev(values) if len(values) > 1 else 0.0
        summaries.append(item)
    write_csv(OUT / f"{STEM}_metrics.csv", summaries)

    contrasts = []
    scenarios = sorted({row["scenario"] for row in payload["runs"]})
    controllers = sorted({row["controller"] for row in payload["runs"]})
    for scenario in scenarios:
        families: dict[str, list[dict]] = defaultdict(list)
        for first, second in combinations(controllers, 2):
            seeds = sorted(seed for name, policy, seed in by_policy if name == scenario and policy == first)
            for metric in metric_names:
                deltas = [
                    by_policy[(scenario, first, seed)][metric]
                    - by_policy[(scenario, second, seed)][metric]
                    for seed in seeds
                ]
                stats = paired_summary(deltas)
                families[metric].append({
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
        for family in families.values():
            adjusted = holm_adjust([float(row["sign_test_p"]) for row in family])
            for row, p_adjusted in zip(family, adjusted, strict=True):
                row["holm_p_within_scenario_metric_6_pairs"] = p_adjusted
                contrasts.append(row)
    contrasts.sort(key=lambda row: (row["scenario"], row["metric"], row["controller_a"], row["controller_b"]))
    write_csv(OUT / f"{STEM}_paired.csv", contrasts)

    lines = [
        "# Congestion по обслуживаемой оси: development screen",
        "",
        "30 парных seed (7101–7130), 7 сценариев, 1800 с. Axis-specific включает congested min-green только если очередь на текущей зелёной оси ≥14; baseline Improved включает его при сумме очередей двух осей ≥14. Положительное Δ mean wait означает хуже для controller A. Holm выполняется по шести парам внутри каждой scenario × metric семьи.",
        "",
        "| Сценарий | Контроллер | Wait, с | Queue | Residual | Throughput/ч | Jain | Switches | Yellow, % |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['scenario']} | {row['controller']} | {row['average_wait_seconds']:.2f} "
            f"| {row['average_queue_length']:.2f} | {row['residual_vehicles']:.1f} "
            f"| {row['throughput_per_hour']:.1f} | {row['fairness_index']:.3f} "
            f"| {row['phase_switches']:.1f} | {100*row['yellow_fraction']:.2f} |"
        )
    lines.extend(["", "Полные метрики и скорректированные парные контрасты см. в соседних CSV. Это development-данные; новые seed ещё не использовались для независимой validation."])
    (OUT / f"{STEM}_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(summaries)} summaries and {len(contrasts)} paired contrasts")


if __name__ == "__main__":
    main()
