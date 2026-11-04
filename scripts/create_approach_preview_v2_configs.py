"""Конфигурации Approach Preview v2: факторный дизайн A/B/C/D с причинным датчиком.

Факторы (политика × информация), все арки при одинаковом регламенте и одних и тех же
потоках прибытий (парность по seed):

* A — Detector-based Vehicle-actuated, датчика подъезда нет;
* B — тот же Vehicle-actuated, использует причинный датчик (продление и call-ahead);
* C — rollout-контроллер без датчика (прибытия — историческая интенсивность либо нули);
* D — тот же rollout-контроллер с причинным датчиком.

Регламент для всех: жёлтый 3 с, max-green 45 с, потеря времени на старт зелёного 2 с,
интервал насыщенного потока 2 с, min-green — исследовательская сетка 4/6/8 с (не норматив).
Параметры политик подбираются только на development (seed 31101–31120); validation —
seed 32101–32130; final — seed 33101–33130 и запускается один раз после заморозки.

Использование::

    python scripts/create_approach_preview_v2_configs.py --stage development
    python scripts/create_approach_preview_v2_configs.py --stage validation
    python scripts/create_approach_preview_v2_configs.py --stage final
"""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = "outputs/approach_preview_v2"
SEEDS = {
    "development": list(range(31101, 31121)),
    "validation": list(range(32101, 32131)),
    "final": list(range(33101, 33131)),
}
PRIMARY_MIN_GREEN = 6
MIN_GREEN_GRID = (4, 6, 8)
YELLOW = 3
MAX_GREEN = 45
STARTUP_LOSS = 2.0
SERVICE = 2.0
HORIZON = 1800

# Пресеты датчика: параметры закреплены до анализа, sensitivity — отдельные пресеты.
SENSOR_PRESETS: dict[str, dict] = {
    "camera_nominal": {
        "preview_seconds": 10.0, "sensor_model": "causal",
        "sensor_detection_distance_m": 100.0, "sensor_mean_speed_mps": 10.0,
        "sensor_speed_cv": 0.2, "sensor_profile_sd": 0.3,
        "sensor_frame_period_seconds": 0.5, "sensor_latency_seconds": 0.3,
        "sensor_position_noise_m": 1.0, "sensor_speed_noise_mps": 0.5,
        "preview_detection_probability": 0.95,
        "sensor_dropout_start_probability": 0.02, "sensor_dropout_mean_frames": 3.0,
        "sensor_false_positive_rate_per_minute": 0.5,
        "sensor_duplicate_track_probability": 0.02,
    },
    "camera_good": {
        "preview_seconds": 10.0, "sensor_model": "causal",
        "sensor_detection_distance_m": 100.0, "sensor_mean_speed_mps": 10.0,
        "sensor_speed_cv": 0.2, "sensor_profile_sd": 0.3,
        "sensor_frame_period_seconds": 0.25, "sensor_latency_seconds": 0.1,
        "sensor_position_noise_m": 0.5, "sensor_speed_noise_mps": 0.25,
        "preview_detection_probability": 1.0,
    },
    "camera_degraded": {
        "preview_seconds": 10.0, "sensor_model": "causal",
        "sensor_detection_distance_m": 100.0, "sensor_mean_speed_mps": 10.0,
        "sensor_speed_cv": 0.2, "sensor_profile_sd": 0.3,
        "sensor_frame_period_seconds": 0.5, "sensor_latency_seconds": 0.8,
        "sensor_position_noise_m": 2.0, "sensor_speed_noise_mps": 1.0,
        "preview_detection_probability": 0.8,
        "sensor_dropout_start_probability": 0.05, "sensor_dropout_mean_frames": 4.0,
        "sensor_false_positive_rate_per_minute": 2.0,
        "sensor_duplicate_track_probability": 0.05,
        "sensor_eta_bias_seconds": 0.5,
    },
    "oracle_upper_bound": {"preview_seconds": 10.0, "sensor_model": "oracle"},
}

