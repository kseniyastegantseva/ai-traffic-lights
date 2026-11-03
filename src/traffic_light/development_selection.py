"""Apply the predeclared noninferiority and congestion gates to a dev experiment."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

OVERLOAD_SCENARIOS = ("high_load", "true_oversaturated")
MODERATE_SCENARIOS = ("symmetric_low", "symmetric")


def assess_development(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["runs"]
    by: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        by.setdefault((row["scenario"], row["controller"]), []).append(row)

    controller_specs: dict[str, dict[str, Any]] = {}
    for spec in payload["configuration"]["controllers"]:
        if spec["type"] == "queue_based" and spec.get("legacy_rule"):
            name = "queue_based_legacy"
        else:
            name = spec.get("result_name") or spec["type"]
        controller_specs[name] = spec

    def average(scenario: str, controller: str, metric: str) -> float:
        values = [float(row[metric]) for row in by[(scenario, controller)]]
        return statistics.mean(values)

    candidates = [name for name in controller_specs if name.startswith(("improved_", "adaptive_"))]
    evaluations = []
    for name in candidates:
        reasons = []
        metrics: dict[str, dict[str, float]] = {}
        for scenario in OVERLOAD_SCENARIOS:
            metrics[scenario] = {}
            for metric in ("average_queue_length", "waiting_at_end", "throughput_per_hour"):
                candidate = average(scenario, name, metric)
                original = average(scenario, "queue_based", metric)
                metrics[scenario][metric] = candidate
                qualifies = candidate < original if metric != "throughput_per_hour" else candidate >= original
                if not qualifies:
                    reasons.append(
                        f"{scenario}: {metric} {candidate:.4g} vs original {original:.4g}"
                    )
        for scenario in MODERATE_SCENARIOS:
            metrics[scenario] = {}
            for metric in ("average_wait_seconds", "average_queue_length"):
                candidate = average(scenario, name, metric)
                original = average(scenario, "queue_based", metric)
                metrics[scenario][metric] = candidate
                if candidate > 1.10 * original:
                    reasons.append(
                        f"{scenario}: {metric} worsens by {(candidate / original - 1) * 100:.2f}%"
                    )
        evaluations.append(
            {
                "name": name,
                "parameters": controller_specs[name],
                "eligible": not reasons,
                "reasons": reasons,
                "metrics": metrics,
            }
        )

    eligible = [item for item in evaluations if item["eligible"]]
    selected = None
    if eligible:
        selected = min(
            eligible,
            key=lambda item: (
                item["metrics"]["high_load"]["average_queue_length"],
                item["parameters"].get("relative_switching_margin", 0.0),
                item["parameters"].get("congested_min_green_seconds", item["parameters"].get("min_green_seconds", 0)),
                item["parameters"].get("max_green_seconds", 0),
            ),
        )["name"]
    return {
        "development_file": str(path),
        "seeds": payload["configuration"]["simulation"]["seeds"],
        "candidate_count": len(evaluations),
        "eligible_candidates": [item["name"] for item in eligible],
        "selected_candidate": selected,
        "selection_rule": {
            "overload": "lower mean average queue and lower residual, with throughput no lower than original",
            "moderate": "mean completed wait and average queue no more than 10% above original",
            "ranking": "lowest 18/min mean average queue; tie prefers smaller relative margin, shorter congested minimum, then shorter maximum; remaining ties retain explicit candidate order (threshold 6, 10, 14)",
        },
        "candidates": evaluations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = assess_development(args.file)
    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(
        f"candidates={result['candidate_count']}; eligible={len(result['eligible_candidates'])}; "
        f"selected={result['selected_candidate'] or 'none'}"
    )
    if not result["eligible_candidates"]:
        for candidate in result["candidates"]:
            print(candidate["name"] + ": " + "; ".join(candidate["reasons"]))


if __name__ == "__main__":
    main()
