#!/usr/bin/env python3
"""Run the preregistered held-out screen (Tier 1 item 2) against the frozen selection.

Inputs
  FREEZE.json        read FIRST and through require_freeze(): both the selection and the pool are
                     re-hashed, so this cannot run against an un-frozen or since-changed selection
  data/WVS/WVS_wave7.dta
                     the human surface is the survey-weighted (W_WEIGHT) country mean of the RAW
                     code, codes < 0 missing (PREREGISTRATION section 4). Raw, because screen_test
                     carries direction in the item's sign; recoding would destroy it. The pool's
                     Qnnn items are WVS-7 variables, so no crosswalk is involved. No respondent
                     floor is registered; `min_n` exists only for the labelled sensitivity check.
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
DIMS = ["patience", "risktaking", "posrecip", "negrecip", "altruism", "trust"]
MIN_N = 1          # registered: any valid respondent (section 4 sets only codes < 0 missing)
SENSITIVITY_MIN_N = 50


def load_gps() -> pd.DataFrame:
    return pd.read_stata(GPS_DTA).set_index("isocode")[DIMS]


def human_surface(items: list[str], min_n: int = MIN_N) -> tuple[pd.DataFrame, dict]:
    """Country x item survey-weighted means of the RAW code, straight from WVS wave 7."""
    import pyreadstat

    usecols = ["B_COUNTRY_ALPHA", "W_WEIGHT"] + items
    df, _ = pyreadstat.read_dta(str(WVS7), usecols=usecols, encoding="latin1")
    meta = {"countries": 0, "items_requested": len(items), "cells_below_floor": 0,
            "cells_empty": 0, "min_n": min_n}
    rows = {}
    for cc, g in df.groupby("B_COUNTRY_ALPHA"):
        w = g["W_WEIGHT"].fillna(0)
        vals = {}
        for q in items:
            v = pd.to_numeric(g[q], errors="coerce").astype(float)
            mask = (v >= 0) & (w > 0)
            if mask.sum() == 0:
                vals[q] = np.nan
                meta["cells_empty"] += 1          # item not fielded in that country
                continue
            if mask.sum() < min_n:
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
          f"({meta['cells_empty']} cells not fielded, {meta['cells_below_floor']} below a floor of {MIN_N})")
    print(f"countries shared with GPS: {len(human.index.intersection(gps.index))} | "
          f"selected items with human data: {len(covered)} of {len(sel)}")

    res = ST.screen(sel, human, gps)                    # registered draws/seed defaults
    res["cells_empty"] = meta["cells_empty"]
    res["cells_below_floor"] = meta["cells_below_floor"]
    res["min_n"] = MIN_N
    Path(a.out).write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps(res, indent=2))
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
