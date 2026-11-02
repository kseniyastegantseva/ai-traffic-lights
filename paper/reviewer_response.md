# Draft response to reviewers — verification required

**Important:** the original reviewer report was not present among the accessible files. The attached task mentioned seven major and four minor comments but did not include their wording. The eleven items below are therefore a provisional response map synthesized from the old article and the task specification; they are not represented as the reviewer's actual comments. Reconcile every item with the original report before submission.

## Major comments (provisional topics)

### Major 1 — Signal safety and yellow clearance

**Response:** We revised the SimPy service and phase logic so a phase change enters a yellow interval, the conflicting axis remains red during that interval, and new service starts require green. An already-started service may finish during yellow.

**Location/evidence:** `src/traffic_light/simulation.py` records phase transitions in `phase_history`; `tests/test_simulation.py` checks that a yellow transition precedes the next green. **Status: implemented and verified; 52 tests passed, and all 1800 saved full-series phase histories were audited.**

### Major 2 — Service timing and vehicle conservation

**Response:** Vehicles now move through waiting, in-service, and departed states. Departure is recorded after the service interval; an unfinished service at the horizon remains in-service. Every run asserts `initial + arrived = departed + waiting + in_service`.

**Location/evidence:** `src/traffic_light/simulation.py`, result fields `waiting_at_end`, `in_service_at_end`, and `vehicles_departed`; regression test in `tests/test_simulation.py`. **Status: implemented and verified; all full-series runs satisfy vehicle conservation.**

### Major 3 — Queue initialization and experiment reproducibility

**Response:** Initial queues are accepted by the model and YAML scenario. Seeded Poisson arrival events are explicitly generated and their SHA-256 digest is stored in every result. Initial vehicles are present at time zero; unobserved prior delay is excluded.

**Location/evidence:** `src/traffic_light/simulation.py`, `src/traffic_light/config.py`, `configs/piere_revision_1800.yaml`. **Status: implemented and verified; all scenario/seed groups share the same stream hash across controllers.**

### Major 4 — Controller baselines and bounded waiting

**Response:** Added separate `fixed_15`, `fixed_35`, fixed-Webster, vehicle-actuated, revised queue-based, and legacy queue-based configurations. Adaptive policies have a maximum green when the competing phase has a request. Webster's formula, bounds, and fallback are described in the revised manuscript.

**Location/evidence:** `src/traffic_light/controllers.py`, `src/traffic_light/experiments.py`, revision YAML configurations, and results in `paper/simulation_results.md`. **Status: implemented and compared in both full horizons.** The vehicle-actuated gap is an aggregate-queue proxy, not detector passage-headway logic.

### Major 5 — Demand scenarios and overload validity

**Response:** The earlier 9 veh/min/approach scenario is renamed `high_load`. A rough capacity estimate using the configured 2 s discharge time gives about 13.82 veh/min/approach under equal fixed_35 allocation, so 9 veh/min is not an overload. Added an 18 veh/min candidate overload and piecewise demand/sudden-dominance scenarios.

**Location/evidence:** `docs/INITIAL_AUDIT.md`, revision configurations, and `paper/simulation_results.md`. **Status: confirmed for this model configuration:** queue-based residual queues increase from a mean 758 to 1505 over the two horizons; fixed and actuated baselines also accumulate queues. This does not establish field capacity.

### Major 6 — Statistical evidence and revised numerical claims

**Response:** Added a paired comparison by scenario, horizon, and seed; 95% t intervals for mean paired differences; exact two-sided sign tests; and Holm correction. The old reported improvements are explicitly excluded from the revised draft.

**Location/evidence:** `src/traffic_light/experiments.py`, `paper/revised_manuscript.md`, and `paper/simulation_results.md`. **Status: complete for the configured runs; results show mixed performance, including a clear queue-based loss under high load.**

### Major 7 — Perception validity and control integration

**Response:** The manuscript now distinguishes aggregate Vehicle Count Accuracy from object-detection precision, recall, and mAP. A reproducible synthetic observation-error mechanism perturbs only the controller's view; physical queues remain unchanged.

**Location/evidence:** `src/traffic_light/simulation.py`, `src/traffic_light/interactive.py`, `app/dashboard.py`, `configs/piere_perception_sensitivity.yaml`, and `paper/simulation_results.md`. Existing repository artifacts report 16 images, 643 actual counts, 95 absolute directional errors, 85.23% Vehicle Count Accuracy, and MAE 1.484 vehicles per approach-image. Synthetic sensitivity metrics were identical over 0–20% error in the tested symmetric case. The dashboard now feeds its four image counts into the SimPy model as initial queues. **Status: model path and UI contract are tested; live YOLO inference, checkpoint provenance, ablations, and annotation remain unverified.**

## Minor comments (provisional topics)

### Minor 1 — Metric definitions and right-censoring

**Response:** The draft now defines waiting time, queue area, horizon semantics, and treatment of incomplete service. Completed-vehicle wait is separated from observed delay for vehicles still in the system.

**Location/evidence:** `src/traffic_light/simulation.py`, `docs/INITIAL_AUDIT.md`, `paper/revised_manuscript.md`. **Status: definitions and tests verified; 52 tests passed.**

### Minor 2 — Reproducible configurations and outputs

**Response:** Added quick, 1800 s, 3600 s, and perception-sensitivity YAML configurations with explicit seeds and output locations.

**Location/evidence:** revision configurations and ignored `outputs/` JSON. **Status: quick, both full horizons, and sensitivity CLI runs completed. Outputs are not committed due to size; compact tabulations and reproduction commands are in `paper/simulation_results.md`.**

### Minor 3 — Scope of the camera-based claim

**Response:** The revised draft states that one image provides an initial count under an explicit queue-zone assumption; it does not imply continuous video tracking or field deployment.

**Location/evidence:** `paper/revised_manuscript.md`, `wiki/architecture.md`, `src/traffic_light/interactive.py`, and dashboard tests. **Status: four detector counts now initialize the revised SimPy model; no continuous video or live inference validation is claimed.**

### Minor 4 — Bibliography and review traceability

**Response:** The manuscript does not repeat the old reference list as independently verified. The original reviewer report was not available, so actual comment wording and mapping cannot be confirmed.

**Location/evidence:** this response file, `paper/revised_manuscript.md`, and `paper/references_audit.md`. **Status: selected citations in the revised manuscript were checked against publisher, conference, software-maintainer, and catalog records. The old list was curated rather than copied wholesale. Exact comment wording remains unresolved because the original reviewer report was not available.**
