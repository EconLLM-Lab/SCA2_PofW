"""Sequential Phase-1 queue. Durable resume before compute; stop on ANY fatal failure."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from sca2_workbench.cohort import PACKAGE, check_prefix
from sync import restore, upload_unit


def plan(pilot, reg, items):
    """Pilot = base + ARG x every item (ARG is a non-USA adapter); full = every model x every item."""
    if pilot:
        return ["base", "ARG"], items
    return [x["key"] for x in reg["models"]], items


def check_cu_budget(elapsed_seconds, cu_per_hour, max_cu):
    """Abort between units once queue compute time costs more than the cap (None = no cap)."""
    if max_cu is not None and elapsed_seconds / 3600 * cu_per_hour > max_cu:
        raise RuntimeError(f"ABORT CU cap {max_cu} exceeded after {elapsed_seconds:.0f} s at {cu_per_hour} CU/h")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--frozen", type=Path, required=True)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--unit-seconds", type=float, required=True, help="expected A100 per adapter/item from estimate; abort at 2x")
    ap.add_argument("--base-seconds", type=float, required=True)
    ap.add_argument("--pilot", action="store_true", help="base + ARG on all items; required before full scale")
    ap.add_argument("--max-cu", type=float, help="abort between units once queue time exceeds this many CU")
    ap.add_argument("--cu-per-hour", type=float, default=13.08, help="planning rate; read the real one in Colab")
    args = ap.parse_args()
    check_prefix(args.prefix)
    if not os.environ.get("HF_TOKEN"):
        raise ValueError("set HF_TOKEN from a Colab secret")
    args.output.mkdir(parents=True, exist_ok=True)
    restore(args.output, args.prefix)
    reg = json.loads((PACKAGE / "models.json").read_text())
    items = json.loads((PACKAGE / "items.json").read_text())["items"]
    keys, items = plan(args.pilot, reg, items)
    if not args.pilot and not (args.output / "PILOT_VERIFIED.json").exists():
        raise ValueError("pilot verification missing; run --pilot first and inspect the remote pilot")
    started = time.monotonic()
    for key in keys:
        for item in items:
            check_cu_budget(time.monotonic() - started, args.cu_per_hour, args.max_cu)
            budget = args.base_seconds if key == "base" else args.unit_seconds
            cmd = [sys.executable, str(PACKAGE / "runner" / "unit.py"), "--model", key,
                   "--item", item["item_id"], "--weights", "nf4_dequant", "--dtype", "float64",
                   "--device", "cuda", "--output", str(args.output), "--frozen", str(args.frozen),
                   "--timeout", str(2 * budget)]
            print("UNIT_START", key, item["item_id"], flush=True)
            rc = subprocess.run(cmd, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
            marker = args.output / "units" / f"nf4_dequant_float64_{key}_{item['item_id']}.json"
            # A failing gate must also be banked before aborting. OOM has attempt logs only.
            if marker.exists():
                for attempt in range(3):
                    try:
                        upload_unit(args.output, marker, args.prefix)
                        break
                    except Exception:
                        if attempt == 2:
                            raise
                        time.sleep(2 ** (attempt + 1))
            if rc != 0:
                raise RuntimeError(f"ABORT unit rc={rc}: {key}/{item['item_id']}; do not continue cohort")
            if not marker.exists() or not json.loads(marker.read_text())["pass"]:
                raise RuntimeError("ABORT missing or failed completion marker")
    if args.pilot:
        (args.output / "PILOT_VERIFIED.json").write_text(json.dumps({"prefix": args.prefix, "pass": True}))
        from huggingface_hub import HfApi, hf_hub_download
        from sca2_workbench.cohort import digest
        commit = HfApi().upload_file(repo_id="Bonorinoa/SCA2-paper-b-artifacts", repo_type="dataset",
                                    path_or_fileobj=args.output / "PILOT_VERIFIED.json",
                                    path_in_repo=args.prefix + "/exports/PILOT_VERIFIED.json")
        remote = hf_hub_download("Bonorinoa/SCA2-paper-b-artifacts",
                                 args.prefix + "/exports/PILOT_VERIFIED.json",
                                 repo_type="dataset", revision=commit.oid)
        if digest(remote) != digest(args.output / "PILOT_VERIFIED.json"):
            raise ValueError("remote pilot marker digest mismatch")
    print("PILOT_DONE" if args.pilot else "COHORT_DONE", flush=True)


if __name__ == "__main__":
    main()
