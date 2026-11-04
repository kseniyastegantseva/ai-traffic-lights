"""Парный анализ независимого exploratory-сравнения; Holm отдельно на метрику."""
import csv
import gzip
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from scipy.stats import t

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/approach_preview_v2_followup"
DEST = ROOT / "paper/approach_v2_audit/followup_contrasts.csv"
with gzip.open(OUT / "eval_runs.json.gz", "rt", encoding="utf-8") as f:
    raw = json.load(f)["runs"]
selected = json.loads((OUT / "selection.json").read_text())["selected"]
idx = {}
streams = defaultdict(set)
for r in raw:
    key = (r["scenario"], r["seed"], r["controller"])
    if key in idx or r["vehicle_balance_error"]:
        raise ValueError(f"Дубликат или ошибка баланса: {key}")
    idx[key] = r
    streams[key[:2]].add(r["arrival_stream_sha256"])
if any(len(x) != 1 for x in streams.values()):
    raise ValueError("Непарные потоки")

metrics = ("queue_area_vehicle_seconds", "max_red_with_queue", "max_wait_seconds",
           "p95_wait_seconds", "fairness_index", "waiting_at_end", "throughput_per_hour")
contrasts = (("D_original", "A"), ("D_original", "B_original"), ("D_original", selected),
             ("D_guard20", "D_original"), ("D_guard30", "D_original"))
rows = []
for scenario in sorted({s for s, _, _ in idx}):
    for left, right in contrasts:
        ls = {seed for s, seed, arm in idx if s == scenario and arm == left}
        rs = {seed for s, seed, arm in idx if s == scenario and arm == right}
        if ls != rs or len(ls) != 8:
            raise ValueError(f"Неполная пара: {scenario}, {left}, {right}")
        for metric in metrics:
            def get(r, metric=metric):
                if metric == "max_red_with_queue":
                    return max(r["max_red_with_queue_seconds_by_phase"].values())
                return float(r[metric])

            vals = [(get(idx[scenario, seed, left]), get(idx[scenario, seed, right])) for seed in sorted(ls)]
            diffs = [a-b for a, b in vals]
            avg, ref = statistics.mean(diffs), statistics.mean(b for _, b in vals)
            half = t.ppf(.975, len(diffs)-1)*statistics.stdev(diffs)/math.sqrt(len(diffs))
            positive, negative = sum(d > 0 for d in diffs), sum(d < 0 for d in diffs)
            n = positive + negative
            p = min(1., 2*sum(math.comb(n, i) for i in range(min(positive, negative)+1))/2**n)
            rows.append({"scenario": scenario, "contrast": f"{left}-{right}", "metric": metric,
                         "pairs": len(vals), "right_mean": ref, "mean_diff": avg,
                         "relative_pct": 100*avg/ref if ref else None, "ci_low": avg-half,
                         "ci_high": avg+half, "sign_p": p})
for metric in metrics:
    family = sorted((r for r in rows if r["metric"] == metric), key=lambda r: r["sign_p"])
    adjusted = 0.
    for i, row in enumerate(family):
        adjusted = max(adjusted, min(1., (len(family)-i)*row["sign_p"]))
        row["holm_per_metric"] = adjusted
DEST.parent.mkdir(parents=True, exist_ok=True)
with DEST.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys(), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print("runs", len(raw), "contrasts", len(rows), "stream_mismatch 0, balance_errors 0")
