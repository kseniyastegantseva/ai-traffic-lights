"""Plot switching-margin development metrics and paired wait contrasts."""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/total_improvement/figures/switching_margin_1800"
STEM = "switching_margin_1800"
VARIANTS = [
    "margin_abs0_rel000",
    "margin_abs1_rel000",
    "margin_abs2_rel000",
    "margin_abs1_rel020",
    "margin_elapsed_decay_0025",
]


def read(name: str) -> list[dict[str, str]]:
    with (ROOT / f"outputs/total_improvement/{STEM}_{name}.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def save(fig: plt.Figure, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", dpi=180)
    svg = OUT / f"{name}.svg"
    fig.savefig(svg)
    svg.write_text(
        "\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
    )
    plt.close(fig)


def main() -> None:
    summary = read("metrics")
    scenarios = list(dict.fromkeys(row["scenario"] for row in summary))
    x = np.arange(len(scenarios))
    labels = {
        "vehicle_actuated": "Vehicle-actuated",
        "queue_based": "Queue-based",
        "improved_abs1_rel010": "Improved 1/.10",
        "margin_abs0_rel000": "Margin 0/0",
        "margin_abs1_rel000": "Margin 1/0",
        "margin_abs2_rel000": "Margin 2/0",
        "margin_abs1_rel020": "Margin 1/.20",
        "margin_elapsed_decay_0025": "Time-decay",
    }
    for metric, ylabel, filename in (
        ("average_wait_seconds", "Completed mean wait, s", "wait_by_scenario"),
        ("phase_switches", "Phase switches per 1800 s", "switches_by_scenario"),
        ("yellow_fraction", "Time spent in yellow, %", "yellow_fraction_by_scenario"),
    ):
        fig, axis = plt.subplots(figsize=(11, 6))
        for policy, label in labels.items():
            selected = {row["scenario"]: row for row in summary if row["controller"] == policy}
            values = [float(selected[name][metric]) for name in scenarios]
            if metric == "yellow_fraction":
                values = [100 * value for value in values]
            axis.plot(x, values, marker="o", label=label)
        axis.set_xticks(x, scenarios, rotation=25, ha="right")
        axis.set_ylabel(ylabel)
        axis.set_xlabel("Scenario")
        axis.grid(True, alpha=0.25)
        axis.legend(ncol=2, fontsize=8)
        save(fig, filename)

    paired = read("paired")
    fig, axis = plt.subplots(figsize=(12, 6))
    offsets = np.linspace(-0.24, 0.24, len(VARIANTS))
    for offset, variant in zip(offsets, VARIANTS, strict=True):
        means, lows, highs = [], [], []
        for scenario in scenarios:
            row = next(
                item for item in paired
                if item["scenario"] == scenario
                and item["metric"] == "average_wait_seconds"
                and "improved_abs1_rel010" in {item["controller_a"], item["controller_b"]}
                and variant in {item["controller_a"], item["controller_b"]}
            )
            sign = 1 if row["controller_a"] == variant else -1
            mean = sign * float(row["mean_delta_a_minus_b"])
            lo, hi = float(row["ci95_low"]), float(row["ci95_high"])
            ci_low, ci_high = (lo, hi) if sign == 1 else (-hi, -lo)
            means.append(mean)
            lows.append(mean - ci_low)
            highs.append(ci_high - mean)
        axis.errorbar(x + offset, means, yerr=[lows, highs], marker="o", capsize=2, label=labels[variant])
    axis.axhline(0, color="black", linewidth=1)
    axis.set_xticks(x, scenarios, rotation=25, ha="right")
    axis.set_ylabel("Variant − Improved, s (95% paired CI)")
    axis.set_xlabel("Scenario")
    axis.grid(True, axis="y", alpha=0.25)
    axis.legend(ncol=2, fontsize=8)
    save(fig, "paired_wait_deltas")

    validation_path = ROOT / "outputs/total_improvement/switching_margin_validation_1800_paired.csv"
    with validation_path.open(encoding="utf-8", newline="") as handle:
        validation = list(csv.DictReader(handle))
    fig, axis = plt.subplots(figsize=(11, 5.5))
    offset = {"improved_abs1_rel010": -0.11, "vehicle_actuated": 0.11}
    label = {"improved_abs1_rel010": "vs Improved", "vehicle_actuated": "vs Vehicle-actuated"}
    for comparator in offset:
        selected = [row for row in validation if row["comparator"] == comparator]
        means = [float(row["mean_wait_delta_candidate_minus_comparator"]) for row in selected]
        lows = [mean - float(row["ci95_low"]) for mean, row in zip(means, selected, strict=True)]
        highs = [float(row["ci95_high"]) - mean for mean, row in zip(means, selected, strict=True)]
        axis.errorbar(
            x + offset[comparator], means,
            yerr=[lows, highs], marker="o", capsize=3, label=label[comparator],
        )
    axis.axhline(0, color="black", linewidth=1)
    axis.set_xticks(x, scenarios, rotation=25, ha="right")
    axis.set_ylabel("Relative margin 0,20 − comparator, s (95% paired CI)")
    axis.set_xlabel("Independent validation scenario")
    axis.grid(True, axis="y", alpha=0.25)
    axis.legend()
    save(fig, "validation_paired_wait_deltas")
    print(f"wrote 5 figures under {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
