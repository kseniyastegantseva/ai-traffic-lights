"""Summarize the initial-state experiment without excluding its full horizon."""
from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def summarize(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in payload["runs"]:
        grouped[(row["scenario"], row["controller"])].append(row)
    summary = []
    for (scenario, controller), rows in sorted(grouped.items()):
        post_warmup: list[float] = []
        for row in rows:
            series = row["queue_series"]
            if len(series) < 300:
                raise ValueError(f"queue trace shorter than 300 s for {scenario}/{controller}/{row['seed']}")
            post_warmup.append(statistics.mean(series[300:]))
        summary.append(
            {
                "scenario": scenario,
                "controller": controller,
                "runs": len(rows),
                "full_horizon_wait_mean_seconds": statistics.mean(float(r["average_wait_seconds"]) for r in rows),
                "full_horizon_queue_area_mean": statistics.mean(float(r["average_queue_length"]) for r in rows),
                "full_horizon_residual_waiting_mean": statistics.mean(float(r["waiting_at_end"]) for r in rows),
                "full_horizon_departed_mean": statistics.mean(float(r["vehicles_departed"]) for r in rows),
                "post_300s_mean_sampled_queue": statistics.mean(post_warmup),
            }
        )
    return summary


def main() -> None:
    path = ROOT / "outputs/queue_based_initial_state_1800.json"
    rows = summarize(path)
    out = ROOT / "outputs/queue_based_initial_state_summary.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"rows={len(rows)}; full horizon retained; post-300s sampled queue included")


if __name__ == "__main__":
    main()
