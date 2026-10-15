# VM-side helper for the 2^6 factorial (bank 2, 64 sign-profile units).
# Imported by vm_fact_refcache.py / vm_fact_wave1.py / vm_fact_wave2.py.
# Data root is separate from cohort 1 so nothing of cohort 1 can be overwritten;
# protocol_bank2 also refuses any Hub path outside bank2/<run>/profiles.
import os, subprocess, sys

REPO = "/content/SCA2_PofW"
ROOT = "/content/drive/MyDrive/SCA2_paper_b_bank2_profiles"
SG = REPO + "/synthetic_generation/outputs"
ENV = dict(os.environ,
           SCA2_PB_PROTOCOL="bank2", SCA2_PB_UNITS="profiles",
           SCA2_PB_DATA_ROOT=ROOT,
           SCA2_PB_BANK2_DIR=SG + "/gps_sign_relabel_bank2",
           SCA2_PB_PROFILE_DIR=SG + "/gps_sign_relabel_bank2_profiles",
           PYTHONUNBUFFERED="1", ACCELERATE_MIXED_PRECISION="fp16",
           PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True", TRANSFORMERS_NO_BF16="1")


def run(args, log_name):
    log = f"{ROOT}/logs/{log_name}.log"
    os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, "a") as lg:
        lg.write(f"\n=== {log_name} start ===\n"); lg.flush()
        rc = subprocess.run([sys.executable, *args], cwd=REPO, env=ENV,
                            stdout=lg, stderr=subprocess.STDOUT).returncode
    print(log_name, "rc:", rc, "| log:", log)
    return rc
