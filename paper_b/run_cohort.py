#!/usr/bin/env python3
"""Paper B — cohort runner: prepare (CPU) then train (GPU) with resume.

Skips countries already prepared / already trained, writes a run manifest, and
logs per-country minutes. Designed to run inside a Colab GPU session; safe to
re-run after any interruption.

Usage (Colab GPU):
  export HF_TOKEN=...
  export SCA2_PB_DATA_ROOT=/content/drive/MyDrive/SCA2_paper_b
  python paper_b/run_cohort.py --wave 1        # first half
  python paper_b/run_cohort.py --wave 2        # second half
  python paper_b/run_cohort.py --countries ARG # pilot
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C

def split_waves(units: list[str]) -> dict[int, list[str]]:
    """Two halves for two concurrent T4 sessions (42 countries -> 21/21, 64 units -> 32/32)."""
    half = (len(units) + 1) // 2
    return {1: list(units[:half]), 2: list(units[half:])}


WAVES = split_waves(list(C.COHORT))


def manifest_path(wave):
    # per-wave manifest: two concurrent sessions must not clobber one index file
    if wave:
        return C.RUN_MANIFEST_FILE.with_name(f"run_manifest_wave{wave}.json")
    return C.RUN_MANIFEST_FILE


def load_manifest(path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:  # never let a partial/concurrent write kill a wave
            return {"protocol": "paper_b frozen 2026-10-09", "countries": {}}
    return {"protocol": "paper_b frozen 2026-10-09", "countries": {}}


def save_manifest(path, m: dict) -> None:
    C.DATA_ROOT.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(m, indent=2))
    tmp.replace(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wave", type=int, choices=[1, 2])
    ap.add_argument("--countries", nargs="*")
    ap.add_argument("--skip-prepare", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="prepare only, do not train")
    a = ap.parse_args()

    if a.countries:
        countries = [c.upper() for c in a.countries]
    elif a.wave:
        countries = WAVES[a.wave]
    else:
        countries = C.COHORT
    bad = [c for c in countries if c not in C.COHORT]
    if bad:
        print(f"refusing unknown: {bad}")
        return 2
    print(f"cohort run: {len(countries)} countries {'(dry-run)' if a.dry_run else ''}")

    C.LOG_DIR.mkdir(parents=True, exist_ok=True)
    mpath = manifest_path(a.wave)
    m = load_manifest(mpath)

    if not a.skip_prepare:
        import subprocess
        cmd = [sys.executable, str(Path(__file__).parent / "prepare_data.py"), "--countries", *countries]
        print(">>> prepare_data:", " ".join(cmd))
        rc = subprocess.call(cmd)
        if rc != 0:
            print(f"prepare failed (rc={rc})")
            return rc

    if a.dry_run:
        print("dry-run: prepared only")
        return 0

    from train_country import train_country  # imported here so prepare-only runs need no torch

    t0 = time.time()
    for i, cc in enumerate(countries, 1):
        rec = m["countries"].get(cc, {})
        out = C.ADAPTER_DIR / cc
        record_path = out / "run_record.json"
        if (out / "adapter_config.json").exists():
            if os.environ.get("SCA2_PB_PROTOCOL") == "bank2":
                recorded = ""
                if record_path.is_file():
                    recorded = json.loads(record_path.read_text()).get("bank_run_id", "")
                if recorded == C.BANK_RUN_ID:
                    print(f"[{i}/{len(countries)}] {cc}: this bank already trained, skip")
                    continue
                print(f"[{i}/{len(countries)}] {cc}: adapter present for a different bank, refusing")
                return 2
            print(f"[{i}/{len(countries)}] {cc}: adapter present, skip")
            continue
        print(f"[{i}/{len(countries)}] {cc}: training...")
        try:
            out = train_country(cc)
            rec = {"status": "done", "adapter_dir": str(out),
                   "run_record": json.loads((out / "run_record.json").read_text())}
        except Exception as e:  # noqa: BLE001 — record and continue the cohort
            rec = {"status": "error", "error": f"{type(e).__name__}: {e}"}
            print(f"  !! {cc}: {rec['error']}")
        m["countries"][cc] = rec
        save_manifest(mpath, m)

    done = sum(1 for r in m["countries"].values() if r.get("status") == "done")
    print(f"\ncohort done: {done} adapters | elapsed {(time.time()-t0)/60:.1f} min")
    save_manifest(mpath, m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
