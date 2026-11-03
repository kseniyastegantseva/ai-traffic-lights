"""Plot fairness and paired waiting-time results for the max-red screen."""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/total_improvement/figures/max_red_development_1800"
STEM = "max_red_development_1800"
VARIANTS = [f"queue_based_max_red_{limit}s" for limit in (36, 42, 48)]
LABELS = {36: "cap 36 s", 42: "cap 42 s", 48: "cap 48 s"}


def rows(name: str) -> list[dict[str, str]]:
    with (ROOT / f"outputs/total_improvement/{STEM}_{name}.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
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


def main() -> None:
    summary = rows("metrics")
    paired = rows("paired")
    scenarios = list(dict.fromkeys(row["scenario"] for row in summary))
    x = np.arange(len(scenarios))

    fig, axis = plt.subplots(figsize=(11, 6))
    comparison = [
        "vehicle_actuated",
        "queue_based_improved",
        *VARIANTS,
    ]
    for controller in comparison:
        selected = {
            row["scenario"]: row
            for row in summary
            if row["controller"] == controller
        }
        values = [float(selected[scenario]["max_signal_red_seconds"]) for scenario in scenarios]
        label = controller.replace("queue_based_max_red_", "cap ").replace("vehicle_actuated", "VA").replace(
            "queue_based_improved", "Improved"
        )
        axis.plot(x, values, marker="o", label=label)
    axis.set_xticks(x, scenarios, rotation=25, ha="right")
    axis.set_ylabel("Максимальный непрерывный red, с")
    axis.set_xlabel("Сценарий")
    axis.grid(True, alpha=0.25)
    axis.legend(ncol=2)
    save(fig, "max_signal_red_by_scenario")

    fig, axis = plt.subplots(figsize=(11, 6))
    colors = {36: "#1f77b4", 42: "#ff7f0e", 48: "#2ca02c"}
    offsets = {36: -0.16, 42: 0.0, 48: 0.16}
    for comparator, linestyle in (("queue_based_improved", "-"), ("vehicle_actuated", "--")):
        for limit, controller in zip((36, 42, 48), VARIANTS, strict=True):
            means, lows, highs = [], [], []
            for scenario in scenarios:
                match = next(
                    row
                    for row in paired
                    if row["scenario"] == scenario
                    and row["metric"] == "average_wait_seconds"
                    and {row["controller_a"], row["controller_b"]} == {controller, comparator}
                )
                sign = 1 if match["controller_a"] == controller else -1
                mean = sign * float(match["mean_delta_a_minus_b"])
                low = sign * float(match["ci95_low"] if sign == 1 else match["ci95_high"])
                high = sign * float(match["ci95_high"] if sign == 1 else match["ci95_low"])
                means.append(mean)
                lows.append(mean - low)
                highs.append(high - mean)
            label = f"{LABELS[limit]} − {'Improved' if comparator.endswith('improved') else 'VA'}"
            axis.errorbar(
                x + offsets[limit],
                means,
                yerr=[lows, highs],
                marker="o",
                capsize=2,
                color=colors[limit],
                linestyle=linestyle,
                label=label,
            )
    axis.axhline(0, color="black", linewidth=1)
    axis.set_xticks(x, scenarios, rotation=25, ha="right")
    axis.set_ylabel("Парная разница completed mean wait, с")
    axis.set_xlabel("Сценарий")
    axis.grid(True, axis="y", alpha=0.25)
    axis.legend(ncol=2, fontsize=8)
    save(fig, "paired_wait_deltas")

    fig, axis = plt.subplots(figsize=(11, 5.5))
    for controller in comparison:
        selected = {
            row["scenario"]: row
            for row in summary
            if row["controller"] == controller
        }
        values = [float(selected[scenario]["fairness_index"]) for scenario in scenarios]
        label = controller.replace("queue_based_max_red_", "cap ").replace("vehicle_actuated", "VA").replace(
            "queue_based_improved", "Improved"
        )
        axis.plot(x, values, marker="o", label=label)
    axis.set_xticks(x, scenarios, rotation=25, ha="right")
    axis.set_ylim(0, 1.02)
    axis.set_ylabel("Jain index по среднему ожиданию подходов")
    axis.set_xlabel("Сценарий")
    axis.grid(True, alpha=0.25)
    axis.legend(ncol=2)
    save(fig, "fairness_by_scenario")
    print(f"wrote 3 figures under {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
