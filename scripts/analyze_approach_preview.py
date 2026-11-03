"""Анализ управления с датчиком подъезда: метрики, парные контрасты, выбор baseline.

development: из сетки выбирает настроенный Vehicle-actuated и Improved по заранее
объявленному правилу и считает контрасты кандидатов на development-seed.
validation: использует сохранённый выбор и считает те же контрасты на новых seed.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path

from traffic_light.statistics_audit import holm_adjust, paired_summary

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/approach_preview"
SUBCAPACITY = (
    "symmetric_low", "symmetric", "symmetric_9", "asymmetric_ns", "asymmetric_ew",
    "sudden_dominance_switch",
)
OVERLOAD = ("high_load", "true_oversaturated")
DEFAULT_VA = "va_min8_gap3"
PREVIEW_PREFIX = "preview_"
METRICS = (
    "average_wait_seconds", "average_queue_length", "throughput_per_hour", "waiting_at_end",
)


def load_runs(stems: list[str]) -> dict[tuple[str, str, int], dict]:
    runs: dict[tuple[str, str, int], dict] = {}
    for stem in stems:
        payload = json.loads((OUT / f"{stem}.json").read_text(encoding="utf-8"))
        for run in payload["runs"]:
            key = (run["scenario"], run["controller"], int(run["seed"]))
            if key in runs and runs[key]["average_wait_seconds"] != run["average_wait_seconds"]:
                raise ValueError(f"Anchor run differs between files: {key}")
            runs[key] = run
    return runs


def switches(run: dict) -> int:
    return sum(1 for item in run["phase_history"] if item["color"] == "yellow")


def mean_metric(runs: dict, scenario: str, controller: str, metric: str) -> float:
    return statistics.mean(
        float(r[metric]) for (s, c, _), r in runs.items() if s == scenario and c == controller
    )


def select_baselines(runs: dict) -> dict[str, str]:
    controllers = sorted({c for _, c, _ in runs})

    def score(name: str) -> float:
        return statistics.mean(
            mean_metric(runs, s, name, "average_wait_seconds") for s in SUBCAPACITY
        )

    va = min((c for c in controllers if c.startswith("va_")), key=score)
    imp = min((c for c in controllers if c.startswith("imp20_")), key=score)
    return {"vehicle_actuated": va, "improved": imp}


def contrasts(runs: dict, pairs: list[tuple[str, str]], scenarios: list[str]) -> list[dict]:
    rows = []
    for scenario in scenarios:
        for candidate, comparator in pairs:
            seeds = sorted(
                {sd for (s, c, sd) in runs if s == scenario and c == candidate}
                & {sd for (s, c, sd) in runs if s == scenario and c == comparator}
            )
            if not seeds:
                continue
            diff = [
                float(runs[(scenario, candidate, sd)]["average_wait_seconds"])
                - float(runs[(scenario, comparator, sd)]["average_wait_seconds"])
                for sd in seeds
            ]
            reference = mean_metric(runs, scenario, comparator, "average_wait_seconds")
            stats = paired_summary(diff)
            rows.append({
                "scenario": scenario, "candidate": candidate, "comparator": comparator,
                "pairs": stats["n"], "mean_delta_wait_s": stats["mean"],
                "relative_delta_pct": 100 * stats["mean"] / reference if reference else 0.0,
                "ci95_low": stats["ci_low"], "ci95_high": stats["ci_high"],
                "sign_test_p": stats["sign_p"],
            })
    adjusted = holm_adjust([float(r["sign_test_p"]) for r in rows])
    for row, p_adj in zip(rows, adjusted, strict=True):
        row["holm_p"] = p_adj
    return rows


def fmt_p(value: float) -> str:
    return "<0.0001" if value < 0.0001 else f"{value:.4f}"


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("development", "validation"), required=True)
    parser.add_argument("--stems", nargs="+", required=True)
    args = parser.parse_args()
    runs = load_runs(args.stems)
    scenarios = sorted({s for s, _, _ in runs}, key=lambda s: (s in OVERLOAD, s))
    controllers = sorted({c for _, c, _ in runs})

    selection_path = OUT / "development_selection.json"
    if args.mode == "development":
        selection = select_baselines(runs)
        selection_path.write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    else:
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
    tuned_va, tuned_imp = selection["vehicle_actuated"], selection["improved"]

    metric_rows = []
    for scenario in scenarios:
        for controller in controllers:
            subset = [r for (s, c, _), r in runs.items() if s == scenario and c == controller]
            if not subset:
                continue
            waits = [float(r["average_wait_seconds"]) for r in subset]
            metric_rows.append({
                "scenario": scenario, "controller": controller, "runs": len(subset),
                "average_wait_seconds": statistics.mean(waits),
                "wait_sd": statistics.stdev(waits) if len(waits) > 1 else 0.0,
                **{m: statistics.mean(float(r[m]) for r in subset) for m in METRICS[1:]},
                "phase_switches": statistics.mean(switches(r) for r in subset),
                "max_red_with_queue_seconds": statistics.mean(
                    max(r["max_red_with_queue_seconds_by_phase"].values()) for r in subset
                ),
            })
    previews = [c for c in controllers if c.startswith(PREVIEW_PREFIX)]
    pairs: list[tuple[str, str]] = []
    for candidate in previews:
        pairs += [(candidate, tuned_va), (candidate, DEFAULT_VA), (candidate, tuned_imp)]
    pairs += [(tuned_va, DEFAULT_VA), (tuned_imp, tuned_va)]
    pairs = [p for p in dict.fromkeys(pairs) if p[0] in controllers and p[1] in controllers]
    paired_rows = contrasts(runs, pairs, scenarios)

    tag = args.mode
    write_csv(OUT / f"{tag}_metrics.csv", metric_rows)
    write_csv(OUT / f"{tag}_paired.csv", paired_rows)

    title = "Development" if tag == "development" else "Независимая проверка (validation)"
    lines = [
        f"# Управление с датчиком подъезда: {title}",
        "",
        (
            f"Seed: {len({sd for _, _, sd in runs})}, сценариев: {len(scenarios)}, "
            "горизонт 1800 с. "
            f"Настроенный Vehicle-actuated: `{tuned_va}`; настроенный Improved (margin 0,20): "
            f"`{tuned_imp}`. Выбор — по минимуму среднего ожидания в шести сценариях ниже "
            "пропускной способности, объявлен до анализа."
        ),
        "",
        (
            "Δ — среднее парное различие «кандидат − компаратор» в секундах (отрицательное — "
            "кандидат лучше); Holm применён ко всей таблице контрастов."
        ),
        "",
        "## Среднее ожидание завершивших обслуживание, с",
        "",
        "| Сценарий | " + " | ".join(controllers) + " |",
        "|---|" + "---:|" * len(controllers),
    ]
    for scenario in scenarios:
        cells = [
            f"{mean_metric(runs, scenario, c, 'average_wait_seconds'):.2f}" for c in controllers
        ]
        lines.append(f"| {scenario} | " + " | ".join(cells) + " |")
    lines += ["", "## Парные контрасты по ожиданию", "",
              "| Сценарий | Кандидат | Компаратор | Δ, с | Δ, % | 95% CI | Holm p |",
              "|---|---|---|---:|---:|---:|---:|"]
    for r in paired_rows:
        lines.append(
            f"| {r['scenario']} | {r['candidate']} | {r['comparator']} | "
            f"{r['mean_delta_wait_s']:.3f} | {r['relative_delta_pct']:.1f} | "
            f"[{r['ci95_low']:.3f}; {r['ci95_high']:.3f}] | {fmt_p(r['holm_p'])} |"
        )
    lines += ["", "## Переключения и справедливость (среднее по seed)", "",
              "| Сценарий | Контроллер | Переключений за 1800 с | Макс. красный при очереди, с | Остаток в очереди | Throughput, авто/ч |",
              "|---|---|---:|---:|---:|---:|"]
    for r in metric_rows:
        lines.append(
            f"| {r['scenario']} | {r['controller']} | {r['phase_switches']:.1f} | "
            f"{r['max_red_with_queue_seconds']:.1f} | {r['waiting_at_end']:.1f} | "
            f"{r['throughput_per_hour']:.0f} |"
        )
    (OUT / f"{tag}_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{tag}: {len(metric_rows)} metric rows, {len(paired_rows)} paired contrasts; "
          f"tuned VA={tuned_va}, tuned Improved={tuned_imp}")


if __name__ == "__main__":
    main()
