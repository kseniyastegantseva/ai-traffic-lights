from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

LaneName = Literal["north", "south", "east", "west"]
PhaseName = Literal["north_south", "east_west"]
ControllerType = Literal[
    "fixed", "fixed_8", "fixed_15", "fixed_35", "fixed_webster", "vehicle_actuated",
    "queue_based", "queue_based_improved", "queue_based_empty_gap_fix", "queue_based_max_red",
    "actuated", "ai", "q_learning",
]


class TrafficDemandConfig(BaseModel):
    arrival_rate_per_minute: float = Field(ge=0)


class IntersectionConfig(BaseModel):
    lanes: dict[LaneName, TrafficDemandConfig]
    min_green_seconds: int = Field(default=15, ge=1)
    yellow_seconds: int = Field(default=3, ge=0)

    @model_validator(mode="after")
    def require_four_approaches(self):
        if set(self.lanes) != {"north", "south", "east", "west"}:
            raise ValueError("IntersectionConfig must define north, south, east, and west lanes")
        return self


class SimulationConfig(BaseModel):
    duration_seconds: int = Field(default=900, ge=1)
    seed: int = 42
    service_time_seconds: float = Field(default=2.0, gt=0)
    observation_error_rate: float = Field(default=0.0, ge=0.0, le=0.2)
    empirical_observation_errors_by_lane: dict[LaneName, list[int]] = Field(default_factory=dict)


class ControllerConfig(BaseModel):
    type: ControllerType
    phase_duration_seconds: int = Field(default=35, ge=1)
    decision_interval_seconds: int = Field(default=10, ge=1)
    min_green_seconds: int = Field(default=8, ge=1)
    max_green_seconds: int = Field(default=45, ge=1)
    switching_margin: int = Field(default=1, ge=0)
    relative_switching_margin: float = Field(default=0.10, ge=0.0, le=1.0)
    congested_min_green_seconds: int = Field(default=20, ge=1)
    congestion_queue_threshold: int = Field(default=10, ge=0)
    empty_gap_seconds: float = Field(default=1.0, ge=0.0)
    max_red_seconds: float = Field(default=48.0, gt=0.0)
    result_name: str | None = None
    legacy_rule: bool = False
    policy_path: str = "outputs/q_learning_policy.json"

    @model_validator(mode="after")
    def validate_green_bounds(self):
        if self.max_green_seconds < self.min_green_seconds:
            raise ValueError("max_green_seconds must be greater than or equal to min_green_seconds")
        if (
            self.type in {"queue_based_improved", "queue_based_max_red"}
            and self.max_green_seconds < self.congested_min_green_seconds
        ):
            raise ValueError(
                "max_green_seconds must be greater than or equal to congested_min_green_seconds"
            )
        return self


class RunConfig(BaseModel):
    simulation: SimulationConfig
    intersection: IntersectionConfig
    controller: ControllerConfig
    output: dict[str, str] = Field(default_factory=dict)


class ExperimentSimulationConfig(BaseModel):
    duration_seconds: int = Field(default=900, ge=1)
    seeds: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])
    service_time_seconds: float = Field(default=2.0, gt=0)
    empirical_observation_errors_by_lane: dict[LaneName, list[int]] = Field(default_factory=dict)
    store_queue_series: bool = True


class DemandPeriodConfig(BaseModel):
    start_seconds: int = Field(ge=0)
    end_seconds: int = Field(ge=1)
    lanes: dict[LaneName, TrafficDemandConfig]


class ScenarioConfig(BaseModel):
    name: str
    title: str
    description: str = ""
    intersection: IntersectionConfig
    demand_schedule: list[DemandPeriodConfig] | None = None
    initial_queues: dict[LaneName, int] = Field(default_factory=dict)
    observation_error_rate: float = Field(default=0.0, ge=0.0, le=0.2)


class ExperimentConfig(BaseModel):
    name: str = "experiment"
    title: str = "Эксперимент"
    description: str = ""
    simulation: ExperimentSimulationConfig
    intersection: IntersectionConfig | None = None
    scenarios: list[ScenarioConfig] | None = None
    controllers: list[ControllerConfig]
    output: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_demand_schedules(self):
        for scenario in self.scenarios or []:
            periods = sorted(scenario.demand_schedule or [], key=lambda period: period.start_seconds)
            for index, period in enumerate(periods):
                if period.end_seconds <= period.start_seconds:
                    raise ValueError(f"Invalid demand period in scenario {scenario.name}")
                if index and period.start_seconds < periods[index - 1].end_seconds:
                    raise ValueError(f"Overlapping demand periods in scenario {scenario.name}")
        return self


def load_yaml(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_run_config(path: str | Path) -> RunConfig:
    return RunConfig.model_validate(load_yaml(path))


def load_experiment_config(path: str | Path) -> ExperimentConfig:
    return ExperimentConfig.model_validate(load_yaml(path))
