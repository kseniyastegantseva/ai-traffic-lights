# Queue-Aware Traffic Signal Control Initialized from Road Images

**Darya A. Limarenko¹, Kseniya M. Stegantseva¹, Elena Yu. Silantyeva¹**

¹ Information Processing and Control Systems Department (IU5), Bauman Moscow State Technical University, Moscow, Russia

Correspondence: Darya A. Limarenko (dascha.limarenko@gmail.com); Kseniya M. Stegantseva (kseniyastegantseva@gmail.com); Elena Yu. Silantyeva (iu5elena@bk.ru)

## Abstract

A camera-based count can initialize a traffic signal model, but the value of queue feedback depends on demand, signal constraints, and the treatment of vehicles still waiting at the end of a run. We evaluate a deterministic queue-based phase rule against fixed 15-s and 35-s plans, Webster timing, and an aggregate vehicle-actuated proxy at an isolated four-approach intersection. YOLO11s estimates the initial approach counts; SimPy [9] models subsequent arrivals, service, yellow clearance, and queue evolution. Matched Poisson arrival streams are compared over 30 seeds at 1,800-s and 3,600-s horizons across nine demand scenarios. Queue-based control has the lowest mean completed-vehicle wait in several moderate-demand cases, but not at 3 or 9 vehicles/min per approach. At 18 and 24 vehicles/min, it performs substantially worse than the vehicle-actuated and fixed-Webster baselines, with larger queues and more vehicles left waiting. On a reused 16-image diagnostic set, the detector obtains 85.23% vehicle-count accuracy; count-error perturbations modestly increase waiting in most tested regimes. The results support a reproducible evaluation workflow, not a general claim of AI superiority or field readiness.

**Keywords:** traffic signal control; queue feedback; discrete-event simulation; vehicle detection; paired experiment

## 1. Introduction

Fixed-time signal plans allocate green without observing current queues. Webster timing improves the split for an assumed demand profile [2], while traffic-responsive and learning-based controllers use measurements or state feedback [1, 3–6]. Any comparison depends on a valid baseline and on consistent signal and vehicle accounting. This study tests whether a simple queue-based rule reduces mean waiting relative to fixed-time and responsive alternatives when every controller receives the same arrivals. The hypothesis is conditional: direct queue feedback can help when demand is within capacity, but it need not remain effective under overload. Unlike a comparison against only an unresponsive fixed cycle, the design includes both a demand-calibrated Webster split and a queue-actuated proxy, so any improvement must exceed established fixed and responsive alternatives.

The contribution is a reproducible assessment of an image-initialized, single-intersection prototype. YOLO11s supplies counts for four approach zones; a deterministic heuristic selects between two conflicting phases. It is not a trained reinforcement-learning policy. The experiments isolate control effects with matched arrival events, bounded green times, explicit yellow intervals, and separate records for waiting, in-service, and departed vehicles.

## 2. System and simulation model

The workflow in Fig. 1 treats one image as an initial-state estimate. Vehicles detected in each approach zone are assumed to be waiting; the system does not track video or infer their prior delay. SimPy [9] then generates arrivals and service events. North–south and east–west are mutually exclusive phases. Each approach has a waiting queue; a vehicle starts service only during green and departs after a 2-s headway. A phase change includes 3 s of yellow: an existing service may finish, but no new service starts. The controller is evaluated once per second. The image-to-simulation path can use detected counts as initial queues, but the reported paired demand matrix starts with empty queues; perception metrics and the operational image-initialization path are evaluated separately. The sensitivity series perturbs the controller's queue observations under shared physical arrivals. This separation prevents detector errors from being conflated with the main comparison of phase policies. At an integer-time tie, the phase decision is processed before a new service start. This ordering prevents a vehicle from entering service on a phase that has just changed. Arrival events are generated from each configured piecewise-constant rate and reused across controllers within a paired seed.

![Image-to-simulation workflow](figures/figure_01_system_architecture.png)

*Fig. 1. Approach counts from an image initialize the queues in the discrete-event signal model.*

The simulation covers the half-open interval [0,T). A service completing at T is not counted as a departure. Initial vehicles enter at time zero with no assumed pre-observation delay. Vehicle conservation is checked for every run:

**(1)** N₀ + A(T) = D(T) + Q(T) + B(T), where N₀ is the initial queue count, A is subsequent arrivals, D is departures, Q is the waiting queue, and B is vehicles in service.

