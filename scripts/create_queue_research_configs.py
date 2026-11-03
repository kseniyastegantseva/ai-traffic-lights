"""Create versioned, seed-explicit configurations for queue-controller research."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_SEEDS = list(range(701, 716))
ADAPTIVE_DEVELOPMENT_SEEDS = list(range(801, 816))
FINAL_SEEDS = list(range(1001, 1031))
INITIAL_STATE_SEEDS = list(range(1101, 1131))


def load(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def make_controllers(include_development_grid: bool = False) -> list[dict]:
    controllers = [
        {"type": "fixed_8"},
        {"type": "fixed_15"},
        {"type": "fixed_35"},
        {"type": "fixed_webster"},
        {"type": "vehicle_actuated"},
        {"type": "queue_based", "min_green_seconds": 8, "max_green_seconds": 45, "switching_margin": 1},
    ]
    if include_development_grid:
        for minimum in (15, 20, 25):
            for relative_margin in (0.0, 0.10):
                for maximum in (35, 45, 60):
                    controllers.append(
                        {
                            "type": "queue_based_improved",
                            "min_green_seconds": minimum,
                            "max_green_seconds": maximum,
                            "switching_margin": 1,
                            "relative_switching_margin": relative_margin,
                            "congested_min_green_seconds": minimum,
                            "congestion_queue_threshold": 0,
                            "result_name": (
                                f"improved_min{minimum}_max{maximum}_rel{relative_margin:g}"
                            ),
                        }
                    )
        controllers.append(
            {"type": "queue_based", "legacy_rule": True, "min_green_seconds": 8, "max_green_seconds": 45}
        )
    else:
        controllers.extend(
            [
                {
                    "type": "queue_based_improved",
                    "min_green_seconds": 8,
                    "max_green_seconds": 45,
                    "switching_margin": 1,
                    "relative_switching_margin": 0.10,
                    "congested_min_green_seconds": 20,
                    "congestion_queue_threshold": 10,
                },
                {"type": "queue_based", "legacy_rule": True, "min_green_seconds": 8, "max_green_seconds": 45},
            ]
        )
    return controllers


def make_adaptive_controllers() -> list[dict]:
    controllers = [
        c for c in make_controllers(include_development_grid=False)
        if c["type"] != "queue_based_improved"
    ]
    for congested_minimum in (15, 20, 25):
        for threshold in (6, 10, 14):
            for relative_margin in (0.0, 0.10):
                controllers.append(
                    {
                        "type": "queue_based_improved",
                        "min_green_seconds": 8,
                        "max_green_seconds": 45,
                        "switching_margin": 1,
                        "relative_switching_margin": relative_margin,
                        "congested_min_green_seconds": congested_minimum,
                        "congestion_queue_threshold": threshold,
                        "result_name": (
                            f"adaptive_high{congested_minimum}_threshold{threshold}_rel{relative_margin:g}"
                        ),
                    }
                )
    return controllers


def write_config(path: Path, config: dict) -> None:
    path.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )


def main() -> None:
    primary = load("configs/piere_revision_1800.yaml")
    addendum = load("configs/piere_revision_addendum_1800.yaml")
    scenarios = deepcopy(primary["scenarios"] + addendum["scenarios"])

    development_scenarios = [
        deepcopy(next(s for s in scenarios if s["name"] == name))
        for name in ("symmetric", "symmetric_low", "high_load", "true_oversaturated")
    ]
    development = {
        "name": "queue_based_development_1800",
        "title": "Queue-based controller development, 1800 s",
        "description": (
            "Development-only parameter screen. Seeds 701–715 are excluded from final validation. "
            "Predeclared eligibility: at 18 and 24 vehicles/min/approach, mean queue area and "
            "residual must be lower and throughput no lower than original; at symmetric 3 and 6, "
            "completed wait and mean queue may not worsen by more than 10%. Among eligible variants, "
            "choose the lowest 18/min mean queue area; ties prefer the smaller relative margin, then "
            "shorter minimum green. The final seed set is untouched during selection."
        ),
        "simulation": {
            "duration_seconds": 1800,
            "seeds": DEVELOPMENT_SEEDS,
            "service_time_seconds": 2.0,
            "store_queue_series": False,
        },
        "scenarios": development_scenarios,
        "controllers": make_controllers(include_development_grid=True),
        "output": {
            "path": "outputs/queue_based_development_1800.json",
            "summary_csv": "outputs/queue_based_development_1800_summary.csv",
            "report_markdown": "outputs/queue_based_development_1800_report.md",
        },
    }
    write_config(ROOT / "configs/queue_based_development_1800.yaml", development)

    adaptive_development = deepcopy(development)
    adaptive_development.update(
        name="queue_based_adaptive_development_1800",
        title="Queue-based adaptive minimum development, 1800 s",
        description=(
            "Second development stage on untouched seeds 801–815. The constant-minimum screen "
            "showed a material low-demand penalty and was not selected. This screen tests base "
            "min-green 8 s with congestion-triggered longer holds. The final seed set 1001–1030 "
            "remains untouched."
        ),
        simulation={**development["simulation"], "seeds": ADAPTIVE_DEVELOPMENT_SEEDS},
        controllers=make_adaptive_controllers(),
        output={
            "path": "outputs/queue_based_adaptive_development_1800.json",
            "summary_csv": "outputs/queue_based_adaptive_development_1800_summary.csv",
            "report_markdown": "outputs/queue_based_adaptive_development_1800_report.md",
        },
    )
    write_config(
        ROOT / "configs/queue_based_adaptive_development_1800.yaml", adaptive_development
    )

    for duration in (1800, 3600):
        config = {
            "name": f"queue_based_final_{duration}",
            "title": f"Queue-based final validation, {duration} s",
            "description": (
                "Locked controller parameters and unseen seeds 1001–1030. Includes the nine "
                "predeclared PIERE demand scenarios; every controller within a scenario/seed "
                "uses the same generated arrival stream. No warm-up is removed."
            ),
            "simulation": {
                "duration_seconds": duration,
                "seeds": FINAL_SEEDS,
                "service_time_seconds": 2.0,
                "store_queue_series": False,
            },
            "scenarios": deepcopy(scenarios),
            "controllers": make_controllers(include_development_grid=False),
            "output": {
                "path": f"outputs/queue_based_final_{duration}.json",
                "summary_csv": f"outputs/queue_based_final_{duration}_summary.csv",
                "report_markdown": f"outputs/queue_based_final_{duration}_report.md",
            },
        }
        write_config(ROOT / f"configs/queue_based_final_{duration}.yaml", config)

    symmetric = deepcopy(next(s for s in scenarios if s["name"] == "symmetric"))
    empty = deepcopy(symmetric)
    empty.update(name="initial_empty", title="Пустое начальное состояние")
    queued = deepcopy(symmetric)
    queued.update(
        name="initial_five_each",
        title="По пять автомобилей в начальной очереди каждого подхода",
        initial_queues={lane: 5 for lane in ("north", "south", "east", "west")},
    )
    initial_state = {
        "name": "queue_based_initial_state_1800",
        "title": "Sensitivity to initial queues, 1800 s",
        "description": (
            "Matched arrivals and unseen seeds 1101–1130 compare the empty initial state with five "
            "initial vehicles per approach. No warm-up is removed; queue samples support a separate "
            "full-horizon versus post-300-s transient sensitivity summary."
        ),
        "simulation": {
            "duration_seconds": 1800,
            "seeds": INITIAL_STATE_SEEDS,
            "service_time_seconds": 2.0,
            "store_queue_series": True,
        },
        "scenarios": [empty, queued],
        "controllers": [
            {"type": "fixed_8"},
            {"type": "vehicle_actuated"},
            {"type": "queue_based", "min_green_seconds": 8, "max_green_seconds": 45, "switching_margin": 1},
            {
                "type": "queue_based_improved",
                "min_green_seconds": 8,
                "max_green_seconds": 45,
                "switching_margin": 1,
                "relative_switching_margin": 0.10,
                "congested_min_green_seconds": 20,
                "congestion_queue_threshold": 10,
            },
        ],
        "output": {
            "path": "outputs/queue_based_initial_state_1800.json",
            "summary_csv": "outputs/queue_based_initial_state_1800_summary.csv",
            "report_markdown": "outputs/queue_based_initial_state_1800_report.md",
        },
    }
    write_config(ROOT / "configs/queue_based_initial_state_1800.yaml", initial_state)


if __name__ == "__main__":
    main()
