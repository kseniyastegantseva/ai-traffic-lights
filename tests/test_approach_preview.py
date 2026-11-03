from __future__ import annotations

from copy import deepcopy

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
    BaseController,
    ControllerState,
    QueueBasedApproachPreviewController,
    VehicleActuatedController,
)
from traffic_light.experiments import build_controller, run_experiment
from traffic_light.simulation import Arrival, run_simulation


def _intersection(rate: float = 6.0) -> IntersectionConfig:
    return IntersectionConfig(
        lanes={lane: TrafficDemandConfig(arrival_rate_per_minute=rate)
               for lane in ("north", "south", "east", "west")},
        min_green_seconds=8,
        yellow_seconds=3,
    )


class _Recorder(BaseController):
    name = "recorder"

    def __init__(self) -> None:
        self.states: list[ControllerState] = []

    def choose_phase(self, state: ControllerState):
        self.states.append(deepcopy(state))
        return state.current_phase


def _state(queues: dict[str, int], upcoming=None, now: float = 10.0, started: float = 0.0):
    full = {"north": 0, "south": 0, "east": 0, "west": 0, **queues}
    return ControllerState(
        now=now,
        current_phase="north_south",
        phase_started_at=started,
        queues=full,
        yellow_seconds=3,
        upcoming_arrival_offsets=upcoming,
    )


_EMPTY_PREVIEW = {"north": [], "south": [], "east": [], "west": []}


def test_sensor_reports_future_arrivals_inside_window_only():
    recorder = _Recorder()
    arrivals = [Arrival(5.5, "north"), Arrival(12.0, "east")]
    config = SimulationConfig(duration_seconds=20, preview_seconds=10.0)
    run_simulation(_intersection(), config, recorder, arrivals=arrivals)

    by_time = {int(state.now): state for state in recorder.states}
    assert by_time[0].upcoming_arrival_offsets["north"] == [5.5]
    assert by_time[0].upcoming_arrival_offsets["east"] == []
    assert by_time[4].upcoming_arrival_offsets["north"] == [1.5]
    assert by_time[4].upcoming_arrival_offsets["east"] == [8.0]
    # Приехавшая машина уже стоит в очереди и больше не «подъезжает».
    assert by_time[6].upcoming_arrival_offsets["north"] == []
    assert by_time[6].queues["north"] + by_time[6].in_service_by_lane["north"] == 1


def test_sensor_is_absent_by_default_and_does_not_change_other_controllers():
    recorder = _Recorder()
    run_simulation(_intersection(), SimulationConfig(duration_seconds=5), recorder,
                   arrivals=[Arrival(2.0, "north")])
    assert all(state.upcoming_arrival_offsets is None for state in recorder.states)

    arrivals = [Arrival(float(t), lane) for t in range(1, 120, 3) for lane in ("north", "east")]
    plain = run_simulation(
        _intersection(), SimulationConfig(duration_seconds=120), VehicleActuatedController(),
        arrivals=arrivals,
    )
    with_sensor = run_simulation(
        _intersection(), SimulationConfig(duration_seconds=120, preview_seconds=10.0),
        VehicleActuatedController(), arrivals=arrivals,
    )
    assert plain.phase_history == with_sensor.phase_history
    assert plain.average_wait_seconds == with_sensor.average_wait_seconds
    assert plain.arrival_stream_sha256 == with_sensor.arrival_stream_sha256


def test_sensor_detection_probability_and_time_jitter_are_seeded():
    arrivals = [Arrival(float(t) + 0.5, "north") for t in range(2, 40, 4)]

    def offsets(**kwargs):
        recorder = _Recorder()
        config = SimulationConfig(duration_seconds=40, seed=7, preview_seconds=20.0, **kwargs)
        run_simulation(_intersection(), config, recorder, arrivals=arrivals)
        return recorder.states[0].upcoming_arrival_offsets["north"]

    assert offsets(preview_detection_probability=0.0) == []
    assert len(offsets()) == len([a for a in arrivals if a.at < 20])
    noisy = offsets(preview_time_jitter_seconds=1.5)
    assert noisy == offsets(preview_time_jitter_seconds=1.5)
    assert noisy != offsets()
    partial = offsets(preview_detection_probability=0.5)
    assert 0 < len(partial) < len(offsets())


