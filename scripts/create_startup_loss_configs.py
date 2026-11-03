"""Create a seed-paired startup lost-time sensitivity series."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SEEDS = list(range(11101, 11131))
SCENARIOS = {
    "symmetric_low",
    "symmetric",
    "symmetric_9",
    "asymmetric_ns",
    "asymmetric_ew",
    "sudden_dominance_switch",
    "high_load",
    "true_oversaturated",
}


def controllers() -> list[dict]:
    common = {
        "min_green_seconds": 8,
        "max_green_seconds": 45,
        "switching_margin": 1,
        "relative_switching_margin": 0.10,
        "congested_min_green_seconds": 25,
        "congestion_queue_threshold": 14,
    }
    variants = [
        {"type": "fixed_8"},
        {"type": "fixed_15"},
        {"type": "fixed_35"},
        {"type": "fixed_webster"},
        {"type": "vehicle_actuated"},
        {"type": "queue_based", **common},
        {"type": "queue_based", "legacy_rule": True, **common},
        {"type": "queue_based_improved", **common},
        {
            "type": "queue_based_empty_gap_fix",
            **common,
            "empty_gap_seconds": 1.0,
            "result_name": "queue_based_empty_gap_1s",
        },
        {
            "type": "queue_based_max_red",
            **common,
            "max_red_seconds": 42.0,
            "result_name": "queue_based_max_red_42s",
        },
        {
            "type": "queue_based_smooth_min_green",
            **common,
            "smooth_congestion_start_queue": 10,
            "smooth_congestion_end_queue": 18,
            "result_name": "queue_based_smooth_10_18",
        },
        {
            "type": "queue_based_hysteresis",
            **common,
            "congestion_exit_threshold": 10,
            "result_name": "queue_based_hysteresis_14_10",
        },
        {
            "type": "queue_based_persistent_congestion",
            **common,
            "congestion_persistence_seconds": 5.0,
            "result_name": "queue_based_persistent_5s",
        },
        {
            "type": "queue_based_axis_specific_congestion",
            **common,
            "result_name": "queue_based_axis_specific_14",
        },
        {
            "type": "queue_based_improved",
            **common,
            "relative_switching_margin": 0.20,
            "result_name": "queue_based_relative_margin_020",
        },
        {
            "type": "queue_based_elapsed_margin",
            **common,
            "switching_margin_decay_per_second": 0.025,
            "result_name": "queue_based_elapsed_margin_025",
        },
    ]
    return variants


def main() -> None:
    source = yaml.safe_load(
        (ROOT / "configs/queue_based_final_1800.yaml").read_text(encoding="utf-8")
    )
    scenarios = [deepcopy(item) for item in source["scenarios"] if item["name"] in SCENARIOS]
    if {item["name"] for item in scenarios} != SCENARIOS:
        raise ValueError("The locked source is missing a requested demand scenario")

    for startup_loss in (0.0, 1.0, 2.0, 3.0):
        stem = f"startup_loss_{startup_loss:g}_1800"
        config = {
            "name": f"total_improvement_{stem}",
            "title": f"Startup lost time {startup_loss:g} s sensitivity, 1800 s",
            "description": (
                "Paired sensitivity of a separately modeled phase startup delay. Saturation "
                "service headway stays 2 s, yellow clearance stays 3 s, and dynamic all-red "
                "only clears active service. All policies share the same arrivals within each "
                "scenario/seed; these sensitivity seeds do not tune controller parameters."
            ),
            "simulation": {
                "duration_seconds": 1800,
                "seeds": SEEDS,
                "service_time_seconds": 2.0,
                "startup_lost_time_seconds": startup_loss,
                "store_queue_series": False,
            },
            "scenarios": scenarios,
            "controllers": controllers(),
            "output": {
                "path": f"outputs/total_improvement/{stem}.json",
                "summary_csv": f"outputs/total_improvement/{stem}_summary.csv",
                "report_markdown": f"outputs/total_improvement/{stem}_report.md",
            },
        }
        target = ROOT / "configs" / f"total_improvement_{stem}.yaml"
        target.write_text(
            yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=100),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
