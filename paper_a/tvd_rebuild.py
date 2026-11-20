#!/usr/bin/env python3
"""Rebuild Paper A's per-cell model-to-human distance (tvd) locally.

The public repository ships no values derived from survey respondents, so the
`tvd` column is not in country_item_scores.csv there. It is rebuilt here from

  * paper_a/inputs/model_option_probs.csv   model option probabilities (committed, no human column)
  * data/wvs_eval_full/*_WVS_wave7.parquet  the WVS wave-7 microdata you download from WVSA
  * data/GPS/GPS_dataset_country_level/country_gps.dta   the GPS country file (Falk et al. 2018)

Method (identical to 13_unified_comparison.item_metrics and 16_non_llm_baseline):
  p_human  weighted share of each option (W_WEIGHT, valid codes >= 0, weight > 0, n >= 50), built on the
           model option grid of the adapter arm; options absent from the raw data get probability 0 (not dropped).
  tvd      0.5 * sum |p_model - p_human| after an inner merge on option_value and renormalising both sides.
  armA/armB  non-LLM baselines from paper_a/16_non_llm_baseline.arm_distributions with the GPS z-scores
             (b = 0.5, clamped). uniform = 1/k on the grid.
Eight arms x 428 cells; reproduces the frozen column to <= 1e-15.

Run:  env -u PYTHONPATH .venv/bin/python paper_a/tvd_rebuild.py
Writes paper_a/outputs/paper_a/country_item_scores_tvd.csv (gitignored) and prints the headline means.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
WVS_DIR = REPO / "data" / "wvs_eval_full"
GPS_DTA = REPO / "data" / "GPS" / "GPS_dataset_country_level" / "country_gps.dta"
MODEL_PROBS = REPO / "paper_a" / "inputs" / "model_option_probs.csv"
SCORES = REPO / "paper_a" / "outputs" / "paper_a" / "country_item_scores.csv"
OUT_TVD = REPO / "paper_a" / "outputs" / "paper_a" / "country_item_scores_tvd.csv"
GRID_ARM = "adapter"  # option grid used for p_human, armA/armB and uniform
MIN_N = 50
DIMS = ["patience", "risktaking", "posrecip", "negrecip", "altruism", "trust"]
HEADLINE_ARMS = ["adapter", "base", "persona", "adapter_persona"]
DATA_MSG = ("tvd is not shipped (it derives from survey respondents). Rebuild it with "
            "`python paper_a/tvd_rebuild.py` after placing the WVS and GPS downloads under data/ (see DATA.md).")


def _load_script(filename: str):
    spec = importlib.util.spec_from_file_location(filename.split(".")[0].replace("-", "_") + "_mod",
                                                  REPO / "paper_a" / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REPO))
    spec.loader.exec_module(mod)
    return mod


def load_model_probs(path: Path = MODEL_PROBS) -> pd.DataFrame:
    return pd.read_csv(path, float_precision="round_trip")


def build_p_human(model: pd.DataFrame, wvs_dir: Path = WVS_DIR) -> pd.DataFrame:
    """Weighted human option shares on the model grid, zero-filled. Columns: eval_country, question_id, option_value, population_prob."""
    import pyarrow.parquet as pq

    grid = model[model.arm == GRID_ARM][["country", "question_id", "option_value"]]
    items = sorted(grid.question_id.unique())
    out = []
    for cc, gc in grid.groupby("country"):
        f = Path(wvs_dir) / f"{cc}_WVS_wave7.parquet"
        names = set(pq.ParquetFile(f).schema.names)
        df = pd.read_parquet(f, columns=["W_WEIGHT"] + [q for q in items if q in names])
        w = df["W_WEIGHT"].fillna(0).astype(float)
        for q, gq in gc.groupby("question_id"):
            if q not in df:
                continue
            v = df[q].astype(float)
            keep = (v >= 0) & np.isfinite(v) & (w > 0)
            if int(keep.sum()) < MIN_N:
                continue
            share = pd.DataFrame({"option_value": v[keep].values, "w": w[keep].values}).groupby("option_value").w.sum()
            share = share / share.sum()
            ph = gq["option_value"].astype(float).map(share).fillna(0.0)  # zero-fill options absent in raw data
            out.append(pd.DataFrame({"eval_country": cc, "question_id": q,
                                     "option_value": gq["option_value"].astype(float).values,
                                     "population_prob": ph.values}))
    return pd.concat(out, ignore_index=True)


def load_gps_z(gps_dta: Path = GPS_DTA) -> pd.DataFrame:
    """GPS country file -> long frame (country, dim, z). The dta columns are the z-scores used by the paper."""
    gps = pd.read_stata(gps_dta, convert_categoricals=False).set_index("isocode")
    return pd.DataFrame([{"country": c, "dim": d, "z": float(gps.loc[c, d])}
                         for c in gps.index for d in DIMS])


def synthetic_arms(p_human: pd.DataFrame, z_df: pd.DataFrame) -> pd.DataFrame:
    """armA, armB (GPS z, b = 0.5, clamped) and uniform on the p_human grid. Columns: arm, country, question_id, option_value, model_prob."""
    nl = _load_script("16_non_llm_baseline.py")
    parts = []
    for arm in ("armA", "armB"):
        o = nl.arm_distributions(z_df, p_human, arm)
        parts.append(o.rename(columns={"eval_country": "country"})[["country", "question_id", "option_value", "model_prob"]].assign(arm=arm))
    u = p_human.rename(columns={"eval_country": "country"})[["country", "question_id", "option_value"]].copy()
    u["model_prob"] = 1.0 / u.groupby(["country", "question_id"]).option_value.transform("size")
    parts.append(u.assign(arm="uniform"))
    return pd.concat(parts, ignore_index=True)


def tvd_cells(opts: pd.DataFrame, p_human: pd.DataFrame) -> pd.DataFrame:
    """tvd per (arm, country, item) by the item_metrics rule."""
    ph = {k: g for k, g in p_human.groupby(["eval_country", "question_id"])}
    rows = []
    for (arm, cc, q), d in opts.groupby(["arm", "country", "question_id"]):
        if (cc, q) not in ph:
            continue
        d = d.drop_duplicates("option_value").sort_values("option_value")
        m = pd.DataFrame({"option_value": d.option_value.astype(float).values,
                          "pm": d.model_prob.astype(float).values}).merge(
            ph[(cc, q)][["option_value", "population_prob"]], on="option_value", how="inner")
        if len(m) < 2:
            continue
        pm = m.pm.values / m.pm.values.sum()
        pp = m.population_prob.values / m.population_prob.values.sum()
        rows.append({"arm": arm, "country": cc, "item": q, "tvd": 0.5 * np.abs(pm - pp).sum()})
    return pd.DataFrame(rows)


def rebuild_tvd(model_probs: Path = MODEL_PROBS, wvs_dir: Path = WVS_DIR, gps_dta: Path = GPS_DTA) -> pd.DataFrame:
    model = load_model_probs(model_probs)
    p_human = build_p_human(model, wvs_dir)
    allopts = pd.concat([model, synthetic_arms(p_human, load_gps_z(gps_dta))], ignore_index=True)
    res = tvd_cells(allopts, p_human)
    return res.sort_values(["arm", "country", "item"]).reset_index(drop=True)


def strict_items() -> list[str]:
    """The 23 strict items, as defined in 22_paper_a_surface.STRICT_ITEMS."""
    s = _load_script("22_paper_a_surface.py").STRICT_ITEMS
    return [q for qs in s.values() for q in qs]


def headline_means(tvd: pd.DataFrame, arms=HEADLINE_ARMS) -> dict[str, float]:
    """Mean tvd over all cells of the strict items, per arm."""
    s = tvd[tvd.item.isin(strict_items())]
    return {a: float(s[s.arm == a].tvd.mean()) for a in arms}


def load_tvd(scores: Path = SCORES, rebuilt: Path = OUT_TVD) -> pd.DataFrame:
    """tvd per (arm, country, item): the committed column if present, else the rebuilt file, else a clear failure."""
    if Path(scores).exists():
        d = pd.read_csv(scores)
        if "tvd" in d.columns and d.loc[d.arm != "human", "tvd"].notna().all():
            return d.loc[d.arm != "human", ["arm", "country", "item", "tvd"]].reset_index(drop=True)
    if Path(rebuilt).exists():
        return pd.read_csv(rebuilt)
    raise SystemExit(DATA_MSG)


def main() -> None:
    for p in [MODEL_PROBS, GPS_DTA]:
        if not p.exists():
            raise SystemExit(f"missing input {p}. {DATA_MSG}")
    if not any(WVS_DIR.glob("*_WVS_wave7.parquet")):
        raise SystemExit(f"missing WVS parquet files in {WVS_DIR}. {DATA_MSG}")
    res = rebuild_tvd()
    OUT_TVD.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT_TVD, index=False)
    print(f"wrote {OUT_TVD.relative_to(REPO)}: {len(res)} cells, arms {sorted(res.arm.unique())}")
    n = len(strict_items())
    print(f"headline mean tvd on the {n} strict items:")
    for a, m in headline_means(res).items():
        print(f"  {a:16s} {m:.4f}")


if __name__ == "__main__":
    main()
