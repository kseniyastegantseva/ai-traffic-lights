"""Пересчитать вторичные исходы и validation из сохранённых запусков v2.

Результаты записываются в paper/approach_v2_audit/, исходные данные не меняются.
Семейство Holm: все контрасты и сценарии отдельно для каждой метрики и пресета.
"""
from __future__ import annotations

import csv
import gzip
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from scipy.stats import t

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs/approach_preview_v2"
DEST = ROOT / "paper/approach_v2_audit"
METRICS = (
    "queue_area_vehicle_seconds", "throughput_per_hour", "waiting_at_end", "observed_delay_seconds",
    "observed_delay_per_vehicle_seconds", "average_wait_seconds", "p95_wait_seconds", "max_wait_seconds",
    "fairness_index", "max_red_with_queue", "phase_switches", "red_north_south", "red_east_west",
    "wait_north", "wait_south", "wait_east", "wait_west",
)
CONTRASTS = (("D", "A"), ("D", "B"), ("C", "A"), ("D", "C"), ("B", "A"))


def load(stage, sensor):
    name = f"approach_preview_v2_{stage}_m6_{sensor}.json.gz"
    with gzip.open(SOURCE / name, "rt", encoding="utf-8") as f:
        return json.load(f)["runs"]


def value(row, metric):
    if metric == "max_red_with_queue":
        return max(row["max_red_with_queue_seconds_by_phase"].values())
    if metric.startswith("red_"):
        return row["max_red_with_queue_seconds_by_phase"][metric.removeprefix("red_")]
    if metric.startswith("wait_"):
        return row["lane_waits"][metric.removeprefix("wait_")]
    return row[metric]


def calc(stage, sensor):
    raw = load(stage, "nosensor") + load(stage, sensor)
    index = {}
    for r in raw:
        arm = r["controller"][:1]
        if arm not in "ABCD" or r["controller"][1:2] != "_":
            continue
        key = r["scenario"], int(r["seed"]), arm
        if key in index:
            raise ValueError(f"Дубликат {key}")
        index[key] = r
    scenarios = sorted({s for s, _, a in index if a == "D"})
    results = []
    for scenario in scenarios:
        arms = {a: {seed for s, seed, arm in index if s == scenario and arm == a} for a in "ABCD"}
        for left, right in CONTRASTS:
            seeds = sorted(arms[left] & arms[right])
            if not seeds or arms[left] != arms[right]:
                raise ValueError(f"Непарные seed: {scenario} {left} {right}")
            for seed in seeds:
                if index[scenario, seed, left]["arrival_stream_sha256"] != index[scenario, seed, right]["arrival_stream_sha256"]:
                    raise ValueError(f"Разный поток: {scenario} {seed}")
            for metric in METRICS:
                pairs = [(float(value(index[scenario, seed, left], metric)),
                          float(value(index[scenario, seed, right], metric))) for seed in seeds]
                diffs = [a-b for a, b in pairs]
                mean = statistics.mean(diffs)
                baseline = statistics.mean(b for _, b in pairs)
                half = t.ppf(.975, len(diffs)-1) * statistics.stdev(diffs) / math.sqrt(len(diffs))
                pos = sum(d > 0 for d in diffs)
                neg = sum(d < 0 for d in diffs)
                n = pos + neg
                p = min(1., 2 * sum(math.comb(n, i) for i in range(min(pos, neg)+1)) / 2**n)
                results.append({"stage": stage, "sensor": sensor, "scenario": scenario,
                                "contrast": f"{left}-{right}", "metric": metric, "pairs": len(seeds),
                                "reference_mean": baseline, "mean_diff": mean,
                                "relative_pct": 100*mean/baseline if baseline else None,
                                "ci_low": mean-half, "ci_high": mean+half,
                                "ci_low_pct": 100*(mean-half)/baseline if baseline else None,
                                "ci_high_pct": 100*(mean+half)/baseline if baseline else None,
                                "sign_p": p})
    families = defaultdict(list)
    for row in results:
        families[row["metric"]].append(row)
    for family in families.values():
        family.sort(key=lambda row: row["sign_p"])
        adjusted = 0.
        for i, row in enumerate(family):
            adjusted = max(adjusted, min(1., (len(family)-i)*row["sign_p"]))
            row["holm_p_per_metric"] = adjusted
    return results


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    final = calc("final", "camera_nominal")
    with (SOURCE / "final_m6_contrasts.csv").open(encoding="utf-8", newline="") as f:
        original = {(r["scenario"], r["contrast"], r["metric"]): r for r in csv.DictReader(f)
                    if r["variant"] == "camera_nominal"}
    compared = 0
    for row in final:
        key = (row["scenario"], row["contrast"], row["metric"])
        if key not in original:
            continue
        for field in ("mean_diff", "relative_pct", "ci_low", "ci_high", "sign_p"):
            if row[field] is not None and not math.isclose(row[field], float(original[key][field]),
                                                           rel_tol=1e-8, abs_tol=1e-8):
                raise ValueError(f"Несовпадение {key}, {field}")
        compared += 1
    print("final совпало строк с исходным анализатором:", compared)
    variants = ("camera_nominal", "camera_good", "camera_degraded", "oracle_upper_bound",
                "sweep_distance60", "sweep_distance150", "sweep_latency1", "sweep_latency2", "sweep_outage")
    validation = [row for sensor in variants for row in calc("validation", sensor)]
    for name, rows in (("final_outcomes.csv", final), ("validation_outcomes.csv", validation)):
        with (DEST / name).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys(), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        print(name, len(rows))


if __name__ == "__main__":
    main()
