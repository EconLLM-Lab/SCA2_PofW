#!/usr/bin/env python3
"""Regenerate the paper's headline tables from published sources.

What this script needs (our model outputs, not WVS/GPS microdata):

  data/phase2/raw/wvs/ksenias_base8/model_option_probabilities.csv
  data/phase2/raw/wvs/co2_8/model_option_probabilities.csv
  DPO_eval_WVS/eval_results_wvs_wave7/model_option_probabilities.csv
  data/phase2/raw/wvs/persona_baseline/model_option_probabilities_persona.csv
  data/phase2/raw/wvs/persona_adapter/model_option_probabilities_*_adapter_persona.csv
  plus the matching population_response_distributions.csv files
  data/phase2/aux/wdi.csv
  data/wvs_eval_full/*_WVS_wave7.parquet   # WVS microdata: obtain from WVSA, not us
  synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json

If the option-probability CSVs are missing locally, this script does **not**
guess a public URL. Set SCA2_EVAL_REMOTE (rclone remote:path) or SCA2_EVAL_URL
(zip of that folder) only after those stores are actually published. Until then
the banks live in gitignored `data/phase2/raw/wvs/` on lab machines.

Adapter *weights* are optional for table regeneration. The Hugging Face repo
`Bonorinoa/SCA2-phase2-adapters` is private. Weights are required only to
re-score new item batteries.

Do NOT publish WVS or GPS microdata. When an eval pack is published, publish
only our option-probability CSVs.

Human composites in script 13 read `data/wvs_eval_full/*_WVS_wave7.parquet`,
rebuilt locally from WVSA files (not shipped).

Committed `analysis/phase2/outputs/unified_construct_bridge.csv` is the git
freeze (adapter trust ρ = 0.78). The working-paper 16×23 trust ρ = 0.80 is a
later matched surface — do not treat a successful regen of 0.78 as matching 0.80.

Run:  env -u PYTHONPATH .venv/bin/python analysis/phase2/reproduce_tables.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "data" / "phase2" / "raw" / "wvs"
PY = REPO / ".venv" / "bin" / "python"

REQUIRED = [
    RAW / "ksenias_base8" / "model_option_probabilities.csv",
    RAW / "co2_8" / "model_option_probabilities.csv",
    REPO / "DPO_eval_WVS" / "eval_results_wvs_wave7" / "model_option_probabilities.csv",
    RAW / "persona_baseline" / "model_option_probabilities_persona.csv",
]


def have_local() -> bool:
    persona = list((RAW / "persona_adapter").glob("model_option_probabilities_*_adapter_persona.csv"))
    return all(p.exists() for p in REQUIRED) and len(persona) == 16


def fetch_remote() -> None:
    remote = os.environ.get("SCA2_EVAL_REMOTE", "").strip()
    url = os.environ.get("SCA2_EVAL_URL", "").strip()
    RAW.mkdir(parents=True, exist_ok=True)
    if remote:
        print(f"rclone copy {remote} -> {RAW}")
        subprocess.check_call(["rclone", "copy", remote, str(RAW), "--progress"])
        return
    if url:
        dest = REPO / "data" / "phase2" / "raw" / "eval_banks.zip"
        print(f"download {url} -> {dest}")
        subprocess.check_call(["curl", "-L", "-o", str(dest), url])
        subprocess.check_call(["unzip", "-o", str(dest), "-d", str(RAW.parent)])
        return
    sys.exit(
        "Missing eval banks. Either place the CSVs listed in the docstring "
        "under data/phase2/raw/wvs/, or set SCA2_EVAL_REMOTE (rclone) or "
        "SCA2_EVAL_URL (zip). Do not fetch WVS microdata from us."
    )


def run(script: str) -> None:
    cmd = [str(PY) if PY.exists() else sys.executable, str(REPO / "analysis" / "phase2" / script)]
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    print("==>", script)
    subprocess.check_call(cmd, cwd=str(REPO), env=env)


def main() -> None:
    if not have_local():
        fetch_remote()
        if not have_local():
            sys.exit("Fetch finished but required CSVs are still missing.")
    run("01_build_unified_eval.py")
    run("13_unified_comparison.py")
    run("17_anchor_permutation_placebo.py")
    run("18_2x2_analysis.py")
    print("OK — compare analysis/phase2/outputs/unified_construct_bridge.csv "
          "and PLACEBO_REPORT.md to the committed copies.")


if __name__ == "__main__":
    main()
