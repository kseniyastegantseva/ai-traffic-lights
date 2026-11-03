# Congestion по обслуживаемой оси, development, 1800 с

Paired development screen on new seeds 7101–7130. Compares the current intersection-total congestion trigger with a policy that activates the 25-second minimum only when the currently served axis itself has at least 14 queued vehicles. Includes original Queue-based and Vehicle-actuated references.

## Методика

Для каждой пары сценарий/seed стратегии используют общий хэшированный поток. Процент изменения среднего ожидания рассчитан относительно указанного в сводной таблице baseline (`fixed_35` или `fixed`); если baseline не запускался, показано N/A.

## Сводная таблица

| Сценарий | Стратегия | Запуски | Среднее ожидание, с | Медианное ожидание, с | Средняя очередь | Максимальная очередь | Пропускная способность/час | Справедливость | Baseline | Изменение к baseline, % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Асимметричный спрос Восток–Запад | queue_based | 30 | 6.47 | 5.61 | 3.03 | 11.43 | 1673.73 | 0.99 | N/A | N/A |
| Асимметричный спрос Восток–Запад | queue_based_axis_specific_congestion | 30 | 6.47 | 5.61 | 3.03 | 11.43 | 1673.73 | 0.99 | N/A | N/A |
| Асимметричный спрос Восток–Запад | queue_based_improved | 30 | 6.47 | 5.61 | 3.03 | 11.43 | 1673.73 | 0.99 | N/A | N/A |
| Асимметричный спрос Восток–Запад | vehicle_actuated | 30 | 6.66 | 5.80 | 3.11 | 12.13 | 1674.33 | 0.98 | N/A | N/A |
| Асимметричный спрос Север–Юг | queue_based | 30 | 6.45 | 5.51 | 3.02 | 11.83 | 1673.93 | 0.99 | N/A | N/A |
| Асимметричный спрос Север–Юг | queue_based_axis_specific_congestion | 30 | 6.46 | 5.51 | 3.02 | 11.80 | 1673.93 | 0.99 | N/A | N/A |
| Асимметричный спрос Север–Юг | queue_based_improved | 30 | 6.45 | 5.50 | 3.02 | 11.80 | 1673.93 | 0.99 | N/A | N/A |
| Асимметричный спрос Север–Юг | vehicle_actuated | 30 | 6.61 | 5.73 | 3.09 | 12.10 | 1673.47 | 0.97 | N/A | N/A |
| Высокая нагрузка | queue_based | 30 | 319.67 | 318.72 | 382.02 | 758.67 | 2793.80 | 0.99 | N/A | N/A |
| Высокая нагрузка | queue_based_axis_specific_congestion | 30 | 206.17 | 207.86 | 244.89 | 466.97 | 3378.20 | 0.98 | N/A | N/A |
| Высокая нагрузка | queue_based_improved | 30 | 203.13 | 204.01 | 241.66 | 463.33 | 3385.13 | 0.98 | N/A | N/A |
| Высокая нагрузка | vehicle_actuated | 30 | 193.70 | 191.63 | 231.62 | 449.20 | 3413.73 | 0.98 | N/A | N/A |
| Внезапная смена доминирующей оси | queue_based | 30 | 6.36 | 5.40 | 2.99 | 12.03 | 1677.20 | 0.99 | N/A | N/A |
| Внезапная смена доминирующей оси | queue_based_axis_specific_congestion | 30 | 6.36 | 5.40 | 2.99 | 12.03 | 1677.20 | 0.99 | N/A | N/A |
| Внезапная смена доминирующей оси | queue_based_improved | 30 | 6.36 | 5.40 | 2.99 | 12.03 | 1677.20 | 0.99 | N/A | N/A |
| Внезапная смена доминирующей оси | vehicle_actuated | 30 | 6.58 | 5.71 | 3.09 | 11.87 | 1677.27 | 1.00 | N/A | N/A |
| Симметричный спрос 9 авто/мин | queue_based | 30 | 10.23 | 9.31 | 6.15 | 18.30 | 2144.20 | 0.99 | N/A | N/A |
| Симметричный спрос 9 авто/мин | queue_based_axis_specific_congestion | 30 | 10.12 | 9.28 | 6.08 | 17.83 | 2144.27 | 0.99 | N/A | N/A |
| Симметричный спрос 9 авто/мин | queue_based_improved | 30 | 9.94 | 9.13 | 5.97 | 17.67 | 2145.33 | 0.99 | N/A | N/A |
| Симметричный спрос 9 авто/мин | vehicle_actuated | 30 | 9.31 | 8.24 | 5.59 | 16.93 | 2145.07 | 1.00 | N/A | N/A |
| Низкий симметричный спрос | queue_based | 30 | 5.38 | 3.54 | 1.09 | 5.77 | 721.80 | 0.99 | N/A | N/A |
| Низкий симметричный спрос | queue_based_axis_specific_congestion | 30 | 5.38 | 3.54 | 1.09 | 5.77 | 721.80 | 0.99 | N/A | N/A |
| Низкий симметричный спрос | queue_based_improved | 30 | 5.38 | 3.54 | 1.09 | 5.77 | 721.80 | 0.99 | N/A | N/A |
| Низкий симметричный спрос | vehicle_actuated | 30 | 4.26 | 3.27 | 0.86 | 5.73 | 722.27 | 0.99 | N/A | N/A |
| Насыщенный спрос 24 авто/мин | queue_based | 30 | 458.24 | 456.82 | 733.51 | 1473.43 | 2821.27 | 1.00 | N/A | N/A |
| Насыщенный спрос 24 авто/мин | queue_based_axis_specific_congestion | 30 | 370.24 | 370.57 | 590.15 | 1176.23 | 3415.67 | 1.00 | N/A | N/A |
| Насыщенный спрос 24 авто/мин | queue_based_improved | 30 | 368.98 | 369.85 | 588.66 | 1174.93 | 3418.20 | 1.00 | N/A | N/A |
| Насыщенный спрос 24 авто/мин | vehicle_actuated | 30 | 365.25 | 365.51 | 584.23 | 1169.57 | 3429.20 | 1.00 | N/A | N/A |

