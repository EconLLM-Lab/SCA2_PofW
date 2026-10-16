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


def load_hub_run(run_id: str, repo: str, cache_dir: Path, units: list[str] | None = None) -> dict[str, pd.DataFrame]:
    from huggingface_hub import HfApi, hf_hub_download
    units = units or F.all_units()
    present = set(HfApi().list_repo_files(repo, repo_type="dataset"))   # an error aborts: never guess
    out = {}
    for u in units:
        name = f"runs/{run_id}/synthetic/{u}_adapter_option_probabilities.csv"
        if name not in present:
            continue
        p = hf_hub_download(repo, name, repo_type="dataset", local_dir=str(cache_dir))
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
    a = ap.parse_args()
    items = (json.loads(Path(a.items_file).read_text()) if a.items_file
             else [r["Question"] for r in pd.read_csv(a.pool).to_dict("records")])
    scores = (load_run_dir(Path(a.scores_dir)) if a.scores_dir
              else load_hub_run(a.run_id, a.repo, Path(a.cache_dir or f"/tmp/pb_scores/{a.run_id}")))
    print(f"units with scores: {len(scores)} | items requested: {len(items)}")
    values = probe_values(scores, items)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    values.to_csv(a.out, index=False)
    print(f"wrote {a.out}: {len(values)} rows = {len(items)} items x {len(F.all_units())} units")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
