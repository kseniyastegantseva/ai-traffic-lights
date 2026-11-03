from __future__ import annotations

import json
from dataclasses import dataclass
from math import ceil
from pathlib import Path

from traffic_light.config import PhaseName

PHASE_LANES: dict[PhaseName, tuple[str, str]] = {
    "north_south": ("north", "south"),
    "east_west": ("east", "west"),
}


def other_phase(phase: PhaseName) -> PhaseName:
    return "east_west" if phase == "north_south" else "north_south"


@dataclass
class ControllerState:
    now: float
    current_phase: PhaseName
    phase_started_at: float
    queues: dict[str, int]
    current_gap_seconds: float = 0.0
    red_request_elapsed_seconds: dict[PhaseName, float] | None = None
    yellow_seconds: float = 0.0
    service_seconds: float = 2.0
    in_service_by_lane: dict[str, int] | None = None
    # Смещения (с, от now) ожидаемых прибытий по полосам по данным датчика подъезда;
    # None — датчика нет, пустой список — датчик есть, но машин в окне не видит.
    upcoming_arrival_offsets: dict[str, list[float]] | None = None


class BaseController:
    name = "base"

    def choose_phase(self, state: ControllerState) -> PhaseName:
        raise NotImplementedError


@dataclass
class FixedTimeController(BaseController):
    phase_duration_seconds: int = 35
    name: str = "fixed"

    def choose_phase(self, state: ControllerState) -> PhaseName:
        elapsed = state.now - state.phase_started_at
        if elapsed >= self.phase_duration_seconds:
            return other_phase(state.current_phase)
        return state.current_phase


@dataclass
class FixedWebsterController(BaseController):
    """Fixed-cycle Webster split using the configured design flow ratios."""

    green_seconds: dict[PhaseName, float]
    min_green_seconds: float = 8.0
    name: str = "fixed_webster"

    @staticmethod
    def green_split(
        critical_flow_ratios: dict[PhaseName, float],
        lost_time_seconds: float,
        min_green_seconds: float = 8.0,
        max_green_seconds: float = 90.0,
    ) -> dict[PhaseName, float]:
        ratios = {phase: max(0.0, float(critical_flow_ratios.get(phase, 0.0))) for phase in PHASE_LANES}
        total = sum(ratios.values())
        if total <= 0 or total >= 0.90 or lost_time_seconds >= 60.0:
            # Webster's optimum cycle is undefined/non-operational here; use
            # an explicit equal-split fallback bounded by configured limits.
            split = max(min_green_seconds, min(max_green_seconds, (120.0 - lost_time_seconds) / 2))
            return {phase: split for phase in PHASE_LANES}
        cycle = (1.5 * lost_time_seconds + 5.0) / (1.0 - total)
        effective_green = max(2 * min_green_seconds, cycle - lost_time_seconds)
        return {
            phase: max(min_green_seconds, min(max_green_seconds, effective_green * ratios[phase] / total))
            for phase in PHASE_LANES
        }

    def choose_phase(self, state: ControllerState) -> PhaseName:
        if state.now - state.phase_started_at >= self.green_seconds[state.current_phase]:
            return other_phase(state.current_phase)
        return state.current_phase


@dataclass
class VehicleActuatedController(BaseController):
    min_green_seconds: int = 8
    max_green_seconds: int = 45
    gap_seconds: float = 3.0
    name: str = "vehicle_actuated"

    def choose_phase(self, state: ControllerState) -> PhaseName:
        elapsed = state.now - state.phase_started_at
        other = other_phase(state.current_phase)
        current_q = sum(state.queues[lane] for lane in PHASE_LANES[state.current_phase])
        other_q = sum(state.queues[lane] for lane in PHASE_LANES[other])
        if other_q == 0:
            return state.current_phase
        if elapsed >= self.max_green_seconds:
            return other
        if elapsed < self.min_green_seconds:
            return state.current_phase
        # With aggregate queue observations, an empty current approach and a
        # competing request is the available gap-out proxy; it is not detector
        # headway logic and is documented as such.
        if current_q == 0 and other_q > 0 and state.current_gap_seconds >= self.gap_seconds:
            return other
        return state.current_phase