Waiting for a vehicle arriving at a_i and starting service at s_i is W_i=s_i−a_i. The reported mean uses vehicles whose service completes before T:

**(2)** W̄=(1/N_d)Σ_{j:d_j<T}(s_j−a_j).

The time-average queue and throughput are

**(3)** Q̄=(1/T)∫₀ᵀQ(t)dt;  X=3600D(T)/T vehicles/h.

Unfinished waiting and service are retained at T; mean completed-vehicle wait is therefore interpreted beside throughput, queue area, and residual waiting, especially under overload. This distinction matters because vehicles with the longest waits are also the ones most likely to remain unfinished at the horizon.

## 3. Controllers and experimental design

The fixed baselines hold green for 15 s or 35 s, followed by yellow. Fixed-Webster timing [2] estimates critical flow ratios from configured mean rates and allocates effective green in an optimized two-phase cycle. It computes y_NS=max(v_N,v_S)/s and y_EW=max(v_E,v_W)/s, with saturation flow s=30 vehicles/min. The cycle and effective green allocation are

**(4)** C₀=(1.5L+5)/(1−Y),  Y=y_NS+y_EW;  g_a=(C₀−L)y_a/Y,

where L is two-phase lost time and a denotes either axis. Green is bounded to 8–45 s; for a non-operational Webster estimate it uses an equal split within those bounds. This split is fixed for a scenario and cannot respond to a later demand change.

The vehicle-actuated policy extends green while the active queue is nonempty. It may end the phase after a 3-s empty gap if the competing phase has a request; minimum and maximum greens are 8 s and 45 s. Since the model has no detector passage headways, this policy is an aggregate-queue proxy. The queue-based heuristic switches after the 8-s minimum if the competing queue exceeds the active queue by more than one vehicle. It also switches at 45 s when the competing phase has a request. Neither responsive policy is a learned AI model.

Arrivals follow configured piecewise-constant Poisson rates. Every controller in a scenario/seed pair receives the same generated event list, verified by a stored SHA-256 digest. The original matrix contains 900 runs per horizon (five scenarios × 30 seeds × six controller configurations). The addendum contains 720 runs per horizon (four additional scenarios × 30 new seeds × six configurations). The original five scenarios and four addendum scenarios were run with 30 seeds and 1,800-s and 3,600-s horizons: symmetric 6/min, asymmetric N/S 10/4, variable demand, a dominant-axis switch at 900 s, 18/min high load, symmetric 3/min, symmetric 9/min, mirrored E/W 4/10, and 24/min. The original high-load series retains its name. Each scenario uses the same four approach rates for all seeds; variable demand changes from 6/min on every approach to 3/min north/south and 12/min east/west at 900 s, while the dominance-switch case reverses 10/4 to 4/10. Alongside the five primary controllers, the generated records retain a legacy queue-based variant as an implementation reproducibility check; it is not shown in the main comparison table. The primary comparisons include fixed 15 s, fixed 35 s, fixed-Webster, vehicle-actuated, and queue-based control.

With a 2-s discharge headway, saturation flow is 30 vehicles/min during green. Under an equal 35-s split with two 3-s yellow intervals, approximate per-approach capacity is c ≈ 30×35/(2×35+2×3) = 13.82 vehicles/min. Thus 9/min is below this estimate (v/c≈0.65); 18/min (≈1.30) and 24/min (≈1.74) exceed it. These are model-based estimates, not field capacity measurements.

The estimated per-approach capacity and demand ratio are

**(5)** c_i≈s g_i/C;  ρ_i=v_i/c_i,

where g_i/C is the allocated green share. At 18/min and 24/min, observed queue growth and residual demand confirm overload behavior inside this configured model; they do not calibrate a physical junction.

For the primary contrast, the seed-level difference is Δ_r=W̄_queue,r−W̄_baseline,r. We report its mean and 95% Student-t interval: **(6)** Δ̄ ± t_{0.975,n−1}s_Δ/√n. A two-sided exact paired sign test assesses the direction of differences; Holm's step-down adjustment covers five comparator tests within each scenario/horizon family. No warm-up is removed: the estimand is the transient from an initially empty system or image-derived queue, not steady-state performance.

## 4. Perception evaluation

