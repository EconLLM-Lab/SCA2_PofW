# VM-side driver for card C9-4 experiment A: the adapter + persona cell.
#   For each of the 42 cohort countries, load that country's cohort-1 adapter (adapters/<CC> at the pinned
#   revision 7550fd4c) AND prompt it with the C8 country-named persona of the same country, then score the strict
#   battery (spec persona_strict_v1, the same spec as C8). Run id adapter-persona-strict-v1-20261019, model names
#   <CC>_adapter_persona (the names paper_b/c9_tvd.py expects).
#
# Gates, all before any adapter+persona unit is scored; any failure exits non-zero and scores nothing:
#   G1  the spec built here hashes to the pinned persona_strict_v1 spec.
#   G3  the fresh base model reproduces the banked strict base (bank2-strict-v1-20261016) within the Paper B
#       base tolerances.
#   G2  the cohort-1 ARG adapter, scored WITHOUT the persona, reproduces the banked cohort-1 ARG adapter rows
#       (run paper-b-20261011, planning/.../model_probs.csv) within the same tolerances; it must also differ from
#       the base (so the adapter is really applied); and disabling it must give back the base (switchback).
# Resume reads the Hub (CSV + manifest recorded under this spec), never the VM disk.
# Run it as a child with SCA2_PB_UNITS=countries (vm_c9_launch.py does this); the file is uploaded to the VM,
# so the run summary records its SHA-256 instead of the checkout revision.
import hashlib
import json
import os
import sys
import time
from pathlib import Path

REPO = Path("/content/SCA2_PofW")
sys.path[:0] = [str(REPO / "paper_b"), str(REPO / "paper_b" / "colab")]

RUN_ID = "adapter-persona-strict-v1-20261019"
COHORT1_REVISION = "7550fd4cfe514470bb8d80918a43c9ae424d26b5"
COHORT1_RUN = "paper-b-20261011"
COHORT1_SCORES = REPO / "planning/sprint_2026-10-11/paper-b-20261011/model_probs.csv"
GATE_COUNTRY = "ARG"
MIN_ADAPTER_EFFECT = 1e-3       # max |p_adapter - p_base| over the battery must exceed this, or no adapter acted


