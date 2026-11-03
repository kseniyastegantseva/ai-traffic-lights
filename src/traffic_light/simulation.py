from __future__ import annotations

import hashlib
import random
from collections import deque
from collections.abc import Callable
from dataclasses import asdict, dataclass
from statistics import mean, median

import simpy

from traffic_light.config import DemandPeriodConfig, IntersectionConfig, PhaseName, SimulationConfig
from traffic_light.controllers import PHASE_LANES, BaseController, ControllerState

LANES = ("north", "south", "east", "west")


@dataclass(frozen=True)
class Vehicle:
    lane: str
    arrived_at: float


@dataclass(frozen=True)
class Arrival:
    at: float
    lane: str


def generate_arrivals(
    intersection: IntersectionConfig,
    simulation: SimulationConfig,
    demand_schedule: list[DemandPeriodConfig] | None = None,
) -> list[Arrival]:
    """Generate one immutable set of Poisson arrivals, shared by controller runs."""
    events: list[Arrival] = []
    for lane_index, lane in enumerate(LANES):
        rng = random.Random(simulation.seed + 104729 * (lane_index + 1))
        periods = demand_schedule or []
        if not periods:
            periods = [
                DemandPeriodConfig(
                    start_seconds=0,
                    end_seconds=simulation.duration_seconds,
                    lanes=intersection.lanes,
                )
            ]
        for period in sorted(periods, key=lambda item: item.start_seconds):
            start = max(0.0, float(period.start_seconds))
            end = min(float(simulation.duration_seconds), float(period.end_seconds))
            rate_config = period.lanes.get(lane)
            rate = rate_config.arrival_rate_per_minute if rate_config else 0.0
            if rate <= 0 or end <= start:
                continue
            now = start
            while True:
                now += rng.expovariate(rate / 60.0)
                if now >= end:
                    break
                events.append(Arrival(now, lane))
    return sorted(events, key=lambda event: (event.at, LANES.index(event.lane)))


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
    max_queue_length: int
    stops: int
    fairness_index: float
    lane_waits: dict[str, float]
    queue_series: list[int]
    initial_vehicles: int = 0
    waiting_at_end: int = 0
    in_service_at_end: int = 0
    observed_delay_seconds: float = 0.0
    phase_history: list[dict] | None = None
    arrival_stream_sha256: str = ""
    observation_error_rate: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class IntersectionSimulation:
    """SimPy model with half-open horizon [0, duration_seconds).

    A vehicle joins its queue at its arrival timestamp. A green signal may start
    service; each started vehicle occupies the server for service_time_seconds
    and departs at completion, including when yellow starts in between. Queue
    samples use integer-second left endpoints. Simultaneous arrivals are added
    before service starts; at integer ties, phase decisions run before a new
    service starts. Departures at the horizon are not counted.
    Initial vehicles are present at t=0; their pre-observation delay is unknown
    and is excluded from waiting-time estimates.
    """

    def __init__(
        self,
        intersection: IntersectionConfig,
        simulation: SimulationConfig,
        controller: BaseController,
        initial_queues: dict[str, int] | None = None,
        arrivals: list[Arrival] | None = None,
        initial_phase: PhaseName = "north_south",
        trace_callback: Callable[[dict], None] | None = None,
    ) -> None:
        self.intersection = intersection
        self.config = simulation
        self.controller = controller
        self.trace_callback = trace_callback
        self.env = simpy.Environment()
        self._service_wakeups = {lane: self.env.event() for lane in LANES}
        self.current_phase: PhaseName = initial_phase
        self.signal_color = "green"
        self.phase_history: list[dict] = [{"at": 0.0, "phase": initial_phase, "color": "green"}]
        self.phase_started_at = 0.0
        self.queues: dict[str, deque[Vehicle]] = {
            lane: deque() for lane in intersection.lanes
        }
        self.initial_vehicles = 0
        for lane, count in (initial_queues or {}).items():
            if lane not in self.queues or count < 0:
                raise ValueError(f"Invalid initial queue for {lane}: {count}")
            self.queues[lane].extend(Vehicle(lane, 0.0) for _ in range(count))
            self.initial_vehicles += count
        arrival_events = arrivals if arrivals is not None else generate_arrivals(intersection, simulation)
        if any(
            event.lane not in self.queues
            or event.at < 0
            or event.at >= simulation.duration_seconds
            for event in arrival_events
        ):
            raise ValueError("Arrival events must use a valid lane and lie inside [0, duration_seconds).")
        self.arrivals = sorted(arrival_events, key=lambda event: (event.at, LANES.index(event.lane)))
        stream_text = "\n".join(f"{float(event.at).hex()},{event.lane}" for event in self.arrivals)
        self.arrival_stream_sha256 = hashlib.sha256(stream_text.encode("utf-8")).hexdigest()
        self.last_observed_request_at: dict[str, float] = {lane: 0.0 for lane in LANES}
        self.waits: list[float] = []
        self.waits_by_lane: dict[str, list[float]] = {lane: [] for lane in intersection.lanes}
        self.queue_samples: list[int] = []
        self.arrived = 0
        for event in self.arrivals:
            if event.at == 0:
                self.queues[event.lane].append(Vehicle(event.lane, 0.0))
                self.arrived += 1
        self._initial_queue_counts = {lane: len(queue) for lane, queue in self.queues.items()}
        self.departed = 0
        self.departed_by_lane = {lane: 0 for lane in LANES}
        self.in_service = 0
        self.in_service_by_lane = {lane: 0 for lane in LANES}
        self.stops = 0
        self._last_event_time = 0.0
        self._queue_area = 0.0
        self._max_queue = self.initial_vehicles
        self._observed_delay = 0.0

    def run(self) -> SimulationResult:
        self.env.process(self._control())
        self.env.process(self._arrival_process())
        self.env.process(self._service("north"))
        self.env.process(self._service("south"))
        self.env.process(self._service("east"))
        self.env.process(self._service("west"))
        self.env.process(self._sample_queues())
        self.env.run(until=self.config.duration_seconds)
        return self._result()

    def _arrival_process(self):
        for event in self.arrivals:
            if event.at == 0:
                continue
            delay = event.at - self.env.now
            if delay > 0:
                yield self.env.timeout(delay)
            self._integrate_queue_area()
            self.queues[event.lane].append(Vehicle(event.lane, event.at))
            self.arrived += 1
            self._max_queue = max(self._max_queue, self._queue_count())
            self._notify_services()

    def _service(self, lane: str):
        while True:
            if self.signal_color == "green" and lane in PHASE_LANES[self.current_phase] and self.queues[lane]:
                self._integrate_queue_area()
                vehicle = self.queues[lane].popleft()
                self.in_service += 1
                self.in_service_by_lane[lane] += 1
                wait = self.env.now - vehicle.arrived_at
                self._observed_delay += wait
                yield self.env.timeout(self.config.service_time_seconds)
                if self.env.now < self.config.duration_seconds:
                    self._integrate_queue_area()
                    self.in_service -= 1
                    self.in_service_by_lane[lane] -= 1
                    self.departed += 1
                    self.departed_by_lane[lane] += 1
                    self.waits.append(wait)
                    self.waits_by_lane[lane].append(wait)
                    self.stops += int(wait > 1)
                    if self.env.now > 0 and self.env.now % 1 == 0:
                        yield self.env.timeout(0)
                else:
                    return
            else:
                wakeup = self._service_wakeups[lane]
                yield wakeup

    def _control(self):
        while True:
            now = self.env.now
            if self.signal_color == "yellow":
                if now - self.phase_started_at >= self.intersection.yellow_seconds:
                    self.current_phase = "east_west" if self.current_phase == "north_south" else "north_south"
                    self.signal_color = "green"
                    self.phase_started_at = now
                    self.phase_history.append({"at": now, "phase": self.current_phase, "color": "green"})
                    self._notify_services()
            else:
                observed_queues = self._observed_queues(now)
                for lane, count in observed_queues.items():
                    if count:
                        self.last_observed_request_at[lane] = now
                state = ControllerState(
                    now=now,
                    current_phase=self.current_phase,
                    phase_started_at=self.phase_started_at,
                    queues=observed_queues,
                    current_gap_seconds=max(
                        0.0,
                        now
                        - max(
                            self.last_observed_request_at[lane]
                            for lane in PHASE_LANES[self.current_phase]
                        ),
                    ),
                )
                next_phase = self.controller.choose_phase(state)
                if next_phase != self.current_phase:
                    self.phase_started_at = now
                    if self.intersection.yellow_seconds:
                        self.signal_color = "yellow"
                        self.phase_history.append(
                            {"at": now, "phase": self.current_phase, "color": "yellow"}
                        )
                    else:
                        self.current_phase = next_phase
                        self.signal_color = "green"
                        self.phase_history.append({"at": now, "phase": self.current_phase, "color": "green"})
                    self._notify_services()
            yield self.env.timeout(1)

    def _sample_queues(self):
        while True:
            self._integrate_queue_area()
            self.queue_samples.append(self._queue_count())
            if self.trace_callback is not None:
                is_initial_snapshot = self.env.now == 0
                other_phase: PhaseName = (
                    "east_west" if self.current_phase == "north_south" else "north_south"
                )
                self.trace_callback(
                    {
                        "second": int(self.env.now),
                        "phase": self.phase_history[0]["phase"] if is_initial_snapshot else self.current_phase,
                        "color": "green" if is_initial_snapshot else self.signal_color,
                        "signals": {
                            self.phase_history[0]["phase"] if is_initial_snapshot else self.current_phase: (
                                "green" if is_initial_snapshot else self.signal_color
                            ),
                            other_phase: "red",
                        },
                        "queues": (
                            self._initial_queue_counts.copy()
                            if is_initial_snapshot
                            else {lane: len(queue) for lane, queue in self.queues.items()}
                        ),
                        "departed": 0 if is_initial_snapshot else self.departed,
                        "departed_by_lane": (
                            {lane: 0 for lane in LANES}
                            if is_initial_snapshot
                            else self.departed_by_lane.copy()
                        ),
                        "in_service_by_lane": self.in_service_by_lane.copy(),
                    }
                )
            yield self.env.timeout(1)

    def _queue_count(self) -> int:
        return sum(map(len, self.queues.values()))

    def _notify_services(self) -> None:
        for lane, wakeup in self._service_wakeups.items():
            if not wakeup.triggered:
                wakeup.succeed()
            self._service_wakeups[lane] = self.env.event()

    def _observed_queues(self, now: float) -> dict[str, int]:
        error_rate = self.config.observation_error_rate
        observed: dict[str, int] = {}
        for lane_index, lane in enumerate(LANES):
            seed = self.config.seed + int(now * 10) * 1009 + lane_index * 9176
            profile = self.config.empirical_observation_errors_by_lane.get(lane, [])
            empirical_rng = random.Random(seed + 65537)
            empirical_error = empirical_rng.choice(profile) if profile else 0
            rng = random.Random(seed)
            count = 0
            for _ in self.queues[lane]:
                draw = rng.random()
                if draw < error_rate / 2:
                    continue
                count += 2 if draw < error_rate else 1
            observed[lane] = max(0, count + empirical_error)
        return observed

    def _integrate_queue_area(self):
        now = min(float(self.env.now), float(self.config.duration_seconds))
        if now > self._last_event_time:
            self._queue_area += self._queue_count() * (now - self._last_event_time)
            self._last_event_time = now

    def _result(self) -> SimulationResult:
        self._integrate_queue_area()
        duration = self.config.duration_seconds
        lane_waits = {lane: mean(waits) if waits else 0.0 for lane, waits in self.waits_by_lane.items()}
        waiting = self._queue_count()
        self._observed_delay += sum(
            duration - vehicle.arrived_at
            for queue in self.queues.values()
            for vehicle in queue
        )
        assert self.initial_vehicles + self.arrived == self.departed + waiting + self.in_service
        return SimulationResult(
            controller=self.controller.name,
            seed=self.config.seed,
            duration_seconds=duration,
            vehicles_arrived=self.arrived,
            vehicles_departed=self.departed,
            throughput_per_hour=self.departed * 3600 / duration,
            average_wait_seconds=mean(self.waits) if self.waits else 0.0,
            median_wait_seconds=median(self.waits) if self.waits else 0.0,
            max_wait_seconds=max(self.waits) if self.waits else 0.0,
            average_queue_length=self._queue_area / duration,
            max_queue_length=self._max_queue,
            stops=self.stops,
            fairness_index=_jain_index(list(lane_waits.values())),
            lane_waits=lane_waits,
            queue_series=self.queue_samples,
            initial_vehicles=self.initial_vehicles,
            waiting_at_end=waiting,
            in_service_at_end=self.in_service,
            observed_delay_seconds=self._observed_delay,
            phase_history=self.phase_history,
            arrival_stream_sha256=self.arrival_stream_sha256,
            observation_error_rate=self.config.observation_error_rate,
        )


def run_simulation(
    intersection: IntersectionConfig,
    simulation: SimulationConfig,
    controller: BaseController,
    initial_queues: dict[str, int] | None = None,
    arrivals: list[Arrival] | None = None,
    initial_phase: PhaseName = "north_south",
    trace_callback: Callable[[dict], None] | None = None,
) -> SimulationResult:
    return IntersectionSimulation(
        intersection,
        simulation,
        controller,
        initial_queues,
        arrivals,
        initial_phase,
        trace_callback,
    ).run()


def _jain_index(values: list[float]) -> float:
    if not values or not any(values):
        return 1.0
    numerator = sum(values) ** 2
    denominator = len(values) * sum(value**2 for value in values)
    return numerator / denominator if denominator else 1.0
