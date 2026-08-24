from traffic_light.interactive import classify_load, simulate_interactive_traffic


def test_classify_load_recognizes_directional_and_overloaded_scenarios():
    assert (
        classify_load({"north": 10, "west": 1, "south": 8, "east": 1}).code
        == "north_south_peak"
    )
    assert (
        classify_load({"north": 1, "west": 10, "south": 1, "east": 8}).code
        == "east_west_peak"
    )
    assert classify_load({"north": 20, "west": 20, "south": 20, "east": 20}).code == (
        "oversaturated"
    )


def test_interactive_simulation_uses_exact_input_and_clears_all_queues():
    queues = {"north": 4, "west": 2, "south": 3, "east": 1}

    result = simulate_interactive_traffic(queues)

    assert result.initial_queues == queues
    assert result.departed == sum(queues.values())
    assert all(value == 0 for value in result.frames[-1].queues.values())
    assert result.total_time_seconds > 0
    assert result.frames[-1].departed_by_lane == queues


def test_interactive_simulation_keeps_both_directions_separate_until_they_cross():
    result = simulate_interactive_traffic({"north": 2, "west": 2, "south": 2, "east": 2})

    assert all("departed_by_lane" in frame.to_dict() for frame in result.frames)
    assert result.frames[-1].departed_by_lane == {
        "north": 2,
        "west": 2,
        "south": 2,
        "east": 2,
    }
    # The clearance frames are retained after the queues reach zero so the
    # final vehicles have time to travel across the intersection.
    zero_queue_frame = next(
        frame for frame in result.frames if sum(frame.queues.values()) == 0
    )
    assert result.frames[-1].second - zero_queue_frame.second >= 4


def test_interactive_simulation_switches_to_waiting_direction():
    result = simulate_interactive_traffic({"north": 5, "west": 5, "south": 5, "east": 5})

    signal_pairs = {
        (frame.signals["north_south"], frame.signals["east_west"])
        for frame in result.frames
    }
    assert ("green", "red") in signal_pairs
    assert ("yellow", "red") in signal_pairs
    assert ("red", "green") in signal_pairs
    assert result.switches >= 1
    assert sum(phase.duration_seconds for phase in result.phases) == result.total_time_seconds


def test_only_one_of_two_traffic_lights_can_allow_movement():
    result = simulate_interactive_traffic({"north": 20, "west": 20, "south": 20, "east": 20})

    for frame in result.frames:
        colors = tuple(frame.signals.values())
        assert colors.count("green") <= 1
        assert not ("green" in colors and "yellow" in colors)