Inference used Ultralytics 8.4.129 and PyTorch 2.7.1 on CPU at 1280-pixel input size. Direct single-scale runs used confidence 0.03. The production path proposed full-frame boxes at 0.01, applied a 0.03 vehicle filter, and merged crop detections with duplicate suppression. The VisDrone checkpoint detects car, motorcycle, bus, and truck classes. Evaluation was rerun on 16 annotated images containing 643 vehicles and 64 image–approach counts. Vehicle-count accuracy is VCA = max(0, 1 − Σ|ŷ−y|/Σy); directional MAE is the absolute count error per image–approach pair. The production pipeline predicted 684 vehicles, with VCA 85.23% and MAE 1.484 (Table I). A direct single-scale VisDrone run reached 85.38% and 1.469; the full-frame production path alone reached 86.16% and 1.391. Direct COCO-pretrained YOLO11s reached 38.88% and 6.141 on the same images. Because the inference paths differ, the small differences among VisDrone variants are pipeline comparisons, not isolated effects of model weights. Adding x2 or x3 crop detections separately with non-maximum suppression produced VCA 85.38%; combining both scales in the production path produced 85.23%. Without duplicate suppression, crop combinations predicted 1,424–2,150 vehicles and VCA fell to zero. This ablation shows that overlapping detections can dominate aggregate counts; it does not establish an independently validated optimal threshold.

*Table I. Directional counts on the 16-image diagnostic set.*
| Approach | Reference | Predicted | Absolute error |
|---|---:|---:|---:|
| North | 189 | 206 | 17 |
| South | 155 | 147 | 8 |
| East | 119 | 134 | 15 |
| West | 180 | 197 | 17 |
| Total | 643 | 684 | 95 |

These are count metrics, not object-level precision, recall, or mAP; bounding-box labels are unavailable. The same small image set has been used before and is not an independent holdout. Training provenance, unseen-scene generalization, and data/model redistribution rights remain unverified. YOLO11 is cited as software because no formal YOLO11 paper is listed by its maintainers [7]; the VisDrone benchmark is described in [8].

Figure 2 shows one example of the production detector output and approach count annotations. The experiment evaluates aggregated counts rather than box-level matching.

![YOLO11s detection example](figures/perception_example_test_06.jpg)

*Fig. 2. VisDrone predictions and approach zones on diagnostic image 06; ground-truth/predicted counts are N 15/10, S 10/9, E 7/8, and W 10/11.*

The sensitivity analysis separates perception perturbations from physical arrivals. With synthetic 0–20% count errors, queue-based mean wait at 20% versus 0% rose by 0.03 s (95% paired interval −0.06 to 0.13) in symmetric demand, 0.41 s (0.30–0.52) in asymmetric demand, 0.28 s (0.15–0.40) under variable demand, 0.31 s (0.21–0.41) after a dominance switch, and 1.66 s (−0.38 to 3.71) at high load. Synthetic errors are applied at controller observations, not to the physical queue or arrivals: at each decision, each queued vehicle is missed, duplicated by one, or observed correctly according to a seeded draw. A separate bootstrap of signed directional residuals from the same images raised mean wait by 0.54–2.71 s in four regimes; the high-load change was 0.43 s (95% interval −1.29 to 2.14). The bootstrap resamples 16 observed residuals independently over time. Both perturbations are diagnostic and are not calibrated deployment-error estimates.

Figure 3 summarizes the synthetic observation-error sensitivity across demand regimes.

![Queue-based wait under synthetic count errors](figures/figure_08_perception_sensitivity.png)

*Fig. 3. Queue-based mean wait by synthetic observation-error rate and demand regime; bars show 95% intervals.*

## 5. Results and discussion

Table II gives mean completed-vehicle wait at 3,600 s for all five primary controllers. Each cell is the mean of 30 matched seeds. Queue-based control is competitive under asymmetric and changing demand but is not uniformly best. Vehicle-actuated control has lower mean wait at 3/min and 9/min; at 24/min, it has the lowest mean (721.53 s), narrowly below Webster (724.44 s) and well below queue-based control (913.02 s). Table values are rounded to two decimals.

