# Динамика минимальной зелёной фазы: development screen

Парная серия: 30 seed (5101–5130), 7 сценариев, горизонт 1800 с; у каждого контроллера одинаковые arrivals в пределах scenario/seed. Это исследовательский development набор, а не независимый final test.
Положительное Δ mean wait означает, что controller A хуже controller B. Holm-коррекция выполняется по 21 паре в каждой семье scenario × metric.

## Основные варианты

| Сценарий | Контроллер | Ожидание, с | Очередь | Остаток, авто | Поток/ч | Jain | Переключения | Жёлтый, % |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| asymmetric_ew | queue_based_hysteresis_14_10 | 6.52 | 3.03 | 3.5 | 1667.5 | 0.987 | 122.4 | 20.34 |
| asymmetric_ew | queue_based_improved | 6.52 | 3.03 | 3.5 | 1667.5 | 0.987 | 122.4 | 20.34 |
| asymmetric_ew | queue_based_persistent_10s | 6.50 | 3.02 | 3.5 | 1667.5 | 0.987 | 122.4 | 20.35 |
| asymmetric_ew | queue_based_persistent_5s | 6.50 | 3.02 | 3.5 | 1667.5 | 0.987 | 122.4 | 20.35 |
| asymmetric_ew | queue_based_smooth_min_green_10_18 | 6.55 | 3.05 | 3.5 | 1667.5 | 0.988 | 122.2 | 20.32 |
| asymmetric_ns | queue_based_hysteresis_14_10 | 6.51 | 3.02 | 4.2 | 1662.9 | 0.988 | 121.9 | 20.28 |
| asymmetric_ns | queue_based_improved | 6.51 | 3.02 | 4.2 | 1662.9 | 0.988 | 121.9 | 20.28 |
| asymmetric_ns | queue_based_persistent_10s | 6.51 | 3.02 | 4.2 | 1662.9 | 0.988 | 121.9 | 20.28 |
| asymmetric_ns | queue_based_persistent_5s | 6.51 | 3.02 | 4.2 | 1662.9 | 0.988 | 121.9 | 20.28 |
| asymmetric_ns | queue_based_smooth_min_green_10_18 | 6.59 | 3.06 | 4.2 | 1662.9 | 0.989 | 121.7 | 20.26 |
| high_load | queue_based_hysteresis_14_10 | 201.57 | 240.28 | 463.5 | 3383.5 | 0.986 | 46.0 | 7.66 |
| high_load | queue_based_improved | 201.18 | 239.85 | 462.9 | 3384.6 | 0.986 | 46.1 | 7.68 |
| high_load | queue_based_persistent_10s | 201.93 | 240.70 | 464.3 | 3381.9 | 0.986 | 46.7 | 7.78 |
| high_load | queue_based_persistent_5s | 201.24 | 239.92 | 463.0 | 3384.5 | 0.986 | 46.2 | 7.70 |
| high_load | queue_based_smooth_min_green_10_18 | 201.26 | 239.97 | 463.2 | 3384.1 | 0.986 | 46.0 | 7.67 |
| sudden_dominance_switch | queue_based_hysteresis_14_10 | 6.46 | 2.99 | 3.6 | 1660.0 | 0.994 | 121.4 | 20.19 |
| sudden_dominance_switch | queue_based_improved | 6.46 | 2.99 | 3.6 | 1660.0 | 0.994 | 121.4 | 20.19 |
| sudden_dominance_switch | queue_based_persistent_10s | 6.46 | 2.99 | 3.6 | 1660.0 | 0.994 | 121.4 | 20.19 |
| sudden_dominance_switch | queue_based_persistent_5s | 6.46 | 2.99 | 3.6 | 1660.0 | 0.994 | 121.4 | 20.19 |
| sudden_dominance_switch | queue_based_smooth_min_green_10_18 | 6.46 | 2.99 | 3.6 | 1660.0 | 0.993 | 121.3 | 20.18 |
| symmetric_9 | queue_based_hysteresis_14_10 | 10.03 | 5.98 | 7.5 | 2130.0 | 0.990 | 144.7 | 24.08 |
| symmetric_9 | queue_based_improved | 9.93 | 5.92 | 7.7 | 2129.5 | 0.992 | 147.7 | 24.58 |
| symmetric_9 | queue_based_persistent_10s | 10.02 | 5.97 | 7.7 | 2129.5 | 0.991 | 149.0 | 24.80 |
| symmetric_9 | queue_based_persistent_5s | 9.98 | 5.95 | 7.7 | 2129.5 | 0.992 | 148.4 | 24.70 |
| symmetric_9 | queue_based_smooth_min_green_10_18 | 9.65 | 5.75 | 7.2 | 2130.5 | 0.992 | 145.5 | 24.22 |
| symmetric_low | queue_based_hysteresis_14_10 | 5.37 | 1.07 | 1.4 | 716.6 | 0.985 | 85.0 | 14.16 |
| symmetric_low | queue_based_improved | 5.37 | 1.07 | 1.4 | 716.6 | 0.985 | 85.0 | 14.16 |
| symmetric_low | queue_based_persistent_10s | 5.37 | 1.07 | 1.4 | 716.6 | 0.985 | 85.0 | 14.16 |
| symmetric_low | queue_based_persistent_5s | 5.37 | 1.07 | 1.4 | 716.6 | 0.985 | 85.0 | 14.16 |
| symmetric_low | queue_based_smooth_min_green_10_18 | 5.37 | 1.07 | 1.4 | 716.6 | 0.985 | 85.0 | 14.16 |
| true_oversaturated | queue_based_hysteresis_14_10 | 367.21 | 583.77 | 1160.4 | 3419.2 | 0.997 | 40.7 | 6.76 |
| true_oversaturated | queue_based_improved | 367.11 | 583.67 | 1160.3 | 3419.5 | 0.997 | 40.7 | 6.77 |
| true_oversaturated | queue_based_persistent_10s | 367.81 | 584.46 | 1161.0 | 3418.0 | 0.997 | 41.2 | 6.86 |
| true_oversaturated | queue_based_persistent_5s | 367.22 | 583.80 | 1160.4 | 3419.1 | 0.997 | 41.0 | 6.82 |
| true_oversaturated | queue_based_smooth_min_green_10_18 | 367.20 | 583.72 | 1160.2 | 3419.6 | 0.997 | 40.6 | 6.76 |

Полные seed-level показатели и парные контрасты находятся в соседних CSV. Максимальный сигнал red рассчитан по истории фаз и не равен времени ожидания автомобиля на red.
