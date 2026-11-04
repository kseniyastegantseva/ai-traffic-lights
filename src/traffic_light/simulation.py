from __future__ import annotations

import bisect
import hashlib
import math
import random
from collections import deque
from collections.abc import Callable
from dataclasses import asdict, dataclass
from statistics import mean, median

import simpy

from traffic_light.config import DemandPeriodConfig, IntersectionConfig, PhaseName, SimulationConfig
from traffic_light.controllers import PHASE_LANES, BaseController, ControllerState, other_phase
from traffic_light.sensor import SensorParams, build_feed

LANES = ("north", "south", "east", "west")


@dataclass(frozen=True)
class Vehicle:
    lane: str
    arrived_at: float


@dataclass(frozen=True)
class Arrival:
    at: float
    lane: str


def _poisson_count(rng: random.Random, mean: float) -> int:
    limit, product, count = math.exp(-mean), 1.0, 0
    while True:
        product *= rng.random()
        if product <= limit:
            return count
        count += 1


def _modulation_path(
    rng: random.Random, start: float, end: float, process: dict
) -> list[tuple[float, float, float]]:
    """Двухсостояний MMPP: список (начало, конец, множитель) с сохранением средней интенсивности."""
    high, low = process["burst_high_factor"], process["burst_low_factor"]
    mean_factor = (high + low) / 2.0
    path: list[tuple[float, float, float]] = []
    now, state_high = start, rng.random() < 0.5
    while now < end:
        length = rng.expovariate(1.0 / process["burst_mean_state_seconds"])
        stop = min(end, now + length)
        path.append((now, stop, (high if state_high else low) / mean_factor))
        now, state_high = stop, not state_high
    return path


def _non_poisson_arrivals(
    simulation: SimulationConfig, periods: list[DemandPeriodConfig], process: dict
) -> list[Arrival]:
    events: list[Arrival] = []
    kind = process["arrival_process"]
    axis_paths: dict[tuple[str, int], list[tuple[float, float, float]]] = {}
    for lane_index, lane in enumerate(LANES):
        rng = random.Random(f"{simulation.seed}:{lane}:{kind}:arrivals")
        for period_index, period in enumerate(sorted(periods, key=lambda item: item.start_seconds)):
            start = max(0.0, float(period.start_seconds))
            end = min(float(simulation.duration_seconds), float(period.end_seconds))
            rate_config = period.lanes.get(lane)
            rate = rate_config.arrival_rate_per_minute / 60.0 if rate_config else 0.0
            if rate <= 0 or end <= start:
                continue
            if kind == "platoon":
                mean_size = process["platoon_mean_size"]
                now = start
                while True:
                    now += rng.expovariate(rate / mean_size)
                    if now >= end:
                        break
                    size = 1 + _poisson_count(rng, mean_size - 1.0)
                    at = now
                    for _ in range(size):
                        if at < end:
                            events.append(Arrival(at, lane))
                        at += process["platoon_headway_seconds"] * rng.uniform(0.8, 1.2)
            else:  # bursty
                if process["burst_shared_axis"]:
                    axis = 0 if lane in PHASE_LANES["north_south"] else 1
                    key = (str(axis), period_index)
                    if key not in axis_paths:
                        axis_rng = random.Random(f"{simulation.seed}:axis{axis}:burst-state")
                        axis_paths[key] = _modulation_path(axis_rng, start, end, process)
                    path = axis_paths[key]
                else:
                    path = _modulation_path(rng, start, end, process)
                for seg_start, seg_end, factor in path:
                    segment_rate = rate * factor
                    if segment_rate <= 0:
                        continue
                    now = seg_start
                    while True:
                        now += rng.expovariate(segment_rate)
                        if now >= seg_end:
                            break
                        events.append(Arrival(now, lane))
    return events


