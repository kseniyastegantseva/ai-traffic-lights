"""Создать seed-явные конфигурации исследования управления с датчиком подъезда.

Development: seed 12101–12130, подбор параметров Vehicle-actuated и Improved,
сравнение с rollout-контроллером `queue_based_approach_preview` при идеальном и
ухудшенном датчике подъезда.
"""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_SEEDS = list(range(12101, 12131))
VALIDATION_SEEDS = list(range(13101, 13131))
SCENARIOS = (
    "symmetric_low",
    "symmetric",
    "symmetric_9",
    "asymmetric_ns",
    "asymmetric_ew",
    "sudden_dominance_switch",
    "high_load",
    "true_oversaturated",
)
OUTPUT_DIR = "outputs/approach_preview"


def _va(min_green: int, gap: float) -> dict:
    return {
        "type": "vehicle_actuated",
        "min_green_seconds": min_green,
        "max_green_seconds": 45,
        "gap_seconds": gap,
        "result_name": f"va_min{min_green}_gap{gap:g}",
    }


def _improved(min_green: int) -> dict:
    return {
        "type": "queue_based_improved",
        "min_green_seconds": min_green,
        "max_green_seconds": 45,
        "switching_margin": 1,
        "relative_switching_margin": 0.2,
        "congested_min_green_seconds": 25,
        "congestion_queue_threshold": 14,
        "result_name": f"imp20_min{min_green}",
    }


def _preview_controller(name: str, min_green: int = 4) -> dict:
    return {
        "type": "queue_based_approach_preview",
        "min_green_seconds": min_green,
        "max_green_seconds": 45,
        "planning_horizon_seconds": 50,
        "max_switch_delay_seconds": 24,
        "continuation_min_green_seconds": 8,
        "result_name": name,
    }


def _experiment(
    source: dict, name: str, title: str, description: str, controllers: list[dict],
    *, seeds: list[int], preview: dict | None = None,
) -> dict:
    simulation = {
        "duration_seconds": 1800,
        "seeds": seeds,
        "service_time_seconds": 2.0,
        "store_queue_series": False,
    }
    simulation.update(preview or {})
    scenarios = [deepcopy(s) for s in source["scenarios"] if s["name"] in SCENARIOS]
    if {s["name"] for s in scenarios} != set(SCENARIOS):
        raise ValueError("The source configuration is missing a requested scenario")
    return {
        "name": name,
        "title": title,
        "description": description,
        "simulation": simulation,
        "scenarios": scenarios,
        "controllers": controllers,
        "output": {
            "path": f"{OUTPUT_DIR}/{name}.json",
            "summary_csv": f"{OUTPUT_DIR}/{name}_summary.csv",
            "report_markdown": f"{OUTPUT_DIR}/{name}_report.md",
        },
    }


def _parse_va(name: str) -> dict:
    _, minimum, gap = name.split("_")
    return _va(int(minimum.removeprefix("min")), float(gap.removeprefix("gap")))


