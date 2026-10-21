"""Local Mac queue: all 43 models x 23 items, one 8B process at a time, no token, no Hub calls.

Resume = hash-checked unit markers in --output. A failing gate is recorded and the queue goes on;
it stops on 3 consecutive failures, RSS > 16 GB, free disk < 40 GB, or a unit over 4x its B0 time.
RUN_STATUS.json is replaced atomically after every unit (the cron watchdog reads it).
"""
import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from sca2_workbench.cohort import PACKAGE, RSS_LIMIT, digest, fetch_inputs, source_digest as current_source_digest
from sca2_workbench.sign_route import load_profiles, profile_of_tag
from sca2_workbench.cohort import unit_tag
from cohort_queue import plan

B0_SECONDS = {"base": 32.5, "adapter": 65.3,   # Mac M4 Pro, float64, benchmark/BENCHMARK.md
              "prompt": 65.0}   # base + sign-profile prompt: 2-unit proof 61.7 s, first 37 units median 63.6 s
WALL_FACTOR = 4
MIN_FREE_BYTES = 40e9
MAX_CONSECUTIVE_FAILURES = 3
WEIGHTS, DTYPE = "nf4_dequant", "float64"


class Terminated(BaseException):
    """SIGTERM arrived (kill <pid>). BaseException so no unit-level handler swallows it."""


@dataclass
class UnitResult:
    rc: int
    wall: float
    peak_rss: float


def wall_limit(key):
    # wall_limit is defined at module level so the test can call it directly
    if isinstance(key, str) and key.startswith("base_sp"):
        return WALL_FACTOR * B0_SECONDS["prompt"]   # longer prompt; the plain-base limit aborted at 36/598
    if key == "base":
        return WALL_FACTOR * B0_SECONDS["base"]
    return WALL_FACTOR * B0_SECONDS["adapter"]


def marker_path(root, key, item_id):
    return Path(root) / "units" / f"{WEIGHTS}_{DTYPE}_{key}_{item_id}.json"


def unit_state(root, key, item_id, source):
    """'done' | 'failed' | None. A marker whose files or source differ is an error, never a skip."""
    marker = marker_path(root, key, item_id)
    if not marker.exists():
        return None
    rec = json.loads(marker.read_text())
    for name, sha in rec["files"].items():
        path = Path(root) / name
        if not path.exists() or digest(path) != sha:
            raise ValueError(f"completion digest mismatch: {name}")
    if rec["inputs"]["source_digest"] != source:
        raise ValueError(f"marker source digest differs from the current source: {marker.name}")
    return "done" if rec["pass"] else "failed"


