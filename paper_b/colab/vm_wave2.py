# VM-side: wave 2 (remaining cohort countries, resumable).
# colab exec -s pb-b -f paper_b/colab/vm_wave2.py --timeout 36000
import os, subprocess, sys
REPO = "/content/SCA2_PofW"
LOG = "/content/drive/MyDrive/SCA2_paper_b/logs/wave2.log"
os.makedirs(os.path.dirname(LOG), exist_ok=True)
env = dict(os.environ, SCA2_PB_DATA_ROOT="/content/drive/MyDrive/SCA2_paper_b",
           PYTHONUNBUFFERED="1",
           ACCELERATE_MIXED_PRECISION="fp16", PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True",
           TRANSFORMERS_NO_BF16="1")
with open(LOG, "a") as lg:
    lg.write("\n=== wave2 start ===\n"); lg.flush()
    r = subprocess.run([sys.executable, "paper_b/run_cohort.py", "--wave", "2"],
                       cwd=REPO, env=env, stdout=lg, stderr=subprocess.STDOUT)
print("wave2 rc:", r.returncode)
