# VM-side boot for the near-zero run (card T5, C6): pull the four reduced banks, verify the pinned SHA-256,
# extract to /content/pb_data/near_zero and check every unit's manifest against its bank file.
# Order on a fresh VM: provision_score_vm.sh (setup, token, vm_fact_boot) -> this file -> vm_run_nz_train.py.
#   colab exec -s pb-nz -f paper_b/colab/vm_nearzero_boot.py --timeout 600
import json, os, shutil, sys, tarfile
sys.path.insert(0, "/content/SCA2_PofW/paper_b/colab"); sys.path.insert(0, "/content/SCA2_PofW/paper_b")
from vm_fact_common import REPO, ROOT
import hub_io
import protocol_bank2 as P2

assert os.environ.get("HF_TOKEN"), "HF_TOKEN is not set in this kernel; run setenv first"
from huggingface_hub import hf_hub_download
pins = json.loads(open(f"{REPO}/paper_b/score_plan_pins.json").read())
b = pins.get("nearzero_bank_bundle")
assert b, "score_plan_pins.json has no nearzero_bank_bundle pin; the VM checkout is older than the upload"
repo = hub_io.load_pins()["artifacts_repo"]
tmp = "/content/pb_pull_nz"


def dl(r, hub_path, dest):
    shutil.copyfile(hf_hub_download(repo_id=r, filename=hub_path, repo_type="dataset", local_dir=tmp,
                                    token=os.environ["HF_TOKEN"]), dest)


bundle = hub_io.pull_pinned(dl, repo, b["hub_path"], "/content/near_zero_banks.tgz", b["sha256"])
dest = f"{ROOT}/near_zero"
shutil.rmtree(dest, ignore_errors=True)
os.makedirs(dest)
with tarfile.open(bundle) as tf:
    tf.extractall(dest, filter="data")
run_id = hub_io.load_pins()["relabel_run_id"]
ms = P2.load_nearzero_manifests(dest, run_id)          # SHA-256 of every bank file against its manifest
print({u: m["train_kept"] for u, m in ms.items()})
print("NEARZERO BOOT OK")
