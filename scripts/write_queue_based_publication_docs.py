"""Write the three requested research notes from audited final CSV tables."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "outputs/queue_based_final_summary.csv"
CONTRASTS = ROOT / "outputs/queue_based_final_paired_contrasts.csv"
AUDIT = ROOT / "outputs/queue_based_final_audit_status.json"
CONTROLLERS = (
    "fixed_8",
    "fixed_15",
    "fixed_35",
    "fixed_webster",
    "vehicle_actuated",
    "queue_based",
    "queue_based_improved",
    "queue_based_legacy",
)
LABEL = {
    "fixed_8": "Fixed 8 s",
    "fixed_15": "Fixed 15 s",
    "fixed_35": "Fixed 35 s",
    "fixed_webster": "Webster",
    "vehicle_actuated": "Vehicle-actuated",
    "queue_based": "Queue-based original",
    "queue_based_improved": "Queue-based improved",
    "queue_based_legacy": "Queue-based legacy",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def f(value: str | float, digits: int = 2) -> str:
    return f"{float(value):,.{digits}f}"


def ci(row: dict[str, str], metric: str) -> str:
    return (
        f"{f(row[f'{metric}_mean'])} "
        f"[{f(row[f'{metric}_ci95_low'])}; {f(row[f'{metric}_ci95_high'])}]"
    )


def result_tables(summary: list[dict[str, str]]) -> str:
    out = []
    by_key = {(row["scenario"], row["duration_seconds"], row["controller"]): row for row in summary}
    for duration in (1800, 3600):
        out += [f"### Горизонт {duration} с", "", "| Сценарий | Контроллер | Ожидание, с: среднее [95% ДИ] | Средняя очередь | Макс. очередь | Макс. ожидание, с | Throughput, авто/ч | Остаток, авто | Переключения | Достигнуто max-green | Среднее зелёное, с | Зелёное время, % | Жёлтый, с | Утилизация зелёного | Простой зелёного | v/c макс. полоса |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        scenarios = sorted({row["scenario"] for row in summary if int(row["duration_seconds"]) == duration})
        for scenario in scenarios:
            title = next(row["scenario_title"] for row in summary if row["scenario"] == scenario)
            for controller in CONTROLLERS:
                row = by_key.get((scenario, str(duration), controller))
                if row is None:
                    continue
                out.append(
                    f"| {title} | {LABEL[controller]} | {ci(row, 'average_wait_seconds')} | "
                    f"{f(row['average_queue_length_mean'])} | {f(row['max_queue_length_mean'])} | "
                    f"{f(row['max_wait_seconds_mean'])} | {f(row['throughput_per_hour_mean'])} | "
                    f"{f(row['waiting_at_end_mean'])} | {f(row['switches_mean'], 1)} | "
                    f"{f(row['green_max_reached_count_mean'], 1)} | "
                    f"{f(row['green_mean_seconds_mean'])} | "
                    f"{f(float(row['green_fraction_mean']) * 100, 1)}% | "
                    f"{f(row['yellow_seconds_mean'])} | "
                    f"{f(float(row['green_utilization_mean']) * 100, 1)}% | "
                    f"{f(float(row['green_idle_fraction_mean']) * 100, 1)}% | "
                    f"{f(row['max_lane_v_c_mean'], 3)} |"
                )
        out.append("")
    return "\n".join(out)


def initial_state_table() -> str:
    rows = read_rows(ROOT / "outputs/queue_based_initial_state_summary.csv")
    out = [
        "| Стартовое состояние | Контроллер | Ожидание завершивших, с | Средняя очередь за горизонт | Остаток очереди | Средняя наблюдаемая очередь после 300 с |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        state = "Пустое" if row["scenario"] == "initial_empty" else "По 5 на подходе"
        out.append(
            f"| {state} | {LABEL[row['controller']]} | "
            f"{f(row['full_horizon_wait_mean_seconds'])} | "
            f"{f(row['full_horizon_queue_area_mean'])} | "
            f"{f(row['full_horizon_residual_waiting_mean'])} | "
            f"{f(row['post_300s_mean_sampled_queue'])} |"
        )
    return "\n".join(out)


def improvement_table(summary: list[dict[str, str]], contrasts: list[dict[str, str]]) -> str:
    by = {(row["scenario"], row["duration_seconds"], row["controller"]): row for row in summary}
    paired = {
        (row["scenario"], row["duration_seconds"], row["metric"], row["left_minus_right"]): row
        for row in contrasts
    }
    lines = ["| Горизонт | Сценарий | Снижение ожидания, с | Снижение ожидания, % | Δ средней очереди, авто | Δ throughput, авто/ч | Δ остатка, авто | sign p (Holm) |", "|---:|---|---:|---:|---:|---:|---:|---:|"]
    for duration in (1800, 3600):
        scenarios = sorted({row["scenario"] for row in summary if int(row["duration_seconds"]) == duration})
        for scenario in scenarios:
            original = by[(scenario, str(duration), "queue_based")]
            wait = paired[(scenario, str(duration), "average_wait_seconds", "queue_based - queue_based_improved")]
            queue = paired[(scenario, str(duration), "average_queue_length", "queue_based - queue_based_improved")]
            throughput = paired[(scenario, str(duration), "throughput_per_hour", "queue_based - queue_based_improved")]
            residual = paired[(scenario, str(duration), "waiting_at_end", "queue_based - queue_based_improved")]
            benefit = float(wait["mean_difference"])
            pct = benefit / float(original["average_wait_seconds_mean"]) * 100 if float(original["average_wait_seconds_mean"]) else 0
            lines.append(
                f"| {duration} | {original['scenario_title']} | {f(benefit)} | {f(pct)} | "
                f"{f(-float(queue['mean_difference']))} | {f(-float(throughput['mean_difference']))} | "
                f"{f(-float(residual['mean_difference']))} | {f(wait['exact_sign_p'], 4)} "
                f"({f(wait['holm_p_within_scenario_horizon_metric'], 4)}) |"
            )
    return "\n".join(lines)


def main() -> None:
    summary = read_rows(SUMMARY)
    contrasts = read_rows(CONTRASTS)
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    common = (
        "Новые независимые seed: 1001–1030 (30 на сценарий), парный генератор Poisson-поступлений; "
        "1800 и 3600 с анализируются отдельно. Зафиксированный вариант improved: base min-green 8 с, "
        "при сумме наблюдаемых очередей ≥14 — congested min-green 25 с, max-green 45 с, "
        "абсолютный margin 1 и относительный hysteresis 0,10. Он выбран по development seed "
        "801–815 до раскрытия final seed."
    )
    experiments = f"""# Итоговые эксперименты Queue-based

