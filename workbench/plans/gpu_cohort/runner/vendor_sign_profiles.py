"""Build-time vendoring of the 26 sign-profile prompts (W2 prompt route). Not used at capture time.

Reads the Paper B module `paper_b/sign_prompt.py` from the MAIN worktree by file path, regenerates each
prompt from its six signs, and writes `plans/gpu_cohort/sign_profiles.json` with the prompt text, its sha256 and
the archived Paper B sign-prompt scores (`sign_out/<profile>_option_probabilities.csv`, model-only).
Country membership is NOT copied: the sign vectors are derived from the human GPS table (common.md rule 2).

    env -u PYTHONPATH uv run --project workbench python workbench/plans/gpu_cohort/runner/vendor_sign_profiles.py \
        /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW
"""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

PACKAGE = Path(__file__).resolve().parents[1]
SIGNPROMPT = Path("planning/sprint_2026-10-11/paper-b-signprompt")


def load_module(path):
    spec = importlib.util.spec_from_file_location("paper_b_sign_prompt", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def archive_for(csv_path, source):
    """{item_id: {source, probs, logprobs}} from one profile's Paper B option-probability CSV."""
    out = {}
    with Path(csv_path).open(newline="") as f:
        for row in csv.DictReader(f):
            item = out.setdefault(f"wvs_{row['question_id']}", {"source": source, "probs": {}, "logprobs": {}})
            item["probs"][row["option_code"]] = float(row["model_prob"])
            item["logprobs"][row["option_code"]] = float(row["option_logprob"])
    return out


def main(main_root):
    root = Path(main_root)
    module_path = root / "paper_b" / "sign_prompt.py"
    sp = load_module(module_path)
    raw = json.loads((root / SIGNPROMPT / "sign_profiles.json").read_text())
    items = {x["item_id"] for x in json.loads((PACKAGE / "items.json").read_text())["items"]}
    profiles = []
    for row in raw:
        signs = {d: row["signs"][d] for d in sp.DIMS}
        prompt = sp.sign_prompt(signs)
        assert prompt == row["prompt"], f"{row['profile_id']}: regenerated prompt differs from Paper B's file"
        assert sp.profile_id(signs) == row["profile_id"] and not sp.leak_hits(prompt)
        arch = archive_for(root / SIGNPROMPT / "sign_out" / f"{row['profile_id']}_option_probabilities.csv",
                           f"paper-b-signprompt/sign_out/{row['profile_id']}_option_probabilities.csv "
                           "(run sign-prompt-20261011)")
        assert set(arch) == items, f"{row['profile_id']}: archive items differ from items.json"
        profiles.append({"profile_id": row["profile_id"], "signs": signs, "prompt": prompt,
                         "prompt_sha256": sha(prompt), "archive": arch})
    profiles.sort(key=lambda p: p["profile_id"])
    assert len(profiles) == 26
    doc = {"source_module": "paper_b/sign_prompt.py", "source_module_sha256":
           hashlib.sha256(module_path.read_bytes()).hexdigest(), "dims": list(sp.DIMS),
           "combine": "sign_prompt + blank line + survey_prompt_v1 (paper_b/score_sign_profiles.py::combined_prompt)",
           "profiles": profiles}
    out = PACKAGE / "sign_profiles.json"
    out.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print("WROTE", out, len(profiles), "profiles; module sha", doc["source_module_sha256"][:12])


if __name__ == "__main__":
    main(sys.argv[1])
