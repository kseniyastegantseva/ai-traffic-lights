"""Record the reproducibility environment and hashes for the empty-gap stage."""
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
)


def main() -> None:
    raw_json = OUT / "empty_gap_development_1800.json"
    compressed_json = OUT / "empty_gap_development_1800.json.gz"
    if raw_json.exists():
        with (
            raw_json.open("rb") as source,
            compressed_json.open("wb") as target,
            gzip.GzipFile(fileobj=target, mode="wb", mtime=0) as compressed,
        ):
            shutil.copyfileobj(source, compressed)
    if not compressed_json.exists():
        raise FileNotFoundError("Run JSON or its gzip archive is required")
    with gzip.open(compressed_json, "rb") as handle:
        run_json_sha256 = hashlib.sha256(handle.read()).hexdigest()

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
        "duration_seconds": 1800,
        "scenario_count": 8,
        "controller_rows": 8,
        "run_count": 1920,
        "run_json_storage": "gzip for publication; local uncompressed copy may remain ignored",
        "uncompressed_run_json_sha256": run_json_sha256,
        "replay_audit": "0 metric mismatches, 0 unpaired groups, 0 duplicate keys",
        "statistics_audit": "64 groups, 56 paired comparisons, 0 mismatches",
    }
    (OUT / "environment.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT)}"
        for path in HASH_PATHS
    ]
    lines.append(f"# sha256 after decompressing run JSON: {run_json_sha256}")
    (OUT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(
        """# Total improvement: empty-green development artifacts

This directory contains the first, exploratory stage of the next-generation controller audit.
It does not replace or overwrite earlier PIERE/Queue-based outputs.

## Reproduction

From the repository root in Python 3.12 with the project runtime and development packages:

```bash
python scripts/create_total_improvement_configs.py
traffic-sim compare --config configs/total_improvement_empty_gap_development_1800.yaml
python scripts/analyze_total_improvement_empty_gap.py
python scripts/plot_total_improvement_empty_gap.py
python scripts/audit_queue_based_results.py outputs/total_improvement/empty_gap_development_1800.json --replay-output outputs/total_improvement/empty_gap_development_1800_replay.json
python scripts/audit_queue_based_statistics.py outputs/total_improvement/empty_gap_development_1800.json
python scripts/finalize_total_improvement_artifacts.py
python scripts/audit_queue_based_results.py outputs/total_improvement/empty_gap_development_1800.json.gz
python scripts/audit_queue_based_statistics.py outputs/total_improvement/empty_gap_development_1800.json.gz
```

The simulation used CPU only. Exact package versions and SHA-256 values are recorded in
`environment.json` and `SHA256SUMS.txt`. The published full run log is gzip-compressed; an
uncompressed local copy is ignored by Git. It stores histories without the redundant one-second
queue series; all waits, hashes, phase history, throughput, residual counts and independent replay
metrics are retained.

Seed 2101–2130 are development seeds and are not an independent final-test set after their results
have been examined. See `../../docs/TOTAL_SYSTEM_IMPROVEMENT_AUDIT.md` for interpretation and
limitations.
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
