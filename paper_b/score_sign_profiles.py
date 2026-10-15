#!/usr/bin/env python3
"""Score the 26 sign-profile prompts on the base model.

CPU: --prepare-only writes the profile file and scans for country leaks.
GPU: loads the frozen 4-bit notebook loader and writes one CSV per profile.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_lib as L
import score_cohort as S
import sign_prompt as SP

DEFAULT_GPS = (
    Path(__file__).resolve().parents[1]
    / "synthetic_generation" / "outputs" / "gps_sign_relabel_all" / "gps_z_vectors.json"
)


def cohort_profiles(gps_path: Path) -> list[dict]:
    import config as C
    z = SP.load_gps_json(gps_path)
    return SP.profiles_from_gps(z, list(C.COHORT))


def combined_prompt(sign_text: str, spec: dict) -> str:
    survey = L.build_survey_user_prompt(spec, prompt_country=None)
    text = sign_text.rstrip() + "\n\n" + survey
    hits = SP.leak_hits(text)
    if hits:
        raise SystemExit(f"refusing to score a prompt that names {hits}")
    return text


def prepare(out_dir: Path, gps_path: Path) -> Path:
    rows = cohort_profiles(gps_path)
    if len(rows) != 26:
        raise SystemExit(f"expected 26 sign profiles, got {len(rows)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "sign_profiles.json"
    path.write_text(json.dumps(rows, indent=2) + "\n")
    print(f"profiles {len(rows)} -> {path}")
    return path


def score(profile_path: Path, spec_path: Path, out_dir: Path) -> int:
    profiles = json.loads(profile_path.read_text())
    spec = json.loads(spec_path.read_text())
    questions = spec["questions"]
    model, tok = S.load_base_model_and_tokenizer()
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, row in enumerate(profiles, 1):
        dest = out_dir / f"{row['profile_id']}_option_probabilities.csv"
        if dest.exists() and dest.stat().st_size > 0:
            print(f"[{i}/{len(profiles)}] {row['profile_id']} already scored, skip")
            continue
        print(f"[{i}/{len(profiles)}] {row['profile_id']} members={','.join(row['members'])}")
        rows_out = []
        for spec_q in questions:
            prompt_text = combined_prompt(row["prompt"], spec_q)
            option_scores, option_tokens = [], []
            for code in spec_q["codes"]:
                logp, ntok = S.sequence_logprob(
                    model, tok, prompt_text, f"{S.E.COMPLETION_PREFIX}{code}")
                option_scores.append(logp)
                option_tokens.append(ntok)
            probs = L.stable_softmax(option_scores, S.E.OPTION_SCORE_TEMPERATURE)
            for idx, (code, score, ntok, prob) in enumerate(
                    zip(spec_q["codes"], option_scores, option_tokens, probs)):
                rows_out.append({
                    "model": "sign_prompt",
                    "profile_id": row["profile_id"],
                    "question_id": spec_q["question_id"],
                    "option_index": idx,
                    "option_code": code,
                    "option_logprob": score,
                    "option_token_count": ntok,
                    "model_prob": prob,
                })
        import pandas as pd
        frame = pd.DataFrame(rows_out)
        sums = frame.groupby("question_id")["model_prob"].sum()
        if ((sums - 1).abs() > 1e-4).any():
            raise SystemExit(f"{row['profile_id']}: probabilities do not sum to one")
        frame.to_csv(dest, index=False)
        print(f"  wrote {dest.name} rows={len(frame)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare-only", action="store_true")
    ap.add_argument("--gps", default=str(DEFAULT_GPS))
    ap.add_argument("--profiles", default="")
    ap.add_argument("--spec", default="")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    out = Path(a.out_dir)
    if a.prepare_only:
        prepare(out, Path(a.gps))
        return 0
    if not a.profiles or not a.spec:
        raise SystemExit("scoring requires --profiles and --spec")
    return score(Path(a.profiles), Path(a.spec), out)


if __name__ == "__main__":
    raise SystemExit(main())
