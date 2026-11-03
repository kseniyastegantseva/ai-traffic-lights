# Total improvement: empty-green development artifacts

This directory contains the first, exploratory stage of the next-generation controller audit.
It does not replace or overwrite earlier PIERE/Queue-based outputs.

## Reproduction

From the repository root in Python 3.12 with the project runtime and development packages:

```bash
python scripts/create_total_improvement_configs.py
traffic-sim compare --config configs/total_improvement_empty_gap_development_1800.yaml
python scripts/analyze_total_improvement_empty_gap.py
python scripts/plot_total_improvement_empty_gap.py
python scripts/audit_queue_based_results.py outputs/total_improvement/empty_gap_development_1800.json --replay-output outputs/total_improvement/empty_gap_development_1800_replay.json
python scripts/audit_queue_based_statistics.py outputs/total_improvement/empty_gap_development_1800.json
python scripts/finalize_total_improvement_artifacts.py
python scripts/audit_queue_based_results.py outputs/total_improvement/empty_gap_development_1800.json.gz
python scripts/audit_queue_based_statistics.py outputs/total_improvement/empty_gap_development_1800.json.gz
```

The simulation used CPU only. Exact package versions and SHA-256 values are recorded in
`environment.json` and `SHA256SUMS.txt`. The published full run log is gzip-compressed; an
uncompressed local copy is ignored by Git. It stores histories without the redundant one-second
queue series; all waits, hashes, phase history, throughput, residual counts and independent replay
metrics are retained.

Seed 2101–2130 are development seeds and are not an independent final-test set after their results
have been examined. See `../../docs/TOTAL_SYSTEM_IMPROVEMENT_AUDIT.md` for interpretation and
limitations.
