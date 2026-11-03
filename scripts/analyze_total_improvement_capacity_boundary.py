"""Analyze the paired 9–18 vehicle/minute controller capacity-boundary screen."""
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


def run_metrics(row: dict) -> dict[str, float]:
    history = row["phase_history"] or []
    yellow_intervals = [
        float(history[index + 1]["at"]) - float(event["at"])
        for index, event in enumerate(history[:-1])
        if event["color"] == "yellow"
    ]
    maximum_red = max(
        max_signal_red_by_phase(history, int(row["duration_seconds"])).values()
    )
    residual = int(row["waiting_at_end"]) + int(row["in_service_at_end"])
    arrivals = int(row["vehicles_arrived"])
    duration = float(row["duration_seconds"])
    average_queue = float(row["average_queue_length"])
    return {
        "average_wait_seconds": float(row["average_wait_seconds"]),
        "max_wait_seconds": float(row["max_wait_seconds"]),
        "observed_delay_seconds": float(row["observed_delay_seconds"]),
        "queue_area_vehicle_seconds": average_queue * duration,
        "average_queue_length": average_queue,
        "max_queue_length": float(row["max_queue_length"]),
        "throughput_per_hour": float(row["throughput_per_hour"]),
        "residual_vehicles": float(residual),
        "unserved_fraction": residual / max(1, arrivals),
        "phase_switches": float(len(yellow_intervals)),
        "yellow_seconds": sum(yellow_intervals),
        "yellow_fraction": sum(yellow_intervals) / duration,
        "green_fraction": (duration - sum(yellow_intervals)) / duration,
        "max_red_seconds": maximum_red,
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=int, choices=(1800, 3600), default=1800)
    duration = parser.parse_args().duration
    output_dir = ROOT / "outputs/total_improvement"
    input_path = output_dir / f"capacity_boundary_{duration}.json"
    summary_path = output_dir / f"capacity_boundary_{duration}_metrics.csv"
    paired_path = output_dir / f"capacity_boundary_{duration}_paired.csv"
    report_path = output_dir / f"capacity_boundary_{duration}_analysis.md"
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in payload["runs"]:
        groups[(row["scenario"], row["controller"])].append(row)
    by_seed: dict[tuple[str, str, int], dict[str, float]] = {}
    metrics = tuple(run_metrics(payload["runs"][0]))
    summary_rows = []
    for (scenario, controller), runs in sorted(groups.items()):
        values = []
        for row in runs:
            value = run_metrics(row)
            values.append(value)
            by_seed[(scenario, controller, int(row["seed"]))] = value
        record: dict = {
            "scenario": scenario,
            "controller": controller,
            "runs": len(runs),
            "arrival_hashes_unique": len({row["arrival_stream_sha256"] for row in runs}),
        }
        for metric in metrics:
            observations = [row[metric] for row in values]
            record[metric] = statistics.mean(observations)
            record[f"{metric}_sd"] = (
                statistics.stdev(observations) if len(observations) > 1 else 0.0
            )
            if metric == "max_red_seconds":
                record["max_red_seconds_worst_seed"] = max(observations)
        summary_rows.append(record)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(summary_path, summary_rows)

    metric_rows: list[dict] = []
    scenarios = sorted({row["scenario"] for row in payload["runs"]})
    controllers = sorted({row["controller"] for row in payload["runs"]})
    metric_families: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for scenario in scenarios:
        for first, second in combinations(controllers, 2):
            seeds = sorted(
                seed
                for run_scenario, controller, seed in by_seed
                if run_scenario == scenario and controller == first
            )
            for metric in metrics:
                differences = [
                    by_seed[(scenario, first, seed)][metric]
                    - by_seed[(scenario, second, seed)][metric]
                    for seed in seeds
                ]
                stats = paired_summary(differences)
                row = {
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
                metric_families[(scenario, metric)].append(row)
        for metric in metrics:
            family = metric_families[(scenario, metric)]
            adjusted = holm_adjust([float(row["sign_test_p"]) for row in family])
            for row, p_adjusted in zip(family, adjusted, strict=True):
                row["holm_p_within_demand_metric_36_pairs"] = p_adjusted
                metric_rows.append(row)
    write_csv(paired_path, metric_rows)

    lines = [
        "# Capacity boundary 9–18 авто/мин/подход: development",
        "",
        f"15 парных seed на уровень, горизонт {duration} с. Каждый контроллер разделяет arrival stream",
        "внутри пары demand/seed. Это exploratory screen, а не final test. Положительная Δ для",
        "ожидания/очереди/остатка означает худший результат у controller A; положительная Δ для",
        "throughput означает больше обслуженных машин у A. Сравниваются 36 пар контроллеров",
        "внутри каждой пары сценарий × показатель с поправкой Holm.",
        "Максимальный red — наибольший непрерывный интервал, когда ось показывает red, выведенный",
        "из phase history; он не требует наличия ожидающей машины и потому является signal-time,",
        "а не max vehicle wait-on-red.",
        "",
        "## Основные показатели",
        "",
        "| Спрос | Контроллер | Wait, с | Queue area, veh·s | Средняя очередь | Residual | Throughput/ч | Переключения | Yellow, % | Max red, с |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        rate = row["scenario"].removeprefix("demand_")
        lines.append(
            f"| {rate} | {row['controller']} | {row['average_wait_seconds']:.2f} "
            f"| {row['queue_area_vehicle_seconds']:.0f} | {row['average_queue_length']:.2f} "
            f"| {row['residual_vehicles']:.1f} | {row['throughput_per_hour']:.1f} "
            f"| {row['phase_switches']:.1f} | {100 * row['yellow_fraction']:.2f} "
            f"| {row['max_red_seconds']:.1f} |"
        )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"{duration}s: wrote {len(summary_rows)} metric rows and "
        f"{len(metric_rows)} paired comparisons"
    )


if __name__ == "__main__":
    main()
