# Независимая проверка относительного switching margin 0,20

30 новых парных seed (9101–9130), семь сценариев, горизонт 1800 с. Заранее выбранная политика: абсолютный margin 1 и relative margin 0,20. Контрасты выполнены отдельно против Improved (1/0,10) и Vehicle-actuated; Holm применён сразу по 14 сравнениям. Положительное Δ означает большее ожидание у кандидата.

| Сценарий | Компаратор | Пар | Δ ожидания, с | 95% CI | Holm p |
|---|---|---:|---:|---:|---:|
| asymmetric_ew | improved_abs1_rel010 | 30 | -0.039 | [-0.065; -0.012] | 0.1129 |
| asymmetric_ew | vehicle_actuated | 30 | -0.168 | [-0.296; -0.040] | 0.9247 |
| asymmetric_ns | improved_abs1_rel010 | 30 | -0.018 | [-0.047; 0.011] | 0.5924 |
| asymmetric_ns | vehicle_actuated | 30 | -0.187 | [-0.313; -0.062] | 0.2994 |
| high_load | improved_abs1_rel010 | 30 | -6.236 | [-6.856; -5.616] | <0.0001 |
| high_load | vehicle_actuated | 30 | 2.951 | [1.400; 4.503] | 0.0143 |
| sudden_dominance_switch | improved_abs1_rel010 | 30 | -0.026 | [-0.062; 0.009] | 0.9247 |
| sudden_dominance_switch | vehicle_actuated | 30 | -0.122 | [-0.246; 0.001] | 0.9247 |
| symmetric_9 | improved_abs1_rel010 | 30 | -0.732 | [-0.913; -0.551] | <0.0001 |
| symmetric_9 | vehicle_actuated | 30 | 0.233 | [0.039; 0.426] | 0.1290 |
| symmetric_low | improved_abs1_rel010 | 30 | 0.001 | [-0.001; 0.003] | 1.0000 |
| symmetric_low | vehicle_actuated | 30 | 1.161 | [1.019; 1.304] | <0.0001 |
| true_oversaturated | improved_abs1_rel010 | 30 | -3.384 | [-3.879; -2.889] | <0.0001 |
| true_oversaturated | vehicle_actuated | 30 | 0.451 | [-0.469; 1.372] | 1.0000 |