## Дизайн

{common}

Сравниваются Fixed 8/15/35 с, Webster, Vehicle-actuated, Queue-based original, отдельный Queue-based improved и legacy. По каждой паре seed arrival-stream hash совпадает. Docker daemon в проверочной WSL-среде недоступен; прогоны выполнены установленным Python 3.12 окружением. Начальное состояние основного дизайна пустое, warm-up не исключался. JSON 3600 с опубликован с gzip-сжатием (102 898 322 байта исходника; 4,6 МБ архив); SHA-256 разжатой копии совпадает с исходным JSON. Replay/statistics и графический генератор читают `.json.gz` напрямую.

Восемь контроллеров, девять сценариев, два горизонта дают 2 160 запусков на горизонт. Независимый replay каждого прогона пересоздал arrivals и обслуживание из FIFO очередей по фазовым интервалам. Баланс машин, arrival hash и сохранённые метрики совпали: {audit['runs_1800']} прогонов при 1800 с и {audit['runs_3600']} при 3600 с; несовпадений {audit['metric_mismatch_runs']}.

Среднее ожидание относится только к полностью завершившим обслуживание автомобилям до конца горизонта. Поэтому оно дополняется средней длиной очереди (queue-area / time), накопленной очередной задержкой, остаточной очередью, машинами в обслуживании на конце и throughput. Необслуженным автомобилям не приписывается гипотетическое полное время ожидания. Полные средние, 95% t-интервалы и paired-контрасты доступны в `outputs/queue_based_final_summary.csv` и `outputs/queue_based_final_paired_contrasts.csv`.

## Стартовое состояние и переходный период

На отдельных seed 1101–1130 сравнивались пустое состояние и пять начальных автомобилей на каждом подходе. Полный горизонт 1800 с сохранён; никакой warm-up не исключался. Средняя очередь после 300 с рассчитана отдельно по секундным samples и является только sensitivity-анализом, не оценкой стационарного режима.

{initial_state_table()}

## Результаты по сценарию и контроллеру

Ожидание дано как среднее и 95% CI среднего по 30 прогонам; остальные столбцы — средние по seed.

{result_tables(summary)}

## Статистика и интерпретация

Разности рассчитывались внутри одинаковых seed. Для парных разностей приводятся 95% t-интервалы, точный двусторонний sign test (нули исключены) и поправка Holm по 13 заранее перечисленным контроллерным контрастам в каждой семье scenario × horizon × metric. Статистическую значимость не следует трактовать как практическую значимость. Поскольку очереди могут не опустеть за горизонт, особенно в сценарии 24 авто/мин, среднее завершивших автомобили не является исчерпывающей оценкой задержек.

