# Max-red fairness development screen

30 paired development seeds, six balanced/asymmetric/changing/high-load scenarios, 1800 s.
Every controller uses the same arrivals within scenario/seed. Positive deltas are worse
for wait/queue/residual/red/range; positive throughput delta is better. Holm correction
is applied across all 10 controller pairs within each scenario × metric family.
Max signal red is derived from phase indications; it is not vehicle waiting time.

## Среднее по seed

| Сценарий | Контроллер | Wait, с | Max signal red (mean of run max), с | Worst red with queued demand, с | Residual | Max lane mean wait, с | Jain fairness | Switches | Yellow, % |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| asymmetric_ew | queue_based_improved | 6.56 | 47.7 | 48.0 | 4.2 | 7.83 | 0.987 | 121.7 | 20.24 |
| asymmetric_ew | queue_based_max_red_36s | 6.56 | 47.1 | 36.0 | 4.2 | 7.78 | 0.988 | 122.0 | 20.29 |
| asymmetric_ew | queue_based_max_red_42s | 6.57 | 47.4 | 41.6 | 4.2 | 7.80 | 0.988 | 121.8 | 20.26 |
| asymmetric_ew | queue_based_max_red_48s | 6.57 | 47.7 | 47.0 | 4.2 | 7.83 | 0.987 | 121.7 | 20.24 |
| asymmetric_ew | vehicle_actuated | 6.61 | 41.5 | 46.4 | 4.5 | 8.30 | 0.979 | 125.8 | 20.94 |
| asymmetric_ns | queue_based_improved | 6.40 | 44.7 | 48.0 | 4.2 | 7.71 | 0.984 | 121.2 | 20.17 |
| asymmetric_ns | queue_based_max_red_36s | 6.39 | 43.8 | 35.9 | 4.2 | 7.71 | 0.984 | 121.3 | 20.18 |
| asymmetric_ns | queue_based_max_red_42s | 6.39 | 44.3 | 41.6 | 4.2 | 7.72 | 0.984 | 121.2 | 20.17 |
| asymmetric_ns | queue_based_max_red_48s | 6.40 | 44.7 | 47.0 | 4.2 | 7.71 | 0.985 | 121.2 | 20.17 |
| asymmetric_ns | vehicle_actuated | 6.46 | 39.9 | 48.0 | 3.9 | 8.30 | 0.974 | 125.5 | 20.89 |
| high_load | queue_based_improved | 203.95 | 48.0 | 48.0 | 460.6 | 233.79 | 0.984 | 46.3 | 7.71 |
| high_load | queue_based_max_red_36s | 218.10 | 35.0 | 35.0 | 511.9 | 248.66 | 0.986 | 55.9 | 9.28 |
| high_load | queue_based_max_red_42s | 211.99 | 41.0 | 41.0 | 493.6 | 242.14 | 0.985 | 50.5 | 8.41 |
| high_load | queue_based_max_red_48s | 208.11 | 47.0 | 47.0 | 480.3 | 237.62 | 0.985 | 46.8 | 7.79 |
| high_load | vehicle_actuated | 195.51 | 48.0 | 48.0 | 447.8 | 235.49 | 0.974 | 38.2 | 6.35 |
| sudden_dominance_switch | queue_based_improved | 6.47 | 45.9 | 48.0 | 3.8 | 7.12 | 0.992 | 122.2 | 20.34 |
| sudden_dominance_switch | queue_based_max_red_36s | 6.47 | 44.5 | 35.9 | 3.8 | 7.13 | 0.992 | 122.4 | 20.37 |
| sudden_dominance_switch | queue_based_max_red_42s | 6.46 | 45.3 | 41.6 | 3.8 | 7.12 | 0.992 | 122.2 | 20.34 |
| sudden_dominance_switch | queue_based_max_red_48s | 6.47 | 45.9 | 47.3 | 3.8 | 7.12 | 0.992 | 122.2 | 20.34 |
| sudden_dominance_switch | vehicle_actuated | 6.56 | 40.8 | 44.0 | 4.3 | 7.21 | 0.993 | 124.7 | 20.75 |
| symmetric_low | queue_based_improved | 5.28 | 54.0 | 48.0 | 1.7 | 6.22 | 0.982 | 83.6 | 13.91 |
| symmetric_low | queue_based_max_red_36s | 5.27 | 54.0 | 36.0 | 1.7 | 6.20 | 0.983 | 84.4 | 14.06 |
| symmetric_low | queue_based_max_red_42s | 5.28 | 54.0 | 42.0 | 1.7 | 6.21 | 0.982 | 83.8 | 13.95 |
| symmetric_low | queue_based_max_red_48s | 5.28 | 54.0 | 48.0 | 1.7 | 6.22 | 0.982 | 83.6 | 13.91 |
| symmetric_low | vehicle_actuated | 4.26 | 55.8 | 19.0 | 1.4 | 4.84 | 0.988 | 121.8 | 20.28 |
| true_oversaturated | queue_based_improved | 369.01 | 48.0 | 48.0 | 1161.4 | 394.21 | 0.997 | 40.9 | 6.80 |
| true_oversaturated | queue_based_max_red_36s | 385.54 | 35.0 | 35.0 | 1229.0 | 409.02 | 0.997 | 53.3 | 8.89 |
| true_oversaturated | queue_based_max_red_42s | 380.34 | 41.0 | 41.0 | 1208.6 | 404.65 | 0.997 | 46.4 | 7.73 |
| true_oversaturated | queue_based_max_red_48s | 376.20 | 47.0 | 47.0 | 1193.4 | 401.26 | 0.997 | 41.5 | 6.92 |
| true_oversaturated | vehicle_actuated | 366.29 | 48.0 | 48.0 | 1157.4 | 396.43 | 0.995 | 37.8 | 6.28 |

Seed-level metrics and all Holm-adjusted paired contrasts are in the adjacent CSV files.
These seed IDs are development data, not an independent final test set.
