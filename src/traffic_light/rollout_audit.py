"""Аудит прогнозной модели rollout относительно исполняемой модели SimPy (P06, P10, P11).

* ``area_discrepancy`` — для фиксированного плана переключений сравнивает посекундную
  площадь очереди rollout и SimPy из одного и того же состояния контроллера (целые времена
  прибытий и целое время обслуживания: тактовая сетка rollout точна, ожидаются нули).
* ``fractional_arrival_error`` — ошибка округления ETA (floor/round/ceil) при дробных
  временах прибытий.
* ``exhaustive_regret`` — сожаление выбранного первого действия относительно полного
  перебора планов с одним-двумя переключениями на коротком горизонте (в той же модели).
"""
from __future__ import annotations

import itertools
import random
from copy import deepcopy
from dataclasses import dataclass

from traffic_light.config import IntersectionConfig, SimulationConfig, TrafficDemandConfig
from traffic_light.controllers import (
    BaseController,
    ControllerState,
    QueueBasedApproachPreviewController,
    other_phase,
)
from traffic_light.simulation import Arrival, run_simulation

LANES = ("north", "south", "east", "west")


class PlanController(BaseController):
    """Переключается ровно в заданные такты (без min/max green) и записывает состояния."""

    name = "plan"

    def __init__(self, switch_ticks) -> None:
        self.switch_ticks = {int(tick) for tick in switch_ticks}
        self.states: dict[int, ControllerState] = {}

    def choose_phase(self, state: ControllerState):
        self.states[int(state.now)] = deepcopy(state)
        if int(state.now) in self.switch_ticks:
            return other_phase(state.current_phase)
        return state.current_phase


def audit_intersection(yellow: int) -> IntersectionConfig:
    return IntersectionConfig(
        lanes={lane: TrafficDemandConfig(arrival_rate_per_minute=6) for lane in LANES},
        min_green_seconds=1,
        yellow_seconds=yellow,
    )


@dataclass(frozen=True)
class AuditCase:
    seed: int
    yellow: int
    startup: float
    service: float
    start_tick: int
    switches: tuple[int, ...]
    horizon: int = 30
    fractional: bool = False


def _case_world(case: AuditCase):
    rng = random.Random(case.seed)
    queues = {lane: rng.randint(0, 6) for lane in LANES}
    arrivals: list[Arrival] = []
    for lane in LANES:
        at = 0.0
        for _ in range(rng.randint(0, 6)):
            at += rng.uniform(0.5, 8.0) if case.fractional else float(rng.randint(1, 8))
            arrivals.append(Arrival(at, lane))
    limit = case.start_tick + case.horizon + 5
    return queues, [event for event in arrivals if event.at < limit]


def _run(case: AuditCase, duration: int, queues, arrivals, plan: PlanController):
    config = SimulationConfig(
        duration_seconds=duration,
        seed=case.seed,
        service_time_seconds=case.service,
        startup_lost_time_seconds=case.startup,
        preview_seconds=float(case.horizon + 5),
    )
    return run_simulation(
        audit_intersection(case.yellow),
        config,
        plan,
        initial_queues=queues,
        arrivals=[event for event in arrivals if event.at < duration],
    )


def area_discrepancy(case: AuditCase, eta_rounding: str = "ceil") -> tuple[list[float], list[float]] | None:
    """Посекундная площадь очереди: (rollout, SimPy). None — состояние на start_tick недоступно."""
    queues, arrivals = _case_world(case)
    absolute = [case.start_tick + step for step in case.switches]
    plan = PlanController(absolute)
    _run(case, case.start_tick + case.horizon + 1, queues, arrivals, plan)
    state = plan.states.get(case.start_tick)
    if state is None:
        return None
    controller = QueueBasedApproachPreviewController(
        planning_horizon_seconds=case.horizon, eta_rounding=eta_rounding
    )
    predicted = controller.rollout_trajectory(
        state,
        state.now - state.phase_started_at,
        None,
        explicit_switch_steps=tuple(case.switches),
    )
    areas = [
        _run(case, case.start_tick + k, queues, arrivals, PlanController(absolute)).queue_area_vehicle_seconds
        for k in range(case.horizon + 1)
    ]
    actual = [areas[k + 1] - areas[k] for k in range(case.horizon)]
    return predicted, actual


def integer_grid_cases(seeds=range(20)) -> list[AuditCase]:
    cases = []
    for seed in seeds:
        for yellow, startup, service in itertools.product((0, 1, 3), (0.0, 2.0), (2.0, 4.0)):
            for switches in ((0,), (5,), (0, 12)):
                cases.append(AuditCase(seed, yellow, startup, service, 10, switches))
    return cases