LANES = ("north", "south", "east", "west")


def _lanes(north: float, south: float, east: float, west: float) -> dict:
    return {
        "north": {"arrival_rate_per_minute": north}, "south": {"arrival_rate_per_minute": south},
        "east": {"arrival_rate_per_minute": east}, "west": {"arrival_rate_per_minute": west},
    }


def scenario_catalog(min_green: int) -> list[dict]:
    def base(name: str, title: str, lanes: dict, **extra) -> dict:
        return {
            "name": name, "title": title, "description": extra.pop("description", title),
            "intersection": {"lanes": lanes, "min_green_seconds": min_green, "yellow_seconds": YELLOW},
            **extra,
        }

    return [
        base("symmetric_low", "Симметричный низкий спрос, 3/мин", _lanes(3, 3, 3, 3)),
        base("symmetric_mid", "Симметричный спрос, 6/мин", _lanes(6, 6, 6, 6)),
        base("symmetric_9", "Симметричный спрос, 9/мин", _lanes(9, 9, 9, 9)),
        base("asymmetric_ns", "Асимметрия Север–Юг: 10 против 4", _lanes(10, 10, 4, 4)),
        base("asymmetric_low_ew", "Слабый поперечный поток: 8 против 2", _lanes(8, 8, 2, 2)),
        base(
            "sudden_switch", "Смена доминирующей оси на 900 с", _lanes(6.5, 6.5, 6.5, 6.5),
            demand_schedule=[
                {"start_seconds": 0, "end_seconds": 900, "lanes": _lanes(10, 10, 3, 3)},
                {"start_seconds": 900, "end_seconds": 1800, "lanes": _lanes(3, 3, 10, 10)},
            ],
        ),
        base(
            "platoon_mid", "Пачки по 4 автомобиля, средний 6/мин", _lanes(6, 6, 6, 6),
            arrival_process="platoon", platoon_mean_size=4.0, platoon_headway_seconds=1.8,
        ),
        base(
            "bursty_shared_axis", "Всплески, общие для оси, средний 6/мин", _lanes(6, 6, 6, 6),
            arrival_process="bursty", burst_high_factor=2.5, burst_low_factor=0.2,
            burst_mean_state_seconds=40.0, burst_shared_axis=True,
        ),
        base("initial_queue", "Начальная очередь по 6 на подходе, 5/мин", _lanes(5, 5, 5, 5),
             initial_queues={"north": 6, "south": 6, "east": 6, "west": 6}),
        base("capacity_boundary", "Граница ёмкости, 12/мин", _lanes(12, 12, 12, 12)),
        base("oversaturated", "Перегрузка, 18/мин", _lanes(18, 18, 18, 18)),
    ]


SUBSET_SCENARIOS = ("symmetric_mid", "asymmetric_ns", "platoon_mid", "bursty_shared_axis",
                    "capacity_boundary")
OVERLOAD_SCENARIOS = ("capacity_boundary", "oversaturated")


def _dva(min_green: int, gap: float, *, preview: bool, extension: float = 3.0, name: str = "") -> dict:
    return {
        "type": "detector_vehicle_actuated", "min_green_seconds": min_green,
        "max_green_seconds": MAX_GREEN, "passage_gap_seconds": gap, "use_preview": preview,
        "extension_eta_seconds": extension, "call_ahead_seconds": 3.0, "result_name": name,
    }


def _roll(min_green: int, continuation: int, future: str, name: str) -> dict:
    return {
        "type": "queue_based_approach_preview", "min_green_seconds": min_green,
        "max_green_seconds": MAX_GREEN, "planning_horizon_seconds": 50,
        "max_switch_delay_seconds": 24, "continuation_min_green_seconds": continuation,
        "future_arrivals": future, "eta_rounding": "floor", "result_name": name,
    }


