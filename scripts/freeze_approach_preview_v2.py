"""Заморозка реализации и выбора параметров перед независимым final-запуском.

Записывает ``outputs/approach_preview_v2/FREEZE.json``: SHA-256 исходников
``src/traffic_light``, скриптов v2 и ``development_selection.json``. Запуск final-конфигураций
через ``run_approach_preview_v2.py`` отказывается работать, если хотя бы один хеш изменился.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/approach_preview_v2"
FREEZE = OUT / "FREEZE.json"


def code_hashes() -> dict[str, str]:
    files = sorted((ROOT / "src/traffic_light").glob("*.py")) + sorted(ROOT.glob("scripts/*approach_preview_v2.py"))
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}


def selection_hash() -> str:
    return hashlib.sha256((OUT / "development_selection.json").read_bytes()).hexdigest()


def current_state() -> dict:
    return {"code_sha256": code_hashes(), "development_selection_sha256": selection_hash()}


def verify_freeze() -> None:
    if not FREEZE.exists():
        raise SystemExit("FREEZE.json отсутствует: final нельзя запускать до заморозки реализации.")
    recorded = json.loads(FREEZE.read_text(encoding="utf-8"))
    state = current_state()
    if recorded["code_sha256"] != state["code_sha256"] or (
        recorded["development_selection_sha256"] != state["development_selection_sha256"]
    ):
        raise SystemExit("Код или выбор параметров изменились после заморозки: final-запуск отклонён.")


def main() -> None:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False).stdout.strip()
    payload = {**current_state(), "git_commit_at_freeze": commit,
               "note": "Записано после validation и до первого запуска final."}
    FREEZE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"frozen: {FREEZE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