@dataclass
class QueueBasedApproachPreviewController(BaseController):
    """Rollout-управление по очередям и подъезжающим автомобилям.

    На каждом такте перебирает момент переключения (сейчас, через 1..N секунд, не
    переключать) и оценивает каждый вариант прогоном вперёд: очередь плюс ожидаемые
    прибытия по датчику подъезда, дальше — правило gap-out. Выбирает вариант с наименьшей
    площадью очереди. При равной оценке удерживает текущий зелёный. Максимальный зелёный
    при конкурирующей очереди принудительный, поэтому ось не может быть заморожена.
    Без датчика (``upcoming_arrival_offsets is None``) прибытия в прогоне нулевые.
    """

    min_green_seconds: int = 4
    max_green_seconds: int = 45
    planning_horizon_seconds: int = 50
    max_switch_delay_seconds: int = 24
    continuation_min_green_seconds: int = 8
    name: str = "queue_based_approach_preview"

    def choose_phase(self, state: ControllerState) -> PhaseName:
        elapsed = state.now - state.phase_started_at
        phase = state.current_phase
        other = other_phase(phase)
        current_lanes, other_lanes = PHASE_LANES[phase], PHASE_LANES[other]
        current_q = sum(state.queues[lane] for lane in current_lanes)
        other_q = sum(state.queues[lane] for lane in other_lanes)
        upcoming = state.upcoming_arrival_offsets or {}
        other_expected = sum(len(upcoming.get(lane, ())) for lane in other_lanes)
        if elapsed < self.min_green_seconds or (other_q == 0 and other_expected == 0):
            return phase
        if elapsed >= self.max_green_seconds and other_q > 0:
            return other

        base_switch_now = other_q > 0 and (
            elapsed >= self.max_green_seconds
            or (elapsed >= self.continuation_min_green_seconds and current_q == 0)
        )
        candidates: list[int | None] = list(range(self.max_switch_delay_seconds + 1))
        if not base_switch_now:
            candidates.append(None)
        best_cost, best_delay = None, None
        for delay in candidates:
            cost = self._rollout(state, elapsed, delay)
            if best_cost is None or cost <= best_cost + 1e-9:
                best_cost, best_delay = cost, delay
        return other if best_delay == 0 else phase

    def _rollout(self, state: ControllerState, elapsed: float, switch_delay: int | None) -> float:
        lanes = tuple(state.queues)
        queue = {lane: float(state.queues[lane]) for lane in lanes}
        service = max(state.service_seconds, 1e-9)
        busy = state.in_service_by_lane or {}
        free_at = {lane: (1.0 if busy.get(lane) else 0.0) for lane in lanes}
        arrivals: dict[str, dict[int, int]] = {lane: {} for lane in lanes}
        for lane, offsets in (state.upcoming_arrival_offsets or {}).items():
            for offset in offsets:
                second = int(offset)
                if second < self.planning_horizon_seconds:
                    arrivals[lane][second] = arrivals[lane].get(second, 0) + 1

        green = state.current_phase
        yellow_until: float | None = None
        plan_done = switch_delay is None
        cost = 0.0
        for step in range(self.planning_horizon_seconds):
            for lane in lanes:
                queue[lane] += arrivals[lane].get(step, 0)
            if yellow_until is not None and step >= yellow_until:
                green, yellow_until, elapsed = other_phase(green), None, 0.0
                for lane in PHASE_LANES[green]:
                    free_at[lane] = max(free_at[lane], float(step))
            if yellow_until is None:
                current = sum(queue[lane] for lane in PHASE_LANES[green])
                competing = sum(queue[lane] for lane in PHASE_LANES[other_phase(green)])
                switch = False
                if not plan_done and step == switch_delay:
                    switch, plan_done = True, True
                elif plan_done and competing > 0 and (
                    elapsed >= self.max_green_seconds
                    or (elapsed >= self.continuation_min_green_seconds and current == 0)
                ):
                    switch = True
                if switch:
                    yellow_until = step + state.yellow_seconds
                else:
                    for lane in PHASE_LANES[green]:
                        if queue[lane] >= 1.0 and free_at[lane] <= step:
                            queue[lane] -= 1.0
                            free_at[lane] = step + service
                    elapsed += 1
            cost += sum(queue.values())
        return cost