def main() -> int:
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("REFUSING: HF_TOKEN is not set; no model loaded"); return 2
    if os.environ.get("SCA2_PB_UNITS") != "countries":
        print("REFUSING: SCA2_PB_UNITS must be 'countries' (cohort-1 adapters live at adapters/<CC>)"); return 2
    if os.environ.get("SCA2_PB_PROTOCOL") == "bank2":       # the bank-2 switch moves every adapter path to bank2/
        print("REFUSING: SCA2_PB_PROTOCOL=bank2 would point the resolver at bank-2 adapters"); return 2

    import pandas as pd
    import config as C
    import eval_config as E
    import score_cohort as SC
    import score_plan as SPL
    import score_runtime as R
    from build_scoring_spec import write_spec
    from huggingface_hub import HfApi, hf_hub_download

    countries = sorted(SPL.PERSONA_COUNTRIES)
    if sorted(C.COHORT) != countries:
        print("REFUSING: config.COHORT is not the 42 cohort countries under SCA2_PB_UNITS=countries"); return 2
    if C.hub_adapter_path(GATE_COUNTRY) != f"adapters/{GATE_COUNTRY}":
        print(f"REFUSING: adapter path is {C.hub_adapter_path(GATE_COUNTRY)!r}, not the cohort-1 prefix"); return 2

    # ---- G1: spec pin
    pins = json.loads(SPL.PINS.read_text())
    spec = SPL.build_spec("persona_strict_v1")
    spec_sha = SPL.spec_hash(spec)
    if spec_sha != pins["spec_sha256"]["persona_strict_v1"]:
        print(f"G1 REFUSING: spec {spec_sha[:12]} != pinned persona_strict_v1"); return 2
    root = Path(os.environ.get("SCA2_PB_DATA_ROOT", "/content/pb_data"))
    spec = R.load_spec(write_spec(spec, root / "specs" / "adapter_persona_strict_v1.json"))
    questions = spec["questions"]
    print(f"G1 ok: spec {spec_sha[:12]} | {len(questions)} questions | {len(countries)} countries")

    api = HfApi(token=token)
    store = R.HuggingFaceArtifactStore()
    local_dir = E.DATA_ROOT / "local_scores"
    driver_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    def listing():
        return api.list_repo_files(SPL.ARTIFACTS_REPO, repo_type="dataset")   # an error aborts the run

    def read_manifest(run_id, model):
        p = hf_hub_download(SPL.ARTIFACTS_REPO, f"runs/{run_id}/manifests/{model}_manifest.json",
                            repo_type="dataset", token=token)
        return json.loads(Path(p).read_text())

    def upload_json(obj, name):
        api.upload_file(path_or_fileobj=json.dumps(obj, indent=2).encode(), path_in_repo=f"runs/{RUN_ID}/{name}",
                        repo_id=SPL.ARTIFACTS_REPO, repo_type="dataset", commit_message=f"{RUN_ID}: {name}")

    t0 = time.time()
    base, tok = SC.load_base_model_and_tokenizer()
    print(f"base loaded in {time.time() - t0:.0f} s")

    # ---- G3: base parity against the banked strict base
    t = time.time()
    base_new = SC.score_model_questions(base, tok, "base", questions, prompt_country=None)
    p = hf_hub_download(SPL.ARTIFACTS_REPO, f"runs/{SPL.PERSONA_BASE_REFERENCE_RUN}/synthetic/base_option_probabilities.csv",
                        repo_type="dataset", token=token)
    banked_base = pd.read_csv(p, dtype={"question_id": str, "option_code": str})
    g3 = SPL.base_parity(base_new.astype({"question_id": str, "option_code": str}), banked_base)
    print(f"G3 base parity ({time.time() - t:.0f} s): {json.dumps(g3)}")

    # ---- G2: cohort-1 ARG adapter without persona vs its banked scores; adapter effect; switchback
    from peft import PeftModel
    t = time.time()
    adir, source = R.resolve_adapter(GATE_COUNTRY, COHORT1_REVISION, E.ADAPTER_CACHE_DIR)
    peft = PeftModel.from_pretrained(base, str(adir), adapter_name=GATE_COUNTRY, is_trainable=False)
    peft.set_adapter(GATE_COUNTRY)
    plain = SC.score_model_questions(peft, tok, f"{GATE_COUNTRY}_adapter", questions, prompt_country=None)
    plain = plain.astype({"question_id": str, "option_code": str})
    banked = pd.read_csv(COHORT1_SCORES, dtype={"question_id": str, "option_code": str})
    banked = banked[(banked.model == "adapter") & (banked.eval_country == GATE_COUNTRY)]
    g2_parity = SPL.base_parity(plain, banked)
    g2_parity["reference_run"] = COHORT1_RUN
    effect = SPL.base_parity(plain, base_new.astype({"question_id": str, "option_code": str}))["max_dprob"]
    with peft.disable_adapter():
        back = SC.score_model_questions(peft, tok, "base", questions, prompt_country=None)
    sb = SPL.base_parity(back.astype({"question_id": str, "option_code": str}),
                         base_new.astype({"question_id": str, "option_code": str}))
    g2 = {"country": GATE_COUNTRY, "adapter_revision": COHORT1_REVISION, "adapter_source": source,
          "adapter_sha256": R.adapter_sha256(adir), "parity_vs_banked_cohort1": g2_parity,
          "adapter_effect_max_dprob": effect, "adapter_effect_min": MIN_ADAPTER_EFFECT,
          "switchback_vs_base": sb, "seconds": round(time.time() - t, 1)}
    g2["pass"] = bool(g2_parity["pass"] and effect > MIN_ADAPTER_EFFECT and sb["pass"])
    print(f"G2 adapter gate: {json.dumps(g2)}")

    gates = {"run_id": RUN_ID, "spec_sha256": spec_sha, "driver_sha256": driver_sha, "G3": g3, "G2": g2,
             "gate_pass": bool(g3["pass"] and g2["pass"]), "packages": R.package_versions()}
    upload_json(gates, "gates.json")
    if not gates["gate_pass"]:
        print("GATES FAILED: no adapter+persona unit scored"); return 3
    print("GATES PASS")

    # ---- the 42 adapter+persona units
    def done(cc):
        return SPL._present(RUN_ID, listing(), f"{cc}_adapter_persona", spec_sha, read_manifest)

    timings = {}
    for cc in countries:
        name = f"{cc}_adapter_persona"
        if done(cc):
            print(f"{name}: on the Hub under this spec, skipped"); continue
        t = time.time()
        adir, source = R.resolve_adapter(cc, COHORT1_REVISION, E.ADAPTER_CACHE_DIR)
        if cc not in peft.peft_config:
            peft.load_adapter(str(adir), adapter_name=cc, is_trainable=False)
        peft.set_adapter(cc)
        if peft.active_adapter != cc:
            print(f"REFUSING: active adapter is {peft.active_adapter!r}, not {cc}"); return 4
        df = SC.score_model_questions(peft, tok, name, questions, prompt_country=cc)
        reason = R.validate_scored_frame(df.astype({"option_code": str}), questions)
        if reason:
            print(f"REFUSING: {name} scored output invalid: {reason}"); return 4
        df = df.copy()
        df["run_id"] = RUN_ID
        df["adapter_revision"] = COHORT1_REVISION
        R.persist_unit_scores(scores=df, model_name=name, run_id=RUN_ID, repo=SPL.ARTIFACTS_REPO, hub=store,
                              adapter_sha256=R.adapter_sha256(adir), code_revision=f"uploaded-driver:{driver_sha}",
                              local_dir=local_dir, spec_sha=spec_sha, adapter_revision=COHORT1_REVISION)
        if cc != GATE_COUNTRY:
            peft.delete_adapter(cc)          # keep GPU memory flat; ARG stays loaded from the gate
        timings[cc] = round(time.time() - t, 1)
        print(f"{name}: scored + persisted from {source} in {timings[cc]} s")

    missing = [cc for cc in countries if not done(cc)]
    summary = {"run_id": RUN_ID, "spec_sha256": spec_sha, "driver_sha256": driver_sha,
               "adapter_revision": COHORT1_REVISION, "units_expected": len(countries),
               "units_missing": missing, "unit_seconds": timings, "wall_seconds": round(time.time() - t0, 1)}
    upload_json(summary, "run_summary.json")
    print(f"C9A_DONE missing={len(missing)} {missing[:5]}")
    return 0 if not missing else 4


if __name__ == "__main__":
    sys.exit(main())
