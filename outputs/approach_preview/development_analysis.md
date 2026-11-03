# Управление с датчиком подъезда: Development

Seed: 30, сценариев: 8, горизонт 1800 с. Настроенный Vehicle-actuated: `va_min1_gap0`; настроенный Improved (margin 0,20): `imp20_min1`. Выбор — по минимуму среднего ожидания в шести сценариях ниже пропускной способности, объявлен до анализа.

Δ — среднее парное различие «кандидат − компаратор» в секундах (отрицательное — кандидат лучше); Holm применён ко всей таблице контрастов.

## Среднее ожидание завершивших обслуживание, с

| Сценарий | imp20_min1 | imp20_min2 | imp20_min4 | imp20_min8 | preview_degraded10 | preview_degraded10_min2 | preview_ideal10 | preview_ideal10_min2 | preview_ideal5 | preview_none | va_min1_gap0 | va_min1_gap0.5 | va_min1_gap1 | va_min2_gap0 | va_min2_gap0.5 | va_min2_gap1 | va_min2_gap2 | va_min4_gap1 | va_min4_gap2 | va_min6_gap1 | va_min6_gap2 | va_min8_gap3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| asymmetric_ew | 5.16 | 5.28 | 5.41 | 6.42 | 4.29 | 4.16 | 3.75 | 3.65 | 3.71 | 5.07 | 4.37 | 4.37 | 4.37 | 4.56 | 4.56 | 4.56 | 5.00 | 5.07 | 5.29 | 5.68 | 5.83 | 6.57 |
| asymmetric_ns | 5.22 | 5.37 | 5.51 | 6.28 | 4.34 | 4.17 | 3.74 | 3.64 | 3.74 | 5.05 | 4.43 | 4.43 | 4.43 | 4.66 | 4.66 | 4.66 | 5.10 | 5.06 | 5.34 | 5.67 | 5.91 | 6.63 |
| sudden_dominance_switch | 5.20 | 5.32 | 5.49 | 6.28 | 4.34 | 4.17 | 3.73 | 3.61 | 3.76 | 5.01 | 4.38 | 4.38 | 4.38 | 4.61 | 4.61 | 4.61 | 5.07 | 5.02 | 5.35 | 5.67 | 5.88 | 6.59 |
| symmetric | 5.16 | 5.23 | 5.37 | 5.96 | 4.08 | 3.96 | 3.17 | 3.04 | 3.27 | 4.72 | 4.23 | 4.23 | 4.23 | 4.38 | 4.38 | 4.38 | 4.80 | 4.72 | 5.02 | 5.25 | 5.40 | 6.01 |
| symmetric_9 | 8.62 | 8.75 | 8.92 | 9.41 | 6.67 | 6.61 | 5.88 | 5.83 | 6.13 | 7.22 | 7.09 | 7.09 | 7.09 | 7.16 | 7.16 | 7.16 | 8.11 | 7.25 | 8.12 | 7.49 | 8.29 | 9.18 |
| symmetric_low | 4.85 | 4.87 | 4.95 | 5.29 | 2.42 | 2.24 | 1.51 | 1.36 | 1.55 | 3.23 | 2.72 | 2.72 | 2.72 | 2.87 | 2.87 | 2.87 | 2.98 | 3.23 | 3.26 | 3.70 | 3.73 | 4.36 |
| high_load | 193.79 | 193.67 | 193.73 | 193.65 | 186.33 | 186.23 | 185.79 | 185.70 | 185.76 | 186.58 | 189.67 | 189.67 | 189.67 | 189.71 | 189.71 | 189.71 | 190.07 | 189.61 | 190.40 | 189.42 | 190.09 | 190.23 |
| true_oversaturated | 363.52 | 363.63 | 363.84 | 363.43 | 360.59 | 360.49 | 360.77 | 360.53 | 360.63 | 361.07 | 362.61 | 362.61 | 362.61 | 362.78 | 362.78 | 362.78 | 363.03 | 362.55 | 363.06 | 362.72 | 363.10 | 363.23 |

## Парные контрасты по ожиданию

