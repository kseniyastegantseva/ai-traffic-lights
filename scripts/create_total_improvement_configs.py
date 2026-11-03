"""Create a seed-explicit development experiment for the empty-green diagnostic."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SEEDS = list(range(2101, 2131))
CAPACITY_SEEDS = list(range(3101, 3116))
MAX_RED_SEEDS = list(range(4101, 4131))
MIN_GREEN_SEEDS = list(range(5101, 5131))
AXIS_SPECIFIC_SEEDS = list(range(7101, 7131))
SWITCHING_MARGIN_SEEDS = list(range(8101, 8131))
SWITCHING_MARGIN_VALIDATION_SEEDS = list(range(9101, 9131))
SCENARIOS = (
    "symmetric_low",
    "symmetric",
    "symmetric_9",
    "asymmetric_ns",
    "asymmetric_ew",
    "sudden_dominance_switch",
    "high_load",
    "true_oversaturated",
)


def main() -> None:
    source = yaml.safe_load(
        (ROOT / "configs/queue_based_final_1800.yaml").read_text(encoding="utf-8")
    )
    scenarios = [
        deepcopy(scenario)
        for scenario in source["scenarios"]
        if scenario["name"] in SCENARIOS
    ]
    if {scenario["name"] for scenario in scenarios} != set(SCENARIOS):
        raise ValueError("The source configuration is missing a requested scenario")

    controllers = [
        {"type": "fixed_8"},
        {"type": "vehicle_actuated"},
        {
            "type": "queue_based",
            "min_green_seconds": 8,
            "max_green_seconds": 45,
            "switching_margin": 1,
        },
        {
            "type": "queue_based",
            "legacy_rule": True,
            "min_green_seconds": 8,
            "max_green_seconds": 45,
            "switching_margin": 1,
        },
        {
            "type": "queue_based_improved",
            "min_green_seconds": 8,
            "max_green_seconds": 45,
            "switching_margin": 1,
            "relative_switching_margin": 0.10,
            "congested_min_green_seconds": 25,
            "congestion_queue_threshold": 14,
        },
    ]
    for gap_seconds in (0.0, 1.0, 3.0):
        controllers.append(
            {
                "type": "queue_based_empty_gap_fix",
                "min_green_seconds": 8,
                "max_green_seconds": 45,
                "switching_margin": 1,
                "relative_switching_margin": 0.10,
                "congested_min_green_seconds": 25,
                "congestion_queue_threshold": 14,
                "empty_gap_seconds": gap_seconds,
                "result_name": f"queue_based_empty_gap_{gap_seconds:g}s",
            }
        )

    config = {
        "name": "total_improvement_empty_gap_development_1800",
        "title": "Диагностика empty-green gap-out, development, 1800 с",
        "description": (
            "Exploratory development comparison on seeds 2101–2130, separate from previous "
            "experiments. Every controller shares the same Poisson arrival stream per "
            "scenario/seed. Tests 0/1/3-second empty-current-axis gap-out against Fixed 8, "
            "Vehicle-actuated, Queue-based original/legacy and locked Queue-based Improved. "
            "These seeds are not a final test set."
        ),
        "simulation": {
            "duration_seconds": 1800,
            "seeds": SEEDS,
            "service_time_seconds": 2.0,
            "store_queue_series": False,
        },
        "scenarios": scenarios,
        "controllers": controllers,
        "output": {
            "path": "outputs/total_improvement/empty_gap_development_1800.json",
            "summary_csv": "outputs/total_improvement/empty_gap_development_1800_summary.csv",
            "report_markdown": "outputs/total_improvement/empty_gap_development_1800_report.md",
        },
    }
    target = ROOT / "configs/total_improvement_empty_gap_development_1800.yaml"
    target.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )

    capacity_scenario = deepcopy(next(s for s in source["scenarios"] if s["name"] == "symmetric_low"))
    capacity_scenarios = []
    for rate in range(9, 19):
        scenario = deepcopy(capacity_scenario)
        scenario["name"] = f"demand_{rate}"
        scenario["title"] = f"Симметричный спрос {rate} авто/мин/подход"
        scenario["description"] = (
            f"{rate} автомобиля в минуту на каждом подходе; development screen, не final test."
        )
        for lane_config in scenario["intersection"]["lanes"].values():
            lane_config["arrival_rate_per_minute"] = rate
        capacity_scenarios.append(scenario)

    capacity_controllers = [
        {"type": "fixed_8"},
        {"type": "fixed_15"},
        {"type": "fixed_35"},
        {"type": "fixed_webster"},
        {"type": "vehicle_actuated"},
        {"type": "queue_based", "min_green_seconds": 8, "max_green_seconds": 45},
        {
            "type": "queue_based_improved",
            "min_green_seconds": 8,
            "max_green_seconds": 45,
            "switching_margin": 1,
            "relative_switching_margin": 0.10,
            "congested_min_green_seconds": 25,
            "congestion_queue_threshold": 14,
        },
        {"type": "queue_based", "legacy_rule": True, "min_green_seconds": 8, "max_green_seconds": 45},
        {
            "type": "queue_based_empty_gap_fix",
            "min_green_seconds": 8,
            "max_green_seconds": 45,
            "switching_margin": 1,
            "relative_switching_margin": 0.10,
            "congested_min_green_seconds": 25,
            "congestion_queue_threshold": 14,
            "empty_gap_seconds": 1.0,
            "result_name": "queue_based_empty_gap_1s",
        },
    ]
    capacity_config = {
        "name": "total_improvement_capacity_boundary_1800",
        "title": "Граница насыщения 9–18 авто/мин/подход, development, 1800 с",
        "description": (
            "Paired exploratory load sweep across 9–18 vehicles/minute/approach on seeds 3101–3115. "
            "All controllers share arrivals within a demand/seed pair. The screen reports completed "
            "wait together with queue area, residual, throughput, switching, yellow and signal-red "
            "metrics; it is not an independent final test."
        ),
        "simulation": {
            "duration_seconds": 1800,
            "seeds": CAPACITY_SEEDS,
            "service_time_seconds": 2.0,
            "store_queue_series": False,
        },
        "scenarios": capacity_scenarios,
        "controllers": capacity_controllers,
        "output": {
            "path": "outputs/total_improvement/capacity_boundary_1800.json",
            "summary_csv": "outputs/total_improvement/capacity_boundary_1800_summary.csv",
            "report_markdown": "outputs/total_improvement/capacity_boundary_1800_report.md",
        },
    }
    capacity_target = ROOT / "configs/total_improvement_capacity_boundary_1800.yaml"
    capacity_target.write_text(
        yaml.safe_dump(capacity_config, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )

    extended_capacity = deepcopy(capacity_config)
    extended_capacity.update(
        name="total_improvement_capacity_boundary_3600",
        title="Граница насыщения 9–18 авто/мин/подход, development, 3600 с",
        description=(
            "Extended-horizon paired development screen using the same 3101–3115 seed IDs and "
            "arrival prefixes as the 1800-second sweep; results at each horizon are reported "
            "separately and are not independent seed replications."
        ),
    )
    extended_capacity["simulation"]["duration_seconds"] = 3600
    extended_capacity["output"] = {
        "path": "outputs/total_improvement/capacity_boundary_3600.json",
        "summary_csv": "outputs/total_improvement/capacity_boundary_3600_summary.csv",
        "report_markdown": "outputs/total_improvement/capacity_boundary_3600_report.md",
    }
    extended_target = ROOT / "configs/total_improvement_capacity_boundary_3600.yaml"
    extended_target.write_text(
        yaml.safe_dump(extended_capacity, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )

    max_red_scenarios = [
        deepcopy(scenario)
        for scenario in source["scenarios"]
        if scenario["name"] in (
            "symmetric_low",
            "asymmetric_ns",
            "asymmetric_ew",
            "sudden_dominance_switch",
            "high_load",
            "true_oversaturated",
        )
    ]
    max_red_controllers = [
        {
            "type": "vehicle_actuated",
            "min_green_seconds": 8,
            "max_green_seconds": 45,
            "result_name": "vehicle_actuated",
        },
        {
            "type": "queue_based_improved",
            "min_green_seconds": 8,
            "max_green_seconds": 45,
            "switching_margin": 1,
            "relative_switching_margin": 0.10,
            "congested_min_green_seconds": 25,
            "congestion_queue_threshold": 14,
        },
    ]
    for max_red_seconds in (36, 42, 48):
        max_red_controllers.append(
            {
                "type": "queue_based_max_red",
                "min_green_seconds": 8,
                "max_green_seconds": 45,
                "switching_margin": 1,
                "relative_switching_margin": 0.10,
                "congested_min_green_seconds": 25,
                "congestion_queue_threshold": 14,
                "max_red_seconds": max_red_seconds,
                "result_name": f"queue_based_max_red_{max_red_seconds}s",
            }
        )
    max_red_config = {
        "name": "total_improvement_max_red_development_1800",
        "title": "Ограничение непрерывного red, development, 1800 с",
        "description": (
            "Exploratory paired fairness screen on six balanced, asymmetric, changing and high-load "
            "scenarios with seeds 4101–4130. The candidate adds a phase-level red timer to locked "
            "Queue-based Improved; the competing phase is forced at 36/42/48 seconds once its "
            "minimum-green condition is satisfied. Vehicle-actuated is included as a baseline."
        ),
        "simulation": {
            "duration_seconds": 1800,
            "seeds": MAX_RED_SEEDS,
            "service_time_seconds": 2.0,
            "store_queue_series": False,
        },
        "scenarios": max_red_scenarios,
        "controllers": max_red_controllers,
        "output": {
            "path": "outputs/total_improvement/max_red_development_1800.json",
            "summary_csv": "outputs/total_improvement/max_red_development_1800_summary.csv",
            "report_markdown": "outputs/total_improvement/max_red_development_1800_report.md",
        },
    }
    max_red_target = ROOT / "configs/total_improvement_max_red_development_1800.yaml"
    max_red_target.write_text(
        yaml.safe_dump(max_red_config, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )

    min_green_scenarios = [
        deepcopy(scenario)
        for scenario in source["scenarios"]
        if scenario["name"] in (
            "symmetric_low",
            "symmetric_9",
            "asymmetric_ns",
            "asymmetric_ew",
            "sudden_dominance_switch",
            "high_load",
            "true_oversaturated",
        )
    ]
    min_green_controllers = [
        {
            "type": "vehicle_actuated",
            "min_green_seconds": 8,
            "max_green_seconds": 45,
            "result_name": "vehicle_actuated",
        },
        {
            "type": "queue_based",
            "min_green_seconds": 8,
            "max_green_seconds": 45,
            "switching_margin": 1,
        },
        {
            "type": "queue_based_improved",
            "min_green_seconds": 8,
            "max_green_seconds": 45,
            "switching_margin": 1,
            "relative_switching_margin": 0.10,
            "congested_min_green_seconds": 25,
            "congestion_queue_threshold": 14,
        },
        {
            "type": "queue_based_smooth_min_green",
            "min_green_seconds": 8,
            "max_green_seconds": 45,
            "switching_margin": 1,
            "relative_switching_margin": 0.10,
            "congested_min_green_seconds": 25,
            "congestion_queue_threshold": 14,
            "smooth_congestion_start_queue": 10,
            "smooth_congestion_end_queue": 18,
            "result_name": "queue_based_smooth_min_green_10_18",
        },
        {
            "type": "queue_based_hysteresis",
            "min_green_seconds": 8,
            "max_green_seconds": 45,
            "switching_margin": 1,
            "relative_switching_margin": 0.10,
            "congested_min_green_seconds": 25,
            "congestion_queue_threshold": 14,
            "congestion_exit_threshold": 10,
            "result_name": "queue_based_hysteresis_14_10",
        },
        {
            "type": "queue_based_persistent_congestion",
            "min_green_seconds": 8,
            "max_green_seconds": 45,
            "switching_margin": 1,
            "relative_switching_margin": 0.10,
            "congested_min_green_seconds": 25,
            "congestion_queue_threshold": 14,
            "congestion_persistence_seconds": 5,
            "result_name": "queue_based_persistent_5s",
        },
        {
            "type": "queue_based_persistent_congestion",
            "min_green_seconds": 8,
            "max_green_seconds": 45,
            "switching_margin": 1,
            "relative_switching_margin": 0.10,
            "congested_min_green_seconds": 25,
            "congestion_queue_threshold": 14,
            "congestion_persistence_seconds": 10,
            "result_name": "queue_based_persistent_10s",
        },
    ]
    min_green_config = {
        "name": "total_improvement_min_green_dynamics_1800",
        "title": "Плавный и устойчивый minimum green, development, 1800 с",
        "description": (
            "Paired 30-seed development screen (5101–5130) comparing the locked Improved controller "
            "with a linear queue ramp, enter/exit hysteresis and persistent-congestion variants. "
            "The strategies retain the same base/congested min/max green and queue-switch margin; "
            "only the congestion activation rule changes."
        ),
        "simulation": {
            "duration_seconds": 1800,
            "seeds": MIN_GREEN_SEEDS,
            "service_time_seconds": 2.0,
            "store_queue_series": False,
        },
        "scenarios": min_green_scenarios,
        "controllers": min_green_controllers,
        "output": {
            "path": "outputs/total_improvement/min_green_dynamics_1800.json",
            "summary_csv": "outputs/total_improvement/min_green_dynamics_1800_summary.csv",
            "report_markdown": "outputs/total_improvement/min_green_dynamics_1800_report.md",
        },
    }
    min_green_target = ROOT / "configs/total_improvement_min_green_dynamics_1800.yaml"
    min_green_target.write_text(
        yaml.safe_dump(min_green_config, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )

    validation = deepcopy(min_green_config)
    validation.update(
        name="total_improvement_min_green_validation_1800",
        title="Независимая проверка плавного minimum green, 1800 с",
        description=(
            "Independent paired validation on previously unused seeds 6101–6130. Compares the locked "
            "Queue-based Improved rule with the preselected linear minimum-green ramp from the "
            "development screen, across the same seven demand regimes. This is a confirmation set, "
            "not used for parameter selection."
        ),
    )
    validation["simulation"]["seeds"] = list(range(6101, 6131))
    validation["controllers"] = [
        deepcopy(controller)
        for controller in min_green_controllers
        if controller["type"] in {"queue_based_improved", "queue_based_smooth_min_green"}
    ]
    validation["output"] = {
        "path": "outputs/total_improvement/min_green_validation_1800.json",
        "summary_csv": "outputs/total_improvement/min_green_validation_1800_summary.csv",
        "report_markdown": "outputs/total_improvement/min_green_validation_1800_report.md",
    }
    validation_target = ROOT / "configs/total_improvement_min_green_validation_1800.yaml"
    validation_target.write_text(
        yaml.safe_dump(validation, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )

    axis_scenarios = [
        deepcopy(scenario)
        for scenario in source["scenarios"]
        if scenario["name"] in (
            "symmetric_low",
            "symmetric_9",
            "asymmetric_ns",
            "asymmetric_ew",
            "sudden_dominance_switch",
            "high_load",
            "true_oversaturated",
        )
    ]
    axis_controllers = [
        {"type": "vehicle_actuated", "min_green_seconds": 8, "max_green_seconds": 45},
        {"type": "queue_based", "min_green_seconds": 8, "max_green_seconds": 45, "switching_margin": 1},
        {
            "type": "queue_based_improved",
            "min_green_seconds": 8,
            "max_green_seconds": 45,
            "switching_margin": 1,
            "relative_switching_margin": 0.10,
            "congested_min_green_seconds": 25,
            "congestion_queue_threshold": 14,
        },
        {
            "type": "queue_based_axis_specific_congestion",
            "min_green_seconds": 8,
            "max_green_seconds": 45,
            "switching_margin": 1,
            "relative_switching_margin": 0.10,
            "congested_min_green_seconds": 25,
            "congestion_queue_threshold": 14,
        },
    ]
    axis_config = {
        "name": "total_improvement_axis_specific_congestion_1800",
        "title": "Congestion по обслуживаемой оси, development, 1800 с",
        "description": (
            "Paired development screen on new seeds 7101–7130. Compares the current intersection-total "
            "congestion trigger with a policy that activates the 25-second minimum only when the "
            "currently served axis itself has at least 14 queued vehicles. Includes original Queue-based "
            "and Vehicle-actuated references."
        ),
        "simulation": {
            "duration_seconds": 1800,
            "seeds": AXIS_SPECIFIC_SEEDS,
            "service_time_seconds": 2.0,
            "store_queue_series": False,
        },
        "scenarios": axis_scenarios,
        "controllers": axis_controllers,
        "output": {
            "path": "outputs/total_improvement/axis_specific_congestion_1800.json",
            "summary_csv": "outputs/total_improvement/axis_specific_congestion_1800_summary.csv",
            "report_markdown": "outputs/total_improvement/axis_specific_congestion_1800_report.md",
        },
    }
    axis_target = ROOT / "configs/total_improvement_axis_specific_congestion_1800.yaml"
    axis_target.write_text(
        yaml.safe_dump(axis_config, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )

    margin_controllers = [
        {"type": "vehicle_actuated", "min_green_seconds": 8, "max_green_seconds": 45},
        {"type": "queue_based", "min_green_seconds": 8, "max_green_seconds": 45, "switching_margin": 1},
    ]
    for absolute_margin, relative_margin, result_name in (
        (1, 0.10, "improved_abs1_rel010"),
        (0, 0.0, "margin_abs0_rel000"),
        (1, 0.0, "margin_abs1_rel000"),
        (2, 0.0, "margin_abs2_rel000"),
        (1, 0.20, "margin_abs1_rel020"),
    ):
        margin_controllers.append(
            {
                "type": "queue_based_improved",
                "min_green_seconds": 8,
                "max_green_seconds": 45,
                "switching_margin": absolute_margin,
                "relative_switching_margin": relative_margin,
                "congested_min_green_seconds": 25,
                "congestion_queue_threshold": 14,
                "result_name": result_name,
            }
        )
    margin_controllers.append(
        {
            "type": "queue_based_elapsed_margin",
            "min_green_seconds": 8,
            "max_green_seconds": 45,
            "switching_margin": 1,
            "relative_switching_margin": 0.20,
            "congested_min_green_seconds": 25,
            "congestion_queue_threshold": 14,
            "switching_margin_decay_per_second": 0.025,
            "minimum_switching_margin": 1,
            "result_name": "margin_elapsed_decay_0025",
        }
    )
    margin_scenarios = [
        deepcopy(scenario)
        for scenario in source["scenarios"]
        if scenario["name"] in (
            "symmetric_low",
            "symmetric_9",
            "asymmetric_ns",
            "asymmetric_ew",
            "sudden_dominance_switch",
            "high_load",
            "true_oversaturated",
        )
    ]
    margin_config = {
        "name": "total_improvement_switching_margin_1800",
        "title": "Абсолютные, относительные и временные пороги переключения, 1800 с",
        "description": (
            "Paired development screen on new seeds 8101–8130. Compares absolute and relative "
            "queue margins, including zero/low/high values and a time-decaying margin that relaxes "
            "after effective minimum green. Original Queue-based and Vehicle-actuated references are included."
        ),
        "simulation": {
            "duration_seconds": 1800,
            "seeds": SWITCHING_MARGIN_SEEDS,
            "service_time_seconds": 2.0,
            "store_queue_series": False,
        },
        "scenarios": margin_scenarios,
        "controllers": margin_controllers,
        "output": {
            "path": "outputs/total_improvement/switching_margin_1800.json",
            "summary_csv": "outputs/total_improvement/switching_margin_1800_summary.csv",
            "report_markdown": "outputs/total_improvement/switching_margin_1800_report.md",
        },
    }
    margin_target = ROOT / "configs/total_improvement_switching_margin_1800.yaml"
    margin_target.write_text(
        yaml.safe_dump(margin_config, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )

    margin_validation = deepcopy(margin_config)
    margin_validation.update(
        name="total_improvement_switching_margin_validation_1800",
        title="Независимая проверка относительного switching margin 0,20, 1800 с",
        description=(
            "Independent paired validation on unused seeds 9101–9130. Compares one preselected "
            "relative-margin candidate (absolute 1, relative 0.20) against locked Improved "
            "(absolute 1, relative 0.10) and Vehicle-actuated across all seven scenarios."
        ),
    )
    margin_validation["simulation"]["seeds"] = SWITCHING_MARGIN_VALIDATION_SEEDS
    margin_validation["controllers"] = [
        {"type": "vehicle_actuated", "min_green_seconds": 8, "max_green_seconds": 45},
        {
            "type": "queue_based_improved",
            "min_green_seconds": 8,
            "max_green_seconds": 45,
            "switching_margin": 1,
            "relative_switching_margin": 0.10,
            "congested_min_green_seconds": 25,
            "congestion_queue_threshold": 14,
            "result_name": "improved_abs1_rel010",
        },
        {
            "type": "queue_based_improved",
            "min_green_seconds": 8,
            "max_green_seconds": 45,
            "switching_margin": 1,
            "relative_switching_margin": 0.20,
            "congested_min_green_seconds": 25,
            "congestion_queue_threshold": 14,
            "result_name": "margin_abs1_rel020",
        },
    ]
    margin_validation["output"] = {
        "path": "outputs/total_improvement/switching_margin_validation_1800.json",
        "summary_csv": "outputs/total_improvement/switching_margin_validation_1800_summary.csv",
        "report_markdown": "outputs/total_improvement/switching_margin_validation_1800_report.md",
    }
    margin_validation_target = ROOT / "configs/total_improvement_switching_margin_validation_1800.yaml"
    margin_validation_target.write_text(
        yaml.safe_dump(margin_validation, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
