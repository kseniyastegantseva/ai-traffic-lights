# Revised simulation results

These results supersede the five-seed numbers in the earlier article. They were produced from commit `947d83ae3a333ef2ae2c7d286efc3463e6b2342e` using Python 3.12.3, SimPy 4.1.2, pandas 2.2.3, Pydantic 2.14.2, NumPy 1.26.4, and PyYAML 6.0.1. The environment did not have `ultralytics`; no new detector inference was performed.

## Main series

Each horizon has 900 runs: five scenarios × 30 seeds × six controllers. The controllers were `fixed_15`, `fixed_35`, `fixed_webster`, `vehicle_actuated`, `queue_based`, and `queue_based_legacy`. Each scenario/seed group used one arrival stream across all controllers. All 150 groups at each horizon had matching SHA-256 stream digests. All 1800 runs satisfied `initial + arrived = departed + waiting + in_service`; every queue series had exactly one sample per simulated second. Phase histories contained no consecutive yellow intervals or repeated green records for the same phase without an intervening transition.

Mean completed-vehicle waiting time in seconds (mean across 30 seeds):

| Scenario | Horizon | fixed_15 | fixed_35 | Webster | Vehicle-actuated | Queue-based |
|---|---:|---:|---:|---:|---:|---:|
| Symmetric | 1800 s | 8.19 | 14.13 | 6.61 | 6.10 | 6.00 |
| Symmetric | 3600 s | 8.16 | 14.22 | 6.64 | 6.11 | 6.04 |
| Asymmetric N/S | 1800 s | 10.86 | 16.47 | 7.26 | 6.56 | 6.43 |
| Asymmetric N/S | 3600 s | 11.05 | 16.63 | 7.32 | 6.59 | 6.47 |
| Variable demand | 1800 s | 14.72 | 18.71 | 16.99 | 6.39 | 6.17 |
| Variable demand | 3600 s | 18.88 | 20.73 | 28.89 | 6.61 | 6.41 |
| Dominant axis switches | 1800 s | 11.28 | 16.78 | 33.73 | 6.58 | 6.49 |
| Dominant axis switches | 3600 s | 11.34 | 16.75 | 127.99 | 6.64 | 6.48 |
| High load | 1800 s | 237.50 | 200.86 | 195.95 | 191.34 | 315.60 |
| High load | 3600 s | 469.82 | 389.21 | 375.96 | 371.36 | 630.22 |

Paired contrasts are `queue_based − comparator`. Negative values favor queue-based control. Intervals are 95% Student-t intervals over paired seed differences. The exact two-sided sign test was used, with Holm adjustment across the five comparator tests within each scenario/horizon.

| Scenario | Horizon | Comparator | Paired difference, s (95% CI) | Holm-adjusted p |
|---|---:|---|---:|---:|
| Symmetric | 1800 s | fixed_15 | −2.19 [−2.36, −2.03] | <0.001 |
| Symmetric | 1800 s | fixed_35 | −8.13 [−8.37, −7.90] | <0.001 |
| Symmetric | 1800 s | Webster | −0.61 [−0.77, −0.46] | <0.001 |
| Symmetric | 1800 s | Vehicle-actuated | −0.11 [−0.24, 0.03] | 0.086 |
| Symmetric | 3600 s | Vehicle-actuated | −0.07 [−0.16, 0.02] | 0.856 |
| Asymmetric N/S | 1800 s | fixed_15 | −4.44 [−4.85, −4.02] | <0.001 |
| Asymmetric N/S | 1800 s | Webster | −0.84 [−1.00, −0.68] | <0.001 |
| Asymmetric N/S | 1800 s | Vehicle-actuated | −0.14 [−0.23, −0.04] | <0.001 |
| Variable demand | 1800 s | Vehicle-actuated | −0.22 [−0.31, −0.12] | <0.001 |
| Dominant axis switches | 1800 s | Webster | −27.24 [−30.64, −23.83] | <0.001 |
| Dominant axis switches | 1800 s | Vehicle-actuated | −0.09 [−0.21, 0.04] | 0.362 |
| Dominant axis switches | 3600 s | Webster | −121.51 [−130.68, −112.34] | <0.001 |
| Dominant axis switches | 3600 s | Vehicle-actuated | −0.17 [−0.25, −0.08] | 0.001 |
| High load | 1800 s | fixed_15 | +78.10 [+75.24, +80.96] | <0.001 |
| High load | 1800 s | fixed_35 | +114.75 [+111.90, +117.60] | <0.001 |
| High load | 1800 s | Webster | +119.65 [+116.71, +122.60] | <0.001 |
| High load | 1800 s | Vehicle-actuated | +124.27 [+121.22, +127.32] | <0.001 |
| High load | 3600 s | fixed_15 | +160.40 [+155.98, +164.82] | <0.001 |
| High load | 3600 s | fixed_35 | +241.01 [+237.39, +244.63] | <0.001 |
| High load | 3600 s | Webster | +254.26 [+250.66, +257.86] | <0.001 |
| High load | 3600 s | Vehicle-actuated | +258.86 [+255.11, +262.60] | <0.001 |

In symmetric demand, queue-based control was not distinguishable from vehicle-actuated control after correction at either horizon. It also improved modestly over Webster. In the changing-demand scenarios, queue-based and vehicle-actuated means were close; comparisons were not uniformly significant. The fixed Webster split performed poorly after the dominant axis changed because its split was computed from the configured base rates and did not adapt to the later schedule. Queue-based control was clearly inferior under high load.