| Сценарий | Кандидат | Компаратор | Δ, с | Δ, % | 95% CI | Holm p |
|---|---|---|---:|---:|---:|---:|
| asymmetric_ew | preview_degraded10 | va_min1_gap0 | -0.082 | -1.9 | [-0.168; 0.003] | 1.0000 |
| asymmetric_ew | preview_degraded10 | va_min8_gap3 | -2.283 | -34.7 | [-2.382; -2.184] | <0.0001 |
| asymmetric_ew | preview_degraded10 | imp20_min1 | -0.871 | -16.9 | [-0.981; -0.762] | <0.0001 |
| asymmetric_ew | preview_degraded10_min2 | va_min1_gap0 | -0.218 | -5.0 | [-0.298; -0.139] | 0.0012 |
| asymmetric_ew | preview_degraded10_min2 | va_min8_gap3 | -2.420 | -36.8 | [-2.518; -2.321] | <0.0001 |
| asymmetric_ew | preview_degraded10_min2 | imp20_min1 | -1.008 | -19.5 | [-1.122; -0.894] | <0.0001 |
| asymmetric_ew | preview_ideal10 | va_min1_gap0 | -0.624 | -14.3 | [-0.700; -0.547] | <0.0001 |
| asymmetric_ew | preview_ideal10 | va_min8_gap3 | -2.825 | -43.0 | [-2.931; -2.718] | <0.0001 |
| asymmetric_ew | preview_ideal10 | imp20_min1 | -1.413 | -27.4 | [-1.521; -1.304] | <0.0001 |
| asymmetric_ew | preview_ideal10_min2 | va_min1_gap0 | -0.728 | -16.6 | [-0.812; -0.644] | <0.0001 |
| asymmetric_ew | preview_ideal10_min2 | va_min8_gap3 | -2.929 | -44.5 | [-3.041; -2.816] | <0.0001 |
| asymmetric_ew | preview_ideal10_min2 | imp20_min1 | -1.517 | -29.4 | [-1.630; -1.404] | <0.0001 |
| asymmetric_ew | preview_ideal5 | va_min1_gap0 | -0.667 | -15.2 | [-0.728; -0.605] | <0.0001 |
| asymmetric_ew | preview_ideal5 | va_min8_gap3 | -2.868 | -43.6 | [-2.969; -2.766] | <0.0001 |
| asymmetric_ew | preview_ideal5 | imp20_min1 | -1.456 | -28.2 | [-1.557; -1.354] | <0.0001 |
| asymmetric_ew | preview_none | va_min1_gap0 | 0.693 | 15.9 | [0.619; 0.768] | <0.0001 |
| asymmetric_ew | preview_none | va_min8_gap3 | -1.508 | -22.9 | [-1.606; -1.409] | <0.0001 |
| asymmetric_ew | preview_none | imp20_min1 | -0.096 | -1.9 | [-0.200; 0.008] | 1.0000 |
| asymmetric_ew | va_min1_gap0 | va_min8_gap3 | -2.201 | -33.5 | [-2.294; -2.109] | <0.0001 |
| asymmetric_ew | imp20_min1 | va_min1_gap0 | 0.789 | 18.0 | [0.694; 0.884] | <0.0001 |
| asymmetric_ns | preview_degraded10 | va_min1_gap0 | -0.091 | -2.1 | [-0.170; -0.011] | 1.0000 |
| asymmetric_ns | preview_degraded10 | va_min8_gap3 | -2.299 | -34.6 | [-2.388; -2.209] | <0.0001 |
| asymmetric_ns | preview_degraded10 | imp20_min1 | -0.883 | -16.9 | [-0.986; -0.780] | <0.0001 |
| asymmetric_ns | preview_degraded10_min2 | va_min1_gap0 | -0.253 | -5.7 | [-0.335; -0.170] | 0.0012 |
| asymmetric_ns | preview_degraded10_min2 | va_min8_gap3 | -2.461 | -37.1 | [-2.565; -2.357] | <0.0001 |
| asymmetric_ns | preview_degraded10_min2 | imp20_min1 | -1.045 | -20.0 | [-1.145; -0.945] | <0.0001 |
| asymmetric_ns | preview_ideal10 | va_min1_gap0 | -0.689 | -15.6 | [-0.767; -0.611] | <0.0001 |
| asymmetric_ns | preview_ideal10 | va_min8_gap3 | -2.897 | -43.7 | [-3.004; -2.789] | <0.0001 |
| asymmetric_ns | preview_ideal10 | imp20_min1 | -1.481 | -28.4 | [-1.587; -1.375] | <0.0001 |
| asymmetric_ns | preview_ideal10_min2 | va_min1_gap0 | -0.787 | -17.8 | [-0.863; -0.711] | <0.0001 |
| asymmetric_ns | preview_ideal10_min2 | va_min8_gap3 | -2.995 | -45.1 | [-3.098; -2.892] | <0.0001 |
| asymmetric_ns | preview_ideal10_min2 | imp20_min1 | -1.579 | -30.3 | [-1.681; -1.477] | <0.0001 |
| asymmetric_ns | preview_ideal5 | va_min1_gap0 | -0.690 | -15.6 | [-0.755; -0.625] | <0.0001 |
| asymmetric_ns | preview_ideal5 | va_min8_gap3 | -2.898 | -43.7 | [-2.983; -2.812] | <0.0001 |
| asymmetric_ns | preview_ideal5 | imp20_min1 | -1.482 | -28.4 | [-1.579; -1.385] | <0.0001 |
| asymmetric_ns | preview_none | va_min1_gap0 | 0.623 | 14.1 | [0.557; 0.689] | <0.0001 |
| asymmetric_ns | preview_none | va_min8_gap3 | -1.585 | -23.9 | [-1.685; -1.485] | <0.0001 |
| asymmetric_ns | preview_none | imp20_min1 | -0.169 | -3.2 | [-0.259; -0.079] | 0.3850 |
| asymmetric_ns | va_min1_gap0 | va_min8_gap3 | -2.208 | -33.3 | [-2.303; -2.113] | <0.0001 |
| asymmetric_ns | imp20_min1 | va_min1_gap0 | 0.792 | 17.9 | [0.701; 0.883] | <0.0001 |
| sudden_dominance_switch | preview_degraded10 | va_min1_gap0 | -0.034 | -0.8 | [-0.124; 0.056] | 1.0000 |
| sudden_dominance_switch | preview_degraded10 | va_min8_gap3 | -2.250 | -34.1 | [-2.367; -2.133] | <0.0001 |
| sudden_dominance_switch | preview_degraded10 | imp20_min1 | -0.855 | -16.4 | [-0.946; -0.764] | <0.0001 |
| sudden_dominance_switch | preview_degraded10_min2 | va_min1_gap0 | -0.208 | -4.7 | [-0.301; -0.115] | 0.0215 |
| sudden_dominance_switch | preview_degraded10_min2 | va_min8_gap3 | -2.424 | -36.8 | [-2.552; -2.295] | <0.0001 |
| sudden_dominance_switch | preview_degraded10_min2 | imp20_min1 | -1.028 | -19.8 | [-1.112; -0.944] | <0.0001 |
| sudden_dominance_switch | preview_ideal10 | va_min1_gap0 | -0.652 | -14.9 | [-0.747; -0.558] | <0.0001 |
| sudden_dominance_switch | preview_ideal10 | va_min8_gap3 | -2.868 | -43.5 | [-2.986; -2.750] | <0.0001 |
| sudden_dominance_switch | preview_ideal10 | imp20_min1 | -1.473 | -28.3 | [-1.565; -1.381] | <0.0001 |
| sudden_dominance_switch | preview_ideal10_min2 | va_min1_gap0 | -0.769 | -17.6 | [-0.863; -0.676] | <0.0001 |
| sudden_dominance_switch | preview_ideal10_min2 | va_min8_gap3 | -2.985 | -45.3 | [-3.110; -2.860] | <0.0001 |
| sudden_dominance_switch | preview_ideal10_min2 | imp20_min1 | -1.590 | -30.6 | [-1.687; -1.493] | <0.0001 |
| sudden_dominance_switch | preview_ideal5 | va_min1_gap0 | -0.614 | -14.0 | [-0.705; -0.524] | <0.0001 |
| sudden_dominance_switch | preview_ideal5 | va_min8_gap3 | -2.830 | -42.9 | [-2.955; -2.705] | <0.0001 |
| sudden_dominance_switch | preview_ideal5 | imp20_min1 | -1.435 | -27.6 | [-1.520; -1.350] | <0.0001 |
| sudden_dominance_switch | preview_none | va_min1_gap0 | 0.635 | 14.5 | [0.585; 0.684] | <0.0001 |
| sudden_dominance_switch | preview_none | va_min8_gap3 | -1.581 | -24.0 | [-1.684; -1.479] | <0.0001 |
| sudden_dominance_switch | preview_none | imp20_min1 | -0.186 | -3.6 | [-0.262; -0.110] | 0.0062 |
| sudden_dominance_switch | va_min1_gap0 | va_min8_gap3 | -2.216 | -33.6 | [-2.319; -2.113] | <0.0001 |
| sudden_dominance_switch | imp20_min1 | va_min1_gap0 | 0.821 | 18.7 | [0.735; 0.906] | <0.0001 |
| symmetric | preview_degraded10 | va_min1_gap0 | -0.152 | -3.6 | [-0.213; -0.092] | 0.0062 |
| symmetric | preview_degraded10 | va_min8_gap3 | -1.931 | -32.1 | [-2.041; -1.822] | <0.0001 |
| symmetric | preview_degraded10 | imp20_min1 | -1.079 | -20.9 | [-1.177; -0.980] | <0.0001 |
| symmetric | preview_degraded10_min2 | va_min1_gap0 | -0.274 | -6.5 | [-0.356; -0.192] | <0.0001 |
| symmetric | preview_degraded10_min2 | va_min8_gap3 | -2.053 | -34.1 | [-2.172; -1.934] | <0.0001 |
| symmetric | preview_degraded10_min2 | imp20_min1 | -1.201 | -23.3 | [-1.297; -1.105] | <0.0001 |
| symmetric | preview_ideal10 | va_min1_gap0 | -1.061 | -25.0 | [-1.124; -0.997] | <0.0001 |
| symmetric | preview_ideal10 | va_min8_gap3 | -2.840 | -47.2 | [-2.942; -2.737] | <0.0001 |
| symmetric | preview_ideal10 | imp20_min1 | -1.987 | -38.5 | [-2.076; -1.899] | <0.0001 |
| symmetric | preview_ideal10_min2 | va_min1_gap0 | -1.198 | -28.3 | [-1.253; -1.143] | <0.0001 |
| symmetric | preview_ideal10_min2 | va_min8_gap3 | -2.977 | -49.5 | [-3.084; -2.870] | <0.0001 |
| symmetric | preview_ideal10_min2 | imp20_min1 | -2.125 | -41.2 | [-2.210; -2.040] | <0.0001 |
| symmetric | preview_ideal5 | va_min1_gap0 | -0.963 | -22.7 | [-1.030; -0.896] | <0.0001 |
| symmetric | preview_ideal5 | va_min8_gap3 | -2.742 | -45.6 | [-2.836; -2.648] | <0.0001 |
| symmetric | preview_ideal5 | imp20_min1 | -1.890 | -36.6 | [-1.984; -1.795] | <0.0001 |
| symmetric | preview_none | va_min1_gap0 | 0.486 | 11.5 | [0.417; 0.554] | <0.0001 |
| symmetric | preview_none | va_min8_gap3 | -1.293 | -21.5 | [-1.424; -1.163] | <0.0001 |
| symmetric | preview_none | imp20_min1 | -0.441 | -8.5 | [-0.548; -0.334] | 0.0002 |
| symmetric | va_min1_gap0 | va_min8_gap3 | -1.779 | -29.6 | [-1.878; -1.680] | <0.0001 |
| symmetric | imp20_min1 | va_min1_gap0 | 0.927 | 21.9 | [0.834; 1.020] | <0.0001 |
| symmetric_9 | preview_degraded10 | va_min1_gap0 | -0.420 | -5.9 | [-0.523; -0.317] | <0.0001 |
| symmetric_9 | preview_degraded10 | va_min8_gap3 | -2.509 | -27.3 | [-2.652; -2.367] | <0.0001 |
| symmetric_9 | preview_degraded10 | imp20_min1 | -1.947 | -22.6 | [-2.113; -1.781] | <0.0001 |
| symmetric_9 | preview_degraded10_min2 | va_min1_gap0 | -0.479 | -6.8 | [-0.602; -0.357] | <0.0001 |
| symmetric_9 | preview_degraded10_min2 | va_min8_gap3 | -2.569 | -28.0 | [-2.705; -2.433] | <0.0001 |
| symmetric_9 | preview_degraded10_min2 | imp20_min1 | -2.007 | -23.3 | [-2.180; -1.833] | <0.0001 |
| symmetric_9 | preview_ideal10 | va_min1_gap0 | -1.207 | -17.0 | [-1.330; -1.085] | <0.0001 |
| symmetric_9 | preview_ideal10 | va_min8_gap3 | -3.297 | -35.9 | [-3.436; -3.157] | <0.0001 |
| symmetric_9 | preview_ideal10 | imp20_min1 | -2.735 | -31.7 | [-2.873; -2.596] | <0.0001 |
| symmetric_9 | preview_ideal10_min2 | va_min1_gap0 | -1.258 | -17.7 | [-1.373; -1.142] | <0.0001 |
| symmetric_9 | preview_ideal10_min2 | va_min8_gap3 | -3.347 | -36.5 | [-3.481; -3.213] | <0.0001 |
| symmetric_9 | preview_ideal10_min2 | imp20_min1 | -2.785 | -32.3 | [-2.927; -2.643] | <0.0001 |
| symmetric_9 | preview_ideal5 | va_min1_gap0 | -0.959 | -13.5 | [-1.081; -0.837] | <0.0001 |
| symmetric_9 | preview_ideal5 | va_min8_gap3 | -3.048 | -33.2 | [-3.187; -2.910] | <0.0001 |
| symmetric_9 | preview_ideal5 | imp20_min1 | -2.486 | -28.8 | [-2.640; -2.332] | <0.0001 |
| symmetric_9 | preview_none | va_min1_gap0 | 0.128 | 1.8 | [0.019; 0.237] | 1.0000 |
| symmetric_9 | preview_none | va_min8_gap3 | -1.961 | -21.4 | [-2.108; -1.815] | <0.0001 |
| symmetric_9 | preview_none | imp20_min1 | -1.399 | -16.2 | [-1.550; -1.248] | <0.0001 |
| symmetric_9 | va_min1_gap0 | va_min8_gap3 | -2.089 | -22.8 | [-2.243; -1.935] | <0.0001 |
| symmetric_9 | imp20_min1 | va_min1_gap0 | 1.527 | 21.5 | [1.364; 1.690] | <0.0001 |
| symmetric_low | preview_degraded10 | va_min1_gap0 | -0.302 | -11.1 | [-0.392; -0.212] | <0.0001 |
| symmetric_low | preview_degraded10 | va_min8_gap3 | -1.940 | -44.5 | [-2.052; -1.827] | <0.0001 |
| symmetric_low | preview_degraded10 | imp20_min1 | -2.426 | -50.0 | [-2.532; -2.319] | <0.0001 |
| symmetric_low | preview_degraded10_min2 | va_min1_gap0 | -0.481 | -17.7 | [-0.560; -0.402] | <0.0001 |
| symmetric_low | preview_degraded10_min2 | va_min8_gap3 | -2.119 | -48.6 | [-2.231; -2.007] | <0.0001 |
| symmetric_low | preview_degraded10_min2 | imp20_min1 | -2.605 | -53.7 | [-2.699; -2.510] | <0.0001 |
| symmetric_low | preview_ideal10 | va_min1_gap0 | -1.210 | -44.5 | [-1.278; -1.143] | <0.0001 |
| symmetric_low | preview_ideal10 | va_min8_gap3 | -2.848 | -65.3 | [-2.947; -2.749] | <0.0001 |
| symmetric_low | preview_ideal10 | imp20_min1 | -3.334 | -68.8 | [-3.428; -3.240] | <0.0001 |
| symmetric_low | preview_ideal10_min2 | va_min1_gap0 | -1.361 | -50.0 | [-1.420; -1.301] | <0.0001 |
| symmetric_low | preview_ideal10_min2 | va_min8_gap3 | -2.998 | -68.8 | [-3.091; -2.905] | <0.0001 |
| symmetric_low | preview_ideal10_min2 | imp20_min1 | -3.484 | -71.9 | [-3.568; -3.401] | <0.0001 |
| symmetric_low | preview_ideal5 | va_min1_gap0 | -1.176 | -43.2 | [-1.240; -1.113] | <0.0001 |
| symmetric_low | preview_ideal5 | va_min8_gap3 | -2.814 | -64.5 | [-2.913; -2.715] | <0.0001 |
| symmetric_low | preview_ideal5 | imp20_min1 | -3.300 | -68.1 | [-3.390; -3.210] | <0.0001 |
| symmetric_low | preview_none | va_min1_gap0 | 0.503 | 18.5 | [0.438; 0.568] | <0.0001 |
| symmetric_low | preview_none | va_min8_gap3 | -1.134 | -26.0 | [-1.217; -1.052] | <0.0001 |
| symmetric_low | preview_none | imp20_min1 | -1.620 | -33.4 | [-1.713; -1.528] | <0.0001 |
| symmetric_low | va_min1_gap0 | va_min8_gap3 | -1.638 | -37.6 | [-1.717; -1.559] | <0.0001 |
| symmetric_low | imp20_min1 | va_min1_gap0 | 2.124 | 78.0 | [2.045; 2.202] | <0.0001 |
| high_load | preview_degraded10 | va_min1_gap0 | -3.342 | -1.8 | [-4.297; -2.386] | 0.0002 |
| high_load | preview_degraded10 | va_min8_gap3 | -3.902 | -2.1 | [-4.706; -3.097] | <0.0001 |
| high_load | preview_degraded10 | imp20_min1 | -7.459 | -3.8 | [-8.584; -6.333] | <0.0001 |
| high_load | preview_degraded10_min2 | va_min1_gap0 | -3.436 | -1.8 | [-4.377; -2.495] | <0.0001 |
| high_load | preview_degraded10_min2 | va_min8_gap3 | -3.996 | -2.1 | [-4.799; -3.194] | <0.0001 |
| high_load | preview_degraded10_min2 | imp20_min1 | -7.553 | -3.9 | [-8.622; -6.484] | <0.0001 |
| high_load | preview_ideal10 | va_min1_gap0 | -3.880 | -2.0 | [-4.887; -2.874] | <0.0001 |
| high_load | preview_ideal10 | va_min8_gap3 | -4.440 | -2.3 | [-5.119; -3.761] | <0.0001 |
| high_load | preview_ideal10 | imp20_min1 | -7.997 | -4.1 | [-9.077; -6.917] | <0.0001 |
| high_load | preview_ideal10_min2 | va_min1_gap0 | -3.969 | -2.1 | [-5.006; -2.932] | <0.0001 |
| high_load | preview_ideal10_min2 | va_min8_gap3 | -4.529 | -2.4 | [-5.271; -3.787] | <0.0001 |
| high_load | preview_ideal10_min2 | imp20_min1 | -8.086 | -4.2 | [-9.154; -7.017] | <0.0001 |
| high_load | preview_ideal5 | va_min1_gap0 | -3.913 | -2.1 | [-4.864; -2.961] | <0.0001 |
| high_load | preview_ideal5 | va_min8_gap3 | -4.473 | -2.4 | [-5.214; -3.732] | <0.0001 |
| high_load | preview_ideal5 | imp20_min1 | -8.030 | -4.1 | [-9.129; -6.931] | <0.0001 |
| high_load | preview_none | va_min1_gap0 | -3.088 | -1.6 | [-3.931; -2.244] | 0.0002 |
| high_load | preview_none | va_min8_gap3 | -3.648 | -1.9 | [-4.577; -2.718] | <0.0001 |
| high_load | preview_none | imp20_min1 | -7.204 | -3.7 | [-8.281; -6.128] | <0.0001 |
| high_load | va_min1_gap0 | va_min8_gap3 | -0.560 | -0.3 | [-1.662; 0.542] | 0.7899 |
| high_load | imp20_min1 | va_min1_gap0 | 4.117 | 2.2 | [2.998; 5.236] | <0.0001 |
| true_oversaturated | preview_degraded10 | va_min1_gap0 | -2.017 | -0.6 | [-2.927; -1.106] | 0.0679 |
| true_oversaturated | preview_degraded10 | va_min8_gap3 | -2.635 | -0.7 | [-3.316; -1.955] | 0.0002 |
| true_oversaturated | preview_degraded10 | imp20_min1 | -2.921 | -0.8 | [-3.572; -2.271] | <0.0001 |
| true_oversaturated | preview_degraded10_min2 | va_min1_gap0 | -2.119 | -0.6 | [-3.059; -1.178] | 0.1612 |
| true_oversaturated | preview_degraded10_min2 | va_min8_gap3 | -2.737 | -0.8 | [-3.524; -1.950] | 0.0002 |
| true_oversaturated | preview_degraded10_min2 | imp20_min1 | -3.023 | -0.8 | [-3.694; -2.353] | <0.0001 |
| true_oversaturated | preview_ideal10 | va_min1_gap0 | -1.837 | -0.5 | [-2.773; -0.900] | 0.0976 |
| true_oversaturated | preview_ideal10 | va_min8_gap3 | -2.455 | -0.7 | [-3.229; -1.682] | <0.0001 |
| true_oversaturated | preview_ideal10 | imp20_min1 | -2.741 | -0.8 | [-3.449; -2.034] | 0.0002 |
| true_oversaturated | preview_ideal10_min2 | va_min1_gap0 | -2.078 | -0.6 | [-2.944; -1.211] | 0.0324 |
| true_oversaturated | preview_ideal10_min2 | va_min8_gap3 | -2.696 | -0.7 | [-3.508; -1.884] | <0.0001 |
| true_oversaturated | preview_ideal10_min2 | imp20_min1 | -2.982 | -0.8 | [-3.650; -2.314] | <0.0001 |
| true_oversaturated | preview_ideal5 | va_min1_gap0 | -1.986 | -0.5 | [-2.901; -1.070] | 0.0976 |
| true_oversaturated | preview_ideal5 | va_min8_gap3 | -2.604 | -0.7 | [-3.405; -1.803] | 0.0003 |
| true_oversaturated | preview_ideal5 | imp20_min1 | -2.890 | -0.8 | [-3.560; -2.220] | <0.0001 |
| true_oversaturated | preview_none | va_min1_gap0 | -1.538 | -0.4 | [-2.336; -0.741] | 0.0087 |
| true_oversaturated | preview_none | va_min8_gap3 | -2.157 | -0.6 | [-3.001; -1.312] | 0.0062 |
| true_oversaturated | preview_none | imp20_min1 | -2.443 | -0.7 | [-3.046; -1.840] | <0.0001 |
| true_oversaturated | va_min1_gap0 | va_min8_gap3 | -0.618 | -0.2 | [-1.560; 0.323] | 1.0000 |
| true_oversaturated | imp20_min1 | va_min1_gap0 | 0.904 | 0.2 | [0.019; 1.790] | 1.0000 |