## Рейтинг стратегий по сценариям

| Сценарий | Стратегия | Ранг | Среднее ожидание, с | Изменение к baseline, % |
| --- | --- | --- | --- | --- |
| Асимметричный спрос Восток–Запад | queue_based | 1 | 6.47 | N/A |
| Асимметричный спрос Восток–Запад | queue_based_axis_specific_congestion | 1 | 6.47 | N/A |
| Асимметричный спрос Восток–Запад | queue_based_improved | 1 | 6.47 | N/A |
| Асимметричный спрос Восток–Запад | vehicle_actuated | 4 | 6.66 | N/A |
| Асимметричный спрос Север–Юг | queue_based | 1 | 6.45 | N/A |
| Асимметричный спрос Север–Юг | queue_based_improved | 2 | 6.45 | N/A |
| Асимметричный спрос Север–Юг | queue_based_axis_specific_congestion | 3 | 6.46 | N/A |
| Асимметричный спрос Север–Юг | vehicle_actuated | 4 | 6.61 | N/A |
| Внезапная смена доминирующей оси | queue_based_axis_specific_congestion | 1 | 6.36 | N/A |
| Внезапная смена доминирующей оси | queue_based_improved | 1 | 6.36 | N/A |
| Внезапная смена доминирующей оси | queue_based | 3 | 6.36 | N/A |
| Внезапная смена доминирующей оси | vehicle_actuated | 4 | 6.58 | N/A |
| Высокая нагрузка | vehicle_actuated | 1 | 193.70 | N/A |
| Высокая нагрузка | queue_based_improved | 2 | 203.13 | N/A |
| Высокая нагрузка | queue_based_axis_specific_congestion | 3 | 206.17 | N/A |
| Высокая нагрузка | queue_based | 4 | 319.67 | N/A |
| Насыщенный спрос 24 авто/мин | vehicle_actuated | 1 | 365.25 | N/A |
| Насыщенный спрос 24 авто/мин | queue_based_improved | 2 | 368.98 | N/A |
| Насыщенный спрос 24 авто/мин | queue_based_axis_specific_congestion | 3 | 370.24 | N/A |
| Насыщенный спрос 24 авто/мин | queue_based | 4 | 458.24 | N/A |
| Низкий симметричный спрос | vehicle_actuated | 1 | 4.26 | N/A |
| Низкий симметричный спрос | queue_based | 2 | 5.38 | N/A |
| Низкий симметричный спрос | queue_based_axis_specific_congestion | 2 | 5.38 | N/A |
| Низкий симметричный спрос | queue_based_improved | 2 | 5.38 | N/A |
| Симметричный спрос 9 авто/мин | vehicle_actuated | 1 | 9.31 | N/A |
| Симметричный спрос 9 авто/мин | queue_based_improved | 2 | 9.94 | N/A |
| Симметричный спрос 9 авто/мин | queue_based_axis_specific_congestion | 3 | 10.12 | N/A |
| Симметричный спрос 9 авто/мин | queue_based | 4 | 10.23 | N/A |

## Сводка по стратегиям

| Стратегия | Победы | Средний ранг | Среднее ожидание, с | Среднее изменение к baseline, % | Средняя очередь | Справедливость |
| --- | --- | --- | --- | --- | --- | --- |
| queue_based_improved | 2 | 1.71 | 86.67 | N/A | 120.92 | 0.99 |
| vehicle_actuated | 4 | 2.29 | 84.63 | N/A | 118.80 | 0.99 |
| queue_based_axis_specific_congestion | 2 | 2.29 | 87.31 | N/A | 121.61 | 0.99 |
| queue_based | 2 | 2.71 | 116.12 | N/A | 161.68 | 0.99 |

