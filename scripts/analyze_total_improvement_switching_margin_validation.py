"""Analyze the selected switching-margin candidate on independent seeds."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from traffic_light.statistics_audit import holm_adjust, paired_summary

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/total_improvement"
STEM = "switching_margin_validation_1800"
CANDIDATE = "margin_abs1_rel020"
COMPARATORS = ("improved_abs1_rel010", "vehicle_actuated")


def main() -> None:
    payload = json.loads((OUT / f"{STEM}.json").read_text(encoding="utf-8"))
    groups: dict[str, dict[str, dict[int, dict]]] = defaultdict(lambda: defaultdict(dict))
    for run in payload["runs"]:
        groups[run["scenario"]][run["controller"]][int(run["seed"])] = run

    rows = []
    for scenario, policies in sorted(groups.items()):
        candidate = policies[CANDIDATE]
        for comparator in COMPARATORS:
            common = sorted(set(candidate) & set(policies[comparator]))
            differences = [
                float(candidate[seed]["average_wait_seconds"])
                - float(policies[comparator][seed]["average_wait_seconds"])
                for seed in common
            ]
            stats = paired_summary(differences)
            rows.append({
                "scenario": scenario,
                "comparator": comparator,
                "pairs": stats["n"],
                "mean_wait_delta_candidate_minus_comparator": stats["mean"],
                "paired_sd": stats["sd"],
                "ci95_low": stats["ci_low"],
                "ci95_high": stats["ci_high"],
                "sign_test_p": stats["sign_p"],
            })
    adjusted = holm_adjust([float(row["sign_test_p"]) for row in rows])
    for row, p_adj in zip(rows, adjusted, strict=True):
        row["holm_p_across_14_contrasts"] = p_adj

    with (OUT / f"{STEM}_paired.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Независимая проверка относительного switching margin 0,20",
        "",
        "30 новых парных seed (9101–9130), семь сценариев, горизонт 1800 с. Заранее выбранная политика: абсолютный margin 1 и relative margin 0,20. Контрасты выполнены отдельно против Improved (1/0,10) и Vehicle-actuated; Holm применён сразу по 14 сравнениям. Положительное Δ означает большее ожидание у кандидата.",
        "",
        "| Сценарий | Компаратор | Пар | Δ ожидания, с | 95% CI | Holm p |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        p_value = (
            "<0.0001"
            if row["holm_p_across_14_contrasts"] < 0.0001
            else f"{row['holm_p_across_14_contrasts']:.4f}"
        )
        lines.append(
            f"| {row['scenario']} | {row['comparator']} | {row['pairs']} "
            f"| {row['mean_wait_delta_candidate_minus_comparator']:.3f} "
            f"| [{row['ci95_low']:.3f}; {row['ci95_high']:.3f}] "
            f"| {p_value} |"
        )
    (OUT / f"{STEM}_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} independent paired contrasts")


if __name__ == "__main__":
    main()
