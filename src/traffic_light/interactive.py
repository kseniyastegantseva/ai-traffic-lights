from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

from traffic_light.config import (
    IntersectionConfig,
    LaneName,
    PhaseName,
    SimulationConfig,
    TrafficDemandConfig,
)
from traffic_light.controllers import QueueBasedController
from traffic_light.simulation import IntersectionSimulation

SignalColor = Literal["red", "yellow", "green"]

LANES: tuple[LaneName, ...] = ("north", "west", "south", "east")


@dataclass(frozen=True)
class LoadScenario:
    code: str
    title: str
    description: str


@dataclass(frozen=True)
class InteractiveFrame:
    second: int
    signals: dict[PhaseName, SignalColor]
    queues: dict[LaneName, int]
    departed: int
    departed_by_lane: dict[LaneName, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PhaseInterval:
    axis: PhaseName
    color: SignalColor
    started_at: int
    ended_at: int

    @property
    def duration_seconds(self) -> int:
        return self.ended_at - self.started_at


@dataclass(frozen=True)
class InteractiveSimulationResult:
    initial_queues: dict[LaneName, int]
    scenario: LoadScenario
    frames: list[InteractiveFrame]
    phases: list[PhaseInterval]
    total_time_seconds: int
    departed: int
    switches: int
    north_south_green_seconds: int
    east_west_green_seconds: int


def classify_load(queues: dict[LaneName, int]) -> LoadScenario:
    total = sum(queues.values())
    north_south = queues["north"] + queues["south"]
    east_west = queues["east"] + queues["west"]

    if total == 0:
        return LoadScenario("empty", "Движение отсутствует", "Все подходы свободны.")
    if total >= 60:
        return LoadScenario(
            "high_load",
            "Большая начальная очередь",
            "На снимке много автомобилей; один снимок не определяет насыщение потока.",
        )
    if north_south >= east_west * 1.5 and north_south - east_west >= 4:
        return LoadScenario(
            "north_south_peak",
            "Пиковая нагрузка север-юг",
            "Основной поток движется между северным и южным подходами.",
        )
    if east_west >= north_south * 1.5 and east_west - north_south >= 4:
        return LoadScenario(
            "east_west_peak",
            "Пиковая нагрузка запад-восток",
            "Основной поток движется между западным и восточным подходами.",
        )
    if total <= 16:
        return LoadScenario(
            "low_load",
            "Низкая нагрузка",
            "Небольшая очередь без выраженного доминирующего направления.",
        )
    return LoadScenario(
        "uniform",
        "Равномерная нагрузка",
        "Поток распределён между обеими осями перекрёстка.",
    )


def simulate_interactive_traffic(
    initial_queues: dict[LaneName, int],
    *,
    min_green_seconds: int = 8,
    max_green_seconds: int = 30,
    yellow_seconds: int = 3,
    service_time_seconds: int = 2,
) -> InteractiveSimulationResult:
    queues = {lane: max(0, int(initial_queues.get(lane, 0))) for lane in LANES}
    initial = queues.copy()
    total = sum(queues.values())
    scenario = classify_load(queues)
    if total == 0:
        frame = InteractiveFrame(
            0,
            {"north_south": "red", "east_west": "red"},
            queues.copy(),
            0,
            {lane: 0 for lane in LANES},
        )
        return InteractiveSimulationResult(initial, scenario, [frame], [], 0, 0, 0, 0, 0)

    initial_phase = _heavier_phase(queues)
    intersection = IntersectionConfig(
        lanes={lane: TrafficDemandConfig(arrival_rate_per_minute=0) for lane in LANES},
        min_green_seconds=min_green_seconds,
        yellow_seconds=yellow_seconds,
    )
    horizon = int(
        total * service_time_seconds
        + 2 * yellow_seconds * (total // max_green_seconds + 2)
        + max_green_seconds
        + 10
    )
    if horizon > 7200:
        raise RuntimeError("Интерактивная симуляция превысила ограничение в два часа.")
    trace: list[dict] = []
    simulation = SimulationConfig(
        duration_seconds=max(1, horizon),
        seed=0,
        service_time_seconds=service_time_seconds,
    )
    controller = QueueBasedController(
        min_green_seconds=min_green_seconds,
        max_green_seconds=max_green_seconds,
        switching_margin=1,
    )
    sim_result = IntersectionSimulation(
        intersection,
        simulation,
        controller,
        initial_queues=queues,
        arrivals=[],
        initial_phase=initial_phase,
        trace_callback=trace.append,
    ).run()
    clear_index = next(
        (
            index
            for index, frame in enumerate(trace)
            if frame["departed"] == total and not any(frame["queues"].values())
        ),
        None,
    )
    if clear_index is None:
        raise RuntimeError("Интерактивная симуляция не очистила начальные очереди.")

    frames = [
        InteractiveFrame(
            second=frame["second"],
            signals=frame["signals"],
            queues=frame["queues"],
            departed=frame["departed"],
            departed_by_lane=frame["departed_by_lane"],
        )
        for frame in trace[: clear_index + 1]
    ]
    last = frames[-1]
    for offset in range(1, 6):
        frames.append(
            InteractiveFrame(
                second=last.second + offset,
                signals=last.signals.copy(),
                queues=last.queues.copy(),
                departed=last.departed,
                departed_by_lane=last.departed_by_lane.copy(),
            )
        )
    second = frames[-1].second + 1

    raw_intervals: list[tuple[PhaseName, SignalColor, int]] = []
    for frame in frames:
        active_axis = next(
            (axis for axis, color in frame.signals.items() if color != "red"),
            None,
        )
        if active_axis is None:
            continue
        active_color = frame.signals[active_axis]
        if not raw_intervals or raw_intervals[-1][:2] != (active_axis, active_color):
            raw_intervals.append((active_axis, active_color, frame.second))
    phases = _build_intervals(raw_intervals, second)
    switches = sum(interval.color == "yellow" for interval in phases)
    north_south_green = sum(
        interval.duration_seconds
        for interval in phases
        if interval.axis == "north_south" and interval.color == "green"
    )
    east_west_green = sum(
        interval.duration_seconds
        for interval in phases
        if interval.axis == "east_west" and interval.color == "green"
    )
    return InteractiveSimulationResult(
        initial_queues=initial,
        scenario=scenario,
        frames=frames,
        phases=phases,
        total_time_seconds=second,
        departed=sim_result.vehicles_departed,
        switches=switches,
        north_south_green_seconds=north_south_green,
        east_west_green_seconds=east_west_green,
    )


def _heavier_phase(queues: dict[LaneName, int]) -> PhaseName:
    north_south = queues["north"] + queues["south"]
    east_west = queues["east"] + queues["west"]
    return "north_south" if north_south >= east_west else "east_west"


def _build_intervals(
    raw_intervals: list[tuple[PhaseName, SignalColor, int]], total_time_seconds: int
) -> list[PhaseInterval]:
    intervals = []
    for index, (axis, color, started_at) in enumerate(raw_intervals):
        ended_at = (
            raw_intervals[index + 1][2]
            if index + 1 < len(raw_intervals)
            else total_time_seconds
        )
        intervals.append(PhaseInterval(axis, color, started_at, ended_at))
    return intervals


def _signal_states(
    active_axis: PhaseName, active_color: SignalColor
) -> dict[PhaseName, SignalColor]:
    other_axis: PhaseName = "east_west" if active_axis == "north_south" else "north_south"
    return {active_axis: active_color, other_axis: "red"}
