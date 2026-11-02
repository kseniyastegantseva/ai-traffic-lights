"""Build a compact dashboard payload from full PIERE and perception runs."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
CONTROLLERS = (
    "fixed_15",
    "fixed_35",
    "fixed_webster",
    "vehicle_actuated",
    "queue_based",
    "queue_based_legacy",
)
SCENARIOS = (
    "symmetric",
    "asymmetric_ns",
    "variable_demand",
    "sudden_dominance_switch",
    "high_load",
    "symmetric_low",
    "symmetric_9",
    "asymmetric_ew",
    "true_oversaturated",
)
EXAMPLE_SEED = 101


def load_result(name: str) -> dict:
    return json.loads((OUTPUTS / name).read_text(encoding="utf-8"))


def enrich_summary(payload: dict) -> list[dict]:
    residuals: dict[tuple[str, str], list[float]] = defaultdict(list)
    delays: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in payload["runs"]:
        key = (row["scenario"], row["controller"])
        residuals[key].append(float(row["waiting_at_end"]))
        delays[key].append(float(row["observed_delay_seconds"]))
    enriched = []
    for row in payload["summary"]:
        key = (row["scenario"], row["controller"])
        enriched.append(
            {
                **row,
                "mean_waiting_at_end": mean(residuals[key]),
                "mean_observed_delay_seconds": mean(delays[key]),
                "horizon_seconds": int(payload["runs"][0]["duration_seconds"]),
            }
        )
    return enriched


def build_trace_data(payload: dict) -> dict:
    by_group: dict[tuple[str, str], list[dict]] = defaultdict(list)
    example_runs: dict[tuple[str, str], dict] = {}
    for run in payload["runs"]:
        if run["scenario"] not in SCENARIOS:
            continue
        key = (run["scenario"], run["controller"])
        by_group[key].append(run)
        if int(run["seed"]) == EXAMPLE_SEED:
            example_runs[key] = run

    traces = {}
    for scenario in SCENARIOS:
        traces[scenario] = {}
        for controller in CONTROLLERS:
            key = (scenario, controller)
            runs = by_group.get(key, [])
            if not runs:
                continue
            arrays = [np.asarray(run["queue_series"], dtype=np.float64) for run in runs]
            if len({array.size for array in arrays}) != 1:
                raise ValueError(f"Queue trace lengths differ for {key}")
            example = example_runs.get(key)
            traces[scenario][controller] = {
                "mean_queue_series": np.mean(np.stack(arrays), axis=0).round(3).tolist(),
                "example_seed": EXAMPLE_SEED if example else None,
                "example_arrival_stream_sha256": (
                    example["arrival_stream_sha256"] if example else None
                ),
                "example_queue_series": example["queue_series"] if example else None,
                "example_phase_history": example["phase_history"] if example else None,
            }
        hashes = {
            traces[scenario][controller]["example_arrival_stream_sha256"]
            for controller in traces[scenario]
            if traces[scenario][controller]["example_arrival_stream_sha256"]
        }
        if len(hashes) > 1:
            raise ValueError(f"Controllers do not share the same example arrival stream: {scenario}")
    return traces


def perception_records(payload: dict, expanded: bool) -> list[dict]:
    rows = []
    for row in payload["summary"]:
        if row["controller"] != "queue_based":
            continue
        scenario = row["scenario"]
        if expanded:
            regime, rate_label = scenario.rsplit("_", 1)
            rate = {"0pct": 0.0, "5pct": 0.05, "10pct": 0.1, "20pct": 0.2}[rate_label]
        else:
            regime = scenario
            rate = None
        rows.append({**row, "regime": regime, "observation_error_rate": rate})
    return rows


def main() -> None:
    payloads = {
        1800: load_result("piere_revision_1800.json"),
        3600: load_result("piere_revision_3600.json"),
    }
    addenda = {
        1800: load_result("piere_revision_addendum_1800.json"),
        3600: load_result("piere_revision_addendum_3600.json"),
    }
    summary = {
        str(horizon): enrich_summary(payload) + enrich_summary(addenda[horizon])
        for horizon, payload in payloads.items()
    }
    sensitivity = load_result("piere_perception_sensitivity_expanded.json")
    empirical = load_result("piere_perception_empirical_errors.json")
    dashboard = {
        "schema_version": 1,
        "source_files": [
            "outputs/piere_revision_1800.json",
            "outputs/piere_revision_3600.json",
            "outputs/piere_revision_addendum_1800.json",
            "outputs/piere_revision_addendum_3600.json",
            "outputs/piere_perception_sensitivity_expanded.json",
            "outputs/piere_perception_empirical_errors.json",
        ],
        "example_seed": EXAMPLE_SEED,
        "summary": summary,
        "paired_statistics": {
            str(horizon): payload["paired_statistics"]
            for horizon, payload in payloads.items()
        },
        "queue_traces_3600": build_trace_data({"runs": payloads[3600]["runs"] + addenda[3600]["runs"]}),
        "perception_sensitivity": perception_records(sensitivity, expanded=True),
        "perception_empirical_bootstrap": perception_records(empirical, expanded=False),
    }
    target = OUTPUTS / "piere_dashboard_data.json"
    target.write_text(json.dumps(dashboard, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {target} ({target.stat().st_size / 1024:.1f} KiB)")


if __name__ == "__main__":
    main()
