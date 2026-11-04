"""Построить краткую таблицу из независимого пересчёта final."""
import csv
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "paper/approach_v2_audit"
with (path / "final_outcomes.csv").open(encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))
index = {(r["scenario"], r["contrast"], r["metric"]): r for r in rows}


def fmt(row):
    return (f"{float(row['relative_pct']):+.1f} "
            f"[{float(row['ci_low_pct']):+.1f}; {float(row['ci_high_pct']):+.1f}]")


lines = [
    "# Подтверждённые расчёты и отрицательные результаты", "",
    ("Final 1800 с, camera_nominal, 30 пар seed. Процент — разность средних, делённая на среднее "
    "правого arm. 95 % t-интервалы не скорректированы на множественность; Holm для дополнительных "
    "исходов считается отдельно по 55 тестам каждой метрики. Исходная семья основной метрики "
    "содержит 66 тестов, включая взаимодействие. Источники: `final_outcomes.csv`, "
    "`scripts/audit_approach_v2_outcomes.py`."), "",
    "| Сценарий | D−A, % [95 % ДИ] | D−B, % [95 % ДИ] | D−A max red, % | D−A max wait, % |",
    "|---|---:|---:|---:|---:|",
]
for scenario in sorted({r["scenario"] for r in rows}):
    a = index[scenario, "D-A", "queue_area_vehicle_seconds"]
    b = index[scenario, "D-B", "queue_area_vehicle_seconds"]
    red = index[scenario, "D-A", "max_red_with_queue"]
    wait = index[scenario, "D-A", "max_wait_seconds"]
    lines.append(f"| {scenario} | {fmt(a)} | {fmt(b)} | {float(red['relative_pct']):+.1f} | "
                 f"{float(wait['relative_pct']):+.1f} |")
lines += [
    "", ("В 10 сценариях весь нескорректированный 95 % интервал D−A ниже −5 %; в oversaturated "
    "эффект мал. По исходной семье 66 sign-test все 11 D−A и D−B имеют Holm p < 0,001. "
    "Интервалы и sign test отвечают на разные вопросы."), "",
    ("Среднее максимума ожидания обслуженных автомобилей при D−A: asymmetric_low_ew +55,8 % "
    "(разность +15,73 с, 95 % ДИ [13,82; 17,63], Holm < 0,001); symmetric_low +39,8 % "
    "(+7,38 с, [5,10; 9,67], Holm < 0,001); sudden_switch +23,9 % (+8,89 с, [6,24; 11,54], "
    "Holm 0,0025). В asymmetric_low_ew среднее ожидание east выросло на 14,3 % (+1,20 с, "
    "[0,77; 1,63], Holm 0,030). Индекс Джейна вычислен по средним ожиданиям четырёх направлений; "
    "равенство плохих ожиданий тоже может давать высокий индекс."), "",
    ("p95 и max относятся только к автомобилям, выехавшим до конца горизонта; наблюдаемое "
    "накопленное ожидание включает оставшихся в очереди и автомобили, начавшие обслуживание. "
    "Метрики имеют разную интерпретацию. Сырые индивидуальные ожидания и распределение длительностей "
    "решений в доступном наборе отсутствуют."), "",
    ("Отрицательный результат исходного final: preview в Vehicle-actuated B−A даёт +8,4 % в "
    "symmetric_9 и +6,2 % в capacity_boundary; объяснение через продление зелёного правдоподобно, "
    "но отдельной причинной абляцией не доказано. Результаты ошибок наблюдения и по направлениям — "
    "в CSV; 3600 с содержит только шесть сценариев."),
]
(path / "CONFIRMED_RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
