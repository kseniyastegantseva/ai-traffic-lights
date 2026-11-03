"""Plot the exploratory and independent validation min-green comparisons."""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/total_improvement/figures/min_green_dynamics_1800"
STEM = "min_green_dynamics_1800"


def read_csv(stem: str, suffix: str) -> list[dict[str, str]]:
    with (ROOT / f"outputs/total_improvement/{stem}_{suffix}.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        return list(csv.DictReader(handle))


def save(fig: plt.Figure, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", dpi=180)
    fig.savefig(OUT / f"{name}.svg")
    svg = OUT / f"{name}.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
    plt.close(fig)


def main() -> None:
    metrics = read_csv(STEM, "metrics")
    chosen = [
        "vehicle_actuated",
        "queue_based_improved",
        "queue_based_smooth_min_green_10_18",
        "queue_based_hysteresis_14_10",
        "queue_based_persistent_5s",
        "queue_based_persistent_10s",
    ]
    labels = {
        "vehicle_actuated": "Vehicle-actuated",
        "queue_based_improved": "Improved",
        "queue_based_smooth_min_green_10_18": "Smooth 10–18",
        "queue_based_hysteresis_14_10": "Hysteresis 14/10",
        "queue_based_persistent_5s": "Persistent 5 s",
        "queue_based_persistent_10s": "Persistent 10 s",
    }
    scenarios = list(dict.fromkeys(row["scenario"] for row in metrics))
    x = np.arange(len(scenarios))
    fig, axis = plt.subplots(figsize=(11, 6))
    for controller in chosen:
        lookup = {row["scenario"]: row for row in metrics if row["controller"] == controller}
        axis.plot(x, [float(lookup[name]["average_wait_seconds"]) for name in scenarios], marker="o", label=labels[controller])
    axis.set_xticks(x, scenarios, rotation=25, ha="right")
    axis.set_ylabel("Среднее завершённое ожидание, с")
    axis.set_xlabel("Сценарий")
    axis.grid(True, alpha=0.25)
    axis.legend(ncol=2, fontsize=8)
    save(fig, "wait_by_scenario")

    validation = read_csv("min_green_validation_1800", "paired")
    means = [float(row["mean_wait_delta_smooth_minus_improved"]) for row in validation]
    lows = [mean - float(row["ci95_low"]) for mean, row in zip(means, validation, strict=True)]
    highs = [float(row["ci95_high"]) - mean for mean, row in zip(means, validation, strict=True)]
    fig, axis = plt.subplots(figsize=(10, 5.5))
    axis.errorbar(np.arange(len(validation)), means, yerr=[lows, highs], fmt="o", capsize=4)
    axis.axhline(0, color="black", linewidth=1)
    axis.set_xticks(np.arange(len(validation)), [row["scenario"] for row in validation], rotation=25, ha="right")
    axis.set_ylabel("Smooth ramp − Improved, с (95% paired CI)")
    axis.set_xlabel("Новый validation сценарий")
    axis.grid(True, axis="y", alpha=0.25)
    save(fig, "validation_paired_wait_delta")
    print(f"wrote 2 figures under {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
