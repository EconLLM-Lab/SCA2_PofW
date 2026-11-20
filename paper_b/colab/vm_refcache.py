# VM-side: run the shared reference cache pass (GPU).
# colab exec -s pb-a -f paper_b/colab/vm_refcache.py --timeout 5400
import os, subprocess, sys
REPO = "/content/SCA2_PofW"
os.environ["SCA2_PB_DATA_ROOT"] = "/content/drive/MyDrive/SCA2_paper_b"
os.environ["ACCELERATE_MIXED_PRECISION"] = "fp16"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
os.environ["TRANSFORMERS_NO_BF16"] = "1"
raise SystemExit(subprocess.call([sys.executable, "paper_b/compute_ref_cache.py"], cwd=REPO))
