from __future__ import annotations

from pathlib import Path

import pytest

from traffic_light.config import (
    ControllerConfig,
    ExperimentConfig,
    ExperimentSimulationConfig,
    IntersectionConfig,
    ScenarioConfig,
    SimulationConfig,
    TrafficDemandConfig,
)
from traffic_light.controllers import (
    ControllerState,
    FixedTimeController,
    QueueBasedController,
    QueueBasedEmptyGapFixController,
    QueueBasedHysteresisController,
    QueueBasedImprovedController,
    QueueBasedMaxRedController,
    QueueBasedPersistentCongestionController,
    QueueBasedSmoothMinGreenController,
)
from traffic_light.experiments import build_controller, build_paired_statistics, run_experiment
from traffic_light.queue_audit import (
    arrival_digest,
    max_red_with_queued_vehicles_by_phase,
    max_signal_red_by_phase,
    regenerate_arrivals,
    replay_run,
)
from traffic_light.simulation import run_simulation
from traffic_light.statistics_audit import (
    _resolve_configured_path,
    exact_sign_p,
    holm_adjust,
    paired_summary,
)

LANES = ("north", "south", "east", "west")


def zero_demand_intersection(yellow_seconds: int = 3) -> IntersectionConfig:
    return IntersectionConfig(
        lanes={lane: TrafficDemandConfig(arrival_rate_per_minute=0) for lane in LANES},
        min_green_seconds=8,
        yellow_seconds=yellow_seconds,
    )


def test_fixed_8_controller_uses_eight_green_and_three_yellow_seconds():
    controller = build_controller(ControllerConfig(type="fixed_8"), 8, zero_demand_intersection())
    result = run_simulation(
        zero_demand_intersection(),
        SimulationConfig(duration_seconds=25, seed=3),
        controller,
        initial_queues={"north": 2, "south": 0, "east": 2, "west": 0},
        arrivals=[],
    )

    assert result.phase_history[:5] == [
        {"at": 0.0, "phase": "north_south", "color": "green"},
        {"at": 8, "phase": "north_south", "color": "yellow"},
        {"at": 11, "phase": "east_west", "color": "green"},
        {"at": 19, "phase": "east_west", "color": "yellow"},
        {"at": 22, "phase": "north_south", "color": "green"},
    ]
    assert result.initial_vehicles == result.vehicles_departed + result.waiting_at_end + result.in_service_at_end


def test_fixed_8_does_not_serve_conflicting_axis_during_yellow():
    trace = []
    result = run_simulation(
        zero_demand_intersection(),
        SimulationConfig(duration_seconds=16, seed=2, service_time_seconds=2),
        FixedTimeController(phase_duration_seconds=8, name="fixed_8"),
        initial_queues={"north": 20, "east": 20},
        arrivals=[],
        trace_callback=trace.append,
    )

    east_departures = [frame["departed_by_lane"]["east"] for frame in trace]
    assert max(east_departures[:11]) == 0
    assert east_departures[13] == 1
    east_service = [frame["in_service_by_lane"]["east"] for frame in trace]
    assert not any(east_service[8:11])
    assert any(east_service[11:13])
    assert result.initial_vehicles == result.vehicles_departed + result.waiting_at_end + result.in_service_at_end


def test_original_queue_rule_is_unchanged_and_improved_rule_has_its_own_hysteresis():
    state = ControllerState(
        now=8,
        current_phase="north_south",
        phase_started_at=0,
        queues={"north": 0, "south": 0, "east": 2, "west": 0},
    )
    original = QueueBasedController(min_green_seconds=8, max_green_seconds=45, switching_margin=1)
    improved = QueueBasedImprovedController(
        min_green_seconds=20,
        max_green_seconds=45,
        switching_margin=1,
        relative_switching_margin=0.10,
    )

    assert original.choose_phase(state) == "east_west"
    assert improved.choose_phase(state) == "north_south"
    state.now = 20
    state.queues.update(north=100, east=125)
    assert improved.choose_phase(state) == "east_west"
    state.now = 45
    state.queues.update(north=1000, east=1)
    assert improved.choose_phase(state) == "east_west"


