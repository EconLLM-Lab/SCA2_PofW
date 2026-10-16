# VM-side boot for the Hub-only factorial run (no Drive, no browser clicks).
# Order on a fresh VM:  vm_setup.py  ->  setenv (HF_TOKEN)  ->  this file  ->  vm_fact_wave*.py
# colab exec -s pb-a -f paper_b/colab/vm_fact_boot.py --timeout 1200
import os, shutil, subprocess, sys, tarfile
sys.path.insert(0, "/content/SCA2_PofW/paper_b/colab"); sys.path.insert(0, "/content/SCA2_PofW/paper_b")
from vm_fact_common import REPO, ROOT, run
import hub_io

assert os.environ.get("HF_TOKEN"), "HF_TOKEN is not set in this kernel; run setenv first"
from huggingface_hub import HfApi, hf_hub_download
pins = hub_io.load_pins()
repo = pins["artifacts_repo"]
tmp = "/content/pb_pull"


def dl(r, hub_path, dest):
    p = hf_hub_download(repo_id=r, filename=hub_path, repo_type="dataset", local_dir=tmp,
                        token=os.environ["HF_TOKEN"])
    shutil.copyfile(p, dest)


os.makedirs(ROOT, exist_ok=True)
bundle = hub_io.pull_pinned(dl, repo, pins["bundle"]["hub_path"], "/content/bank2_bundle.tgz", pins["bundle"]["sha256"])
with tarfile.open(bundle) as tf:
    tf.extractall(REPO)
hub_io.pull_pinned(dl, repo, pins["refcache"]["hub_path"], f"{ROOT}/shared_reference_logps.jsonl", pins["refcache"]["sha256"])
hub_io.pull_pinned(dl, repo, pins["refcache_manifest"]["hub_path"], f"{ROOT}/shared_reference_logps_manifest.json",
                   pins["refcache_manifest"]["sha256"])
rows = sum(1 for _ in open(f"{ROOT}/shared_reference_logps.jsonl"))
assert rows == pins["refcache"]["rows"], (rows, pins["refcache"]["rows"])
print(f"pinned inputs verified: bundle, reference cache ({rows} rows), manifest")

api = HfApi()
print("write probe:", hub_io.write_probe(api, repo, pins["relabel_run_id"], "boot"))
rc = run(["paper_b/verify_gates.py", "--scan-text"], "fact_gates")
print("gates rc:", rc)
print("BOOT OK" if rc == 0 else "BOOT FAILED")
raise SystemExit(rc)