## Переключения и справедливость (среднее по seed)

| Сценарий | Контроллер | Переключений за 1800 с | Макс. красный при очереди, с | Остаток в очереди | Throughput, авто/ч |
|---|---|---:|---:|---:|---:|
| asymmetric_ew | imp20_min1 | 156.7 | 35.2 | 2.6 | 1668 |
| asymmetric_ew | imp20_min2 | 155.4 | 35.5 | 2.8 | 1668 |
| asymmetric_ew | imp20_min4 | 146.9 | 35.9 | 2.8 | 1668 |
| asymmetric_ew | imp20_min8 | 121.4 | 35.3 | 3.6 | 1666 |
| asymmetric_ew | preview_degraded10 | 132.7 | 36.8 | 2.2 | 1669 |
| asymmetric_ew | preview_degraded10_min2 | 140.6 | 36.6 | 2.3 | 1669 |
| asymmetric_ew | preview_ideal10 | 116.2 | 39.9 | 1.9 | 1669 |
| asymmetric_ew | preview_ideal10_min2 | 119.8 | 41.2 | 1.9 | 1670 |
| asymmetric_ew | preview_ideal5 | 121.9 | 37.3 | 1.8 | 1669 |
| asymmetric_ew | preview_none | 176.8 | 24.2 | 2.7 | 1668 |
| asymmetric_ew | va_min1_gap0 | 204.0 | 23.2 | 2.2 | 1668 |
| asymmetric_ew | va_min1_gap0.5 | 204.0 | 23.2 | 2.2 | 1668 |
| asymmetric_ew | va_min1_gap1 | 204.0 | 23.2 | 2.2 | 1668 |
| asymmetric_ew | va_min2_gap0 | 195.2 | 23.3 | 2.4 | 1668 |
| asymmetric_ew | va_min2_gap0.5 | 195.2 | 23.3 | 2.4 | 1668 |
| asymmetric_ew | va_min2_gap1 | 195.2 | 23.3 | 2.4 | 1668 |
| asymmetric_ew | va_min2_gap2 | 174.8 | 27.5 | 2.8 | 1668 |
| asymmetric_ew | va_min4_gap1 | 176.7 | 24.5 | 2.7 | 1668 |
| asymmetric_ew | va_min4_gap2 | 163.8 | 27.4 | 3.0 | 1668 |
| asymmetric_ew | va_min6_gap1 | 155.1 | 26.8 | 3.2 | 1667 |
| asymmetric_ew | va_min6_gap2 | 147.6 | 28.6 | 3.2 | 1667 |
| asymmetric_ew | va_min8_gap3 | 126.5 | 31.7 | 3.7 | 1666 |
| asymmetric_ns | imp20_min1 | 158.1 | 37.2 | 3.1 | 1663 |
| asymmetric_ns | imp20_min2 | 156.5 | 36.8 | 3.1 | 1663 |
| asymmetric_ns | imp20_min4 | 146.9 | 37.2 | 2.9 | 1663 |
| asymmetric_ns | imp20_min8 | 121.0 | 36.9 | 3.4 | 1662 |
| asymmetric_ns | preview_degraded10 | 132.7 | 39.2 | 2.6 | 1664 |
| asymmetric_ns | preview_degraded10_min2 | 139.6 | 38.3 | 2.5 | 1664 |
| asymmetric_ns | preview_ideal10 | 116.6 | 42.6 | 2.1 | 1664 |
| asymmetric_ns | preview_ideal10_min2 | 120.2 | 41.5 | 2.1 | 1664 |
| asymmetric_ns | preview_ideal5 | 121.5 | 39.4 | 2.2 | 1664 |
| asymmetric_ns | preview_none | 175.7 | 24.4 | 2.9 | 1663 |
| asymmetric_ns | va_min1_gap0 | 203.3 | 23.1 | 2.6 | 1663 |
| asymmetric_ns | va_min1_gap0.5 | 203.3 | 23.1 | 2.6 | 1663 |
| asymmetric_ns | va_min1_gap1 | 203.3 | 23.1 | 2.6 | 1663 |
| asymmetric_ns | va_min2_gap0 | 194.6 | 23.9 | 2.6 | 1663 |
| asymmetric_ns | va_min2_gap0.5 | 194.6 | 23.9 | 2.6 | 1663 |
| asymmetric_ns | va_min2_gap1 | 194.6 | 23.9 | 2.6 | 1663 |
| asymmetric_ns | va_min2_gap2 | 174.6 | 28.3 | 2.8 | 1663 |
| asymmetric_ns | va_min4_gap1 | 175.6 | 24.6 | 2.9 | 1663 |
| asymmetric_ns | va_min4_gap2 | 163.6 | 27.4 | 3.0 | 1662 |
| asymmetric_ns | va_min6_gap1 | 154.1 | 25.6 | 2.8 | 1663 |
| asymmetric_ns | va_min6_gap2 | 147.3 | 29.1 | 3.0 | 1662 |
| asymmetric_ns | va_min8_gap3 | 126.3 | 31.3 | 3.8 | 1661 |
| sudden_dominance_switch | imp20_min1 | 155.5 | 38.0 | 2.2 | 1664 |
| sudden_dominance_switch | imp20_min2 | 154.1 | 37.7 | 2.3 | 1664 |
| sudden_dominance_switch | imp20_min4 | 145.4 | 37.9 | 2.3 | 1664 |
| sudden_dominance_switch | imp20_min8 | 120.5 | 36.7 | 3.0 | 1663 |
| sudden_dominance_switch | preview_degraded10 | 132.3 | 39.5 | 2.0 | 1665 |
| sudden_dominance_switch | preview_degraded10_min2 | 139.1 | 38.8 | 1.9 | 1665 |
| sudden_dominance_switch | preview_ideal10 | 117.8 | 41.2 | 1.4 | 1666 |
| sudden_dominance_switch | preview_ideal10_min2 | 121.2 | 40.6 | 1.2 | 1666 |
| sudden_dominance_switch | preview_ideal5 | 121.5 | 37.2 | 1.5 | 1666 |
| sudden_dominance_switch | preview_none | 174.6 | 24.8 | 2.2 | 1664 |
| sudden_dominance_switch | va_min1_gap0 | 203.2 | 23.3 | 1.8 | 1665 |
| sudden_dominance_switch | va_min1_gap0.5 | 203.2 | 23.3 | 1.8 | 1665 |
| sudden_dominance_switch | va_min1_gap1 | 203.2 | 23.3 | 1.8 | 1665 |
| sudden_dominance_switch | va_min2_gap0 | 194.9 | 24.4 | 1.9 | 1665 |
| sudden_dominance_switch | va_min2_gap0.5 | 194.9 | 24.4 | 1.9 | 1665 |
| sudden_dominance_switch | va_min2_gap1 | 194.9 | 24.4 | 1.9 | 1665 |
| sudden_dominance_switch | va_min2_gap2 | 173.8 | 27.2 | 2.0 | 1665 |
| sudden_dominance_switch | va_min4_gap1 | 174.5 | 24.8 | 2.2 | 1664 |
| sudden_dominance_switch | va_min4_gap2 | 162.5 | 27.5 | 2.3 | 1664 |
| sudden_dominance_switch | va_min6_gap1 | 154.2 | 26.1 | 2.1 | 1664 |
| sudden_dominance_switch | va_min6_gap2 | 146.7 | 28.9 | 2.2 | 1664 |
| sudden_dominance_switch | va_min8_gap3 | 126.0 | 32.1 | 2.6 | 1664 |
| symmetric | imp20_min1 | 161.8 | 33.0 | 2.1 | 1428 |
| symmetric | imp20_min2 | 161.5 | 32.7 | 2.2 | 1428 |
| symmetric | imp20_min4 | 156.1 | 32.0 | 2.3 | 1427 |
| symmetric | imp20_min8 | 132.5 | 31.0 | 2.5 | 1427 |
| symmetric | preview_degraded10 | 157.3 | 26.0 | 1.7 | 1429 |
| symmetric | preview_degraded10_min2 | 166.3 | 25.9 | 1.5 | 1429 |
| symmetric | preview_ideal10 | 140.1 | 27.4 | 1.3 | 1430 |
| symmetric | preview_ideal10_min2 | 145.3 | 27.5 | 1.1 | 1430 |
| symmetric | preview_ideal5 | 144.2 | 25.3 | 1.3 | 1429 |
| symmetric | preview_none | 195.7 | 17.1 | 2.2 | 1428 |
| symmetric | va_min1_gap0 | 226.9 | 16.8 | 1.6 | 1428 |
| symmetric | va_min1_gap0.5 | 226.9 | 16.8 | 1.6 | 1428 |
| symmetric | va_min1_gap1 | 226.9 | 16.8 | 1.6 | 1428 |
| symmetric | va_min2_gap0 | 217.8 | 16.8 | 1.4 | 1429 |
| symmetric | va_min2_gap0.5 | 217.8 | 16.8 | 1.4 | 1429 |
| symmetric | va_min2_gap1 | 217.8 | 16.8 | 1.4 | 1429 |
| symmetric | va_min2_gap2 | 196.6 | 19.5 | 1.8 | 1428 |
| symmetric | va_min4_gap1 | 195.7 | 17.1 | 2.2 | 1428 |
| symmetric | va_min4_gap2 | 184.5 | 19.1 | 2.2 | 1427 |
| symmetric | va_min6_gap1 | 171.6 | 17.6 | 2.1 | 1428 |
| symmetric | va_min6_gap2 | 165.2 | 20.0 | 1.9 | 1428 |
| symmetric | va_min8_gap3 | 141.6 | 22.3 | 2.5 | 1427 |
| symmetric_9 | imp20_min1 | 193.1 | 24.9 | 6.0 | 2135 |
| symmetric_9 | imp20_min2 | 191.0 | 24.7 | 6.2 | 2134 |
| symmetric_9 | imp20_min4 | 182.6 | 25.5 | 6.5 | 2134 |
| symmetric_9 | imp20_min8 | 146.1 | 25.1 | 6.9 | 2134 |
| symmetric_9 | preview_degraded10 | 143.9 | 28.9 | 4.7 | 2137 |
| symmetric_9 | preview_degraded10_min2 | 148.5 | 28.1 | 4.7 | 2137 |
| symmetric_9 | preview_ideal10 | 133.3 | 31.6 | 3.9 | 2139 |
| symmetric_9 | preview_ideal10_min2 | 136.0 | 31.7 | 4.0 | 2139 |
| symmetric_9 | preview_ideal5 | 123.4 | 32.0 | 4.5 | 2138 |
| symmetric_9 | preview_none | 164.6 | 27.6 | 5.2 | 2137 |
| symmetric_9 | va_min1_gap0 | 178.8 | 29.9 | 5.2 | 2136 |
| symmetric_9 | va_min1_gap0.5 | 178.8 | 29.9 | 5.2 | 2136 |
| symmetric_9 | va_min1_gap1 | 178.8 | 29.9 | 5.2 | 2136 |
| symmetric_9 | va_min2_gap0 | 173.7 | 30.3 | 5.4 | 2136 |
| symmetric_9 | va_min2_gap0.5 | 173.7 | 30.3 | 5.4 | 2136 |
| symmetric_9 | va_min2_gap1 | 173.7 | 30.3 | 5.4 | 2136 |
| symmetric_9 | va_min2_gap2 | 140.1 | 34.0 | 5.9 | 2135 |
| symmetric_9 | va_min4_gap1 | 161.5 | 30.6 | 5.1 | 2137 |
| symmetric_9 | va_min4_gap2 | 136.8 | 34.2 | 6.1 | 2135 |
| symmetric_9 | va_min6_gap1 | 147.1 | 30.2 | 5.1 | 2137 |
| symmetric_9 | va_min6_gap2 | 129.9 | 34.4 | 6.1 | 2135 |
| symmetric_9 | va_min8_gap3 | 109.5 | 37.4 | 6.5 | 2134 |
| symmetric_low | imp20_min1 | 87.9 | 43.1 | 0.8 | 719 |
| symmetric_low | imp20_min2 | 87.7 | 43.1 | 0.8 | 719 |
| symmetric_low | imp20_min4 | 87.2 | 43.1 | 0.8 | 719 |
| symmetric_low | imp20_min8 | 84.2 | 41.9 | 1.0 | 719 |
| symmetric_low | preview_degraded10 | 130.2 | 20.7 | 0.3 | 720 |
| symmetric_low | preview_degraded10_min2 | 136.9 | 20.5 | 0.3 | 720 |
| symmetric_low | preview_ideal10 | 116.6 | 19.6 | 0.2 | 720 |
| symmetric_low | preview_ideal10_min2 | 120.5 | 19.7 | 0.2 | 720 |
| symmetric_low | preview_ideal5 | 124.0 | 15.3 | 0.2 | 720 |
| symmetric_low | preview_none | 146.1 | 9.8 | 0.7 | 719 |
| symmetric_low | va_min1_gap0 | 159.6 | 9.1 | 0.4 | 720 |
| symmetric_low | va_min1_gap0.5 | 159.6 | 9.1 | 0.4 | 720 |
| symmetric_low | va_min1_gap1 | 159.6 | 9.1 | 0.4 | 720 |
| symmetric_low | va_min2_gap0 | 155.5 | 9.0 | 0.5 | 720 |
| symmetric_low | va_min2_gap0.5 | 155.5 | 9.0 | 0.5 | 720 |
| symmetric_low | va_min2_gap1 | 155.5 | 9.0 | 0.5 | 720 |
| symmetric_low | va_min2_gap2 | 152.9 | 11.0 | 0.5 | 720 |
| symmetric_low | va_min4_gap1 | 146.1 | 9.8 | 0.7 | 719 |
| symmetric_low | va_min4_gap2 | 145.2 | 11.3 | 0.7 | 719 |
| symmetric_low | va_min6_gap1 | 134.1 | 10.7 | 0.7 | 719 |
| symmetric_low | va_min6_gap2 | 133.9 | 12.1 | 0.7 | 719 |
| symmetric_low | va_min8_gap3 | 122.6 | 14.0 | 0.8 | 719 |
| high_load | imp20_min1 | 42.9 | 48.0 | 452.3 | 3407 |
| high_load | imp20_min2 | 42.9 | 48.0 | 452.2 | 3407 |
| high_load | imp20_min4 | 42.5 | 48.0 | 452.3 | 3407 |
| high_load | imp20_min8 | 41.8 | 48.0 | 452.1 | 3407 |
| high_load | preview_degraded10 | 39.3 | 48.0 | 443.2 | 3425 |
| high_load | preview_degraded10_min2 | 39.5 | 48.0 | 443.2 | 3425 |
| high_load | preview_ideal10 | 39.1 | 48.0 | 443.0 | 3425 |
| high_load | preview_ideal10_min2 | 39.2 | 48.0 | 442.9 | 3425 |
| high_load | preview_ideal5 | 39.2 | 48.0 | 442.7 | 3426 |
| high_load | preview_none | 40.7 | 48.0 | 443.7 | 3424 |
| high_load | va_min1_gap0 | 39.5 | 48.0 | 447.2 | 3417 |
| high_load | va_min1_gap0.5 | 39.5 | 48.0 | 447.2 | 3417 |
| high_load | va_min1_gap1 | 39.5 | 48.0 | 447.2 | 3417 |
| high_load | va_min2_gap0 | 39.3 | 48.0 | 446.9 | 3417 |
| high_load | va_min2_gap0.5 | 39.3 | 48.0 | 446.9 | 3417 |
| high_load | va_min2_gap1 | 39.3 | 48.0 | 446.9 | 3417 |
| high_load | va_min2_gap2 | 39.0 | 48.0 | 447.8 | 3416 |
| high_load | va_min4_gap1 | 39.0 | 48.0 | 446.9 | 3418 |
| high_load | va_min4_gap2 | 38.8 | 48.0 | 448.3 | 3415 |
| high_load | va_min6_gap1 | 38.8 | 48.0 | 446.7 | 3418 |
| high_load | va_min6_gap2 | 38.5 | 48.0 | 448.1 | 3415 |
| high_load | va_min8_gap3 | 38.1 | 48.0 | 447.7 | 3416 |
| true_oversaturated | imp20_min1 | 40.0 | 48.0 | 1163.3 | 3430 |
| true_oversaturated | imp20_min2 | 39.9 | 48.0 | 1163.3 | 3430 |
| true_oversaturated | imp20_min4 | 39.6 | 48.0 | 1163.6 | 3429 |
| true_oversaturated | imp20_min8 | 39.2 | 48.0 | 1163.2 | 3430 |
| true_oversaturated | preview_degraded10 | 38.3 | 48.0 | 1159.8 | 3437 |
| true_oversaturated | preview_degraded10_min2 | 38.3 | 48.0 | 1159.7 | 3437 |
| true_oversaturated | preview_ideal10 | 37.7 | 48.0 | 1159.6 | 3437 |
| true_oversaturated | preview_ideal10_min2 | 37.8 | 48.0 | 1159.4 | 3438 |
| true_oversaturated | preview_ideal5 | 38.0 | 48.0 | 1159.5 | 3437 |
| true_oversaturated | preview_none | 38.8 | 48.0 | 1159.9 | 3437 |
| true_oversaturated | va_min1_gap0 | 38.5 | 48.0 | 1162.7 | 3431 |
| true_oversaturated | va_min1_gap0.5 | 38.5 | 48.0 | 1162.7 | 3431 |
| true_oversaturated | va_min1_gap1 | 38.5 | 48.0 | 1162.7 | 3431 |
| true_oversaturated | va_min2_gap0 | 38.5 | 48.0 | 1162.2 | 3432 |
| true_oversaturated | va_min2_gap0.5 | 38.5 | 48.0 | 1162.2 | 3432 |
| true_oversaturated | va_min2_gap1 | 38.5 | 48.0 | 1162.2 | 3432 |
| true_oversaturated | va_min2_gap2 | 38.2 | 48.0 | 1162.9 | 3430 |
| true_oversaturated | va_min4_gap1 | 38.1 | 48.0 | 1162.1 | 3432 |
| true_oversaturated | va_min4_gap2 | 37.8 | 48.0 | 1162.6 | 3431 |
| true_oversaturated | va_min6_gap1 | 37.9 | 48.0 | 1162.1 | 3432 |
| true_oversaturated | va_min6_gap2 | 37.7 | 48.0 | 1162.7 | 3431 |
| true_oversaturated | va_min8_gap3 | 37.6 | 48.0 | 1162.8 | 3431 |
