# Управление с датчиком подъезда: Независимая проверка (validation)

Seed: 30, сценариев: 8, горизонт 1800 с. Настроенный Vehicle-actuated: `va_min1_gap0`; настроенный Improved (margin 0,20): `imp20_min1`. Выбор — по минимуму среднего ожидания в шести сценариях ниже пропускной способности, объявлен до анализа.

Δ — среднее парное различие «кандидат − компаратор» в секундах (отрицательное — кандидат лучше); Holm применён ко всей таблице контрастов.

## Среднее ожидание завершивших обслуживание, с

| Сценарий | imp20_min1 | preview_degraded10_min2 | preview_ideal10_min2 | preview_none_min2 | va_min1_gap0 | va_min8_gap3 |
|---|---:|---:|---:|---:|---:|---:|
| asymmetric_ew | 5.20 | 4.20 | 3.65 | 4.60 | 4.40 | 6.63 |
| asymmetric_ns | 5.21 | 4.20 | 3.63 | 4.63 | 4.41 | 6.54 |
| sudden_dominance_switch | 5.24 | 4.21 | 3.67 | 4.63 | 4.44 | 6.58 |
| symmetric | 5.16 | 3.96 | 3.00 | 4.37 | 4.23 | 6.01 |
| symmetric_9 | 8.77 | 6.67 | 5.91 | 7.14 | 7.16 | 9.26 |
| symmetric_low | 4.97 | 2.18 | 1.35 | 2.86 | 2.71 | 4.39 |
| high_load | 193.36 | 185.69 | 185.22 | 186.11 | 188.78 | 190.31 |
| true_oversaturated | 363.30 | 360.16 | 359.93 | 360.39 | 361.77 | 362.52 |

## Парные контрасты по ожиданию

