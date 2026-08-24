from traffic_light.config import IntersectionConfig, SimulationConfig, TrafficDemandConfig
from traffic_light.controllers import AIPhaseController, FixedTimeController
from traffic_light.simulation import run_simulation


def intersection() -> IntersectionConfig:
    return IntersectionConfig(
        lanes={
            "north": TrafficDemandConfig(arrival_rate_per_minute=6),
            "south": TrafficDemandConfig(arrival_rate_per_minute=6),
            "east": TrafficDemandConfig(arrival_rate_per_minute=3),
            "west": TrafficDemandConfig(arrival_rate_per_minute=3),
        }
    )


def test_simulation_is_reproducible_for_seed():
    config = SimulationConfig(duration_seconds=300, seed=7)
    first = run_simulation(intersection(), config, FixedTimeController())
    second = run_simulation(intersection(), config, FixedTimeController())
    assert first.to_dict() == second.to_dict()


def test_fixed_controller_moves_vehicles():
    result = run_simulation(
        intersection(),
        SimulationConfig(duration_seconds=300, seed=1),
        FixedTimeController(phase_duration_seconds=30),
    )
    assert result.vehicles_arrived > 0
    assert result.vehicles_departed > 0
    assert result.average_wait_seconds >= 0


def test_ai_controller_runs():
    result = run_simulation(
        intersection(),
        SimulationConfig(duration_seconds=300, seed=1),
        AIPhaseController(),
    )
    assert result.controller == "ai"
    assert 0 < result.fairness_index <= 1
