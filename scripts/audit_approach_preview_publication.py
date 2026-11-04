"""Независимая проверка сохранённого архива v2; входной каталог не изменяется.

python scripts/audit_approach_preview_publication.py /path/to/extracted/ai-traffic-lights
Требуется scipy для квантиля распределения Стьюдента.
"""
import csv
import gzip
import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import t

root = Path(sys.argv[1])
out = root / "outputs/approach_preview_v2"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


freeze = json.loads((out / "FREEZE.json").read_text())
bad_code = [p for p, h in freeze["code_sha256"].items() if not (root / p).exists() or sha(root / p) != h]
selection_ok = sha(out / "development_selection.json") == freeze["development_selection_sha256"]
bad_manifest = []
for f in out.glob("*_manifest.json"):
    m = json.loads(f.read_text())
    for key in ("config", "result"):
        p = root / m[key + "_path"]
        if not p.exists() or sha(p) != m[key + "_sha256"]:
            bad_manifest.append((f.name, key))
print("freeze_code_mismatch", bad_code, "selection_match", selection_ok)
print("manifests", len(list(out.glob('*_manifest.json'))), "hash_mismatches", bad_manifest)

for suffix, expected_scenarios in (("", 11), ("_3600", 6)):
    runs = []
    for sensor in ("nosensor", "camera_nominal"):
        p = out / f"approach_preview_v2_final_m6{suffix}_{sensor}.json.gz"
        with gzip.open(p, "rt") as f:
            runs += json.load(f)["runs"]
    idx = {}
    streams = defaultdict(set)
    duplicates = 0
    balance = 0
    for r in runs:
        arm = r["controller"][:1]
        if arm not in "ABCD" or r["controller"][1:2] != "_":
            continue
        key = (r["scenario"], r["seed"], arm)
        duplicates += key in idx
        idx[key] = r
        streams[key[:2]].add(r["arrival_stream_sha256"])
        balance += r["vehicle_balance_error"] != 0
    scenarios = sorted({key[0] for key in idx})
    expected = {(s, seed, arm) for s in scenarios for seed in range(33101, 33131) for arm in "ABCD"}
    print("final", suffix or "1800", "scenarios", len(scenarios), "missing", len(expected - idx.keys()),
          "extra", len(idx.keys() - expected), "duplicates", duplicates,
          "stream_mismatch", sum(len(v) != 1 for v in streams.values()), "balance_errors", balance)
    assert len(scenarios) == expected_scenarios
    specs = [("D-A", "D", "A"), ("D-B", "D", "B"), ("C-A", "C", "A"),
             ("D-C", "D", "C"), ("B-A", "B", "A"), ("(D-C)-(B-A)", None, None)]
    rows = []
    for s in scenarios:
        for label, left, right in specs:
            values = [[idx[s, seed, a]["queue_area_vehicle_seconds"] for a in "ABCD"] for seed in range(33101, 33131)]
            pos = {a: i for i, a in enumerate("ABCD")}
            diffs = [(v[pos[left]] - v[pos[right]]) if left else (v[3] - v[2]) - (v[1] - v[0]) for v in values]
            ref = statistics.mean(v[pos[right] if right else 0] for v in values)
            avg = statistics.mean(diffs)
            margin = t.ppf(.975, len(diffs)-1) * statistics.stdev(diffs) / math.sqrt(len(diffs))
            nonzero = [d for d in diffs if d != 0]
            n = len(nonzero)
            k = min(sum(d > 0 for d in nonzero), sum(d < 0 for d in nonzero))
            p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k+1)) / 2**n)
            rows.append({"scenario": s, "contrast": label, "mean": avg, "pct": 100*avg/ref,
                         "low": 100*(avg-margin)/ref, "high": 100*(avg+margin)/ref, "p": p})
    order = sorted(range(len(rows)), key=lambda i: rows[i]["p"])
    previous = 0
    for rank, i in enumerate(order):
        previous = max(previous, min(1, (len(rows)-rank)*rows[i]["p"]))
        rows[i]["holm"] = previous
    report = list(csv.DictReader((out / f"final_m6{suffix}_contrasts.csv").open()))
    original = {(x["scenario"], x["contrast"]): x for x in report if x["metric"] == "queue_area_vehicle_seconds" and x["variant"] == "camera_nominal" + suffix}
    mismatches = []
    for x in rows:
        y = original.get((x["scenario"], x["contrast"]))
        if not y or any(not math.isclose(x[a], float(y[b]), rel_tol=1e-8, abs_tol=1e-8) for a,b in
                        (("mean","mean_diff"),("pct","relative_pct"),("low","ci_low_pct"),("high","ci_high_pct"),("p","sign_p"),("holm","holm_p"))):
            mismatches.append((x["scenario"], x["contrast"]))
    print("independent_contrasts", len(rows), "mismatches", mismatches)
    for x in rows:
        if x["contrast"] in ("D-A", "D-B"):
            print(x["scenario"], x["contrast"], "pct/CI/Holm",
                  *(f"{x[k]:.6g}" for k in ("pct", "low", "high", "holm")))