def test_preview_controller_holds_green_for_imminent_arrival_but_not_without_sensor():
    controller = QueueBasedApproachPreviewController()
    imminent = {**_EMPTY_PREVIEW, "north": [1.0]}
    assert controller.choose_phase(_state({"east": 1}, imminent)) == "north_south"
    assert controller.choose_phase(_state({"east": 1}, None)) == "east_west"
    assert controller.choose_phase(_state({"east": 1}, _EMPTY_PREVIEW)) == "east_west"


def test_preview_controller_prepares_for_competing_arrival_and_ignores_idle_intersection():
    controller = QueueBasedApproachPreviewController()
    assert controller.choose_phase(_state({}, _EMPTY_PREVIEW)) == "north_south"
    expected_east = {**_EMPTY_PREVIEW, "east": [2.0]}
    assert controller.choose_phase(_state({}, expected_east)) == "east_west"


def test_preview_controller_respects_minimum_and_maximum_green():
    controller = QueueBasedApproachPreviewController(min_green_seconds=4, max_green_seconds=45)
    assert controller.choose_phase(_state({"east": 6}, None, now=3.0)) == "north_south"
    # Длинная очередь на текущей оси удерживает зелёный, пока не достигнут максимум.
    assert controller.choose_phase(_state({"north": 8, "east": 1}, None, now=20.0)) == "north_south"
    assert controller.choose_phase(_state({"north": 8, "east": 1}, None, now=50.0)) == "east_west"


def test_experiment_factory_wires_gap_name_and_preview_controller():
    default = build_controller(ControllerConfig(type="vehicle_actuated"), 8)
    assert (default.gap_seconds, default.name, default.min_green_seconds) == (3.0, "vehicle_actuated", 8)
    tuned = build_controller(
        ControllerConfig(type="vehicle_actuated", min_green_seconds=4, gap_seconds=1.0,
                         result_name="va_min4_gap1"), 8)
    assert (tuned.gap_seconds, tuned.name, tuned.min_green_seconds) == (1.0, "va_min4_gap1", 4)

    preview = build_controller(
        ControllerConfig(type="queue_based_approach_preview", planning_horizon_seconds=40,
                         max_switch_delay_seconds=12, result_name="preview_ideal10"), 8)
    assert isinstance(preview, QueueBasedApproachPreviewController)
    assert (preview.name, preview.planning_horizon_seconds, preview.max_switch_delay_seconds) == (
        "preview_ideal10", 40, 12)
    # Минимальный зелёный берётся из конфигурации контроллера (по умолчанию 8 с).
    assert preview.min_green_seconds == ControllerConfig(
        type="queue_based_approach_preview").min_green_seconds == 8


def test_preview_experiment_is_paired_conserves_vehicles_and_beats_blind_rollout_at_low_load():
    experiment = ExperimentConfig(
        name="preview_smoke",
        simulation=ExperimentSimulationConfig(
            duration_seconds=600, seeds=[1, 2, 3], preview_seconds=10.0, store_queue_series=False,
        ),
        scenarios=[ScenarioConfig(name="symmetric", title="symmetric", intersection=_intersection(6.0))],
        controllers=[
            ControllerConfig(type="vehicle_actuated", min_green_seconds=4, gap_seconds=1.0,
                             result_name="va_tuned"),
            ControllerConfig(type="queue_based_approach_preview", min_green_seconds=4,
                             result_name="preview"),
        ],
    )
    rows, summary = run_experiment(experiment)

    assert len(rows) == 6
    for seed in (1, 2, 3):
        pair = [row for row in rows if row["seed"] == seed]
        assert len({row["arrival_stream_sha256"] for row in pair}) == 1
    for row in rows:
        assert row["vehicles_arrived"] + row["initial_vehicles"] == (
            row["vehicles_departed"] + row["waiting_at_end"] + row["in_service_at_end"]
        )
    waits = summary.set_index("controller")["average_wait_seconds"]
    assert waits["preview"] < waits["va_tuned"]
