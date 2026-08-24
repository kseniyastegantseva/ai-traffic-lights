from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from traffic_light.config import LaneName, PhaseName

SignalColor = Literal["red", "yellow", "green"]

LANES: tuple[LaneName, ...] = ("north", "west", "south", "east")
PHASE_LANES: dict[PhaseName, tuple[LaneName, LaneName]] = {
    "north_south": ("north", "south"),
    "east_west": ("east", "west"),
}


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
            "oversaturated",
            "Перегруженный перекрёсток",
            "Высокая суммарная очередь: алгоритм ограничивает длительность фаз.",
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
        )
        return InteractiveSimulationResult(initial, scenario, [frame], [], 0, 0, 0, 0, 0)

    current_phase: PhaseName = _heavier_phase(queues)
    signal_color: SignalColor = "green"
    phase_started_at = 0
    yellow_started_at: int | None = None
    next_phase: PhaseName | None = None
    last_service_at = 0
    departed = 0
    switches = 0
    frames: list[InteractiveFrame] = []
    raw_intervals: list[tuple[PhaseName, SignalColor, int]] = [
        (current_phase, signal_color, 0)
    ]
    second = 0

    while sum(queues.values()) > 0:
        if signal_color == "yellow":
            if yellow_started_at is not None and second - yellow_started_at >= yellow_seconds:
                current_phase = next_phase or current_phase
                signal_color = "green"
                phase_started_at = second
                last_service_at = second - service_time_seconds
                raw_intervals.append((current_phase, signal_color, second))
        else:
            green_elapsed = second - phase_started_at
            preferred = _preferred_phase(queues, current_phase, green_elapsed, max_green_seconds)
            if preferred != current_phase and green_elapsed >= min_green_seconds:
                signal_color = "yellow"
                yellow_started_at = second
                next_phase = preferred
                switches += 1
                raw_intervals.append((current_phase, signal_color, second))

        if signal_color == "green" and second - last_service_at >= service_time_seconds:
            for lane in PHASE_LANES[current_phase]:
                if queues[lane] > 0:
                    queues[lane] -= 1
                    departed += 1
            last_service_at = second

        frames.append(
            InteractiveFrame(
                second,
                _signal_states(current_phase, signal_color),
                queues.copy(),
                departed,
            )
        )
        second += 1
        if second > 7200:
            raise RuntimeError("Интерактивная симуляция превысила ограничение в два часа.")

    phases = _build_intervals(raw_intervals, second)
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
        departed=departed,
        switches=switches,
        north_south_green_seconds=north_south_green,
        east_west_green_seconds=east_west_green,
    )


def _heavier_phase(queues: dict[LaneName, int]) -> PhaseName:
    north_south = queues["north"] + queues["south"]
    east_west = queues["east"] + queues["west"]
    return "north_south" if north_south >= east_west else "east_west"


def _preferred_phase(
    queues: dict[LaneName, int],
    current_phase: PhaseName,
    green_elapsed: int,
    max_green_seconds: int,
) -> PhaseName:
    other_phase: PhaseName = "east_west" if current_phase == "north_south" else "north_south"
    current_pressure = sum(queues[lane] for lane in PHASE_LANES[current_phase])
    other_pressure = sum(queues[lane] for lane in PHASE_LANES[other_phase])
    if other_pressure == 0:
        return current_phase
    if current_pressure == 0 or green_elapsed >= max_green_seconds:
        return other_phase
    return other_phase if other_pressure > current_pressure + 1 else current_phase


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
