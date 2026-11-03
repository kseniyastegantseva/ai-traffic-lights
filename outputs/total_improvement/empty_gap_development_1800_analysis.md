# Анализ empty-green gap-out: development

Серия носит исследовательский характер; seed 2101–2130 не использовались в предыдущих
матрицах и не являются независимым final-test после просмотра этих результатов.
Положительная парная разность ожидания означает, что candidate хуже comparator.
Поправка Holm применяется к девяти контрастам (3 gap × 3 comparator) внутри каждого
сценария; основные метрики описательны, ожидание — заранее выбранный парный показатель.

## Сводные показатели

| Сценарий | Контроллер | Ожидание, с | Очередь, авто | авто/ч | Остаток, авто | Переключения | Жёлтый, с | Макс. ожидание, с |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| asymmetric_ew | fixed_8 | 19.271 | 9.024 | 1645.7 | 10.2 | 163.0 | 489.0 | 84.2 |
| asymmetric_ew | queue_based | 6.411 | 2.971 | 1657.3 | 4.4 | 121.6 | 364.9 | 37.7 |
| asymmetric_ew | queue_based_empty_gap_0s | 6.661 | 3.088 | 1657.2 | 4.4 | 140.2 | 420.7 | 27.6 |
| asymmetric_ew | queue_based_empty_gap_1s | 6.661 | 3.088 | 1657.2 | 4.4 | 140.2 | 420.7 | 27.6 |
| asymmetric_ew | queue_based_empty_gap_3s | 6.635 | 3.076 | 1656.9 | 4.6 | 137.9 | 413.8 | 28.1 |
| asymmetric_ew | queue_based_improved | 6.409 | 2.971 | 1657.3 | 4.4 | 121.6 | 364.9 | 37.7 |
| asymmetric_ew | queue_based_legacy | 6.662 | 3.089 | 1657.2 | 4.4 | 140.2 | 420.7 | 27.7 |
| asymmetric_ew | vehicle_actuated | 6.588 | 3.053 | 1657.5 | 4.3 | 126.8 | 380.3 | 32.1 |
| asymmetric_ns | fixed_8 | 18.201 | 8.456 | 1637.2 | 10.8 | 163.0 | 489.0 | 82.7 |
| asymmetric_ns | queue_based | 6.375 | 2.938 | 1650.9 | 4.0 | 120.4 | 361.3 | 39.9 |
| asymmetric_ns | queue_based_empty_gap_0s | 6.632 | 3.057 | 1649.7 | 4.6 | 138.9 | 416.7 | 29.4 |
| asymmetric_ns | queue_based_empty_gap_1s | 6.632 | 3.057 | 1649.7 | 4.6 | 138.9 | 416.7 | 29.4 |
| asymmetric_ns | queue_based_empty_gap_3s | 6.638 | 3.059 | 1649.9 | 4.5 | 136.2 | 408.5 | 29.2 |
| asymmetric_ns | queue_based_improved | 6.373 | 2.937 | 1650.9 | 4.0 | 120.4 | 361.3 | 39.9 |
| asymmetric_ns | queue_based_legacy | 6.638 | 3.060 | 1649.7 | 4.6 | 138.9 | 416.7 | 29.5 |
| asymmetric_ns | vehicle_actuated | 6.602 | 3.043 | 1650.3 | 4.2 | 125.8 | 377.5 | 33.7 |
| high_load | fixed_8 | 349.691 | 414.475 | 2610.3 | 832.0 | 163.0 | 489.0 | 747.1 |
| high_load | queue_based | 310.561 | 368.425 | 2792.5 | 740.9 | 146.7 | 440.2 | 673.7 |
| high_load | queue_based_empty_gap_0s | 194.801 | 229.194 | 3384.4 | 444.9 | 46.3 | 138.8 | 426.0 |
| high_load | queue_based_empty_gap_1s | 194.801 | 229.194 | 3384.4 | 444.9 | 46.3 | 138.8 | 426.0 |
| high_load | queue_based_empty_gap_3s | 194.801 | 229.194 | 3384.4 | 444.9 | 46.3 | 138.8 | 426.0 |
| high_load | queue_based_improved | 194.801 | 229.194 | 3384.4 | 444.9 | 46.3 | 138.8 | 426.0 |
| high_load | queue_based_legacy | 310.561 | 368.425 | 2792.5 | 740.9 | 146.7 | 440.2 | 673.7 |
| high_load | vehicle_actuated | 184.838 | 218.507 | 3414.5 | 429.9 | 38.0 | 113.9 | 420.6 |
| sudden_dominance_switch | fixed_8 | 16.976 | 7.864 | 1641.9 | 9.4 | 163.0 | 489.0 | 75.7 |
| sudden_dominance_switch | queue_based | 6.413 | 2.960 | 1651.9 | 4.4 | 120.6 | 361.8 | 39.6 |
| sudden_dominance_switch | queue_based_empty_gap_0s | 6.710 | 3.097 | 1651.1 | 4.8 | 139.7 | 419.2 | 29.6 |
| sudden_dominance_switch | queue_based_empty_gap_1s | 6.710 | 3.097 | 1651.1 | 4.8 | 139.7 | 419.2 | 29.6 |
| sudden_dominance_switch | queue_based_empty_gap_3s | 6.630 | 3.060 | 1651.3 | 4.7 | 136.7 | 410.0 | 29.8 |
| sudden_dominance_switch | queue_based_improved | 6.413 | 2.960 | 1651.9 | 4.4 | 120.6 | 361.8 | 39.6 |
| sudden_dominance_switch | queue_based_legacy | 6.718 | 3.101 | 1651.1 | 4.8 | 139.7 | 419.2 | 29.6 |
| sudden_dominance_switch | vehicle_actuated | 6.574 | 3.034 | 1652.0 | 4.4 | 125.8 | 377.3 | 32.0 |
| symmetric | fixed_8 | 6.921 | 2.742 | 1418.5 | 3.5 | 163.0 | 489.0 | 33.4 |
| symmetric | queue_based | 6.042 | 2.393 | 1418.5 | 3.5 | 132.8 | 398.5 | 31.5 |
| symmetric | queue_based_empty_gap_0s | 5.962 | 2.363 | 1418.3 | 3.6 | 152.1 | 456.2 | 25.9 |
| symmetric | queue_based_empty_gap_1s | 5.962 | 2.363 | 1418.3 | 3.6 | 152.1 | 456.2 | 25.9 |
| symmetric | queue_based_empty_gap_3s | 5.967 | 2.365 | 1418.5 | 3.5 | 150.8 | 452.5 | 25.4 |
| symmetric | queue_based_improved | 6.042 | 2.393 | 1418.5 | 3.5 | 132.8 | 398.5 | 31.5 |
| symmetric | queue_based_legacy | 5.962 | 2.363 | 1418.3 | 3.6 | 152.1 | 456.2 | 25.9 |
| symmetric | vehicle_actuated | 6.012 | 2.384 | 1417.4 | 4.0 | 141.9 | 425.7 | 23.9 |
| symmetric_9 | fixed_8 | 14.531 | 8.650 | 2110.1 | 10.7 | 163.0 | 489.0 | 66.7 |
| symmetric_9 | queue_based | 9.974 | 5.922 | 2115.8 | 7.9 | 149.3 | 447.8 | 43.3 |
| symmetric_9 | queue_based_empty_gap_0s | 9.791 | 5.807 | 2116.9 | 7.4 | 150.7 | 452.0 | 40.0 |
| symmetric_9 | queue_based_empty_gap_1s | 9.791 | 5.807 | 2116.9 | 7.4 | 150.7 | 452.0 | 40.0 |
| symmetric_9 | queue_based_empty_gap_3s | 9.786 | 5.803 | 2116.7 | 7.4 | 150.0 | 450.0 | 40.4 |
| symmetric_9 | queue_based_improved | 9.708 | 5.761 | 2116.3 | 7.6 | 147.3 | 441.8 | 41.1 |
| symmetric_9 | queue_based_legacy | 10.034 | 5.954 | 2116.0 | 7.8 | 152.5 | 457.4 | 42.9 |
| symmetric_9 | vehicle_actuated | 9.162 | 5.434 | 2118.1 | 6.8 | 110.0 | 329.9 | 37.0 |
| symmetric_low | fixed_8 | 5.176 | 1.019 | 706.4 | 1.5 | 163.0 | 489.0 | 18.6 |
| symmetric_low | queue_based | 5.267 | 1.037 | 706.1 | 1.6 | 82.3 | 246.8 | 42.9 |
| symmetric_low | queue_based_empty_gap_0s | 4.261 | 0.841 | 705.8 | 1.8 | 121.6 | 364.8 | 14.9 |
| symmetric_low | queue_based_empty_gap_1s | 4.261 | 0.841 | 705.8 | 1.8 | 121.6 | 364.8 | 14.9 |
| symmetric_low | queue_based_empty_gap_3s | 4.255 | 0.840 | 705.9 | 1.7 | 121.3 | 363.9 | 15.1 |
| symmetric_low | queue_based_improved | 5.267 | 1.037 | 706.1 | 1.6 | 82.3 | 246.8 | 42.9 |
| symmetric_low | queue_based_legacy | 4.261 | 0.841 | 705.8 | 1.8 | 121.6 | 364.8 | 14.9 |
| symmetric_low | vehicle_actuated | 4.270 | 0.842 | 706.1 | 1.7 | 120.7 | 362.1 | 15.9 |
| true_oversaturated | fixed_8 | 485.653 | 770.726 | 2614.3 | 1550.4 | 163.0 | 489.0 | 1007.2 |
| true_oversaturated | queue_based | 451.880 | 717.825 | 2824.7 | 1445.2 | 142.4 | 427.1 | 947.9 |
| true_oversaturated | queue_based_empty_gap_0s | 362.756 | 573.887 | 3419.1 | 1148.0 | 40.9 | 122.6 | 753.8 |
| true_oversaturated | queue_based_empty_gap_1s | 362.756 | 573.887 | 3419.1 | 1148.0 | 40.9 | 122.6 | 753.8 |
| true_oversaturated | queue_based_empty_gap_3s | 362.756 | 573.887 | 3419.1 | 1148.0 | 40.9 | 122.6 | 753.8 |
| true_oversaturated | queue_based_improved | 362.756 | 573.887 | 3419.1 | 1148.0 | 40.9 | 122.6 | 753.8 |
| true_oversaturated | queue_based_legacy | 451.880 | 717.825 | 2824.7 | 1445.2 | 142.4 | 427.1 | 947.9 |
| true_oversaturated | vehicle_actuated | 358.702 | 569.145 | 3429.7 | 1142.7 | 37.6 | 112.7 | 754.2 |