def fractional_arrival_error(seeds=range(20)) -> list[dict]:
    """Относительная ошибка суммарной площади очереди при дробных временах прибытия."""
    rows = []
    for mode in ("floor", "round", "ceil"):
        errors, signed = [], []
        for seed in seeds:
            for switches in ((0,), (6,)):
                case = AuditCase(seed, 3, 2.0, 2.0, 10, switches, fractional=True)
                result = area_discrepancy(case, eta_rounding=mode)
                if result is None:
                    continue
                predicted, actual = result
                if sum(actual) <= 0:
                    continue
                relative = (sum(predicted) - sum(actual)) / sum(actual)
                signed.append(relative)
                errors.append(abs(relative))
        rows.append(
            {
                "eta_rounding": mode,
                "cases": len(errors),
                "mean_signed_relative_error": sum(signed) / len(signed) if signed else 0.0,
                "mean_abs_relative_error": sum(errors) / len(errors) if errors else 0.0,
                "max_abs_relative_error": max(errors) if errors else 0.0,
            }
        )
    return rows


def _plans(horizon: int, yellow: int, min_gap: int):
    yield ()
    for first in range(horizon):
        yield (first,)
    for first in range(horizon):
        for second in range(first + yellow + min_gap, horizon):
            yield (first, second)


def _random_state(rng: random.Random, horizon: int, yellow: int) -> ControllerState:
    # Половина состояний — «пустой» текущий подход против очереди на конкурирующем, где
    # переключение действительно может быть оптимальным.
    if rng.random() < 0.5:
        queues = {lane: rng.randint(0, 8) for lane in LANES}
    else:
        queues = {
            "north": rng.randint(0, 1), "south": rng.randint(0, 1),
            "east": rng.randint(2, 9), "west": rng.randint(2, 9),
        }
    etas = {
        lane: sorted(rng.uniform(0.0, horizon - 1) for _ in range(rng.randint(0, 3))) for lane in LANES
    }
    elapsed = rng.randint(4, 20)
    return ControllerState(
        now=100.0,
        current_phase="north_south",
        phase_started_at=100.0 - elapsed,
        queues=queues,
        yellow_seconds=yellow,
        service_seconds=2.0,
        in_service_by_lane={lane: rng.randint(0, 1) for lane in LANES},
        service_remaining_by_lane={lane: rng.choice((0.0, 1.0)) for lane in LANES},
        startup_lost_seconds=2.0,
        upcoming_arrival_offsets=etas,
        preview_status="ok",
        preview_window_seconds=float(horizon),
    )


def exhaustive_regret(seeds=range(200), horizon: int = 16, yellow: int = 3) -> dict:
    """Сожаление первого действия rollout-контроллера относительно перебора планов (в модели).

    Состояния случайные (очереди, ETA, остаток обслуживания, возраст зелёного); перебор —
    все планы с 0, 1 или 2 переключениями на горизонте ``horizon`` с ограничением на
    минимальный интервал между переключениями. Это проверка качества эвристики «одно
    переключение + gap-out» внутри самой прогнозной модели, а не в SimPy.
    """
    controller = QueueBasedApproachPreviewController(
        min_green_seconds=4,
        continuation_min_green_seconds=4,
        planning_horizon_seconds=horizon,
        max_switch_delay_seconds=horizon - 2,
    )
    regrets: list[float] = []
    for seed in seeds:
        state = _random_state(random.Random(seed), horizon, yellow)
        elapsed = state.now - state.phase_started_at
        chosen = controller.choose_phase(state)
        by_first: dict[str, float] = {"hold": float("inf"), "switch": float("inf")}
        for steps in _plans(horizon, yellow, controller.continuation_min_green_seconds):
            cost = sum(controller.rollout_trajectory(state, elapsed, None, explicit_switch_steps=steps))
            kind = "switch" if steps and steps[0] == 0 else "hold"
            by_first[kind] = min(by_first[kind], cost)
        best = min(by_first.values())
        taken = by_first["switch" if chosen != state.current_phase else "hold"]
        regrets.append(taken - best)
    states = len(regrets)
    return {
        "states": states,
        "non_optimal_share": sum(value > 1e-9 for value in regrets) / states if states else 0.0,
        "mean_regret_vehicle_seconds": sum(regrets) / states if states else 0.0,
        "max_regret_vehicle_seconds": max(regrets) if regrets else 0.0,
    }
