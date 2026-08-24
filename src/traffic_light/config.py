from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

LaneName = Literal["north", "south", "east", "west"]
PhaseName = Literal["north_south", "east_west"]
ControllerType = Literal["fixed", "actuated", "ai", "q_learning"]


class TrafficDemandConfig(BaseModel):
    arrival_rate_per_minute: float = Field(ge=0)


class IntersectionConfig(BaseModel):
    lanes: dict[LaneName, TrafficDemandConfig]
    min_green_seconds: int = Field(default=15, ge=1)
    yellow_seconds: int = Field(default=3, ge=0)


class SimulationConfig(BaseModel):
    duration_seconds: int = Field(default=900, ge=1)
    seed: int = 42
    service_time_seconds: float = Field(default=2.0, gt=0)


class ControllerConfig(BaseModel):
    type: ControllerType
    phase_duration_seconds: int = Field(default=35, ge=1)
    decision_interval_seconds: int = Field(default=10, ge=1)
    policy_path: str = "outputs/q_learning_policy.json"


class RunConfig(BaseModel):
    simulation: SimulationConfig
    intersection: IntersectionConfig
    controller: ControllerConfig
    output: dict[str, str] = Field(default_factory=dict)


class ExperimentSimulationConfig(BaseModel):
    duration_seconds: int = Field(default=900, ge=1)
    seeds: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])
    service_time_seconds: float = Field(default=2.0, gt=0)


class ScenarioConfig(BaseModel):
    name: str
    title: str
    description: str = ""
    intersection: IntersectionConfig


class ExperimentConfig(BaseModel):
    name: str = "experiment"
    title: str = "Эксперимент"
    description: str = ""
    simulation: ExperimentSimulationConfig
    intersection: IntersectionConfig | None = None
    scenarios: list[ScenarioConfig] | None = None
    controllers: list[ControllerConfig]
    output: dict[str, str] = Field(default_factory=dict)


def load_yaml(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_run_config(path: str | Path) -> RunConfig:
    return RunConfig.model_validate(load_yaml(path))


def load_experiment_config(path: str | Path) -> ExperimentConfig:
    return ExperimentConfig.model_validate(load_yaml(path))
