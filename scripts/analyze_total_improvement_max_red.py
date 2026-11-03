"""Analyze phase-red fairness and delay in the 30-seed max-red development screen."""
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
STEM = "max_red_development_1800"


def run_metrics(row: dict) -> dict[str, float]:
    history = row.get("phase_history") or []
    yellow = sum(
        float(history[index + 1]["at"]) - float(event["at"])
        for index, event in enumerate(history[:-1])
        if event["color"] == "yellow"
    )
    lane_waits = row.get("lane_waits") or {}
    lane_mean_waits = [float(value) for value in lane_waits.values()]
    red_by_phase = max_signal_red_by_phase(history, int(row["duration_seconds"]))
    red_with_queue = row.get("max_red_with_queue_seconds_by_phase") or {}
    residual = int(row["waiting_at_end"]) + int(row["in_service_at_end"])
    duration = float(row["duration_seconds"])
    return {
        "average_wait_seconds": float(row["average_wait_seconds"]),
        "max_completed_wait_seconds": float(row["max_wait_seconds"]),
        "average_queue_length": float(row["average_queue_length"]),
        "residual_vehicles": float(residual),
        "throughput_per_hour": float(row["throughput_per_hour"]),
        "fairness_index": float(row["fairness_index"]),
        "max_lane_mean_wait_seconds": max(lane_mean_waits, default=0.0),
        "lane_mean_wait_range_seconds": (
            max(lane_mean_waits) - min(lane_mean_waits) if lane_mean_waits else 0.0
        ),
        "phase_switches": float(sum(event["color"] == "yellow" for event in history)),
        "yellow_fraction": yellow / duration,
        "max_signal_red_seconds": max(red_by_phase.values(), default=0.0),
        "max_red_with_queue_seconds": max(
            (float(value) for value in red_with_queue.values()), default=0.0
        ),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    payload = json.loads((OUT / f"{STEM}.json").read_text(encoding="utf-8"))
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    seed_metrics: dict[tuple[str, str, int], dict[str, float]] = {}
    for row in payload["runs"]:
        key = (row["scenario"], row["controller"])
        grouped[key].append(row)
        seed_metrics[(*key, int(row["seed"]))] = run_metrics(row)

    metrics = tuple(run_metrics(payload["runs"][0]))
    summary_rows = []
    for (scenario, controller), rows in sorted(grouped.items()):
        values = [seed_metrics[(scenario, controller, int(row["seed"]))] for row in rows]
        summary = {
            "scenario": scenario,
            "controller": controller,
            "runs": len(rows),
            "unique_arrival_hashes": len({row["arrival_stream_sha256"] for row in rows}),
        }
        for metric in metrics:
            observations = [value[metric] for value in values]
            summary[metric] = statistics.mean(observations)
            summary[f"{metric}_sd"] = statistics.stdev(observations) if len(observations) > 1 else 0.0
            if metric in {"max_signal_red_seconds", "max_red_with_queue_seconds"}:
                summary[f"{metric}_worst_seed"] = max(observations)
        summary_rows.append(summary)
    write_csv(OUT / f"{STEM}_metrics.csv", summary_rows)

    scenarios = sorted({row["scenario"] for row in payload["runs"]})
    controllers = sorted({row["controller"] for row in payload["runs"]})
    paired_rows = []
    for scenario in scenarios:
        family_by_metric: dict[str, list[dict]] = defaultdict(list)
        for first, second in combinations(controllers, 2):
            seeds = sorted(
                seed for name, controller, seed in seed_metrics
                if name == scenario and controller == first
            )
            for metric in metrics:
                differences = [
                    seed_metrics[(scenario, first, seed)][metric]
                    - seed_metrics[(scenario, second, seed)][metric]
                    for seed in seeds
                ]
                stats = paired_summary(differences)
                family_by_metric[metric].append(
                    {
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
                    }
                )
        for family in family_by_metric.values():
            adjusted = holm_adjust([float(row["sign_test_p"]) for row in family])
            for row, p_adjusted in zip(family, adjusted, strict=True):
                row["holm_p_within_scenario_metric_10_pairs"] = p_adjusted
                paired_rows.append(row)
    paired_rows.sort(key=lambda row: (row["scenario"], row["metric"], row["controller_a"], row["controller_b"]))
    write_csv(OUT / f"{STEM}_paired.csv", paired_rows)

    lines = [
        "# Max-red fairness development screen",
        "",
        "30 paired development seeds, six balanced/asymmetric/changing/high-load scenarios, 1800 s.",
        "Every controller uses the same arrivals within scenario/seed. Positive deltas are worse",
        "for wait/queue/residual/red/range; positive throughput delta is better. Holm correction",
        "is applied across all 10 controller pairs within each scenario × metric family.",
        "Max signal red is derived from phase indications; it is not vehicle waiting time.",
        "",
        "## Среднее по seed",
        "",
        "| Сценарий | Контроллер | Wait, с | Max signal red (mean of run max), с | Worst red with queued demand, с | Residual | Max lane mean wait, с | Jain fairness | Switches | Yellow, % |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['scenario']} | {row['controller']} | {row['average_wait_seconds']:.2f} "
            f"| {row['max_signal_red_seconds']:.1f} | {row['max_red_with_queue_seconds_worst_seed']:.1f} "
            f"| {row['residual_vehicles']:.1f} "
            f"| {row['max_lane_mean_wait_seconds']:.2f} | {row['fairness_index']:.3f} "
            f"| {row['phase_switches']:.1f} | {100 * row['yellow_fraction']:.2f} |"
        )
    lines.extend(
        [
            "",
            "Seed-level metrics and all Holm-adjusted paired contrasts are in the adjacent CSV files.",
            "These seed IDs are development data, not an independent final test set.",
        ]
    )
    (OUT / f"{STEM}_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(summary_rows)} summary rows and {len(paired_rows)} paired contrasts")


if __name__ == "__main__":
    main()
