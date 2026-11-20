#!/usr/bin/env python3
"""Regenerate Paper A headline tables from frozen scores + licensed WVS extracts.

Paper A surface is 16 countries x 23 items (trust adapter-GPS = 0.74).
This script does **not** rerun the older 30-item unified construct table (0.78).

Required for the locked 16x23 adapter numbers:
  paper_a/outputs/paper_a/country_item_scores.csv
  (copied from the September 2026 matched-surface audit; also rebuilt by
  22_paper_a_surface.py if the audit CSV is present)

Required for the 42-country human map:
  data/wvs_eval_full/*_WVS_wave7.parquet   # obtain from WVSA, not us
  data/GPS/GPS_dataset_country_level/country_gps.dta

Model-to-human distance (tvd) is not shipped. It is the committed column when present, otherwise
the file rebuilt by paper_a/tvd_rebuild.py from the WVS + GPS downloads (see DATA.md).

Optional model-output zip (not the source of 0.74):
  SCA2_EVAL_URL=https://drive.google.com/uc?export=download&id=1lIAx0ueSpgaZPmAzNbFSD31ddGQH7Nqo

Adapter weights are optional for table regeneration.

Run:  env -u PYTHONPATH .venv/bin/python paper_a/reproduce_tables.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PY = REPO / ".venv" / "bin" / "python"
PAPER_A = REPO / "paper_a" / "outputs" / "paper_a"


def run(script: str) -> None:
    cmd = [str(PY) if PY.exists() else sys.executable, str(REPO / "paper_a" / script)]
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    print("==>", script)
    subprocess.check_call(cmd, cwd=str(REPO), env=env)


def report_tvd_headline() -> None:
    """Print the model-to-human tvd headline. Uses the committed tvd column if present, else the rebuilt file."""
    sys.path.insert(0, str(REPO / "paper_a"))
    import tvd_rebuild as T

    have_column = False
    if T.SCORES.exists():
        import pandas as pd

        have_column = "tvd" in pd.read_csv(T.SCORES, nrows=1).columns
    if not have_column and not T.OUT_TVD.exists():
        if any(T.WVS_DIR.glob("*_WVS_wave7.parquet")) and T.GPS_DTA.exists():
            print("==> rebuilding tvd (paper_a/tvd_rebuild.py)")
            run("tvd_rebuild.py")
        else:
            sys.exit(T.DATA_MSG)
    tvd = T.load_tvd()
    print("Mean tvd on the strict items (source:", "committed column" if have_column else "rebuilt file", ")")
    for arm, mean in T.headline_means(tvd).items():
        print(f"  {arm:16s} {mean:.4f}")


def main() -> None:
    if not (PAPER_A / "country_item_scores.csv").exists():
        print(
            "Missing frozen Paper A scores at",
            PAPER_A / "country_item_scores.csv",
            file=sys.stderr,
        )
        sys.exit(2)
    run("22_paper_a_surface.py")
    report_tvd_headline()
    print("OK — Paper A lock is paper_a/outputs/paper_a/SURFACE_LOCK.json")
    print("Do not compare that file to unified_construct_bridge.csv (different estimand).")


if __name__ == "__main__":
    main()
