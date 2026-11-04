"""Дополнительные случаи трёх переключений: фиксированные планы, не доказательство."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from traffic_light.rollout_audit import AuditCase, area_discrepancy

rows = []
for fractional in (False, True):
    for seed in range(10):
        case = AuditCase(seed + 500, 3, 2.0, 2.0, 10, (0, 10, 20), 30, fractional)
        result = area_discrepancy(case, eta_rounding="floor")
        if result is None:
            rows.append({"seed": seed, "fractional": fractional, "available": False})
            continue
        pred, actual = result
        rows.append({"seed": seed, "fractional": fractional, "available": True,
                     "max_step_error": max(abs(a-b) for a, b in zip(pred, actual, strict=True)),
                     "sum_error": sum(pred)-sum(actual), "actual_area": sum(actual)})
out = ROOT / "outputs/approach_preview_v2_followup/extra_physics.json"
out.parent.mkdir(parents=True, exist_ok=True)
with out.open("x", encoding="utf-8") as f:
    json.dump(rows, f, indent=2)
print(json.dumps(rows))
