# VM-side helper for the 2^6 factorial (bank 2, 64 sign-profile units).
# Imported by vm_fact_boot.py / vm_fact_wave1.py / vm_fact_wave2.py / vm_fact_status.py.
# The Hub is the only durable store (no Drive, no OAuth). Data root is the VM's local disk; the
# runner syncs logs, wave manifest and ledger to Hub state/<tag>/ after every unit.
# protocol_bank2 refuses any Hub path outside bank2/<run>/ so cohort-1 adapters cannot be touched.
import os, shlex, subprocess, sys

REPO = "/content/SCA2_PofW"
ROOT = "/content/pb_data"
SG = REPO + "/synthetic_generation/outputs"
def child_env(**extra):
    """The environment for a child process, built when it is CALLED.

    Not at import. The kernel's os.environ changes during a session — the HF token is set after the
    VM boots — and a module-level snapshot hands every later child the environment as it was when this
    module was first imported. That cost a re-provision on 2026-10-16: the gate refused with
    "HF_TOKEN missing" on a VM whose kernel demonstrably had the token, because an earlier launch had
    already cached this module.
    """
    env = dict(os.environ,
               SCA2_PB_PROTOCOL="bank2", SCA2_PB_UNITS="profiles",
               SCA2_PB_DATA_ROOT=ROOT,
               SCA2_PB_BANK2_DIR=SG + "/gps_sign_relabel_bank2",
               SCA2_PB_PROFILE_DIR=SG + "/gps_sign_relabel_bank2_profiles",
               PYTHONUNBUFFERED="1", ACCELERATE_MIXED_PRECISION="fp16",
               PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True", TRANSFORMERS_NO_BF16="1")
    env.update(extra)
    return env


def run(args, log_name):
    """Blocking run for short steps (gates). Long jobs use launch_detached."""
    log = f"{ROOT}/logs/{log_name}.log"
    os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, "a") as lg:
        lg.write(f"\n=== {log_name} start ===\n"); lg.flush()
        rc = subprocess.run([sys.executable, *args], cwd=REPO, env=child_env(),
                            stdout=lg, stderr=subprocess.STDOUT).returncode
    print(log_name, "rc:", rc, "| log:", log)
    return rc


def _alive(pid_file, rc_file):
    if os.path.exists(rc_file) or not os.path.exists(pid_file):
        return False
    try:
        os.kill(int(open(pid_file).read()), 0)
        return True
    except (OSError, ValueError):
        return False


def launch_detached(steps):
    """steps = [(name, args, extra_env)], run one after another in a single detached shell.

    The shell survives the client that started it (a closed laptop or a quit Docker costs nothing);
    each step writes <name>.log and <name>.rc. A step that fails does not stop the next one.
    """
    os.makedirs(f"{ROOT}/logs", exist_ok=True)
    first = steps[0][0]
    pid_file, rc_file = f"{ROOT}/logs/{first}.pid", f"{ROOT}/logs/{first}.rc"
    if _alive(pid_file, rc_file):
        raise SystemExit(f"{first} is already running (pid {open(pid_file).read()}); not launching a second copy")
    parts = []
    for name, args, extra in steps:
        log, rc = f"{ROOT}/logs/{name}.log", f"{ROOT}/logs/{name}.rc"
        if os.path.exists(rc):
            os.remove(rc)
        envs = " ".join(f"{k}={shlex.quote(v)}" for k, v in (extra or {}).items())
        parts.append(f"({envs} {shlex.quote(sys.executable)} {' '.join(map(shlex.quote, args))} >> {shlex.quote(log)} 2>&1; "
                     f"echo $? > {shlex.quote(rc)})")
    p = subprocess.Popen(["sh", "-c", "; ".join(parts)], cwd=REPO, env=child_env(), start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    open(pid_file, "w").write(str(p.pid))
    print(f"launched detached: {[s[0] for s in steps]} | pid {p.pid} | logs {ROOT}/logs/")
