"""Тесты второй версии Approach Preview: причинный датчик, равные условия, аудит rollout."""
from __future__ import annotations

import inspect
import itertools
import random
import time
from copy import deepcopy

import pytest

from traffic_light import sensor as sensor_module
from traffic_light.config import (
    ControllerConfig,
    IntersectionConfig,
    SimulationConfig,
    TrafficDemandConfig,
)
from traffic_light.controllers import (
    PHASE_LANES,
    BaseController,
    ControllerState,
    DetectorVehicleActuatedController,
    QueueBasedApproachPreviewController,
)
from traffic_light.experiments import build_controller
from traffic_light.rollout_audit import (
    area_discrepancy,
    exhaustive_regret,
    fractional_arrival_error,
    integer_grid_cases,
)
from traffic_light.sensor import (
    CausalSensorFeed,
    HiddenApproachTrack,
    SensorParams,
    build_feed,
    estimate_eta,
)
from traffic_light.simulation import Arrival, generate_arrivals, run_simulation

LANES = ("north", "south", "east", "west")


def _intersection(rate: float = 6.0, yellow: int = 3, min_green: int = 6) -> IntersectionConfig:
    return IntersectionConfig(
        lanes={lane: TrafficDemandConfig(arrival_rate_per_minute=rate) for lane in LANES},
        min_green_seconds=min_green,
        yellow_seconds=yellow,
    )


def _ideal(**overrides) -> SimulationConfig:
    """Идеальный датчик: постоянная скорость, нулевые шумы и задержка."""
    values = {
        "duration_seconds": 120,
        "preview_seconds": 40.0,
        "sensor_model": "causal",
        "sensor_speed_cv": 0.0,
        "sensor_profile_sd": 0.0,
        "sensor_position_noise_m": 0.0,
        "sensor_speed_noise_mps": 0.0,
        "sensor_latency_seconds": 0.0,
        "sensor_frame_period_seconds": 0.5,
    }
    values.update(overrides)
    return SimulationConfig(**values)


def _feed(arrivals, config: SimulationConfig) -> CausalSensorFeed:
    return build_feed(arrivals, SensorParams.from_config(config), float(config.duration_seconds))


class _Recorder(BaseController):
    name = "recorder"

    def __init__(self) -> None:
        self.states: list[ControllerState] = []

    def choose_phase(self, state: ControllerState):
        self.states.append(deepcopy(state))
        return state.current_phase


def _load_script(name: str):
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- P01/P02/P12: причинность


def test_identical_observations_different_hidden_future():
    config = _ideal(sensor_speed_cv=0.2, sensor_profile_sd=0.3, sensor_position_noise_m=1.0,
                    sensor_speed_noise_mps=0.5, sensor_latency_seconds=0.3)
    common = [Arrival(float(t), lane) for t in range(12, 60, 7) for lane in ("north", "east")]
    # Машины появляются на подходе не раньше at-33 с (минимальная скорость 3 м/с на 100 м).
    world_a = common + [Arrival(100.0, "south")]
    world_b = common + [Arrival(105.0, "west"), Arrival(140.0, "north")]
    config = config.model_copy(update={"duration_seconds": 200})
    feed_a, feed_b = _feed(world_a, config), _feed(world_b, config)
    for step in range(66 * 2):
        now = step * 0.5
        assert feed_a.view(now) == feed_b.view(now), now


@pytest.mark.parametrize("seed", range(6))
def test_non_anticipativity_many_worlds_and_horizons(seed):
    rng = random.Random(seed)
    config = SimulationConfig(
        duration_seconds=300,
        seed=seed,
        preview_seconds=12.0,
        sensor_model="causal",
        preview_detection_probability=0.85,
        sensor_dropout_start_probability=0.1,
        sensor_false_positive_rate_per_minute=2.0,
        sensor_duplicate_track_probability=0.2,
    )
    prefix = [Arrival(rng.uniform(1, 100), rng.choice(LANES)) for _ in range(25)]
    cutoff = 100.0
    horizon = cutoff + 40.0  # дальше ни одна машина не успевает попасть в зону к моменту cutoff
    futures = [
        [Arrival(rng.uniform(horizon, 290), rng.choice(LANES)) for _ in range(rng.randint(0, 30))]
        for _ in range(2)
    ]
    feeds = [_feed(prefix + future, config) for future in futures]
    for step in range(int(cutoff)):
        assert feeds[0].view(float(step)) == feeds[1].view(float(step))


