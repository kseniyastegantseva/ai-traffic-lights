"""Повтор одного парного seed без записи в исходный final."""
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from traffic_light.config import load_experiment_config
from traffic_light.experiments import run_experiment

OUT = ROOT / "outputs/approach_preview_v2_followup"
SOURCE = ROOT / "outputs/approach_preview_v2"
checks = []
for sensor in ("nosensor", "camera_nominal"):
    name = f"approach_preview_v2_final_m6_{sensor}"
    conf = load_experiment_config(ROOT / f"configs/{name}.yaml")
    conf = conf.model_copy(update={"scenarios": [s for s in conf.scenarios if s.name == "symmetric_low"],
                                  "controllers": [c for c in conf.controllers if c.result_name and c.result_name[0] in "ABCD"],
                                  "simulation": conf.simulation.model_copy(update={"seeds": [33101]})})
    rows, _ = run_experiment(conf)
    with gzip.open(SOURCE / f"{name}.json.gz", "rt", encoding="utf-8") as f:
        old = {r["controller"]: r for r in json.load(f)["runs"] if r["scenario"] == "symmetric_low" and r["seed"] == 33101}
    for row in rows:
        expected = old[row["controller"]]
        differences = [k for k in row if row[k] != expected.get(k)]
        checks.append({"controller": row["controller"], "different_fields": differences})
OUT.mkdir(parents=True, exist_ok=True)
with (OUT / "replay_sample.json").open("x", encoding="utf-8") as f:
    json.dump(checks, f, indent=2)
print(json.dumps(checks))
