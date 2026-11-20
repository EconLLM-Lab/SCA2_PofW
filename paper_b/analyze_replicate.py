#!/usr/bin/env python3
"""Paper B — the unseeded-retrain replicate, against the original unit with the same bits.

The replicate is one profile unit (default `P_1_0_1_1_0_1`) retrained from the same recipe with no
seed fixed, scored on the same two instruments as the original (strict battery, held-out pool v1).
It is called "an unseeded retrain" and nothing else: this module never computes or cites a
weight-space cosine (verifier finding F8), because a retrain's weight geometry is not the object of
interest and a cosine over LoRA factors would not be comparable across ranks anyway.

Three quantities, each on the same bits (the same question and option cells):

  max |probability difference|     over every scored cell of each battery, with the grid compared
                                   cell by cell (a silently missing cell would hide a difference)
  Pearson of expected codes        y = sum_k p_k * code_k per item, correlated over the 23 strict
                                   items and over the 223 held-out items; the frozen-instrument
                                   E[recode] variant is reported beside it for the strict battery
  strict-surface differences       replicate minus original on each of the seven strict surfaces
                                   (patience kept as two), divided by that surface's SD over the 64
                                   profile composites of the bank-2 strict run

Inputs are local scorer CSVs. No GPU, no network, no human data.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "heldout"))
import analyze_factorial as AF  # noqa: E402
import analyze_surface as AS  # noqa: E402
from ceiling import surface_items  # noqa: E402

UNIT = "P_1_0_1_1_0_1"
INTERPRETATION = "an unseeded retrain"
ADAPTER_SUFFIX = "_adapter"
DEFAULT_POOL = HERE / "heldout" / "pool_skeleton.csv"


# --------------------------------------------------------------------- selection
def unit_frame(df: pd.DataFrame, unit: str) -> pd.DataFrame:
    """The rows of one unit: by eval_country when the frame carries it, else by model name."""
    if "eval_country" in df.columns and (df.eval_country.astype(str) == unit).any():
        sub = df[df.eval_country.astype(str) == unit]
    elif "model" in df.columns and (df.model.astype(str) == f"{unit}{ADAPTER_SUFFIX}").any():
        sub = df[df.model.astype(str) == f"{unit}{ADAPTER_SUFFIX}"]
    else:
        raise ValueError(f"no rows for unit {unit!r} in this frame")
    if sub.empty:
        raise ValueError(f"no rows for unit {unit!r} in this frame")
    return sub.copy()


def with_country(df: pd.DataFrame, unit: str | None = None) -> pd.DataFrame:
    """analyze_surface.model_item_table groups by eval_country; a single-unit file has none."""
    out = df.copy()
    if "eval_country" not in out.columns:
        if unit is None:
            name = str(out.model.iloc[0])
            unit = name[: -len(ADAPTER_SUFFIX)] if name.endswith(ADAPTER_SUFFIX) else name
        out["eval_country"] = unit
    return out


# ------------------------------------------------------------------- probability
def prob_table(df: pd.DataFrame) -> pd.Series:
    """(question_id, option_code) -> model_prob; duplicates are a corrupt input, not a tie."""
    need = {"question_id", "option_code", "model_prob"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"scorer frame missing columns: {sorted(missing)}")
    idx = pd.MultiIndex.from_arrays([df.question_id.astype(str), df.option_code.astype(str)],
                                    names=["question_id", "option_code"])
    s = pd.Series(df.model_prob.to_numpy(float), index=idx)
    if s.index.has_duplicates:
        dup = sorted(set(s.index[s.index.duplicated()]))[:3]
        raise ValueError(f"duplicate (question_id, option_code) cells, e.g. {dup}")
    if not np.all(np.isfinite(s.to_numpy())) or (s < 0).any():
        raise ValueError("model_prob must be finite and non-negative")
    return s


def max_abs_prob_diff(replicate: pd.DataFrame, original: pd.DataFrame) -> dict:
    """Largest |p_replicate - p_original| over the cells both scored, with the grid compared."""
    a, b = prob_table(replicate), prob_table(original)
    only_a = a.index.difference(b.index)
    only_b = b.index.difference(a.index)
    common = a.index.intersection(b.index)
    if len(common) == 0:
        raise ValueError("the two frames share no (question_id, option_code) cell")
    diff = (a.loc[common] - b.loc[common]).abs()
    return {"n_cells_compared": int(len(common)),
            "grids_match": bool(len(only_a) == 0 and len(only_b) == 0),
            "n_cells_only_replicate": int(len(only_a)),
            "n_cells_only_original": int(len(only_b)),
            "max_abs_prob_diff": float(diff.max()),
            "mean_abs_prob_diff": float(diff.mean())}


# ------------------------------------------------------------------ expected codes
def _item_probabilities(df: pd.DataFrame, item: str) -> tuple[list[str], np.ndarray]:
    sub = df[df.question_id.astype(str) == str(item)]
    if sub.empty:
        raise ValueError(f"{item}: not scored")
    codes = [str(c) for c in sub.option_code]
    if len(set(codes)) != len(codes):
        raise ValueError(f"{item}: duplicate option codes")
    p = np.asarray(sub.model_prob, dtype=float)
    if not np.all(np.isfinite(p)) or np.any(p < 0):
        raise ValueError(f"{item}: model_prob must be finite and non-negative")
    if abs(float(p.sum()) - 1.0) > 1e-6:
        raise ValueError(f"{item}: model_prob sums to {float(p.sum())}, not 1")
    return codes, p


def expected_codes(df: pd.DataFrame, items) -> pd.Series:
    """y = sum_k p_k * code_k per item (the probe's model quantity; build_probe_input.expected_code)."""
    out = {}
    for item in items:
        codes, p = _item_probabilities(df, item)
        out[str(item)] = float(np.dot(p, np.array([float(c) for c in codes])))
    return pd.Series(out, name="expected_code")


def expected_codes_recoded(df: pd.DataFrame, items) -> pd.Series:
    """E[recode] per item under the frozen instrument recode (analyze_surface.recode_value)."""
    out = {}
    for item in items:
        codes, p = _item_probabilities(df, item)
        out[str(item)] = float(np.dot(p, np.array([AS.recode_value(float(c), str(item)) for c in codes])))
    return pd.Series(out, name="expected_recode")


def pearson_over_items(a: pd.Series, b: pd.Series) -> dict:
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if len(d) < 2 or d.a.nunique() < 2 or d.b.nunique() < 2:
        return {"n_items": int(len(d)), "pearson": float("nan")}
    return {"n_items": int(len(d)), "pearson": float(d.a.corr(d.b))}


# ------------------------------------------------------- strict surfaces in SD units
def surface_sd_units(replicate: pd.DataFrame, original: pd.DataFrame,
                     profiles64: pd.DataFrame) -> pd.DataFrame:
    """Every strict surface: replicate - original, and that difference / the surface's 64-unit SD."""
    comp = AF.unit_composites(profiles64)
    sd = comp.pivot(index="unit", columns="surface", values="composite").std(ddof=1)
    a = AS.model_item_table(with_country(replicate)).set_index("item").e_recode
    b = AS.model_item_table(with_country(original)).set_index("item").e_recode
    rows = []
    for surface, qs in surface_items(AS.STRICT_ITEMS).items():
        if not set(qs) <= set(a.index) or not set(qs) <= set(b.index):
            raise ValueError(f"{surface}: the unit is missing one of {qs}")
        ra, rb = float(a[qs].mean()), float(b[qs].mean())
        rows.append({"surface": surface, "items": ";".join(qs), "n_items": len(qs),
                     "replicate_composite": ra, "original_composite": rb, "diff": ra - rb,
                     "sd_over_64_profiles": float(sd[surface]),
                     "diff_sd": (ra - rb) / float(sd[surface])})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------- assembly
def analyse(*, rep_strict: pd.DataFrame, orig_strict64: pd.DataFrame,
            rep_heldout: pd.DataFrame, orig_heldout: pd.DataFrame, unit: str,
            heldout_items, strict_items, results_dir, inputs: dict | None = None) -> dict:
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    strict_orig_unit = unit_frame(orig_strict64, unit)
    rep_s = unit_frame(rep_strict, unit)
    ho_rep = unit_frame(rep_heldout, unit)
    ho_orig = unit_frame(orig_heldout, unit)

    strict_codes_r = expected_codes(rep_s, strict_items)
    strict_codes_o = expected_codes(strict_orig_unit, strict_items)
    ho_codes_r = expected_codes(ho_rep, heldout_items)
    ho_codes_o = expected_codes(ho_orig, heldout_items)

    diff = pd.DataFrame({
        "battery": ["strict"] * len(strict_items) + ["heldout"] * len(heldout_items),
        "item": list(map(str, strict_items)) + list(map(str, heldout_items)),
        "replicate_expected_code": list(strict_codes_r.reindex(list(map(str, strict_items))).to_numpy())
        + list(ho_codes_r.reindex(list(map(str, heldout_items))).to_numpy()),
        "original_expected_code": list(strict_codes_o.reindex(list(map(str, strict_items))).to_numpy())
        + list(ho_codes_o.reindex(list(map(str, heldout_items))).to_numpy()),
    })
    diff["diff"] = diff.replicate_expected_code - diff.original_expected_code
    diff.to_csv(results_dir / "replicate_item_codes.csv", index=False)

    surf = surface_sd_units(rep_s, strict_orig_unit, orig_strict64)
    surf.to_csv(results_dir / "replicate_surface_diff.csv", index=False)

    out = {
        "unit": unit,
        "interpretation": INTERPRETATION,
        "what_this_compares": ("the same unit retrained from the same recipe with no seed fixed, "
                               "scored on the same instruments as the original unit"),
        "not_computed": ["weight-space cosine (verifier finding F8)"],
        "strict": {
            **max_abs_prob_diff(rep_s, strict_orig_unit),
            "n_items": int(len(strict_items)),
            "pearson_expected_codes": pearson_over_items(strict_codes_r, strict_codes_o),
            "pearson_expected_codes_recoded": pearson_over_items(
                expected_codes_recoded(rep_s, strict_items),
                expected_codes_recoded(strict_orig_unit, strict_items)),
        },
        "heldout": {
            **max_abs_prob_diff(ho_rep, ho_orig),
            "n_items": int(len(heldout_items)),
            "pearson_expected_codes": pearson_over_items(ho_codes_r, ho_codes_o),
        },
        "strict_surface_diff_sd_units": surf.set_index("surface").to_dict(orient="index"),
        "max_abs_surface_diff_sd": float(surf.diff_sd.abs().max()),
        "surface_with_largest_abs_diff_sd": str(surf.loc[surf.diff_sd.abs().idxmax(), "surface"]),
    }
    if inputs:
        out["inputs"] = inputs
    (results_dir / "replicate_analysis.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--replicate-strict", required=True, help="replicate unit, strict battery")
    ap.add_argument("--original-strict", required=True,
                    help="bank-2 strict run holding the original unit (64 profiles or one unit)")
    ap.add_argument("--replicate-heldout", required=True, help="replicate unit, held-out pool v1")
    ap.add_argument("--original-heldout", required=True, help="original unit, held-out pool v1")
    ap.add_argument("--unit", default=UNIT)
    ap.add_argument("--pool", default=str(DEFAULT_POOL), help="held-out pool skeleton (Question column)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    read = lambda p: pd.read_csv(p, dtype={"option_code": str, "question_id": str})  # noqa: E731
    paths = {"replicate_strict": a.replicate_strict, "original_strict": a.original_strict,
             "replicate_heldout": a.replicate_heldout, "original_heldout": a.original_heldout}
    heldout_items = [str(q) for q in pd.read_csv(a.pool).Question]
    out = analyse(rep_strict=read(a.replicate_strict), orig_strict64=read(a.original_strict),
                  rep_heldout=read(a.replicate_heldout), orig_heldout=read(a.original_heldout),
                  unit=a.unit, heldout_items=heldout_items,
                  strict_items=AS.all_strict_items(), results_dir=Path(a.out),
                  inputs={k: {"path": str(v), "sha256": AS.sha256_file(v)} for k, v in paths.items()})
    print(json.dumps({k: out[k] for k in ("unit", "interpretation", "strict", "heldout",
                                          "max_abs_surface_diff_sd")}, indent=1, default=float))
    print(f"wrote {a.out}/replicate_analysis.json, replicate_surface_diff.csv, replicate_item_codes.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
