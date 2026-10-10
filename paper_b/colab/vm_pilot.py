# VM-side: pilot one country end-to-end (prepare + train + save).
# colab exec -s pb-a -f paper_b/colab/vm_pilot.py --timeout 7200
import os, subprocess, sys
REPO = "/content/SCA2_PofW"
os.environ["SCA2_PB_DATA_ROOT"] = "/content/drive/MyDrive/SCA2_paper_b"
os.environ["ACCELERATE_MIXED_PRECISION"] = "fp16"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
os.environ["TRANSFORMERS_NO_BF16"] = "1"
raise SystemExit(subprocess.call(
    [sys.executable, "paper_b/run_cohort.py", "--countries", "ARG"], cwd=REPO))