@dataclass
class QueueBasedController(BaseController):
    min_green_seconds: int = 8
    max_green_seconds: int = 45
    switching_margin: int = 1
    legacy_rule: bool = False
    name: str = "queue_based"

    def choose_phase(self, state: ControllerState) -> PhaseName:
        elapsed = state.now - state.phase_started_at
        other = other_phase(state.current_phase)
        current_q = sum(state.queues[lane] for lane in PHASE_LANES[state.current_phase])
        other_q = sum(state.queues[lane] for lane in PHASE_LANES[other])
        if self.legacy_rule:
            if other_q == 0:
                return state.current_phase
            if elapsed < self.min_green_seconds:
                return state.current_phase
            if elapsed >= self.max_green_seconds or current_q == 0:
                return other
            return other if other_q > current_q + self.switching_margin else state.current_phase
        if other_q == 0:
            return state.current_phase
        if elapsed >= self.max_green_seconds:
            return other
        if elapsed < self.min_green_seconds:
            return state.current_phase
        return other if other_q > current_q + self.switching_margin else state.current_phase


@dataclass
class QueueBasedImprovedController(BaseController):
    """Queue-pressure controller with congestion-aware green hold and hysteresis.

    The absolute margin preserves the original queue rule at small queues. The
    longer minimum green activates only once total observed queues cross the
    configured threshold. The relative term scales the switching threshold as
    queues grow. A competing queue still triggers a hard switch at maximum green.
    """

    min_green_seconds: int = 8
    max_green_seconds: int = 45
    switching_margin: int = 1
    relative_switching_margin: float = 0.10
    congested_min_green_seconds: int = 20
    congestion_queue_threshold: int = 10
    name: str = "queue_based_improved"

    def _observe_queue_state(self, total_q: int, state: ControllerState) -> None:
        """Hook for experimental minimum-green policies with memory."""

    def _effective_min_green(self, total_q: int, current_q: int) -> float:
        return (
            self.congested_min_green_seconds
            if total_q >= self.congestion_queue_threshold
            else self.min_green_seconds
        )

    def _effective_switching_margin(self, total_q: int, elapsed: float) -> int:
        del elapsed
        return max(
            self.switching_margin,
            ceil(self.relative_switching_margin * total_q),
        )

    def choose_phase(self, state: ControllerState) -> PhaseName:
        elapsed = state.now - state.phase_started_at
        other = other_phase(state.current_phase)
        current_q = sum(state.queues[lane] for lane in PHASE_LANES[state.current_phase])
        other_q = sum(state.queues[lane] for lane in PHASE_LANES[other])
        total_q = current_q + other_q
        self._observe_queue_state(total_q, state)
        if other_q == 0:
            return state.current_phase
        if elapsed >= self.max_green_seconds:
            return other
        effective_min_green = self._effective_min_green(total_q, current_q)
        if elapsed < effective_min_green:
            return state.current_phase
        margin = self._effective_switching_margin(total_q, elapsed)
        return other if other_q > current_q + margin else state.current_phase


@dataclass
class QueueBasedSmoothMinGreenController(QueueBasedImprovedController):
    """Linearly ramps minimum green across a queue band instead of one threshold."""

    smooth_congestion_start_queue: int = 10
    smooth_congestion_end_queue: int = 18
    name: str = "queue_based_smooth_min_green"

    def _effective_min_green(self, total_q: int, current_q: int) -> float:
        width = self.smooth_congestion_end_queue - self.smooth_congestion_start_queue
        progress = min(
            1.0,
            max(0.0, (total_q - self.smooth_congestion_start_queue) / width),
        )
        return self.min_green_seconds + progress * (
            self.congested_min_green_seconds - self.min_green_seconds
        )


@dataclass
class QueueBasedHysteresisController(QueueBasedImprovedController):
    """Uses separate queue thresholds to enter and leave congestion mode."""

    congestion_exit_threshold: int = 10
    congestion_active: bool = False
    name: str = "queue_based_hysteresis"

    def _observe_queue_state(self, total_q: int, state: ControllerState) -> None:
        if self.congestion_active:
            if total_q <= self.congestion_exit_threshold:
                self.congestion_active = False
        elif total_q >= self.congestion_queue_threshold:
            self.congestion_active = True

    def _effective_min_green(self, total_q: int, current_q: int) -> float:
        return (
            self.congested_min_green_seconds
            if self.congestion_active
            else self.min_green_seconds
        )


