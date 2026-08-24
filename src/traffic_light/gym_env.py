from __future__ import annotations

from typing import ClassVar

import numpy as np

from traffic_light.config import IntersectionConfig, SimulationConfig

try:
    import gymnasium as gym
    from gymnasium import spaces
except ImportError:  # pragma: no cover
    gym = None
    spaces = None


LANE_ORDER = ("north", "south", "east", "west")


class TrafficLightEnv(gym.Env if gym else object):
    """Gymnasium-среда для обучения выбора фазы светофора."""

    metadata: ClassVar[dict[str, list[str]]] = {"render_modes": []}

    def __init__(
        self,
        intersection: IntersectionConfig,
        simulation: SimulationConfig,
        decision_interval_seconds: int = 10,
        max_queue: int = 50,
    ) -> None:
        if gym is None:
            raise ImportError("Install gymnasium to use TrafficLightEnv.")
        self.intersection = intersection
        self.simulation = simulation
        self.decision_interval_seconds = decision_interval_seconds
        self.max_queue = max_queue
        self.max_steps = max(1, simulation.duration_seconds // decision_interval_seconds)
        self.service_capacity = max(
            1,
            int(decision_interval_seconds / simulation.service_time_seconds),
        )
        self.arrival_rates = np.array(
            [
                intersection.lanes[lane].arrival_rate_per_minute
                * decision_interval_seconds
                / 60
                for lane in LANE_ORDER
            ],
            dtype=np.float32,
        )

        self.observation_space = spaces.Box(
            low=0,
            high=max_queue,
            shape=(5,),
            dtype=np.float32,
        )
        self.action_space = spaces.Discrete(2)
        self.queues = np.zeros(4, dtype=np.float32)
        self.current_phase = 0
        self.step_index = 0

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        self.queues = np.zeros(4, dtype=np.float32)
        self.current_phase = 0
        self.step_index = 0
        return self._observation(), {}

    def step(self, action: int):
        action = int(action)
        switched = action != self.current_phase
        self.current_phase = action

        arrivals = self.np_random.poisson(self.arrival_rates).astype(np.float32)
        self.queues = np.clip(self.queues + arrivals, 0, self.max_queue)

        served_lanes = (0, 1) if self.current_phase == 0 else (2, 3)
        for lane_index in served_lanes:
            self.queues[lane_index] = max(0.0, self.queues[lane_index] - self.service_capacity)

        self.step_index += 1
        terminated = self.step_index >= self.max_steps
        reward = -float(self.queues.sum()) - (1.0 if switched else 0.0)
        info = {
            "total_queue": float(self.queues.sum()),
            "phase": "north_south" if self.current_phase == 0 else "east_west",
            "switched": switched,
        }
        return self._observation(), reward, terminated, False, info

    def _observation(self) -> np.ndarray:
        return np.array([*self.queues, float(self.current_phase)], dtype=np.float32)