def test_controller_actions_equal_until_observations_differ():
    config = SimulationConfig(
        duration_seconds=240, seed=3, preview_seconds=12.0, sensor_model="causal"
    )
    early = [Arrival(float(t), lane) for t in range(5, 50, 4) for lane in ("north", "east")]
    futures = [[Arrival(150.0, "south")], [Arrival(170.0, "west"), Arrival(190.0, "east")]]
    histories = []
    for future in futures:
        result = run_simulation(
            _intersection(), config, QueueBasedApproachPreviewController(min_green_seconds=4),
            arrivals=early + future,
        )
        histories.append([item for item in result.phase_history if item["at"] < 110])
    assert histories[0] == histories[1]


def test_no_ground_truth_eta_access():
    source = inspect.getsource(CausalSensorFeed)
    for forbidden in ("crossing_at", "entry_at", "Arrival", "HiddenApproachTrack", "actual_at"):
        assert forbidden not in source, forbidden
    feed = _feed([Arrival(30.0, "north")], _ideal())
    stored = list(vars(feed).values())
    flat = []
    for value in stored:
        flat.extend(value if isinstance(value, list) else [value])
    assert not any(isinstance(item, (Arrival, HiddenApproachTrack)) for item in flat)
    # В тексте функции подачи данных контроллеру нет обращений к списку прибытий.
    simulation_source = inspect.getsource(sensor_module)
    assert "self.arrivals" not in simulation_source


def test_preview_window_boundary_and_eta_independent_of_visibility():
    # Скорость 10 м/с, зона 100 м: машина прибывает в 25,0 и входит в зону в 15,0.
    for bias in (-4.0, 0.0, 4.0):
        config = _ideal(sensor_eta_bias_seconds=bias)
        feed = _feed([Arrival(25.0, "north")], config)
        assert feed.view(14.9).offsets["north"] == []
        seen = feed.view(15.0).offsets["north"]
        assert len(seen) == 1
        assert seen[0] == pytest.approx(max(0.0, 10.0 + bias), abs=1e-6) or bias < 0


def test_eta_negative_positive_and_stale():
    arrival = [Arrival(25.0, "north")]
    early = _feed(arrival, _ideal(sensor_eta_bias_seconds=-6.0))
    # Предсказание «уже пора», но машина физически не пересекла линию: ETA зажат нулём, трек жив.
    assert early.view(22.0).offsets["north"] == [0.0]
    assert early.view(24.9).offsets["north"] == [0.0]
    assert early.view(25.0).offsets["north"] == []  # закрыт событием стоп-линии
    late = _feed(arrival, _ideal(sensor_eta_bias_seconds=6.0))
    assert late.view(24.5).offsets["north"][0] == pytest.approx(6.5, abs=0.6)
    assert late.view(25.0).offsets["north"] == []  # реальное прибытие закрывает трек раньше ETA
    # Пропажа измерений: трек устаревает через track_timeout после последнего сообщения.
    stale = _feed(arrival, _ideal(sensor_outage_windows=[(18.0, 40.0)], sensor_track_timeout_seconds=1.0,
                                  sensor_watchdog_seconds=5.0))
    assert stale.view(18.0).offsets["north"] != []
    assert stale.view(19.0).offsets["north"] == []  # ETA не живёт дольше таймаута без измерений


def test_stopped_vehicle_and_queue_tail_do_not_create_fast_approach():
    assert estimate_eta(40.0, 0.0, 1.0) == pytest.approx(40.0)
    assert estimate_eta(30.0, 0.1, 1.0) == pytest.approx(30.0)
    speeds = [0.0, 0.5, 1.0, 2.0, 5.0, 10.0]
    etas = [estimate_eta(50.0, speed, 1.0) for speed in speeds]
    assert etas == sorted(etas, reverse=True)
    assert min(etas) == pytest.approx(5.0)


