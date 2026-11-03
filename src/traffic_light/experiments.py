from __future__ import annotations

import json
import math
import platform
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from statistics import mean, stdev

import pandas as pd
from scipy.stats import t as student_t

from traffic_light.config import (
    ControllerConfig,
    ExperimentConfig,
    IntersectionConfig,
    SimulationConfig,
)
from traffic_light.controllers import (
    ActuatedController,
    AIPhaseController,
    BaseController,
    FixedTimeController,
    FixedWebsterController,
    QLearningPolicyController,
    QueueBasedController,
    QueueBasedEmptyGapFixController,
    QueueBasedImprovedController,
    QueueBasedMaxRedController,
    VehicleActuatedController,
)
from traffic_light.simulation import generate_arrivals, run_simulation

BASELINE_CONTROLLERS = ("fixed_35", "fixed")


def build_controller(
    config: ControllerConfig,
    min_green_seconds: int,
    intersection: IntersectionConfig | None = None,
) -> BaseController:
    if config.type in {"fixed", "fixed_8", "fixed_15", "fixed_35"}:
        duration = config.phase_duration_seconds
        if config.type == "fixed_8":
            duration = 8
        elif config.type == "fixed_15":
            duration = 15
        elif config.type == "fixed_35":
            duration = 35
        return FixedTimeController(
            phase_duration_seconds=duration,
            name=config.type if config.type != "fixed" else "fixed",
        )
    if config.type == "actuated":
        return ActuatedController(
            min_green_seconds=min_green_seconds,
            decision_interval_seconds=config.decision_interval_seconds,
        )
    if config.type == "fixed_webster":
        if intersection is None:
            raise ValueError("fixed_webster requires intersection demand rates")
        rates = intersection.lanes
        ratios = {
            "north_south": max(rates["north"].arrival_rate_per_minute, rates["south"].arrival_rate_per_minute) / 30.0,
            "east_west": max(rates["east"].arrival_rate_per_minute, rates["west"].arrival_rate_per_minute) / 30.0,
        }
        green = FixedWebsterController.green_split(
            ratios, 2 * intersection.yellow_seconds, max(8, min_green_seconds), config.max_green_seconds
        )
        return FixedWebsterController(green_seconds=green, min_green_seconds=min_green_seconds)
    if config.type == "vehicle_actuated":
        return VehicleActuatedController(
            min_green_seconds=config.min_green_seconds,
            max_green_seconds=config.max_green_seconds,
        )
    if config.type == "queue_based":
        return QueueBasedController(
            min_green_seconds=config.min_green_seconds,
            max_green_seconds=config.max_green_seconds,
            switching_margin=config.switching_margin,
            legacy_rule=config.legacy_rule,
            name="queue_based_legacy" if config.legacy_rule else "queue_based",
        )
    if config.type == "queue_based_improved":
        return QueueBasedImprovedController(
            min_green_seconds=config.min_green_seconds,
            max_green_seconds=config.max_green_seconds,
            switching_margin=config.switching_margin,
            relative_switching_margin=config.relative_switching_margin,
            congested_min_green_seconds=config.congested_min_green_seconds,
            congestion_queue_threshold=config.congestion_queue_threshold,
            name=config.result_name or "queue_based_improved",
        )
    if config.type == "queue_based_empty_gap_fix":
        return QueueBasedEmptyGapFixController(
            min_green_seconds=config.min_green_seconds,
            max_green_seconds=config.max_green_seconds,
            switching_margin=config.switching_margin,
            relative_switching_margin=config.relative_switching_margin,
            congested_min_green_seconds=config.congested_min_green_seconds,
            congestion_queue_threshold=config.congestion_queue_threshold,
            empty_gap_seconds=config.empty_gap_seconds,
            name=config.result_name or "queue_based_empty_gap_fix",
        )
    if config.type == "queue_based_max_red":
        return QueueBasedMaxRedController(
            min_green_seconds=config.min_green_seconds,
            max_green_seconds=config.max_green_seconds,
            switching_margin=config.switching_margin,
            relative_switching_margin=config.relative_switching_margin,
            congested_min_green_seconds=config.congested_min_green_seconds,
            congestion_queue_threshold=config.congestion_queue_threshold,
            max_red_seconds=config.max_red_seconds,
            name=config.result_name or "queue_based_max_red",
        )
    if config.type == "ai":
        return AIPhaseController(
            min_green_seconds=min_green_seconds,
            decision_interval_seconds=config.decision_interval_seconds,
        )
    return QLearningPolicyController(
        policy_path=config.policy_path,
        min_green_seconds=min_green_seconds,
        decision_interval_seconds=config.decision_interval_seconds,
    )


