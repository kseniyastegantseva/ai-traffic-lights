"""Independent checks of saved experiment summaries and paired statistics."""
from __future__ import annotations

import csv
import gzip
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from scipy.stats import t as student_t


def _load_payload(path: Path) -> dict[str, Any]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def exact_sign_p(differences: list[float]) -> float:
    nonzero = [value for value in differences if value != 0]
    if not nonzero:
        return 1.0
    negatives = sum(value < 0 for value in nonzero)
    smaller = min(negatives, len(nonzero) - negatives)
    tail = sum(math.comb(len(nonzero), k) for k in range(smaller + 1))
    return min(1.0, 2.0 * tail / (2 ** len(nonzero)))


def holm_adjust(p_values: list[float]) -> list[float]:
    ordered = sorted(range(len(p_values)), key=p_values.__getitem__)
    adjusted = [0.0] * len(p_values)
    running_max = 0.0
    for rank, index in enumerate(ordered):
        running_max = max(running_max, (len(ordered) - rank) * p_values[index])
        adjusted[index] = min(1.0, running_max)
    return adjusted


def paired_summary(differences: list[float]) -> dict[str, float | int | None]:
    n = len(differences)
    if not n:
        return {"n": 0, "mean": 0.0, "sd": 0.0, "ci_low": None, "ci_high": None, "sign_p": 1.0}
    average = statistics.mean(differences)
    deviation = statistics.stdev(differences) if n > 1 else 0.0
    half = float(student_t.ppf(0.975, n - 1)) * deviation / math.sqrt(n) if n > 1 else None
    return {
        "n": n,
        "mean": average,
        "sd": deviation,
        "ci_low": average - half if half is not None else None,
        "ci_high": average + half if half is not None else None,
        "sign_p": exact_sign_p(differences),
    }


def _summary_from_runs(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, float]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["scenario"], row["controller"])].append(row)
    metrics = (
        "average_wait_seconds",
        "median_wait_seconds",
        "average_queue_length",
        "max_queue_length",
        "throughput_per_hour",
        "fairness_index",
        "stops",
    )
    result = {}
    for key, group in groups.items():
        summary = {metric: statistics.mean(float(row[metric]) for row in group) for metric in metrics}
        waits = [float(row["average_wait_seconds"]) for row in group]
        summary["wait_std"] = statistics.stdev(waits) if len(waits) > 1 else 0.0
        n = len(waits)
        summary["wait_95ci_half_width"] = (
            float(student_t.ppf(0.975, n - 1)) * summary["wait_std"] / math.sqrt(n)
            if n > 1
            else 0.0
        )
        summary["runs"] = float(n)
        result[key] = summary
    return result


