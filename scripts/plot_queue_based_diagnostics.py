"""Create the eight requested reproducible diagnostic figures (PNG/SVG/PDF)."""
from __future__ import annotations

import ast
import csv
import gzip
import json
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from build_queue_based_final_report import phase_metrics
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/queue_based_diagnostics"
CONTROLLERS = ("queue_based", "queue_based_improved", "fixed_webster", "vehicle_actuated")
LABEL = {
    "queue_based": "Queue-based original",
    "queue_based_improved": "Queue-based improved",
    "fixed_webster": "Fixed Webster",
    "vehicle_actuated": "Vehicle-actuated",
    "fixed_8": "Fixed 8 s",
    "fixed_15": "Fixed 15 s",
    "fixed_35": "Fixed 35 s",
}
COLORS = {
    "queue_based": "#c43c39",
    "queue_based_improved": "#2a7f62",
    "fixed_webster": "#3973ac",
    "vehicle_actuated": "#e0952c",
    "fixed_8": "#7551a6",
    "fixed_15": "#718d3d",
    "fixed_35": "#58616a",
}


def load_json(path: Path) -> dict:
    if not path.exists() and path.suffix == ".json":
        path = path.with_suffix(path.suffix + ".gz")
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def save(fig: plt.Figure, stem: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg", "pdf"):
        fig.savefig(OUT / f"{stem}.{ext}", dpi=180, bbox_inches="tight")
    plt.close(fig)


def phase_hist(row: dict) -> list[float]:
    lengths = []
    history = row["phase_history"]
    for index, event in enumerate(history):
        if event["color"] != "green":
            continue
        if index + 1 < len(history) and history[index + 1]["color"] == "yellow":
            lengths.append(float(history[index + 1]["at"]) - float(event["at"]))
    return lengths


def mean_and_sem(rows: list[dict], metric: str) -> tuple[list[str], list[float], list[float]]:
    controllers = [name for name in CONTROLLERS if any(row["controller"] == name for row in rows)]
    means, errors = [], []
    for name in controllers:
        values = [float(row[metric]) for row in rows if row["controller"] == name]
        means.append(statistics.mean(values))
        errors.append(statistics.stdev(values) / len(values) ** 0.5 if len(values) > 1 else 0.0)
    return controllers, means, errors


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    runs = []
    for duration in (1800, 3600):
        payload = load_json(ROOT / f"outputs/queue_based_final_{duration}.json")
        runs.extend(payload["runs"])

    for duration in (1800, 3600):
        trace_file = ROOT / f"outputs/queue_based_diagnostic_traces_{duration}.csv"
        trace_groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
        with trace_file.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if int(row["seed"]) == 1001:
                    row["queues"] = ast.literal_eval(row["queues"])
                    trace_groups[(row["scenario"], row["controller"])].append(row)
        fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        for ax, scenario, title in zip(
            axes,
            ("high_load", "true_oversaturated"),
            ("Высокая нагрузка: 18 авто/мин на подход", "Перегрузка: 24 авто/мин на подход"),
            strict=True,
        ):
            for controller in CONTROLLERS:
                frames = trace_groups.get((scenario, controller), [])
                if not frames:
                    continue
                times = [int(frame["second"]) for frame in frames]
                ns = [sum(frame["queues"][lane] for lane in ("north", "south")) for frame in frames]
                ew = [sum(frame["queues"][lane] for lane in ("east", "west")) for frame in frames]
                ax.plot(times, ns, color=COLORS[controller], lw=1.1, label=f"{LABEL[controller]} · N/S")
                ax.plot(times, ew, color=COLORS[controller], lw=1.1, ls="--", alpha=0.8, label=f"{LABEL[controller]} · E/W")
            ax.set_title(title)
            ax.set_ylabel("Очередь, автомобили")
            ax.grid(alpha=0.25)
        axes[-1].set_xlabel(f"Время, с; горизонт {duration} с, seed 1001, парные потоки")
        axes[0].legend(ncol=4, fontsize=8)
        save(fig, f"01_directional_queues_{duration}")

    high = [row for row in runs if row["scenario"] == "high_load" and row["duration_seconds"] == 3600 and row["controller"] in CONTROLLERS]
    fig, ax = plt.subplots(figsize=(9, 5))
    data = [
        [length for row in high if row["controller"] == name for length in phase_hist(row)]
        for name in CONTROLLERS
    ]
    ax.boxplot(data, showfliers=False)
    ax.set_xticks(np.arange(1, len(CONTROLLERS) + 1), [LABEL[name] for name in CONTROLLERS])
    ax.set_ylabel("Зелёная фаза, с (полные наблюдаемые фазы)")
    ax.set_title("Распределение длительности зелёного при 18 авто/мин на подход")
    ax.tick_params(axis="x", rotation=18)
    ax.grid(axis="y", alpha=0.25)
    save(fig, "02_green_duration_distribution")

    for metric, stem, title, ylabel in (
        ("switches", "03_switches", "Число переключений при 18 авто/мин на подход", "Переключения за прогон"),
        ("yellow_seconds", "04_yellow_time", "Потери времени на жёлтом при 18 авто/мин на подход", "Жёлтый, с за прогон"),
    ):
        selected = [row for row in high]
        values = {name: [phase_metrics(row)[metric] for row in selected if row["controller"] == name] for name in CONTROLLERS}
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.boxplot([values[name] for name in CONTROLLERS], showfliers=False)
        ax.set_xticks(np.arange(1, len(CONTROLLERS) + 1), [LABEL[name] for name in CONTROLLERS])
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.tick_params(axis="x", rotation=18)
        ax.grid(axis="y", alpha=0.25)
        save(fig, stem)

    audit_path = ROOT / "outputs/queue_based_final_replay_metrics.json"
    audits = load_json(audit_path)
    replay = [row for result in audits for row in result["runs"]]
    for scenario in ("high_load", "true_oversaturated"):
        subset = [row for row in replay if row["scenario"] == scenario and row["duration_seconds"] == 3600 and row["controller"] in CONTROLLERS]
        controllers = [name for name in CONTROLLERS if any(row["controller"] == name for row in subset)]
        for metric, name_part, title_part, ylabel in (
            ("green_utilization", "utilization", "Использование зелёного", "Занятость зелёного, доля доступного lane-time"),
            ("green_idle_fraction", "idle_fraction", "Простой зелёного", "Доля доступного lane-time без обслуживания"),
        ):
            means, errors = [], []
            for controller in controllers:
                vals = [row[metric] for row in subset if row["controller"] == controller]
                means.append(statistics.mean(vals))
                errors.append(
                    float(student_t.ppf(0.975, len(vals) - 1))
                    * statistics.stdev(vals)
                    / len(vals) ** 0.5
                    if len(vals) > 1
                    else 0.0
                )
            fig, ax = plt.subplots(figsize=(9, 5))
            ax.bar([LABEL[name] for name in controllers], means, yerr=errors, capsize=4,
                   color=[COLORS[name] for name in controllers])
            ax.set_ylim(0, 1.05)
            ax.set_ylabel(ylabel)
            ax.set_title(f"{title_part}: {scenario}")
            ax.tick_params(axis="x", rotation=18)
            ax.grid(axis="y", alpha=0.25)
            save(fig, f"05_{name_part}_{scenario}")

    scenario_order = ["symmetric_low", "symmetric", "symmetric_9", "asymmetric_ns", "asymmetric_ew", "variable_demand", "sudden_dominance_switch", "high_load", "true_oversaturated"]
    scenario_labels = {row["scenario"]: row["scenario_title"] for row in runs}
    for metric, stem, title, ylabel in (
        ("throughput_per_hour", "06_throughput", "Пропускная способность по сценариям", "автомобилей/ч"),
        ("waiting_at_end", "07_residual_queue", "Остаточная очередь на горизонте", "ожидающих автомобилей"),
        ("average_wait_seconds", "08_wait_by_demand", "Среднее ожидание завершивших обслуживание", "секунды"),
    ):
        durations = (1800, 3600)
        fig, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=True)
        for ax, duration in zip(axes, durations, strict=True):
            scenario_names = [name for name in scenario_order if any(row["scenario"] == name and row["duration_seconds"] == duration for row in runs)]
            x = np.arange(len(scenario_names))
            for controller in ("fixed_8", "fixed_15", "fixed_35", "fixed_webster", "vehicle_actuated", "queue_based", "queue_based_improved"):
                means, lows, highs = [], [], []
                for scenario in scenario_names:
                    vals = [float(row[metric]) for row in runs if row["scenario"] == scenario and row["duration_seconds"] == duration and row["controller"] == controller]
                    if not vals:
                        means.append(np.nan); lows.append(0); highs.append(0); continue
                    avg = statistics.mean(vals)
                    half = (
                        float(student_t.ppf(0.975, len(vals) - 1))
                        * statistics.stdev(vals)
                        / len(vals) ** 0.5
                        if len(vals) > 1
                        else 0.0
                    )
                    means.append(avg); lows.append(half); highs.append(half)
                ax.errorbar(x, means, yerr=[lows, highs], marker="o", ms=3, lw=1, capsize=2,
                            color=COLORS.get(controller, "#444444"), label=LABEL.get(controller, controller))
            ax.set_title(f"Горизонт {duration} с")
            ax.set_ylabel(ylabel)
            ax.grid(alpha=0.25)
        axes[-1].set_xticks(np.arange(len(scenario_names)), [scenario_labels.get(name, name) for name in scenario_names], rotation=22, ha="right")
        axes[0].legend(ncol=4, fontsize=8)
        fig.suptitle(title)
        save(fig, stem)
    print("created 12 figures × PNG/SVG/PDF in outputs/queue_based_diagnostics")


if __name__ == "__main__":
    main()