## Парные contrasts по ожиданию

| Сценарий | Candidate | Comparator | Δ, с | Относительно, % | 95% CI, с | sign p | Holm p |
|---|---|---|---:|---:|---:|---:|---:|
| asymmetric_ew | queue_based_empty_gap_0s | queue_based_improved | 0.252 | 3.92 | [0.131, 0.372] | 0.01612 | 0.14512 |
| asymmetric_ew | queue_based_empty_gap_0s | queue_based_legacy | -0.001 | -0.02 | [-0.003, 0.001] | 1.00000 | 1.00000 |
| asymmetric_ew | queue_based_empty_gap_0s | vehicle_actuated | 0.073 | 1.11 | [-0.047, 0.193] | 0.20049 | 1.00000 |
| asymmetric_ew | queue_based_empty_gap_1s | queue_based_improved | 0.252 | 3.92 | [0.131, 0.372] | 0.01612 | 0.14512 |
| asymmetric_ew | queue_based_empty_gap_1s | queue_based_legacy | -0.001 | -0.02 | [-0.003, 0.001] | 1.00000 | 1.00000 |
| asymmetric_ew | queue_based_empty_gap_1s | vehicle_actuated | 0.073 | 1.11 | [-0.047, 0.193] | 0.20049 | 1.00000 |
| asymmetric_ew | queue_based_empty_gap_3s | queue_based_improved | 0.226 | 3.52 | [0.094, 0.358] | 0.09874 | 0.69116 |
| asymmetric_ew | queue_based_empty_gap_3s | queue_based_legacy | -0.027 | -0.41 | [-0.110, 0.056] | 1.00000 | 1.00000 |
| asymmetric_ew | queue_based_empty_gap_3s | vehicle_actuated | 0.047 | 0.72 | [-0.079, 0.174] | 0.85554 | 1.00000 |
| asymmetric_ns | queue_based_empty_gap_0s | queue_based_improved | 0.258 | 4.05 | [0.114, 0.402] | 0.09874 | 0.78990 |
| asymmetric_ns | queue_based_empty_gap_0s | queue_based_legacy | -0.007 | -0.10 | [-0.022, 0.009] | 1.00000 | 1.00000 |
| asymmetric_ns | queue_based_empty_gap_0s | vehicle_actuated | 0.030 | 0.45 | [-0.083, 0.143] | 0.85554 | 1.00000 |
| asymmetric_ns | queue_based_empty_gap_1s | queue_based_improved | 0.258 | 4.05 | [0.114, 0.402] | 0.09874 | 0.78990 |
| asymmetric_ns | queue_based_empty_gap_1s | queue_based_legacy | -0.007 | -0.10 | [-0.022, 0.009] | 1.00000 | 1.00000 |
| asymmetric_ns | queue_based_empty_gap_1s | vehicle_actuated | 0.030 | 0.45 | [-0.083, 0.143] | 0.85554 | 1.00000 |
| asymmetric_ns | queue_based_empty_gap_3s | queue_based_improved | 0.265 | 4.15 | [0.133, 0.396] | 0.00522 | 0.04701 |
| asymmetric_ns | queue_based_empty_gap_3s | queue_based_legacy | -0.000 | -0.00 | [-0.087, 0.087] | 0.58466 | 1.00000 |
| asymmetric_ns | queue_based_empty_gap_3s | vehicle_actuated | 0.036 | 0.55 | [-0.072, 0.145] | 1.00000 | 1.00000 |
| high_load | queue_based_empty_gap_0s | queue_based_improved | 0.000 | 0.00 | [0.000, 0.000] | 1.00000 | 1.00000 |
| high_load | queue_based_empty_gap_0s | queue_based_legacy | -115.759 | -37.27 | [-117.887, -113.632] | 0.00000 | 0.00000 |
| high_load | queue_based_empty_gap_0s | vehicle_actuated | 9.964 | 5.39 | [8.808, 11.119] | 0.00000 | 0.00000 |
| high_load | queue_based_empty_gap_1s | queue_based_improved | 0.000 | 0.00 | [0.000, 0.000] | 1.00000 | 1.00000 |
| high_load | queue_based_empty_gap_1s | queue_based_legacy | -115.759 | -37.27 | [-117.887, -113.632] | 0.00000 | 0.00000 |
| high_load | queue_based_empty_gap_1s | vehicle_actuated | 9.964 | 5.39 | [8.808, 11.119] | 0.00000 | 0.00000 |
| high_load | queue_based_empty_gap_3s | queue_based_improved | 0.000 | 0.00 | [0.000, 0.000] | 1.00000 | 1.00000 |
| high_load | queue_based_empty_gap_3s | queue_based_legacy | -115.759 | -37.27 | [-117.887, -113.632] | 0.00000 | 0.00000 |
| high_load | queue_based_empty_gap_3s | vehicle_actuated | 9.964 | 5.39 | [8.808, 11.119] | 0.00000 | 0.00000 |
| sudden_dominance_switch | queue_based_empty_gap_0s | queue_based_improved | 0.297 | 4.63 | [0.171, 0.424] | 0.01612 | 0.12900 |
| sudden_dominance_switch | queue_based_empty_gap_0s | queue_based_legacy | -0.008 | -0.12 | [-0.023, 0.006] | 0.50000 | 1.00000 |
| sudden_dominance_switch | queue_based_empty_gap_0s | vehicle_actuated | 0.136 | 2.07 | [0.021, 0.251] | 0.09874 | 0.49369 |
| sudden_dominance_switch | queue_based_empty_gap_1s | queue_based_improved | 0.297 | 4.63 | [0.171, 0.424] | 0.01612 | 0.12900 |
| sudden_dominance_switch | queue_based_empty_gap_1s | queue_based_legacy | -0.008 | -0.12 | [-0.023, 0.006] | 0.50000 | 1.00000 |
| sudden_dominance_switch | queue_based_empty_gap_1s | vehicle_actuated | 0.136 | 2.07 | [0.021, 0.251] | 0.09874 | 0.49369 |
| sudden_dominance_switch | queue_based_empty_gap_3s | queue_based_improved | 0.217 | 3.38 | [0.094, 0.340] | 0.01612 | 0.12900 |
| sudden_dominance_switch | queue_based_empty_gap_3s | queue_based_legacy | -0.088 | -1.31 | [-0.164, -0.012] | 0.00522 | 0.04701 |
| sudden_dominance_switch | queue_based_empty_gap_3s | vehicle_actuated | 0.056 | 0.85 | [-0.051, 0.162] | 0.36159 | 1.00000 |
| symmetric | queue_based_empty_gap_0s | queue_based_improved | -0.080 | -1.32 | [-0.210, 0.050] | 0.36159 | 1.00000 |
| symmetric | queue_based_empty_gap_0s | queue_based_legacy | 0.000 | 0.00 | [0.000, 0.000] | 1.00000 | 1.00000 |
| symmetric | queue_based_empty_gap_0s | vehicle_actuated | -0.049 | -0.82 | [-0.149, 0.051] | 0.58466 | 1.00000 |
| symmetric | queue_based_empty_gap_1s | queue_based_improved | -0.080 | -1.32 | [-0.210, 0.050] | 0.36159 | 1.00000 |
| symmetric | queue_based_empty_gap_1s | queue_based_legacy | 0.000 | 0.00 | [0.000, 0.000] | 1.00000 | 1.00000 |
| symmetric | queue_based_empty_gap_1s | vehicle_actuated | -0.049 | -0.82 | [-0.149, 0.051] | 0.58466 | 1.00000 |
| symmetric | queue_based_empty_gap_3s | queue_based_improved | -0.075 | -1.24 | [-0.209, 0.059] | 0.58466 | 1.00000 |
| symmetric | queue_based_empty_gap_3s | queue_based_legacy | 0.005 | 0.08 | [-0.060, 0.070] | 1.00000 | 1.00000 |
| symmetric | queue_based_empty_gap_3s | vehicle_actuated | -0.044 | -0.74 | [-0.144, 0.056] | 0.58466 | 1.00000 |
| symmetric_9 | queue_based_empty_gap_0s | queue_based_improved | 0.083 | 0.86 | [-0.078, 0.244] | 0.36159 | 0.72319 |
| symmetric_9 | queue_based_empty_gap_0s | queue_based_legacy | -0.243 | -2.43 | [-0.402, -0.085] | 0.00408 | 0.03262 |
| symmetric_9 | queue_based_empty_gap_0s | vehicle_actuated | 0.628 | 6.86 | [0.378, 0.879] | 0.00522 | 0.03262 |
| symmetric_9 | queue_based_empty_gap_1s | queue_based_improved | 0.083 | 0.86 | [-0.078, 0.244] | 0.36159 | 0.72319 |
| symmetric_9 | queue_based_empty_gap_1s | queue_based_legacy | -0.243 | -2.43 | [-0.402, -0.085] | 0.00408 | 0.03262 |
| symmetric_9 | queue_based_empty_gap_1s | vehicle_actuated | 0.628 | 6.86 | [0.378, 0.879] | 0.00522 | 0.03262 |
| symmetric_9 | queue_based_empty_gap_3s | queue_based_improved | 0.078 | 0.81 | [-0.064, 0.220] | 0.09874 | 0.39495 |
| symmetric_9 | queue_based_empty_gap_3s | queue_based_legacy | -0.248 | -2.47 | [-0.433, -0.064] | 0.09874 | 0.39495 |
| symmetric_9 | queue_based_empty_gap_3s | vehicle_actuated | 0.623 | 6.80 | [0.407, 0.840] | 0.00006 | 0.00054 |
| symmetric_low | queue_based_empty_gap_0s | queue_based_improved | -1.007 | -19.11 | [-1.165, -0.848] | 0.00000 | 0.00000 |
| symmetric_low | queue_based_empty_gap_0s | queue_based_legacy | 0.000 | 0.00 | [0.000, 0.000] | 1.00000 | 1.00000 |
| symmetric_low | queue_based_empty_gap_0s | vehicle_actuated | -0.009 | -0.22 | [-0.051, 0.032] | 0.36159 | 1.00000 |
| symmetric_low | queue_based_empty_gap_1s | queue_based_improved | -1.007 | -19.11 | [-1.165, -0.848] | 0.00000 | 0.00000 |
| symmetric_low | queue_based_empty_gap_1s | queue_based_legacy | 0.000 | 0.00 | [0.000, 0.000] | 1.00000 | 1.00000 |
| symmetric_low | queue_based_empty_gap_1s | vehicle_actuated | -0.009 | -0.22 | [-0.051, 0.032] | 0.36159 | 1.00000 |
| symmetric_low | queue_based_empty_gap_3s | queue_based_improved | -1.012 | -19.22 | [-1.162, -0.862] | 0.00000 | 0.00000 |
| symmetric_low | queue_based_empty_gap_3s | queue_based_legacy | -0.006 | -0.13 | [-0.031, 0.019] | 0.34493 | 1.00000 |
| symmetric_low | queue_based_empty_gap_3s | vehicle_actuated | -0.015 | -0.35 | [-0.041, 0.011] | 0.13605 | 0.81628 |
| true_oversaturated | queue_based_empty_gap_0s | queue_based_improved | 0.000 | 0.00 | [0.000, 0.000] | 1.00000 | 1.00000 |
| true_oversaturated | queue_based_empty_gap_0s | queue_based_legacy | -89.124 | -19.72 | [-91.278, -86.971] | 0.00000 | 0.00000 |
| true_oversaturated | queue_based_empty_gap_0s | vehicle_actuated | 4.054 | 1.13 | [3.057, 5.050] | 0.00001 | 0.00005 |
| true_oversaturated | queue_based_empty_gap_1s | queue_based_improved | 0.000 | 0.00 | [0.000, 0.000] | 1.00000 | 1.00000 |
| true_oversaturated | queue_based_empty_gap_1s | queue_based_legacy | -89.124 | -19.72 | [-91.278, -86.971] | 0.00000 | 0.00000 |
| true_oversaturated | queue_based_empty_gap_1s | vehicle_actuated | 4.054 | 1.13 | [3.057, 5.050] | 0.00001 | 0.00005 |
| true_oversaturated | queue_based_empty_gap_3s | queue_based_improved | 0.000 | 0.00 | [0.000, 0.000] | 1.00000 | 1.00000 |
| true_oversaturated | queue_based_empty_gap_3s | queue_based_legacy | -89.124 | -19.72 | [-91.278, -86.971] | 0.00000 | 0.00000 |
| true_oversaturated | queue_based_empty_gap_3s | vehicle_actuated | 4.054 | 1.13 | [3.057, 5.050] | 0.00001 | 0.00005 |
