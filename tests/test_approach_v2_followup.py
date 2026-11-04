"""Контракт дополнительного ограничения без изменения исходного D."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from approach_v2_followup import RedGuard

from traffic_light.controllers import BaseController, ControllerState


class Hold(BaseController):
    min_green_seconds = 6
    name = "hold"

    def choose_phase(self, state):
        return state.current_phase


def state(now=30, age=20, queued=1, start=0):
    return ControllerState(now=now, current_phase="north_south", phase_started_at=start,
                           queues={"north": 1, "south": 0, "east": queued, "west": 0},
                           red_request_elapsed_seconds={"east_west": age})


def test_guard_switches_only_after_threshold_with_competing_queue_and_min_green():
    guard = RedGuard(Hold(), 20)
    assert guard.choose_phase(state()) == "east_west"
    assert guard.choose_phase(state(age=19.9)) == "north_south"
    assert guard.choose_phase(state(queued=0)) == "north_south"
    assert guard.choose_phase(state(now=30, start=25)) == "north_south"