def test_duplicate_false_positive_and_missed_tracks_are_bounded():
    arrival = [Arrival(30.0, "north")]
    duplicated = _feed(arrival, _ideal(sensor_duplicate_track_probability=1.0, sensor_track_timeout_seconds=2.0))
    assert max(len(duplicated.view(t / 2).offsets["north"]) for t in range(20, 60)) <= 2
    # Фантом-дубликат не живёт дольше таймаута после прибытия машины.
    assert duplicated.view(30.0 + 2.6).offsets["north"] == []
    missed = _feed(arrival, _ideal(preview_detection_probability=0.0))
    assert all(missed.view(t / 2).offsets["north"] == [] for t in range(60))
    ghosts = _feed([], _ideal(sensor_false_positive_rate_per_minute=30.0, duration_seconds=120))
    seen = [len(ghosts.view(float(t)).offsets["north"]) for t in range(120)]
    assert max(seen) >= 1  # ложные объекты действительно появляются
    # Любой ложный объект исчезает не позже, чем через 4 с жизни + таймаут + кадр.
    assert all(count <= 10 for count in seen)


def test_ideal_causal_sensor_matches_oracle_eta_inside_window():
    arrivals = [Arrival(t + 0.5, "east") for t in (14, 22, 33)]
    causal = _feed(arrivals, _ideal(preview_seconds=10.0))
    for now in (10.0, 12.0, 20.0):
        offsets = causal.view(now).offsets["east"]
        truth = sorted(a.at - now for a in arrivals if 0 < a.at - now < 10.0)
        assert len(offsets) == len(truth)
        assert offsets == pytest.approx(truth, abs=0.51)


def test_sensor_outage_fallback_is_blind_and_safe():
    arrivals = [Arrival(float(t), lane) for t in range(3, 200, 5) for lane in LANES]
    config = SimulationConfig(
        duration_seconds=200, seed=1, preview_seconds=10.0, sensor_model="causal",
        sensor_outage_windows=[(50.0, 110.0)],
    )
    recorder = _Recorder()
    run_simulation(_intersection(), config, recorder, arrivals=arrivals)
    inside = [s for s in recorder.states if 55 <= s.now < 108]
    assert inside and all(s.upcoming_arrival_offsets is None and s.preview_status == "unavailable"
                          for s in inside)
    assert all(s.preview_status == "ok" for s in recorder.states if s.now < 48 or s.now > 113)
    result = run_simulation(
        _intersection(), config, QueueBasedApproachPreviewController(min_green_seconds=4),
        arrivals=arrivals,
    )
    assert result.sensor_unavailable_seconds >= 50
    assert result.vehicle_balance_error == 0
    assert max(result.max_red_with_queue_seconds_by_phase.values()) < 45 + 3 + 6


# ---------------------------------------------------------------- P03/P04: равные условия


def test_detector_va_uses_passage_gap_and_optional_preview():
    def state(queues, upcoming=None, gap=5.0, now=20.0, busy=None):
        return ControllerState(
            now=now, current_phase="north_south", phase_started_at=0.0,
            queues={**dict.fromkeys(LANES, 0), **queues}, detector_gap_seconds=gap,
            in_service_by_lane={**dict.fromkeys(LANES, 0), **(busy or {})},
            upcoming_arrival_offsets=upcoming,
        )

    plain = DetectorVehicleActuatedController(min_green_seconds=6, passage_gap_seconds=2.0)
    assert plain.choose_phase(state({"east": 1}, gap=2.0)) == "east_west"
    assert plain.choose_phase(state({"east": 1}, gap=1.0)) == "north_south"
    assert plain.choose_phase(state({"east": 1, "north": 1}, gap=9.0)) == "north_south"
    assert plain.choose_phase(state({"east": 1}, gap=9.0, busy={"south": 1})) == "north_south"
    assert plain.choose_phase(state({}, gap=9.0)) == "north_south"  # нет конкурирующего запроса
    assert plain.choose_phase(state({"east": 1}, gap=9.0, now=3.0)) == "north_south"  # min-green
    assert plain.choose_phase(state({"east": 1, "north": 4}, gap=0.0, now=45.0)) == "east_west"
    previewed = DetectorVehicleActuatedController(min_green_seconds=6, use_preview=True)
    soon = {**{lane: [] for lane in LANES}, "north": [2.0]}
    far = {**{lane: [] for lane in LANES}, "north": [9.0]}
    assert previewed.choose_phase(state({"east": 1}, soon, gap=9.0)) == "north_south"
    assert previewed.choose_phase(state({"east": 1}, far, gap=9.0)) == "east_west"
    # Датчик без устройства preview не должен менять решение A относительно B при пустом окне.
    empty = {lane: [] for lane in LANES}
    assert previewed.choose_phase(state({"east": 1}, empty, gap=9.0)) == plain.choose_phase(
        state({"east": 1}, None, gap=9.0)
    )
    call_ahead = {**{lane: [] for lane in LANES}, "east": [2.0]}
    assert previewed.choose_phase(state({}, call_ahead, gap=9.0)) == "east_west"


