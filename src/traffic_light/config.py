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
    "queue_based_smooth_min_green", "queue_based_hysteresis", "queue_based_persistent_congestion",
    "queue_based_axis_specific_congestion",
    "queue_based_elapsed_margin", "queue_based_approach_preview",
    "detector_vehicle_actuated",
    "actuated", "ai", "q_learning",
]
SensorModel = Literal["oracle", "causal"]
ArrivalProcess = Literal["poisson", "platoon", "bursty"]


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
    startup_lost_time_seconds: float = Field(default=0.0, ge=0.0)
    observation_error_rate: float = Field(default=0.0, ge=0.0, le=0.2)
    empirical_observation_errors_by_lane: dict[LaneName, list[int]] = Field(default_factory=dict)
    # Датчик подъезжающих автомобилей (камера/детектор выше по потоку). Ноль — датчика нет.
    preview_seconds: float = Field(default=0.0, ge=0.0)
    preview_detection_probability: float = Field(default=1.0, ge=0.0, le=1.0)
    preview_time_jitter_seconds: float = Field(default=0.0, ge=0.0)
    # oracle — теоретическая верхняя граница: окно и ETA берутся из скрытого Arrival.at.
    # causal — наблюдения из скрытых траекторий с задержкой, шумом и сбоями (traffic_light.sensor).
    sensor_model: SensorModel = "oracle"
    sensor_detection_distance_m: float = Field(default=100.0, gt=0.0)
    sensor_mean_speed_mps: float = Field(default=10.0, gt=0.0)
    sensor_speed_cv: float = Field(default=0.2, ge=0.0, le=0.6)
    sensor_profile_sd: float = Field(default=0.3, ge=0.0, le=0.8)
    sensor_frame_period_seconds: float = Field(default=0.5, gt=0.0)
    sensor_latency_seconds: float = Field(default=0.3, ge=0.0)
    sensor_position_noise_m: float = Field(default=1.0, ge=0.0)
    sensor_speed_noise_mps: float = Field(default=0.5, ge=0.0)
    sensor_eta_bias_seconds: float = 0.0
    sensor_min_speed_mps: float = Field(default=1.0, gt=0.0)
    sensor_track_timeout_seconds: float = Field(default=2.0, gt=0.0)
    sensor_watchdog_seconds: float = Field(default=2.0, gt=0.0)
    sensor_dropout_start_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    sensor_dropout_mean_frames: float = Field(default=3.0, ge=1.0)
    sensor_false_positive_rate_per_minute: float = Field(default=0.0, ge=0.0)
    sensor_duplicate_track_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    sensor_outage_windows: list[tuple[float, float]] = Field(default_factory=list)
    # Оценка интенсивности прибытий по ранее наблюдённым событиям (EWMA) для прогноза за окном.
    arrival_rate_tau_seconds: float = Field(default=0.0, ge=0.0)


