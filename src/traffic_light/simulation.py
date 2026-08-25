from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from statistics import mean, median

import simpy

from traffic_light.config import IntersectionConfig, PhaseName, SimulationConfig
from traffic_light.controllers import PHASE_LANES, BaseController, ControllerState


@dataclass(frozen=True)
class Vehicle:
    lane: str
    arrived_at: float


@dataclass
class SimulationResult:
    controller: str
    seed: int
    duration_seconds: int
    vehicles_arrived: int
    vehicles_departed: int
    throughput_per_hour: float
    average_wait_seconds: float
    median_wait_seconds: float
    max_wait_seconds: float
    average_queue_length: float
    stops: int
    fairness_index: float
    lane_waits: dict[str, float]
    queue_series: list[int]

    def to_dict(self) -> dict:
        return asdict(self)


class IntersectionSimulation:
    def __init__(
        self,
        intersection: IntersectionConfig,
        simulation: SimulationConfig,
        controller: BaseController,
    ) -> None:
        self.intersection = intersection
        self.config = simulation
        self.controller = controller
        self.random = random.Random(simulation.seed)
        self.env = simpy.Environment()
        self.current_phase: PhaseName = "north_south"
        self.phase_started_at = 0.0
        self.queues: dict[str, list[Vehicle]] = {lane: [] for lane in intersection.lanes}
        self.waits: list[float] = []
        self.waits_by_lane: dict[str, list[float]] = {lane: [] for lane in intersection.lanes}
        self.queue_samples: list[int] = []
        self.arrived = 0
        self.departed = 0
        self.stops = 0

    def run(self) -> SimulationResult:
        for lane in self.intersection.lanes:
            self.env.process(self._arrivals(lane))
        self.env.process(self._service())
        self.env.process(self._control())
        self.env.process(self._sample_queues())
        self.env.run(until=self.config.duration_seconds)
        return self._result()

    def _arrivals(self, lane: str):
        rate_per_minute = self.intersection.lanes[lane].arrival_rate_per_minute
        if rate_per_minute <= 0:
            return
        mean_gap_seconds = 60 / rate_per_minute
        while True:
            yield self.env.timeout(self.random.expovariate(1 / mean_gap_seconds))
            self.queues[lane].append(Vehicle(lane=lane, arrived_at=self.env.now))
            self.arrived += 1

    def _service(self):
        while True:
            moved = False
            for lane in PHASE_LANES[self.current_phase]:
                if self.queues[lane]:
                    vehicle = self.queues[lane].pop(0)
                    wait = self.env.now - vehicle.arrived_at
                    self.waits.append(wait)
                    self.waits_by_lane[lane].append(wait)
                    self.departed += 1
                    self.stops += int(wait > 1)
                    moved = True
            yield self.env.timeout(self.config.service_time_seconds if moved else 1)

    def _control(self):
        while True:
            state = ControllerState(
                now=self.env.now,
                current_phase=self.current_phase,
                phase_started_at=self.phase_started_at,
                queues={lane: len(queue) for lane, queue in self.queues.items()},
            )
            next_phase = self.controller.choose_phase(state)
            if next_phase != self.current_phase:
                yield self.env.timeout(self.intersection.yellow_seconds)
                self.current_phase = next_phase
                self.phase_started_at = self.env.now
            yield self.env.timeout(1)

    def _sample_queues(self):
        while True:
            self.queue_samples.append(sum(len(queue) for queue in self.queues.values()))
            yield self.env.timeout(1)

    def _result(self) -> SimulationResult:
        duration_hours = self.config.duration_seconds / 3600
        lane_waits = {
            lane: mean(waits) if waits else 0.0
            for lane, waits in self.waits_by_lane.items()
        }
        return SimulationResult(
            controller=self.controller.name,
            seed=self.config.seed,
            duration_seconds=self.config.duration_seconds,
            vehicles_arrived=self.arrived,
            vehicles_departed=self.departed,
            throughput_per_hour=self.departed / duration_hours,
            average_wait_seconds=mean(self.waits) if self.waits else 0.0,
            median_wait_seconds=median(self.waits) if self.waits else 0.0,
            max_wait_seconds=max(self.waits) if self.waits else 0.0,
            average_queue_length=mean(self.queue_samples) if self.queue_samples else 0.0,
            stops=self.stops,
            fairness_index=_jain_index(list(lane_waits.values())),
            lane_waits=lane_waits,
            queue_series=self.queue_samples,
        )


def run_simulation(
    intersection: IntersectionConfig,
    simulation: SimulationConfig,
    controller: BaseController,
) -> SimulationResult:
    return IntersectionSimulation(intersection, simulation, controller).run()


def _jain_index(values: list[float]) -> float:
    if not values or not any(values):
        return 1.0
    numerator = sum(values) ** 2
    denominator = len(values) * sum(value**2 for value in values)
    return numerator / denominator if denominator else 1.0
