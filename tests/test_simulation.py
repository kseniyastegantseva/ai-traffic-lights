from traffic_light.config import IntersectionConfig, SimulationConfig, TrafficDemandConfig
from traffic_light.controllers import (
    AIPhaseController,
    ControllerState,
    FixedTimeController,
    FixedWebsterController,
    VehicleActuatedController,
)
from traffic_light.simulation import (
    Arrival,
    IntersectionSimulation,
    generate_arrivals,
    run_simulation,
)


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


def test_all_controllers_receive_the_same_seeded_arrivals():
    config = SimulationConfig(duration_seconds=120, seed=19)
    events_a = generate_arrivals(intersection(), config)
    events_b = generate_arrivals(intersection(), config)
    assert events_a == events_b


def test_vehicle_conservation_includes_initial_waiting_and_in_service():
    result = run_simulation(
        intersection(),
        SimulationConfig(duration_seconds=1, seed=4),
        FixedTimeController(),
        initial_queues={"north": 2, "south": 1, "east": 0, "west": 0},
        arrivals=[Arrival(0.5, "north")],
    )
    assert result.initial_vehicles + result.vehicles_arrived == (
        result.vehicles_departed + result.waiting_at_end + result.in_service_at_end
    )
    assert result.initial_vehicles == 3
    assert result.waiting_at_end + result.in_service_at_end == 4


def test_arrivals_at_zero_are_present_before_first_service_and_horizon_is_half_open():
    result = run_simulation(
        intersection(),
        SimulationConfig(duration_seconds=1, seed=8),
        FixedTimeController(),
        arrivals=[Arrival(0.0, "north")],
    )
    assert result.vehicles_arrived == 1
    assert result.in_service_at_end == 1


def test_arrival_during_green_starts_service_at_its_event_time():
    result = run_simulation(
        intersection(),
        SimulationConfig(duration_seconds=6, seed=8),
        FixedTimeController(phase_duration_seconds=20),
        arrivals=[Arrival(1.5, "north")],
    )
    assert result.vehicles_departed == 1
    assert result.average_wait_seconds == 0


def test_controller_cannot_start_conflicting_green_during_yellow():
    from traffic_light.controllers import QueueBasedController

    result = run_simulation(
        IntersectionConfig(
            lanes={lane: TrafficDemandConfig(arrival_rate_per_minute=0) for lane in ("north", "south", "east", "west")},
            yellow_seconds=3,
        ),
        SimulationConfig(duration_seconds=10, seed=1),
        QueueBasedController(min_green_seconds=1, max_green_seconds=2),
        initial_queues={"north": 1, "south": 0, "east": 10, "west": 0},
    )
    assert result.initial_vehicles == result.vehicles_departed + result.waiting_at_end + result.in_service_at_end
    history = result.phase_history or []
    assert any(event["color"] == "yellow" for event in history)
    green_phases = [event["phase"] for event in history if event["color"] == "green"]
    assert green_phases[:2] == ["north_south", "east_west"]


def test_vehicle_actuated_gap_out_waits_for_gap_and_minimum_green():
    controller = VehicleActuatedController(min_green_seconds=5, max_green_seconds=30, gap_seconds=3)
    state = ControllerState(4, "north_south", 0, {"north": 0, "south": 0, "east": 1, "west": 0}, 5)
    assert controller.choose_phase(state) == "north_south"
    state.now = 8
    assert controller.choose_phase(state) == "east_west"


def test_queue_based_max_green_serves_competing_request_but_skips_empty_axis():
    from traffic_light.controllers import QueueBasedController

    controller = QueueBasedController(min_green_seconds=8, max_green_seconds=45)
    state = ControllerState(
        45,
        "north_south",
        0,
        {"north": 3, "south": 3, "east": 2, "west": 2},
    )
    assert controller.choose_phase(state) == "east_west"
    state.queues["east"] = 0
    state.queues["west"] = 0
    assert controller.choose_phase(state) == "north_south"


def test_webster_split_and_invalid_demand_fallback_are_bounded():
    split = FixedWebsterController.green_split(
        {"north_south": 0.3, "east_west": 0.3}, lost_time_seconds=6
    )
    assert split["north_south"] == split["east_west"]
    assert 8 <= split["north_south"] <= 90
    fallback = FixedWebsterController.green_split(
        {"north_south": 0.6, "east_west": 0.5}, lost_time_seconds=6
    )
    assert fallback["north_south"] == fallback["east_west"]


def test_observation_errors_do_not_mutate_physical_queues():
    simulation = IntersectionSimulation(
        intersection(),
        SimulationConfig(duration_seconds=10, seed=5, observation_error_rate=0.2),
        AIPhaseController(),
        initial_queues={"north": 100},
        arrivals=[],
    )
    observed = simulation._observed_queues(1.0)
    assert len(simulation.queues["north"]) == 100
    assert observed["north"] != 100


def test_empirical_observation_profile_is_seeded_and_clamped():
    config = SimulationConfig(
        duration_seconds=10,
        seed=5,
        empirical_observation_errors_by_lane={"north": [-3, -1, 2, 4]},
    )
    first = IntersectionSimulation(
        intersection(), config, AIPhaseController(), initial_queues={"north": 10}, arrivals=[]
    )
    second = IntersectionSimulation(
        intersection(), config, AIPhaseController(), initial_queues={"north": 10}, arrivals=[]
    )

    assert first._observed_queues(1.0) == second._observed_queues(1.0)
    assert len(first.queues["north"]) == 10

    empty = IntersectionSimulation(
        intersection(),
        SimulationConfig(
            duration_seconds=10,
            empirical_observation_errors_by_lane={"north": [-3]},
        ),
        AIPhaseController(),
        arrivals=[],
    )
    assert empty._observed_queues(0.0)["north"] == 0


def test_trace_callback_exposes_simpy_queue_phase_and_departure_state():
    from traffic_light.controllers import QueueBasedController

    trace = []
    intersection_config = IntersectionConfig(
        lanes={
            lane: TrafficDemandConfig(arrival_rate_per_minute=0)
            for lane in ("north", "south", "east", "west")
        },
        min_green_seconds=2,
        yellow_seconds=1,
    )
    result = run_simulation(
        intersection_config,
        SimulationConfig(duration_seconds=30, seed=3, service_time_seconds=1),
        QueueBasedController(min_green_seconds=2, max_green_seconds=5),
        initial_queues={"north": 2, "south": 0, "east": 1, "west": 0},
        arrivals=[],
        initial_phase="north_south",
        trace_callback=trace.append,
    )

    assert trace[0]["second"] == 0
    assert trace[0]["queues"] == {"north": 2, "south": 0, "east": 1, "west": 0}
    assert any(frame["color"] == "yellow" for frame in trace)
    assert trace[-1]["departed_by_lane"] == {"north": 2, "south": 0, "east": 1, "west": 0}
    assert result.vehicles_departed == 3
