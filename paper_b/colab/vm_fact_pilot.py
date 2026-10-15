import subprocess, sys, os
# Pilot: ONE representative profile unit through the frozen path, to measure real
# minutes/units before the 64-unit cohort is committed to GPU.
ENV = dict(os.environ,
           SCA2_PB_PROTOCOL="bank2", SCA2_PB_UNITS="profiles",
           SCA2_PB_DATA_ROOT="/content/drive/MyDrive/SCA2_paper_b_bank2_profiles",
           SCA2_PB_BANK2_DIR="/content/SCA2_PofW/synthetic_generation/outputs/gps_sign_relabel_bank2",
           SCA2_PB_PROFILE_DIR="/content/SCA2_PofW/synthetic_generation/outputs/gps_sign_relabel_bank2_profiles",
           PYTHONUNBUFFERED="1", ACCELERATE_MIXED_PRECISION="fp16",
           PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True", TRANSFORMERS_NO_BF16="1")
REPO = "/content/SCA2_PofW"
log = "/content/drive/MyDrive/SCA2_paper_b_bank2_profiles/logs/fact_pilot.log"
os.makedirs(os.path.dirname(log), exist_ok=True)
with open(log, "a") as lg:
    lg.write("\n=== fact_pilot start ===\n"); lg.flush()
    rc = subprocess.run([sys.executable, "paper_b/run_cohort.py", "--countries", "P_1_0_1_1_0_1"],
                        cwd=REPO, env=ENV, stdout=lg, stderr=subprocess.STDOUT).returncode
print("pilot rc:", rc, "| log:", log)