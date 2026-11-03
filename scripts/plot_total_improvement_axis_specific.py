"""Plot axis-specific congestion development metrics and paired wait differences."""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/total_improvement/figures/axis_specific_congestion_1800"
STEM = "axis_specific_congestion_1800"


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
    policies = ["vehicle_actuated", "queue_based", "queue_based_improved", "queue_based_axis_specific_congestion"]
    labels = {
        "vehicle_actuated": "Vehicle-actuated",
        "queue_based": "Queue-based",
        "queue_based_improved": "Improved",
        "queue_based_axis_specific_congestion": "Axis-specific",
    }
    x = np.arange(len(scenarios))
    for metric, ylabel, filename in (
        ("average_wait_seconds", "Completed mean wait, s", "wait_by_scenario"),
        ("residual_vehicles", "Residual vehicles at 1800 s", "residual_by_scenario"),
        ("phase_switches", "Phase switches per 1800 s", "switches_by_scenario"),
    ):
        fig, axis = plt.subplots(figsize=(11, 6))
        for policy in policies:
            by_scenario = {row["scenario"]: row for row in summary if row["controller"] == policy}
            axis.plot(x, [float(by_scenario[name][metric]) for name in scenarios], marker="o", label=labels[policy])
        axis.set_xticks(x, scenarios, rotation=25, ha="right")
        axis.set_ylabel(ylabel)
        axis.set_xlabel("Scenario")
        axis.grid(True, alpha=0.25)
        axis.legend(ncol=2)
        save(fig, filename)

    paired = [row for row in read("paired") if row["metric"] == "average_wait_seconds"]
    selected = []
    for scenario in scenarios:
        row = next(
            item for item in paired
            if item["scenario"] == scenario
            and {item["controller_a"], item["controller_b"]}
            == {"queue_based_axis_specific_congestion", "queue_based_improved"}
        )
        sign = 1 if row["controller_a"] == "queue_based_axis_specific_congestion" else -1
        mean = sign * float(row["mean_delta_a_minus_b"])
        low, high = float(row["ci95_low"]), float(row["ci95_high"])
        ci_low, ci_high = (low, high) if sign == 1 else (-high, -low)
        selected.append((mean, mean - ci_low, ci_high - mean))
    means = [item[0] for item in selected]
    fig, axis = plt.subplots(figsize=(10, 5.5))
    axis.errorbar(x, means, yerr=[[item[1] for item in selected], [item[2] for item in selected]], fmt="o", capsize=4)
    axis.axhline(0, color="black", linewidth=1)
    axis.set_xticks(x, scenarios, rotation=25, ha="right")
    axis.set_ylabel("Axis-specific − Improved, s (95% paired CI)")
    axis.set_xlabel("Scenario")
    axis.grid(True, axis="y", alpha=0.25)
    save(fig, "paired_wait_delta")
    print(f"wrote 4 figures under {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
