"""Real Mac dry run: baseline, SIGKILL during layer 8, resume, compare immutable bytes."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from sca2_workbench.cohort import PACKAGE, digest, json_bytes, publish, update_index


def run_checked(cmd):
    start = time.monotonic()
    rc = subprocess.run(cmd).returncode
    print("COMMAND_EXIT", rc, "seconds", round(time.monotonic() - start, 3), json.dumps(cmd), flush=True)
    if rc:
        raise RuntimeError(f"command failed: {rc}")
    return time.monotonic() - start


def inventory(root):
    files = sorted(root.glob("*.json")) + sorted(root.glob("*.bin")) + sorted((root / "units").glob("*.json"))
    return {str(p.relative_to(root)): digest(p) for p in files}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="ARG")
    ap.add_argument("--item", default="wvs_Q57")
    ap.add_argument("--weights", choices=["nf4_dequant", "unquantized"], default="nf4_dequant")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--publish-viewer", action="store_true")
    args = ap.parse_args()
    base, killed = args.out / "baseline", args.out / "resumed"
    if base.exists() or killed.exists():
        raise ValueError("verification requires new directories; preserve previous evidence")
    common = [sys.executable, str(PACKAGE / "runner" / "unit.py"), "--model", args.model,
              "--item", args.item, "--weights", args.weights, "--dtype", "float64", "--device", "cpu",
              "--frozen", str(PACKAGE / "local_nf4"), "--timeout", "900"]
    base_wall = run_checked(common + ["--output", str(base)])
    # Supervisor stays alive to reap the model child and capture its real SIGKILL status.
    p = subprocess.Popen(common + ["--output", str(killed), "--pause-after-layer", "8"])
    start, victim = time.monotonic(), None
    while p.poll() is None:
        logs = list((killed / "attempts").glob("*.log"))
        if logs and "PAUSE_FOR_KILL" in logs[0].read_text(errors="replace"):
            children = psutil.Process(p.pid).children()
            if len(children) != 1:
                raise RuntimeError("expected exactly one model child")
            victim = children[0].pid
            os.kill(victim, signal.SIGKILL)
            break
        if time.monotonic() - start > 300:
            raise RuntimeError("kill checkpoint not reached")
        time.sleep(.1)
    killed_exit = p.wait(timeout=30)
    if victim is None or killed_exit == 0:
        raise RuntimeError("did not exercise a real mid-capture kill")
    print("KILLED", victim, "supervisor_exit", killed_exit, flush=True)
    resume_wall = run_checked(common + ["--output", str(killed)])
    a, b = inventory(base), inventory(killed)
    if a != b:
        raise AssertionError({"baseline": a, "resumed": b})
    before = inventory(killed)
    run_checked(common + ["--output", str(killed)])
    assert before == inventory(killed), "skip changed immutable bytes"
    if args.publish_viewer:
        exports = PACKAGE.parents[1] / "exports"
        for relative in a:
            if relative != "index.json" and not relative.startswith("units/"):
                publish(exports / relative, (base / relative).read_bytes())
        update_index(exports)
    attempts = [json.loads(p.read_text()) for p in (base / "attempts").glob("*.json") if not p.name.endswith(".rc.json")]
    record = {"pass": True, "model": args.model, "item": args.item, "weights": args.weights,
              "compared_files": len(a), "sha256": a, "killed_exit": killed_exit,
              "baseline_wall_seconds": base_wall, "resume_wall_seconds": resume_wall,
              "attempt": attempts[0], "baseline": str(base.resolve()), "resumed": str(killed.resolve())}
    publish(args.out / "verification.json", json_bytes(record))
    print("BYTE_IDENTICAL", json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
