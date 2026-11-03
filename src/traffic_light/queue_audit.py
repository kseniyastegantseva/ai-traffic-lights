"""Independently replay saved PIERE runs from seeded arrivals and phase logs.

This checker uses only the Python standard library. It regenerates the Poisson
arrival streams from the saved experiment configuration, then replays each
lane as a FIFO server over the archived green intervals. It does not import or
call the SimPy model or its metric aggregation code.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

LANES = ("north", "south", "east", "west")
LANE_INDEX = {lane: index for index, lane in enumerate(LANES)}
PHASE_LANES = {
    "north_south": ("north", "south"),
    "east_west": ("east", "west"),
}


def max_signal_red_by_phase(history: list[dict], duration_seconds: int) -> dict[str, float]:
    """Derive the longest continuous red indication for each axis from phase starts.

    This is signal red time, whether or not a vehicle was waiting on that axis; it
    must not be interpreted as maximum vehicle waiting time or detector headway.
    """
    green_events = [
        (float(event["at"]), event["phase"])
        for event in history
        if event["color"] == "green"
    ]
    result = {}
    for phase in PHASE_LANES:
        starts = [time for time, event_phase in green_events if event_phase == phase]
        intervals: list[float] = []
        if not starts or (starts[0] > 0 and history[0]["phase"] != phase):
            intervals.append(starts[0] if starts else float(duration_seconds))
        for start, event_phase in green_events:
            if event_phase != phase:
                continue
            opposing = next(
                (
                    time
                    for time, candidate in green_events
                    if time > start and candidate != phase
                ),
                None,
            )
            if opposing is None:
                continue
            next_own = next((time for time in starts if time > opposing), None)
            red_end = next_own if next_own is not None else float(duration_seconds)
            intervals.append(max(0.0, red_end - opposing))
        result[phase] = max(intervals, default=0.0)
    return result


def max_red_with_queued_vehicles_by_phase(
    history: list[dict],
    duration_seconds: int,
    arrivals_by_lane: dict[str, list[float]],
    service_starts_by_lane: dict[str, list[tuple[float, float, float]]],
) -> dict[str, float]:
    """Independently derive the longest red interval that overlaps a waiting queue.

    Waiting starts at the red interval boundary if a queue already exists, or at
    the first arrival during red. The interval ends when that axis receives green.
    Service starts, rather than completions, remove a vehicle from its waiting queue.
    """
    green_events = [
        (float(event["at"]), event["phase"])
        for event in history
        if event["color"] == "green"
    ]
    result = {phase: 0.0 for phase in PHASE_LANES}
    for phase, lanes in PHASE_LANES.items():
        arrivals = sorted(time for lane in lanes for time in arrivals_by_lane[lane])
        service_starts = sorted(
            start for lane in lanes for start, _, _ in service_starts_by_lane[lane]
        )
        for red_start, green_phase in green_events:
            if green_phase == phase:
                continue
            next_own_green = next(
                (time for time, candidate in green_events if time > red_start and candidate == phase),
                float(duration_seconds),
            )
            red_end = min(float(duration_seconds), next_own_green)
            if red_end <= red_start:
                continue
            queued_at_red_start = sum(time <= red_start for time in arrivals) - sum(
                time <= red_start for time in service_starts
            )
            if queued_at_red_start > 0:
                request_start = red_start
            else:
                request_start = next(
                    (time for time in arrivals if red_start < time < red_end),
                    None,
                )
            if request_start is not None:
                result[phase] = max(result[phase], red_end - request_start)
    return result


def load_payload(path: Path) -> dict[str, Any]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def regenerate_arrivals(
    configuration: dict[str, Any], scenario: dict[str, Any], seed: int
) -> list[tuple[float, str]]:
    """Recreate the saved lane-wise Poisson streams using their explicit seeds."""
    duration = int(configuration["simulation"]["duration_seconds"])
    periods = scenario.get("demand_schedule") or [
        {
            "start_seconds": 0,
            "end_seconds": duration,
            "lanes": scenario["intersection"]["lanes"],
        }
    ]
    events: list[tuple[float, str]] = []
    for lane_index, lane in enumerate(LANES):
        rng = random.Random(seed + 104729 * (lane_index + 1))
        for period in sorted(periods, key=lambda item: item["start_seconds"]):
            start = max(0.0, float(period["start_seconds"]))
            end = min(float(duration), float(period["end_seconds"]))
            rate = period["lanes"].get(lane, {}).get("arrival_rate_per_minute", 0.0)
            if rate <= 0 or end <= start:
                continue
            at = start
            while True:
                at += rng.expovariate(float(rate) / 60.0)
                if at >= end:
                    break
                events.append((at, lane))
    return sorted(events, key=lambda event: (event[0], LANE_INDEX[event[1]]))


def arrival_digest(arrivals: list[tuple[float, str]]) -> str:
    payload = "\n".join(f"{float(at).hex()},{lane}" for at, lane in arrivals)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _green_intervals(row: dict[str, Any]) -> tuple[dict[str, list[tuple[float, float]]], list[tuple[float, float]], list[float]]:
    duration = float(row["duration_seconds"])
    history = row.get("phase_history") or []
    lane_intervals = {lane: [] for lane in LANES}
    yellow_intervals: list[tuple[float, float]] = []
    green_lengths: list[float] = []
    previous_at = -1.0
    for index, entry in enumerate(history):
        start = float(entry["at"])
        if start < 0 or start >= duration or start <= previous_at:
            raise ValueError("phase history timestamps must increase inside the run horizon")
        previous_at = start
        end = float(history[index + 1]["at"]) if index + 1 < len(history) else duration
        end = min(duration, end)
        if entry["color"] == "green":
            green_lengths.append(end - start)
            for lane in PHASE_LANES[entry["phase"]]:
                lane_intervals[lane].append((start, end))
        elif entry["color"] == "yellow":
            yellow_intervals.append((start, end))
        elif entry["color"] == "all_red":
            continue
        else:
            raise ValueError(f"unknown signal color {entry['color']!r}")
    return lane_intervals, yellow_intervals, green_lengths


def replay_run(
    row: dict[str, Any],
    scenario: dict[str, Any],
    configuration: dict[str, Any],
) -> dict[str, Any]:
    """Recompute run metrics from regenerated arrivals and archived phases."""
    duration = float(row["duration_seconds"])
    service = float(configuration["simulation"]["service_time_seconds"])
    startup_loss = float(configuration["simulation"].get("startup_lost_time_seconds", 0.0))
    arrivals = regenerate_arrivals(configuration, scenario, int(row["seed"]))
    if arrival_digest(arrivals) != row["arrival_stream_sha256"]:
        raise ValueError("regenerated arrival stream does not match the saved digest")

    initial_queues = scenario.get("initial_queues") or {}
    by_lane = {lane: [0.0] * int(initial_queues.get(lane, 0)) for lane in LANES}
    for at, lane in arrivals:
        by_lane[lane].append(at)
    for times in by_lane.values():
        times.sort()

    lane_green, yellow_intervals, green_lengths = _green_intervals(row)
    starts_by_lane: dict[str, list[tuple[float, float, float]]] = {}
    completed_waits: list[float] = []
    lane_completed_waits: dict[str, list[float]] = {lane: [] for lane in LANES}
    in_service = 0
    residual_waiting = 0
    queue_delay_area = 0.0
    lane_green_seconds: dict[str, float] = {}

    for lane in LANES:
        times = by_lane[lane]
        starts: list[tuple[float, float, float]] = []  # start, finish, waiting time
        cursor = 0
        available_at = 0.0
        for green_start, green_end in lane_green[lane]:
            while cursor < len(times):
                start = max(green_start + startup_loss, available_at, times[cursor])
                # A new service must begin strictly before green ends. Service
                # already started can finish during yellow.
                if start >= green_end or start >= duration:
                    break
                arrival_at = times[cursor]
                cursor += 1
                finish = start + service
                starts.append((start, finish, start - arrival_at))
                available_at = finish
                if finish < duration:
                    wait = start - arrival_at
                    completed_waits.append(wait)
                    lane_completed_waits[lane].append(wait)
                else:
                    in_service += 1
                    break
        starts_by_lane[lane] = starts
        residual_waiting += len(times) - cursor
        queue_delay_area += sum(wait for _, _, wait in starts)
        queue_delay_area += sum(duration - at for at in times[cursor:])
        lane_green_seconds[lane] = sum(end - start for start, end in lane_green[lane])

    max_red_with_queue = max_red_with_queued_vehicles_by_phase(
        history=row.get("phase_history") or [],
        duration_seconds=int(duration),
        arrivals_by_lane=by_lane,
        service_starts_by_lane=starts_by_lane,
    )

    # Queue maximum is evaluated after arrivals at a timestamp and before
    # service starts at that timestamp, matching the model's stated tie rule.
    arrivals_at: Counter[float] = Counter()
    starts_at: Counter[float] = Counter()
    for times in by_lane.values():
        arrivals_at.update(times)
    for starts in starts_by_lane.values():
        starts_at.update(start for start, _, _ in starts)
    waiting = 0
    maximum_queue = 0
    for at in sorted(set(arrivals_at) | set(starts_at)):
        waiting += arrivals_at[at]
        maximum_queue = max(maximum_queue, waiting)
        waiting -= starts_at[at]
        if waiting < 0:
            raise ValueError("replay produced a negative waiting queue")

    departed = len(completed_waits)
    initial_vehicles = sum(int(count) for count in initial_queues.values())
    total_vehicles_presented = len(arrivals) + initial_vehicles
    green_seconds = sum(lane_green_seconds[lane] for lane in LANES) / 2.0
    yellow_seconds = sum(end - start for start, end in yellow_intervals)
    green_busy_lane_seconds = 0.0
    green_service_wall_intervals: dict[str, list[tuple[float, float]]] = {
        phase: [] for phase in PHASE_LANES
    }
    for lane, starts in starts_by_lane.items():
        phase = "north_south" if lane in PHASE_LANES["north_south"] else "east_west"
        for service_start, finish, _ in starts:
            service_end = min(duration, finish)
            for green_start, green_end in lane_green[lane]:
                overlap = max(0.0, min(service_end, green_end) - max(service_start, green_start))
                green_busy_lane_seconds += overlap
                if overlap:
                    green_service_wall_intervals[phase].append(
                        (max(service_start, green_start), min(service_end, green_end))
                    )
    # Utilization denominator is two parallel lane servers available during
    # each green phase; this is a lane-time capacity fraction, not road capacity.
    green_available_lane_seconds = 2.0 * green_seconds
    green_idle_lane_seconds = max(0.0, green_available_lane_seconds - green_busy_lane_seconds)
    v_c_by_lane = {
        lane: len([at for at in by_lane[lane] if at > 0 or at == 0])
        / (lane_green_seconds[lane] / service)
        if lane_green_seconds[lane] > 0
        else math.inf
        for lane in LANES
    }
    phase_switches = sum(entry["color"] == "yellow" for entry in (row.get("phase_history") or []))
    controller_config = next(
        (
            item
            for item in configuration.get("controllers", [])
            if (item.get("result_name") or (
                "queue_based_legacy" if item.get("legacy_rule") else item["type"]
            )) == row["controller"]
        ),
        {},
    )
    max_green = float(controller_config.get("max_green_seconds", math.inf))
    return {
        "arrivals": len(arrivals),
        "initial_vehicles": initial_vehicles,
        "total_vehicles_presented": total_vehicles_presented,
        "departures": departed,
        "vehicles_in_service_at_end": in_service,
        "residual_queue": residual_waiting,
        "average_wait_seconds": statistics.mean(completed_waits) if completed_waits else 0.0,
        "median_wait_seconds": statistics.median(completed_waits) if completed_waits else 0.0,
        "max_wait_seconds": max(completed_waits) if completed_waits else 0.0,
        "lane_waits": {
            lane: statistics.mean(waits) if waits else 0.0
            for lane, waits in lane_completed_waits.items()
        },
        "stops": sum(wait > 1 for wait in completed_waits),
        "queue_delay_area_vehicle_seconds": queue_delay_area,
        "mean_accrued_wait_per_vehicle_seconds": (
            queue_delay_area / total_vehicles_presented if total_vehicles_presented else 0.0
        ),
        "average_queue_length": queue_delay_area / duration,
        "max_queue_length": maximum_queue,
        "throughput_per_hour": departed * 3600.0 / duration,
        "green_seconds": green_seconds,
        "green_fraction": green_seconds / duration,
        "yellow_seconds": yellow_seconds,
        "phase_switches": int(phase_switches),
        "max_red_with_queue_seconds_by_phase": max_red_with_queue,
        "green_durations_seconds": green_lengths,
        "green_mean_seconds": statistics.mean(green_lengths) if green_lengths else 0.0,
        "green_max_reached_count": sum(length >= max_green - 1e-9 for length in green_lengths),
        "green_active_lane_seconds": green_busy_lane_seconds,
        "green_available_lane_seconds": green_available_lane_seconds,
        "green_idle_lane_seconds": green_idle_lane_seconds,
        "green_idle_fraction": (
            green_idle_lane_seconds / green_available_lane_seconds
            if green_available_lane_seconds
            else 0.0
        ),
        "green_utilization": (
            green_busy_lane_seconds / green_available_lane_seconds
            if green_available_lane_seconds
            else 0.0
        ),
        "v_c_by_lane": v_c_by_lane,
    }


def audit_file(path: Path) -> dict[str, Any]:
    payload = load_payload(path)
    configuration = payload["configuration"]
    scenarios = {item["name"]: item for item in configuration["scenarios"]}
    key_counts: Counter[tuple[str, int, int, str]] = Counter()
    stream_hashes: dict[tuple[str, int, int], set[str]] = defaultdict(set)
    mismatches: list[dict[str, Any]] = []
    replayed: list[dict[str, Any]] = []
    metric_fields = {
        "arrivals": "vehicles_arrived",
        "departures": "vehicles_departed",
        "vehicles_in_service_at_end": "in_service_at_end",
        "residual_queue": "waiting_at_end",
        "average_wait_seconds": "average_wait_seconds",
        "median_wait_seconds": "median_wait_seconds",
        "max_wait_seconds": "max_wait_seconds",
        "stops": "stops",
        "average_queue_length": "average_queue_length",
        "queue_delay_area_vehicle_seconds": "observed_delay_seconds",
        "max_queue_length": "max_queue_length",
        "throughput_per_hour": "throughput_per_hour",
    }
    for row in payload["runs"]:
        key = (
            row["scenario"], int(row["duration_seconds"]), int(row["seed"]), row["controller"]
        )
        key_counts[key] += 1
        stream_hashes[key[:3]].add(row["arrival_stream_sha256"])
        replay = replay_run(row, scenarios[row["scenario"]], configuration)
        replayed.append(
            {
                "scenario": row["scenario"],
                "scenario_title": row["scenario_title"],
                "duration_seconds": row["duration_seconds"],
                "seed": row["seed"],
                "controller": row["controller"],
                "saved_average_wait_seconds": row["average_wait_seconds"],
                "saved_average_queue_length": row["average_queue_length"],
                "saved_throughput_per_hour": row["throughput_per_hour"],
                "saved_waiting_at_end": row["waiting_at_end"],
                "independent": replay,
            }
        )
        row_errors = []
        for actual_name, stored_name in metric_fields.items():
            actual = replay[actual_name]
            stored = float(row[stored_name])
            if not math.isclose(float(actual), stored, rel_tol=1e-10, abs_tol=1e-8):
                row_errors.append({"metric": stored_name, "stored": stored, "replayed": actual})
        stored_red_with_queue = row.get("max_red_with_queue_seconds_by_phase")
        if stored_red_with_queue is not None:
            for phase, actual in replay["max_red_with_queue_seconds_by_phase"].items():
                stored = float(stored_red_with_queue[phase])
                if not math.isclose(float(actual), stored, rel_tol=1e-10, abs_tol=1e-8):
                    row_errors.append(
                        {
                            "metric": f"max_red_with_queue_seconds_by_phase.{phase}",
                            "stored": stored,
                            "replayed": actual,
                        }
                    )
        for lane, stored_wait in row["lane_waits"].items():
            replayed_wait = replay["lane_waits"][lane]
            if not math.isclose(
                replayed_wait, float(stored_wait), rel_tol=1e-10, abs_tol=1e-8
            ):
                row_errors.append(
                    {
                        "metric": f"lane_waits.{lane}",
                        "stored": stored_wait,
                        "replayed": replayed_wait,
                    }
                )
        if int(row["initial_vehicles"]) + replay["arrivals"] != (
            replay["departures"] + replay["residual_queue"] + replay["vehicles_in_service_at_end"]
        ):
            row_errors.append({"metric": "vehicle_conservation"})
        if row_errors:
            mismatches.append({"scenario": key[0], "seed": key[2], "controller": key[3], "errors": row_errors})
    duplicate_keys = [list(key) for key, count in key_counts.items() if count != 1]
    unpaired_streams = [list(key) for key, hashes in stream_hashes.items() if len(hashes) != 1]
    return {
        "file": str(path),
        "runs": len(payload["runs"]),
        "unique_scenario_horizon_seed_groups": len(stream_hashes),
        "duplicate_run_keys": duplicate_keys,
        "arrival_stream_pairing_errors": unpaired_streams,
        "metric_mismatch_runs": len(mismatches),
        "metric_mismatches": mismatches,
        "replayed_runs": replayed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path, help="saved experiment JSON files")
    parser.add_argument("--summary-only", action="store_true", help="omit replayed run details")
    parser.add_argument(
        "--replay-output",
        type=Path,
        help="save independently replayed per-run metrics as JSON for downstream analysis",
    )
    args = parser.parse_args()
    reports = [audit_file(path) for path in args.files]
    if args.replay_output:
        args.replay_output.parent.mkdir(parents=True, exist_ok=True)
        args.replay_output.write_text(
            json.dumps(
                [
                    {
                        "file": report["file"],
                        "runs": [
                            {
                                key: row[key]
                                for key in (
                                    "scenario",
                                    "scenario_title",
                                    "duration_seconds",
                                    "seed",
                                    "controller",
                                )
                            }
                            | row["independent"]
                            for row in report["replayed_runs"]
                        ],
                    }
                    for report in reports
                ],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )
    for report in reports:
        print(
            f"{report['file']}: runs={report['runs']}; "
            f"groups={report['unique_scenario_horizon_seed_groups']}; "
            f"duplicates={len(report['duplicate_run_keys'])}; "
            f"unpaired={len(report['arrival_stream_pairing_errors'])}; "
            f"metric_mismatch_runs={report['metric_mismatch_runs']}"
        )
        if not args.summary_only:
            report.pop("replayed_runs")
        if report["metric_mismatches"]:
            print(json.dumps(report["metric_mismatches"][:3], indent=2))


if __name__ == "__main__":
    main()
