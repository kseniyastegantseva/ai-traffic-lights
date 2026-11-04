"""Исследовательский компромисс по фактическим результатам новых seed."""
import gzip
import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
with gzip.open(ROOT / "outputs/approach_preview_v2_followup/eval_runs.json.gz", "rt") as f:
    runs = json.load(f)["runs"]
fig, axes = plt.subplots(1, 2, figsize=(10, 4.3))
for ax, scenario in zip(axes, ("asymmetric_low_ew", "capacity_boundary"), strict=True):
    for name, label, color in (("A", "A", "#555555"), ("B_original", "B", "#777777"),
                               ("D_original", "D", "#1764a3"), ("D_guard20", "D + 20 s", "#c0392b"),
                               ("D_guard30", "D + 30 s", "#d08719")):
        subset = [r for r in runs if r["scenario"] == scenario and r["controller"] == name]
        if len(subset) != 8:
            raise ValueError((scenario, name, len(subset)))
        x = statistics.mean(r["queue_area_vehicle_seconds"] for r in subset)
        y = statistics.mean(max(r["max_red_with_queue_seconds_by_phase"].values()) for r in subset)
        ax.scatter(x, y, s=45, color=color)
        ax.annotate(label, (x, y), xytext=(5, 4), textcoords="offset points", fontsize=9)
    ax.set_title(scenario)
    ax.set_xlabel("Mean queue area, vehicle-seconds")
    ax.grid(alpha=.2)
axes[0].set_ylabel("Mean maximum red with queue, s")
fig.suptitle("Exploratory comparison: 8 paired seeds per scenario")
fig.tight_layout()
target = ROOT / "paper/approach_v2_audit/fairness_tradeoff.svg"
fig.savefig(target)
target.write_text("\n".join(line.rstrip() for line in target.read_text().splitlines()) + "\n")
