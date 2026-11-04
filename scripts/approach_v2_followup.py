"""Отдельное exploratory-исследование: новая сетка B и ограничение красного.

Команды: prepare-dev, run-dev, select, prepare-eval, run-eval.
Старые final, FREEZE и исходный контроллер не изменяются.
"""
from __future__ import annotations

import gzip
import json
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from create_approach_preview_v2_configs import (
    SENSOR_PRESETS,
    _dva,
    _experiment,
    _roll,
    scenario_catalog,
)

from traffic_light import experiments
from traffic_light.config import ExperimentConfig
from traffic_light.controllers import PHASE_LANES, BaseController, other_phase

OUT = ROOT / "outputs/approach_preview_v2_followup"
SCENARIOS = ("symmetric_low", "symmetric_mid", "symmetric_9", "asymmetric_low_ew", "platoon_mid", "capacity_boundary", "oversaturated")
DEV_SEEDS = list(range(34101, 34107))
EVAL_SEEDS = list(range(35101, 35109))
original_builder = experiments.build_controller


class RedGuard(BaseController):
    """Форсирует запрос при достижении порога; clearance выполняет симулятор."""

    def __init__(self, inner, limit):
        self.inner, self.limit, self.name = inner, limit, inner.name

    def choose_phase(self, state):
        other = other_phase(state.current_phase)
        queued = sum(state.queues[lane] for lane in PHASE_LANES[other])
        age = (state.red_request_elapsed_seconds or {}).get(other, 0)
        if queued and age >= self.limit and state.now - state.phase_started_at >= self.inner.min_green_seconds:
            return other
        return self.inner.choose_phase(state)


def build(config, min_green_seconds, intersection=None):
    controller = original_builder(config, min_green_seconds, intersection)
    if config.result_name and config.result_name.startswith("D_guard"):
        controller = RedGuard(controller, float(config.result_name.removeprefix("D_guard")))
    return controller


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        f.write(data)


def config(stage, controllers, seeds, sensor):
    scenarios = [s for s in scenario_catalog(6) if s["name"] in SCENARIOS]
    cfg = _experiment("followup_" + stage, "Дополнительное исследование", "Новые seed, отдельный протокол",
                      stage="validation", scenarios=scenarios, controllers=controllers, sensor=sensor,
                      seeds=seeds)
    return cfg


def grid():
    return [_dva(6, gap, preview=True, extension=ext, name=f"B_g{gap}_e{ext}_c{call}")
            | {"call_ahead_seconds": call}
            for gap in (0, 1, 3) for ext in (0, 2, 4) for call in (0, 3)]


def run_chunk(scenario):
    experiments.build_controller = build
    conf = ExperimentConfig.model_validate(scenario)
    return experiments.run_experiment(conf)[0]


def run(stage):
    path = OUT / f"{stage}_config.yaml"
    target = OUT / f"{stage}_runs.json.gz"
    if target.exists():
        raise SystemExit(f"Результат уже существует: {target}")
    conf = yaml.safe_load(path.read_text(encoding="utf-8"))
    chunks = [dict(conf, scenarios=[scenario]) for scenario in conf["scenarios"]]
    with ProcessPoolExecutor(max_workers=7) as pool:
        runs = [row for chunk in pool.map(run_chunk, chunks) for row in chunk]
    with gzip.open(target, "xt", encoding="utf-8") as f:
        json.dump({"configuration": conf, "runs": runs}, f, ensure_ascii=False)
    print(stage, "runs", len(runs), flush=True)


def main():
    stage = sys.argv[1]
    OUT.mkdir(parents=True, exist_ok=True)
    if stage == "prepare-dev":
        cfg = config("dev", grid(), DEV_SEEDS, SENSOR_PRESETS["camera_nominal"])
        write_new(OUT / "dev_config.yaml", yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False))
    elif stage == "run-dev":
        run("dev")
    elif stage == "select":
        with gzip.open(OUT / "dev_runs.json.gz", "rt") as f:
            rows = json.load(f)["runs"]
        reference = "B_g0_e2_c3"
        score = {}
        for name in sorted({r["controller"] for r in rows}):
            ratios = []
            for scenario in SCENARIOS:
                vals = [r["queue_area_vehicle_seconds"] for r in rows if r["scenario"] == scenario and r["controller"] == name]
                ref = [r["queue_area_vehicle_seconds"] for r in rows if r["scenario"] == scenario and r["controller"] == reference]
                if len(vals) != len(DEV_SEEDS) or len(ref) != len(DEV_SEEDS):
                    raise ValueError("Неполная development-серия")
                ratios.append(statistics.mean(vals) / statistics.mean(ref))
            score[name] = statistics.mean(ratios)
        selected = min(score, key=lambda x: (score[x], x))
        write_new(OUT / "selection.json", json.dumps({"selected": selected, "scores": score}, indent=2) + "\n")
        print("selected", selected, "score", score[selected], flush=True)
    elif stage == "prepare-eval":
        selected = json.loads((OUT / "selection.json").read_text())["selected"]
        new_b = next(x for x in grid() if x["result_name"] == selected)
        original_b = _dva(6, 0, preview=True, extension=2, name="B_original")
        a = _dva(6, 0, preview=False, name="A")
        d = _roll(6, 6, "zero", "D_original")
        guards = [_roll(6, 6, "zero", f"D_guard{limit}") for limit in (20, 30)]
        cfg = config("eval", [a, original_b, new_b, d, *guards], EVAL_SEEDS, SENSOR_PRESETS["camera_nominal"])
        write_new(OUT / "eval_config.yaml", yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False))
    elif stage == "run-eval":
        run("eval")
    else:
        raise SystemExit("Неизвестная команда")


if __name__ == "__main__":
    main()
