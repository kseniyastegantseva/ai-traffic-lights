# Пороги переключения очередей: development screen

30 парных seed (8101–8130), 7 сценариев, 1800 с. Варьируются абсолютный margin, относительная доля суммарной очереди и отдельный margin, уменьшающийся после effective min-green. Положительное Δ mean wait означает хуже для controller A. Holm выполняется по 28 парам внутри каждой scenario × metric семьи.

| Сценарий | Контроллер | Wait, с | Queue | Residual | Throughput/ч | Jain | Switches | Yellow, % |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| asymmetric_ew | improved_abs1_rel010 | 6.47 | 3.03 | 4.3 | 1676.5 | 0.984 | 121.4 | 20.20 |
| asymmetric_ew | margin_abs0_rel000 | 7.15 | 3.35 | 4.9 | 1675.3 | 0.987 | 141.2 | 23.50 |
| asymmetric_ew | margin_abs1_rel000 | 6.47 | 3.03 | 4.3 | 1676.5 | 0.984 | 121.4 | 20.20 |
| asymmetric_ew | margin_abs1_rel020 | 6.39 | 2.99 | 4.3 | 1676.5 | 0.981 | 120.7 | 20.09 |
| asymmetric_ew | margin_abs2_rel000 | 6.53 | 3.06 | 4.2 | 1676.8 | 0.919 | 100.3 | 16.71 |
| asymmetric_ew | margin_elapsed_decay_0025 | 6.39 | 2.99 | 4.3 | 1676.5 | 0.981 | 120.7 | 20.09 |
| asymmetric_ew | queue_based | 6.47 | 3.03 | 4.3 | 1676.5 | 0.984 | 121.4 | 20.20 |
| asymmetric_ew | vehicle_actuated | 6.59 | 3.08 | 4.2 | 1676.8 | 0.972 | 124.9 | 20.76 |
| asymmetric_ns | improved_abs1_rel010 | 6.58 | 3.08 | 4.2 | 1675.5 | 0.982 | 121.8 | 20.26 |
| asymmetric_ns | margin_abs0_rel000 | 7.28 | 3.41 | 4.9 | 1674.1 | 0.987 | 142.1 | 23.62 |
| asymmetric_ns | margin_abs1_rel000 | 6.58 | 3.08 | 4.2 | 1675.5 | 0.982 | 121.8 | 20.26 |
| asymmetric_ns | margin_abs1_rel020 | 6.53 | 3.06 | 4.1 | 1675.6 | 0.980 | 121.5 | 20.21 |
| asymmetric_ns | margin_abs2_rel000 | 6.52 | 3.05 | 4.9 | 1674.1 | 0.922 | 99.6 | 16.57 |
| asymmetric_ns | margin_elapsed_decay_0025 | 6.53 | 3.06 | 4.1 | 1675.6 | 0.980 | 121.5 | 20.21 |
| asymmetric_ns | queue_based | 6.58 | 3.08 | 4.2 | 1675.5 | 0.982 | 121.8 | 20.26 |
| asymmetric_ns | vehicle_actuated | 6.72 | 3.14 | 4.9 | 1674.0 | 0.973 | 125.7 | 20.93 |
| high_load | improved_abs1_rel010 | 204.08 | 244.05 | 469.3 | 3386.4 | 0.984 | 46.0 | 7.66 |
| high_load | margin_abs0_rel000 | 213.01 | 255.94 | 502.0 | 3320.9 | 0.985 | 63.1 | 10.49 |
| high_load | margin_abs1_rel000 | 213.03 | 255.96 | 502.2 | 3320.7 | 0.986 | 62.8 | 10.45 |
| high_load | margin_abs1_rel020 | 197.95 | 237.39 | 459.1 | 3406.8 | 0.983 | 41.8 | 6.94 |
| high_load | margin_abs2_rel000 | 213.05 | 255.98 | 502.3 | 3320.3 | 0.986 | 62.6 | 10.41 |
| high_load | margin_elapsed_decay_0025 | 201.53 | 241.26 | 465.4 | 3394.1 | 0.984 | 43.2 | 7.18 |
| high_load | queue_based | 318.76 | 383.27 | 763.8 | 2797.3 | 0.994 | 146.1 | 24.33 |
| high_load | vehicle_actuated | 195.94 | 235.32 | 456.4 | 3412.1 | 0.978 | 37.9 | 6.32 |
| sudden_dominance_switch | improved_abs1_rel010 | 6.56 | 3.07 | 4.9 | 1674.9 | 0.993 | 122.5 | 20.37 |
| sudden_dominance_switch | margin_abs0_rel000 | 7.29 | 3.42 | 5.1 | 1674.5 | 0.993 | 142.8 | 23.77 |
| sudden_dominance_switch | margin_abs1_rel000 | 6.56 | 3.07 | 4.9 | 1674.9 | 0.993 | 122.5 | 20.37 |
| sudden_dominance_switch | margin_abs1_rel020 | 6.52 | 3.05 | 4.8 | 1675.1 | 0.994 | 122.2 | 20.33 |
| sudden_dominance_switch | margin_abs2_rel000 | 6.52 | 3.05 | 4.4 | 1675.9 | 0.991 | 100.5 | 16.71 |
| sudden_dominance_switch | margin_elapsed_decay_0025 | 6.52 | 3.05 | 4.8 | 1675.1 | 0.994 | 122.2 | 20.33 |
| sudden_dominance_switch | queue_based | 6.56 | 3.07 | 4.9 | 1674.9 | 0.993 | 122.5 | 20.37 |
| sudden_dominance_switch | vehicle_actuated | 6.68 | 3.13 | 4.4 | 1675.9 | 0.995 | 126.5 | 21.05 |
| symmetric_9 | improved_abs1_rel010 | 10.30 | 6.22 | 7.3 | 2157.3 | 0.989 | 147.4 | 24.53 |
| symmetric_9 | margin_abs0_rel000 | 11.12 | 6.72 | 7.6 | 2156.8 | 0.985 | 152.7 | 25.40 |
| symmetric_9 | margin_abs1_rel000 | 10.36 | 6.26 | 7.3 | 2157.4 | 0.988 | 147.0 | 24.47 |
| symmetric_9 | margin_abs1_rel020 | 9.61 | 5.81 | 6.9 | 2158.2 | 0.992 | 145.1 | 24.15 |
| symmetric_9 | margin_abs2_rel000 | 9.57 | 5.79 | 7.2 | 2157.5 | 0.991 | 135.8 | 22.59 |
| symmetric_9 | margin_elapsed_decay_0025 | 9.62 | 5.81 | 6.9 | 2158.1 | 0.992 | 145.3 | 24.17 |
| symmetric_9 | queue_based | 10.69 | 6.47 | 8.0 | 2156.0 | 0.987 | 150.2 | 24.99 |
| symmetric_9 | vehicle_actuated | 9.59 | 5.80 | 7.1 | 2157.9 | 0.996 | 107.6 | 17.89 |
| symmetric_low | improved_abs1_rel010 | 5.34 | 1.07 | 1.5 | 720.3 | 0.984 | 84.1 | 14.00 |
| symmetric_low | margin_abs0_rel000 | 4.43 | 0.89 | 1.6 | 720.1 | 0.991 | 124.8 | 20.77 |
| symmetric_low | margin_abs1_rel000 | 5.34 | 1.07 | 1.5 | 720.3 | 0.984 | 84.1 | 14.00 |
| symmetric_low | margin_abs1_rel020 | 5.34 | 1.07 | 1.5 | 720.3 | 0.984 | 84.1 | 14.00 |
| symmetric_low | margin_abs2_rel000 | 7.36 | 1.48 | 2.1 | 719.1 | 0.985 | 62.2 | 10.34 |
| symmetric_low | margin_elapsed_decay_0025 | 5.34 | 1.07 | 1.5 | 720.3 | 0.984 | 84.1 | 14.00 |
| symmetric_low | queue_based | 5.34 | 1.07 | 1.5 | 720.3 | 0.984 | 84.1 | 14.00 |
| symmetric_low | vehicle_actuated | 4.44 | 0.89 | 1.7 | 719.9 | 0.992 | 123.8 | 20.61 |
| true_oversaturated | improved_abs1_rel010 | 370.31 | 592.09 | 1175.5 | 3419.5 | 0.997 | 40.7 | 6.77 |
| true_oversaturated | margin_abs0_rel000 | 381.02 | 611.05 | 1218.9 | 3332.5 | 0.997 | 62.0 | 10.31 |
| true_oversaturated | margin_abs1_rel000 | 380.89 | 610.85 | 1218.6 | 3333.3 | 0.997 | 61.8 | 10.25 |
| true_oversaturated | margin_abs1_rel020 | 367.16 | 588.30 | 1171.1 | 3428.2 | 0.996 | 39.1 | 6.51 |
| true_oversaturated | margin_abs2_rel000 | 380.58 | 610.54 | 1218.4 | 3333.6 | 0.997 | 61.3 | 10.22 |
| true_oversaturated | margin_elapsed_decay_0025 | 368.88 | 590.42 | 1173.8 | 3422.7 | 0.997 | 39.7 | 6.61 |
| true_oversaturated | queue_based | 458.63 | 736.26 | 1473.3 | 2823.9 | 0.998 | 142.7 | 23.74 |
| true_oversaturated | vehicle_actuated | 366.48 | 587.51 | 1170.6 | 3429.2 | 0.996 | 37.4 | 6.23 |

Полные метрики и скорректированные парные контрасты см. в соседних CSV. Это development-данные; новые seed ещё не использовались для независимой validation.
