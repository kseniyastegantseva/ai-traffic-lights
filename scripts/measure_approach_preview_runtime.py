"""Время принятия решения rollout-контроллера: median/p95/p99/max и деградация по нагрузке.

Реальные измерения ``time.perf_counter`` на состояниях, записанных из прогона SimPy, и на
синтетическом стрессе (много ETA). Результат — ``outputs/approach_preview_v2/runtime_profile.*``.
Бюджет решения — 1 с (шаг управления); превышение фиксируется, а детерминированный fallback
по числу шагов rollout (``max_work_units``) проверяется отдельно.
"""
from __future__ import annotations

import json
import platform
import statistics
import sys
import time
import tracemalloc
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from traffic_light.config import IntersectionConfig, SimulationConfig, TrafficDemandConfig
from traffic_light.controllers import (
    BaseController,
    ControllerState,
    QueueBasedApproachPreviewController,
)
from traffic_light.simulation import run_simulation

LANES = ("north", "south", "east", "west")
OUT = ROOT / "outputs/approach_preview_v2"


class Recorder(BaseController):
    name = "recorder"

    def __init__(self, inner: BaseController) -> None:
        self.inner, self.states = inner, []

    def choose_phase(self, state):
        self.states.append(deepcopy(state))
        return self.inner.choose_phase(state)


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))]


def profile(controller: QueueBasedApproachPreviewController, states: list[ControllerState]) -> dict:
    durations = []
    tracemalloc.start()
    for state in states:
        started = time.perf_counter()
        controller.choose_phase(state)
        durations.append(time.perf_counter() - started)
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return {
        "decisions": len(durations),
        "median_ms": 1000 * statistics.median(durations),
        "p95_ms": 1000 * percentile(durations, 0.95),
        "p99_ms": 1000 * percentile(durations, 0.99),
        "max_ms": 1000 * max(durations),
        "peak_memory_kib": peak / 1024,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    intersection = IntersectionConfig(
        lanes={lane: TrafficDemandConfig(arrival_rate_per_minute=12) for lane in LANES},
        min_green_seconds=6, yellow_seconds=3,
    )
    config = SimulationConfig(
        duration_seconds=1800, seed=7, startup_lost_time_seconds=2.0, preview_seconds=10.0,
        sensor_model="causal", arrival_rate_tau_seconds=120.0,
    )
    recorder = Recorder(QueueBasedApproachPreviewController(min_green_seconds=6, continuation_min_green_seconds=6))
    run_simulation(intersection, config, recorder)
    contested = [s for s in recorder.states if s.now - s.phase_started_at >= 6]
    controller = QueueBasedApproachPreviewController(min_green_seconds=6, continuation_min_green_seconds=6)
    result = {"platform": platform.platform(), "python": platform.python_version(),
              "recorded_decisions": profile(controller, contested)}
    for etas in (10, 40, 120, 400):
        stress = deepcopy(contested[len(contested) // 2])
        stress.upcoming_arrival_offsets = {lane: [(i * 9.5 / max(etas // 4, 1)) for i in range(etas // 4)] for lane in LANES}
        stress.queues = {"north": 0, "south": 0, "east": 6, "west": 4}
        result[f"stress_{etas}_etas"] = profile(controller, [stress] * 200)
    budget = QueueBasedApproachPreviewController(max_work_units=600)
    result["fallback_budget_600_units"] = profile(budget, contested)
    result["budget_seconds"] = 1.0
    result["within_budget"] = all(
        item["max_ms"] < 1000 for key, item in result.items() if isinstance(item, dict) and "max_ms" in item
    )
    (OUT / "runtime_profile.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = ["# Профиль времени решения rollout-контроллера", "",
             f"{result['platform']}, Python {result['python']}. Бюджет решения — 1 с.", "",
             "| Режим | Решений | median, мс | p95, мс | p99, мс | max, мс | пик памяти, КиБ |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for key, item in result.items():
        if isinstance(item, dict) and "max_ms" in item:
            lines.append(
                f"| {key} | {item['decisions']} | {item['median_ms']:.2f} | {item['p95_ms']:.2f} | "
                f"{item['p99_ms']:.2f} | {item['max_ms']:.2f} | {item['peak_memory_kib']:.0f} |"
            )
    (OUT / "runtime_profile.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k.startswith("recorded")}, indent=1))


if __name__ == "__main__":
    main()
