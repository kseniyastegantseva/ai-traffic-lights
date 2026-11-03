"""Create development figures for the empty-green gap-out study."""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/total_improvement/figures"
METRICS = ROOT / "outputs/total_improvement/empty_gap_development_1800_metrics.csv"
PAIRED = ROOT / "outputs/total_improvement/empty_gap_development_1800_paired.csv"
DEMAND_ORDER = (
    "symmetric_low",
    "symmetric",
    "symmetric_9",
    "high_load",
    "true_oversaturated",
)
DEMAND_LABELS = ("3", "6", "9", "18", "24")
CONTROLLERS = {
    "queue_based_improved": "Improved",
    "queue_based_empty_gap_1s": "Empty gap 1 s",
    "vehicle_actuated": "Vehicle-actuated",
}


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _save(fig: plt.Figure, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", dpi=180)
    svg_path = OUT / f"{name}.svg"
    fig.savefig(svg_path)
    svg_lines = svg_path.read_text(encoding="utf-8").splitlines()
    svg_path.write_text("\n".join(line.rstrip() for line in svg_lines) + "\n", encoding="utf-8")
    plt.close(fig)


def _metric_plot(summary: list[dict[str, str]], metric: str, ylabel: str, name: str) -> None:
    fig, axis = plt.subplots(figsize=(8.5, 5.0))
    x = np.arange(len(DEMAND_ORDER))
    for controller, label in CONTROLLERS.items():
        values = []
        errors = []
        for scenario in DEMAND_ORDER:
            row = next(
                item
                for item in summary
                if item["scenario"] == scenario and item["controller"] == controller
            )
            n = int(row["runs"])
            values.append(float(row[metric]))
            errors.append(
                float(student_t.ppf(0.975, n - 1))
                * float(row[f"{metric}_sd"])
                / np.sqrt(n)
            )
        axis.errorbar(x, values, yerr=errors, marker="o", capsize=3, label=label)
    axis.set_xticks(x, DEMAND_LABELS)
    axis.set_xlabel("Интенсивность, автомобилей в минуту на подход")
    axis.set_ylabel(ylabel)
    axis.grid(True, alpha=0.25)
    axis.legend()
    _save(fig, name)


def _paired_wait_plot(paired: list[dict[str, str]]) -> None:
    scenarios = list(DEMAND_ORDER) + [
        "asymmetric_ns",
        "asymmetric_ew",
        "sudden_dominance_switch",
    ]
    labels = ["3", "6", "9", "18", "24", "Asym N/S", "Asym E/W", "Смена"]
    fig, axis = plt.subplots(figsize=(10.0, 5.5))
    x = np.arange(len(scenarios))
    for offset, controller, label in (
        (0.0, "queue_based_empty_gap_1s", "Empty gap 1 s"),
    ):
        means, lower, upper = [], [], []
        for scenario in scenarios:
            row = next(
                item
                for item in paired
                if item["scenario"] == scenario
                and item["candidate"] == controller
                and item["comparator"] == "vehicle_actuated"
            )
            mean = float(row["mean_wait_delta_candidate_minus_comparator_seconds"])
            means.append(mean)
            lower.append(mean - float(row["ci95_low_seconds"]))
            upper.append(float(row["ci95_high_seconds"]) - mean)
        axis.errorbar(
            x + offset,
            means,
            yerr=[lower, upper],
            marker="o",
            capsize=3,
            label=label,
        )
    axis.axhline(0, color="black", linewidth=1)
    axis.set_xticks(x, labels, rotation=15)
    axis.set_ylabel("Парная разность среднего ожидания, с\n(кандидат минус Vehicle-actuated)")
    axis.grid(True, axis="y", alpha=0.25)
    axis.legend()
    _save(fig, "paired_wait_delta_vs_vehicle_actuated")


def main() -> None:
    summary = _read(METRICS)
    paired = _read(PAIRED)
    _metric_plot(summary, "average_wait_seconds", "Среднее ожидание выехавших, с", "wait_by_demand")
    _metric_plot(summary, "phase_switches", "Переключения за 1800 с", "switches_by_demand")
    _metric_plot(summary, "throughput_per_hour", "Пропускная способность, авто/ч", "throughput_by_demand")
    _metric_plot(summary, "yellow_fraction", "Доля горизонта на жёлтом", "yellow_fraction_by_demand")
    _paired_wait_plot(paired)
    print("wrote 5 figures (PNG/SVG) under", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