def generate_arrivals(
    intersection: IntersectionConfig,
    simulation: SimulationConfig,
    demand_schedule: list[DemandPeriodConfig] | None = None,
    process: dict | None = None,
) -> list[Arrival]:
    """Generate one immutable arrival stream, shared by controller runs.

    По умолчанию — пуассоновский поток (побитово как в прежних сериях). ``process`` с ключом
    ``arrival_process`` ``platoon``/``bursty`` включает пачки или модулированный поток.
    """
    if process and process.get("arrival_process", "poisson") != "poisson":
        periods = demand_schedule or [
            DemandPeriodConfig(
                start_seconds=0, end_seconds=simulation.duration_seconds, lanes=intersection.lanes
            )
        ]
        events = _non_poisson_arrivals(simulation, periods, process)
        return sorted(events, key=lambda event: (event.at, LANES.index(event.lane)))
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
    max_red_with_queue_seconds_by_phase: dict[PhaseName, float] | None = None
    # Метрики без цензурирования и физические инварианты (результат schema v3).
    queue_area_vehicle_seconds: float = 0.0
    observed_delay_per_vehicle_seconds: float = 0.0
    p95_wait_seconds: float = 0.0
    phase_switches: int = 0
    yellow_seconds_total: float = 0.0
    all_red_seconds_total: float = 0.0
    green_idle_seconds: float = 0.0
    vehicle_balance_error: int = 0
    sensor_model: str = "none"
    sensor_unavailable_seconds: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class IntersectionSimulation:
    """SimPy model with half-open horizon [0, duration_seconds).

    A vehicle joins its queue at its arrival timestamp. A green signal may start
    service; each started vehicle occupies the server for service_time_seconds
    and departs at completion, including when yellow starts in between. Queue
    samples use integer-second left endpoints. Startup lost time delays service
    starts only until the phase's startup deadline; saturation headway remains
    service_time_seconds. Simultaneous arrivals are added
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
        self._pending_phase: PhaseName | None = None
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
        self._causal_feed = None
        self._preview_times: list[float] = []
        self._preview_events: list[tuple[float, float, str]] = []
        if simulation.preview_seconds > 0 and simulation.sensor_model == "causal":
            self._causal_feed = build_feed(
                self.arrivals, SensorParams.from_config(simulation), float(simulation.duration_seconds)
            )
        elif simulation.sensor_model == "oracle":
            self._preview_times, self._preview_events = self._build_preview_events()
        self.sensor_unavailable_seconds = 0.0
        self.last_actuation_at: dict[str, float] = {lane: 0.0 for lane in LANES}
        self._service_finish_at: dict[str, float | None] = {lane: None for lane in LANES}
        self._arrival_times_by_lane: dict[str, list[float]] = {
            lane: [event.at for event in self.arrivals if event.lane == lane and event.at > 0]
            for lane in LANES
        }
        self._rate_estimate: dict[str, float] = {lane: 0.0 for lane in LANES}
        self._green_idle_seconds = 0.0
        self.waits: list[float] = []
        self.waits_by_lane: dict[str, list[float]] = {lane: [] for lane in intersection.lanes}
        self.queue_samples: list[int] = []
        self.arrived = 0
        for event in self.arrivals:
            if event.at == 0:
                self.queues[event.lane].append(Vehicle(event.lane, 0.0))
                self.arrived += 1
        self._initial_queue_counts = {lane: len(queue) for lane, queue in self.queues.items()}
        initial_red_phase = other_phase(initial_phase)
        self.red_request_started_at: dict[PhaseName, float] = (
            {initial_red_phase: 0.0}
            if sum(self._initial_queue_counts[lane] for lane in PHASE_LANES[initial_red_phase]) > 0
            else {}
        )
        self.red_queue_since: dict[PhaseName, float] = (
            {initial_red_phase: 0.0}
            if sum(self._initial_queue_counts[lane] for lane in PHASE_LANES[initial_red_phase]) > 0
            else {}
        )
        self.max_red_with_queue_seconds_by_phase: dict[PhaseName, float] = {
            phase: 0.0 for phase in PHASE_LANES
        }
        self.departed = 0
        self.departed_by_lane = {lane: 0 for lane in LANES}
        self.in_service = 0
        self.in_service_by_lane = {lane: 0 for lane in LANES}
        self.stops = 0
        self._last_event_time = 0.0
        self._queue_area = 0.0
        # Include both supplied initial queues and arrivals preloaded at t=0.
        self._max_queue = self._queue_count()
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
            arrival_phase = "north_south" if event.lane in PHASE_LANES["north_south"] else "east_west"
            if self.signal_color == "all_red":
                self.red_queue_since.setdefault(arrival_phase, event.at)
                self.red_request_started_at.setdefault(arrival_phase, event.at)
            elif arrival_phase != self.current_phase:
                self.red_queue_since.setdefault(arrival_phase, event.at)
            self.arrived += 1
            self.last_actuation_at[event.lane] = event.at
            self._max_queue = max(self._max_queue, self._queue_count())
            self._notify_services()

    def _service(self, lane: str):
        while True:
            if self.signal_color == "green" and lane in PHASE_LANES[self.current_phase] and self.queues[lane]:
                startup_ready_at = self.phase_started_at + self.config.startup_lost_time_seconds
                if self.env.now < startup_ready_at:
                    yield self.env.timeout(startup_ready_at - self.env.now)
                    continue
                self._integrate_queue_area()
                vehicle = self.queues[lane].popleft()
                self.in_service += 1
                self.in_service_by_lane[lane] += 1
                self.last_actuation_at[lane] = self.env.now
                self._service_finish_at[lane] = self.env.now + self.config.service_time_seconds
                wait = self.env.now - vehicle.arrived_at
                self._observed_delay += wait
                yield self.env.timeout(self.config.service_time_seconds)
                self._service_finish_at[lane] = None
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
                    self._pending_phase = other_phase(self.current_phase)
                    if self.in_service:
                        self._enter_all_red(now)
                    else:
                        self._activate_pending_phase(now)
            elif self.signal_color == "all_red":
                if self.in_service == 0:
                    self._activate_pending_phase(now)
            else:
                observed_queues = self._observed_queues(now)
                for lane, count in observed_queues.items():
                    if count:
                        self.last_observed_request_at[lane] = now
                red_phase = other_phase(self.current_phase)
                red_queue = sum(observed_queues[lane] for lane in PHASE_LANES[red_phase])
                if red_queue > 0:
                    self.red_request_started_at.setdefault(red_phase, now)
                else:
                    self.red_request_started_at.pop(red_phase, None)
                self.red_request_started_at.pop(self.current_phase, None)
                preview_offsets, preview_status = self._sensor_snapshot(now)
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
                    red_request_elapsed_seconds={
                        phase: now - started_at
                        for phase, started_at in self.red_request_started_at.items()
                    },
                    yellow_seconds=self.intersection.yellow_seconds,
                    service_seconds=self.config.service_time_seconds,
                    in_service_by_lane=self.in_service_by_lane.copy(),
                    upcoming_arrival_offsets=preview_offsets,
                    startup_lost_seconds=self.config.startup_lost_time_seconds,
                    service_remaining_by_lane={
                        lane: (max(0.0, finish - now) if finish is not None else 0.0)
                        for lane, finish in self._service_finish_at.items()
                    },
                    detector_gap_seconds=max(
                        0.0,
                        now - max(self.last_actuation_at[lane] for lane in PHASE_LANES[self.current_phase]),
                    ),
                    preview_status=preview_status,
                    preview_window_seconds=self.config.preview_seconds,
                    arrival_rate_per_second_by_lane=self._update_rate_estimate(now),
                )
                next_phase = self.controller.choose_phase(state)
                if next_phase != self.current_phase:
                    self.phase_started_at = now
                    self._pending_phase = next_phase
                    if self.intersection.yellow_seconds:
                        self.signal_color = "yellow"
                        self.phase_history.append(
                            {"at": now, "phase": self.current_phase, "color": "yellow"}
                        )
                    elif self.in_service:
                        self._enter_all_red(now)
                    else:
                        self._activate_pending_phase(now)
                    self._notify_services()
            yield self.env.timeout(1)

    def _build_preview_events(self) -> tuple[list[float], list[tuple[float, float, str]]]:
        """События: (истинное время прибытия, прогнозное время, полоса).

        Обнаружение и погрешность времени фиксируются для каждой машины отдельно и не зависят
        от остальных генераторов случайных чисел, поэтому потоки прибытий и прочие метрики
        не меняются при включении датчика.
        """
        if self.config.preview_seconds <= 0:
            return [], []
        events: list[tuple[float, float, str]] = []
        for index, event in enumerate(self.arrivals):
            if event.at <= 0:
                continue
            rng = random.Random(f"{self.config.seed}:{index}:preview")
            if rng.random() >= self.config.preview_detection_probability:
                continue
            jitter = rng.gauss(0.0, self.config.preview_time_jitter_seconds) if (
                self.config.preview_time_jitter_seconds > 0
            ) else 0.0
            events.append((event.at, event.at + jitter, event.lane))
        events.sort()
        return [item[0] for item in events], events

    def _sensor_snapshot(self, now: float) -> tuple[dict[str, list[float]] | None, str | None]:
        """Единственный путь данных датчика к контроллеру."""
        if self.config.preview_seconds <= 0:
            return None, None
        if self._causal_feed is not None:
            view = self._causal_feed.view(now)
            return view.offsets, view.status
        return self._upcoming_arrival_offsets(now), "ok"

    def _update_rate_estimate(self, now: float) -> dict[str, float] | None:
        tau = self.config.arrival_rate_tau_seconds
        if tau <= 0:
            return None
        alpha = 1.0 / tau
        for lane in LANES:
            times = self._arrival_times_by_lane[lane]
            # События строго до now: уже произошедшие и наблюдённые, без будущего.
            count = bisect.bisect_left(times, now) - bisect.bisect_left(times, now - 1.0)
            self._rate_estimate[lane] += alpha * (count - self._rate_estimate[lane])
        return self._rate_estimate.copy()

    def _upcoming_arrival_offsets(self, now: float) -> dict[str, list[float]] | None:
        if self.config.preview_seconds <= 0:
            return None
        offsets: dict[str, list[float]] = {lane: [] for lane in LANES}
        end = now + self.config.preview_seconds
        index = bisect.bisect_right(self._preview_times, now)
        while index < len(self._preview_events) and self._preview_events[index][0] < end:
            actual_at, predicted_at, lane = self._preview_events[index]
            if actual_at > now:
                # Просроченный прогноз остаётся видимым до наблюдаемого прибытия.
                offsets[lane].append(max(0.0, predicted_at - now))
            index += 1
        return offsets

    def _activate_pending_phase(self, now: float) -> None:
        next_phase = self._pending_phase
        if next_phase is None:
            raise RuntimeError("Cannot activate a phase without a pending transition.")
        previous_phase = self.current_phase
        red_started = self.red_queue_since.pop(next_phase, None)
        if red_started is not None:
            self.max_red_with_queue_seconds_by_phase[next_phase] = max(
                self.max_red_with_queue_seconds_by_phase[next_phase], now - red_started
            )
        if sum(len(self.queues[lane]) for lane in PHASE_LANES[previous_phase]) > 0:
            self.red_queue_since.setdefault(previous_phase, now)
        else:
            self.red_queue_since.pop(previous_phase, None)
        self.red_request_started_at.pop(next_phase, None)
        if sum(len(self.queues[lane]) for lane in PHASE_LANES[previous_phase]) > 0:
            self.red_request_started_at.setdefault(previous_phase, now)
        else:
            self.red_request_started_at.pop(previous_phase, None)
        self.current_phase = next_phase
        self._pending_phase = None
        self.signal_color = "green"
        self.phase_started_at = now
        self.phase_history.append({"at": now, "phase": self.current_phase, "color": "green"})
        self._notify_services()

    def _enter_all_red(self, now: float) -> None:
        self.signal_color = "all_red"
        self.phase_started_at = now
        for phase, lanes in PHASE_LANES.items():
            if sum(len(self.queues[lane]) for lane in lanes) > 0:
                self.red_queue_since.setdefault(phase, now)
                self.red_request_started_at.setdefault(phase, now)
        self.phase_history.append({"at": now, "phase": self.current_phase, "color": "all_red"})

    def _sample_queues(self):
        while True:
            self._integrate_queue_area()
            if self._causal_feed is not None and self._causal_feed.status(self.env.now) != "ok":
                self.sensor_unavailable_seconds += 1.0
            if self.signal_color == "green" and not any(
                self.queues[lane] or self.in_service_by_lane[lane]
                for lane in PHASE_LANES[self.current_phase]
            ):
                self._green_idle_seconds += 1.0
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
                        "signals": (
                            {
                                "north_south": "red",
                                "east_west": "red",
                            }
                            if not is_initial_snapshot and self.signal_color == "all_red"
                            else {
                                self.phase_history[0]["phase"] if is_initial_snapshot else self.current_phase: (
                                    "green" if is_initial_snapshot else self.signal_color
                                ),
                                other_phase: "red",
                            }
                        ),
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
        max_red_with_queue = self.max_red_with_queue_seconds_by_phase.copy()
        for phase, started_at in self.red_queue_since.items():
            max_red_with_queue[phase] = max(max_red_with_queue[phase], duration - started_at)
        self._observed_delay += sum(
            duration - vehicle.arrived_at
            for queue in self.queues.values()
            for vehicle in queue
        )
        balance_error = self.initial_vehicles + self.arrived - (
            self.departed + waiting + self.in_service
        )
        assert balance_error == 0
        yellow_total = all_red_total = 0.0
        for index, item in enumerate(self.phase_history):
            stop = (
                self.phase_history[index + 1]["at"]
                if index + 1 < len(self.phase_history)
                else float(duration)
            )
            if item["color"] == "yellow":
                yellow_total += stop - item["at"]
            elif item["color"] == "all_red":
                all_red_total += stop - item["at"]
        sorted_waits = sorted(self.waits)
        p95 = sorted_waits[max(0, math.ceil(0.95 * len(sorted_waits)) - 1)] if sorted_waits else 0.0
        total_vehicles = self.initial_vehicles + self.arrived
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
            max_red_with_queue_seconds_by_phase=max_red_with_queue,
            queue_area_vehicle_seconds=self._queue_area,
            observed_delay_per_vehicle_seconds=(
                self._observed_delay / total_vehicles if total_vehicles else 0.0
            ),
            p95_wait_seconds=p95,
            phase_switches=sum(1 for item in self.phase_history if item["color"] == "yellow")
            or sum(
                1
                for index, item in enumerate(self.phase_history[1:], start=1)
                if item["color"] == "green" and item["phase"] != self.phase_history[index - 1]["phase"]
            ),
            yellow_seconds_total=yellow_total,
            all_red_seconds_total=all_red_total,
            green_idle_seconds=self._green_idle_seconds,
            vehicle_balance_error=balance_error,
            sensor_model=(
                "none" if self.config.preview_seconds <= 0 else self.config.sensor_model
            ),
            sensor_unavailable_seconds=self.sensor_unavailable_seconds,
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
