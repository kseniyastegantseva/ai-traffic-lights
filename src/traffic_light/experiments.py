from __future__ import annotations

import json
from pathlib import Path
from statistics import stdev

import pandas as pd

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
    QLearningPolicyController,
)
from traffic_light.simulation import run_simulation

BASELINE_CONTROLLER = "fixed"


def build_controller(config: ControllerConfig, min_green_seconds: int) -> BaseController:
    if config.type == "fixed":
        return FixedTimeController(phase_duration_seconds=config.phase_duration_seconds)
    if config.type == "actuated":
        return ActuatedController(
            min_green_seconds=min_green_seconds,
            decision_interval_seconds=config.decision_interval_seconds,
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
        for controller_config in config.controllers:
            for seed in config.simulation.seeds:
                simulation = SimulationConfig(
                    duration_seconds=config.simulation.duration_seconds,
                    seed=seed,
                    service_time_seconds=config.simulation.service_time_seconds,
                )
                controller = build_controller(
                    controller_config,
                    min_green_seconds=scenario["intersection"].min_green_seconds,
                )
                result = run_simulation(scenario["intersection"], simulation, controller)
                rows.append(
                    {
                        "scenario": scenario["name"],
                        "scenario_title": scenario["title"],
                        "scenario_description": scenario["description"],
                        **result.to_dict(),
                    }
                )

    frame = pd.DataFrame(rows)
    summary = (
        frame.groupby(["scenario", "scenario_title", "controller"])
        .agg(
            runs=("seed", "count"),
            average_wait_seconds=("average_wait_seconds", "mean"),
            wait_std=("average_wait_seconds", _std_or_zero),
            median_wait_seconds=("median_wait_seconds", "mean"),
            average_queue_length=("average_queue_length", "mean"),
            throughput_per_hour=("throughput_per_hour", "mean"),
            fairness_index=("fairness_index", "mean"),
            stops=("stops", "mean"),
        )
        .reset_index()
    )
    summary["wait_95ci_half_width"] = summary.apply(
        lambda row: 1.96 * row["wait_std"] / (row["runs"] ** 0.5),
        axis=1,
    )
    summary = _add_baseline_improvement(summary)
    return rows, summary


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
        "experiment": {
            "name": config.name if config else "experiment",
            "title": config.title if config else "Эксперимент",
            "description": config.description if config else "",
        },
        "runs": results,
        "summary": summary.to_dict(orient="records"),
        "analytics": {
            "scenario_ranking": analytics["scenario_ranking"].to_dict(orient="records"),
            "strategy_overview": analytics["strategy_overview"].to_dict(orient="records"),
            "ai_vs_actuated": analytics["ai_vs_actuated"].to_dict(orient="records"),
        },
    }
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary.to_csv(csv_path, index=False)
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(
        build_markdown_report(summary, config, analytics),
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
                "Для каждого сценария все стратегии запускаются на одинаковом наборе random seed. "
                "Ключевым baseline считается стратегия `fixed`; улучшение считается как снижение "
                "среднего времени ожидания относительно неё."
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
                    "wait_improvement_vs_fixed_pct": "Улучшение к fixed, %",
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
                    "mean_improvement_vs_fixed_pct": "Среднее улучшение к fixed, %",
                    "mean_queue_length": "Средняя очередь",
                    "mean_fairness_index": "Справедливость",
                },
            ),
            "",
            "## AI против adaptive",
            "",
            _to_markdown_table(
                analytics["ai_vs_actuated"],
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
            "## Основные выводы",
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
    summary["wait_improvement_vs_fixed_pct"] = 0.0
    for scenario in summary["scenario"].unique():
        mask = summary["scenario"] == scenario
        baseline = summary.loc[mask & (summary["controller"] == BASELINE_CONTROLLER)]
        if baseline.empty:
            continue
        baseline_wait = float(baseline.iloc[0]["average_wait_seconds"])
        if baseline_wait <= 0:
            continue
        summary.loc[mask, "wait_improvement_vs_fixed_pct"] = (
            (baseline_wait - summary.loc[mask, "average_wait_seconds"]) / baseline_wait * 100
        )
    return summary


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
        "throughput_per_hour",
        "fairness_index",
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
        "throughput_per_hour": "Пропускная способность/час",
        "fairness_index": "Справедливость",
        "wait_improvement_vs_fixed_pct": "Улучшение к fixed, %",
    }
    display = display.rename(columns=rename)
    for column in display.select_dtypes(include="number").columns:
        if column in {"Запуски", "Победы", "Ранг"}:
            display[column] = display[column].map(lambda value: f"{value:.0f}")
        else:
            display[column] = display[column].map(lambda value: f"{value:.2f}")
    headers = list(display.columns)
    rows = [[str(value) for value in row] for row in display.to_numpy().tolist()]
    separator = ["---"] * len(headers)
    table_rows = [headers, separator, *rows]
    return "\n".join("| " + " | ".join(row) + " |" for row in table_rows)