def validation_experiments(source: dict, preview_min_green: int) -> list[dict]:
    """Независимая проверка: выбор baseline берётся из development_selection.json."""
    selection = json.loads(
        (ROOT / OUTPUT_DIR / "development_selection.json").read_text(encoding="utf-8")
    )
    tuned_va = _parse_va(selection["vehicle_actuated"])
    tuned_imp = _improved(int(selection["improved"].removeprefix("imp20_min")))
    blind = _preview_controller(f"preview_none_min{preview_min_green}", preview_min_green)
    experiments = [
        _experiment(
            source,
            "approach_preview_baselines_val_1800",
            "Проверка: baseline и rollout без датчика, validation 1800 с",
            "Seed 13101–13130, заранее выбранные на development настройки.",
            [_va(8, 3.0), tuned_va, tuned_imp, blind],
            seeds=VALIDATION_SEEDS,
        )
    ]
    sensors = {
        "ideal10": {"preview_seconds": 10.0},
        "degraded10": {
            "preview_seconds": 10.0,
            "preview_detection_probability": 0.8,
            "preview_time_jitter_seconds": 1.0,
        },
    }
    for key, preview in sensors.items():
        experiments.append(
            _experiment(
                source,
                f"approach_preview_{key}_min{preview_min_green}_val_1800",
                f"Проверка: датчик подъезда {key}, validation 1800 с",
                "Seed 13101–13130; тот же настроенный Vehicle-actuated как anchor.",
                [deepcopy(tuned_va),
                 _preview_controller(f"preview_{key}_min{preview_min_green}", preview_min_green)],
                seeds=VALIDATION_SEEDS,
                preview=preview,
            )
        )
    return experiments


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validation", action="store_true")
    parser.add_argument("--preview-min-green", type=int, default=2)
    args = parser.parse_args()
    source = yaml.safe_load(
        (ROOT / "configs/queue_based_final_1800.yaml").read_text(encoding="utf-8")
    )
    if args.validation:
        for experiment in validation_experiments(source, args.preview_min_green):
            path = ROOT / "configs" / f"{experiment['name']}.yaml"
            path.write_text(
                yaml.safe_dump(experiment, allow_unicode=True, sort_keys=False), encoding="utf-8"
            )
            print(f"wrote {path.relative_to(ROOT)}")
        return
    baselines = [_va(8, 3.0)]
    baselines += [_va(m, g) for m in (2, 4, 6) for g in (1.0, 2.0)]
    baselines += [_improved(m) for m in (8, 4, 2)]
    baselines.append(_preview_controller("preview_none"))
    anchor = _va(4, 1.0)

    experiments = [
        _experiment(
            source,
            "approach_preview_baselines_dev_1800",
            "Настройка baseline и rollout без датчика подъезда, development 1800 с",
            "Seed 12101–12130. Сетка min-green/gap для Vehicle-actuated, Improved с margin 0,20 "
            "и rollout-контроллер без датчика подъезда (preview_none).",
            baselines,
            seeds=DEVELOPMENT_SEEDS,
        ),
    ]
    sensors = {
        "ideal5": ({"preview_seconds": 5.0}, "идеальный датчик, окно 5 с"),
        "ideal10": ({"preview_seconds": 10.0}, "идеальный датчик, окно 10 с"),
        "degraded10": (
            {
                "preview_seconds": 10.0,
                "preview_detection_probability": 0.8,
                "preview_time_jitter_seconds": 1.0,
            },
            "ухудшенный датчик: окно 10 с, обнаружение 80%, погрешность времени σ=1 с",
        ),
    }
    for key, (preview, label) in sensors.items():
        experiments.append(
            _experiment(
                source,
                f"approach_preview_{key}_dev_1800",
                f"Управление с датчиком подъезда: {label}, development 1800 с",
                "Seed 12101–12130; те же потоки прибытий, что в baseline-серии. "
                "Для парности включён anchor Vehicle-actuated 4 с / gap 1 с.",
                [deepcopy(anchor), _preview_controller(f"preview_{key}")],
                seeds=DEVELOPMENT_SEEDS,
                preview=preview,
            )
        )
    # Второй раунд development: лучший Vehicle-actuated оказался на краю сетки (min 2 с,
    # gap 1 с), поэтому сетка расширена, а rollout-контроллеру дан тот же минимальный зелёный.
    extra_baselines = [_va(m, g) for m, g in ((1, 0.0), (1, 0.5), (1, 1.0), (2, 0.0), (2, 0.5))]
    extra_baselines.append(_improved(1))
    experiments.append(
        _experiment(
            source,
            "approach_preview_baselines2_dev_1800",
            "Расширенная настройка baseline, development 1800 с",
            "Seed 12101–12130. Расширение сетки Vehicle-actuated (min 1–2 с, gap 0–1 с) и Improved (min 1 с).",
            extra_baselines,
            seeds=DEVELOPMENT_SEEDS,
        )
    )
    for key in ("ideal10", "degraded10"):
        preview, label = sensors[key]
        experiments.append(
            _experiment(
                source,
                f"approach_preview_{key}_min2_dev_1800",
                f"Управление с датчиком подъезда, минимум зелёного 2 с: {label}, development 1800 с",
                "Seed 12101–12130; тот же минимальный зелёный 2 с, что у лучшего Vehicle-actuated.",
                [deepcopy(anchor), _preview_controller(f"preview_{key}_min2", min_green=2)],
                seeds=DEVELOPMENT_SEEDS,
                preview=preview,
            )
        )
    for experiment in experiments:
        path = ROOT / "configs" / f"{experiment['name']}.yaml"
        path.write_text(
            yaml.safe_dump(experiment, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