def grid_controllers(min_green: int) -> dict[str, list[dict]]:
    gaps = (0.0, 2.0, 3.0, 4.0)  # интервал 1 с совпадает с 2 с на односекундном такте
    extensions = (2.0, 4.0)
    continuations = sorted({min_green, 8})
    futures = ("zero", "historical_rate")
    return {
        "A": [_dva(min_green, g, preview=False, name=f"A_dva_g{g:g}") for g in gaps],
        "B": [
            _dva(min_green, g, preview=True, extension=e, name=f"B_dva_pv_g{g:g}_e{e:g}")
            for g in gaps for e in extensions
        ],
        "C": [
            _roll(min_green, c, f, f"C_roll_c{c}_{'zero' if f == 'zero' else 'hist'}")
            for c in continuations for f in futures
        ],
        "D": [
            _roll(min_green, c, f, f"D_roll_pv_c{c}_{'zero' if f == 'zero' else 'hist'}")
            for c in continuations for f in futures
        ],
    }


def selected_controllers(min_green: int) -> dict[str, dict]:
    """Контроллеры arm A–D, выбранные на development (файл development_selection.json)."""
    path = ROOT / OUT_DIR / "development_selection.json"
    selection = json.loads(path.read_text(encoding="utf-8"))[f"min_green_{min_green}"]
    grid = grid_controllers(min_green)
    chosen = {}
    for arm in "ABCD":
        names = {item["result_name"]: item for item in grid[arm]}
        chosen[arm] = deepcopy(names[selection[arm]])
    return chosen


def _experiment(
    name: str, title: str, description: str, *, stage: str, scenarios: list[dict],
    controllers: list[dict], sensor: dict | None, seeds: list[int] | None = None,
    duration: int = HORIZON,
) -> dict:
    simulation = {
        "duration_seconds": duration,
        "seeds": seeds or SEEDS[stage],
        "service_time_seconds": SERVICE,
        "startup_lost_time_seconds": STARTUP_LOSS,
        "arrival_rate_tau_seconds": 120.0,
        "store_queue_series": False,
    }
    simulation.update(sensor or {})
    return {
        "name": name, "title": title, "description": description, "simulation": simulation,
        "scenarios": deepcopy(scenarios), "controllers": deepcopy(controllers),
        "output": {
            "path": f"{OUT_DIR}/{name}.json",
            "summary_csv": f"{OUT_DIR}/{name}_summary.csv",
            "report_markdown": f"{OUT_DIR}/{name}_report.md",
        },
    }


def factorial_experiments(stage: str, min_green: int = PRIMARY_MIN_GREEN) -> list[dict]:
    """Файлы основной серии: arms A/C без датчика и B/D с причинным датчиком (nominal)."""
    scenarios = scenario_catalog(min_green)
    prefix = f"approach_preview_v2_{stage}_m{min_green}"
    if stage == "development":
        grid = grid_controllers(min_green)
        blind = grid["A"] + grid["C"]
        sensed = grid["B"] + grid["D"]
    else:
        chosen = selected_controllers(min_green)
        references = [
            {"type": "vehicle_actuated", "min_green_seconds": min_green, "max_green_seconds": MAX_GREEN,
             "gap_seconds": 2.0, "result_name": "ref_va_proxy_gap2"},
            {"type": "queue_based_improved", "min_green_seconds": min_green, "max_green_seconds": MAX_GREEN,
             "switching_margin": 1, "relative_switching_margin": 0.2, "congested_min_green_seconds": 25,
             "congestion_queue_threshold": 14, "result_name": "ref_queue_based_improved"},
        ]
        blind = [chosen["A"], chosen["C"], *references]
        sensed = [chosen["B"], chosen["D"]]
    return [
        _experiment(
            f"{prefix}_nosensor", f"Approach Preview v2 ({stage}, m={min_green}): без датчика",
            "Arms A и C: информации о подъезжающих автомобилях нет.",
            stage=stage, scenarios=scenarios, controllers=blind, sensor=None,
        ),
        _experiment(
            f"{prefix}_camera_nominal", f"Approach Preview v2 ({stage}, m={min_green}): причинный датчик",
            "Arms B и D: причинный датчик camera_nominal.",
            stage=stage, scenarios=scenarios, controllers=sensed, sensor=SENSOR_PRESETS["camera_nominal"],
        ),
    ]