def write_status(root, status):
    path = Path(root) / "RUN_STATUS.json"
    temp = path.with_name(f".RUN_STATUS.json.{os.getpid()}.tmp")
    with temp.open("w") as f:
        json.dump(status, f, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


@contextmanager
def single_queue(root):
    Path(root).mkdir(parents=True, exist_ok=True)
    with (Path(root) / "queue.lock").open("a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError(f"a queue is already running on {root}") from None
        yield


def run_queue(keys, items, *, root, run_unit, free_bytes, source_digest, pid, total=None, only=None,
              now=time.time):
    root = Path(root)
    units = [(k, i["item_id"]) for k in keys for i in items]
    if only is not None:
        units = [u for u in units if u in only]
    status = {"total": total if total is not None else len(units), "done": 0, "failed": [],
              "last_unit": None, "last_unit_at": now(), "pid": pid, "state": "running",
              "abort_reason": None, "last_unit_seconds": None, "last_peak_rss_gb": None}

    def abort(reason):
        status.update(state="aborted", abort_reason=reason)

    write_status(root, status)
    consecutive = 0
    try:
        for key, item_id in units:
            name = f"{key}/{item_id}"
            state = unit_state(root, key, item_id, source_digest)
            if state is None:
                if free_bytes() < MIN_FREE_BYTES:
                    abort(f"free disk below {MIN_FREE_BYTES / 1e9:.0f} GB before {name}")
                    break
                res = run_unit(key, item_id)
                state = unit_state(root, key, item_id, source_digest) or "failed"   # crash/kill: no marker
                status.update(last_unit_seconds=round(res.wall, 1), last_peak_rss_gb=round(res.peak_rss / 1e9, 2))
                consecutive = 0 if state == "done" else consecutive + 1
            else:
                res = None
            status["last_unit"], status["last_unit_at"] = name, now()
            if state == "done":
                status["done"] += 1
            else:
                status["failed"].append(name)
            reason = None
            if res and res.peak_rss > RSS_LIMIT:
                reason = f"RSS {res.peak_rss / 1e9:.1f} GB above 16 GB at {name}"
            elif res and res.wall > wall_limit(key):
                reason = f"wall time {res.wall:.0f} s above 4x B0 ({wall_limit(key):.0f} s) at {name}"
            elif consecutive >= MAX_CONSECUTIVE_FAILURES:
                reason = f"{consecutive} consecutive failures, last {name}"
            if reason:
                abort(reason)
            write_status(root, status)
            if reason:
                return status
        else:
            status["state"] = "finished"
    except Terminated:
        abort("SIGTERM")
    write_status(root, status)
    return status


def kill_descendants(*_):
    """On SIGTERM: stop the unit.py child AND its worker (own session), then unwind."""
    import psutil
    for child in psutil.Process().children(recursive=True):
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
    raise Terminated()


def plan_route(profiles, items):
    """One base-model unit per sign profile and strict-battery item."""
    return [unit_tag("base", pid) for pid in sorted(profiles)], items


def unit_command(key, item_id, *, root, frozen, baseline=None):
    profile = profile_of_tag(key)
    cmd = [sys.executable, str(PACKAGE / "runner" / "unit.py"), "--model", "base" if profile else key,
           "--item", item_id, "--weights", WEIGHTS, "--dtype", DTYPE, "--device", "cpu",
           "--output", str(root), "--frozen", str(frozen), "--timeout", str(wall_limit(key))]
    if profile:
        if baseline is None:
            raise ValueError("prompt route requires a baseline directory")
        cmd += ["--prompt-profile", profile, "--baseline", str(baseline)]
    return cmd


def unit_runner(root, frozen, baseline=None):
    root = Path(root)

    def run_unit(key, item_id):
        cmd = unit_command(key, item_id, root=root, frozen=frozen, baseline=baseline)
        # Offline: adapters are prefetched and the base is cached; no per-unit Hub round trip.
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", HF_HUB_OFFLINE="1")
        print("UNIT_START", key, item_id, flush=True)
        started_wall, started = time.time(), time.monotonic()
        rc = subprocess.run(cmd, env=env).returncode
        wall = time.monotonic() - started
        peak = 0
        for rc_file in (root / "attempts").glob(f"{key}_{item_id}_*.rc.json"):
            if rc_file.stat().st_mtime >= started_wall - 1:
                peak = max(peak, json.loads(rc_file.read_text())["peak_rss_bytes"])
        print("UNIT_END", key, item_id, f"rc={rc} wall={wall:.1f}s peak_rss={peak / 1e9:.2f}GB", flush=True)
        return UnitResult(rc=rc, wall=wall, peak_rss=peak)
    return run_unit


def prefetch(registry):
    """Download every adapter at its pinned revision (public, no token) and sha256-check it."""
    for entry in registry["models"]:
        fetch_inputs(registry, entry["key"])      # raises on any weight/config digest mismatch
        print("PREFETCH_OK", entry["key"], flush=True)
    n = sum(1 for e in registry["models"] if e["key"] != "base")
    print(f"PREFETCH_VERIFIED {n}/{n}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", action="store_true", required=True, help="no HF_TOKEN, no Hub calls during the run")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--frozen", type=Path, required=True)
    ap.add_argument("--only", nargs="+", metavar="KEY:ITEM", help="proof runs: just these units")
    ap.add_argument("--prefetch-only", action="store_true")
    ap.add_argument("--prompt-route", action="store_true")
    ap.add_argument("--baseline", type=Path)
    args = ap.parse_args()
    if args.prompt_route != (args.baseline is not None):
        ap.error("--prompt-route and --baseline must be supplied together")
    reg = json.loads((PACKAGE / "models.json").read_text())
    if args.prefetch_only:
        prefetch(reg)
        return
    items = json.loads((PACKAGE / "items.json").read_text())["items"]
    keys, items = plan_route(load_profiles(), items) if args.prompt_route else plan(False, reg, items)
    only = {tuple(x.split(":", 1)) for x in args.only} if args.only else None
    signal.signal(signal.SIGTERM, kill_descendants)
    with single_queue(args.output):
        status = run_queue(keys, items, root=args.output, run_unit=unit_runner(args.output, args.frozen, args.baseline),
                           free_bytes=lambda: __import__("shutil").disk_usage(args.output).free,
                           source_digest=current_source_digest(), pid=os.getpid(), only=only)
    print("QUEUE_END", json.dumps(status), flush=True)
    raise SystemExit(0 if status["state"] == "finished" and not status["failed"] else 1)


if __name__ == "__main__":
    main()