class ControllerConfig(BaseModel):
    type: ControllerType
    phase_duration_seconds: int = Field(default=35, ge=1)
    decision_interval_seconds: int = Field(default=10, ge=1)
    min_green_seconds: int = Field(default=8, ge=1)
    max_green_seconds: int = Field(default=45, ge=1)
    gap_seconds: float = Field(default=3.0, ge=0.0)
    planning_horizon_seconds: int = Field(default=50, ge=5)
    max_switch_delay_seconds: int = Field(default=24, ge=0)
    continuation_min_green_seconds: int = Field(default=8, ge=1)
    # Rollout: прогноз прибытий за пределами окна датчика ("zero" — нулевые, "historical_rate" — EWMA).
    future_arrivals: Literal["zero", "historical_rate"] = "zero"
    # Округление ETA до такта rollout: floor (прежнее), round, ceil.
    eta_rounding: Literal["floor", "round", "ceil"] = "floor"
    # Детерминированный бюджет вычислений (число шагов rollout); None — без ограничения.
    max_work_units: int | None = Field(default=None, ge=1)
    # Detector-based Vehicle-actuated.
    passage_gap_seconds: float = Field(default=2.0, ge=0.0)
    use_preview: bool = False
    extension_eta_seconds: float = Field(default=3.0, ge=0.0)
    call_ahead_seconds: float = Field(default=3.0, ge=0.0)
    switching_margin: int = Field(default=1, ge=0)
    relative_switching_margin: float = Field(default=0.10, ge=0.0, le=1.0)
    congested_min_green_seconds: int = Field(default=20, ge=1)
    congestion_queue_threshold: int = Field(default=10, ge=0)
    empty_gap_seconds: float = Field(default=1.0, ge=0.0)
    max_red_seconds: float = Field(default=48.0, gt=0.0)
    smooth_congestion_start_queue: int = Field(default=10, ge=0)
    smooth_congestion_end_queue: int = Field(default=18, ge=1)
    congestion_exit_threshold: int = Field(default=10, ge=0)
    congestion_persistence_seconds: float = Field(default=5.0, ge=0.0)
    switching_margin_decay_per_second: float = Field(default=0.025, ge=0.0)
    minimum_switching_margin: int = Field(default=1, ge=1)
    result_name: str | None = None
    legacy_rule: bool = False
    policy_path: str = "outputs/q_learning_policy.json"

    @model_validator(mode="after")
    def validate_green_bounds(self):
        if self.max_green_seconds < self.min_green_seconds:
            raise ValueError("max_green_seconds must be greater than or equal to min_green_seconds")
        if (
            self.type in {
                "queue_based_improved",
                "queue_based_max_red",
                "queue_based_smooth_min_green",
                "queue_based_hysteresis",
                "queue_based_persistent_congestion",
                "queue_based_axis_specific_congestion",
                "queue_based_elapsed_margin",
            }
            and self.max_green_seconds < self.congested_min_green_seconds
        ):
            raise ValueError(
                "max_green_seconds must be greater than or equal to congested_min_green_seconds"
            )
        if (
            self.type == "queue_based_smooth_min_green"
            and self.smooth_congestion_end_queue <= self.smooth_congestion_start_queue
        ):
            raise ValueError("smooth_congestion_end_queue must exceed smooth_congestion_start_queue")
        if (
            self.type == "queue_based_hysteresis"
            and self.congestion_exit_threshold >= self.congestion_queue_threshold
        ):
            raise ValueError("congestion_exit_threshold must be below congestion_queue_threshold")
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
    startup_lost_time_seconds: float = Field(default=0.0, ge=0.0)
    empirical_observation_errors_by_lane: dict[LaneName, list[int]] = Field(default_factory=dict)
    preview_seconds: float = Field(default=0.0, ge=0.0)
    preview_detection_probability: float = Field(default=1.0, ge=0.0, le=1.0)
    preview_time_jitter_seconds: float = Field(default=0.0, ge=0.0)
    # oracle — теоретическая верхняя граница: окно и ETA берутся из скрытого Arrival.at.
    # causal — наблюдения из скрытых траекторий с задержкой, шумом и сбоями (traffic_light.sensor).
    sensor_model: SensorModel = "oracle"
    sensor_detection_distance_m: float = Field(default=100.0, gt=0.0)
    sensor_mean_speed_mps: float = Field(default=10.0, gt=0.0)
    sensor_speed_cv: float = Field(default=0.2, ge=0.0, le=0.6)
    sensor_profile_sd: float = Field(default=0.3, ge=0.0, le=0.8)
    sensor_frame_period_seconds: float = Field(default=0.5, gt=0.0)
    sensor_latency_seconds: float = Field(default=0.3, ge=0.0)
    sensor_position_noise_m: float = Field(default=1.0, ge=0.0)
    sensor_speed_noise_mps: float = Field(default=0.5, ge=0.0)
    sensor_eta_bias_seconds: float = 0.0
    sensor_min_speed_mps: float = Field(default=1.0, gt=0.0)
    sensor_track_timeout_seconds: float = Field(default=2.0, gt=0.0)
    sensor_watchdog_seconds: float = Field(default=2.0, gt=0.0)
    sensor_dropout_start_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    sensor_dropout_mean_frames: float = Field(default=3.0, ge=1.0)
    sensor_false_positive_rate_per_minute: float = Field(default=0.0, ge=0.0)
    sensor_duplicate_track_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    sensor_outage_windows: list[tuple[float, float]] = Field(default_factory=list)
    # Оценка интенсивности прибытий по ранее наблюдённым событиям (EWMA) для прогноза за окном.
    arrival_rate_tau_seconds: float = Field(default=0.0, ge=0.0)
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
    # Процесс прибытий; по умолчанию пуассоновский (потоки прежних серий не меняются).
    arrival_process: ArrivalProcess = "poisson"
    platoon_mean_size: float = Field(default=4.0, ge=1.0)
    platoon_headway_seconds: float = Field(default=1.8, gt=0.0)
    burst_high_factor: float = Field(default=2.5, ge=1.0)
    burst_low_factor: float = Field(default=0.2, ge=0.0, le=1.0)
    burst_mean_state_seconds: float = Field(default=40.0, gt=0.0)
    burst_shared_axis: bool = False


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