def test_improved_controller_respects_max_green_when_competing_demand_exists():
    controller = QueueBasedImprovedController(min_green_seconds=20, max_green_seconds=45)
    state = ControllerState(
        now=45,
        current_phase="north_south",
        phase_started_at=0,
        queues={"north": 40, "south": 30, "east": 1, "west": 0},
    )
    assert controller.choose_phase(state) == "east_west"
    state.queues.update(east=0, west=0)
    assert controller.choose_phase(state) == "north_south"


def test_empty_gap_fix_switches_from_empty_axis_after_minimum_green():
    state = ControllerState(
        now=8,
        current_phase="north_south",
        phase_started_at=0,
        queues={"north": 0, "south": 0, "east": 1, "west": 0},
        current_gap_seconds=8,
    )
    improved = QueueBasedImprovedController(
        min_green_seconds=8,
        max_green_seconds=45,
        switching_margin=1,
        relative_switching_margin=0.10,
        congested_min_green_seconds=25,
        congestion_queue_threshold=14,
    )
    empty_gap_fix = QueueBasedEmptyGapFixController(
        min_green_seconds=8,
        max_green_seconds=45,
        switching_margin=1,
        relative_switching_margin=0.10,
        congested_min_green_seconds=25,
        congestion_queue_threshold=14,
        empty_gap_seconds=1,
    )

    assert improved.choose_phase(state) == "north_south"
    assert empty_gap_fix.choose_phase(state) == "east_west"
    state.now = 7
    assert empty_gap_fix.choose_phase(state) == "north_south"


def test_empty_gap_fix_requires_configured_short_gap_and_keeps_queue_pressure_rule():
    state = ControllerState(
        now=8,
        current_phase="north_south",
        phase_started_at=0,
        queues={"north": 0, "south": 0, "east": 1, "west": 0},
        current_gap_seconds=1,
    )
    controller = QueueBasedEmptyGapFixController(empty_gap_seconds=3)
    assert controller.choose_phase(state) == "north_south"
    state.current_gap_seconds = 3
    assert controller.choose_phase(state) == "east_west"

    state.queues.update(north=1, east=1)
    state.current_gap_seconds = 10
    assert controller.choose_phase(state) == "north_south"


def test_empty_gap_fix_factory_name_and_yellow_clearance_are_preserved():
    controller = build_controller(
        ControllerConfig(
            type="queue_based_empty_gap_fix",
            min_green_seconds=8,
            max_green_seconds=45,
            congested_min_green_seconds=25,
            congestion_queue_threshold=14,
            empty_gap_seconds=1,
            result_name="empty_gap_1s",
        ),
        min_green_seconds=8,
        intersection=zero_demand_intersection(),
    )
    result = run_simulation(
        zero_demand_intersection(),
        SimulationConfig(duration_seconds=16, seed=1),
        controller,
        initial_queues={"east": 1},
        arrivals=[],
    )

    assert isinstance(controller, QueueBasedEmptyGapFixController)
    assert result.phase_history[:3] == [
        {"at": 0.0, "phase": "north_south", "color": "green"},
        {"at": 8, "phase": "north_south", "color": "yellow"},
        {"at": 11, "phase": "east_west", "color": "green"},
    ]


def test_improved_config_rejects_congested_minimum_above_max_green():
    with pytest.raises(ValueError):
        ControllerConfig(
            type="queue_based_improved",
            min_green_seconds=8,
            congested_min_green_seconds=46,
            max_green_seconds=45,
        )


def test_experiment_factory_passes_adaptive_parameters_to_improved_controller():
    controller = build_controller(
        ControllerConfig(
            type="queue_based_improved",
            min_green_seconds=8,
            max_green_seconds=45,
            congested_min_green_seconds=15,
            congestion_queue_threshold=6,
            relative_switching_margin=0.1,
        ),
        min_green_seconds=8,
    )

    assert isinstance(controller, QueueBasedImprovedController)
    assert controller.congested_min_green_seconds == 15
    assert controller.congestion_queue_threshold == 6


