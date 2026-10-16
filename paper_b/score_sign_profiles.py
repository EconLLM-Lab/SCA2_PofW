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


def all_profile_rows() -> list[dict]:
    """One sign prompt per cell of the 2^6 factorial, ids equal to the adapter units."""
    import factorial as F
    rows = []
    for unit in F.all_units():
        signs = {d: ("positive" if bit else "negative")
                 for d, bit in zip(F.DIMS, F.bits_of_unit(unit))}
        prompt = SP.sign_prompt(signs)
        hits = SP.leak_hits(prompt)
        if hits:
            raise SystemExit(f"sign prompt leaked {hits}")
        rows.append({"profile_id": unit, "signs": signs, "prompt": prompt, "members": []})
    return rows


def select_profiles(rows: list[dict], only: list[str]) -> list[dict]:
    unknown = sorted(set(only) - {r["profile_id"] for r in rows})
    if unknown:
        raise SystemExit(f"unknown profile ids: {unknown[:3]}")
    keep = set(only)
    return [r for r in rows if r["profile_id"] in keep]


def rows_per_profile(spec: dict) -> int:
    return sum(len(q["codes"]) for q in spec["questions"])


def prepare(out_dir: Path, gps_path: Path, units: str = "cohort26") -> Path:
    if units == "all64":
        rows = all_profile_rows()
        if len(rows) != 64:
            raise SystemExit(f"expected 64 sign profiles, got {len(rows)}")
    else:
        rows = cohort_profiles(gps_path)
        if len(rows) != 26:
            raise SystemExit(f"expected 26 sign profiles, got {len(rows)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "sign_profiles.json"
    path.write_text(json.dumps(rows, indent=2) + "\n")
    print(f"profiles {len(rows)} -> {path}")
    return path


def done_profiles(files, run_id: str) -> set[str]:
    """A profile is done only with its CSV AND its manifest; a bare CSV is not trusted."""
    fs = set(files)
    pre, suf = f"runs/{run_id}/synthetic/", "_option_probabilities.csv"
    csv_ids = {f[len(pre):-len(suf)] for f in fs if f.startswith(pre) and f.endswith(suf)}
    return {p for p in csv_ids if f"runs/{run_id}/manifests/{p}_manifest.json" in fs}


def hub_done(repo: str, run_id: str) -> set[str]:
    from huggingface_hub import HfApi
    return done_profiles(HfApi().list_repo_files(repo, repo_type="dataset"), run_id)   # a listing error aborts


def profile_manifest(*, run_id: str, profile_id: str, csv_sha256: str, n_rows: int, spec_sha256: str,
                     code_revision: str) -> dict:
    import time
    import score_runtime as R
    return {"run_id": run_id, "model": "sign_prompt", "profile_id": profile_id, "csv_sha256": csv_sha256,
            "n_rows": int(n_rows), "spec_sha256": spec_sha256, "code_revision_sha256": code_revision,
            "stack_versions": R.package_versions(), "sanitized": True, "contains_human_data": False,
            "persisted_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def upload_profile(repo: str, run_id: str, dest: Path, pid: str, manifest: dict) -> None:
    """CSV first, manifest last: the manifest marks the profile done, so an interrupted upload is redone."""
    import json as _json
    import hub_io
    from huggingface_hub import HfApi
    api = HfApi()
    hub_io._retry(lambda: api.upload_file(
        path_or_fileobj=str(dest), path_in_repo=f"runs/{run_id}/synthetic/{pid}_option_probabilities.csv",
        repo_id=repo, repo_type="dataset", commit_message=f"{run_id}: {pid} sign-prompt option probabilities"),
        f"upload {pid}")
    hub_io._retry(lambda: api.upload_file(
        path_or_fileobj=_json.dumps(manifest, indent=2).encode(), path_in_repo=f"runs/{run_id}/manifests/{pid}_manifest.json",
        repo_id=repo, repo_type="dataset", commit_message=f"{run_id}: {pid} manifest"), f"upload {pid} manifest")


def score(profile_path: Path, spec_path: Path, out_dir: Path,
          hub_repo: str = "", hub_run: str = "") -> int:
    profiles = json.loads(profile_path.read_text())
    spec = json.loads(spec_path.read_text())
    questions = spec["questions"]
    done = hub_done(hub_repo, hub_run) if hub_run else set()
    todo = [p for p in profiles if p["profile_id"] not in done]
    print(f"{len(profiles)} profiles requested; {len(done & {p['profile_id'] for p in profiles})} already on the Hub; {len(todo)} to score")
    if not todo:
        return 0
    model, tok = S.load_base_model_and_tokenizer()
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, row in enumerate(profiles, 1):
        dest = out_dir / f"{row['profile_id']}_option_probabilities.csv"
        if row["profile_id"] in done:
            print(f"[{i}/{len(profiles)}] {row['profile_id']} on the Hub, skip")
            continue
        if dest.exists() and dest.stat().st_size > 0 and not hub_run:
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
        if len(frame) != rows_per_profile(spec):
            raise SystemExit(f"{row['profile_id']}: {len(frame)} rows, spec expects {rows_per_profile(spec)}")
        frame.to_csv(dest, index=False)
        print(f"  wrote {dest.name} rows={len(frame)}")
        if hub_run:
            import hashlib
            import score_runtime as R
            man = profile_manifest(run_id=hub_run, profile_id=row["profile_id"],
                                   csv_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(), n_rows=len(frame),
                                   spec_sha256=spec.get("spec_sha256", ""),
                                   code_revision=R.code_revision(Path(__file__).resolve().parents[1]))
            upload_profile(hub_repo, hub_run, dest, row["profile_id"], man)
            print(f"  uploaded {row['profile_id']} -> runs/{hub_run}/synthetic/")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare-only", action="store_true")
    ap.add_argument("--gps", default=str(DEFAULT_GPS))
    ap.add_argument("--profiles", default="")
    ap.add_argument("--spec", default="")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--units", choices=["cohort26", "all64"], default="cohort26")
    ap.add_argument("--only", nargs="*", default=[], help="score only these profile ids")
    ap.add_argument("--hub-repo", default="Bonorinoa/SCA2-paper-b-artifacts")
    ap.add_argument("--hub-run", default="", help="run id: upload each profile and resume from the Hub listing")
    a = ap.parse_args()
    out = Path(a.out_dir)
    if a.prepare_only:
        prepare(out, Path(a.gps), a.units)
        return 0
    if not a.profiles or not a.spec:
        raise SystemExit("scoring requires --profiles and --spec")
    if a.only:
        sel = select_profiles(json.loads(Path(a.profiles).read_text()), a.only)
        sub = out / "selected_profiles.json"
        out.mkdir(parents=True, exist_ok=True)
        sub.write_text(json.dumps(sel, indent=2) + "\n")
        a.profiles = str(sub)
    return score(Path(a.profiles), Path(a.spec), out, a.hub_repo, a.hub_run)


if __name__ == "__main__":
    raise SystemExit(main())
