"""Record reproducibility metadata and hashes for completed total-improvement screens."""
from __future__ import annotations

import gzip
import hashlib
import json
import platform
import shutil
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/total_improvement"
PACKAGES = (
    "gymnasium",
    "matplotlib",
    "numpy",
    "opencv-python-headless",
    "pandas",
    "pydantic",
    "PyYAML",
    "pytest",
    "ruff",
    "scipy",
    "simpy",
    "streamlit",
    "typer",
    "ultralytics",
    "torch",
)
HASH_PATHS = (
    ROOT / "configs/total_improvement_empty_gap_development_1800.yaml",
    OUT / "empty_gap_development_1800.json.gz",
    OUT / "empty_gap_development_1800_replay.json",
    OUT / "empty_gap_development_1800_summary.csv",
    OUT / "empty_gap_development_1800_metrics.csv",
    OUT / "empty_gap_development_1800_paired.csv",
    ROOT / "configs/total_improvement_capacity_boundary_1800.yaml",
    ROOT / "configs/total_improvement_capacity_boundary_3600.yaml",
    OUT / "capacity_boundary_1800.json.gz",
    OUT / "capacity_boundary_1800_replay.json",
    OUT / "capacity_boundary_1800_summary.csv",
    OUT / "capacity_boundary_1800_metrics.csv",
    OUT / "capacity_boundary_1800_paired.csv",
    OUT / "capacity_boundary_3600.json.gz",
    OUT / "capacity_boundary_3600_replay.json",
    OUT / "capacity_boundary_3600_summary.csv",
    OUT / "capacity_boundary_3600_metrics.csv",
    OUT / "capacity_boundary_3600_paired.csv",
    ROOT / "configs/total_improvement_max_red_development_1800.yaml",
    OUT / "max_red_development_1800.json.gz",
    OUT / "max_red_development_1800_replay.json",
    OUT / "max_red_development_1800_summary.csv",
    OUT / "max_red_development_1800_metrics.csv",
    OUT / "max_red_development_1800_paired.csv",
    ROOT / "configs/total_improvement_min_green_dynamics_1800.yaml",
    OUT / "min_green_dynamics_1800.json.gz",
    OUT / "min_green_dynamics_1800_replay.json",
    OUT / "min_green_dynamics_1800_summary.csv",
    OUT / "min_green_dynamics_1800_metrics.csv",
    OUT / "min_green_dynamics_1800_paired.csv",
    OUT / "min_green_dynamics_1800_analysis.md",
    ROOT / "configs/total_improvement_min_green_validation_1800.yaml",
    OUT / "min_green_validation_1800.json.gz",
    OUT / "min_green_validation_1800_replay.json",
    OUT / "min_green_validation_1800_summary.csv",
    OUT / "min_green_validation_1800_paired.csv",
    OUT / "min_green_validation_1800_analysis.md",
    ROOT / "configs/total_improvement_axis_specific_congestion_1800.yaml",
    OUT / "axis_specific_congestion_1800.json.gz",
    OUT / "axis_specific_congestion_1800_replay.json",
    OUT / "axis_specific_congestion_1800_summary.csv",
    OUT / "axis_specific_congestion_1800_metrics.csv",
    OUT / "axis_specific_congestion_1800_paired.csv",
    OUT / "axis_specific_congestion_1800_analysis.md",
    ROOT / "configs/total_improvement_switching_margin_1800.yaml",
    OUT / "switching_margin_1800.json.gz",
    OUT / "switching_margin_1800_replay.json",
    OUT / "switching_margin_1800_summary.csv",
    OUT / "switching_margin_1800_metrics.csv",
    OUT / "switching_margin_1800_paired.csv",
    OUT / "switching_margin_1800_analysis.md",
    ROOT / "configs/total_improvement_switching_margin_validation_1800.yaml",
    OUT / "switching_margin_validation_1800.json.gz",
    OUT / "switching_margin_validation_1800_replay.json",
    OUT / "switching_margin_validation_1800_summary.csv",
    OUT / "switching_margin_validation_1800_paired.csv",
    OUT / "switching_margin_validation_1800_analysis.md",
)