| Сценарий | Кандидат | Компаратор | Δ, с | Δ, % | 95% CI | Holm p |
|---|---|---|---:|---:|---:|---:|
| asymmetric_ew | preview_degraded10_min2 | va_min1_gap0 | -0.193 | -4.4 | [-0.267; -0.118] | 0.0032 |
| asymmetric_ew | preview_degraded10_min2 | va_min8_gap3 | -2.430 | -36.6 | [-2.556; -2.304] | <0.0001 |
| asymmetric_ew | preview_degraded10_min2 | imp20_min1 | -0.996 | -19.2 | [-1.078; -0.915] | <0.0001 |
| asymmetric_ew | preview_ideal10_min2 | va_min1_gap0 | -0.750 | -17.1 | [-0.842; -0.659] | <0.0001 |
| asymmetric_ew | preview_ideal10_min2 | va_min8_gap3 | -2.988 | -45.0 | [-3.107; -2.869] | <0.0001 |
| asymmetric_ew | preview_ideal10_min2 | imp20_min1 | -1.554 | -29.9 | [-1.643; -1.465] | <0.0001 |
| asymmetric_ew | preview_none_min2 | va_min1_gap0 | 0.205 | 4.7 | [0.165; 0.246] | <0.0001 |
| asymmetric_ew | preview_none_min2 | va_min8_gap3 | -2.033 | -30.6 | [-2.160; -1.905] | <0.0001 |
| asymmetric_ew | preview_none_min2 | imp20_min1 | -0.599 | -11.5 | [-0.663; -0.534] | <0.0001 |
| asymmetric_ew | va_min1_gap0 | va_min8_gap3 | -2.238 | -33.7 | [-2.364; -2.112] | <0.0001 |
| asymmetric_ew | imp20_min1 | va_min1_gap0 | 0.804 | 18.3 | [0.741; 0.866] | <0.0001 |
| asymmetric_ns | preview_degraded10_min2 | va_min1_gap0 | -0.207 | -4.7 | [-0.285; -0.130] | 0.0086 |
| asymmetric_ns | preview_degraded10_min2 | va_min8_gap3 | -2.333 | -35.7 | [-2.442; -2.224] | <0.0001 |
| asymmetric_ns | preview_degraded10_min2 | imp20_min1 | -1.003 | -19.3 | [-1.086; -0.919] | <0.0001 |
| asymmetric_ns | preview_ideal10_min2 | va_min1_gap0 | -0.783 | -17.8 | [-0.864; -0.702] | <0.0001 |
| asymmetric_ns | preview_ideal10_min2 | va_min8_gap3 | -2.909 | -44.5 | [-3.017; -2.800] | <0.0001 |
| asymmetric_ns | preview_ideal10_min2 | imp20_min1 | -1.578 | -30.3 | [-1.672; -1.485] | <0.0001 |
| asymmetric_ns | preview_none_min2 | va_min1_gap0 | 0.218 | 4.9 | [0.175; 0.261] | <0.0001 |
| asymmetric_ns | preview_none_min2 | va_min8_gap3 | -1.908 | -29.2 | [-2.021; -1.796] | <0.0001 |
| asymmetric_ns | preview_none_min2 | imp20_min1 | -0.578 | -11.1 | [-0.643; -0.512] | <0.0001 |
| asymmetric_ns | va_min1_gap0 | va_min8_gap3 | -2.126 | -32.5 | [-2.228; -2.024] | <0.0001 |
| asymmetric_ns | imp20_min1 | va_min1_gap0 | 0.795 | 18.0 | [0.727; 0.863] | <0.0001 |
| sudden_dominance_switch | preview_degraded10_min2 | va_min1_gap0 | -0.236 | -5.3 | [-0.324; -0.149] | 0.0032 |
| sudden_dominance_switch | preview_degraded10_min2 | va_min8_gap3 | -2.370 | -36.0 | [-2.488; -2.252] | <0.0001 |
| sudden_dominance_switch | preview_degraded10_min2 | imp20_min1 | -1.036 | -19.8 | [-1.141; -0.931] | <0.0001 |
| sudden_dominance_switch | preview_ideal10_min2 | va_min1_gap0 | -0.774 | -17.4 | [-0.850; -0.697] | <0.0001 |
| sudden_dominance_switch | preview_ideal10_min2 | va_min8_gap3 | -2.907 | -44.2 | [-3.010; -2.805] | <0.0001 |
| sudden_dominance_switch | preview_ideal10_min2 | imp20_min1 | -1.573 | -30.0 | [-1.664; -1.482] | <0.0001 |
| sudden_dominance_switch | preview_none_min2 | va_min1_gap0 | 0.188 | 4.2 | [0.143; 0.232] | <0.0001 |
| sudden_dominance_switch | preview_none_min2 | va_min8_gap3 | -1.946 | -29.6 | [-2.045; -1.847] | <0.0001 |
| sudden_dominance_switch | preview_none_min2 | imp20_min1 | -0.612 | -11.7 | [-0.694; -0.529] | <0.0001 |
| sudden_dominance_switch | va_min1_gap0 | va_min8_gap3 | -2.134 | -32.4 | [-2.237; -2.031] | <0.0001 |
| sudden_dominance_switch | imp20_min1 | va_min1_gap0 | 0.799 | 18.0 | [0.718; 0.881] | <0.0001 |
| symmetric | preview_degraded10_min2 | va_min1_gap0 | -0.269 | -6.4 | [-0.344; -0.194] | 0.0008 |
| symmetric | preview_degraded10_min2 | va_min8_gap3 | -2.050 | -34.1 | [-2.175; -1.925] | <0.0001 |
| symmetric | preview_degraded10_min2 | imp20_min1 | -1.202 | -23.3 | [-1.325; -1.078] | <0.0001 |
| symmetric | preview_ideal10_min2 | va_min1_gap0 | -1.229 | -29.1 | [-1.279; -1.179] | <0.0001 |
| symmetric | preview_ideal10_min2 | va_min8_gap3 | -3.010 | -50.1 | [-3.105; -2.915] | <0.0001 |
| symmetric | preview_ideal10_min2 | imp20_min1 | -2.162 | -41.9 | [-2.252; -2.072] | <0.0001 |
| symmetric | preview_none_min2 | va_min1_gap0 | 0.148 | 3.5 | [0.100; 0.197] | 0.0008 |
| symmetric | preview_none_min2 | va_min8_gap3 | -1.633 | -27.2 | [-1.735; -1.531] | <0.0001 |
| symmetric | preview_none_min2 | imp20_min1 | -0.785 | -15.2 | [-0.875; -0.695] | <0.0001 |
| symmetric | va_min1_gap0 | va_min8_gap3 | -1.781 | -29.6 | [-1.889; -1.673] | <0.0001 |
| symmetric | imp20_min1 | va_min1_gap0 | 0.933 | 22.1 | [0.848; 1.018] | <0.0001 |
| symmetric_9 | preview_degraded10_min2 | va_min1_gap0 | -0.487 | -6.8 | [-0.637; -0.338] | 0.0032 |
| symmetric_9 | preview_degraded10_min2 | va_min8_gap3 | -2.584 | -27.9 | [-2.747; -2.421] | <0.0001 |
| symmetric_9 | preview_degraded10_min2 | imp20_min1 | -2.098 | -23.9 | [-2.271; -1.926] | <0.0001 |
| symmetric_9 | preview_ideal10_min2 | va_min1_gap0 | -1.251 | -17.5 | [-1.398; -1.104] | <0.0001 |
| symmetric_9 | preview_ideal10_min2 | va_min8_gap3 | -3.348 | -36.2 | [-3.528; -3.168] | <0.0001 |
| symmetric_9 | preview_ideal10_min2 | imp20_min1 | -2.862 | -32.6 | [-3.039; -2.685] | <0.0001 |
| symmetric_9 | preview_none_min2 | va_min1_gap0 | -0.015 | -0.2 | [-0.130; 0.100] | 1.0000 |
| symmetric_9 | preview_none_min2 | va_min8_gap3 | -2.112 | -22.8 | [-2.285; -1.938] | <0.0001 |
| symmetric_9 | preview_none_min2 | imp20_min1 | -1.626 | -18.5 | [-1.811; -1.440] | <0.0001 |
| symmetric_9 | va_min1_gap0 | va_min8_gap3 | -2.097 | -22.7 | [-2.246; -1.948] | <0.0001 |
| symmetric_9 | imp20_min1 | va_min1_gap0 | 1.611 | 22.5 | [1.421; 1.801] | <0.0001 |
| symmetric_low | preview_degraded10_min2 | va_min1_gap0 | -0.530 | -19.5 | [-0.612; -0.447] | <0.0001 |
| symmetric_low | preview_degraded10_min2 | va_min8_gap3 | -2.206 | -50.3 | [-2.335; -2.077] | <0.0001 |
| symmetric_low | preview_degraded10_min2 | imp20_min1 | -2.784 | -56.1 | [-2.887; -2.680] | <0.0001 |
| symmetric_low | preview_ideal10_min2 | va_min1_gap0 | -1.359 | -50.1 | [-1.413; -1.305] | <0.0001 |
| symmetric_low | preview_ideal10_min2 | va_min8_gap3 | -3.036 | -69.2 | [-3.163; -2.908] | <0.0001 |
| symmetric_low | preview_ideal10_min2 | imp20_min1 | -3.613 | -72.8 | [-3.711; -3.515] | <0.0001 |
| symmetric_low | preview_none_min2 | va_min1_gap0 | 0.148 | 5.5 | [0.119; 0.177] | <0.0001 |
| symmetric_low | preview_none_min2 | va_min8_gap3 | -1.529 | -34.8 | [-1.644; -1.413] | <0.0001 |
| symmetric_low | preview_none_min2 | imp20_min1 | -2.107 | -42.4 | [-2.199; -2.014] | <0.0001 |
| symmetric_low | va_min1_gap0 | va_min8_gap3 | -1.677 | -38.2 | [-1.789; -1.565] | <0.0001 |
| symmetric_low | imp20_min1 | va_min1_gap0 | 2.254 | 83.1 | [2.165; 2.343] | <0.0001 |
| high_load | preview_degraded10_min2 | va_min1_gap0 | -3.092 | -1.6 | [-4.055; -2.130] | <0.0001 |
| high_load | preview_degraded10_min2 | va_min8_gap3 | -4.619 | -2.4 | [-5.498; -3.740] | <0.0001 |
| high_load | preview_degraded10_min2 | imp20_min1 | -7.664 | -4.0 | [-8.523; -6.805] | <0.0001 |
| high_load | preview_ideal10_min2 | va_min1_gap0 | -3.565 | -1.9 | [-4.599; -2.531] | 0.0008 |
| high_load | preview_ideal10_min2 | va_min8_gap3 | -5.092 | -2.7 | [-6.037; -4.146] | <0.0001 |
| high_load | preview_ideal10_min2 | imp20_min1 | -8.136 | -4.2 | [-9.210; -7.063] | <0.0001 |
| high_load | preview_none_min2 | va_min1_gap0 | -2.673 | -1.4 | [-3.542; -1.804] | 0.0001 |
| high_load | preview_none_min2 | va_min8_gap3 | -4.200 | -2.2 | [-5.251; -3.150] | <0.0001 |
| high_load | preview_none_min2 | imp20_min1 | -7.245 | -3.7 | [-8.074; -6.416] | <0.0001 |
| high_load | va_min1_gap0 | va_min8_gap3 | -1.527 | -0.8 | [-2.529; -0.525] | 0.2962 |
| high_load | imp20_min1 | va_min1_gap0 | 4.572 | 2.4 | [3.544; 5.599] | <0.0001 |
| true_oversaturated | preview_degraded10_min2 | va_min1_gap0 | -1.609 | -0.4 | [-2.266; -0.951] | 0.0038 |
| true_oversaturated | preview_degraded10_min2 | va_min8_gap3 | -2.362 | -0.7 | [-2.954; -1.769] | <0.0001 |
| true_oversaturated | preview_degraded10_min2 | imp20_min1 | -3.147 | -0.9 | [-3.794; -2.501] | <0.0001 |
| true_oversaturated | preview_ideal10_min2 | va_min1_gap0 | -1.834 | -0.5 | [-2.443; -1.225] | 0.0002 |
| true_oversaturated | preview_ideal10_min2 | va_min8_gap3 | -2.587 | -0.7 | [-3.290; -1.885] | 0.0002 |
| true_oversaturated | preview_ideal10_min2 | imp20_min1 | -3.373 | -0.9 | [-4.034; -2.712] | <0.0001 |
| true_oversaturated | preview_none_min2 | va_min1_gap0 | -1.373 | -0.4 | [-1.958; -0.787] | 0.0209 |
| true_oversaturated | preview_none_min2 | va_min8_gap3 | -2.126 | -0.6 | [-2.905; -1.347] | 0.0001 |
| true_oversaturated | preview_none_min2 | imp20_min1 | -2.911 | -0.8 | [-3.467; -2.356] | <0.0001 |
| true_oversaturated | va_min1_gap0 | va_min8_gap3 | -0.753 | -0.2 | [-1.552; 0.045] | 0.2962 |
| true_oversaturated | imp20_min1 | va_min1_gap0 | 1.539 | 0.4 | [0.601; 2.477] | 0.0086 |

