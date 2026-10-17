# VM-side scoring driver for ONE card-T4 condition (Hub is the only durable store).
#   python paper_b/colab/vm_score_t4.py <condition>
# Conditions: signprompt_strict_v1 (all 64 sign-prompt cells, no adapter), replicate_strict_v1 and
# replicate_heldout_v1 (the r1 retrain of one unit). Pins and run ids live in paper_b/score_plan.py.
# Unlike vm_score_units.py there is no half split: a condition names its own units. The driver builds the spec,
# refuses if its SHA-256 differs from the pin, refuses a gate marker that does not authorise this condition (a
# replicate needs a marker made on the replicate weights), scores only what the Hub lacks under THIS spec, and
# exits 4 unless the Hub then holds every expected CSV + manifest.
import json, os, subprocess, sys
sys.path.insert(0, "/content/SCA2_PofW/paper_b"); sys.path.insert(0, "/content/SCA2_PofW/paper_b/colab")
from vm_fact_common import REPO, ROOT, child_env
import score_plan as SPL
from build_scoring_spec import write_spec
from huggingface_hub import HfApi, hf_hub_download

cond = sys.argv[1]
c = SPL.CONDITIONS[cond]
units = SPL.condition_units(cond)
token = os.environ.get("HF_TOKEN")
if not token:
    print(f"REFUSING [{cond}]: HF_TOKEN is not set; no model loaded"); sys.exit(2)
want_rep = c.get("replicate", "")
if os.environ.get("SCA2_PB_REPLICATE", "") != want_rep:      # the switch moves every adapter path: it must match
    print(f"REFUSING [{cond}]: SCA2_PB_REPLICATE={os.environ.get('SCA2_PB_REPLICATE', '')!r}, condition needs {want_rep!r}; no model loaded")
    sys.exit(2)
pins = json.loads(SPL.PINS.read_text())
assert pins["adapter_revision"] == SPL.ADAPTER_REVISION, "pins file and plan disagree on the adapter revision"
spec = SPL.build_spec(cond)
got = SPL.spec_hash(spec)
if got != pins["spec_sha256"][cond]:
    print(f"REFUSING: spec {cond} hash {got[:12]} != pinned {pins['spec_sha256'][cond][:12]}; no model loaded")
    sys.exit(2)

marker = f"{ROOT}/adapter_gate.json"
rep_sha = None
try:
    if want_rep:
        import eval_config as E, score_runtime as R             # imported only after the replicate switch is verified
        adapter_dir, source = R.resolve_adapter(units[0], SPL.ADAPTER_REVISION, E.ADAPTER_CACHE_DIR)
        rep_sha = R.adapter_sha256(adapter_dir)
        print(f"[{cond}] replicate adapter {units[0]} from {source}: {adapter_dir} sha256 {rep_sha[:12]}")
    SPL.check_marker_for(cond, json.loads(open(marker).read()), replicate_adapter_sha=rep_sha)
except (OSError, ValueError, RuntimeError) as exc:
    print(f"REFUSING [{cond}]: {exc}; no model loaded")
    sys.exit(2)

os.makedirs(f"{ROOT}/specs", exist_ok=True)
spec_path = write_spec(spec, f"{ROOT}/specs/{cond}.json")
env = child_env(SCA2_PB_ADAPTER_REVISION=SPL.ADAPTER_REVISION)
api = HfApi(token=token)


def listing():
    return api.list_repo_files(SPL.ARTIFACTS_REPO, repo_type="dataset")        # an error aborts: never guess "nothing done"


def read_manifest(run_id, model):
    """One unit's manifest. A read failure aborts the run rather than reading as 'done'."""
    p = hf_hub_download(SPL.ARTIFACTS_REPO, f"runs/{run_id}/manifests/{model}_manifest.json",
                        repo_type="dataset", token=token)
    return json.loads(open(p).read())


todo = SPL.todo_condition(cond, listing(), got, read_manifest)
print(f"[{cond}] run_id {c['run_id']} | spec {got[:12]} | adapter revision {SPL.ADAPTER_REVISION[:12]} | "
      f"to score: {len(todo)} of {len(units)} units")
rc = 0
if todo and c["kind"] == "signprompt":
    rc = subprocess.run([sys.executable, "paper_b/score_sign_profiles.py", "--prepare-only", "--units", "all64",
                         "--out-dir", f"{ROOT}/signprompt"], cwd=REPO, env=env).returncode
    if not rc:
        rc = subprocess.run([sys.executable, "paper_b/score_sign_profiles.py", "--profiles", f"{ROOT}/signprompt/sign_profiles.json",
                             "--spec", str(spec_path), "--out-dir", f"{ROOT}/signprompt/out", "--only", *todo,
                             "--hub-run", c["run_id"]], cwd=REPO, env=env).returncode
elif todo:
    args = SPL.score_cohort_args(c["run_id"], str(spec_path), marker, {"units": todo, "base": False})
    rc = subprocess.run([sys.executable, "paper_b/score_cohort.py", *args], cwd=REPO, env=env).returncode
missing = SPL.todo_condition(cond, listing(), got, read_manifest)
print(f"[{cond}] score rc={rc} | missing on the Hub: {len(missing)} {missing[:4]}")
sys.exit(0 if (rc == 0 and not missing) else 4)