def test_same_rules_for_all_controllers_in_factorial_configs():
    creator = _load_script("create_approach_preview_v2_configs")
    experiments = creator.factorial_experiments("development", min_green=6)
    seen = set()
    for experiment in experiments:
        simulation = experiment["simulation"]
        seen.add(
            (
                simulation["duration_seconds"],
                simulation["service_time_seconds"],
                simulation["startup_lost_time_seconds"],
                tuple(simulation["seeds"]),
                tuple(s["intersection"]["yellow_seconds"] for s in experiment["scenarios"]),
                tuple(s["intersection"]["min_green_seconds"] for s in experiment["scenarios"]),
                frozenset((c["min_green_seconds"], c["max_green_seconds"]) for c in experiment["controllers"]),
            )
        )
    assert len(seen) == 1, seen


def test_experiment_factory_wires_new_controller_fields():
    detector = build_controller(
        ControllerConfig(type="detector_vehicle_actuated", min_green_seconds=4, passage_gap_seconds=1.0,
                         use_preview=True, result_name="dva"), 8)
    assert (detector.min_green_seconds, detector.passage_gap_seconds, detector.use_preview) == (4, 1.0, True)
    preview = build_controller(
        ControllerConfig(type="queue_based_approach_preview", future_arrivals="historical_rate",
                         eta_rounding="ceil", max_work_units=500), 8)
    assert (preview.future_arrivals, preview.eta_rounding, preview.max_work_units) == (
        "historical_rate", "ceil", 500)


# ---------------------------------------------------------------- P06/P08/P09/P10/P11: rollout


@pytest.mark.parametrize("case", integer_grid_cases(seeds=range(3)))
def test_rollout_matches_simpy_fixed_plan(case):
    result = area_discrepancy(case)
    assert result is not None
    predicted, actual = result
    assert predicted == pytest.approx(actual, abs=1e-9)


def test_rollout_fractional_arrival_error_is_small_and_reported():
    rows = {row["eta_rounding"]: row for row in fractional_arrival_error(range(6))}
    assert set(rows) == {"floor", "round", "ceil"}
    assert all(row["mean_abs_relative_error"] < 0.05 for row in rows.values())


def test_rollout_has_no_artificial_switch_loss_without_demand_or_with_zero_yellow():
    controller = QueueBasedApproachPreviewController(planning_horizon_seconds=20)
    empty = ControllerState(now=10.0, current_phase="north_south", phase_started_at=0.0,
                            queues=dict.fromkeys(LANES, 0), yellow_seconds=0)
    assert controller.rollout_trajectory(empty, 10.0, 0) == [0.0] * 20
    assert controller.choose_phase(empty) == "north_south"
    # Нулевой жёлтый: переключение сразу открывает конфликтующую фазу в том же такте.
    state = ControllerState(now=10.0, current_phase="north_south", phase_started_at=0.0,
                            queues={"north": 0, "south": 0, "east": 3, "west": 0}, yellow_seconds=0)
    assert controller.rollout_trajectory(state, 10.0, 0, before_service=False)[0] == 2.0


