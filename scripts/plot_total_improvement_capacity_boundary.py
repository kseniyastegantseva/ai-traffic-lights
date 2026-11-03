"""Plot the 9–18 vehicles/minute development capacity boundary."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/total_improvement/figures/capacity_boundary_1800"
METRICS = ROOT / "outputs/total_improvement/capacity_boundary_1800_metrics.csv"
PAIRED = ROOT / "outputs/total_improvement/capacity_boundary_1800_paired.csv"
DEMANDS = tuple(f"demand_{rate}" for rate in range(9, 19))
LABELS = tuple(str(rate) for rate in range(9, 19))
CONTROLLERS = {
    "fixed_8": "Fixed 8 s",
    "fixed_15": "Fixed 15 s",
    "fixed_35": "Fixed 35 s",
    "fixed_webster": "Webster",
    "vehicle_actuated": "Vehicle-actuated",
    "queue_based": "Queue-based",
    "queue_based_legacy": "Legacy",
    "queue_based_improved": "Improved",
    "queue_based_empty_gap_1s": "Empty-gap 1 s",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def save(fig: plt.Figure, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", dpi=180)
    svg_path = OUT / f"{name}.svg"
    fig.savefig(svg_path)
    svg_lines = svg_path.read_text(encoding="utf-8").splitlines()
    svg_path.write_text("\n".join(line.rstrip() for line in svg_lines) + "\n", encoding="utf-8")
    plt.close(fig)


def metric_plot(rows: list[dict[str, str]], metric: str, ylabel: str, name: str) -> None:
    fig, axis = plt.subplots(figsize=(10, 6))
    x = np.arange(len(DEMANDS))
    for controller, label in CONTROLLERS.items():
        values, errors = [], []
        for scenario in DEMANDS:
            row = next(
                item
                for item in rows
                if item["scenario"] == scenario and item["controller"] == controller
            )
            n = int(row["runs"])
            values.append(float(row[metric]))
            errors.append(
                float(student_t.ppf(0.975, n - 1))
                * float(row[f"{metric}_sd"])
                / np.sqrt(n)
            )
        axis.errorbar(x, values, yerr=errors, marker="o", markersize=3, capsize=2, label=label)
    axis.set_xticks(x, LABELS)
    axis.set_xlabel("Интенсивность, автомобилей/мин/подход")
    axis.set_ylabel(ylabel)
    axis.grid(True, alpha=0.25)
    axis.legend(ncol=3, fontsize=8)
    save(fig, name)


def oriented_pair(row: dict[str, str], controller_a: str, controller_b: str) -> tuple[float, float, float]:
    mean = float(row["mean_delta_a_minus_b"])
    low = float(row["ci95_low"])
    high = float(row["ci95_high"])
    if (row["controller_a"], row["controller_b"]) == (controller_a, controller_b):
        return mean, low, high
    return -mean, -high, -low


def contrast_plot(rows: list[dict[str, str]]) -> None:
    fig, axis = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(DEMANDS))
    pairs = (
        ("queue_based", "vehicle_actuated", "Queue-based − VA"),
        ("queue_based_improved", "vehicle_actuated", "Improved − VA"),
        ("queue_based_improved", "fixed_webster", "Improved − Webster"),
    )
    offsets = (-0.18, 0.0, 0.18)
    for offset, (first, second, label) in zip(offsets, pairs, strict=True):
        means, lower, upper = [], [], []
        for scenario in DEMANDS:
            row = next(
                item
                for item in rows
                if item["scenario"] == scenario
                and item["metric"] == "average_wait_seconds"
                and {item["controller_a"], item["controller_b"]} == {first, second}
            )
            mean, low, high = oriented_pair(row, first, second)
            means.append(mean)
            lower.append(mean - low)
            upper.append(high - mean)
        axis.errorbar(
            x + offset,
            means,
            yerr=[lower, upper],
            marker="o",
            markersize=3,
            capsize=2,
            label=label,
        )
    axis.axhline(0, color="black", linewidth=1)
    axis.set_xticks(x, LABELS)
    axis.set_xlabel("Интенсивность, автомобилей/мин/подход")
    axis.set_ylabel("Парная разность среднего ожидания, с")
    axis.grid(True, axis="y", alpha=0.25)
    axis.legend()
    save(fig, "paired_wait_contrasts")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=int, choices=(1800, 3600), default=1800)
    duration = parser.parse_args().duration
    global OUT, METRICS, PAIRED
    OUT = ROOT / f"outputs/total_improvement/figures/capacity_boundary_{duration}"
    METRICS = ROOT / f"outputs/total_improvement/capacity_boundary_{duration}_metrics.csv"
    PAIRED = ROOT / f"outputs/total_improvement/capacity_boundary_{duration}_paired.csv"
    metrics = read_rows(METRICS)
    paired = read_rows(PAIRED)
    metric_plot(metrics, "average_wait_seconds", "Среднее ожидание завершивших, с", "wait")
    metric_plot(metrics, "queue_area_vehicle_seconds", "Площадь очереди, авто·с", "queue_area")
    metric_plot(metrics, "throughput_per_hour", "Пропускная способность, авто/ч", "throughput")
    metric_plot(metrics, "residual_vehicles", "Остаток ожидающих/обслуживаемых, авто", "residual")
    metric_plot(metrics, "yellow_fraction", "Доля горизонта на жёлтом", "yellow_fraction")
    metric_plot(metrics, "phase_switches", "Переключения за 1800 с", "switches")
    metric_plot(metrics, "max_red_seconds", "Максимальное red indication, с", "max_signal_red")
    contrast_plot(paired)
    print("wrote 8 figures (PNG/SVG) under", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