def test_improved_controller_uses_base_minimum_at_low_demand_and_longer_hold_at_congestion():
    controller = QueueBasedImprovedController(
        min_green_seconds=8,
        max_green_seconds=45,
        switching_margin=1,
        relative_switching_margin=0.0,
        congested_min_green_seconds=25,
        congestion_queue_threshold=10,
    )
    state = ControllerState(
        now=8,
        current_phase="north_south",
        phase_started_at=0,
        queues={"north": 0, "south": 0, "east": 2, "west": 0},
    )
    assert controller.choose_phase(state) == "east_west"
    state.queues.update(north=8, east=12)
    assert controller.choose_phase(state) == "north_south"
    state.now = 24
    assert controller.choose_phase(state) == "north_south"
    state.now = 25
    assert controller.choose_phase(state) == "east_west"


def test_smooth_min_green_ramps_across_queue_band_without_early_threshold_jump():
    improved = QueueBasedImprovedController(
        min_green_seconds=8,
        max_green_seconds=45,
        switching_margin=1,
        relative_switching_margin=0.10,
        congested_min_green_seconds=25,
        congestion_queue_threshold=14,
    )
    smooth = QueueBasedSmoothMinGreenController(
        min_green_seconds=8,
        max_green_seconds=45,
        switching_margin=1,
        relative_switching_margin=0.10,
        congested_min_green_seconds=25,
        congestion_queue_threshold=14,
        smooth_congestion_start_queue=10,
        smooth_congestion_end_queue=18,
    )
    state = ControllerState(
        now=9,
        current_phase="north_south",
        phase_started_at=0,
        queues={"north": 0, "south": 0, "east": 11, "west": 0},
    )

    assert improved.choose_phase(state) == "east_west"
    assert smooth.choose_phase(state) == "north_south"


def test_congestion_hysteresis_stays_active_until_exit_threshold():
    controller = QueueBasedHysteresisController(
        min_green_seconds=8,
        max_green_seconds=45,
        congested_min_green_seconds=25,
        congestion_queue_threshold=14,
        congestion_exit_threshold=10,
    )
    state = ControllerState(
        now=9,
        current_phase="north_south",
        phase_started_at=0,
        queues={"north": 0, "south": 0, "east": 14, "west": 0},
    )
    assert controller.choose_phase(state) == "north_south"

    state.now = 10
    state.queues["east"] = 12
    assert controller.choose_phase(state) == "north_south"
    state.now = 11
    state.queues["east"] = 10
    assert controller.choose_phase(state) == "east_west"


def test_persistent_congestion_uses_consecutive_observation_duration():
    persistent_5 = QueueBasedPersistentCongestionController(
        min_green_seconds=8,
        max_green_seconds=45,
        congested_min_green_seconds=25,
        congestion_queue_threshold=14,
        congestion_persistence_seconds=5,
    )
    persistent_10 = QueueBasedPersistentCongestionController(
        min_green_seconds=8,
        max_green_seconds=45,
        congested_min_green_seconds=25,
        congestion_queue_threshold=14,
        congestion_persistence_seconds=10,
    )
    state = ControllerState(
        now=0,
        current_phase="north_south",
        phase_started_at=0,
        queues={"north": 0, "south": 0, "east": 14, "west": 0},
    )
    assert persistent_5.choose_phase(state) == "north_south"
    assert persistent_10.choose_phase(state) == "north_south"
    state.now = 8
    assert persistent_5.choose_phase(state) == "north_south"
    assert persistent_10.choose_phase(state) == "east_west"


