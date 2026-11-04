"""Повтор выбранных seed исходного final в отдельном каталоге; сравнение всех полей."""
import argparse
import gzip
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from traffic_light.config import load_experiment_config
from traffic_light.experiments import run_experiment

SOURCE = ROOT / "outputs/approach_preview_v2"
OUT = ROOT / "outputs/approach_preview_v2_followup/replay_matrix"


def run_one(args):
    scenario, seeds = args
    result = []
    for sensor in ("nosensor", "camera_nominal"):
        name = f"approach_preview_v2_final_m6_{sensor}"
        conf = load_experiment_config(ROOT / f"configs/{name}.yaml")
        conf = conf.model_copy(update={
            "scenarios": [s for s in conf.scenarios if s.name == scenario],
            "controllers": [c for c in conf.controllers if c.result_name and c.result_name[0] in "ABCD"],
            "simulation": conf.simulation.model_copy(update={"seeds": seeds}),
        })
        rows, _ = run_experiment(conf)
        with gzip.open(SOURCE / f"{name}.json.gz", "rt", encoding="utf-8") as f:
            old = {(r["controller"], r["seed"]): r for r in json.load(f)["runs"]
                   if r["scenario"] == scenario and r["seed"] in seeds}
        for row in rows:
            expected = old[row["controller"], row["seed"]]
            diffs = [k for k in row if row[k] != expected.get(k)]
            result.append({"controller": row["controller"], "seed": row["seed"], "different_fields": diffs})
    return scenario, result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[33101, 33102, 33103])
    parser.add_argument("--workers", type=int, default=6)
    opts = parser.parse_args()
    if any(s < 33101 or s > 33130 for s in opts.seeds) or len(set(opts.seeds)) != len(opts.seeds):
        raise ValueError("Требуются уникальные исходные final-seed 33101–33130")
    conf = load_experiment_config(ROOT / "configs/approach_preview_v2_final_m6_camera_nominal.yaml")
    OUT.mkdir(parents=True, exist_ok=True)
    if any(OUT.glob("*.json")):
        raise SystemExit("Каталог повтора не пуст: результаты не перезаписываются")
    with ProcessPoolExecutor(max_workers=opts.workers) as pool:
        jobs = [pool.submit(run_one, (s.name, opts.seeds)) for s in conf.scenarios]
        for future in as_completed(jobs):
            scenario, rows = future.result()
            path = OUT / f"{scenario}.json"
            with path.open("x", encoding="utf-8") as f:
                json.dump(rows, f, indent=2)
            print(scenario, "runs", len(rows), "mismatch", sum(bool(r["different_fields"]) for r in rows), flush=True)


if __name__ == "__main__":
    main()
