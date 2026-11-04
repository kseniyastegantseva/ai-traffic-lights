"""Параллельный запуск конфигурации Approach Preview v2 с манифестом воспроизводимости.

Сценарии распределяются по процессам; результат совпадает с последовательным
``run_experiment`` (потоки прибытий и случайность детерминированы seed). Рядом с результатом
сохраняется манифест: SHA-256 конфигурации и результата, commit и признак изменённого дерева,
версия Python, список seed и хеши потоков прибытий.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import platform
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from traffic_light.config import ExperimentConfig, load_experiment_config
from traffic_light.experiments import run_experiment, summarize_results


def _run_chunk(config: ExperimentConfig) -> list[dict]:
    rows, _ = run_experiment(config)
    return rows


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def run_config(config_path: Path, workers: int) -> Path:
    config = load_experiment_config(config_path)
    chunks = [config.model_copy(update={"scenarios": [scenario]}) for scenario in config.scenarios or []]
    with ProcessPoolExecutor(max_workers=max(1, workers)) as pool:
        rows = [row for chunk in pool.map(_run_chunk, chunks) for row in chunk]
    summary = summarize_results(rows)
    out_json = ROOT / config.output["path"]
    out_json = out_json.with_suffix(".json.gz")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "result_schema_version": 3,
        "experiment": {"name": config.name, "title": config.title, "description": config.description},
        "configuration": config.model_dump(mode="json"),
        "runs": rows,
    }
    with gzip.open(out_json, "wt", encoding="utf-8", compresslevel=6) as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
    summary_path = ROOT / config.output["summary_csv"]
    summary.to_csv(summary_path, index=False)

    hashes: dict[str, set[str]] = {}
    for row in rows:
        hashes.setdefault(f"{row['scenario']}:{row['seed']}", set()).add(row["arrival_stream_sha256"])
    status = _git("status", "--porcelain", "--", "src", "scripts", "configs")
    manifest = {
        "experiment": config.name,
        "config_path": str(config_path.relative_to(ROOT)),
        "config_sha256": _sha256(config_path),
        "result_path": str(out_json.relative_to(ROOT)),
        "result_sha256": _sha256(out_json),
        "git_commit": _git("rev-parse", "HEAD"),
        "working_tree_dirty": bool(status),
        "working_tree_status_sha256": hashlib.sha256(status.encode()).hexdigest(),
        "python": platform.python_version(),
        "runs": len(rows),
        "seeds": config.simulation.seeds,
        "arrival_hash_consistent": all(len(value) == 1 for value in hashes.values()),
        "vehicle_balance_errors": sum(int(row["vehicle_balance_error"] != 0) for row in rows),
    }
    manifest_path = out_json.with_name(f"{config.name}_manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("configs", nargs="+", type=Path)
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()
    for path in args.configs:
        resolved = path if path.is_absolute() else ROOT / path
        if "_final_" in resolved.name:
            sys.path.insert(0, str(ROOT / "scripts"))
            from freeze_approach_preview_v2 import verify_freeze

            verify_freeze()
        manifest = run_config(resolved, args.workers)
        print(f"{resolved.name}: {manifest.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
