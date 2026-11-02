# Provisional response map for author review

The original reviewer letter was not available in the repository or supplied attachments. The topics below summarize the requested revision themes; they are not quotations or a verified reconstruction of the reviewers' comments. Before resubmission, map each response to the original comment and update section/page references from the final conference template.

## Major topics

### 1. Phase safety and service completion

The revised SimPy model has mutually exclusive north–south and east–west phases. Yellow clearance lasts 3 s; service already in progress may finish, but no new service starts during yellow. Vehicles move through waiting, in-service, and departed states. A vehicle is counted as a departure only when its 2-s service completes before the half-open run horizon. Each run satisfies the vehicle-conservation identity. Phase histories and simulation tests support these changes.

### 2. Matched arrivals and reproducibility

Each scenario specifies its demand rates and 30 seeds. Controllers in a scenario/seed pair receive the same generated arrival list; the stored SHA-256 event digest verifies that pairing. Both 1,800-s and 3,600-s horizons are reported. Runs are transient experiments from an initially empty system or stated image-derived initial queues; no warm-up interval is removed.

### 3. Baseline controllers and bounded green

The comparison includes fixed 15-s and 35-s green plans, fixed Webster timing, a queue-actuated gap proxy, and a deterministic queue-based heuristic. The two responsive policies use an 8-s minimum and 45-s maximum green, subject to a competing-phase request. The actuation policy uses aggregate queue emptiness because passage-headway observations are not modeled. Queue-based is not a trained AI policy.

### 4. Demand levels and overload definition

The nine scenarios cover symmetric 3/6/9 vehicles per minute per approach, N/S and mirrored E/W asymmetry, variable demand, a dominant-axis switch, the retained 18/min high-load case, and a separate 24/min oversaturated case. The equal-split capacity estimate is about 13.82 vehicles/min per approach under the specified 2-s discharge and 35-s green/3-s yellow plan. Thus 9/min is below that estimate. Overload conclusions use queue growth, throughput, and residual vehicles as well as completed-vehicle waiting.

### 5. Paired statistical analysis

For each matched seed, the primary contrast is queue-based minus comparator mean waiting. The manuscript reports a 95% Student-t interval for the mean paired difference, a two-sided exact paired sign test, and Holm adjustment across the five comparator tests in each scenario/horizon family. The sign test assesses direction, not effect magnitude. P-values below 0.0001 are reported as ; absent baseline comparisons are not applicable.

### 6. Mixed controller results and censoring

The 3,600-s queue-based mean waits range from 5.41 s at 3/min to 913.02 s at 24/min. Queue-based is competitive in several asymmetric and changing-demand cases, but vehicle-actuated is lower at 3 and 9/min. At 18/min queue-based exceeds vehicle-actuated by 258.86 s; at 24/min by 191.49 s. Residual queues are also larger under queue-based at both overload levels. The manuscript warns that completed-vehicle mean wait excludes vehicles still waiting at the horizon.

### 7. Detector evaluation and scope

The production VisDrone YOLO11s path was reproduced on the same 16 diagnostic images: 643 reference vehicles, 684 predictions, VCA 85.23%, and directional MAE 1.484 across 64 image/approach counts. The manuscript reports aggregate count results rather than precision, recall, or mAP because bounding-box labels are unavailable. The set is small and previously used; it is not an independent holdout. Checkpoint training provenance, unseen-scene performance, and redistribution rights remain unverified.

### 8. Error propagation into control

A corrected 1,200-run experiment perturbs only controller observations at 0%, 5%, 10%, and 20%; physical arrivals and queue states remain unchanged. The paired 20%-versus-0% queue-based mean-wait changes range from +0.02 to +1.66 s, with demand-dependent intervals. A separate 300-run bootstrap resamples observed signed directional count residuals from the same 16 images. It is explicitly diagnostic and does not estimate field performance.

### 9. Contribution and terminology

The revised claim is a reproducible, matched-seed assessment of an image-initialized signal-control prototype. The queue-based policy is described as a deterministic heuristic, not a learned AI controller. Conclusions state that performance depends on demand and that fixed-Webster can respond poorly to a demand shift because its split is fixed.

### 10. Equations, tables, and figures

The manuscript defines vehicle conservation, completed-vehicle waiting, mean queue, capacity ratio, Webster timing, and the paired confidence interval. The compact article retains a system diagram, detector example, perception-sensitivity plot, controller comparison, and overload/censoring plot, along with directional detector counts, controller means for all nine scenarios, and paired queue-based/vehicle-actuated contrasts. The complete set of additional figures and detailed outputs remains in the repository.

### 11. References and final reconciliation

The selected references support signal-control background, Webster timing, YOLO11 software, the VisDrone benchmark, and SimPy. Bibliographic metadata for these entries is recorded in the bibliography audit. The exact original comments and their requested response format still need author reconciliation because the reviewer letter was not supplied.
