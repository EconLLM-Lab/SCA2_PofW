# VM-side scoring driver for ONE card-T4 condition (Hub is the only durable store).
#   python paper_b/colab/vm_score_t4.py <condition>
# Card T5 adds nearzero_strict_v1 (GBR, COL, GBR_control, COL_control; each adapter needs its own gate marker).
# Conditions: signprompt_strict_v1 (all 64 sign-prompt cells, no adapter), replicate_strict_v1 and
# replicate_heldout_v1 (the r1 retrain of one unit). Pins and run ids live in paper_b/score_plan.py.
# Card C8 adds persona_strict_v1: the country-named persona prompt for the 42 cohort countries, no adapter. Its
# children get SCA2_PB_UNITS=countries (condition_env), and G3 scores the base model under the persona run id and
# compares it with the banked strict base before any persona is scored (exit 3 on a gap beyond the base tolerance).
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
nearzero = bool(c.get("nearzero"))
if nearzero and os.environ.get("SCA2_PB_NEARZERO") != SPL.NEARZERO_DIR_VM:     # the switch moves every adapter path
    print(f"REFUSING [{cond}]: SCA2_PB_NEARZERO={os.environ.get('SCA2_PB_NEARZERO')!r}, condition needs {SPL.NEARZERO_DIR_VM!r}; no model loaded")
    sys.exit(2)
try:
    rev = SPL.adapter_revision_for(cond)                # a near-zero condition scores at its own pinned adapter commit
except RuntimeError as exc:
    print(f"REFUSING [{cond}]: {exc}; no model loaded"); sys.exit(2)
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
    if nearzero:
        import eval_config as E, score_runtime as R             # imported only after the near-zero switch is verified
        markers = []
        for u in units:                                          # every adapter needs its own gate, made on its own weights
            adapter_dir, source = R.resolve_adapter(u, rev, E.ADAPTER_CACHE_DIR)
            sha = R.adapter_sha256(adapter_dir)
            mk = f"{ROOT}/{SPL.gate_marker_name(u)}"
            SPL.check_marker_nearzero(json.loads(open(mk).read()), u, sha, rev)
            markers.append(mk)
            print(f"[{cond}] {u} from {source}: sha256 {sha[:12]} | gate marker ok")
        marker = markers[0]                                      # score_cohort reads only gate_pass from the one it is handed
    elif want_rep:
        import eval_config as E, score_runtime as R             # imported only after the replicate switch is verified
        adapter_dir, source = R.resolve_adapter(units[0], SPL.ADAPTER_REVISION, E.ADAPTER_CACHE_DIR)
        rep_sha = R.adapter_sha256(adapter_dir)
        print(f"[{cond}] replicate adapter {units[0]} from {source}: {adapter_dir} sha256 {rep_sha[:12]}")
    if not nearzero:
        SPL.check_marker_for(cond, json.loads(open(marker).read()), replicate_adapter_sha=rep_sha)
except (OSError, ValueError, RuntimeError) as exc:
    print(f"REFUSING [{cond}]: {exc}; no model loaded")
    sys.exit(2)

os.makedirs(f"{ROOT}/specs", exist_ok=True)
spec_path = write_spec(spec, f"{ROOT}/specs/{cond}.json")
env = child_env(SCA2_PB_ADAPTER_REVISION=rev, **SPL.condition_env(cond))   # the persona switch must reach children
api = HfApi(token=token)


def listing():
    return api.list_repo_files(SPL.ARTIFACTS_REPO, repo_type="dataset")        # an error aborts: never guess "nothing done"


def read_manifest(run_id, model):
    """One unit's manifest. A read failure aborts the run rather than reading as 'done'."""
    p = hf_hub_download(SPL.ARTIFACTS_REPO, f"runs/{run_id}/manifests/{model}_manifest.json",
                        repo_type="dataset", token=token)
    return json.loads(open(p).read())


def read_base(run_id):
    import pandas as pd
    p = hf_hub_download(SPL.ARTIFACTS_REPO, f"runs/{run_id}/synthetic/base_option_probabilities.csv",
                        repo_type="dataset", token=token)
    return pd.read_csv(p, dtype={"question_id": str, "option_code": str})


if c["kind"] == "persona":                           # G3: same stack as the banked adapter columns, or stop here
    if not SPL._present(c["run_id"], listing(), "base", got, read_manifest):
        args = SPL.score_cohort_args(c["run_id"], str(spec_path), marker, {"units": [], "base": True}, revision=rev)
        rc = subprocess.run([sys.executable, "paper_b/score_cohort.py", *args], cwd=REPO, env=env).returncode
        if rc:
            print(f"G3 REFUSING [{cond}]: base scoring rc={rc}; no persona scored"); sys.exit(3)
    parity = SPL.base_parity(read_base(c["run_id"]), read_base(SPL.PERSONA_BASE_REFERENCE_RUN))
    parity["run_id"] = c["run_id"]
    api.upload_file(path_or_fileobj=json.dumps(parity, indent=2).encode(), path_in_repo=f"runs/{c['run_id']}/base_parity.json",
                    repo_id=SPL.ARTIFACTS_REPO, repo_type="dataset", commit_message=f"{c['run_id']}: G3 base parity")
    print(f"[{cond}] G3 base parity vs {SPL.PERSONA_BASE_REFERENCE_RUN}: {json.dumps(parity)}")
    if not parity["pass"]:
        print(f"G3 FAILED [{cond}]: the fresh base differs from the banked base; no persona scored"); sys.exit(3)


todo = SPL.todo_condition(cond, listing(), got, read_manifest)
print(f"[{cond}] run_id {c['run_id']} | spec {got[:12]} | adapter revision {rev[:12]} | "
      f"to score: {len(todo)} of {len(units)} units")
rc = 0
if todo and c["kind"] == "signprompt":
    rc = subprocess.run([sys.executable, "paper_b/score_sign_profiles.py", "--prepare-only", "--units", "all64",
                         "--out-dir", f"{ROOT}/signprompt"], cwd=REPO, env=env).returncode
    if not rc:
        rc = subprocess.run([sys.executable, "paper_b/score_sign_profiles.py", "--profiles", f"{ROOT}/signprompt/sign_profiles.json",
                             "--spec", str(spec_path), "--out-dir", f"{ROOT}/signprompt/out", "--only", *todo,
                             "--hub-run", c["run_id"]], cwd=REPO, env=env).returncode
elif todo and c["kind"] == "persona":
    args = SPL.score_cohort_args(c["run_id"], str(spec_path), marker, {"units": todo, "base": False}, revision=rev,
                                 arm="persona")
    rc = subprocess.run([sys.executable, "paper_b/score_cohort.py", *args], cwd=REPO, env=env).returncode
elif todo:
    args = SPL.score_cohort_args(c["run_id"], str(spec_path), marker, {"units": todo, "base": False}, revision=rev)
    rc = subprocess.run([sys.executable, "paper_b/score_cohort.py", *args], cwd=REPO, env=env).returncode
missing = SPL.todo_condition(cond, listing(), got, read_manifest)
print(f"[{cond}] score rc={rc} | missing on the Hub: {len(missing)} {missing[:4]}")
sys.exit(0 if (rc == 0 and not missing) else 4)
