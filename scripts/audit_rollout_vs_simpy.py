"""Аудит rollout ↔ SimPy: посекундное совпадение площади очереди, округление ETA, регрет.

Результаты сохраняются в ``outputs/approach_preview_v2/rollout_audit.{csv,json,md}``.
Целочисленная сетка (целые прибытия и время обслуживания, жёлтый 0/1/3 с, потеря времени на
старт 0/2 с, обслуживание 2/4 с с динамическим all-red) должна давать нулевое расхождение.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from traffic_light.rollout_audit import (
    area_discrepancy,
    exhaustive_regret,
    fractional_arrival_error,
    integer_grid_cases,
)

OUT = ROOT / "outputs/approach_preview_v2"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, worst = [], 0.0
    for case in integer_grid_cases(range(20)):
        result = area_discrepancy(case)
        if result is None:
            continue
        predicted, actual = result
        delta = max(abs(a - b) for a, b in zip(predicted, actual, strict=True))
        worst = max(worst, delta)
        rows.append({
            "seed": case.seed, "yellow_seconds": case.yellow, "startup_lost_seconds": case.startup,
            "service_seconds": case.service, "switch_steps": "/".join(map(str, case.switches)),
            "horizon": case.horizon, "predicted_area": sum(predicted), "simpy_area": sum(actual),
            "max_abs_step_difference": delta,
        })
    with (OUT / "rollout_audit.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    fractional = fractional_arrival_error(range(40))
    regret = {horizon: exhaustive_regret(range(1000), horizon=horizon) for horizon in (16, 24)}
    summary = {
        "integer_grid_cases": len(rows),
        "integer_grid_max_abs_step_difference": worst,
        "fractional_arrival_error": fractional,
        "exhaustive_search_regret": regret,
    }
    (OUT / "rollout_audit.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Аудит rollout ↔ SimPy", "",
        (
            f"Целочисленная сетка: {len(rows)} случаев, максимальное посекундное расхождение "
            f"площади очереди **{worst:.3g}** авто·с."
        ),
        "",
        "## Дробные времена прибытия (ошибка суммарной площади по горизонту 30 с)", "",
        "| Округление ETA | Случаев | Средняя знаковая ошибка | Средняя абс. ошибка | Максимальная абс. ошибка |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in fractional:
        lines.append(
            f"| {row['eta_rounding']} | {row['cases']} | {row['mean_signed_relative_error']:+.2%} | "
            f"{row['mean_abs_relative_error']:.2%} | {row['max_abs_relative_error']:.2%} |"
        )
    lines += ["", "## Полный перебор планов с ≤2 переключениями (в модели rollout)", "",
              "| Горизонт, с | Состояний | Доля неоптимальных | Среднее сожаление, авто·с | Максимум, авто·с |",
              "|---:|---:|---:|---:|---:|"]
    for horizon, item in regret.items():
        lines.append(
            f"| {horizon} | {item['states']} | {item['non_optimal_share']:.2%} | "
            f"{item['mean_regret_vehicle_seconds']:.4f} | {item['max_regret_vehicle_seconds']:.1f} |"
        )
    (OUT / "rollout_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"integer grid: {len(rows)} cases, max difference {worst}")


if __name__ == "__main__":
    main()
