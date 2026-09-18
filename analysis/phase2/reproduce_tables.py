#!/usr/bin/env python3
"""Regenerate Paper A headline tables from frozen scores + licensed WVS extracts.

Paper A surface is 16 countries x 23 items (trust adapter-GPS = 0.80).
This script does **not** rerun the older 30-item unified construct table (0.78).

Required for the locked 16x23 adapter numbers:
  analysis/phase2/outputs/paper_a/country_item_scores.csv
  (copied from the September 2026 matched-surface audit; also rebuilt by
  22_paper_a_surface.py if the audit CSV is present)

Required for the 42-country human map:
  data/wvs_eval_full/*_WVS_wave7.parquet   # obtain from WVSA, not us
  data/GPS/GPS_dataset_country_level/country_gps.dta

Optional model-output zip (not required to reprint 0.80):
  SCA2_EVAL_URL=https://drive.google.com/uc?export=download&id=1lIAx0ueSpgaZPmAzNbFSD31ddGQH7Nqo

Adapter weights are optional for table regeneration.

Run:  env -u PYTHONPATH .venv/bin/python analysis/phase2/reproduce_tables.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PY = REPO / ".venv" / "bin" / "python"
PAPER_A = REPO / "analysis" / "phase2" / "outputs" / "paper_a"


def run(script: str) -> None:
    cmd = [str(PY) if PY.exists() else sys.executable, str(REPO / "analysis" / "phase2" / script)]
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    print("==>", script)
    subprocess.check_call(cmd, cwd=str(REPO), env=env)


def main() -> None:
    if not (PAPER_A / "country_item_scores.csv").exists():
        print(
            "Missing frozen Paper A scores at",
            PAPER_A / "country_item_scores.csv",
            file=sys.stderr,
        )
        sys.exit(2)
    run("22_paper_a_surface.py")
    print("OK — Paper A lock is analysis/phase2/outputs/paper_a/SURFACE_LOCK.json")
    print("Do not compare that file to unified_construct_bridge.csv (different estimand).")


if __name__ == "__main__":
    main()
