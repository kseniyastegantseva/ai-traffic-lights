from __future__ import annotations

import json
from dataclasses import dataclass
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
class ActuatedController(BaseController):
    min_green_seconds: int = 15
    decision_interval_seconds: int = 10
    name: str = "actuated"

    def choose_phase(self, state: ControllerState) -> PhaseName:
        elapsed = state.now - state.phase_started_at
        if elapsed < self.min_green_seconds or int(state.now) % self.decision_interval_seconds:
            return state.current_phase

        current_pressure = sum(state.queues[lane] for lane in PHASE_LANES[state.current_phase])
        other = other_phase(state.current_phase)
        other_pressure = sum(state.queues[lane] for lane in PHASE_LANES[other])
        return other if other_pressure > current_pressure + 1 else state.current_phase


@dataclass
class AIPhaseController(BaseController):
    min_green_seconds: int = 15
    decision_interval_seconds: int = 10
    name: str = "ai"

    def choose_phase(self, state: ControllerState) -> PhaseName:
        elapsed = state.now - state.phase_started_at
        if elapsed < self.min_green_seconds or int(state.now) % self.decision_interval_seconds:
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
        if elapsed < self.min_green_seconds or int(state.now) % self.decision_interval_seconds:
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
