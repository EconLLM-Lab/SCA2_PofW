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


HUB_REQUIRED = ("adapter_model.safetensors", "adapter_config.json", "run_record.json")


def plan_unit(bank2: bool, on_hub: bool, local_complete: bool, recorded_bank: str, bank_id: str) -> str:
    """What to do with one unit on resume. On bank 2 the Hub is the truth, not the local disk."""
    if bank2:
        if on_hub:
            return "skip_hub"
        if local_complete:
            return "reupload" if recorded_bank == bank_id else "refuse"
        return "train"
    return "skip_local" if local_complete else "train"


def _list_hub_files() -> list[str]:
    from huggingface_hub import HfApi
    return HfApi().list_repo_files(C.HF_ADAPTER_REPO, repo_type="dataset")


def hub_complete_units(units, cfg=C, lister=_list_hub_files) -> set[str]:
    """Units whose adapter is fully on the Hub (the durable bus; Drive FUSE lags and dies with the VM).

    Fails loudly: a listing error must stop the run, because guessing "nothing is banked"
    would silently retrain finished adapters.
    """
    try:
        files = set(lister())
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"hub listing failed ({type(exc).__name__}: {exc}); refusing to retrain blind") from exc
    return {u for u in units
            if all(f"{cfg.hub_adapter_path(u)}/{n}" in files for n in HUB_REQUIRED)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wave", type=int, choices=[1, 2])
    ap.add_argument("--countries", nargs="*")
    ap.add_argument("--skip-prepare", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="prepare only, do not train")
    a = ap.parse_args(argv)

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

    bank2 = os.environ.get("SCA2_PB_PROTOCOL") == "bank2"   # cohort-1 behaviour is unchanged
    api = pins = None
    on_hub: set[str] = set()
    rep = os.environ.get("SCA2_PB_REPLICATE", "").strip()
    tag = f"replicate_{rep}" if rep else (f"wave{a.wave}" if a.wave else "units")
    if bank2:
        import hub_io
        from huggingface_hub import HfApi
        pins = hub_io.load_pins()
        if pins["relabel_run_id"] != C.BANK_RUN_ID:
            print(f"bank on this machine ({C.BANK_RUN_ID}) is not the pinned bank ({pins['relabel_run_id']}); refusing")
            return 2
        api = HfApi()
        hub_io.write_probe(api, pins["artifacts_repo"], C.BANK_RUN_ID, f"{tag}_{int(time.time())}")
        print("hub write probe ok (state repo)")
        on_hub = hub_complete_units(countries)
        print(f"hub already holds {len(on_hub)} of {len(countries)} units for this bank; they will be skipped")

    t0 = time.time()
    for i, cc in enumerate(countries, 1):
        out = C.ADAPTER_DIR / cc
        record_path = out / "run_record.json"
        recorded = json.loads(record_path.read_text()).get("bank_run_id", "") if record_path.is_file() else ""
        action = plan_unit(bank2, cc in on_hub, (out / "adapter_config.json").exists(), recorded, C.BANK_RUN_ID)
        tagline = f"[{i}/{len(countries)}] {cc}"
        if action == "skip_hub":
            print(f"{tagline}: complete on the Hub, skip")
            continue
        if action == "skip_local":
            print(f"{tagline}: adapter present, skip")
            continue
        if action == "refuse":
            print(f"{tagline}: adapter present for a different bank, refusing")
            return 2
        if action == "reupload":
            print(f"{tagline}: finished locally but not on the Hub; re-uploading instead of retraining")
            try:
                hub_io.upload_adapter(api, C.HF_ADAPTER_REPO, out, C.hub_adapter_path(cc), f"{cc} adapter (re-upload)")
                rec = {"status": "done", "adapter_dir": str(out), "run_record": json.loads(record_path.read_text())}
            except Exception as e:  # noqa: BLE001
                rec = {"status": "error", "error": f"{type(e).__name__}: {e}"}
                print(f"  !! {cc}: {rec['error']}")
        else:
            print(f"{tagline}: training...")
            try:
                out = train_country(cc)
                rec = {"status": "done", "adapter_dir": str(out),
                       "run_record": json.loads((out / "run_record.json").read_text())}
            except Exception as e:  # noqa: BLE001 — record and continue the cohort
                rec = {"status": "error", "error": f"{type(e).__name__}: {e}"}
                print(f"  !! {cc}: {rec['error']}")
        m["countries"][cc] = rec
        save_manifest(mpath, m)
        if bank2:
            hub_io.sync_state(api, pins["artifacts_repo"], C.DATA_ROOT, C.BANK_RUN_ID, tag)

    done = sum(1 for r in m["countries"].values() if r.get("status") == "done")
    print(f"\ncohort done: {done} adapters | elapsed {(time.time()-t0)/60:.1f} min")
    save_manifest(mpath, m)
    if bank2:
        # the exit code must tell the truth: success means every requested unit is on the Hub
        missing = sorted(set(countries) - hub_complete_units(countries))
        hub_io.sync_state(api, pins["artifacts_repo"], C.DATA_ROOT, C.BANK_RUN_ID, tag, strict=True)
        if missing:
            print(f"NOT ON THE HUB after the run: {missing}")
            return 4
        print(f"all {len(countries)} requested units are on the Hub")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