def test_independent_replay_recovers_known_censored_queue_metrics():
    configuration = {
        "simulation": {"duration_seconds": 10, "service_time_seconds": 2.0}
    }
    scenario = {
        "intersection": {
            "lanes": {lane: {"arrival_rate_per_minute": 0} for lane in LANES}
        },
        "initial_queues": {"north": 4, "east": 1},
    }
    arrivals = regenerate_arrivals(configuration, scenario, seed=7)
    row = {
        "duration_seconds": 10,
        "seed": 7,
        "arrival_stream_sha256": arrival_digest(arrivals),
        "phase_history": [
            {"at": 0.0, "phase": "north_south", "color": "green"},
            {"at": 5.0, "phase": "north_south", "color": "yellow"},
            {"at": 8.0, "phase": "east_west", "color": "green"},
        ],
    }

    replay = replay_run(row, scenario, configuration)

    assert replay["arrivals"] == 0
    assert replay["departures"] == 3
    assert replay["residual_queue"] == 1
    assert replay["vehicles_in_service_at_end"] == 1
    assert replay["average_wait_seconds"] == 2
    assert replay["queue_delay_area_vehicle_seconds"] == 24
    assert replay["mean_accrued_wait_per_vehicle_seconds"] == 4.8
    assert replay["average_queue_length"] == 2.4
    assert replay["max_queue_length"] == 5
    assert replay["yellow_seconds"] == 3
    assert replay["green_seconds"] == 7
    assert replay["phase_switches"] == 1
    assert replay["green_active_lane_seconds"] == 7
    assert replay["green_available_lane_seconds"] == 14
    assert replay["green_idle_lane_seconds"] == 7
    assert replay["green_utilization"] == 0.5
    assert replay["green_idle_fraction"] == 0.5


def test_final_experiment_pairs_fixed_and_adaptive_controllers_and_can_omit_full_trace():
    scenario = ScenarioConfig(
        name="paired",
        title="Paired",
        intersection=zero_demand_intersection(),
        initial_queues={"north": 2, "east": 1},
    )
    config = ExperimentConfig(
        simulation=ExperimentSimulationConfig(
            duration_seconds=30, seeds=[41, 42], store_queue_series=False
        ),
        scenarios=[scenario],
        controllers=[
            ControllerConfig(type="fixed_8"),
            ControllerConfig(type="queue_based"),
            ControllerConfig(type="queue_based_improved", min_green_seconds=20),
        ],
    )

    rows, _ = run_experiment(config)
    hashes_by_seed = {}
    for row in rows:
        hashes_by_seed.setdefault(row["seed"], set()).add(row["arrival_stream_sha256"])
        assert row["queue_series"] == []
    assert all(len(hashes) == 1 for hashes in hashes_by_seed.values())


def test_paired_sign_test_excludes_ties_from_directional_denominator():
    rows = []
    for seed, wait in ((1, 9.0), (2, 10.0), (3, 11.0)):
        rows.extend(
            [
                {"scenario": "s", "duration_seconds": 1800, "seed": seed,
                 "controller": "queue_based", "average_wait_seconds": 10.0},
                {"scenario": "s", "duration_seconds": 1800, "seed": seed,
                 "controller": "fixed_8", "average_wait_seconds": wait},
            ]
        )
    result = build_paired_statistics(rows)[0]
    assert result["pairs"] == 3
    assert result["sign_test_p"] == 1.0


def test_independent_paired_statistics_match_hand_calculated_example():
    result = paired_summary([-1.0, 0.0, 1.0])
    assert result["n"] == 3
    assert result["mean"] == 0.0
    assert result["sd"] == 1.0
    assert result["sign_p"] == 1.0
    assert exact_sign_p([-1.0, -1.0, -1.0, 0.0]) == 0.25
    assert holm_adjust([0.01, 0.04, 0.03]) == [0.03, 0.06, 0.06]


