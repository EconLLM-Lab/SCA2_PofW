# VM-side provisioning step: create the directory the gate reads the archived base-on-CHN file from.
# Versioned replacement for the scratch helper pb_mkarchive.py (pruned 2026-10-18); provision_score_vm.sh
# expects the marker "archive dir".
#   colab exec -s pb-p -f paper_b/colab/vm_mkarchive.py --timeout 150
import os

ARCHIVE_DIR = "/content/SCA2_PofW/data/phase2/raw/wvs/ksenias_base8"   # eval_config.ARCHIVE_DIR on the VM
os.makedirs(ARCHIVE_DIR, exist_ok=True)
print("archive dir", ARCHIVE_DIR, "exists:", os.path.isdir(ARCHIVE_DIR))
