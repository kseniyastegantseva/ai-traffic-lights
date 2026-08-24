from __future__ import annotations

import json
from pathlib import Path

import typer

from traffic_light.config import load_experiment_config, load_run_config
from traffic_light.experiments import build_controller, run_experiment, save_results
from traffic_light.rl import (
    aggregate_sweep_results,
    run_training_sweep,
    select_best_policy_from_sweep,
    train_q_learning,
)
from traffic_light.simulation import run_simulation

app = typer.Typer(help="Traffic-light discrete-event simulation CLI.")


@app.command()
def run(config: str = typer.Option(..., "--config", "-c")) -> None:
    run_config = load_run_config(config)
    controller = build_controller(
        run_config.controller,
        min_green_seconds=run_config.intersection.min_green_seconds,
    )
    result = run_simulation(run_config.intersection, run_config.simulation, controller)
    output_path = run_config.output.get("path", "outputs/run_result.json")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    typer.echo(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


@app.command()
def compare(config: str = typer.Option(..., "--config", "-c")) -> None:
    experiment_config = load_experiment_config(config)
    results, summary = run_experiment(experiment_config)
    output_path = experiment_config.output.get("path", "outputs/compare_results.json")
    csv_path = experiment_config.output.get("summary_csv", "outputs/compare_summary.csv")
    report_path = experiment_config.output.get("report_markdown", "outputs/experiment_report.md")
    save_results(results, summary, output_path, csv_path, report_path, experiment_config)
    typer.echo(summary.to_string(index=False))
    typer.echo(f"\nОтчёт сохранён: {report_path}")


@app.command()
def train(
    config: str = typer.Option(..., "--config", "-c"),
    episodes: int = typer.Option(200, "--episodes", "-e"),
) -> None:
    run_config = load_run_config(config)
    policy_path = run_config.output.get("policy_path", "outputs/q_learning_policy.json")
    result = train_q_learning(
        run_config,
        episodes=episodes,
        policy_path=policy_path,
    )
    typer.echo(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


@app.command()
def sweep(
    config: str = typer.Option(..., "--config", "-c"),
    episodes: str = typer.Option("10,25,50,100", "--episodes"),
    seeds: str | None = typer.Option(None, "--seeds"),
) -> None:
    run_config = load_run_config(config)
    episode_values = [int(value.strip()) for value in episodes.split(",") if value.strip()]
    seed_values = [int(value.strip()) for value in seeds.split(",") if value.strip()] if seeds else None
    frame = run_training_sweep(run_config, episode_values, seeds=seed_values)
    typer.echo(aggregate_sweep_results(frame).to_string(index=False))
    typer.echo("\nSweep сохранён: outputs/q_learning_sweep.md")


@app.command()
def select_policy(
    config: str = typer.Option("configs/ai.yaml", "--config", "-c"),
    sweep_path: str = typer.Option("outputs/q_learning_sweep.json", "--sweep-path"),
    output_policy_path: str | None = typer.Option(None, "--output-policy-path"),
) -> None:
    run_config = load_run_config(config)
    target_policy_path = output_policy_path or run_config.output.get(
        "policy_path",
        "outputs/q_learning_policy.json",
    )
    selected = select_best_policy_from_sweep(
        sweep_path=sweep_path,
        output_policy_path=target_policy_path,
    )
    typer.echo(json.dumps(selected, ensure_ascii=False, indent=2))
