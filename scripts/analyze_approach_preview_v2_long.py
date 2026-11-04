"""Контрасты A/B/C/D для горизонта 3600 с (final): та же статистика, что в основном анализаторе."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import analyze_approach_preview_v2 as base

STAGE = sys.argv[1] if len(sys.argv) > 1 else "final"


def main() -> None:
    prefix = f"approach_preview_v2_{STAGE}_m6_3600"
    blind = base.index(base.load_runs(base.OUT / f"{prefix}_nosensor.json.gz"))
    sensed = base.index(base.load_runs(base.OUT / f"{prefix}_camera_nominal.json.gz"))
    idx = {**blind, **sensed}
    rows = base.contrast_rows(idx, "camera_nominal_3600")
    base.write_csv(base.OUT / f"{STAGE}_m6_3600_contrasts.csv", rows)
    base.write_csv(base.OUT / f"{STAGE}_m6_3600_arm_metrics.csv", base.arm_metric_rows(idx, "camera_nominal_3600"))
    lines = [f"# Approach Preview v2: {STAGE}, горизонт 3600 с", "",
             "| Сценарий | Контраст | Δ, % | 95% CI, % | Holm p | Вывод |", "|---|---|---:|---:|---:|---|"]
    for r in rows:
        if r["metric"] == base.PRIMARY:
            lines.append(
                f"| {r['scenario']} | {r['contrast']} | {base.fmt(r['relative_pct'], 1)} | "
                f"[{base.fmt(r['ci_low_pct'], 1)}; {base.fmt(r['ci_high_pct'], 1)}] | "
                f"{base.fmt_p(r['holm_p'])} | {r['verdict']} |"
            )
    (base.OUT / f"{STAGE}_m6_3600_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{STAGE} 3600: {len(rows)} contrast rows")


if __name__ == "__main__":
    main()