При 3600 с исходный Queue-based существенно уступил Vehicle-actuated при 18 авто/мин (среднее ожидание 637,93 против 378,49 с; парная разность +259,44 с, Holm p<0,0001) и при 24 авто/мин (918,03 против 728,07 с; +189,96 с, Holm p<0,0001). В этих двух режимах он также имел большую среднюю очередь и меньший throughput. Improved уменьшил ожидание исходного варианта соответственно на 249,08 и 185,62 с, но всё ещё был немного хуже Vehicle-actuated: +10,36 с и +4,34 с; обе парные разности значимы после Holm, хотя разница в перегрузке 24 авто/мин мала по абсолютной величине. Относительно Webster improved практически не отличался при 24 авто/мин (+0,69 с; Holm p=1,0), но при 18 авто/мин был медленнее на 5,53 с (Holm p<0,001).

Сопоставление с Fixed 8 показывает, что один только короткий минимум не объясняет поведение оригинала: при 18 авто/мин Queue-based был быстрее Fixed 8 на 73,47 с при 3600 с (Holm p<0,0001), но имеет иные распределение фаз, число переключений и жёлтые потери. Поэтому это сравнение — baseline-контроль, а не изолированное причинное доказательство эффекта информации об очереди.

{improvement_table(summary, contrasts)}

Параметры не подбирались на seed 1001–1030. Трассы направленных очередей seed 1001–1003 служат диагностикой и не заменяют полную 30-seed оценку.
"""
    assessment = f"""# Оценка Queue-based improved

## Мотивация и разработка

Предварительный независимый replay старой серии 3600 с при 18 авто/мин на подход показал для исходного Queue-based около 293 переключений за прогон, 880 с суммарного жёлтого и среднее зелёное около 9,3 с. Vehicle-actuated переключался примерно 75 раз, тратил 226 с на жёлтый и удерживал зелёный в среднем 44,2 с. Это согласуется с чрезмерно ранним пороговым переключением между двумя большими очередями, но само по себе не изолирует причинный эффект.

Новый независимый final при 18 авто/мин воспроизвёл этот механизм: original в среднем переключался 295 раз, терял на жёлтом 886 с и давал зелёную долю времени 75,4% при средней фазе 9,2 с. Vehicle-actuated переключался 75,6 раза, тратил 226,5 с на жёлтый, средняя зелёная фаза составляла 44,1 с, зелёная доля — 93,7%. При 24 авто/мин значения составили 288 переключений/864 с жёлтого/9,5 с зелёного у original против 78,5/235,5/42,3 с у improved. Зелёная занятость lane-time оставалась около 99–100% у всех насыщенных контроллеров: потери исходного правила объясняются малой долей зелёного и частой сменой фаз, а не преимущественно пустым зелёным.

Первый development screen постоянных minimum green на seed 701–715 не дал кандидата, который одновременно держал умеренный спрос в пределах допуска. Поэтому правило было изменено до финального набора: базовый минимум 8 с; при наблюдаемой сумме очередей от 14 автомобилей — адаптивный минимум 25 с; max 45 с; абсолютный margin 1 и относительный 10%. Четырнадцать из 18 вариантов development screen seed 801–815 прошли заранее заданные non-inferiority gates. Точная процедура отбора и все варианты сохранены в `outputs/queue_based_adaptive_development_selection.json`.

## Paired-сопоставление

Положительное Δ ожидания означает, что improved уменьшил среднее ожидание относительно original; отрицательное Δ throughput означает потерю пропускной способности improved. Sign-test p и Holm p показаны отдельно для разности ожидания.

{improvement_table(summary, contrasts)}

При перегрузке improved сокращает основные индикаторы неудовлетворённого спроса относительно original: при 3600 с и 18 авто/мин уменьшает очередь в среднем на 302,68 автомобиля, увеличивает throughput на 627,07 авто/ч и уменьшает ожидающих на конце на 627,13; при 24 авто/мин соответствующие изменения составляют −302,93, +618,27 и −618,40. Эти эффекты не делают improved победителем над Vehicle-actuated: при 18 авто/мин его среднее ожидание выше на 10,36 с, а при 24 — на 4,34 с. В последнем режиме он статистически близок к Webster по среднему ожиданию.

