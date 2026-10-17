#!/usr/bin/env python3
"""Held-out analysis layer after the freeze: everything PREREGISTRATION.md sections 4, 6, 7 and 8 ask
for beside the primary test (which `run_screen.py` computes and this script re-uses, not re-derives).

Registered (each labelled with its section in the output):
  s4  descriptives: share of selected items with a_i > 0; A per dimension
  s6  comparators, coverage-matched D_common (primary reading) with a paired 2,000-resample country
      bootstrap; D over each route's own imprint-set items; A over all assigned items; per-dimension
      A and coverage. Amendment 2: the repaired items are excluded from both comparator files.
  s7  ceiling: wave-6/7 country-mean Spearman per selected item (ceiling.py output), averaged
  s8  secondary rule (reliability check); leave-one-country-out range of A; sign-prompt arm

Exploratory, labelled as such: effect magnitudes |b_top| per route; A on the 28 countries with both
waves, computed on wave-6 and on wave-7 time-series means (does A replicate in another human wave?).

Every human read goes through freeze.require_freeze (via run_screen.human_surface's caller here).
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
sys.path.insert(0, str(REPO / "paper_b"))
import freeze as FR  # noqa: E402
import run_screen as RS  # noqa: E402
import screen_test as ST  # noqa: E402

RESULTS = REPO / "planning/sprint_2026-10-11/paper-b-tier1/results"
CEIL_DIR = RESULTS / "ceiling_heldout"
IMPRINT = ["trust", "risktaking", "posrecip", "altruism"]
# Amendment 2 (decided by Augusto Gonzalez-Bonorino on 2026-10-17, before the human join): the 12 items
# whose wording Amendment 1 repaired are excluded from both comparator routes, because the comparators
# assigned them on the pre-amendment wording. Of the 12, only Q82 is assigned by either comparator.
REPAIRED = ["Q46", "Q82", "Q121", "Q153", "Q155", "Q157", "Q175", "Q199", "Q253", "Q254", "Q255", "Q256"]


def route(df: pd.DataFrame, *, dim_col: str, sign_col: str) -> pd.DataFrame:
    out = df.rename(columns={dim_col: "top_dimension", sign_col: "sign"})[["question_id", "top_dimension", "sign"]]
    out = out[(out.top_dimension != "none") & (out.sign != 0)].copy()
    out["sign"] = out.sign.astype(float)
    return out.reset_index(drop=True)


def adapter_route(sel: pd.DataFrame, col: str = "primary_selected") -> pd.DataFrame:
    s = sel[sel[col].astype(bool)].copy()
    s["sign"] = np.sign(s.t_top.astype(float))
    return s[["question_id", "top_dimension", "sign"]].reset_index(drop=True)


def per_dim(ia: pd.DataFrame) -> dict:
    return {d: {"A": float(g.a_i.mean()), "n": int(len(g)), "share_pos": float((g.a_i > 0).mean())}
            for d, g in ia.groupby("top_dimension")}


def describe(name: str, ia: pd.DataFrame) -> dict:
    return {"route": name, "n_items": int(len(ia)), "n_scored": int(ia.a_i.notna().sum()),
            "A": float(ia.a_i.mean()), "share_a_pos": float((ia.a_i.dropna() > 0).mean()),
            "per_dimension": per_dim(ia)}


def contrast(a: pd.DataFrame, b: pd.DataFrame, human, gps, label: str) -> dict:
    if len(a) == 0 or len(b) == 0:
        return {"label": label, "n_a": len(a), "n_b": len(b), "note": "empty route: not computed"}
    r = ST.compare(a, b, human, gps)
    r["label"] = label
    return r


def common(a: pd.DataFrame, b: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    q = sorted(set(a.question_id) & set(b.question_id), key=lambda s: int(s[1:]))
    return (a.set_index("question_id").loc[q].reset_index(),
            b.set_index("question_id").loc[q].reset_index())


def loco(sel_route: pd.DataFrame, human: pd.DataFrame, gps: pd.DataFrame) -> dict:
    countries = human.index.intersection(gps.index)
    vals = {}
    for c in countries:
        keep = countries.drop(c)
        vals[c] = float(ST.item_agreement(sel_route, human.loc[keep], gps.loc[keep]).a_i.mean())
    s = pd.Series(vals)
    return {"min": float(s.min()), "max": float(s.max()), "argmin": s.idxmin(), "argmax": s.idxmax(),
            "n_dropped_one_at_a_time": int(len(s))}


def wave_replication(sel_route: pd.DataFrame, gps: pd.DataFrame) -> dict:
    """Exploratory: A computed on time-series wave-6 and wave-7 means over the countries in both waves."""
    import pyreadstat

    import config as C
    xw = json.loads((CEIL_DIR / "ts_crosswalk.json").read_text())
    acc = {q: v["accepted"] for q, v in xw.items() if v.get("accepted") and q in set(sel_route.question_id)}
    ts, _ = pyreadstat.read_dta(str(RS.REPO / "data/WVS/timeseries/WVS_Time_Series_1981-2022_stata_v5_0.dta"),
                                usecols=["S002VS", "COUNTRY_ALPHA", "S017"] + sorted(set(acc.values())),
                                encoding="latin1")
    ts = ts[ts.COUNTRY_ALPHA.isin(list(C.COHORT))]
    means = {}
    for w in (6, 7):
        d = ts[ts.S002VS == w]
        cols = {}
        for q, var in acc.items():
            v = d[[var, "S017", "COUNTRY_ALPHA"]]
            v = v[v[var] >= 0]
            num = (v[var] * v.S017).groupby(v.COUNTRY_ALPHA).sum()
            den = v.S017.groupby(v.COUNTRY_ALPHA).sum()
            cols[q] = num / den
        means[w] = pd.DataFrame(cols)
    both = means[6].dropna(how="all").index.intersection(means[7].dropna(how="all").index)
    items6 = [q for q in acc if means[6].loc[both, q].notna().sum() >= 8]
    r = sel_route[sel_route.question_id.isin(items6)].reset_index(drop=True)
    out = {"countries_both_waves": int(len(both)), "items": int(len(r))}
    for w in (6, 7):
        out[f"A_wave{w}"] = float(ST.item_agreement(r, means[w].loc[both], gps.loc[gps.index.intersection(both)]).a_i.mean())
    return out


def magnitudes(sel: pd.DataFrame, col: str = "primary_selected") -> dict:
    s = sel[sel[col].astype(bool)]
    b = np.array([abs(r[f"b_{r.top_dimension}"]) for _, r in s.iterrows()])
    return {"median_abs_b_top": float(np.median(b)), "max_abs_b_top": float(b.max()),
            "median_abs_t_top": float(s.t_top.abs().median()), "median_sigma": float(s.sigma.median())}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--signprompt-selection", required=True)
    ap.add_argument("--out", default=str(RESULTS / "heldout_analysis.json"))
    ap.add_argument("--items-out", default=str(RESULTS / "heldout_items.csv"))
    a = ap.parse_args()

    frozen = FR.require_freeze(HERE / "FREEZE.json")
    sel = pd.read_csv(frozen["selection_path"])
    pool = [str(q) for q in pd.read_csv(frozen["pool_path"])["Question"]]
    human, meta = RS.human_surface(pool)
    gps = RS.load_gps()
    res: dict = {"frozen_at": frozen["frozen_at"], "selection_sha256": frozen["selection_sha256"],
                 "human_cells_not_fielded": meta["cells_empty"], "n_countries": 42}

    # s4 primary (as computed by run_screen) + descriptives
    res["s4_primary"] = json.loads((HERE / "screen_result.json").read_text())
    prim = adapter_route(sel)
    ia = ST.item_agreement(prim, human, gps)
    res["s4_descriptives"] = describe("adapter_primary", ia)

    # s7 ceiling over the selected items
    c = pd.read_csv(CEIL_DIR / "ceiling_items.csv")
    c = c[c.question_id.isin(prim.question_id)]
    ok = c.dropna(subset=["spearman_w6_w7"])
    res["s7_ceiling"] = {
        "selected": int(len(prim)), "matched_to_time_series": int(len(c)),
        "fielded_in_wave6": int(len(ok)), "mean": float(ok.spearman_w6_w7.mean()),
        "median": float(ok.spearman_w6_w7.median()), "min": float(ok.spearman_w6_w7.min()),
        "countries": int(ok.n_countries.max()),
        "A_over_ceiling_mean": float(res["s4_primary"]["A"] / ok.spearman_w6_w7.mean()),
        "one_third_of_ceiling": float(ok.spearman_w6_w7.mean() / 3),
    }
    ia_ok = ia[ia.question_id.isin(ok.question_id)]
    res["s7_ceiling"]["A_on_ceiling_items"] = float(ia_ok.a_i.mean())

    # s8 secondary rule, LOCO
    sec = sel.assign(primary_selected=sel.secondary_selected)
    r2 = ST.screen(sec.assign(sign=np.sign(sec.t_top.astype(float))), human, gps, boot=0)
    res["s8_secondary_rule"] = {k: r2[k] for k in ("A", "n_selected", "p_perm", "null_q95")}
    res["s8_loco"] = loco(prim, human, gps)

    # s6 comparators with Amendment 2
    face_all = route(pd.read_csv(HERE / "face_valid.csv"), dim_col="dimension", sign_col="sign")
    jev_all = route(pd.read_csv(HERE / "jev/majority_face_valid_jev.csv"), dim_col="dimension", sign_col="sign")
    res["amendment2"] = {"excluded_from_face": sorted(set(face_all.question_id) & set(REPAIRED)),
                         "excluded_from_jev": sorted(set(jev_all.question_id) & set(REPAIRED))}
    face_all = face_all[~face_all.question_id.isin(REPAIRED)].reset_index(drop=True)
    jev_all = jev_all[~jev_all.question_id.isin(REPAIRED)].reset_index(drop=True)
    comps = {}
    for name, rt in (("face_valid", face_all), ("jev", jev_all)):
        imp = rt[rt.top_dimension.isin(IMPRINT)].reset_index(drop=True)
        a_c, b_c = common(prim, rt)
        agree = int(((a_c.top_dimension == b_c.top_dimension) & (a_c.sign == b_c.sign)).sum())
        comps[name] = {
            "coverage_all": rt.top_dimension.value_counts().to_dict(),
            "describe_imprint": describe(name, ST.item_agreement(imp, human, gps)),
            "describe_all": describe(name, ST.item_agreement(rt, human, gps)),
            "D_common": contrast(a_c, b_c, human, gps, f"adapter - {name}, items both assign"),
            "common_items": list(a_c.question_id), "common_same_dim_and_sign": agree,
            "D_own_imprint": contrast(prim, imp, human, gps, f"adapter primary - {name} imprint items"),
        }
    res["s6_comparators"] = comps

    # s8 sign-prompt arm
    sp_sel = pd.read_csv(a.signprompt_selection)
    sp = adapter_route(sp_sel)
    r_sp = ST.screen(sp_sel.assign(sign=np.sign(sp_sel.t_top.astype(float))), human, gps)
    a_c, b_c = common(prim, sp)
    res["s8_signprompt"] = {
        "screen": {k: r_sp[k] for k in ("A", "n_selected", "p_perm", "null_q95", "ci95")},
        "describe": describe("signprompt_primary", ST.item_agreement(sp, human, gps)),
        "overlap_with_adapter_primary": int(len(a_c)),
        "overlap_same_dim_and_sign": int(((a_c.top_dimension == b_c.top_dimension) & (a_c.sign == b_c.sign)).sum()),
        "D_own": contrast(prim, sp, human, gps, "adapter primary - signprompt primary"),
        "D_common": contrast(a_c, b_c, human, gps, "adapter - signprompt, items both select"),
    }

    # exploratory
    res["exploratory_magnitudes"] = {"adapter": magnitudes(sel), "signprompt": magnitudes(sp_sel)}
    res["exploratory_wave_replication"] = wave_replication(prim, gps)

    Path(a.out).write_text(json.dumps(res, indent=2, default=float) + "\n")
    ia.merge(sel[["question_id", "t_top"]], on="question_id").to_csv(a.items_out, index=False)
    print(json.dumps(res, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