def sensitivity_experiments(stage: str, min_green: int = PRIMARY_MIN_GREEN) -> list[dict]:
    """Только validation/final: пресеты датчика, дальность, задержка, отказ датчика."""
    chosen = selected_controllers(min_green)
    sensed = [chosen["B"], chosen["D"]]
    all_scenarios = scenario_catalog(min_green)
    subset = [s for s in all_scenarios if s["name"] in SUBSET_SCENARIOS]
    prefix = f"approach_preview_v2_{stage}_m{min_green}"
    experiments = []
    for preset in ("camera_good", "camera_degraded", "oracle_upper_bound"):
        experiments.append(
            _experiment(
                f"{prefix}_{preset}", f"Approach Preview v2 ({stage}): датчик {preset}",
                "Чувствительность к качеству датчика; oracle — теоретическая верхняя граница.",
                stage=stage, scenarios=all_scenarios, controllers=sensed, sensor=SENSOR_PRESETS[preset],
            )
        )
    nominal = SENSOR_PRESETS["camera_nominal"]
    sweeps = {
        "distance60": {"sensor_detection_distance_m": 60.0},
        "distance150": {"sensor_detection_distance_m": 150.0},
        "latency1": {"sensor_latency_seconds": 1.0},
        "latency2": {"sensor_latency_seconds": 2.0},
        "outage": {"sensor_outage_windows": [[600.0, 720.0], [1200.0, 1260.0]]},
    }
    for key, change in sweeps.items():
        experiments.append(
            _experiment(
                f"{prefix}_sweep_{key}", f"Approach Preview v2 ({stage}): чувствительность {key}",
                "Одно изменение относительно camera_nominal.",
                stage=stage, scenarios=subset, controllers=sensed, sensor={**nominal, **change},
            )
        )
    return experiments


def long_horizon_experiments(stage: str, min_green: int = PRIMARY_MIN_GREEN) -> list[dict]:
    chosen = selected_controllers(min_green)
    subset = [s for s in scenario_catalog(min_green) if s["name"] in SUBSET_SCENARIOS + ("oversaturated",)]
    prefix = f"approach_preview_v2_{stage}_m{min_green}_3600"
    return [
        _experiment(
            f"{prefix}_nosensor", f"Approach Preview v2 ({stage}): горизонт 3600 с, без датчика",
            "Arms A и C, горизонт 3600 с.", stage=stage, scenarios=subset,
            controllers=[chosen["A"], chosen["C"]], sensor=None, duration=3600,
        ),
        _experiment(
            f"{prefix}_camera_nominal", f"Approach Preview v2 ({stage}): горизонт 3600 с, датчик",
            "Arms B и D, горизонт 3600 с.", stage=stage, scenarios=subset,
            controllers=[chosen["B"], chosen["D"]], sensor=SENSOR_PRESETS["camera_nominal"], duration=3600,
        ),
    ]


def write(experiments: list[dict]) -> None:
    for experiment in experiments:
        path = ROOT / "configs" / f"{experiment['name']}.yaml"
        path.write_text(yaml.safe_dump(experiment, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=tuple(SEEDS), required=True)
    parser.add_argument("--min-greens", type=int, nargs="+", default=None)
    args = parser.parse_args()
    if args.stage == "development":
        for m in args.min_greens or MIN_GREEN_GRID:
            write(factorial_experiments("development", m))
        return
    for m in args.min_greens or [PRIMARY_MIN_GREEN]:
        write(factorial_experiments(args.stage, m))
    primary = PRIMARY_MIN_GREEN
    write(sensitivity_experiments(args.stage, primary))
    write(long_horizon_experiments(args.stage, primary))


if __name__ == "__main__":
    main()
