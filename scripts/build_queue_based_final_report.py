"""Build independent, seed-paired result tables from the locked final runs."""
from __future__ import annotations

import csv
import gzip
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from scipy.stats import t as student_t

from traffic_light.statistics_audit import exact_sign_p, holm_adjust

ROOT = Path(__file__).resolve().parents[1]
METRICS = (
    "average_wait_seconds",
    "max_wait_seconds",
    "average_queue_length",
    "throughput_per_hour",
    "waiting_at_end",
    "in_service_at_end",
    "observed_delay_seconds",
    "max_queue_length",
    "stops",
    "fairness_index",
)


def load_output(stem: str) -> dict[str, Any]:
    raw = ROOT / "outputs" / f"{stem}.json"
    compressed = ROOT / "outputs" / f"{stem}.json.gz"
    path = raw if raw.exists() else compressed
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def mean_ci(values: list[float]) -> tuple[float, float, float]:
    mean = statistics.mean(values)
    if len(values) < 2:
        return mean, mean, mean
    half = float(student_t.ppf(0.975, len(values) - 1)) * statistics.stdev(values) / math.sqrt(len(values))
    return mean, mean - half, mean + half


def analyze(
    payloads: list[dict[str, Any]], replay_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    runs = [run for payload in payloads for run in payload["runs"]]
    groups: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    paired: dict[tuple[str, int, str], dict[int, dict[str, dict[str, float]]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for row in runs:
        key = row["scenario"], int(row["duration_seconds"]), row["controller"]
        groups[key].append(row)
        paired[(row["scenario"], int(row["duration_seconds"]), "")][int(row["seed"])][row["controller"]] = {
            metric: float(row[metric]) for metric in METRICS
        }
    replay_groups: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in replay_rows:
        replay_groups[(row["scenario"], int(row["duration_seconds"]), row["controller"])].append(row)

    summary_rows: list[dict[str, Any]] = []
    for (scenario, duration, controller), rows in sorted(groups.items()):
        entry: dict[str, Any] = {
            "scenario": scenario,
            "scenario_title": rows[0]["scenario_title"],
            "duration_seconds": duration,
            "controller": controller,
            "n": len(rows),
        }
        for metric in METRICS:
            values = [float(row[metric]) for row in rows]
            average, low, high = mean_ci(values)
            entry[f"{metric}_mean"] = average
            entry[f"{metric}_ci95_low"] = low
            entry[f"{metric}_ci95_high"] = high
        phase_data = [phase_metrics(row) for row in rows]
        for metric in ("switches", "yellow_seconds", "green_mean_seconds", "green_seconds", "green_fraction"):
            average, low, high = mean_ci([float(x[metric]) for x in phase_data])
            entry[f"{metric}_mean"] = average
            entry[f"{metric}_ci95_low"] = low
            entry[f"{metric}_ci95_high"] = high
        replay = replay_groups[(scenario, duration, controller)]
        for metric in (
            "green_utilization",
            "green_idle_fraction",
            "green_max_reached_count",
            "mean_accrued_wait_per_vehicle_seconds",
        ):
            average, low, high = mean_ci([float(row[metric]) for row in replay])
            entry[f"{metric}_mean"] = average
            entry[f"{metric}_ci95_low"] = low
            entry[f"{metric}_ci95_high"] = high
        v_c = [max(float(value) for value in row["v_c_by_lane"].values()) for row in replay]
        average, low, high = mean_ci(v_c)
        entry["max_lane_v_c_mean"] = average
        entry["max_lane_v_c_ci95_low"] = low
        entry["max_lane_v_c_ci95_high"] = high
        summary_rows.append(entry)

    contrast_rows: list[dict[str, Any]] = []
    families: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for (scenario, duration, _), seeds in sorted(paired.items()):
        if not seeds:
            continue
        controllers = sorted({name for values in seeds.values() for name in values})
        comparisons = [("queue_based", name) for name in controllers if name != "queue_based"]
        comparisons += [("queue_based_improved", name) for name in controllers if name not in {"queue_based_improved", "queue_based"}]
        for metric in METRICS:
            family_key = scenario, duration, metric
            for left, right in comparisons:
                diffs = [seeds[seed][left][metric] - seeds[seed][right][metric] for seed in sorted(seeds)
                         if left in seeds[seed] and right in seeds[seed]]
                if not diffs:
                    continue
                avg, low, high = mean_ci(diffs)
                item = {
                    "scenario": scenario,
                    "duration_seconds": duration,
                    "metric": metric,
                    "left_minus_right": f"{left} - {right}",
                    "n_pairs": len(diffs),
                    "mean_difference": avg,
                    "ci95_low": low,
                    "ci95_high": high,
                    "exact_sign_p": exact_sign_p(diffs),
                }
                families[family_key].append(item)
    for rows in families.values():
        adjusted = holm_adjust([float(row["exact_sign_p"]) for row in rows])
        for row, p_adjusted in zip(rows, adjusted, strict=True):
            row["holm_p_within_scenario_horizon_metric"] = p_adjusted
            contrast_rows.append(row)
    return summary_rows, contrast_rows


def phase_metrics(row: dict[str, Any]) -> dict[str, float]:
    history = row.get("phase_history") or []
    horizon = float(row["duration_seconds"])
    green_by_phase: dict[str, float] = defaultdict(float)
    yellow = 0.0
    greens: list[float] = []
    active: tuple[float, str] | None = None
    for event in history:
        at = float(event["at"])
        if active is not None:
            started, color = active
            end = min(at, horizon)
            elapsed = max(0.0, end - started)
            if color == "green":
                green_by_phase["green"] += elapsed
                greens.append(elapsed)
            elif color == "yellow":
                yellow += elapsed
        active = (at, event["color"])
    if active is not None:
        started, color = active
        elapsed = max(0.0, horizon - started)
        if color == "green":
            green_by_phase["green"] += elapsed
            greens.append(elapsed)
        elif color == "yellow":
            yellow += elapsed
    green_seconds = green_by_phase["green"]
    switches = sum(event["color"] == "yellow" for event in history)
    return {
        "switches": float(switches),
        "yellow_seconds": yellow,
        "green_mean_seconds": statistics.mean(greens) if greens else 0.0,
        "green_seconds": green_seconds,
        "green_fraction": green_seconds / horizon if horizon else 0.0,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    payloads = [load_output(f"queue_based_final_{duration}") for duration in (1800, 3600)]
    replay_payload = json.loads((ROOT / "outputs/queue_based_final_replay_metrics.json").read_text(encoding="utf-8"))
    replay_rows = [row for file_result in replay_payload for row in file_result["runs"]]
    summary, contrasts = analyze(payloads, replay_rows)
    write_csv(ROOT / "outputs/queue_based_final_summary.csv", summary)
    write_csv(ROOT / "outputs/queue_based_final_paired_contrasts.csv", contrasts)
    print(f"summary rows={len(summary)}; paired contrasts={len(contrasts)}")


if __name__ == "__main__":
    main()
