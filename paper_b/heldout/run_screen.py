#!/usr/bin/env python3
"""Run the preregistered held-out screen (Tier 1 item 2) against the frozen selection.

Inputs
  FREEZE.json        read FIRST and through require_freeze(): both the selection and the pool are
                     re-hashed, so this cannot run against an un-frozen or since-changed selection
  data/wvs_eval_full/<CC>_WVS_wave7.parquet
                     per-country WVS-7 respondent frames; the human surface is the survey-weighted
                     country mean of the RAW code (screen_test requires raw codes: direction is
                     carried by the item's sign, so recoding, as the phase-2 composites do, would
                     destroy it). An item-country cell needs >= 50 valid weighted respondents,
                     the same floor the phase-2 pipeline uses.
  ts_crosswalk.json  pool item -> accepted WVS-7 variable
  data/GPS/GPS_dataset_country_level/country_gps.dta
                     country GPS z, loaded exactly as analysis/phase2/13_unified_comparison.py does

Output: the registered statistics (A, permutation p over items, country bootstrap CI) as JSON.

usage: run_screen.py [--out path.json]
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
sys.path.insert(0, str(HERE))
import freeze as FR  # noqa: E402
import screen_test as ST  # noqa: E402

WVS7 = REPO / "data/WVS/WVS_wave7.dta"   # the pool's Qnnn items ARE WVS-7 variables, so no crosswalk
GPS_DTA = REPO / "data/GPS/GPS_dataset_country_level/country_gps.dta"
CEILING = REPO / "planning/sprint_2026-10-11/paper-b-tier1/results/ceiling_surfaces.csv"
DIMS = ["patience", "risktaking", "posrecip", "negrecip", "altruism", "trust"]
MIN_N = 50


def load_gps() -> pd.DataFrame:
    return pd.read_stata(GPS_DTA).set_index("isocode")[DIMS]


def human_surface(items: list[str]) -> tuple[pd.DataFrame, dict]:
    """Country x item survey-weighted means of the RAW code, straight from WVS wave 7."""
    import pyreadstat

    usecols = ["B_COUNTRY_ALPHA", "W_WEIGHT"] + items
    df, _ = pyreadstat.read_dta(str(WVS7), usecols=usecols, encoding="latin1")
    meta = {"countries": 0, "items_requested": len(items), "cells_below_floor": 0}
    rows = {}
    for cc, g in df.groupby("B_COUNTRY_ALPHA"):
        w = g["W_WEIGHT"].fillna(0)
        vals = {}
        for q in items:
            v = pd.to_numeric(g[q], errors="coerce").astype(float)
            mask = (v >= 0) & (w > 0)
            if mask.sum() < MIN_N:
                vals[q] = np.nan
                meta["cells_below_floor"] += 1
                continue
            vals[q] = float((v[mask] * w[mask]).sum() / w[mask].sum())
        rows[cc] = vals
        meta["countries"] += 1
    return pd.DataFrame.from_dict(rows, orient="index"), meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--freeze", default=str(HERE / "FREEZE.json"))
    ap.add_argument("--out", default=str(HERE / "screen_result.json"))
    a = ap.parse_args()

    frozen = FR.require_freeze(Path(a.freeze))          # fails closed if unfrozen or changed
    sel = pd.read_csv(frozen["selection_path"])
    pool = pd.read_csv(frozen["pool_path"])
    items = [str(q) for q in pool["Question"]]
    print(f"frozen {frozen['frozen_at'][:19]} | selection {Path(frozen['selection_path']).name}"
          f" | pool items {len(items)}")

    if "t_top" not in sel.columns:
        raise SystemExit("selection has no t_top column; cannot derive the item signs")
    sel = sel.assign(sign=np.sign(sel.t_top.to_numpy(float)))
    abstained = sel[(sel.top_dimension == "none") | (sel.sign == 0)]
    if len(abstained):
        raise SystemExit(f"{len(abstained)} rows abstained (sign 0 / 'none'); drop them before scoring")
    print(f"selection: {len(sel)} items, {int(sel.primary_selected.sum())} primary, "
          f"signs {sorted(set(sel.sign))}")

    human, meta = human_surface(items)
    gps = load_gps()
    covered = [q for q in sel.question_id if q in human.columns]
    print(f"human surface: {human.shape[0]} countries x {human.shape[1]} items "
          f"({meta['cells_below_floor']} item-country cells below the {MIN_N}-respondent floor)")
    print(f"countries shared with GPS: {len(human.index.intersection(gps.index))} | "
          f"selected items with human data: {len(covered)} of {len(sel)}")

    res = ST.screen(sel, human, gps)                    # registered draws/seed defaults
    res["cells_below_floor"] = meta["cells_below_floor"]
    if CEILING.is_file():
        c = pd.read_csv(CEILING)
        res["ceiling_w6_w7"] = {str(k): float(v) for k, v in
                                c.set_index("surface")["spearman_w6_w7"].dropna().items()}
    Path(a.out).write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "ceiling_w6_w7"}, indent=2))
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
