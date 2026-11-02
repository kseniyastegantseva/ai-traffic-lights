# PIERE simulation results and reproducibility record

This report summarizes the 30-seed paired simulation series in this revision. The complete per-run records, confidence intervals, exact sign-test p-values, Holm adjustments, CSV summaries, and configuration/environment snapshots are committed under `outputs/`. The central result is conditional: queue-based control can perform well at moderate demand, but it does not dominate all baselines or demand levels. Its completed-vehicle wait and residual queue are substantially worse under the model's overloaded workloads.

## Experimental matrix

The primary matrix includes 5 demand scenarios × 30 seeds × 6 controllers at 1800 s and 3600 s (900 runs per horizon). A separate addendum adds four demand conditions × 30 new seeds × 6 controllers (720 runs per horizon): symmetric 3/min, symmetric 9/min, mirrored E/W asymmetry 4/10, and symmetric 24/min. The prior 18/min `high_load` series is retained under its existing name. Every controller within one scenario/seed uses the same generated arrival stream. Hashes, initial/arrived/departed/waiting/in-service counts, one-second queue history, and phase history are stored per run.

The baseline controller set is `fixed_15`, `fixed_35`, `fixed_webster`, `vehicle_actuated`, `queue_based`, and `queue_based_legacy`. Each configuration explicitly records 30 seeds and a 2 s discharge time. The demand-shift scenarios change rates at 900 s.

## Main 3600 s results

Means below are across 30 seeds. The full precision and paired comparisons are in the JSON, CSV, and report file for each horizon/scenario set.

| Demand scenario | Queue-based wait (s) | Best non-queue wait (s) | Mean queue (veh) | Throughput (veh/h) | Residual waiting (veh) |
|---|---:|---:|---:|---:|---:|
| Symmetric 6/min | 6.04 | 6.11 vehicle-actuated | 2.4 | 1433.6 | 2.4 |
| Asymmetric N/S 10/4 | 6.47 | 6.59 vehicle-actuated | 3.0 | 1669.7 | 3.6 |
| Variable demand | 6.41 | 6.61 vehicle-actuated | 3.0 | 1705.1 | 3.1 |
| Dominance switch | 6.48 | 6.64 vehicle-actuated | 3.0 | 1671.4 | 3.4 |
| High load 18/min | 630.22 | 371.36 vehicle-actuated | 755.0 | 2799.3 | 1505.1 |
| Symmetric 3/min | 5.41 | 4.35 vehicle-actuated | 1.1 | 712.3 | 1.1 |
| Symmetric 9/min | 10.28 | 9.35 vehicle-actuated | 6.1 | 2142.3 | 6.2 |
| Asymmetric E/W 4/10 | 6.38 | 6.55 vehicle-actuated | 3.0 | 1664.9 | 4.3 |
| True oversaturated 24/min | 913.02 | 721.53 vehicle-actuated | 1457.3 | 2821.8 | 2907.0 |

The queue-based point estimate is lowest in some balanced and asymmetric scenarios but not at 3/min or 9/min. The original 18/min high-load and new 24/min scenarios show much higher mean waiting, queue area, and end residual under queue-based control. At 24/min, the 3600 s queue-based mean queue is about 1,457 vehicles and its mean waiting residual is about 2,907 vehicles. The corresponding vehicle-actuated values are about 1,150 and 2,289. These are outcomes of the specified model and arrival process, not empirical road capacity estimates.

The completed-vehicle waiting mean has right-censoring/survivor bias when many vehicles remain waiting at `T`: vehicles that are still in the queue do not enter that statistic. Read the mean beside average queue (time integral), throughput, the saved `observed_delay_seconds`, and `waiting_at_end`. No warm-up is applied because these experiments estimate the transient from an initially empty system rather than stationary operation. The runs are not interpreted as steady-state samples.

## Paired inference

The primary contrast is queue-based mean wait minus each comparator, paired by seed. Its confidence interval uses the exact SciPy Student-t quantile with `n−1` degrees of freedom. A two-sided exact sign test reports directional evidence; Holm's step-down procedure adjusts the five comparisons within each scenario/horizon family. P-values below 0.0001 are printed as `<0.0001`; missing baselines are `N/A`. These choices and tests are covered by regression tests.

Detailed results:

- `outputs/piere_revision_1800_report.md` and `outputs/piere_revision_1800_summary.csv`
- `outputs/piere_revision_3600_report.md` and `outputs/piere_revision_3600_summary.csv`
- `outputs/piere_revision_addendum_1800_report.md` and `outputs/piere_revision_addendum_1800_summary.csv`
- `outputs/piere_revision_addendum_3600_report.md` and `outputs/piere_revision_addendum_3600_summary.csv`

## Perception sensitivity

The corrected synthetic sensitivity series has 1,200 runs (five regimes × four observation-error probabilities × 30 seeds × two controllers). The rate is passed through the scenario runner and saved in each result. At 20% versus 0%, queue-based completed-wait changes range from +0.02 to +1.66 s across the regimes; the high-load interval contains zero. The 300-run empirical signed count-residual bootstrap draws from 16 annotated images and applies each residual independently at controller observations. Changes are +0.54 to +2.71 s in four regimes and +0.43 s in high load (paired interval spans zero). This small, reused image set is a diagnostic perturbation, not an estimate of deployment error.

Full sensitivity tables are in `outputs/piere_perception_sensitivity_expanded_report.md` and `outputs/piere_perception_empirical_errors_report.md`. YOLO metrics and limitations are detailed in `paper/perception_results.md`.

## Reproduction

From the repository root with Python 3.12 and the project dependencies installed:

```bash
python -m pip install -e ".[dev]"
traffic-sim compare --config configs/piere_revision_1800.yaml
traffic-sim compare --config configs/piere_revision_3600.yaml
traffic-sim compare --config configs/piere_revision_addendum_1800.yaml
traffic-sim compare --config configs/piere_revision_addendum_3600.yaml
traffic-sim compare --config configs/piere_perception_sensitivity_expanded.yaml
traffic-sim compare --config configs/piere_perception_empirical_errors.yaml
python scripts/rebuild_piere_outputs.py
python scripts/build_piere_dashboard_data.py
python scripts/generate_piere_figures.py
```

The rebuild script recalculates summary statistics and reports from saved run JSON without rerunning the simulations. The dashboard reads the compact `outputs/piere_dashboard_data.json` and never starts an experiment on page load.

## Environment and limitations

Ruff and pytest are part of the revision checks; the complete current test result is recorded in `docs/REVISION_COMPLETION_AUDIT.md`. Docker was unavailable because its daemon could not be reached. Full JSON results remain committed as explicitly requested; GitHub reports warning-size files, so later additions should use compact dashboard data and be assessed before adding further raw traces. The detector evaluation reuses 16 existing images, training provenance and data rights are not established, and no independent holdout set is available.