def run_experiment(config: ExperimentConfig) -> tuple[list[dict], pd.DataFrame]:
    rows: list[dict] = []
    for scenario in _iter_scenarios(config):
        for seed in config.simulation.seeds:
            simulation = SimulationConfig(
                duration_seconds=config.simulation.duration_seconds,
                seed=seed,
                service_time_seconds=config.simulation.service_time_seconds,
                observation_error_rate=scenario.get("observation_error_rate", 0.0),
                empirical_observation_errors_by_lane=(
                    config.simulation.empirical_observation_errors_by_lane
                ),
            )
            arrivals = generate_arrivals(
                scenario["intersection"], simulation, scenario.get("demand_schedule")
            )
            for controller_config in config.controllers:
                controller = build_controller(
                    controller_config,
                    min_green_seconds=scenario["intersection"].min_green_seconds,
                    intersection=scenario["intersection"],
                )
                result = run_simulation(
                    scenario["intersection"],
                    simulation,
                    controller,
                    initial_queues=scenario.get("initial_queues"),
                    arrivals=arrivals,
                )
                result_record = result.to_dict()
                if not config.simulation.store_queue_series:
                    result_record["queue_series"] = []
                rows.append(
                    {
                        "scenario": scenario["name"],
                        "scenario_title": scenario["title"],
                        "scenario_description": scenario["description"],
                        **result_record,
                    }
                )

    return rows, summarize_results(rows)


def summarize_results(rows: list[dict]) -> pd.DataFrame:
    """Recompute the seed-level summary and exact 95% confidence intervals."""
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "scenario",
                "scenario_title",
                "controller",
                "runs",
                "average_wait_seconds",
                "wait_std",
                "median_wait_seconds",
                "average_queue_length",
                "max_queue_length",
                "throughput_per_hour",
                "fairness_index",
                "stops",
                "wait_95ci_half_width",
                "improvement_reference_controller",
                "wait_improvement_vs_fixed_pct",
            ]
        )
    summary = (
        frame.groupby(["scenario", "scenario_title", "controller"])
        .agg(
            runs=("seed", "count"),
            average_wait_seconds=("average_wait_seconds", "mean"),
            wait_std=("average_wait_seconds", _std_or_zero),
            median_wait_seconds=("median_wait_seconds", "mean"),
            average_queue_length=("average_queue_length", "mean"),
            max_queue_length=("max_queue_length", "mean"),
            throughput_per_hour=("throughput_per_hour", "mean"),
            fairness_index=("fairness_index", "mean"),
            stops=("stops", "mean"),
        )
        .reset_index()
    )
    summary["wait_95ci_half_width"] = summary.apply(
        lambda row: student_t.ppf(0.975, row["runs"] - 1)
        * row["wait_std"]
        / (row["runs"] ** 0.5)
        if row["runs"] > 1
        else 0.0,
        axis=1,
    )
    summary = _add_baseline_improvement(summary)
    return summary