def test_rollout_uses_remaining_service_time_and_startup():
    controller = QueueBasedApproachPreviewController(planning_horizon_seconds=6)

    def state(remaining, startup=0.0):
        return ControllerState(
            now=10.0, current_phase="north_south", phase_started_at=0.0,
            queues={"north": 3, "south": 0, "east": 0, "west": 0}, yellow_seconds=3,
            in_service_by_lane={"north": 1, "south": 0, "east": 0, "west": 0},
            service_remaining_by_lane={"north": remaining, "south": 0.0, "east": 0.0, "west": 0.0},
            startup_lost_seconds=startup,
        )

    nearly_done = controller.rollout_trajectory(state(0.1), 10.0, None)
    just_started = controller.rollout_trajectory(state(1.9), 10.0, None)
    assert nearly_done[:3] == [3.0, 2.0, 2.0]
    assert just_started[:3] == [3.0, 3.0, 2.0]
    # Только что начавшийся зелёный не обслуживает очередь до окончания потери времени на старт.
    fresh = state(0.0, startup=2.0)
    fresh.phase_started_at = 9.0
    fresh.in_service_by_lane = dict.fromkeys(LANES, 0)
    assert controller.rollout_trajectory(fresh, 1.0, None)[:3] == [3.0, 2.0, 2.0]


def test_eta_rounding_boundaries():
    floor = QueueBasedApproachPreviewController(eta_rounding="floor")
    nearest = QueueBasedApproachPreviewController(eta_rounding="round")
    ceiling = QueueBasedApproachPreviewController(eta_rounding="ceil")
    assert [c._eta_slot(1.9) for c in (floor, nearest, ceiling)] == [1, 2, 2]
    assert [c._eta_slot(1.0) for c in (floor, nearest, ceiling)] == [1, 1, 1]
    assert [c._eta_slot(0.0) for c in (floor, nearest, ceiling)] == [0, 0, 0]
    assert [c._eta_slot(-0.7) for c in (floor, nearest, ceiling)] == [0, 0, 0]


def test_historical_rate_fills_future_beyond_sensor_window_only():
    base = {
        "now": 10.0, "current_phase": "north_south", "phase_started_at": 0.0,
        "queues": dict.fromkeys(LANES, 0), "yellow_seconds": 3, "preview_window_seconds": 10.0,
        "upcoming_arrival_offsets": {lane: [] for lane in LANES},
    }
    rates = {"north": 0.0, "south": 0.0, "east": 0.2, "west": 0.0}
    zero = QueueBasedApproachPreviewController(planning_horizon_seconds=30)
    historical = QueueBasedApproachPreviewController(planning_horizon_seconds=30, future_arrivals="historical_rate")
    state = ControllerState(**base, arrival_rate_per_second_by_lane=rates)
    z = zero.rollout_trajectory(state, 10.0, None)
    h = historical.rollout_trajectory(state, 10.0, None, explicit_switch_steps=())
    assert z == [0.0] * 30
    assert h[:10] == [0.0] * 10  # внутри окна датчика поток не придумывается
    assert h[-1] == pytest.approx(0.2 * 20)


def test_rollout_heuristic_is_near_optimal_inside_the_model():
    report = exhaustive_regret(range(80), horizon=16)
    assert report["non_optimal_share"] <= 0.05
    assert report["mean_regret_vehicle_seconds"] <= 0.5


def test_work_budget_fallback_is_deterministic_and_runtime_is_bounded():
    controller = QueueBasedApproachPreviewController(max_work_units=100)
    etas = {lane: [i * 0.17 for i in range(60)] for lane in LANES}
    state = ControllerState(now=30.0, current_phase="north_south", phase_started_at=0.0,
                            queues={"north": 0, "south": 0, "east": 5, "west": 2}, yellow_seconds=3,
                            upcoming_arrival_offsets=etas, preview_window_seconds=10.0)
    first = controller.choose_phase(state)
    assert controller.last_diagnostics["reason"] == "work_budget_fallback"
    assert controller.choose_phase(state) == first
    full = QueueBasedApproachPreviewController()
    durations = []
    for _ in range(5):
        started = time.perf_counter()
        full.choose_phase(state)
        durations.append(time.perf_counter() - started)
    assert max(durations) < 1.0
    assert full.last_diagnostics["reason"] == "rollout" and "costs" in full.last_diagnostics


