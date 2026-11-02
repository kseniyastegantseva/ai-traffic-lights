# Queue-Aware Traffic Signal Phase Control with Image-Based Initial State Estimation

**Working revision draft.** The original 5-seed percentages are not carried forward because the implementation used for those values had phase, service-completion, and queue-accounting defects. The revised experiments below use 30 seeds and paired arrival streams at two horizons. Detector provenance and the original reviewer report remain unavailable.

## Abstract

This study examines queue-aware phase selection at an isolated four-approach signalized intersection. A camera detector estimates an initial count for each approach, and a discrete-event model represents subsequent arrivals, service, and phase transitions. Thirty-seed paired experiments at 1800 s and 3600 s show that queue-based control lowers mean waiting in the symmetric, asymmetric, and demand-shift cases relative to fixed-time controls, but performs substantially worse in the 18-vehicle/minute-per-approach high-load case. Under high load, queues grow for all controllers; queue-based control leaves more vehicles waiting than the fixed-Webster and vehicle-actuated baselines. A separate symmetric-demand sensitivity series found identical controller outcomes under the tested synthetic observation-error levels from 0% to 20%; this result is limited to the tested demand and perturbation model. The revised model records waiting, in-service, and departed vehicles separately, inserts an exclusive yellow transition, and uses identical seeded arrival events across controller comparisons. The existing 16-image detector evaluation reports Vehicle Count Accuracy of 85.23%, but its training provenance and inference results have not been independently reproduced.

**Keywords:** traffic signal control, queue-based control, discrete-event simulation, vehicle detection, paired experiment

## I. Introduction

Fixed-cycle control allocates green time without responding to the current queue state. A queue-aware controller may reallocate service when demand changes, but its apparent advantage must be assessed under identical arrivals, explicit signal transition rules, and metrics that distinguish served vehicles from vehicles remaining at the end of observation. This revision tests the hypothesis that direct queue feedback changes mean waiting time relative to fixed-time baselines. It does not assume that the adaptive method wins.

The system is a research prototype for a single isolated intersection. Image detection supplies a four-approach initial state. SimPy then represents arrivals and service under a selected controller. The detector is not a continuous video tracker, and an image count is treated as a queue count only under the explicit assumption that vehicles visible in each approach zone are waiting vehicles.

## II. Model and temporal semantics

The state is `S(t) = [q_N(t), q_S(t), q_E(t), q_W(t), p(t)]`, where each `q` is the waiting queue and `p` is the active axis. North–south and east–west are mutually conflicting phases. A vehicle arriving at time `a_i` enters its approach queue. When green permits service, service starts at `s_i` and completes at `d_i = s_i + τ`, where `τ = 2 s` by default. Vehicles already in service may complete during yellow; a new service cannot start during yellow. The yellow interval is 3 s by default.

The simulation horizon is the half-open interval `[0,T)`. A completion at exactly `T` is right-censored and remains `in_service`; it is not counted as a departure. Initial vehicles exist at `t=0`, and their unknown pre-observation waiting is excluded. For every run the conservation identity is

**(1)** `N_initial + N_arrived = N_departed + N_waiting(T) + N_in_service(T)`.

Waiting time for a completed vehicle ends when service starts:

**(2)** `W_i = s_i - a_i`, for vehicles with `d_i < T`.

The reported mean is calculated only over completed vehicles. `observed_delay_seconds` separately accumulates queue delay to service start and the censored delay of vehicles still waiting at `T`; it is not mixed into the completed-vehicle mean. Average queue length is a time integral of waiting vehicles:

**(3)** `Q_mean = (1/T) ∫_0^T Σ_l q_l(t) dt`.

Controller decisions occur once per second. At an integer-time tie, the controller's phase decision is processed before a new service start. Arrivals are generated as independent Poisson processes with configured piecewise-constant rates. A SHA-256 digest of the generated event list is stored with each run so paired controller inputs can be audited.

## III. Controllers

`fixed_15` and `fixed_35` hold each green for 15 s and 35 s, respectively, followed by yellow. These baselines do not use queues for timing.

The fixed Webster baseline estimates critical lane-group flow ratios as `y_NS = max(v_N,v_S)/s` and `y_EW = max(v_E,v_W)/s`, with saturation flow `s = 30 veh/min/lane` implied by the 2 s discharge headway. For `Y = y_NS + y_EW < 0.90`, it uses Webster's optimum cycle estimate

**(4)** `C_0 = (1.5 L + 5)/(1 - Y)`,

where `L` is the two-phase lost time per cycle, then allocates effective green `(C_0 - L)` in proportion to the two critical flow ratios. Greens are bounded by 8 s and 45 s. If `Y ≥ 0.90`, `Y = 0`, or the lost time makes the formula non-operational, the controller uses a documented equal split bounded to 8–45 s. This is a fixed split derived from configured mean rates, not future random arrivals.

`vehicle_actuated` honors an 8 s minimum and 45 s maximum. It extends the active phase while its observed queue remains nonempty, and may gap out after the observed active queue is empty for 3 s while the competing phase has a request. Because the model has no loop-detector passage times, this is an aggregate-queue gap proxy rather than detector-level actuated control.

`queue_based` switches after minimum green when the competing queue exceeds the current queue by more than one vehicle, or when 45 s maximum green is reached and a competing request exists. `queue_based_legacy` retains the previous pressure comparison and switching margin, separately named for reproducibility. Maximum green prevents a waiting competing direction from being postponed indefinitely.

## IV. Demand, capacity, and experimental design