def build_paired_statistics(results: list[dict]) -> list[dict]:
    """Pair queue_based against each controller by scenario, horizon and seed."""
    grouped: dict[tuple[str, int], dict[str, dict[int, float]]] = {}
    for row in results:
        key = (row["scenario"], int(row["duration_seconds"]))
        grouped.setdefault(key, {}).setdefault(row["controller"], {})[int(row["seed"])] = float(
            row["average_wait_seconds"]
        )
    output: list[dict] = []
    for (scenario, duration), controllers in sorted(grouped.items()):
        queue_values = controllers.get("queue_based")
        if not queue_values:
            continue
        for controller, values in sorted(controllers.items()):
            if controller == "queue_based":
                continue
            seeds = sorted(set(queue_values) & set(values))
            differences = [queue_values[seed] - values[seed] for seed in seeds]
            n = len(differences)
            average = mean(differences) if n else 0.0
            deviation = stdev(differences) if n > 1 else 0.0
            half_width = _t_critical_975(n - 1) * deviation / math.sqrt(n) if n > 1 else None
            nonzero = [difference for difference in differences if difference != 0]
            negative = sum(difference < 0 for difference in nonzero)
            positive = len(nonzero) - negative
            smaller = min(negative, positive)
            p_value = (
                min(1.0, 2 * sum(math.comb(len(nonzero), k) for k in range(smaller + 1)) / 2 ** len(nonzero))
                if nonzero
                else 1.0
            )
            output.append(
                {
                    "scenario": scenario,
                    "duration_seconds": duration,
                    "comparator": controller,
                    "pairs": n,
                    "queue_based_minus_comparator_mean_seconds": average,
                    "paired_sd_seconds": deviation,
                    "ci95_low_seconds": average - half_width if half_width is not None else None,
                    "ci95_high_seconds": average + half_width if half_width is not None else None,
                    "sign_test_p": p_value,
                    "holm_p": p_value,
                }
            )
    scenario_keys = sorted({(row["scenario"], row["duration_seconds"]) for row in output})
    for scenario_key in scenario_keys:
        indexes = [
            index
            for index, row in enumerate(output)
            if (row["scenario"], row["duration_seconds"]) == scenario_key
        ]
        ordered = sorted(indexes, key=lambda index: output[index]["sign_test_p"])
        m = len(ordered)
        running_max = 0.0
        for rank, index in enumerate(ordered):
            adjusted = min(1.0, (m - rank) * output[index]["sign_test_p"])
            running_max = max(running_max, adjusted)
            output[index]["holm_p"] = running_max
    return output


def _t_critical_975(degrees_of_freedom: int) -> float:
    """Exact two-sided 95% Student t quantile."""
    if degrees_of_freedom < 1:
        raise ValueError("degrees_of_freedom must be positive")
    return float(student_t.ppf(0.975, degrees_of_freedom))


def _paired_markdown_table(rows: list[dict]) -> str:
    headers = ["scenario", "duration_seconds", "comparator", "pairs", "mean Δ, s", "95% CI, s", "sign p", "Holm p"]
    table = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        ci = "NA" if row["ci95_low_seconds"] is None else f"[{row['ci95_low_seconds']:.2f}, {row['ci95_high_seconds']:.2f}]"
        values = [
            row["scenario"], str(row["duration_seconds"]), row["comparator"], str(row["pairs"]),
            f"{row['queue_based_minus_comparator_mean_seconds']:.2f}", ci,
            _format_p_value(row["sign_test_p"]), _format_p_value(row["holm_p"]),
        ]
        table.append("| " + " | ".join(values) + " |")
    return "\n".join(table)


def _format_p_value(value: float) -> str:
    return "<0.0001" if value < 0.0001 else f"{value:.4f}"


def save_results(
    results: list[dict],
    summary: pd.DataFrame,
    path: str,
    csv_path: str,
    report_path: str,
    config: ExperimentConfig | None = None,
) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    analytics = build_experiment_analytics(summary)
    payload = {
        "result_schema_version": 2,
        "experiment": {
            "name": config.name if config else "experiment",
            "title": config.title if config else "Эксперимент",
            "description": config.description if config else "",
        },
        "configuration": config.model_dump(mode="json") if config else None,
        "environment": _environment_metadata(),
        "runs": results,
        "summary": summary.to_dict(orient="records"),
        "analytics": {
            "scenario_ranking": analytics["scenario_ranking"].to_dict(orient="records"),
            "strategy_overview": analytics["strategy_overview"].to_dict(orient="records"),
            "ai_vs_actuated": analytics["ai_vs_actuated"].to_dict(orient="records"),
        },
        "paired_statistics": build_paired_statistics(results),
    }
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary.to_csv(csv_path, index=False)
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(
        build_markdown_report(summary, config, analytics, results),
        encoding="utf-8",
    )