# ---------------------------------------------------------------- P07/P15: метрики и безопасность


def _assert_safe_history(result, intersection, controller_max_green=45):
    history = result.phase_history
    greens = [item for item in history if item["color"] == "green"]
    for previous, current in itertools.pairwise(greens):
        assert previous["phase"] != current["phase"]
    if intersection.yellow_seconds > 0:
        for first, second in itertools.pairwise(history):
            assert not (first["color"] == "green" and second["color"] == "green")
    for index, item in enumerate(history[:-1]):
        if item["color"] == "yellow":
            assert history[index + 1]["at"] - item["at"] >= intersection.yellow_seconds - 1e-9


@pytest.mark.parametrize("yellow,startup", [(0, 0.0), (3, 0.0), (3, 2.0), (1, 2.0)])
def test_startup_yellow_allred_zero_yellow_keep_phases_exclusive(yellow, startup):
    intersection = _intersection(rate=12.0, yellow=yellow)
    config = SimulationConfig(
        duration_seconds=400, seed=5, service_time_seconds=2.0, startup_lost_time_seconds=startup,
        preview_seconds=10.0, sensor_model="causal",
    )
    trace: list[dict] = []
    for controller in (
        QueueBasedApproachPreviewController(min_green_seconds=4),
        DetectorVehicleActuatedController(min_green_seconds=4, use_preview=True),
    ):
        trace.clear()
        result = run_simulation(intersection, config, controller, trace_callback=trace.append)
        _assert_safe_history(result, intersection)
        for row in trace:
            busy = row["in_service_by_lane"]
            ns = busy["north"] + busy["south"]
            ew = busy["east"] + busy["west"]
            assert not (ns and ew), row
        assert result.vehicle_balance_error == 0
        durations = []
        greens = [i for i, item in enumerate(result.phase_history) if item["color"] == "green"]
        for index, position in enumerate(greens[:-1]):
            durations.append(result.phase_history[greens[index + 1]]["at"] - result.phase_history[position]["at"])
        assert all(d >= 4 - 1e-9 for d in durations)


def test_censored_overload_metrics_are_consistent():
    intersection = _intersection(rate=26.0)
    config = SimulationConfig(duration_seconds=600, seed=2, startup_lost_time_seconds=2.0)
    result = run_simulation(
        intersection, config, DetectorVehicleActuatedController(min_green_seconds=6)
    )
    assert result.vehicle_balance_error == 0
    assert result.waiting_at_end > 0
    assert result.queue_area_vehicle_seconds == pytest.approx(result.average_queue_length * 600)
    completed_wait = result.average_wait_seconds * result.vehicles_departed
    assert result.observed_delay_seconds >= completed_wait - 1e-6
    assert result.observed_delay_seconds > 1.2 * completed_wait  # цензурирование скрыто в completed wait
    assert result.p95_wait_seconds >= result.median_wait_seconds
    assert result.yellow_seconds_total + result.all_red_seconds_total > 0
    assert result.phase_switches > 0
    assert 0 <= result.green_idle_seconds <= 600


def test_arrival_rate_estimate_is_causal():
    base = [Arrival(float(t), "east") for t in range(2, 40, 2)]
    config = SimulationConfig(duration_seconds=120, arrival_rate_tau_seconds=20.0)
    states = []
    for future in ([Arrival(80.0, "east")], [Arrival(81.0, "east"), Arrival(95.0, "north")]):
        recorder = _Recorder()
        run_simulation(_intersection(), config, recorder, arrivals=base + future)
        states.append([s.arrival_rate_per_second_by_lane for s in recorder.states if s.now <= 79])
    assert states[0] == states[1]
    assert states[0][-1]["east"] > 0


# ---------------------------------------------------------------- P14: потоки


