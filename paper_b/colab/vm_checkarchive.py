# VM-side provisioning step: verify the uploaded archived base-on-CHN option file byte for byte.
# Versioned replacement for the scratch helper pb_checkarchive.py (pruned 2026-10-18); provision_score_vm.sh
# expects the marker "archive sha256 ok". The gate compares the base model with this file (report-only), so a
# truncated upload must stop provisioning rather than surface later as an archive gap.
#   colab exec -s pb-p -f paper_b/colab/vm_checkarchive.py --timeout 150
import hashlib
import sys

PATH = "/content/SCA2_PofW/data/phase2/raw/wvs/ksenias_base8/model_option_probabilities_base_on_CHN.csv"
EXPECTED = "b54aab7ae9c4b0e9995fc7cae28f8f484b47c796c5cc2c859fb5e1443ac027e7"   # laptop copy, 2026-10-18

try:
    got = hashlib.sha256(open(PATH, "rb").read()).hexdigest()
except OSError as exc:
    print(f"archive MISSING: {exc}")
    sys.exit(1)
if got != EXPECTED:
    print(f"archive sha256 MISMATCH: {got}")
    sys.exit(1)
print("archive sha256 ok", got[:12])