def test_statistics_audit_resolves_nested_output_paths_from_repository_root(tmp_path, monkeypatch):
    result_path = tmp_path / "outputs" / "total_improvement" / "runs.json"
    configured = Path("outputs/total_improvement/summary.csv")
    (tmp_path / configured).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / configured).write_text("scenario,controller\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert _resolve_configured_path(result_path, str(configured)) == configured


def test_capacity_boundary_max_red_is_derived_from_phase_history():
    history = [
        {"at": 0.0, "phase": "north_south", "color": "green"},
        {"at": 8.0, "phase": "north_south", "color": "yellow"},
        {"at": 11.0, "phase": "east_west", "color": "green"},
        {"at": 19.0, "phase": "east_west", "color": "yellow"},
        {"at": 22.0, "phase": "north_south", "color": "green"},
    ]

    assert max_signal_red_by_phase(history, 25) == {
        "north_south": 11.0,
        "east_west": 11.0,
    }


def test_capacity_boundary_max_red_ends_at_green_when_there_is_no_yellow():
    history = [
        {"at": 0.0, "phase": "north_south", "color": "green"},
        {"at": 8.0, "phase": "east_west", "color": "green"},
        {"at": 16.0, "phase": "north_south", "color": "green"},
    ]

    assert max_signal_red_by_phase(history, 20) == {
        "north_south": 8.0,
        "east_west": 8.0,
    }


def test_independent_red_with_queue_replay_uses_first_arrival_during_red():
    history = [
        {"at": 0.0, "phase": "north_south", "color": "green"},
        {"at": 8.0, "phase": "north_south", "color": "yellow"},
        {"at": 11.0, "phase": "east_west", "color": "green"},
        {"at": 19.0, "phase": "east_west", "color": "yellow"},
        {"at": 22.0, "phase": "north_south", "color": "green"},
    ]
    arrivals = {"north": [15.0], "south": [], "east": [4.0], "west": []}
    service_starts = {lane: [] for lane in LANES}

    assert max_red_with_queued_vehicles_by_phase(history, 25, arrivals, service_starts) == {
        "north_south": 7.0,
        "east_west": 7.0,
    }


def test_max_red_controller_forces_competing_phase_after_minimum_green():
    controller = QueueBasedMaxRedController(
        min_green_seconds=8,
        max_green_seconds=45,
        switching_margin=1,
        relative_switching_margin=0.1,
        congested_min_green_seconds=25,
        congestion_queue_threshold=14,
        max_red_seconds=48,
    )
    state = ControllerState(
        now=20,
        current_phase="north_south",
        phase_started_at=0,
        queues={"north": 20, "south": 0, "east": 1, "west": 0},
        red_request_elapsed_seconds={"east_west": 48},
        yellow_seconds=3,
    )
    assert controller.choose_phase(state) == "north_south"

    state.now = 25
    assert controller.choose_phase(state) == "east_west"
    state.red_request_elapsed_seconds = {}
    state.queues.update(east=0)
    assert controller.choose_phase(state) == "north_south"


def test_max_red_controller_and_factory_preserve_minimum_and_yellow_clearance():
    controller = build_controller(
        ControllerConfig(
            type="queue_based_max_red",
            min_green_seconds=8,
            max_green_seconds=45,
            congested_min_green_seconds=8,
            congestion_queue_threshold=1000,
            switching_margin=1000,
            max_red_seconds=13,
        ),
        min_green_seconds=8,
        intersection=zero_demand_intersection(),
    )
    result = run_simulation(
        zero_demand_intersection(),
        SimulationConfig(duration_seconds=27, seed=1),
        controller,
        initial_queues={"north": 100, "east": 20},
        arrivals=[],
    )

    assert isinstance(controller, QueueBasedMaxRedController)
    assert result.phase_history[:5] == [
        {"at": 0.0, "phase": "north_south", "color": "green"},
        {"at": 9, "phase": "north_south", "color": "yellow"},
        {"at": 12, "phase": "east_west", "color": "green"},
        {"at": 21, "phase": "east_west", "color": "yellow"},
        {"at": 24, "phase": "north_south", "color": "green"},
    ]
    assert result.max_red_with_queue_seconds_by_phase == {
        "north_south": 12.0,
        "east_west": 12.0,
    }