def build_experiment_analytics(summary: pd.DataFrame) -> dict[str, pd.DataFrame]:
    ranking = summary.copy()
    ranking["wait_rank"] = ranking.groupby("scenario")["average_wait_seconds"].rank(
        method="min",
        ascending=True,
    )
    ranking = ranking.sort_values(["scenario_title", "wait_rank", "controller"]).reset_index(drop=True)

    wins = (
        ranking[ranking["wait_rank"] == 1]
        .groupby("controller")
        .size()
        .rename("scenario_wins")
        .reset_index()
    )
    overview = (
        ranking.groupby("controller")
        .agg(
            scenarios=("scenario", "count"),
            mean_rank=("wait_rank", "mean"),
            mean_wait_seconds=("average_wait_seconds", "mean"),
            mean_improvement_vs_fixed_pct=("wait_improvement_vs_fixed_pct", "mean"),
            mean_queue_length=("average_queue_length", "mean"),
            mean_throughput_per_hour=("throughput_per_hour", "mean"),
            mean_fairness_index=("fairness_index", "mean"),
        )
        .reset_index()
        .merge(wins, on="controller", how="left")
        .fillna({"scenario_wins": 0})
        .sort_values(["mean_rank", "mean_wait_seconds", "controller"])
        .reset_index(drop=True)
    )
    overview["scenario_wins"] = overview["scenario_wins"].astype(int)

    ai_vs_actuated = _build_ai_vs_actuated(summary)
    return {
        "scenario_ranking": ranking,
        "strategy_overview": overview,
        "ai_vs_actuated": ai_vs_actuated,
    }


