"""Analyze the locked independent validation of the smooth min-green candidate."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from traffic_light.statistics_audit import holm_adjust, paired_summary

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/total_improvement"
STEM = "min_green_validation_1800"


def main() -> None:
    payload = json.loads((OUT / f"{STEM}.json").read_text(encoding="utf-8"))
    groups: dict[str, dict[str, dict[int, dict]]] = defaultdict(lambda: defaultdict(dict))
    for row in payload["runs"]:
        groups[row["scenario"]][row["controller"]][int(row["seed"])] = row

    rows = []
    for scenario, by_controller in sorted(groups.items()):
        common = sorted(
            set(by_controller["queue_based_smooth_min_green_10_18"])
            & set(by_controller["queue_based_improved"])
        )
        deltas = [
            float(by_controller["queue_based_smooth_min_green_10_18"][seed]["average_wait_seconds"])
            - float(by_controller["queue_based_improved"][seed]["average_wait_seconds"])
            for seed in common
        ]
        stats = paired_summary(deltas)
        rows.append({
            "scenario": scenario,
            "pairs": stats["n"],
            "mean_wait_delta_smooth_minus_improved": stats["mean"],
            "paired_sd": stats["sd"],
            "ci95_low": stats["ci_low"],
            "ci95_high": stats["ci_high"],
            "sign_test_p": stats["sign_p"],
        })
    adjusted = holm_adjust([float(row["sign_test_p"]) for row in rows])
    for row, p_adj in zip(rows, adjusted, strict=True):
        row["holm_p_across_7_scenarios"] = p_adj

    with (OUT / f"{STEM}_paired.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Независимая проверка плавного minimum green",
        "",
        "30 новых seed (6101–6130), 7 сценариев, 1800 с. Единственное заранее выбранное сравнение: линейный ramp min-green 10–18 против Queue-based Improved. Единица парности — scenario/seed; положительное Δ означает большее ожидание у ramp. Holm-коррекция выполнена по семи сценариям.",
        "",
        "| Сценарий | Пар | Δ ожидания, с | 95% CI | Holm p |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['scenario']} | {row['pairs']} | {row['mean_wait_delta_smooth_minus_improved']:.3f} "
            f"| [{row['ci95_low']:.3f}; {row['ci95_high']:.3f}] "
            f"| {row['holm_p_across_7_scenarios']:.4f} |"
        )
    (OUT / f"{STEM}_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} scenario contrasts")


if __name__ == "__main__":
    main()