*Table II. Mean completed-vehicle waiting time in seconds at T=3,600 s (n=30 seeds).*
| Demand scenario (veh/min per approach) | Fixed 15 | Fixed 35 | Webster | Actuated | Queue-based |
|---|---:|---:|---:|---:|---:|
| Symmetric 6 | 8.16 | 14.22 | 6.64 | 6.11 | 6.04 |
| Asymmetric N/S 10/4 | 11.05 | 16.63 | 7.32 | 6.59 | 6.47 |
| Variable | 18.88 | 20.73 | 28.89 | 6.61 | 6.41 |
| Dominance switch | 11.34 | 16.75 | 127.99 | 6.64 | 6.48 |
| High load 18 | 469.82 | 389.21 | 375.96 | 371.36 | 630.22 |
| Symmetric 3 | 6.92 | 12.35 | 5.20 | 4.35 | 5.41 |
| Symmetric 9 | 10.58 | 16.70 | 10.58 | 9.35 | 10.28 |
| Asymmetric E/W 4/10 | 11.02 | 16.57 | 7.34 | 6.55 | 6.38 |
| Oversaturated 24 | 797.60 | 735.35 | 724.44 | 721.53 | 913.02 |


The paired queue-based minus vehicle-actuated differences confirm small gains in some cases and clear losses in others (Table III). The interval for the paired mean difference is

**(6)** Δ̄ ± t_{0.975,n−1}s_Δ/√n.

The sign test evaluates whether paired differences favor one controller more often, not the size of the effect. Holm adjustment controls the familywise error across the five comparisons. At 6/min the interval includes zero. The N/S asymmetric, variable, dominance-switch, and E/W cases show negative point estimates, although the E/W difference is not significant after correction. The queue heuristic loses at 3 and 9/min and by 258.86 s at 18/min. At 24/min its mean wait is 191.49 s higher. The 24/min scenario is explicitly separated from the 18/min high-load scenario; both exceed the equal-split capacity estimate, but the larger arrival rate produces a more severe residual queue. At 1,800 s, the queue-based means are 6.00 s for symmetric 6/min and 315.60 s for 18/min. In the latter, queue-based wait is 124.27 s above vehicle-actuated (95% interval 121.22–127.32), consistent with the 3,600-s loss. The longer horizon therefore does not reverse the overload ranking. These paired outcomes preserve the adverse result rather than attributing it to random arrival differences.

*Table III. Paired queue-based minus vehicle-actuated mean-wait differences at 3,600 s.*
| Scenario | Pairs | Δ wait (s) | 95% CI (s) | Holm p |
|---|---:|---:|---:|---:|
| Symmetric 6 | 30 | −0.07 | [−0.16, 0.02] | 0.856 |
| Asymmetric N/S 10/4 | 30 | −0.12 | [−0.20, −0.05] | 0.005 |
| Variable | 30 | −0.21 | [−0.31, −0.10] | <0.0001 |
| Dominance switch | 30 | −0.17 | [−0.25, −0.08] | 0.001 |
| High load 18 | 30 | +258.86 | [+255.11, +262.60] | <0.0001 |
| Symmetric 3 | 30 | +1.06 | [+0.99, +1.13] | <0.0001 |
| Symmetric 9 | 30 | +0.93 | [+0.77, +1.09] | <0.0001 |
| Asymmetric E/W 4/10 | 30 | −0.17 | [−0.26, −0.09] | 0.099 |
| Oversaturated 24 | 30 | +191.49 | [+188.45, +194.53] | <0.0001 |


Figure 4 compares the controller means and intervals across all nine demand scenarios.

![Controller waiting-time comparison](figures/figure_03_controller_comparison.png)

*Fig. 4. Mean waiting by controller across nine demand scenarios; intervals are 95% t intervals.*

At 1,800 s, queue-based mean wait was 6.00 s in symmetric demand, 6.43 s in N/S asymmetry, 6.17 s in variable demand, and 6.49 s after the dominance switch. In symmetric demand it was 8.13 s lower than fixed-35, 0.61 s lower than Webster, and 0.11 s lower than vehicle-actuated; the last paired interval crossed zero and was not significant after Holm adjustment. At 3,600 s, its mean wait was 6.04 s for symmetric 6/min and 6.47–6.48 s for the two asymmetric and dominance-switch cases.

The Webster split is based on configured mean rates. It cannot adapt to a sudden change after 900 s; its mean wait rises to 127.99 s in the dominance-switch case. Queue feedback and vehicle actuation respond to current queues and remain near 6.5 s in that scenario. Conversely, at low and moderate symmetric demand, vehicle-actuated has a lower mean than queue-based, so the queue rule has no universal advantage.

