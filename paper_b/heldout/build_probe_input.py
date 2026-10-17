"""Build the probe's input table from the bank-2 held-out scores. Model-only: reads no human value.

y_ui = sum_k p_k * code_k, the adapter's expected response code for held-out item i under unit u. The probe
regresses y on the 64-unit design; any per-item monotone recoding is an affine transform of y and leaves
|t| unchanged, so the expected code is the right composite.

Every item must be scored by all 64 units on the same option grid, with probabilities that sum to one.
Anything less raises: a silently missing unit would corrupt the OLS.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "paper_b"))
import factorial as F  # noqa: E402


def expected_code(frame: pd.DataFrame, item: str) -> float:
    codes = [str(c) for c in frame["option_code"]]
    p = np.asarray(frame["model_prob"], dtype=float)
    if len(set(codes)) != len(codes):
        raise ValueError(f"{item}: duplicate option codes {sorted(codes)}")
    if not np.all(np.isfinite(p)) or np.any(p < 0):
        raise ValueError(f"{item}: model_prob must be finite and non-negative")
    if abs(float(p.sum()) - 1.0) > 1e-6:
        raise ValueError(f"{item}: model_prob sums to {float(p.sum())}, not 1")
    return float(np.dot(p, np.array([float(c) for c in codes])))


def probe_values(scores: dict[str, pd.DataFrame], items: list[str]) -> pd.DataFrame:
    """scores: unit -> frame with question_id, option_code, model_prob."""
    units = F.all_units()
    missing_units = [u for u in units if u not in scores]
    if missing_units:
        raise ValueError(f"{len(missing_units)} units have no scores: {missing_units[:5]}")
    rows = []
    for item in items:
        grids = {}
        for u in units:
            frame = scores[u]
            sub = frame[frame["question_id"].astype(str) == str(item)]
            if sub.empty:
                raise ValueError(f"{item}: not scored by {u}")
            grid = tuple(sorted(str(c) for c in sub["option_code"]))
            grids.setdefault(grid, []).append(u)
        if len(grids) != 1:
            sizes = {len(g): len(us) for g, us in grids.items()}
            raise ValueError(f"{item}: option grids differ across units {sizes}")
        for u in units:
            frame = scores[u]
            sub = frame[frame["question_id"].astype(str) == str(item)]
            rows.append({"unit": u, "item": str(item), "value": expected_code(sub, item)})
    return pd.DataFrame(rows)


def load_run_dir(path: Path, units: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Read a local directory of <unit>_adapter_option_probabilities.csv files."""
    units = units or F.all_units()
    out = {}
    for u in units:
        f = Path(path) / f"{u}_adapter_option_probabilities.csv"
        if not f.is_file():
            continue
        df = pd.read_csv(f, dtype={"option_code": str, "question_id": str})
        out[u] = df
    return out


def csv_name(run_id: str, unit: str) -> str:
    return f"runs/{run_id}/synthetic/{unit}_adapter_option_probabilities.csv"


def spec_verified_units(units, run_id: str, present, spec_sha: str | None, read_manifest) -> list[str]:
    """Units whose scores exist AND (when a spec hash is given) whose manifest records that spec.

    The amended pass writes to the paths the pass it supersedes used, so the presence of a file says
    nothing about which spec it came from. Without this check the probe would average 64 units of
    which some were still scored on the pre-repair wording.
    """
    if spec_sha is not None and read_manifest is None:
        raise ValueError("spec_sha was given, so a manifest reader is required")
    out = []
    for u in units:
        if csv_name(run_id, u) not in present:
            continue
        if spec_sha is not None:
            recorded = (read_manifest(run_id, f"{u}_adapter") or {}).get("spec_sha256")
            if recorded != spec_sha:
                continue
        out.append(u)
    return out


def load_hub_run(run_id: str, repo: str, cache_dir: Path, units: list[str] | None = None,
                 spec_sha: str | None = None, read_manifest=None) -> dict[str, pd.DataFrame]:
    import os
    from huggingface_hub import HfApi, hf_hub_download
    units = units or F.all_units()
    # Pass the token explicitly: an unauthenticated listing of a private repo reads as "Repository Not
    # Found", which is indistinguishable from a real 404 and would look like an empty run.
    tok = os.environ.get("HF_TOKEN")
    present = set(HfApi(token=tok).list_repo_files(repo, repo_type="dataset"))  # an error aborts: never guess
    if spec_sha is not None and read_manifest is None:
        raise ValueError("spec_sha was given, so a manifest reader is required")
    out = {}
    for u in spec_verified_units(units, run_id, present, spec_sha, read_manifest):
        name = csv_name(run_id, u)
        p = hf_hub_download(repo, name, repo_type="dataset", local_dir=str(cache_dir), token=tok)
        out[u] = pd.read_csv(p, dtype={"option_code": str, "question_id": str})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--repo", default="Bonorinoa/SCA2-paper-b-artifacts")
    ap.add_argument("--scores-dir", default="", help="local directory instead of the Hub")
    ap.add_argument("--pool", default=str(HERE / "pool_skeleton.csv"))
    ap.add_argument("--items-file", default="", help="JSON list of item ids (default: the whole pool)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache-dir", default="")
    ap.add_argument("--spec-sha", default="",
                    help="require each unit's manifest to record this spec hash (Amendment 1 changed "
                         "the held-out wording while the run id and paths stayed the same)")
    a = ap.parse_args()
    read_manifest = None
    if a.spec_sha:
        import os
        from huggingface_hub import hf_hub_download

        def read_manifest(run_id, model):      # noqa: F811
            try:
                p = hf_hub_download(a.repo, f"runs/{run_id}/manifests/{model}_manifest.json",
                                    repo_type="dataset", token=os.environ.get("HF_TOKEN"))
            except Exception:
                return None
            return json.loads(Path(p).read_text())
    items = (json.loads(Path(a.items_file).read_text()) if a.items_file
             else [r["Question"] for r in pd.read_csv(a.pool).to_dict("records")])
    scores = (load_run_dir(Path(a.scores_dir)) if a.scores_dir
              else load_hub_run(a.run_id, a.repo, Path(a.cache_dir or f"/tmp/pb_scores/{a.run_id}"),
                                spec_sha=a.spec_sha or None, read_manifest=read_manifest))
    print(f"units with scores: {len(scores)} | items requested: {len(items)}")
    values = probe_values(scores, items)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    values.to_csv(a.out, index=False)
    print(f"wrote {a.out}: {len(values)} rows = {len(items)} items x {len(F.all_units())} units")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