def _independent_paired(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, int], dict[str, dict[int, float]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for row in rows:
        groups[(row["scenario"], int(row["duration_seconds"]))][row["controller"]][
            int(row["seed"])
        ] = float(row["average_wait_seconds"])
    output: list[dict[str, Any]] = []
    for (scenario, duration), controllers in sorted(groups.items()):
        base = controllers.get("queue_based", {})
        if not base:
            continue
        family: list[dict[str, Any]] = []
        for comparator, values in sorted(controllers.items()):
            if comparator == "queue_based":
                continue
            seeds = sorted(set(base) & set(values))
            differences = [base[seed] - values[seed] for seed in seeds]
            stats = paired_summary(differences)
            family.append(
                {
                    "scenario": scenario,
                    "duration_seconds": duration,
                    "comparator": comparator,
                    "pairs": stats["n"],
                    "queue_based_minus_comparator_mean_seconds": stats["mean"],
                    "paired_sd_seconds": stats["sd"],
                    "ci95_low_seconds": stats["ci_low"],
                    "ci95_high_seconds": stats["ci_high"],
                    "sign_test_p": stats["sign_p"],
                }
            )
        adjusted = holm_adjust([float(row["sign_test_p"]) for row in family])
        for row, p_adjusted in zip(family, adjusted, strict=True):
            row["holm_p"] = p_adjusted
            output.append(row)
    return output


def audit_saved_statistics(path: Path) -> dict[str, Any]:
    payload = _load_payload(path)
    output = payload["configuration"].get("output", {})
    csv_path = _resolve_configured_path(path, output.get("summary_csv", ""))
    report_path = _resolve_configured_path(path, output.get("report_markdown", ""))
    csv_rows = list(csv.DictReader(csv_path.open(encoding="utf-8", newline="")))
    computed = _summary_from_runs(payload["runs"])
    expected_seeds = set(payload["configuration"]["simulation"]["seeds"])
    expected_scenarios = [scenario["name"] for scenario in payload["configuration"]["scenarios"]]
    expected_controllers = set()
    for controller in payload["configuration"]["controllers"]:
        if controller["type"] == "queue_based" and controller.get("legacy_rule"):
            expected_controllers.add("queue_based_legacy")
        else:
            expected_controllers.add(controller.get("result_name") or controller["type"])
    run_seeds: dict[tuple[str, str], set[int]] = defaultdict(set)
    for row in payload["runs"]:
        run_seeds[(row["scenario"], row["controller"])].add(int(row["seed"]))
    archived_json = {
        (row["scenario"], row["controller"]): row for row in payload["summary"]
    }
    mismatches: list[dict[str, Any]] = []
    for scenario in expected_scenarios:
        for controller in expected_controllers:
            key = (scenario, controller)
            if run_seeds.get(key, set()) != expected_seeds:
                mismatches.append(
                    {
                        "key": key,
                        "metric": "seed_coverage",
                        "expected": len(expected_seeds),
                        "actual": len(run_seeds.get(key, set())),
                    }
                )
    for key, expected in computed.items():
        archived = archived_json.get(key)
        csv_row = next(
            (row for row in csv_rows if (row["scenario"], row["controller"]) == key), None
        )
        if archived is None or csv_row is None:
            mismatches.append({"key": key, "metric": "missing_summary_row"})
            continue
        for metric, value in expected.items():
            if not math.isclose(float(value), float(archived[metric]), rel_tol=1e-10, abs_tol=1e-8):
                mismatches.append({"key": key, "metric": metric, "source": "json"})
            if not math.isclose(float(value), float(csv_row[metric]), rel_tol=1e-10, abs_tol=1e-8):
                mismatches.append({"key": key, "metric": metric, "source": "csv"})

    independent_pairs = _independent_paired(payload["runs"])
    archived_pairs = payload.get("paired_statistics", [])
    if len(independent_pairs) != len(archived_pairs):
        mismatches.append(
            {"metric": "paired_row_count", "independent": len(independent_pairs), "archived": len(archived_pairs)}
        )
    paired_fields = (
        "pairs",
        "queue_based_minus_comparator_mean_seconds",
        "paired_sd_seconds",
        "ci95_low_seconds",
        "ci95_high_seconds",
        "sign_test_p",
        "holm_p",
    )
    archived_pair_map = {
        (row["scenario"], int(row["duration_seconds"]), row["comparator"]): row
        for row in archived_pairs
    }
    for row in independent_pairs:
        key = (row["scenario"], row["duration_seconds"], row["comparator"])
        archived = archived_pair_map.get(key)
        if archived is None:
            mismatches.append({"key": key, "metric": "missing_paired_row"})
            continue
        for metric in paired_fields:
            if row[metric] is None or archived.get(metric) is None:
                if row[metric] != archived.get(metric):
                    mismatches.append({"key": key, "metric": metric})
            elif not math.isclose(
                float(row[metric]), float(archived[metric]), rel_tol=1e-10, abs_tol=1e-8
            ):
                mismatches.append({"key": key, "metric": metric})

    report = report_path.read_text(encoding="utf-8")
    if not report.strip() or any(row["scenario_title"] not in report for row in payload["summary"]):
        mismatches.append({"metric": "markdown_report_content"})
    return {
        "file": str(path),
        "run_rows": len(payload["runs"]),
        "summary_groups": len(computed),
        "paired_comparisons": len(independent_pairs),
        "csv_summary_rows": len(csv_rows),
        "mismatches": mismatches,
    }


def _resolve_configured_path(result_path: Path, configured_path: str) -> Path:
    path = Path(configured_path)
    if path.is_absolute():
        return path
    # Experiment runners write configured paths relative to the working
    # directory. Prefer that exact path; fall back to the repository/output
    # directory for audits launched from another working directory.
    if path.exists():
        return path
    return result_path.parent.parent / path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    failed = False
    for path in args.files:
        report = audit_saved_statistics(path)
        print(
            f"{path}: runs={report['run_rows']}; groups={report['summary_groups']}; "
            f"paired={report['paired_comparisons']}; mismatches={len(report['mismatches'])}"
        )
        if report["mismatches"]:
            print(json.dumps(report["mismatches"][:5], ensure_ascii=False, indent=2))
            failed = True
    if failed:
        raise SystemExit(1)
