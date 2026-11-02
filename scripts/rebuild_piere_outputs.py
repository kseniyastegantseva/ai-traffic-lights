"""Recalculate PIERE summaries and reports from saved run-level JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from traffic_light.config import ExperimentConfig
from traffic_light.experiments import save_results, summarize_results

ROOT = Path(__file__).resolve().parents[1]
RESULT_FILES = (
    "piere_revision_quick.json",
    "piere_revision_1800.json",
    "piere_revision_3600.json",
    "piere_revision_addendum_1800.json",
    "piere_revision_addendum_3600.json",
    "piere_perception_sensitivity.json",
    "piere_perception_sensitivity_expanded.json",
    "piere_perception_empirical_errors.json",
)


def main() -> None:
    output_dir = ROOT / "outputs"
    for filename in RESULT_FILES:
        result_path = output_dir / filename
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        rows = payload["runs"]
        config = ExperimentConfig.model_validate(payload["configuration"])
        summary = summarize_results(rows)
        stem = result_path.stem
        save_results(
            rows,
            summary,
            str(result_path),
            str(output_dir / f"{stem}_summary.csv"),
            str(output_dir / f"{stem}_report.md"),
            config,
        )
        print(f"Rebuilt {filename}: {len(rows)} saved runs")


if __name__ == "__main__":
    main()