@dataclass
class QueueBasedPersistentCongestionController(QueueBasedImprovedController):
    """Enters congestion mode only after high pressure persists for a set time."""

    congestion_persistence_seconds: float = 5.0
    high_pressure_since: float | None = None
    current_time: float = 0.0
    name: str = "queue_based_persistent_congestion"

    def _observe_queue_state(self, total_q: int, state: ControllerState) -> None:
        self.current_time = state.now
        if total_q >= self.congestion_queue_threshold:
            if self.high_pressure_since is None:
                self.high_pressure_since = state.now
        else:
            self.high_pressure_since = None

    def _effective_min_green(self, total_q: int, current_q: int) -> float:
        persistent = (
            self.high_pressure_since is not None
            and total_q >= self.congestion_queue_threshold
            and self.high_pressure_since + self.congestion_persistence_seconds <= self.current_time
        )
        return self.congested_min_green_seconds if persistent else self.min_green_seconds


@dataclass
class QueueBasedAxisSpecificCongestionController(QueueBasedImprovedController):
    """Extends the green only when the currently served axis is congested."""

    name: str = "queue_based_axis_specific_congestion"

    def _effective_min_green(self, total_q: int, current_q: int) -> float:
        return (
            self.congested_min_green_seconds
            if current_q >= self.congestion_queue_threshold
            else self.min_green_seconds
        )


@dataclass
class QueueBasedElapsedMarginController(QueueBasedImprovedController):
    """Gradually relaxes the queue margin after the effective minimum green."""

    switching_margin_decay_per_second: float = 0.025
    minimum_switching_margin: int = 1
    name: str = "queue_based_elapsed_margin"

    def _effective_switching_margin(self, total_q: int, elapsed: float) -> int:
        base_margin = max(
            self.switching_margin,
            ceil(self.relative_switching_margin * total_q),
        )
        minimum_green = self._effective_min_green(total_q, 0)
        elapsed_after_min = max(0.0, elapsed - minimum_green)
        scale = max(
            self.minimum_switching_margin / max(base_margin, 1),
            1.0 - self.switching_margin_decay_per_second * elapsed_after_min,
        )
        return max(self.minimum_switching_margin, ceil(base_margin * scale))


@dataclass
class QueueBasedEmptyGapFixController(QueueBasedImprovedController):
    """Improved queue rule with an empty-green gap-out condition.

    ``current_gap_seconds`` is computed from the absence of queued vehicles in
    the current axis. It is only an aggregate-queue proxy, not detector headway
    or proof that the intersection is physically clear.
    """

    congested_min_green_seconds: int = 25
    congestion_queue_threshold: int = 14
    empty_gap_seconds: float = 1.0
    name: str = "queue_based_empty_gap_fix"

    def choose_phase(self, state: ControllerState) -> PhaseName:
        elapsed = state.now - state.phase_started_at
        other = other_phase(state.current_phase)
        current_q = sum(state.queues[lane] for lane in PHASE_LANES[state.current_phase])
        other_q = sum(state.queues[lane] for lane in PHASE_LANES[other])
        if other_q == 0:
            return state.current_phase
        if elapsed >= self.max_green_seconds:
            return other

        total_q = current_q + other_q
        effective_min_green = (
            self.congested_min_green_seconds
            if total_q >= self.congestion_queue_threshold
            else self.min_green_seconds
        )
        if elapsed < effective_min_green:
            return state.current_phase

        if current_q == 0 and state.current_gap_seconds >= self.empty_gap_seconds:
            return other

        margin = max(
            self.switching_margin,
            ceil(self.relative_switching_margin * total_q),
        )
        return other if other_q > current_q + margin else state.current_phase