For high load, the estimated equal-split per-approach capacity is approximately 13.82 vehicles/minute; configured demand is 18 vehicles/minute per approach (`v/c ≈ 1.30` under this approximation). Mean queue-based arrivals/residual waiting counts were 2157/758 at 1800 s and 4306/1505 at 3600 s. Vehicle-actuated control served 1707/3432 vehicles on average at the two horizons, compared with 1396/2799 for queue-based control. Residual waiting counts for vehicle-actuated were 448/872. These results confirm sustained queue growth in this model and workload; they do not measure real-road capacity.

## Synthetic perception sensitivity

The original sensitivity run was invalid: `_iter_scenarios()` dropped each scenario's `observation_error_rate`, so every simulation received 0% even when the YAML title indicated a higher level. Its previously reported identical outcomes are withdrawn. The runner now propagates the rate and the result record stores it; a regression test checks this contract.

The corrected original symmetric configuration was rerun for 240 runs. The broader configuration `configs/piere_perception_sensitivity_expanded.yaml` contains five demand regimes, four error rates, 30 seeds, and two controllers (1,200 runs total). For each regime/seed, all error levels share the same arrival-stream hash. All records contain the configured error rate, and all 30 paired queue-based phase histories differed between 0% and each nonzero rate in every regime. The perturbation remains an artificial count miss/duplicate process, not calibrated from the detector evaluation.

Queue-based mean completed wait by regime and error rate (seconds):

| Demand regime | 0% | 5% | 10% | 20% | Paired change at 20% vs 0% (95% CI) |
|---|---:|---:|---:|---:|---:|
| Symmetric | 6.040 | 6.074 | 6.064 | 6.074 | +0.034 [−0.064, +0.131] |
| Asymmetric N/S | 6.364 | 6.425 | 6.546 | 6.771 | +0.406 [+0.295, +0.518] |
| Variable demand | 6.174 | 6.301 | 6.312 | 6.446 | +0.271 [+0.145, +0.398] |
| Dominant-axis switch | 6.394 | 6.455 | 6.543 | 6.704 | +0.309 [+0.211, +0.408] |
| High load | 314.957 | 317.381 | 315.376 | 316.621 | +1.664 [−0.384, +3.712] |

The confidence intervals use paired seed differences (n=30) with a two-sided 95% Student-t interval; they are descriptive across tested scenarios and are not corrected for the multiple error-level contrasts. The small absolute changes in high load are noisy relative to its large baseline delay. Higher rates generally increase mean wait in asymmetric and changing demand, while high-load means are not monotonic. The experiment supports scenario-specific sensitivity, not general robustness or empirical YOLO calibration.

### Bootstrap of observed YOLO count residuals

The count annotations provide signed per-image residuals `predicted − actual` for each approach. The empirical profile in `configs/piere_perception_empirical_errors.yaml` resamples, with replacement, the 16 recorded residuals for each lane at each one-second observation; the sampled residual is added to the true lane queue and clipped at zero. This is separate from the synthetic 0–20% miss/duplicate model. It is an additive, independent-over-time bootstrap: it does not model temporal correlation, scene dependence, object identity, or errors outside this reused 16-image set. It is therefore a diagnostic sensitivity analysis, not an estimate of deployment performance.

The 300-run series uses five demand regimes, 30 seeds, and two responsive controllers. Compared with the corresponding 0%-synthetic-error runs, arrival-stream hashes match for every paired seed. Queue-based controller results were:

| Demand regime | Mean wait, error-profile bootstrap (s) | Mean wait, 0% synthetic baseline (s) | Paired change (95% CI), s |
|---|---:|---:|---:|
| Symmetric | 6.582 | 6.040 | +0.541 [+0.404, +0.678] |
| Asymmetric N/S | 9.076 | 6.364 | +2.711 [+2.500, +2.922] |
| Variable demand | 8.202 | 6.174 | +2.028 [+1.840, +2.216] |
| Dominant-axis switch | 8.553 | 6.394 | +2.159 [+1.957, +2.361] |
| High load | 315.384 | 314.957 | +0.427 [−1.289, +2.144] |

The intervals use paired seed differences (n=30), two-sided 95% Student-t intervals, and are not adjusted for five scenario comparisons. The profile changes the `queue_based` phase history for all 30 seeds in every regime. The much smaller high-load change is uncertain relative to its baseline delay. The input residual vectors and full run configuration are preserved in the YAML; generated JSON remains ignored under `outputs/`.

## Reproduction and limitations

### Detector evaluation addendum

After the simulation commit, live detector inference and the x2/x3/NMS ablation were completed on the bundled 16-image set. The production path reproduced the archived VCA 85.23% and MAE 1.484375 exactly. See `paper/perception_results.md` for metrics, checkpoint hashes, method differences, and provenance limitations. This set is diagnostic rather than independent holdout data.

Run from the repository root:

```bash
traffic-sim compare --config configs/piere_revision_1800.yaml
traffic-sim compare --config configs/piere_revision_3600.yaml
traffic-sim compare --config configs/piere_perception_sensitivity.yaml
traffic-sim compare --config configs/piere_perception_sensitivity_expanded.yaml
```

The generated JSON contains every run, full configuration, environment metadata, stream hashes, phase history, and paired statistics. Output files are ignored by Git due to their size. The experiment-generating revision passed 52 tests; after the dashboard trace integration, 53 tests passed and Ruff reported no issues. After the sensitivity-rate fix and empirical profile support, Ruff and the full test suite passed (55 tests); the detector evaluation script also passes `py_compile`. A Streamlit AppTest rendered the simulation screen with no exceptions and one animation iframe. Docker Desktop was unavailable, so image builds were not verified. Independent detector validation, model-training provenance, and the exact wording of the source reviewer comments remain unresolved.
