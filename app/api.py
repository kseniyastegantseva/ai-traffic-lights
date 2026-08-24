from __future__ import annotations

from fastapi import FastAPI

from traffic_light.config import load_experiment_config
from traffic_light.experiments import run_experiment

app = FastAPI(title="Traffic Light AI Simulation")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/experiment/default")
def default_experiment() -> dict:
    config = load_experiment_config("configs/experiment_suite.yaml")
    _, summary = run_experiment(config)
    return {"summary": summary.to_dict(orient="records")}