def main() -> None:
    uncompressed_hashes = {}
    for name in (
        "empty_gap_development_1800",
        "capacity_boundary_1800",
        "capacity_boundary_3600",
        "max_red_development_1800",
        "min_green_dynamics_1800",
        "min_green_validation_1800",
        "axis_specific_congestion_1800",
        "switching_margin_1800",
        "switching_margin_validation_1800",
    ):
        raw_json = OUT / f"{name}.json"
        compressed_json = OUT / f"{name}.json.gz"
        if raw_json.exists():
            with (
                raw_json.open("rb") as source,
                compressed_json.open("wb") as target,
                gzip.GzipFile(fileobj=target, mode="wb", mtime=0) as compressed,
            ):
                shutil.copyfileobj(source, compressed)
        if not compressed_json.exists():
            raise FileNotFoundError(f"Run JSON or its gzip archive is required: {name}")
        with gzip.open(compressed_json, "rb") as handle:
            uncompressed_hashes[name] = hashlib.sha256(handle.read()).hexdigest()

    package_versions = {}
    for package in PACKAGES:
        try:
            package_versions[package] = version(package)
        except PackageNotFoundError:
            package_versions[package] = None
    metadata = {
        "python": sys.version,
        "platform": platform.platform(),
        "packages": package_versions,
        "docker_daemon": "unavailable during this stage",
        "cuda_or_torch": "not installed or used; CPU simulation only",
        "random_seeds": list(range(2101, 2131)),
        "run_json_storage": "gzip for publication; local uncompressed copy may remain ignored",
        "uncompressed_run_json_sha256": uncompressed_hashes,
        "empty_gap_development": {
            "duration_seconds": 1800,
            "seeds": list(range(2101, 2131)),
            "scenario_count": 8,
            "controller_rows": 8,
            "run_count": 1920,
            "replay_audit": "0 metric mismatches, 0 unpaired groups, 0 duplicate keys",
            "statistics_audit": "64 groups, 56 paired comparisons, 0 mismatches",
        },
        "capacity_boundary_1800": {
            "duration_seconds": 1800,
            "seeds": list(range(3101, 3116)),
            "demand_levels_per_approach_vehicles_per_minute": list(range(9, 19)),
            "controller_rows": 9,
            "run_count": 1350,
            "replay_audit": "0 metric mismatches, 0 unpaired groups, 0 duplicate keys",
            "statistics_audit": "90 groups, 80 paired comparisons, 0 mismatches",
        },
        "capacity_boundary_3600": {
            "duration_seconds": 3600,
            "seeds": list(range(3101, 3116)),
            "demand_levels_per_approach_vehicles_per_minute": list(range(9, 19)),
            "controller_rows": 9,
            "run_count": 1350,
            "replay_audit": "0 metric mismatches, 0 unpaired groups, 0 duplicate keys",
            "statistics_audit": "90 groups, 80 paired comparisons, 0 mismatches",
            "seed_relation": "same seed IDs and 1800-second arrival prefixes as the shorter screen; not independent replications",
        },
        "max_red_development_1800": {
            "duration_seconds": 1800,
            "seeds": list(range(4101, 4131)),
            "scenario_count": 6,
            "controller_rows": 5,
            "run_count": 900,
            "replay_audit": "0 metric mismatches, 0 unpaired groups, 0 duplicate keys",
            "statistics_audit": "30 groups; paired contrasts independently recomputed from run JSON",
            "paired_family": "10 controller contrasts within each scenario × metric (custom analyzer)",
        },
        "min_green_dynamics_1800": {
            "duration_seconds": 1800,
            "seeds": list(range(5101, 5131)),
            "scenario_count": 7,
            "controller_rows": 7,
            "run_count": 1470,
            "replay_audit": "0 metric mismatches, 0 unpaired groups, 0 duplicate keys",
            "statistics_audit": "49 groups, 42 built-in pairs; 1617 custom paired contrasts across 11 metrics",
        },
        "min_green_validation_1800": {
            "duration_seconds": 1800,
            "seeds": list(range(6101, 6131)),
            "scenario_count": 7,
            "controller_rows": 2,
            "run_count": 420,
            "replay_audit": "0 metric mismatches, 0 unpaired groups, 0 duplicate keys",
            "statistics_audit": "14 groups, custom analyzer computed 7 paired contrasts",
            "paired_family": "one preselected controller contrast within each scenario; Holm over 7 scenarios",
        },
        "axis_specific_congestion_1800": {
            "duration_seconds": 1800,
            "seeds": list(range(7101, 7131)),
            "scenario_count": 7,
            "controller_rows": 4,
            "run_count": 840,
            "replay_audit": "0 metric mismatches, 0 unpaired groups, 0 duplicate keys",
            "statistics_audit": "28 groups, 21 built-in pairs; 378 custom paired contrasts across 9 metrics",
        },
        "switching_margin_1800": {
            "duration_seconds": 1800,
            "seeds": list(range(8101, 8131)),
            "scenario_count": 7,
            "controller_rows": 8,
            "run_count": 1680,
            "replay_audit": "0 metric mismatches, 0 unpaired groups, 0 duplicate keys",
            "statistics_audit": "56 groups, 49 built-in pairs; 1764 custom paired contrasts across 9 metrics",
        },
        "switching_margin_validation_1800": {
            "duration_seconds": 1800,
            "seeds": list(range(9101, 9131)),
            "scenario_count": 7,
            "controller_rows": 3,
            "run_count": 630,
            "replay_audit": "0 metric mismatches, 0 unpaired groups, 0 duplicate keys",
            "statistics_audit": "21 groups; custom analyzer computed 14 paired contrasts",
            "paired_family": "candidate vs Improved and Vehicle-actuated across seven scenarios; Holm over 14 contrasts",
        },
    }
    (OUT / "environment.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT)}"
        for path in HASH_PATHS
    ]
    lines.extend(
        f"# sha256 after decompressing {name}.json.gz: {digest}"
        for name, digest in uncompressed_hashes.items()
    )
    (OUT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(
        """# Total improvement research artifacts

This directory contains the reproducible exploratory stages completed so far in the
next-generation controller audit. It does not replace or overwrite earlier PIERE/Queue-based
outputs.

## Reproduction

From the repository root in Python 3.12 with the project runtime and development packages:

```bash
python scripts/create_total_improvement_configs.py
traffic-sim compare --config configs/total_improvement_empty_gap_development_1800.yaml
python scripts/analyze_total_improvement_empty_gap.py
python scripts/plot_total_improvement_empty_gap.py
python scripts/audit_queue_based_results.py outputs/total_improvement/empty_gap_development_1800.json --replay-output outputs/total_improvement/empty_gap_development_1800_replay.json
python scripts/audit_queue_based_statistics.py outputs/total_improvement/empty_gap_development_1800.json
traffic-sim compare --config configs/total_improvement_capacity_boundary_1800.yaml
traffic-sim compare --config configs/total_improvement_capacity_boundary_3600.yaml
python scripts/analyze_total_improvement_capacity_boundary.py --duration 1800
python scripts/analyze_total_improvement_capacity_boundary.py --duration 3600
python scripts/plot_total_improvement_capacity_boundary.py --duration 1800
python scripts/plot_total_improvement_capacity_boundary.py --duration 3600
traffic-sim compare --config configs/total_improvement_max_red_development_1800.yaml
python scripts/analyze_total_improvement_max_red.py
python scripts/plot_total_improvement_max_red.py
python scripts/audit_queue_based_results.py outputs/total_improvement/max_red_development_1800.json --replay-output outputs/total_improvement/max_red_development_1800_replay.json
python scripts/audit_queue_based_statistics.py outputs/total_improvement/max_red_development_1800.json
traffic-sim compare --config configs/total_improvement_min_green_dynamics_1800.yaml
python scripts/analyze_total_improvement_min_green.py
python scripts/plot_total_improvement_min_green.py
python scripts/audit_queue_based_results.py outputs/total_improvement/min_green_dynamics_1800.json --replay-output outputs/total_improvement/min_green_dynamics_1800_replay.json
traffic-sim compare --config configs/total_improvement_min_green_validation_1800.yaml
python scripts/analyze_total_improvement_min_green_validation.py
python scripts/audit_queue_based_results.py outputs/total_improvement/min_green_validation_1800.json --replay-output outputs/total_improvement/min_green_validation_1800_replay.json
traffic-sim compare --config configs/total_improvement_axis_specific_congestion_1800.yaml
python scripts/analyze_total_improvement_axis_specific.py
python scripts/plot_total_improvement_axis_specific.py
python scripts/audit_queue_based_results.py outputs/total_improvement/axis_specific_congestion_1800.json --replay-output outputs/total_improvement/axis_specific_congestion_1800_replay.json
traffic-sim compare --config configs/total_improvement_switching_margin_1800.yaml
python scripts/analyze_total_improvement_switching_margin.py
python scripts/plot_total_improvement_switching_margin.py
python scripts/audit_queue_based_results.py outputs/total_improvement/switching_margin_1800.json --replay-output outputs/total_improvement/switching_margin_1800_replay.json
traffic-sim compare --config configs/total_improvement_switching_margin_validation_1800.yaml
python scripts/analyze_total_improvement_switching_margin_validation.py
python scripts/audit_queue_based_results.py outputs/total_improvement/switching_margin_validation_1800.json --replay-output outputs/total_improvement/switching_margin_validation_1800_replay.json
python scripts/audit_queue_based_results.py outputs/total_improvement/capacity_boundary_1800.json --replay-output outputs/total_improvement/capacity_boundary_1800_replay.json
python scripts/audit_queue_based_statistics.py outputs/total_improvement/capacity_boundary_1800.json
python scripts/audit_queue_based_results.py outputs/total_improvement/capacity_boundary_3600.json --replay-output outputs/total_improvement/capacity_boundary_3600_replay.json
python scripts/audit_queue_based_statistics.py outputs/total_improvement/capacity_boundary_3600.json
python scripts/finalize_total_improvement_artifacts.py
python scripts/audit_queue_based_results.py outputs/total_improvement/empty_gap_development_1800.json.gz
python scripts/audit_queue_based_statistics.py outputs/total_improvement/empty_gap_development_1800.json.gz
python scripts/audit_queue_based_results.py outputs/total_improvement/capacity_boundary_1800.json.gz
python scripts/audit_queue_based_statistics.py outputs/total_improvement/capacity_boundary_1800.json.gz
python scripts/audit_queue_based_results.py outputs/total_improvement/capacity_boundary_3600.json.gz
python scripts/audit_queue_based_statistics.py outputs/total_improvement/capacity_boundary_3600.json.gz
python scripts/audit_queue_based_results.py outputs/total_improvement/max_red_development_1800.json.gz
python scripts/audit_queue_based_statistics.py outputs/total_improvement/max_red_development_1800.json.gz
python scripts/audit_queue_based_results.py outputs/total_improvement/min_green_dynamics_1800.json.gz
python scripts/audit_queue_based_statistics.py outputs/total_improvement/min_green_dynamics_1800.json.gz
python scripts/audit_queue_based_results.py outputs/total_improvement/min_green_validation_1800.json.gz
python scripts/audit_queue_based_statistics.py outputs/total_improvement/min_green_validation_1800.json.gz
python scripts/audit_queue_based_results.py outputs/total_improvement/axis_specific_congestion_1800.json.gz
python scripts/audit_queue_based_statistics.py outputs/total_improvement/axis_specific_congestion_1800.json.gz
python scripts/audit_queue_based_results.py outputs/total_improvement/switching_margin_1800.json.gz
python scripts/audit_queue_based_statistics.py outputs/total_improvement/switching_margin_1800.json.gz
python scripts/audit_queue_based_results.py outputs/total_improvement/switching_margin_validation_1800.json.gz
python scripts/audit_queue_based_statistics.py outputs/total_improvement/switching_margin_validation_1800.json.gz
```

The simulation used CPU only. Exact package versions and SHA-256 values are recorded in
`environment.json` and `SHA256SUMS.txt`. The published full run log is gzip-compressed; an
uncompressed local copy is ignored by Git. It stores histories without the redundant one-second
queue series; all waits, hashes, phase history, throughput, residual counts and independent replay
metrics are retained.

Seed 2101–2130 are development seeds and are not an independent final-test set after their results
have been examined. See `../../docs/TOTAL_SYSTEM_IMPROVEMENT_AUDIT.md` for interpretation and
limitations. The min-green candidate was preselected on development seeds 5101–5130 and checked
on separate validation seeds 6101–6130; its supported effect is limited to symmetric demand 9 in
this model. Neither new screen changes the main PIERE manuscript.
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