На 18 авто/мин Queue-based original также лучше Fixed 8 по завершённому ожиданию на 73,47 с при горизонте 3600 с, несмотря на одинаковый минимум зелёного 8 с. Однако отличие числа переключений, фактических зелёных интервалов и суммарного жёлтого не позволяет приписать эту разницу только информации об очередях. Результаты опровергают объяснение «всё преимущество — от минимума 8 с», но не являются изолированным причинным экспериментом.

## Вывод

Вывод основан на полной таблице, а не только на среднем ожидании: оцениваются очередь, throughput и остаточные автомобили. Даже устойчивое превосходство improved над original не доказывает превосходство над Webster или Vehicle-actuated. Если в сценарии очереди/остатки улучшаются, но ожидание обслуженных машин ухудшается, это описывается как компромисс, а не общий выигрыш. Максимальное ожидание и справедливость остаются ограничителями и приводятся в итоговом CSV.

Незавершённые автомобили рассматриваются как цензурированная когорта: известна накопленная задержка до горизонта, но не будущее время выезда. Полный горизонт от пустого состояния сохранён, отдельно сопоставлены пустые очереди и по пять начальных автомобилей на подход; измерения после 300 с являются только чувствительностью к переходному периоду, а не основной оценкой.
"""
    revision = f"""# Материалы для следующей редакции PIERE

Документ содержит предложения по статье после завершённой проверки. Существующие рукописи этим этапом не переписывались.

## Рекомендации

1. Включить **Fixed 8 s** в таблицу baseline. Его отсутствие не позволяло оценить, не объясняется ли результат просто коротким циклом. Fixed 8 имеет тот же зелёный 8 с и жёлтый 3 с, но не использует очередь.
2. Оставить исходный Queue-based под отдельным именем и в качестве воспроизводимого метода. Improved — отдельная новая эвристика, не переименовывать и не подменять оригинал.
3. В Methodology указать min 8/max 45/жёлтый 3/absolute margin 1 для original, адаптивное правило improved, правило наблюдения очередей, seed и переходный режим. Параметры improved были отобраны только на development seed 801–815.
4. Обновить таблицы для всех девяти сценариев отдельно при 1800 и 3600 с. Использовать парный средний эффект и CI; дополнительно показывать queue-area mean, throughput, residual waiting queue и switching/yellow metrics.
5. Обновить графики динамики очередей, распределения фаз, переключений и загрузки зелёного. Для рисунка трасс явно указать пример seed 1001; полная количественная оценка базируется на всех 30 seed.
6. Переписать Conclusion как условный вывод по сценариям. Не заявлять универсального превосходства и не называть сравнение с одним Fixed 8 причинным доказательством: длительность фаз, число переключений и yellow-loss одновременно различаются.
7. Ограничить научную новизну проверяемым вкладом: исследование очередевой эвристики под несколькими профилями спроса и независимая оценка симуляции; не заявлять доказанное преимущество AI без подтверждённых результатами сравнений.

## Числовое основание

Итоговый обзор находится в `outputs/queue_based_final_summary.csv`; paired-статистика для контрастов original/improved и baseline — в `outputs/queue_based_final_paired_contrasts.csv`. Главная сравнительная таблица, средние ожидания с 95% ДИ и изменение original vs improved по всем 18 scenario × horizon приведены в `paper/QUEUE_BASED_FINAL_EXPERIMENTS.md` и `paper/QUEUE_BASED_IMPROVEMENT_ASSESSMENT_RU.md`.

Проверки завершены: 1800 с — {audit['runs_1800']} прогонов; 3600 с — {audit['runs_3600']} прогонов; replay-расхождений — {audit['metric_mismatch_runs']}. Основная оценка начинается с пустого состояния без исключения warm-up; чувствительность к начальным очередям показана отдельно. Среднее ожидание — только среди выехавших до конца горизонта, поэтому выводы опираются также на накопленную задержку и остаточную очередь.

## Перед подачей

Проверить соответствие итоговой версии точному шаблону PIERE, библиографические требования и фактические таблицы/рисунки в шестистраничной рукописи. Этот этап формирует редакционные предложения и не изменяет английскую/русскую основную статью.
"""
    (ROOT / "paper/QUEUE_BASED_FINAL_EXPERIMENTS.md").write_text(experiments, encoding="utf-8")
    (ROOT / "paper/QUEUE_BASED_IMPROVEMENT_ASSESSMENT_RU.md").write_text(assessment, encoding="utf-8")
    (ROOT / "paper/QUEUE_BASED_RESULTS_FOR_REVISION.md").write_text(revision, encoding="utf-8")
    print("wrote 3 queue-based research documents")


if __name__ == "__main__":
    main()