@dataclass
class QueueBasedMaxRedController(QueueBasedImprovedController):
    """Improved queue controller with an observed red-time fairness bound."""

    max_red_seconds: float = 48.0
    name: str = "queue_based_max_red"

    def choose_phase(self, state: ControllerState) -> PhaseName:
        elapsed = state.now - state.phase_started_at
        other = other_phase(state.current_phase)
        current_q = sum(state.queues[lane] for lane in PHASE_LANES[state.current_phase])
        other_q = sum(state.queues[lane] for lane in PHASE_LANES[other])
        if other_q == 0:
            return state.current_phase
        if elapsed >= self.max_green_seconds:
            return other

        total_q = current_q + other_q
        effective_min_green = (
            self.congested_min_green_seconds
            if total_q >= self.congestion_queue_threshold
            else self.min_green_seconds
        )
        if elapsed < effective_min_green:
            return state.current_phase

        red_wait_elapsed = (state.red_request_elapsed_seconds or {}).get(other, 0.0)
        # The request remains red during yellow clearance, so start the transition
        # early enough for the opposing green to begin by the configured limit.
        # The controller observes queues on integer-second ticks. Reserve one
        # additional second for the worst-case observation delay.
        red_limit_at_decision = max(0.0, self.max_red_seconds - state.yellow_seconds - 1.0)
        if red_wait_elapsed >= red_limit_at_decision:
            return other

        margin = max(
            self.switching_margin,
            ceil(self.relative_switching_margin * total_q),
        )
        return other if other_q > current_q + margin else state.current_phase


@dataclass
class ActuatedController(BaseController):
    min_green_seconds: int = 15
    decision_interval_seconds: int = 10
    max_green_seconds: int = 45
    name: str = "actuated"

    def choose_phase(self, state: ControllerState) -> PhaseName:
        elapsed = state.now - state.phase_started_at
        other = other_phase(state.current_phase)
        other_pressure = sum(state.queues[lane] for lane in PHASE_LANES[other])
        if elapsed >= self.max_green_seconds and other_pressure > 0:
            return other
        if elapsed < self.min_green_seconds or int(elapsed) % self.decision_interval_seconds:
            return state.current_phase

        current_pressure = sum(state.queues[lane] for lane in PHASE_LANES[state.current_phase])
        return other if other_pressure > current_pressure + 1 else state.current_phase


@dataclass
class AIPhaseController(BaseController):
    min_green_seconds: int = 15
    decision_interval_seconds: int = 10
    max_green_seconds: int = 45
    name: str = "ai"

    def choose_phase(self, state: ControllerState) -> PhaseName:
        elapsed = state.now - state.phase_started_at
        other = other_phase(state.current_phase)
        other_pressure = sum(state.queues[lane] for lane in PHASE_LANES[other])
        if elapsed >= self.max_green_seconds and other_pressure > 0:
            return other
        if elapsed < self.min_green_seconds or int(elapsed) % self.decision_interval_seconds:
            return state.current_phase

        scores = {
            phase: sum(state.queues[lane] for lane in lanes)
            for phase, lanes in PHASE_LANES.items()
        }
        return max(scores, key=scores.get)


@dataclass
class QLearningPolicyController(BaseController):
    policy_path: str = "outputs/q_learning_policy.json"
    min_green_seconds: int = 15
    decision_interval_seconds: int = 10
    max_green_seconds: int = 45
    name: str = "q_learning"

    def __post_init__(self) -> None:
        path = Path(self.policy_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Q-learning policy not found: {self.policy_path}. "
                "Run `traffic-sim train --config configs/ai.yaml` first."
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.q_table: dict[str, list[float]] = payload.get("q_table", {})

    def choose_phase(self, state: ControllerState) -> PhaseName:
        elapsed = state.now - state.phase_started_at
        other = other_phase(state.current_phase)
        other_pressure = sum(state.queues[lane] for lane in PHASE_LANES[other])
        if elapsed >= self.max_green_seconds and other_pressure > 0:
            return other
        if elapsed < self.min_green_seconds or int(elapsed) % self.decision_interval_seconds:
            return state.current_phase

        key = _state_key(state)
        values = self.q_table.get(key)
        if values is None:
            return self._fallback_phase(state)
        return "north_south" if values[0] >= values[1] else "east_west"

    def _fallback_phase(self, state: ControllerState) -> PhaseName:
        scores = {
            phase: sum(state.queues[lane] for lane in lanes)
            for phase, lanes in PHASE_LANES.items()
        }
        return max(scores, key=scores.get)


def _state_key(state: ControllerState) -> str:
    phase = 0 if state.current_phase == "north_south" else 1
    queue_bins = [
        _queue_bin(state.queues[lane])
        for lane in ("north", "south", "east", "west")
    ]
    return ",".join([*(str(value) for value in queue_bins), str(phase)])


def _queue_bin(value: int) -> int:
    if value <= 0:
        return 0
    if value <= 3:
        return 1
    if value <= 7:
        return 2
    if value <= 15:
        return 3
    return 4
