# Congestion по обслуживаемой оси: development screen

30 парных seed (7101–7130), 7 сценариев, 1800 с. Axis-specific включает congested min-green только если очередь на текущей зелёной оси ≥14; baseline Improved включает его при сумме очередей двух осей ≥14. Положительное Δ mean wait означает хуже для controller A. Holm выполняется по шести парам внутри каждой scenario × metric семьи.

| Сценарий | Контроллер | Wait, с | Queue | Residual | Throughput/ч | Jain | Switches | Yellow, % |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| asymmetric_ew | queue_based | 6.47 | 3.03 | 4.3 | 1673.7 | 0.986 | 122.3 | 20.32 |
| asymmetric_ew | queue_based_axis_specific_congestion | 6.47 | 3.03 | 4.3 | 1673.7 | 0.986 | 122.3 | 20.32 |
| asymmetric_ew | queue_based_improved | 6.47 | 3.03 | 4.3 | 1673.7 | 0.986 | 122.3 | 20.32 |
| asymmetric_ew | vehicle_actuated | 6.66 | 3.11 | 4.0 | 1674.3 | 0.977 | 125.8 | 20.93 |
| asymmetric_ns | queue_based | 6.45 | 3.02 | 4.3 | 1673.9 | 0.986 | 122.4 | 20.36 |
| asymmetric_ns | queue_based_axis_specific_congestion | 6.46 | 3.02 | 4.3 | 1673.9 | 0.985 | 122.4 | 20.36 |
| asymmetric_ns | queue_based_improved | 6.45 | 3.02 | 4.3 | 1673.9 | 0.985 | 122.4 | 20.36 |
| asymmetric_ns | vehicle_actuated | 6.61 | 3.09 | 4.5 | 1673.5 | 0.973 | 126.5 | 21.05 |
| high_load | queue_based | 319.67 | 382.02 | 759.7 | 2793.8 | 0.994 | 146.4 | 24.38 |
| high_load | queue_based_axis_specific_congestion | 206.17 | 244.89 | 467.5 | 3378.2 | 0.983 | 48.5 | 8.08 |
| high_load | queue_based_improved | 203.13 | 241.66 | 464.0 | 3385.1 | 0.983 | 46.3 | 7.71 |
| high_load | vehicle_actuated | 193.70 | 231.62 | 449.7 | 3413.7 | 0.976 | 38.2 | 6.35 |
| sudden_dominance_switch | queue_based | 6.36 | 2.99 | 4.4 | 1677.2 | 0.994 | 120.2 | 19.98 |
| sudden_dominance_switch | queue_based_axis_specific_congestion | 6.36 | 2.99 | 4.4 | 1677.2 | 0.994 | 120.2 | 19.98 |
| sudden_dominance_switch | queue_based_improved | 6.36 | 2.99 | 4.4 | 1677.2 | 0.994 | 120.2 | 19.98 |
| sudden_dominance_switch | vehicle_actuated | 6.58 | 3.09 | 4.3 | 1677.3 | 0.996 | 125.4 | 20.85 |
| symmetric_9 | queue_based | 10.23 | 6.15 | 7.8 | 2144.2 | 0.987 | 149.3 | 24.82 |
| symmetric_9 | queue_based_axis_specific_congestion | 10.12 | 6.08 | 7.7 | 2144.3 | 0.988 | 149.2 | 24.82 |
| symmetric_9 | queue_based_improved | 9.94 | 5.97 | 7.2 | 2145.3 | 0.989 | 147.4 | 24.54 |
| symmetric_9 | vehicle_actuated | 9.31 | 5.59 | 7.3 | 2145.1 | 0.996 | 107.9 | 17.97 |
| symmetric_low | queue_based | 5.38 | 1.09 | 1.4 | 721.8 | 0.985 | 85.4 | 14.20 |
| symmetric_low | queue_based_axis_specific_congestion | 5.38 | 1.09 | 1.4 | 721.8 | 0.985 | 85.4 | 14.20 |
| symmetric_low | queue_based_improved | 5.38 | 1.09 | 1.4 | 721.8 | 0.985 | 85.4 | 14.20 |
| symmetric_low | vehicle_actuated | 4.26 | 0.86 | 1.2 | 722.3 | 0.989 | 121.8 | 20.26 |
| true_oversaturated | queue_based | 458.24 | 733.51 | 1474.4 | 2821.3 | 0.998 | 142.3 | 23.70 |
| true_oversaturated | queue_based_axis_specific_congestion | 370.24 | 590.15 | 1177.2 | 3415.7 | 0.997 | 42.1 | 7.01 |
| true_oversaturated | queue_based_improved | 368.98 | 588.66 | 1176.0 | 3418.2 | 0.997 | 41.0 | 6.81 |
| true_oversaturated | vehicle_actuated | 365.25 | 584.23 | 1170.5 | 3429.2 | 0.995 | 37.5 | 6.25 |

Полные метрики и скорректированные парные контрасты см. в соседних CSV. Это development-данные; новые seed ещё не использовались для независимой validation.