## Основные выводы

## Парные различия queue_based

Разность определена как ожидание `queue_based` минус ожидание сравниваемого алгоритма; отрицательное значение означает меньшее ожидание у queue_based. Интервалы — 95% доверительные t-интервалы среднего парного различия по точному квантилю Стьюдента. P-value получено двусторонним точным знаковым тестом без нулевых разностей; поправка Holm применяется к фактически присутствующим сравнениям внутри каждой пары сценарий/горизонт.

| scenario | duration_seconds | comparator | pairs | mean Δ, s | 95% CI, s | sign p | Holm p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| asymmetric_ew | 1800 | queue_based_axis_specific_congestion | 30 | 0.00 | [0.00, 0.00] | 1.0000 | 1.0000 |
| asymmetric_ew | 1800 | queue_based_improved | 30 | 0.00 | [0.00, 0.00] | 1.0000 | 1.0000 |
| asymmetric_ew | 1800 | vehicle_actuated | 30 | -0.19 | [-0.34, -0.05] | 0.0428 | 0.1283 |
| asymmetric_ns | 1800 | queue_based_axis_specific_congestion | 30 | -0.00 | [-0.01, 0.00] | 0.5000 | 1.0000 |
| asymmetric_ns | 1800 | queue_based_improved | 30 | -0.00 | [-0.01, 0.01] | 1.0000 | 1.0000 |
| asymmetric_ns | 1800 | vehicle_actuated | 30 | -0.15 | [-0.28, -0.02] | 0.0014 | 0.0043 |
| high_load | 1800 | queue_based_axis_specific_congestion | 30 | 113.50 | [111.00, 116.01] | <0.0001 | <0.0001 |
| high_load | 1800 | queue_based_improved | 30 | 116.54 | [114.11, 118.97] | <0.0001 | <0.0001 |
| high_load | 1800 | vehicle_actuated | 30 | 125.97 | [123.18, 128.77] | <0.0001 | <0.0001 |
| sudden_dominance_switch | 1800 | queue_based_axis_specific_congestion | 30 | 0.00 | [-0.00, 0.00] | 1.0000 | 1.0000 |
| sudden_dominance_switch | 1800 | queue_based_improved | 30 | 0.00 | [-0.00, 0.00] | 1.0000 | 1.0000 |
| sudden_dominance_switch | 1800 | vehicle_actuated | 30 | -0.22 | [-0.36, -0.08] | 0.0161 | 0.0484 |
| symmetric_9 | 1800 | queue_based_axis_specific_congestion | 30 | 0.10 | [-0.00, 0.21] | 0.1849 | 0.1849 |
| symmetric_9 | 1800 | queue_based_improved | 30 | 0.29 | [0.17, 0.40] | 0.0002 | 0.0004 |
| symmetric_9 | 1800 | vehicle_actuated | 30 | 0.91 | [0.70, 1.12] | <0.0001 | <0.0001 |
| symmetric_low | 1800 | queue_based_axis_specific_congestion | 30 | 0.00 | [0.00, 0.00] | 1.0000 | 1.0000 |
| symmetric_low | 1800 | queue_based_improved | 30 | 0.00 | [0.00, 0.00] | 1.0000 | 1.0000 |
| symmetric_low | 1800 | vehicle_actuated | 30 | 1.12 | [0.99, 1.26] | <0.0001 | <0.0001 |
| true_oversaturated | 1800 | queue_based_axis_specific_congestion | 30 | 88.00 | [85.61, 90.40] | <0.0001 | <0.0001 |
| true_oversaturated | 1800 | queue_based_improved | 30 | 89.27 | [87.02, 91.51] | <0.0001 | <0.0001 |
| true_oversaturated | 1800 | vehicle_actuated | 30 | 92.99 | [90.67, 95.32] | <0.0001 | <0.0001 |

- `Асимметричный спрос Восток–Запад`: лучшая стратегия `queue_based` со средним ожиданием 6.47 с.
- `Асимметричный спрос Север–Юг`: лучшая стратегия `queue_based` со средним ожиданием 6.45 с.
- `Высокая нагрузка`: лучшая стратегия `vehicle_actuated` со средним ожиданием 193.70 с.
- `Внезапная смена доминирующей оси`: лучшая стратегия `queue_based_axis_specific_congestion` со средним ожиданием 6.36 с.
- `Симметричный спрос 9 авто/мин`: лучшая стратегия `vehicle_actuated` со средним ожиданием 9.31 с.
- `Низкий симметричный спрос`: лучшая стратегия `vehicle_actuated` со средним ожиданием 4.26 с.
- `Насыщенный спрос 24 авто/мин`: лучшая стратегия `vehicle_actuated` со средним ожиданием 365.25 с.
- В среднем по всем сценариям лучшая стратегия по рангу — `queue_based_improved`: средний ранг 1.71, побед 2.
