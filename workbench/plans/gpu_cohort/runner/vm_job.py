"""Shared detached launcher/driver for pilot and cohort; no runtime provisioning."""
import json
import os
from pathlib import Path
import subprocess
import sys

PACKAGE = Path("/content/workbench/plans/gpu_cohort")
STATE = Path("/content/cohort_state")
PILOT_MAX_CU = 35  # queue compute+sync only: ~1.9x the 18.1 CU no-speedup envelope (46 units); setup is extra


def launch(stage):
    from google.colab import userdata
    import psutil
    STATE.mkdir(exist_ok=True)
    pidfile = STATE / "active.pid"
    if pidfile.exists():
        try:
            p = psutil.Process(int(pidfile.read_text()))
            if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                raise ValueError("a cohort driver is already active")
        except psutil.NoSuchProcess:
            pass
    os.environ["HF_TOKEN"] = userdata.get("HF_TOKEN")
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ.pop("PYTHONPATH", None)
    (STATE / "active.rc").unlink(missing_ok=True)
    with (STATE / f"{stage}.log").open("ab", buffering=0) as log:
        p = subprocess.Popen(["/content/cohort-capture/bin/python", str(PACKAGE / "runner" / "vm_job.py"), stage],
                             stdout=log, stderr=subprocess.STDOUT, start_new_session=True, env=dict(os.environ))
    pidfile.write_text(str(p.pid))
    print("DETACHED", stage, "pid", p.pid, flush=True)


def queue_command(stage, config, prefix):
    cmd = [sys.executable, str(PACKAGE / "runner" / "cohort_queue.py"), "--output", "/content/cohort_exports",
           "--frozen", "/content/cohort_nf4", "--prefix", prefix,
           "--unit-seconds", str(config["a100_unit_seconds"]),
           "--base-seconds", str(config["a100_base_seconds"])]
    if stage == "pilot":
        cmd += ["--pilot", "--max-cu", str(PILOT_MAX_CU), "--cu-per-hour", str(config["assumed_cu_per_hour"])]
    return cmd


def driver(stage):
    config = json.loads((PACKAGE / "estimate.json").read_text())
    cmd = queue_command(stage, config, Path("/content/cohort_prefix.txt").read_text().strip())
    rc = 1
    try:
        rc = subprocess.run(cmd).returncode
    finally:
        (STATE / "active.rc").write_text(str(rc))
        (STATE / f"{stage}.rc").write_text(str(rc))
    raise SystemExit(rc)


if __name__ == "__main__":
    driver(sys.argv[1])