At overload, completed-vehicle mean wait understates the burden because many arrivals remain in the queue. The model does not attribute this loss to one controller mechanism. A plausible explanation is frequent switching while both queues remain nonempty, which increases lost yellow time, but phase-history outcomes were not analyzed to test that mechanism. At 18/min, queue-based control has a mean queue of 755 vehicles and 1,505 waiting at T, compared with 445 and 872 under vehicle-actuated control. At 24/min the corresponding values are 1,457 and 2,907 for queue-based, versus 1,150 and 2,289 for vehicle-actuated. Throughput is also lower under queue-based control: 2,799 vs 3,432 vehicles/h at 18/min and 2,822 vs 3,440 at 24/min.

Figure 5 compares completed-vehicle waiting with mean and residual queues in the two overload scenarios.

![Overload and residual-queue comparison](figures/figure_10_overload_and_censoring.png)

*Fig. 5. Completed-vehicle wait, mean queue, and residual waiting at 18 and 24 vehicles/min per approach.*

## 6. Limitations and conclusion

The model covers an isolated two-phase intersection with Poisson arrivals, fixed 2-s service, and a one-second decision step. It omits turning movements, platoons, pedestrian calls, lane changes, spillback, and downstream blocking. The actuated baseline uses queue emptiness as a gap proxy. The image count assumes vehicles in each approach zone are waiting; prior delay is unknown. The detector evaluation uses 16 previously seen images without bounding-box labels or verified training lineage. None of these experiments establishes field capacity, unseen-scene accuracy, or deployment performance.

Queue feedback can reduce completed-vehicle waiting in some asymmetric and changing-demand cases, but vehicle-actuated control is as good or better in several sub-capacity cases. Under the 18- and 24-vehicle/min workloads, queue-based control leaves substantially more vehicles waiting and serves fewer vehicles per hour. The study's contribution is a matched-seed, event-audited comparison that includes those losses, right-censored vehicles, and perception perturbations. The results motivate independent image evaluation and richer traffic models before field trials; they do not support a claim that a deterministic queue heuristic is a generally superior AI controller.

## References

[1] M. Papageorgiou, C. Diakaki, V. Dinopoulou, A. Kotsialos, and Y. Wang, “Review of road traffic control strategies,” *Proceedings of the IEEE*, 91(12), 2043–2067, 2003. doi: 10.1109/JPROC.2003.819610.

[2] F. V. Webster, *Traffic Signal Settings*, Road Research Technical Paper No. 39. London: Her Majesty’s Stationery Office, 1958.

[3] P. Mirchandani and L. Head, “A real-time traffic signal control system: Architecture, algorithms, and analysis,” *Transportation Research Part C*, 9(6), 415–432, 2001. doi: 10.1016/S0968-090X(00)00047-4.

[4] B. Abdulhai, R. Pringle, and G. J. Karakoulas, “Reinforcement learning for true adaptive traffic signal control,” *Journal of Transportation Engineering*, 129(3), 278–285, 2003. doi: 10.1061/(ASCE)0733-947X(2003)129:3(278).

[5] M. Noaeen et al., “Reinforcement learning in urban network traffic signal control: A systematic literature review,” *Expert Systems with Applications*, 199, 116830, 2022. doi: 10.1016/j.eswa.2022.116830.

[6] H. Wei, G. Zheng, H. Yao, and Z. Li, “IntelliLight: A reinforcement learning approach for intelligent traffic light control,” in *Proc. 24th ACM SIGKDD*, 2018, pp. 2496–2505. doi: 10.1145/3219819.3220096.

[7] G. Jocher and J. Qiu, *Ultralytics YOLO11*, v. 11.0.0, 2024. https://docs.ultralytics.com/models/yolo11/.

[8] P. Zhu et al., “VisDrone-DET2018: The vision meets drone object detection in image challenge results,” in *Computer Vision – ECCV 2018 Workshops*, LNCS 11133, pp. 437–468, 2019. doi: 10.1007/978-3-030-11021-5_27.

[9] SimPy Developers, *SimPy*, v. 4.1.2, 2026. https://pypi.org/project/simpy/4.1.2/.
