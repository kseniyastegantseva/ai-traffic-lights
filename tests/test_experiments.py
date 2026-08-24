import json
from pathlib import Path

from traffic_light.config import load_experiment_config
from traffic_light.experiments import (
    build_experiment_analytics,
    build_markdown_report,
    run_experiment,
    save_results,
)


def test_experiment_compares_configured_controllers():
    config = load_experiment_config("configs/experiment.yaml")
    results, summary = run_experiment(config)
    assert len(results) == len(config.controllers) * len(config.simulation.seeds)
    assert set(summary["controller"]) == {"fixed", "actuated", "ai"}


def test_demo_uniform_experiment_builds_unified_report(tmp_path: Path):
    config = load_experiment_config("configs/demo_uniform.yaml")
    results, summary = run_experiment(config)
    assert set(summary["scenario"]) == {"uniform_demo"}
    assert "wait_improvement_vs_fixed_pct" in summary.columns

    report = build_markdown_report(summary, config)
    assert "Демонстрационный эксперимент" in report
    assert "Равномерная нагрузка" in report

    json_path = tmp_path / "result.json"
    csv_path = tmp_path / "summary.csv"
    report_path = tmp_path / "report.md"
    save_results(results, summary, str(json_path), str(csv_path), str(report_path), config)
    assert json_path.exists()
    assert csv_path.exists()
    assert report_path.exists()


def test_experiment_suite_contains_multiple_research_scenarios():
    config = load_experiment_config("configs/experiment_suite.yaml")
    results, summary = run_experiment(config)
    assert len(config.scenarios or []) == 5
    assert len(results) == len(config.controllers) * len(config.simulation.seeds) * 5
    assert set(summary["scenario"]) == {
        "uniform_demo",
        "low_load",
        "morning_peak_ns",
        "evening_peak_ew",
        "oversaturated",
    }
    assert set(summary["controller"]) == {"fixed", "actuated", "ai"}


def test_experiment_suite_report_contains_strategy_analytics(tmp_path: Path):
    config = load_experiment_config("configs/experiment_suite.yaml")
    results, summary = run_experiment(config)
    analytics = build_experiment_analytics(summary)

    assert set(analytics) == {"scenario_ranking", "strategy_overview", "ai_vs_actuated"}
    assert not analytics["strategy_overview"].empty
    assert not analytics["scenario_ranking"].empty
    assert not analytics["ai_vs_actuated"].empty

    report = build_markdown_report(summary, config, analytics)
    assert "Рейтинг стратегий по сценариям" in report
    assert "AI против adaptive" in report

    json_path = tmp_path / "suite.json"
    csv_path = tmp_path / "suite.csv"
    report_path = tmp_path / "suite.md"
    save_results(results, summary, str(json_path), str(csv_path), str(report_path), config)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert "analytics" in payload
    assert "strategy_overview" in payload["analytics"]