The configured design includes symmetric demand, asymmetric north–south demand, a 900 s demand change, a sudden switch in dominant axis at 900 s, and a high-load case. With 2 s per vehicle, one approach can discharge 30 vehicles/min during green. Under a 35 s green and 3 s yellow for each of two phases, an equal split gives an approximate per-approach capacity `c ≈ 30 × 35/(2 × 35 + 2 × 3) = 13.82 veh/min`. Therefore the earlier 9 veh/min case has an approximate `v/c ≈ 0.65` and is not labelled oversaturated. The 18 veh/min case has approximate `v/c ≈ 1.30`; the final overload claim still requires persistent queue growth and end-of-run residual queues to confirm that control timing does not change the actual capacity ratio.

The full configurations specify 30 seeds and horizons of 1800 s and 3600 s. Every controller in a given scenario/seed receives the same generated arrival list. Parameter values are explicit in YAML; no test-run future arrival stream is used to tune a controller. The complete series was run for all five scenarios and six controller configurations. A separate perception sensitivity configuration holds physical arrivals and queues independent of sensing and applies reproducible count errors of 0%, 5%, 10%, and 20% only to controller observations.

For each scenario and horizon, the primary contrast is `queue_based − comparator` in mean waiting time, paired by seed. A 95% Student-t interval is reported for the mean paired difference. The two-sided exact sign test is used as a distribution-light paired test; Holm's step-down adjustment is applied to the five controller comparisons within each scenario/horizon family. This tests direction of paired differences, not their magnitude.

## V. Perception and system integration

The available repository evaluation reports 16 images, 643 manually counted vehicles, total absolute directional-count error 95, Vehicle Count Accuracy 85.23%, and MAE 1.484 vehicles per approach-image. Vehicle Count Accuracy is defined as `max(0, 1 − Σ_i,l |ŷ_i,l − y_i,l| / Σ_i,l y_i,l)`. It is an aggregate count-error score and is not precision, recall, or mAP. The current output file permits directional error summaries, but YOLO inference has not been rerun in this environment. The training dataset is absent, and the checkpoint's run configuration, random seed, and redistribution rights are not verified.

The 85.23% score cannot be converted directly into a 14.77% independent per-vehicle error probability. The synthetic sensitivity experiment uses a different, explicit perturbation: for each true queued vehicle and decision time, a seeded draw either removes that count, duplicates it by one, or leaves it unchanged, with total perturbation probability equal to the requested rate and equal miss/duplicate probability. This isolates controller sensitivity; it is not calibrated to the detector.

The dashboard passes the four detector counts to the revised SimPy model as initial queues, starts with the axis having the larger initial queue, applies queue-based control, and converts its one-second trace to the existing animation format. This UI simulation has no further arrivals and uses an 8 s minimum and 30 s maximum green. The research experiments use the same physical model with generated arrivals and a 45 s controller maximum. The detector-to-SimPy code path is covered by simulation and dashboard contract tests, but a live YOLO inference was not repeated in this environment; the complete image-to-result path has therefore not been revalidated with the checkpoint.

## VI. Results and limitations

The 1800 s and 3600 s series each contain 900 runs (five scenarios, 30 seeds, six controllers). Across the 150 scenario/seed groups per horizon, all controllers have matching arrival-stream hashes. Every run satisfies the vehicle-conservation identity, and queue time series have one sample per simulated second. Results are summarized with full scenario means and paired intervals in `paper/simulation_results.md`; machine-readable run files are generated at the configured `outputs/` paths and are intentionally not versioned because of their size.

At 1800 s, mean completed-vehicle wait for `queue_based` was 6.00 s in symmetric demand, 6.43 s in asymmetric demand, 6.17 s in variable demand, and 6.49 s after a dominant-axis switch. In symmetric demand it improved on fixed_35 by 8.13 s (95% CI [−8.37, −7.90]) and on Webster by 0.61 s ([−0.77, −0.46]); the comparison with vehicle-actuated was −0.11 s ([−0.24, 0.03]) and was not statistically significant after Holm adjustment. Similar results hold at 3600 s. In high_load, queue-based mean wait was 315.60 s at 1800 s and 630.22 s at 3600 s. It was worse than vehicle-actuated by 124.27 s ([121.22, 127.32]) and 258.86 s ([255.11, 262.60]), respectively, with adjusted `p < 0.001` at both horizons.

The high-load scenario is supported as overloaded in this model: the mean queue-based residual waiting count grew from 758 at 1800 s to 1505 at 3600 s, while mean arrivals grew from 2157 to 4306. Vehicle-actuated control also accumulated residual queues (448 and 872), but served more vehicles and had lower mean wait. These are simulation-specific outcomes under Poisson arrivals, a 2 s service time, and the configured phase logic; they are not field capacity measurements.

Across the 30 paired seeds in the perception-sensitivity series, queue-based waiting-time outcomes were identical at 0%, 5%, 10%, and 20% synthetic observation error; the paired change versus 0% was 0.00 s at each level. This does not establish general robustness: the study used one symmetric demand scenario, and the synthetic miss/duplicate process is not calibrated to the detector. The observed counts can vary while the selected phases and reported performance remain unchanged under this tested scenario.

Limitations include an isolated two-phase intersection, Poisson arrivals in the research scenarios, no turning movements, pedestrian calls, platoons, spillback, lane changes, or downstream blocking; a 1 s controller decision step; aggregate queue rather than detector headway for actuation; and a small image-count evaluation. The dashboard's image count assumes vehicles in each zone represent waiting vehicles. No video tracking or continuous camera control is modeled. The image-to-SimPy interface is implemented, but live inference with the checkpoint and deployment-level visual behavior were not validated here. The original reviewer report and independently verified bibliography were not available.

## References

Bibliographic entries from the original manuscript are not reproduced as verified references in this working draft. DOI, title, venue, and access dates must be independently checked before submission.
