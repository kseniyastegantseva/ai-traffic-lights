"""Export one-second directional queues for a small, matched trace subset."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from traffic_light.config import SimulationConfig, load_experiment_config
from traffic_light.experiments import build_controller
from traffic_light.simulation import generate_arrivals, run_simulation

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/queue_based_diagnostic_traces_1800.yaml"
OUTPUT = ROOT / "outputs/queue_based_diagnostic_traces_1800.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    config = load_experiment_config(args.config)
    trace_rows: list[dict] = []
    run_rows: list[dict] = []
    for scenario in config.scenarios or []:
        for seed in config.simulation.seeds:
            simulation = SimulationConfig(
                duration_seconds=config.simulation.duration_seconds,
                seed=seed,
                service_time_seconds=config.simulation.service_time_seconds,
                observation_error_rate=scenario.observation_error_rate,
                empirical_observation_errors_by_lane=config.simulation.empirical_observation_errors_by_lane,
            )
            arrivals = generate_arrivals(scenario.intersection, simulation, scenario.demand_schedule)
            for controller_config in config.controllers:
                trace: list[dict] = []
                controller = build_controller(controller_config, scenario.intersection.min_green_seconds, scenario.intersection)
                result = run_simulation(
                    scenario.intersection,
                    simulation,
                    controller,
                    initial_queues=scenario.initial_queues,
                    arrivals=arrivals,
                    trace_callback=trace.append,
                )
                trace_rows.extend(
                    {
                        "scenario": scenario.name,
                        "seed": seed,
                        "controller": result.controller,
                        **frame,
                    }
                    for frame in trace
                )
                run_rows.append(
                    {
                        "scenario": scenario.name,
                        "seed": seed,
                        "controller": result.controller,
                        "arrival_stream_sha256": result.arrival_stream_sha256,
                        "vehicles_arrived": result.vehicles_arrived,
                        "vehicles_departed": result.vehicles_departed,
                        "average_wait_seconds": result.average_wait_seconds,
                        "average_queue_length": result.average_queue_length,
                        "waiting_at_end": result.waiting_at_end,
                        "in_service_at_end": result.in_service_at_end,
                    }
                )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(trace_rows[0]))
        writer.writeheader()
        writer.writerows(trace_rows)
    run_output = args.output.with_name(args.output.stem.replace("_traces", "_trace_runs") + ".csv")
    with run_output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(run_rows[0]))
        writer.writeheader()
        writer.writerows(run_rows)
    print(f"trace rows={len(trace_rows)}; matched runs={len(run_rows)}")


if __name__ == "__main__":
    main()