def test_platoon_and_bursty_arrivals_keep_mean_rate_and_change_structure():
    intersection = _intersection(rate=12.0)
    config = SimulationConfig(duration_seconds=3600, seed=11)
    poisson = generate_arrivals(intersection, config)
    platoon = generate_arrivals(intersection, config, None, {
        "arrival_process": "platoon", "platoon_mean_size": 4.0, "platoon_headway_seconds": 1.8})
    bursty = generate_arrivals(intersection, config, None, {
        "arrival_process": "bursty", "burst_high_factor": 2.5, "burst_low_factor": 0.2,
        "burst_mean_state_seconds": 40.0, "burst_shared_axis": True})
    for stream in (poisson, platoon, bursty):
        assert len(stream) == pytest.approx(4 * 12 * 60, rel=0.2)
    assert generate_arrivals(intersection, config, None, {"arrival_process": "poisson"}) == poisson

    def burstiness(stream):
        counts = [0] * 120
        for event in stream:
            if event.lane == "north":
                counts[min(119, int(event.at // 30))] += 1
        mean = sum(counts) / len(counts)
        return sum((c - mean) ** 2 for c in counts) / len(counts) / mean  # индекс дисперсии

    assert burstiness(platoon) > 1.5 * burstiness(poisson)
    assert burstiness(bursty) > 1.5 * burstiness(poisson)

    def axis_counts(stream, lanes):
        counts = [0] * 120
        for event in stream:
            if event.lane in lanes:
                counts[min(119, int(event.at // 30))] += 1
        return counts

    north = axis_counts(bursty, ("north",))
    south = axis_counts(bursty, ("south",))
    mean_n, mean_s = sum(north) / 120, sum(south) / 120
    cov = sum((a - mean_n) * (b - mean_s) for a, b in zip(north, south, strict=True)) / 120
    assert cov > 0  # общая модуляция оси коррелирует потоки Север и Юг


def test_v2_sensor_results_are_reproducible():
    arrivals = [Arrival(float(t), lane) for t in range(3, 200, 4) for lane in ("north", "east")]
    config = SimulationConfig(duration_seconds=200, seed=9, preview_seconds=10.0, sensor_model="causal",
                              sensor_dropout_start_probability=0.1, sensor_false_positive_rate_per_minute=1.0)
    runs = [
        run_simulation(_intersection(), config, QueueBasedApproachPreviewController(min_green_seconds=4),
                       arrivals=arrivals)
        for _ in range(2)
    ]
    assert runs[0].phase_history == runs[1].phase_history
    assert runs[0].queue_area_vehicle_seconds == runs[1].queue_area_vehicle_seconds
    assert runs[0].sensor_model == "causal"
    assert PHASE_LANES["north_south"] == ("north", "south")


# ---------------------------------------------------------------- P05/P14: воспроизводимость и без утечки


def test_reproducibility_and_no_test_leak():
    creator = _load_script("create_approach_preview_v2_configs")
    analyzer = _load_script("analyze_approach_preview_v2")
    freeze = _load_script("freeze_approach_preview_v2")
    stages = {name: set(seeds) for name, seeds in creator.SEEDS.items()}
    names = list(stages)
    for i, first in enumerate(names):
        for second in names[i + 1:]:
            assert not stages[first] & stages[second]
    legacy = set(range(12101, 12131)) | set(range(13101, 13131)) | set(range(1001, 1031))
    assert not legacy & set().union(*stages.values())
    # Выбор параметров читает только development-файлы.
    selection_source = inspect.getsource(analyzer.select)
    assert "development" in selection_source
    assert "validation" not in selection_source and "final" not in selection_source
    experiments = creator.factorial_experiments("development", 6)
    assert all(set(e["simulation"]["seeds"]) == stages["development"] for e in experiments)
    # Заморозка охватывает исходники датчика, контроллеров, симуляции и выбранные параметры.
    state = freeze.current_state() if (freeze.OUT / "development_selection.json").exists() else {
        "code_sha256": freeze.code_hashes()
    }
    assert "src/traffic_light/sensor.py" in state["code_sha256"]
    assert "src/traffic_light/controllers.py" in state["code_sha256"]
    assert "src/traffic_light/simulation.py" in state["code_sha256"]
