"""Анализ Approach Preview v2: выбор параметров на development и факторные контрасты A/B/C/D.

``select`` — по заранее объявленному правилу выбирает по одному варианту каждого arm на
development (отдельно для min-green 4/6/8) и сохраняет ``development_selection.json``.

``report`` — для validation/final считает парные контрасты по seed:

* D−A — эффект всего комплекса «прогнозное управление + причинный датчик»;
* D−B — эффект политики при одинаковой информации (оба используют датчик);
* C−A — эффект политики без датчика;
* D−C, B−A — ценность датчика внутри одной политики;
* (D−C)−(B−A) — взаимодействие «датчик × политика».

Основная метрика — площадь очереди ``queue_area_vehicle_seconds`` (без цензурирования);
вторичные — наблюдаемая задержка на машину и completed wait; ограничения (guardrails) —
остаток в очереди, throughput, p95 ожидания, максимальный красный при очереди, переключения.
Доверительные интервалы — точный t по парам seed; p — точный sign test; поправка Holm
применяется по всей семье «контраст × сценарий» основной метрики внутри варианта датчика.
Практически значимым считается относительный эффект не менее 5 % с доверительным
интервалом, не пересекающим ноль.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/approach_preview_v2"
import sys

sys.path.insert(0, str(ROOT / "src"))
from traffic_light.statistics_audit import holm_adjust, paired_summary

PRIMARY = "queue_area_vehicle_seconds"
SECONDARY = ("observed_delay_per_vehicle_seconds", "average_wait_seconds")
GUARDRAILS = ("waiting_at_end", "throughput_per_hour", "p95_wait_seconds", "max_red_with_queue",
              "phase_switches", "lost_time_share", "green_idle_seconds")
ALL_METRICS = (PRIMARY, *SECONDARY, *GUARDRAILS)
CONTRASTS = (
    ("D", "A", "system"),
    ("D", "B", "policy_equal_information"),
    ("C", "A", "policy_without_sensor"),
    ("D", "C", "sensor_in_rollout"),
    ("B", "A", "sensor_in_actuated"),
)
OVERLOAD = ("capacity_boundary", "oversaturated")
PRACTICAL = 0.05
REFERENCE_ARM_NAME = "A_dva_g2"


def load_runs(path: Path) -> list[dict]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        runs = json.load(handle)["runs"]
    for run in runs:
        run["max_red_with_queue"] = max((run.get("max_red_with_queue_seconds_by_phase") or {"x": 0}).values())
        duration = run["duration_seconds"]
        run["lost_time_share"] = (run["yellow_seconds_total"] + run["all_red_seconds_total"]) / duration
    return runs


def arm_of(controller: str) -> str | None:
    return controller[0] if controller[:2] in {"A_", "B_", "C_", "D_"} else None


def index(runs: list[dict]) -> dict[tuple[str, str, int], dict]:
    return {(r["scenario"], r["controller"], int(r["seed"])): r for r in runs}


def mean_over_seeds(idx: dict, scenario: str, controller: str, metric: str) -> float:
    values = [float(r[metric]) for (s, c, _), r in idx.items() if s == scenario and c == controller]
    return statistics.mean(values) if values else float("nan")


def scenarios_of(idx: dict) -> list[str]:
    return sorted({s for s, _, _ in idx}, key=lambda s: (s in OVERLOAD, s))


# ---------------------------------------------------------------- выбор на development


def select(args) -> None:
    selection: dict[str, dict] = {}
    for m in args.min_greens:
        blind = index(load_runs(OUT / f"approach_preview_v2_development_m{m}_nosensor.json.gz"))
        sensed = index(load_runs(OUT / f"approach_preview_v2_development_m{m}_camera_nominal.json.gz"))
        merged = {**blind, **sensed}
        scenarios = scenarios_of(merged)
        controllers = sorted({c for _, c, _ in merged})
        table: dict[str, dict] = {}
        for controller in controllers:
            ratios, guard = [], True
            for scenario in scenarios:
                reference = mean_over_seeds(merged, scenario, REFERENCE_ARM_NAME, PRIMARY)
                ratios.append(mean_over_seeds(merged, scenario, controller, PRIMARY) / reference)
                if scenario in OVERLOAD:
                    ref_end = mean_over_seeds(merged, scenario, REFERENCE_ARM_NAME, "waiting_at_end")
                    own_end = mean_over_seeds(merged, scenario, controller, "waiting_at_end")
                    guard = guard and own_end <= 1.10 * ref_end + 1.0
            table[controller] = {"score": statistics.mean(ratios), "eligible": guard}
        chosen = {}
        for arm in "ABCD":
            candidates = [c for c in controllers if arm_of(c) == arm and table[c]["eligible"]]
            if not candidates:
                raise SystemExit(f"Нет допустимого кандидата arm {arm} при m={m}")
            chosen[arm] = min(candidates, key=lambda c: (table[c]["score"], c))
        selection[f"min_green_{m}"] = {**chosen, "scores": {k: round(v["score"], 5) for k, v in table.items()}}
        print(f"m={m}: " + ", ".join(f"{a}={chosen[a]}" for a in "ABCD"))
    (OUT / "development_selection.json").write_text(
        json.dumps(selection, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


# ---------------------------------------------------------------- контрасты


def arm_name(idx: dict, arm: str) -> str:
    names = {c for _, c, _ in idx if arm_of(c) == arm}
    if len(names) != 1:
        raise ValueError(f"Ожидался один контроллер arm {arm}, найдено {sorted(names)}")
    return names.pop()


def seeds_for(idx: dict, scenario: str, controllers: list[str]) -> list[int]:
    sets = [{sd for (s, c, sd) in idx if s == scenario and c == name} for name in controllers]
    return sorted(set.intersection(*sets)) if sets else []


def contrast_rows(idx: dict, variant: str, metrics=ALL_METRICS) -> list[dict]:
    names = {arm: arm_name(idx, arm) for arm in "ABCD" if any(arm_of(c) == arm for _, c, _ in idx)}
    rows: list[dict] = []
    for scenario in scenarios_of(idx):
        for left, right, label in CONTRASTS:
            if left not in names or right not in names:
                continue
            seeds = seeds_for(idx, scenario, [names[left], names[right]])
            for metric in metrics:
                diffs = [
                    float(idx[(scenario, names[left], sd)][metric])
                    - float(idx[(scenario, names[right], sd)][metric])
                    for sd in seeds
                ]
                reference = statistics.mean(float(idx[(scenario, names[right], sd)][metric]) for sd in seeds)
                rows.append(_row(variant, scenario, f"{left}-{right}", label, metric, diffs, reference))
        if all(arm in names for arm in "ABCD"):
            seeds = seeds_for(idx, scenario, [names[a] for a in "ABCD"])
            for metric in metrics:
                def value(arm: str, sd: int, metric=metric, scenario=scenario) -> float:
                    return float(idx[(scenario, names[arm], sd)][metric])

                diffs = [(value("D", sd) - value("C", sd)) - (value("B", sd) - value("A", sd)) for sd in seeds]
                reference = statistics.mean(value("A", sd) for sd in seeds)
                rows.append(_row(variant, scenario, "(D-C)-(B-A)", "interaction", metric, diffs, reference))
    primary_idx = [i for i, row in enumerate(rows) if row["metric"] == PRIMARY]
    adjusted = holm_adjust([rows[i]["sign_p"] for i in primary_idx])
    for i, p in zip(primary_idx, adjusted, strict=True):
        rows[i]["holm_p"] = p
        rows[i]["verdict"] = _verdict(rows[i])
    return rows


def _row(variant, scenario, contrast, label, metric, diffs, reference) -> dict:
    stats = paired_summary(diffs)
    scale = 100.0 / reference if reference else 0.0
    low, high = stats["ci_low"], stats["ci_high"]
    return {
        "variant": variant, "scenario": scenario, "contrast": contrast, "meaning": label,
        "metric": metric, "pairs": stats["n"], "mean_diff": stats["mean"],
        "relative_pct": stats["mean"] * scale,
        "ci_low": low, "ci_high": high,
        "ci_low_pct": None if low is None else low * scale, "ci_high_pct": None if high is None else high * scale,
        "sign_p": stats["sign_p"], "holm_p": float("nan"), "verdict": "",
    }


def _verdict(row: dict) -> str:
    low, high, rel = row["ci_low_pct"], row["ci_high_pct"], row["relative_pct"]
    if low is None:
        return "n/a"
    if row["contrast"].startswith("("):
        return "interaction_negative" if high < 0 else "interaction_positive" if low > 0 else "interaction_unclear"
    if high < 0 and rel <= -100 * PRACTICAL:
        return "better_practical"
    if low > 0 and rel >= 100 * PRACTICAL:
        return "worse_practical"
    if high < 0:
        return "better_small"
    if low > 0:
        return "worse_small"
    return "no_difference_detected"


def arm_metric_rows(idx: dict, variant: str) -> list[dict]:
    rows = []
    for scenario in scenarios_of(idx):
        for controller in sorted({c for s, c, _ in idx if s == scenario}):
            rows.append({
                "variant": variant, "scenario": scenario, "controller": controller,
                "runs": sum(1 for (s, c, _) in idx if s == scenario and c == controller),
                **{m: mean_over_seeds(idx, scenario, controller, m) for m in ALL_METRICS},
            })
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    import csv

    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def fmt(value, digits=2) -> str:
    return "—" if value is None or math.isnan(value) else f"{value:.{digits}f}"


def fmt_p(value: float) -> str:
    return "—" if math.isnan(value) else ("<0.0001" if value < 1e-4 else f"{value:.4f}")


def report(args) -> None:
    stage, m = args.stage, args.min_green
    prefix = f"approach_preview_v2_{stage}_m{m}"
    blind = index(load_runs(OUT / f"{prefix}_nosensor.json.gz"))
    nominal = index(load_runs(OUT / f"{prefix}_camera_nominal.json.gz"))
    variants: dict[str, dict] = {"camera_nominal": {**blind, **nominal}}
    for extra in sorted(OUT.glob(f"{prefix}_*.json.gz")):
        key = extra.name.removeprefix(f"{prefix}_").removesuffix(".json.gz")
        if key in {"nosensor", "camera_nominal"} or key.startswith("3600"):
            continue
        sensed = index(load_runs(extra))
        scenarios = {s for s, _, _ in sensed}
        restricted = {k: v for k, v in blind.items() if k[0] in scenarios}
        variants[key] = {**restricted, **sensed}
    all_arm, all_contrast = [], []
    for variant, idx in variants.items():
        all_arm += arm_metric_rows(idx, variant)
        all_contrast += contrast_rows(idx, variant)
    write_csv(OUT / f"{stage}_m{m}_arm_metrics.csv", all_arm)
    write_csv(OUT / f"{stage}_m{m}_contrasts.csv", all_contrast)

    lines = [f"# Approach Preview v2: {stage}, min-green {m} с", ""]
    lines += [
        (
            "Δ — среднее парное различие «левый arm − правый arm» по seed; отрицательное значение "
            "означает меньшую очередь у левого. Основная метрика — площадь очереди "
            "(автомобиле-секунды за горизонт). Holm — по контрастам и сценариям варианта датчика."
        ),
        "",
    ]
    for variant in variants:
        subset = [r for r in all_contrast if r["variant"] == variant and r["metric"] == PRIMARY]
        lines += [f"## Вариант датчика: {variant}", "", "### Основная метрика: площадь очереди", "",
                  "| Сценарий | Контраст | Смысл | Δ, авто·с | Δ, % | 95% CI, % | Holm p | Вывод |",
                  "|---|---|---|---:|---:|---:|---:|---|"]
        for r in subset:
            lines.append(
                f"| {r['scenario']} | {r['contrast']} | {r['meaning']} | {fmt(r['mean_diff'], 1)} | "
                f"{fmt(r['relative_pct'], 1)} | [{fmt(r['ci_low_pct'], 1)}; {fmt(r['ci_high_pct'], 1)}] | "
                f"{fmt_p(r['holm_p'])} | {r['verdict']} |"
            )
        lines += ["", "### Сводка вердиктов", "", "| Контраст | практически лучше | меньше, но не практично | не обнаружено | хуже (любое) |",
                  "|---|---:|---:|---:|---:|"]
        for _left, _right, label in CONTRASTS:
            rows = [r for r in subset if r["meaning"] == label]
            if not rows:
                continue
            better = sum(r["verdict"] == "better_practical" for r in rows)
            small = sum(r["verdict"] == "better_small" for r in rows)
            none = sum(r["verdict"] == "no_difference_detected" for r in rows)
            worse = [r["scenario"] for r in rows if r["verdict"].startswith("worse")]
            lines.append(f"| {label} | {better} | {small} | {none} | {', '.join(worse) or '—'} |")
        lines.append("")
    nominal_arm = [r for r in all_arm if r["variant"] == "camera_nominal"]
    lines += ["## Средние метрики (camera_nominal)", ""]
    for metric in (PRIMARY, "observed_delay_per_vehicle_seconds", "average_wait_seconds", "waiting_at_end",
                   "throughput_per_hour", "max_red_with_queue", "phase_switches"):
        controllers = sorted({r["controller"] for r in nominal_arm})
        lines += [f"### {metric}", "", "| Сценарий | " + " | ".join(controllers) + " |",
                  "|---|" + "---:|" * len(controllers)]
        for scenario in scenarios_of(variants["camera_nominal"]):
            cells = []
            for controller in controllers:
                row = next((r for r in nominal_arm if r["scenario"] == scenario and r["controller"] == controller), None)
                cells.append(fmt(row[metric], 2) if row else "—")
            lines.append(f"| {scenario} | " + " | ".join(cells) + " |")
        lines.append("")
    (OUT / f"{stage}_m{m}_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{stage}: {len(all_arm)} arm rows, {len(all_contrast)} contrast rows -> {OUT.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    select_parser = sub.add_parser("select")
    select_parser.add_argument("--min-greens", type=int, nargs="+", default=[4, 6, 8])
    select_parser.set_defaults(func=select)
    report_parser = sub.add_parser("report")
    report_parser.add_argument("--stage", choices=("validation", "final"), required=True)
    report_parser.add_argument("--min-green", type=int, default=6)
    report_parser.set_defaults(func=report)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