def build_markdown_report(
    summary: pd.DataFrame,
    config: ExperimentConfig | None = None,
    analytics: dict[str, pd.DataFrame] | None = None,
    results: list[dict] | None = None,
) -> str:
    analytics = analytics or build_experiment_analytics(summary)
    title = config.title if config else "Экспериментальный отчёт"
    description = config.description if config else ""
    lines = [
        f"# {title}",
        "",
    ]
    if description:
        lines.extend([description, ""])
    lines.extend(
        [
            "## Методика",
            "",
            (
                "Для каждой пары сценарий/seed стратегии используют общий хэшированный поток. "
                "Процент изменения среднего ожидания рассчитан относительно указанного в сводной "
                "таблице baseline (`fixed_35` или `fixed`); если baseline не запускался, показано N/A."
            ),
            "",
            "## Сводная таблица",
            "",
            _to_markdown_table(summary),
            "",
            "## Рейтинг стратегий по сценариям",
            "",
            _to_markdown_table(
                analytics["scenario_ranking"],
                [
                    "scenario_title",
                    "controller",
                    "wait_rank",
                    "average_wait_seconds",
                    "wait_improvement_vs_fixed_pct",
                ],
                {
                    "scenario_title": "Сценарий",
                    "controller": "Стратегия",
                    "wait_rank": "Ранг",
                    "average_wait_seconds": "Среднее ожидание, с",
                    "wait_improvement_vs_fixed_pct": "Изменение к baseline, %",
                },
            ),
            "",
            "## Сводка по стратегиям",
            "",
            _to_markdown_table(
                analytics["strategy_overview"],
                [
                    "controller",
                    "scenario_wins",
                    "mean_rank",
                    "mean_wait_seconds",
                    "mean_improvement_vs_fixed_pct",
                    "mean_queue_length",
                    "mean_fairness_index",
                ],
                {
                    "controller": "Стратегия",
                    "scenario_wins": "Победы",
                    "mean_rank": "Средний ранг",
                    "mean_wait_seconds": "Среднее ожидание, с",
                    "mean_improvement_vs_fixed_pct": "Среднее изменение к baseline, %",
                    "mean_queue_length": "Средняя очередь",
                    "mean_fairness_index": "Справедливость",
                },
            ),
            "",
        ]
    )
    comparison = analytics["ai_vs_actuated"]
    if not comparison.empty:
        lines.extend(
            [
                "## AI против adaptive",
                "",
                _to_markdown_table(
                    comparison,
                    [
                        "scenario_title",
                        "ai_wait_seconds",
                        "actuated_wait_seconds",
                        "ai_delta_seconds",
                        "ai_advantage_pct",
                        "better_controller",
                    ],
                    {
                        "scenario_title": "Сценарий",
                        "ai_wait_seconds": "AI, с",
                        "actuated_wait_seconds": "Adaptive, с",
                        "ai_delta_seconds": "AI - adaptive, с",
                        "ai_advantage_pct": "Преимущество AI, %",
                        "better_controller": "Лучше",
                    },
                ),
                "",
            ]
        )
    lines.extend(["## Основные выводы", ""])
    if results:
        lines.extend(["## Парные различия queue_based", ""])
        paired = build_paired_statistics(results)
        lines.extend(
            [
                "Разность определена как ожидание `queue_based` минус ожидание сравниваемого алгоритма; отрицательное значение означает меньшее ожидание у queue_based. Интервалы — 95% доверительные t-интервалы среднего парного различия по точному квантилю Стьюдента. P-value получено двусторонним точным знаковым тестом без нулевых разностей; поправка Holm применяется к фактически присутствующим сравнениям внутри каждой пары сценарий/горизонт.",
                "",
                _paired_markdown_table(paired),
                "",
            ]
        )
    for scenario, scenario_frame in summary.groupby("scenario_title", sort=False):
        best = scenario_frame.sort_values("average_wait_seconds").iloc[0]
        lines.append(
            f"- `{scenario}`: лучшая стратегия `{best['controller']}` со средним ожиданием "
            f"{best['average_wait_seconds']:.2f} с."
        )
    overview = analytics["strategy_overview"]
    if summary.empty or overview.empty:
        lines.append("Недостаточно данных для расчёта выводов.")
        return "\n".join(lines) + "\n"
    best_overall = overview.iloc[0]
    lines.append(
        f"- В среднем по всем сценариям лучшая стратегия по рангу — "
        f"`{best_overall['controller']}`: средний ранг {best_overall['mean_rank']:.2f}, "
        f"побед {int(best_overall['scenario_wins'])}."
    )
    return "\n".join(lines) + "\n"


def _std_or_zero(values) -> float:
    values = list(values)
    return stdev(values) if len(values) > 1 else 0.0


def _iter_scenarios(config: ExperimentConfig) -> list[dict[str, str | IntersectionConfig]]:
    if config.scenarios:
        return [
            {
                "name": scenario.name,
                "title": scenario.title,
                "description": scenario.description,
                "intersection": scenario.intersection,
                "demand_schedule": scenario.demand_schedule,
                "initial_queues": scenario.initial_queues,
                "observation_error_rate": scenario.observation_error_rate,
            }
            for scenario in config.scenarios
        ]
    if config.intersection:
        return [
            {
                "name": "default",
                "title": "Базовый сценарий",
                "description": "Сценарий из корневого поля intersection.",
                "intersection": config.intersection,
            }
        ]
    raise ValueError("Experiment config must define either intersection or scenarios.")


def _add_baseline_improvement(summary: pd.DataFrame) -> pd.DataFrame:
    summary = summary.copy()
    summary["wait_improvement_vs_fixed_pct"] = float("nan")
    summary["improvement_reference_controller"] = None
    for scenario in summary["scenario"].unique():
        mask = summary["scenario"] == scenario
        available_controllers = set(summary.loc[mask, "controller"])
        baseline_name = next(
            (name for name in BASELINE_CONTROLLERS if name in available_controllers),
            None,
        )
        if baseline_name is None:
            continue
        baseline = summary.loc[mask & (summary["controller"] == baseline_name)]
        if baseline.empty:
            continue
        summary.loc[mask, "improvement_reference_controller"] = baseline_name
        baseline_wait = float(baseline.iloc[0]["average_wait_seconds"])
        if baseline_wait <= 0:
            continue
        summary.loc[mask, "wait_improvement_vs_fixed_pct"] = (
            (baseline_wait - summary.loc[mask, "average_wait_seconds"]) / baseline_wait * 100
        )
    return summary