## Переключения и справедливость (среднее по seed)

| Сценарий | Контроллер | Переключений за 1800 с | Макс. красный при очереди, с | Остаток в очереди | Throughput, авто/ч |
|---|---|---:|---:|---:|---:|
| asymmetric_ew | imp20_min1 | 157.4 | 37.0 | 2.8 | 1666 |
| asymmetric_ew | preview_degraded10_min2 | 139.5 | 38.5 | 2.3 | 1667 |
| asymmetric_ew | preview_ideal10_min2 | 120.1 | 40.3 | 1.6 | 1668 |
| asymmetric_ew | preview_none_min2 | 195.2 | 24.4 | 2.4 | 1667 |
| asymmetric_ew | va_min1_gap0 | 204.6 | 24.2 | 2.2 | 1667 |
| asymmetric_ew | va_min8_gap3 | 126.3 | 32.4 | 3.2 | 1665 |
| asymmetric_ns | imp20_min1 | 157.6 | 37.4 | 3.3 | 1659 |
| asymmetric_ns | preview_degraded10_min2 | 139.3 | 36.8 | 2.7 | 1660 |
| asymmetric_ns | preview_ideal10_min2 | 119.1 | 39.8 | 2.3 | 1661 |
| asymmetric_ns | preview_none_min2 | 195.5 | 23.9 | 3.6 | 1659 |
| asymmetric_ns | va_min1_gap0 | 206.3 | 23.9 | 3.2 | 1659 |
| asymmetric_ns | va_min8_gap3 | 126.1 | 31.2 | 4.2 | 1657 |
| sudden_dominance_switch | imp20_min1 | 157.7 | 37.3 | 3.3 | 1664 |
| sudden_dominance_switch | preview_degraded10_min2 | 139.1 | 37.7 | 2.2 | 1667 |
| sudden_dominance_switch | preview_ideal10_min2 | 120.7 | 40.3 | 2.0 | 1667 |
| sudden_dominance_switch | preview_none_min2 | 194.9 | 25.1 | 2.6 | 1666 |
| sudden_dominance_switch | va_min1_gap0 | 205.3 | 24.2 | 2.7 | 1666 |
| sudden_dominance_switch | va_min8_gap3 | 125.2 | 32.7 | 3.6 | 1664 |
| symmetric | imp20_min1 | 164.0 | 31.1 | 2.1 | 1424 |
| symmetric | preview_degraded10_min2 | 166.4 | 26.6 | 1.7 | 1425 |
| symmetric | preview_ideal10_min2 | 144.6 | 27.3 | 1.3 | 1425 |
| symmetric | preview_none_min2 | 219.4 | 17.6 | 1.9 | 1424 |
| symmetric | va_min1_gap0 | 229.1 | 17.1 | 1.8 | 1425 |
| symmetric | va_min8_gap3 | 142.6 | 21.9 | 2.5 | 1423 |
| symmetric_9 | imp20_min1 | 191.4 | 25.3 | 5.5 | 2137 |
| symmetric_9 | preview_degraded10_min2 | 147.4 | 28.9 | 4.3 | 2139 |
| symmetric_9 | preview_ideal10_min2 | 136.1 | 31.1 | 4.0 | 2140 |
| symmetric_9 | preview_none_min2 | 176.3 | 26.7 | 4.8 | 2139 |
| symmetric_9 | va_min1_gap0 | 179.3 | 31.4 | 4.8 | 2139 |
| symmetric_9 | va_min8_gap3 | 108.5 | 37.4 | 5.5 | 2136 |
| symmetric_low | imp20_min1 | 90.0 | 42.9 | 1.1 | 711 |
| symmetric_low | preview_degraded10_min2 | 138.8 | 18.8 | 0.6 | 712 |
| symmetric_low | preview_ideal10_min2 | 121.1 | 19.7 | 0.4 | 713 |
| symmetric_low | preview_none_min2 | 155.3 | 9.0 | 0.7 | 712 |
| symmetric_low | va_min1_gap0 | 158.5 | 8.8 | 0.8 | 712 |
| symmetric_low | va_min8_gap3 | 124.0 | 14.0 | 1.0 | 712 |
| high_load | imp20_min1 | 43.1 | 48.0 | 442.0 | 3405 |
| high_load | preview_degraded10_min2 | 39.7 | 48.0 | 432.7 | 3424 |
| high_load | preview_ideal10_min2 | 39.3 | 48.0 | 432.2 | 3425 |
| high_load | preview_none_min2 | 41.1 | 48.0 | 433.2 | 3423 |
| high_load | va_min1_gap0 | 39.0 | 48.0 | 436.5 | 3416 |
| high_load | va_min8_gap3 | 38.0 | 48.0 | 437.7 | 3414 |
| true_oversaturated | imp20_min1 | 39.8 | 48.0 | 1159.4 | 3428 |
| true_oversaturated | preview_degraded10_min2 | 38.5 | 48.0 | 1155.6 | 3436 |
| true_oversaturated | preview_ideal10_min2 | 38.2 | 48.0 | 1155.6 | 3436 |
| true_oversaturated | preview_none_min2 | 38.9 | 48.0 | 1155.5 | 3436 |
| true_oversaturated | va_min1_gap0 | 38.3 | 48.0 | 1157.6 | 3432 |
| true_oversaturated | va_min8_gap3 | 37.8 | 48.0 | 1158.6 | 3430 |
