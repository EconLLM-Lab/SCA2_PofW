# VM-side scoring driver for one condition and one half of the 64 units (Hub is the only durable store).
#   python paper_b/colab/vm_score_units.py <condition> <A|B>
# Conditions and pins live in paper_b/score_plan.py. The driver builds the spec on the VM, refuses to run if its
# SHA-256 differs from the pinned one, computes what is left from the Hub listing, scores only that, and exits 4
# unless the Hub then holds every expected file for this half.
import json, os, subprocess, sys
sys.path.insert(0, "/content/SCA2_PofW/paper_b"); sys.path.insert(0, "/content/SCA2_PofW/paper_b/colab")
from vm_fact_common import ENV, REPO, ROOT
import score_plan as SPL
from build_scoring_spec import write_spec
from huggingface_hub import HfApi

cond, half = sys.argv[1], sys.argv[2]
c = SPL.CONDITIONS[cond]
pins = json.loads(SPL.PINS.read_text())
assert pins["adapter_revision"] == SPL.ADAPTER_REVISION, "pins file and plan disagree on the adapter revision"
spec = SPL.build_spec(cond)
got = SPL.spec_hash(spec)
if got != pins["spec_sha256"][cond]:
    print(f"REFUSING: spec {cond} hash {got[:12]} != pinned {pins['spec_sha256'][cond][:12]}; no model loaded")
    sys.exit(2)
try:
    SPL.check_marker(json.loads(open(f"{ROOT}/adapter_gate.json").read()), half)
except (OSError, ValueError, RuntimeError) as exc:
    print(f"REFUSING [{cond}/{half}]: {exc}; no model loaded")
    sys.exit(2)
os.makedirs(f"{ROOT}/specs", exist_ok=True)
spec_path = write_spec(spec, f"{ROOT}/specs/{cond}.json")
env = dict(ENV, SCA2_PB_ADAPTER_REVISION=SPL.ADAPTER_REVISION)
marker = f"{ROOT}/adapter_gate.json"
api = HfApi()


def listing():
    return api.list_repo_files(SPL.ARTIFACTS_REPO, repo_type="dataset")        # an error aborts: never guess "nothing done"


def read_manifest(run_id, model):
    """One unit's manifest. A read failure aborts the run rather than reading as 'done'."""
    from huggingface_hub import hf_hub_download
    p = hf_hub_download(SPL.ARTIFACTS_REPO, f"runs/{run_id}/manifests/{model}_manifest.json",
                        repo_type="dataset")
    return json.loads(open(p).read())


units = SPL.units_for_half(half)
print(f"[{cond}/{half}] run_id {c['run_id']} | spec {got[:12]} | adapter revision {SPL.ADAPTER_REVISION[:12]}")
if c["kind"] == "signprompt":
    rc = subprocess.run([sys.executable, "paper_b/score_sign_profiles.py", "--prepare-only", "--units", "all64",
                         "--out-dir", f"{ROOT}/signprompt"], cwd=REPO, env=env).returncode
    if rc:
        sys.exit(rc)
    rc = subprocess.run([sys.executable, "paper_b/score_sign_profiles.py", "--profiles", f"{ROOT}/signprompt/sign_profiles.json",
                         "--spec", str(spec_path), "--out-dir", f"{ROOT}/signprompt/out", "--only", *units,
                         "--hub-run", c["run_id"]], cwd=REPO, env=env).returncode
    from score_sign_profiles import done_profiles
    done = done_profiles(listing(), c["run_id"], got, read_manifest)   # spec-aware: an amended pool re-scores
    missing = [u for u in units if u not in done]
else:
    todo = SPL.todo_units(c["run_id"], half, listing(), spec_sha=got, read_manifest=read_manifest)
    print(f"[{cond}/{half}] to score: {len(todo['units'])} units, base={todo['base']}")
    rc = 0
    args = SPL.score_cohort_args(c["run_id"], str(spec_path), marker, todo)
    if args:
        rc = subprocess.run([sys.executable, "paper_b/score_cohort.py", *args], cwd=REPO, env=env).returncode
    left = SPL.todo_units(c["run_id"], half, listing(), spec_sha=got, read_manifest=read_manifest)
    missing = left["units"] + (["base"] if left["base"] else [])
print(f"[{cond}/{half}] score rc={rc} | missing on the Hub: {len(missing)} {missing[:4]}")
sys.exit(0 if (rc == 0 and not missing) else 4)