def _environment_metadata() -> dict:
    packages = {}
    for package in (
        "traffic-light-ai",
        "simpy",
        "pandas",
        "pydantic",
        "PyYAML",
        "numpy",
        "scipy",
        "gymnasium",
        "ultralytics",
    ):
        try:
            packages[package] = version(package)
        except PackageNotFoundError:
            packages[package] = None
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        revision = None
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "git_commit": revision,
        "dependencies": packages,
    }


def _build_ai_vs_actuated(summary: pd.DataFrame) -> pd.DataFrame:
    subset = summary[summary["controller"].isin(["ai", "actuated"])].copy()
    pivot = subset.pivot_table(
        index=["scenario", "scenario_title"],
        columns="controller",
        values="average_wait_seconds",
        aggfunc="first",
    ).reset_index()
    if "ai" not in pivot or "actuated" not in pivot:
        return pd.DataFrame(
            columns=[
                "scenario",
                "scenario_title",
                "ai_wait_seconds",
                "actuated_wait_seconds",
                "ai_delta_seconds",
                "ai_advantage_pct",
                "better_controller",
            ]
        )
    pivot["ai_wait_seconds"] = pivot["ai"]
    pivot["actuated_wait_seconds"] = pivot["actuated"]
    pivot["ai_delta_seconds"] = pivot["ai_wait_seconds"] - pivot["actuated_wait_seconds"]
    pivot["ai_advantage_pct"] = (
        (pivot["actuated_wait_seconds"] - pivot["ai_wait_seconds"])
        / pivot["actuated_wait_seconds"]
        * 100
    )
    pivot["better_controller"] = pivot["ai_delta_seconds"].map(
        lambda delta: "ai" if delta < 0 else "actuated"
    )
    return pivot[
        [
            "scenario",
            "scenario_title",
            "ai_wait_seconds",
            "actuated_wait_seconds",
            "ai_delta_seconds",
            "ai_advantage_pct",
            "better_controller",
        ]
    ].sort_values("scenario_title")


def _to_markdown_table(
    frame: pd.DataFrame,
    columns: list[str] | None = None,
    rename: dict[str, str] | None = None,
) -> str:
    columns = columns or [
        "scenario_title",
        "controller",
        "runs",
        "average_wait_seconds",
        "median_wait_seconds",
        "average_queue_length",
        "max_queue_length",
        "throughput_per_hour",
        "fairness_index",
        "improvement_reference_controller",
        "wait_improvement_vs_fixed_pct",
    ]
    display = frame[columns].copy()
    rename = rename or {
        "scenario_title": "Сценарий",
        "controller": "Стратегия",
        "runs": "Запуски",
        "average_wait_seconds": "Среднее ожидание, с",
        "median_wait_seconds": "Медианное ожидание, с",
        "average_queue_length": "Средняя очередь",
        "max_queue_length": "Максимальная очередь",
        "throughput_per_hour": "Пропускная способность/час",
        "fairness_index": "Справедливость",
        "improvement_reference_controller": "Baseline",
        "wait_improvement_vs_fixed_pct": "Изменение к baseline, %",
    }
    display = display.rename(columns=rename)
    for column in display.select_dtypes(exclude="number").columns:
        display[column] = display[column].fillna("N/A")
    for column in display.select_dtypes(include="number").columns:
        if column in {"Запуски", "Победы", "Ранг"}:
            display[column] = display[column].map(
                lambda value: "N/A" if pd.isna(value) else f"{value:.0f}"
            )
        else:
            display[column] = display[column].map(
                lambda value: "N/A" if pd.isna(value) else f"{value:.2f}"
            )
    headers = list(display.columns)
    rows = [[str(value) for value in row] for row in display.to_numpy().tolist()]
    separator = ["---"] * len(headers)
    table_rows = [headers, separator, *rows]
    return "\n".join("| " + " | ".join(row) + " |" for row in table_rows)
