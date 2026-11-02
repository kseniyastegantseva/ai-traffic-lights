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

The sensitivity configuration has 30 paired seeds, one symmetric 6 vehicles/minute/approach demand, and two controllers (`fixed_35`, `queue_based`). It tests 0%, 5%, 10%, and 20% synthetic observation error, applied only to the controller's observed queues. Arrival-stream hashes match for all 30 seeds across error levels. For queue-based control, the performance outputs were identical at each error level: mean wait was 6.040 s at all four levels, and paired waiting-time changes relative to 0% were 0.000 s (95% paired t intervals [0.000, 0.000]).

The result indicates that the perturbations did not change selected control actions or aggregate outcomes in this particular symmetric scenario. It does not demonstrate robustness to empirically observed detector errors or changing demand. The perturbation is independently seeded count misses/duplicates and is not calibrated from the 16-image detector evaluation.

## Reproduction and limitations

Run from the repository root:

```bash
traffic-sim compare --config configs/piere_revision_1800.yaml
traffic-sim compare --config configs/piere_revision_3600.yaml
traffic-sim compare --config configs/piere_perception_sensitivity.yaml
```

The generated JSON contains every run, full configuration, environment metadata, stream hashes, phase history, and paired statistics. Output files are ignored by Git due to their size. The experiment-generating revision passed 52 tests; after the dashboard trace integration, 53 tests passed and Ruff reported no issues. A Streamlit AppTest rendered the simulation screen with no exceptions and one animation iframe. Docker Desktop was unavailable, so image builds were not verified. Live detector inference, model-training provenance, and the exact wording of the source reviewer comments remain unresolved.
