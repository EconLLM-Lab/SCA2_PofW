"""Numbers table for the Paper B claim-lock amendment (card T9, checkpoint C7).

One row per number the paper may cite. Every value is read from a committed output file (JSON or CSV)
written by the script named in the row; nothing is typed here. A test fails if this file contains a float
literal or an integer of 10 or more.

Inputs (all aggregate, no human rows):
    paper_b/heldout/screen_result.json, paper_b/heldout/FREEZE.json
    planning/sprint_2026-10-11/paper-b-tier1/results/{heldout_analysis,heldout_per_dimension,
        bank2_transport_strict}.json, factorial/*, replicate/*, near_zero/*, persona/persona_strict.json (C8),
        c9/{c9_human_agreement,c9_tvd,w1_why_trust}.json (C9; descriptive, not preregistered)
    results/robustness/selection_heldout_{reverse,para_a,para_b}.csv (paper_b/heldout/readout_robustness.py)

usage: python paper_b/build_numbers_table.py [--out PATH] [--readout-dir DIR]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RES = "planning/sprint_2026-10-11/paper-b-tier1/results"
OUT = ROOT / "planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv"
READOUT_DIR = ROOT / RES / "robustness"  # written by paper_b/heldout/readout_robustness.py
COLUMNS = ["claim_id", "sentence_use", "statistic", "value", "ci_low", "ci_high", "n", "surface_label",
           "run_id", "producing_script", "output_file"]

# Run ids as recorded on the T4/T5/T6 handoffs (the held-out ones are read from FREEZE.json).
RUN_COHORT1 = "paper-b-20261011"
RUN_STRICT_B2 = "bank2-strict-v1-20261016"
RUN_SP_STRICT64 = "bank2-signprompt-strict-v1-20261018"
RUN_REPL = "bank2-replicate-r1-strict-v1-20261018; bank2-replicate-r1-heldout-v1-20261018"
RUN_NZ = "bank2-nearzero-strict-v1-20261018"

SURFACES = ["trust", "risktaking", "posrecip", "altruism", "negrecip", "patience:Q43", "patience:Q50"]


def _read(rel: str):
    return json.loads((ROOT / rel).read_text())


def _fmt(x):
    if x is None or x == "":
        return ""
    if isinstance(x, bool):
        return str(int(x))
    if isinstance(x, int):
        return str(x)
    if isinstance(x, str):
        return x
    return repr(float(x))


class Table:
    def __init__(self):
        self.rows = []

    def add(self, claim_id, sentence_use, statistic, value, *, ci=None, n=None, surface, run_id, script, out):
        lo, hi = ci if ci else ("", "")
        self.rows.append({"claim_id": claim_id, "sentence_use": sentence_use, "statistic": statistic,
                          "value": _fmt(value), "ci_low": _fmt(lo), "ci_high": _fmt(hi), "n": _fmt(n),
                          "surface_label": surface, "run_id": run_id, "producing_script": script,
                          "output_file": out})


# ------------------------------------------------------------------ held-out screen (C4/C5 inputs)
def screen_rows(t: Table, freeze: dict):
    sc = _read("paper_b/heldout/screen_result.json")
    ha = _read(f"{RES}/heldout_analysis.json")
    run = freeze["run_ids"]["heldout_v1"]
    surf = ("held-out pool v1 (223 WVS-7 items outside the 23-item battery); adapter primary selection (56 items); "
            "retrospective WVS-7 criterion; 42 countries")
    f_s, f_a = "paper_b/heldout/run_screen.py", "paper_b/heldout/analyze_heldout.py"
    o_s, o_a = "paper_b/heldout/screen_result.json", f"{RES}/heldout_analysis.json"
    t.add("SCR_A_primary", "Registered primary statistic A over the 56 selected items; the country-bootstrap interval "
          "touches 0, so say the magnitude is imprecise", "A (mean signed Spearman vs GPS)", sc["A"],
          ci=sc["ci95"], n=sc["n_selected"], surface=surf, run_id=run, script=f_s, out=o_s)
    t.add("SCR_p_perm", "Registered one-sided permutation p (share of null A >= observed, 10,000 draws); the null is "
          "rejected", "permutation p", sc["p_perm"], n=sc["draws"], surface=surf, run_id=run, script=f_s, out=o_s)
    t.add("SCR_null_mean", "Mean of the permutation null", "null mean of A", sc["null_mean"], n=sc["draws"],
          surface=surf, run_id=run, script=f_s, out=o_s)
    t.add("SCR_null_q95", "95th percentile of the permutation null", "null 95th percentile of A", sc["null_q95"],
          n=sc["draws"], surface=surf, run_id=run, script=f_s, out=o_s)
    t.add("SCR_cells_not_fielded", "Item-country cells never fielded; they enter as missing, not imputed",
          "count of item-country cells", ha["human_cells_not_fielded"], surface=surf, run_id=run, script=f_a, out=o_a)
    d = ha["s4_descriptives"]
    t.add("SCR_share_a_pos", "Share of selected items whose signed item agreement a_i is positive",
          "share of items with a_i > 0", d["share_a_pos"], n=d["n_scored"], surface=surf, run_id=run, script=f_a,
          out=o_a)
    c = ha["s7_ceiling"]
    sc_surf = ("registered wave-6 vs wave-7 ceiling over the selected items fielded in both waves; country means; "
               "28-country overlap; retrospective")
    for key, text in (("mean", "Registered ceiling, mean over items"), ("median", "Registered ceiling, median"),
                      ("min", "Registered ceiling, minimum")):
        t.add(f"SCR_ceiling_{key}", text, f"wave 6 vs 7 Spearman, {key}", c[key], n=c["fielded_in_wave6"],
              surface=sc_surf, run_id=run, script=f_a, out=o_a)
    t.add("SCR_A_over_ceiling", "A as a share of the registered ceiling mean; a benchmark, not a fraction of "
          "achievable signal (the two statistics are built differently)", "A / ceiling mean",
          c["A_over_ceiling_mean"], n=c["fielded_in_wave6"], surface=sc_surf, run_id=run, script=f_a, out=o_a)
    t.add("SCR_one_third_ceiling", "One third of the registered ceiling (the weak-signal bar)",
          "ceiling mean / 3", c["one_third_of_ceiling"], n=c["fielded_in_wave6"], surface=sc_surf, run_id=run,
          script=f_a, out=o_a)
    s2 = ha["s8_secondary_rule"]
    sec = "held-out pool v1; adapter secondary rule (fixed threshold, reliability check); 42 countries"
    t.add("SCR_secondary_A", "Secondary rule A (reliability check, not inference)", "A", s2["A"],
          n=s2["n_selected"], surface=sec, run_id=run, script=f_a, out=o_a)
    t.add("SCR_secondary_p_perm", "Secondary rule permutation p", "permutation p", s2["p_perm"], n=s2["n_selected"],
          surface=sec, run_id=run, script=f_a, out=o_a)
    t.add("SCR_secondary_null_q95", "Secondary rule null 95th percentile", "null 95th percentile of A",
          s2["null_q95"], n=s2["n_selected"], surface=sec, run_id=run, script=f_a, out=o_a)
    lo = ha["s8_loco"]
    t.add("SCR_loco_min", f"Leave-one-country-out minimum of A (drop {lo['argmin']})", "min A", lo["min"],
          n=lo["n_dropped_one_at_a_time"], surface=surf, run_id=run, script=f_a, out=o_a)
    t.add("SCR_loco_max", f"Leave-one-country-out maximum of A (drop {lo['argmax']})", "max A", lo["max"],
          n=lo["n_dropped_one_at_a_time"], surface=surf, run_id=run, script=f_a, out=o_a)
    ab = ha["s8_abs_a_descriptive"]
    asurf = (f"held-out pool v1; adapter primary selection; items with |a_i| >= {ab['cut']} kept (registered "
             f"section-8 descriptive, never the primary); retrospective WVS-7 criterion; 42 countries")
    t.add("SCR_absA_n_kept", f"Registered item-level descriptive: selected items with |a_i| >= {ab['cut']}",
          "count of items kept", ab["n_kept"], n=ab["n_scored"], surface=asurf, run_id=run, script=f_a, out=o_a)
    t.add("SCR_absA_A_kept", "Registered item-level descriptive: A over the items kept after dropping small |a_i|; "
          "not an inference (the cut conditions on the criterion)", "A over kept items", ab["A_kept"],
          n=ab["n_kept"], surface=asurf, run_id=run, script=f_a, out=o_a)
    t.add("SCR_absA_share_pos_kept", "Registered item-level descriptive: share of kept items with a_i > 0",
          "share of kept items with a_i > 0", ab["share_pos_kept"], n=ab["n_kept"], surface=asurf, run_id=run,
          script=f_a, out=o_a)
    w = ha["exploratory_wave_replication"]
    wsurf = "exploratory: items fielded in both WVS waves; country means per wave; 28 countries"
    t.add("SCR_A_wave6", "Exploratory: A on wave-6 country means", "A", w["A_wave6"], n=w["items"], surface=wsurf,
          run_id=run, script=f_a, out=o_a)
    t.add("SCR_A_wave7", "Exploratory: A on wave-7 country means", "A", w["A_wave7"], n=w["items"], surface=wsurf,
          run_id=run, script=f_a, out=o_a)
    for route, text in (("adapter", "adapter route"), ("signprompt", "sign-prompt route")):
        m = ha["exploratory_magnitudes"][route]
        for key in ("median_abs_b_top", "median_abs_t_top"):
            t.add(f"SCR_{route}_{key}", f"Exploratory effect size of the top effect, {text}", key, m[key],
                  surface=f"exploratory: held-out pool v1, {text}, probe over 223 items", run_id=run, script=f_a,
                  out=o_a)


# ------------------------------------------------------------------ per dimension (C5)
def per_dimension_rows(t: Table, freeze: dict):
    pd_json = _read(f"{RES}/heldout_per_dimension.json")
    ha = _read(f"{RES}/heldout_analysis.json")
    run = freeze["run_ids"]["heldout_v1"]
    o = f"{RES}/heldout_per_dimension.json"
    f = "paper_b/heldout/per_dimension.py"
    labels = {
        "adapter_primary": "held-out pool v1; adapter primary selection (56); per assigned dimension; retrospective "
                           "WVS-7 criterion; 42 countries",
        "adapter_secondary": "held-out pool v1; adapter secondary rule (185); per assigned dimension; retrospective",
        "signprompt_primary": "held-out pool v1; sign-prompt primary selection (56); per assigned dimension; "
                              "retrospective",
        "face_valid": "held-out pool v1; face-valid reader, imprint items, Amendment 2 applied; per dimension; "
                      "retrospective",
        "jev_majority": "held-out pool v1; Jev System One majority of 5 runs, imprint items, Amendment 2 applied; "
                        "per dimension; retrospective",
    }
    for route, body in pd_json["routes"].items():
        for dim, cell in body["per_dimension"].items():
            t.add(f"PD_{route}_{dim}_A", f"C5 reading for {dim}, {route}: {cell['reading']}",
                  "A_d (mean signed Spearman over items assigned to dimension)", cell["A"],
                  ci=cell["ci95"], n=cell["n"], surface=labels[route], run_id=run, script=f, out=o)
            if route in ("adapter_primary", "adapter_secondary") and "ci_bonf" in cell:
                t.add(f"PD_{route}_{dim}_A_bonf",
                      f"Exploratory, not registered: Bonferroni interval over {cell['bonf_m']} imprint "
                      f"dimensions for {dim}, {route} (same draws as the registered interval)",
                      "A_d with Bonferroni-adjusted country-bootstrap interval", cell["A"],
                      ci=cell["ci_bonf"], n=cell["n"], surface=labels[route], run_id=run, script=f, out=o)
    for dim, cell in ha["s4_descriptives"]["per_dimension"].items():
        t.add(f"PD_adapter_primary_{dim}_share_pos", f"Share of the {dim} items with a_i > 0 (adapter primary)",
              "share of items with a_i > 0", cell["share_pos"], n=cell["n"], surface=labels["adapter_primary"],
              run_id=run, script="paper_b/heldout/analyze_heldout.py", out=f"{RES}/heldout_analysis.json")


# ------------------------------------------------------------------ comparators and sign-prompt arm
def comparator_rows(t: Table, freeze: dict):
    ha = _read(f"{RES}/heldout_analysis.json")
    run = freeze["run_ids"]["heldout_v1"]
    o, f = f"{RES}/heldout_analysis.json", "paper_b/heldout/analyze_heldout.py"
    for key, name in (("face_valid", "face-valid reader"), ("jev", "Jev System One majority")):
        blk = ha["s6_comparators"][key]
        surf = f"held-out pool v1; {name} versus adapter primary; Amendment 2 applied (Q82 removed); retrospective"
        imp = blk["describe_imprint"]
        t.add(f"CMP_{key}_A_imprint", f"A of the {name} on the items it assigns in the imprint set",
              "A (comparator's own imprint items)", imp["A"], n=imp["n_items"], surface=surf, run_id=run, script=f,
              out=o)
        dc = blk["D_common"]
        t.add(f"CMP_{key}_D_common", f"Registered primary contrast, adapter minus {name} on the items both assign "
              f"(interval covers 0: adapters match a careful reader)", "D_common = A_adapter - A_comparator",
              dc["D"], ci=dc["ci95"], n=dc["n_a"], surface=surf, run_id=run, script=f, out=o)
        do = blk["D_own_imprint"]
        t.add(f"CMP_{key}_D_own", f"Contrast on each route's own items, adapter minus {name}",
              "D_own = A_adapter - A_comparator", do["D"], ci=do["ci95"], n=do["n_b"], surface=surf, run_id=run,
              script=f, out=o)
        t.add(f"CMP_{key}_common_same_dim_sign", f"Items both routes assign on which they agree on dimension and "
              f"sign ({name})", "count agreeing", blk["common_same_dim_and_sign"], n=len(blk["common_items"]),
              surface=surf, run_id=run, script=f, out=o)
    fa = ha["s6_comparators"]["face_valid"]["describe_all"]
    fsurf = ("held-out pool v1; face-valid reader on all items it assigns, negative reciprocity included; "
             "Amendment 2 applied (Q82 removed, so 29 of the registered 30); retrospective")
    t.add("CMP_face_valid_A_all", "Registered descriptive (section 6): A of the face-valid reader on all of its "
          "items, reported beside the imprint-set contrast", "A (comparator's own items, all dimensions)", fa["A"],
          n=fa["n_items"], surface=fsurf, run_id=run, script=f, out=o)
    neg = fa["per_dimension"]["negrecip"]
    t.add("CMP_face_valid_all_negrecip_A", "Registered descriptive (section 6): the face-valid reader's A on its "
          "negative-reciprocity items", "A (negrecip items)", neg["A"], n=neg["n"], surface=fsurf, run_id=run,
          script=f, out=o)
    sp = ha["s8_signprompt"]
    surf = "held-out pool v1; sign-prompt arm (64 prompted profiles, same probe); retrospective; 42 countries"
    rid = freeze["run_ids"]["signprompt_heldout_v1"]
    t.add("SP_A_primary", "Sign-prompt arm A (the same probe applied to prompts): not above the null",
          "A", sp["screen"]["A"], ci=sp["screen"]["ci95"], n=sp["screen"]["n_selected"], surface=surf, run_id=rid,
          script=f, out=o)
    t.add("SP_p_perm", "Sign-prompt arm permutation p (registered construction)", "permutation p",
          sp["screen"]["p_perm"], n=sp["screen"]["n_selected"], surface=surf, run_id=rid, script=f, out=o)
    t.add("SP_null_q95", "Sign-prompt arm null 95th percentile", "null 95th percentile of A",
          sp["screen"]["null_q95"], n=sp["screen"]["n_selected"], surface=surf, run_id=rid, script=f, out=o)
    t.add("SP_overlap_with_adapter", "Items selected by both the adapter and the prompt probe",
          "count of shared primary items", sp["overlap_with_adapter_primary"], surface=surf, run_id=rid, script=f,
          out=o)
    t.add("SP_overlap_same_dim_sign", "Shared items on which the two routes agree on dimension and sign",
          "count agreeing", sp["overlap_same_dim_and_sign"], n=sp["overlap_with_adapter_primary"], surface=surf,
          run_id=rid, script=f, out=o)
    for key, text in (("D_own", "own items"), ("D_common", "the shared items")):
        d = sp[key]
        t.add(f"SP_{key}", f"Adapter minus prompt on {text}; unresolved (interval covers 0)",
              "D = A_adapter - A_prompt", d["D"], ci=d["ci95"], n=d["n_a"], surface=surf, run_id=rid, script=f,
              out=o)


# ------------------------------------------------------------------ readout robustness
def _sign(x):
    return (x > 0) - (x < 0)


def _rel(path: Path) -> str:
    """Repository-relative path for the output_file column (an absolute path is not replicable)."""
    return str(Path(path).resolve().relative_to(ROOT))


def readout_rows(t: Table, freeze: dict, readout_dir: Path):
    sel = ROOT / "paper_b/heldout/selection_amended_20261016.csv"
    base = pd.read_csv(sel)
    if hashlib.sha256(sel.read_bytes()).hexdigest() != freeze["selection_sha256"]:
        raise SystemExit("selection_amended_20261016.csv does not match FREEZE.json; refusing to compare")
    script = ("paper_b/heldout/readout_robustness.py (build_probe_input.py + probe_select.py); counts recomputed "
              "by paper_b/build_numbers_table.py")
    for variant in ("heldout_reverse", "heldout_para_a", "heldout_para_b"):
        path = readout_dir / f"selection_{variant}.csv"
        if not path.is_file():
            raise SystemExit(f"readout selection missing: {path}")
        v = pd.read_csv(path)
        m = base.merge(v, on="question_id", suffixes=("_b", "_v"))
        bp, vp = m.primary_selected_b.astype(bool), m.primary_selected_v.astype(bool)
        same = (m.top_dimension_b == m.top_dimension_v) & (m.t_top_b.map(_sign) == m.t_top_v.map(_sign))
        kw = dict(surface=f"held-out pool v1 re-read under the {variant} variant; probe re-estimated; model-side "
                          f"only", run_id=freeze["run_ids"][variant], script=script, out=_rel(path))
        t.add(f"RO_{variant}_ds_unchanged", "Registered statistic: selected items whose (dimension, sign) is "
              "unchanged under the variant; adverse only if more than half changed", "count unchanged",
              int((same & bp).sum()), n=int(bp.sum()), **kw)
        t.add(f"RO_{variant}_membership_agreement", "Items in the primary set under both readouts (set membership "
              "is a ranking cut and churns)", "count in both primary sets", int((bp & vp).sum()),
              n=int(bp.sum()), **kw)
        t.add(f"RO_{variant}_abs_t_corr", "Pearson of |t_top| between base and variant over the pool",
              "Pearson r", float(m.t_top_b.abs().corr(m.t_top_v.abs())), n=len(m), **kw)


# ------------------------------------------------------------------ bank-2 transport (C3)
def bank2_rows(t: Table):
    b = _read(f"{RES}/bank2_transport_strict.json")
    o, f = f"{RES}/bank2_transport_strict.json", "paper_b/bank2_transport.py"
    s1 = ("strict 23-item battery; cohort-1 country adapters (bank 1); adapter-GPS Spearman over 42 countries; "
          "profile-block bootstrap (26 clusters)")
    s2 = ("strict 23-item battery; bank-2 sign-profile adapters mapped to the 42 countries; adapter-GPS Spearman; "
          "profile-block bootstrap (26 clusters)")
    kept = set(b["c3_pass"]["kept"])
    for sfc in SURFACES:
        c1, c2 = b["cohort1_adapter_gps"][sfc], b["bank2_adapter_gps"][sfc]
        t.add(f"B2_cohort1_{sfc}_rho", f"Banked cohort-1 adapter-GPS, {sfc}", "Spearman rho", c1["point"],
              ci=(c1["ci_lo"], c1["ci_hi"]), n=c1["n"], surface=s1, run_id=RUN_COHORT1, script=f, out=o)
        reading = "C3 pass (interval excludes 0)" if sfc in kept else (
            "C3 drop (interval includes 0)" if sfc in b["c3_pass"]["imprint"] else "not an imprint dimension; reported")
        t.add(f"B2_bank2_{sfc}_rho", f"Bank-2 adapter-GPS, {sfc}: {reading}", "Spearman rho", c2["point"],
              ci=(c2["ci_lo"], c2["ci_hi"]), n=c2["n"], surface=s2, run_id=RUN_STRICT_B2, script=f, out=o)
    sb = "strict battery; bank-2 profile composites vs bank-1 sign-mate country means; 26 shared sign cells"
    both = f"{RUN_COHORT1}; {RUN_STRICT_B2}"
    for row in b["bank_to_bank_table"]:
        t.add(f"B2_bank_to_bank_{row['surface']}_pearson", f"Bank-to-bank agreement, {row['surface']}", "Pearson r",
              row["pearson"], ci=(row["pearson_lo"], row["pearson_hi"]), n=row["n_cells"], surface=sb,
              run_id=both, script=f, out=o)
        t.add(f"B2_bank_to_bank_{row['surface']}_spearman", f"Bank-to-bank agreement, {row['surface']}",
              "Spearman rho", row["spearman"], ci=(row["spearman_lo"], row["spearman_hi"]), n=row["n_cells"],
              surface=sb, run_id=both, script=f, out=o)
    t.add("B2_n_imprint_kept", "Imprint dimensions whose bank-2 interval still excludes 0", "count",
          len(b["c3_pass"]["kept"]), n=len(b["c3_pass"]["imprint"]), surface=s2, run_id=RUN_STRICT_B2, script=f,
          out=o)
    t.add("B2_n_imprint_dropped", "Imprint dimensions whose bank-2 interval includes 0 (transport sentence dropped)",
          "count", len(b["c3_pass"]["dropped"]), n=len(b["c3_pass"]["imprint"]), surface=s2, run_id=RUN_STRICT_B2,
          script=f, out=o)


# ------------------------------------------------------------------ factorial (route contrast)
def factorial_rows(t: Table):
    rep = _read(f"{RES}/factorial/factorial_report.json")
    o = f"{RES}/factorial/factorial_report.json"
    f = "paper_b/analyze_factorial.py + paper_b/factorial_report.py"
    ncell = rep["route_contrast_64_cells"]["n_cells"]
    routes = {"adapter": ("bank-2 adapters", RUN_STRICT_B2, "mtmm_adapter.csv"),
              "signprompt": ("sign-prompt route", RUN_SP_STRICT64, "mtmm_signprompt.csv")}
    for route, (name, run, mtmm) in routes.items():
        blk = rep["route_contrast_64_cells"][route]
        surf = f"strict 23-item battery; {name}; full 2^6 factorial, 64 cells; main effects, model-side only"
        kw = dict(surface=surf, run_id=run, script=f, out=o)
        for sfc, cell in blk["diagonal"].items():
            key = sfc.replace(":", "_")
            t.add(f"FX_{route}64_{key}_own_beta", f"Own effect of the {cell['bit']} bit on the {sfc} surface ({name})",
                  "own main effect (composite units)", cell["beta"], n=ncell, **kw)
            t.add(f"FX_{route}64_{key}_own_t", f"OLS t of the own effect, {sfc} ({name}), error df 42", "OLS t",
                  cell["t"], n=ncell, **kw)
        v5 = blk["plan_V5_rowwise_raw"]
        t.add(f"FX_{route}64_V5_hits", f"Plan V5 (own-surface dominance, rows): bits whose own surface is their "
              f"largest mover; four were required ({name})", "count of 6", v5["hits"], n=v5["n"], **kw)
        t.add(f"FX_{route}64_V5_p_binomial", f"Binomial p for the V5 count ({name})", "binomial p", v5["p_binomial"],
              n=v5["n"], **kw)
        t.add(f"FX_{route}64_rowwise_standardized_hits", f"Own-surface dominance on rows standardized by surface SD "
              f"({name})", "count of 6", blk["rowwise_standardized"]["hits"], n=blk["rowwise_standardized"]["n"],
              **kw)
        t.add(f"FX_{route}64_columnwise_hits", f"Surfaces whose largest mover is their own bit ({name})",
              "count of 7", blk["columnwise"]["hits"], n=blk["columnwise"]["n"], **kw)
        wrong = sum(1 for c in blk["diagonal"].values() if c["beta"] < 0)
        t.add(f"FX_{route}64_own_effects_wrong_signed", f"Own effects pointing against the intended direction "
              f"({name})", "count of 7", wrong, n=len(blk["diagonal"]), **kw)
        trust_top = sum(1 for b in blk["columnwise"]["largest_bit"].values() if b == "trust")
        t.add(f"FX_{route}64_surfaces_largest_mover_is_trust_bit", f"Surfaces on which the trust bit is the largest "
              f"mover ({name})", "count of 7", trust_top, n=len(blk["columnwise"]["largest_bit"]), **kw)
        gf = blk["general_factor"]
        t.add(f"FX_{route}64_pc1_share", f"Share of variance on the first common direction of the seven surfaces "
              f"over 64 cells ({name})", "PC1 share", gf["pc1_share"], n=ncell, **kw)
        t.add(f"FX_{route}64_pc2_share", f"Second-direction share ({name})", "PC2 share", gf["pc2_share"], n=ncell,
              **kw)
        t.add(f"FX_{route}64_mean_abs_inter_surface_r", f"Mean absolute inter-surface correlation ({name})",
              "mean |r|", gf["mean_abs_inter_surface_r"], n=ncell, **kw)
        # cross-talk, read from the main-effect matrix (rows: bit; columns: surface)
        mt = pd.read_csv(ROOT / RES / "factorial" / mtmm).set_index("dimension")
        pairs = ([("risktaking", s) for s in ("altruism", "negrecip", "patience:Q43")] +
                 [("trust", s) for s in ("patience:Q50", "posrecip")]) if route == "adapter" else [
                 ("trust", s) for s in SURFACES]
        for bit, sfc in pairs:
            t.add(f"FX_{route}64_{bit}_bit_on_{sfc.replace(':', '_')}", f"Cross-talk: main effect of the {bit} bit "
                  f"on the {sfc} surface ({name})", "main effect (composite units)", float(mt.loc[bit, sfc]), n=ncell,
                  surface=surf, run_id=run, script=f, out=f"{RES}/factorial/{mtmm}")
    # the 26-cell exploratory contrast, kept only so the superseded numbers stay traceable
    r26 = rep["route_contrast_26_cells"]
    for route, (name, run, _) in routes.items():
        surf = (f"strict 23-item battery; {name}; 26 cells where the strict sign-prompt cell exists; main effects only, "
                "df 19; exploratory, superseded by the 64-cell contrast")
        blk = r26[route]
        wrong = sum(1 for c in blk["diagonal"].values() if c["beta"] < 0)
        t.add(f"FX26_{route}_own_effects_wrong_signed", f"26-cell exploratory: own effects against the intended "
              f"direction ({name}); superseded by the 64-cell count", "count of 7", wrong, n=len(blk["diagonal"]),
              surface=surf, run_id=run, script=f, out=o)
        t.add(f"FX26_{route}_pc1_share", f"26-cell exploratory first-direction share ({name}); superseded by the "
              f"64-cell share", "PC1 share", blk["general_factor"]["pc1_share"], n=r26["n_cells"], surface=surf,
              run_id=run, script=f, out=o)


# ------------------------------------------------------------------ replicate (unseeded retrain)
def replicate_rows(t: Table):
    r = _read(f"{RES}/replicate/replicate_analysis.json")
    o, f = f"{RES}/replicate/replicate_analysis.json", "paper_b/analyze_replicate.py"
    for bat, label in (("strict", "strict 23-item battery"), ("heldout", "held-out pool v1 (223 items)")):
        b = r[bat]
        kw = dict(surface=f"{label}; one unit ({r['unit']}) retrained without a fixed seed vs the original unit; "
                          f"model-side only", run_id=RUN_REPL, script=f, out=o)
        t.add(f"RP_{bat}_n_cells", f"Scored cells compared, unseeded retrain vs original ({label})", "count of cells",
              b["n_cells_compared"], **kw)
        t.add(f"RP_{bat}_max_abs_prob_diff", f"Largest single-cell probability difference between the unseeded "
              f"retrain and the original ({label})", "max |dp|", b["max_abs_prob_diff"], n=b["n_cells_compared"], **kw)
        t.add(f"RP_{bat}_mean_abs_prob_diff", f"Mean absolute probability difference ({label})", "mean |dp|",
              b["mean_abs_prob_diff"], n=b["n_cells_compared"], **kw)
        t.add(f"RP_{bat}_pearson_expected_codes", f"Pearson of expected codes over items, retrain vs original "
              f"({label})", "Pearson r", b["pearson_expected_codes"]["pearson"],
              n=b["pearson_expected_codes"]["n_items"], **kw)
    t.add("RP_strict_pearson_recoded", "Pearson of E[recode] over the 23 strict items, retrain vs original",
          "Pearson r", r["strict"]["pearson_expected_codes_recoded"]["pearson"],
          n=r["strict"]["pearson_expected_codes_recoded"]["n_items"],
          surface=f"strict 23-item battery; one unit ({r['unit']}) unseeded retrain; model-side only",
          run_id=RUN_REPL, script=f, out=o)
    for sfc, cell in r["strict_surface_diff_sd_units"].items():
        t.add(f"RP_surface_diff_sd_{sfc.replace(':', '_')}", f"Strict-surface shift, retrain minus original, in "
              f"profile SDs, {sfc}", "difference / SD over 64 profiles", cell["diff_sd"], n=cell["n_items"],
              surface=f"strict battery surface {sfc}; unit {r['unit']}; SD over the 64 bank-2 profile composites",
              run_id=RUN_REPL, script=f, out=o)
    t.add("RP_max_abs_surface_diff_sd", f"Largest strict-surface shift in profile SDs "
          f"({r['surface_with_largest_abs_diff_sd']}); state the bound as 0.12, not one ninth",
          "max |difference| / SD", r["max_abs_surface_diff_sd"], n=len(r["strict_surface_diff_sd_units"]),
          surface=f"strict battery; unit {r['unit']}; SD over the 64 bank-2 profile composites", run_id=RUN_REPL,
          script=f, out=o)


# ------------------------------------------------------------------ near-zero refit (C6)
def near_zero_rows(t: Table):
    z = _read(f"{RES}/near_zero/near_zero_analysis.json")
    o, f = f"{RES}/near_zero/near_zero_analysis.json", "paper_b/analyze_near_zero.py"
    for row in z["table"]:
        cc, sfc = row["country"], row["surface"]
        key = sfc.replace(":", "_")
        surf = (f"strict battery; near-zero refit of {cc} ({row['profile_unit']}) vs size-matched control; block "
                f"{row['block']}; single refit, no interval")
        flags = f"beyond noise floor: {row['beyond_floor']}; against intended direction: {row['against_intended']}"
        t.add(f"NZ_{cc}_{key}_refit_minus_control_sd", f"C6 contrast, {cc} {sfc} (intended {row['intended_direction']}; "
              f"imprint {row['imprint']}; {flags})", "(refit - control) / SD over 64 profiles",
              row["refit_minus_control_sd"], n=1, surface=surf, run_id=RUN_NZ, script=f, out=o)
        t.add(f"NZ_{cc}_{key}_noise_floor_sd", f"Noise floor for {sfc} (one unseeded retrain of one unit)",
              "|replicate delta| / SD", row["noise_floor_sd"], n=1, surface=surf, run_id=RUN_NZ, script=f, out=o)
    for cc in sorted({r["country"] for r in z["table"]}):
        worst = max((r for r in z["table"] if r["country"] == cc), key=lambda r: abs(r["control_minus_baseline_sd"]))
        t.add(f"NZ_{cc}_max_abs_control_minus_baseline_sd",
              f"Variation between a small-data training (size-matched control) and the full-data baseline, largest "
              f"over surfaces ({cc}, {worst['surface']}); the declared replicate floor is far smaller, so no reversal "
              f"is claimed", "max |(control - baseline)| / SD over 64 profiles", abs(worst["control_minus_baseline_sd"]),
              n=len(z["table"]) // len(z["countries"]),
              surface=f"strict battery; size-matched control for {cc}; subsample variation, not a floor",
              run_id=RUN_NZ, script=f, out=o)
    tab = z["table"]
    against_r = sum(1 for r in tab if r["block"] == "R" and r["imprint"] and r["against_intended"])
    n_r = sum(1 for r in tab if r["block"] == "R" and r["imprint"])
    against_d = sum(1 for r in tab if r["block"] == "D" and r["against_intended"] and r["beyond_floor"])
    n_d = sum(1 for r in tab if r["block"] == "D")
    surf = "strict battery; two near-zero refits (GBR, COL); loss-of-signal and retained-imprint blocks"
    t.add("NZ_blockR_imprint_against", "Retained imprint surfaces moving against their intended direction beyond the "
          "declared floor (COL posrecip); the filter is not promoted, but no reversal is claimed because the move is "
          "far smaller than the small-data subsample variation", "count", against_r, n=n_r, surface=surf, run_id=RUN_NZ,
          script=f, out=o)
    t.add("NZ_blockD_against_beyond_floor", "Dropped-dimension moves against the intended direction beyond the floor "
          "(loss of signal, not evidence)", "count", against_d, n=n_d, surface=surf, run_id=RUN_NZ, script=f, out=o)


# ------------------------------------------------------------------ file hashes (F7)
def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _git_show(spec: str) -> bytes:
    return subprocess.run(["git", "show", spec], cwd=ROOT, capture_output=True, check=True).stdout


def hash_rows(t: Table):
    me = "paper_b/build_numbers_table.py (hashlib, git show)"
    pool = "paper_b/heldout/pool_skeleton.csv"
    tag = "prereg-heldout-2026-10-14"
    work = (ROOT / pool).read_bytes()
    blob = _git_show(f"HEAD:{pool}")
    tag_blob = _git_show(f"{tag}:{pool}")
    crlf_of_tag = tag_blob.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    kw = dict(run_id="n/a (file hash)", script=me)
    t.add("HASH_pool_worktree", "Amended pool, working-tree bytes (CRLF on this Mac); the hash registered in "
          "Amendment 1", "sha256 (hex)", _sha(work), n=len(work), surface=f"{pool} working copy, amended", out=pool,
          **kw)
    t.add("HASH_pool_git_blob_lf", "Amended pool, git blob at HEAD (LF); the repository stores text with LF "
          "(.gitattributes: * text=auto)", "sha256 (hex)", _sha(blob), n=len(blob),
          surface=f"{pool} git blob at HEAD, amended", out=pool, **kw)
    t.add("HASH_pool_pre_amendment_crlf", "Pre-amendment pool, CRLF form (the hash preregistration section 10 "
          "records)", "sha256 (hex)", _sha(crlf_of_tag), n=len(crlf_of_tag),
          surface=f"{pool} at tag {tag}, converted to CRLF", out=pool, **kw)
    t.add("HASH_pool_pre_amendment_lf", "Pre-amendment pool, git blob at the tag (LF)", "sha256 (hex)",
          _sha(tag_blob), n=len(tag_blob), surface=f"{pool} git blob at tag {tag}", out=pool, **kw)
    for rel_path, label in (("paper_b/heldout/overrides.json", "overrides.json (amended; LF both in tree and in git)"),
                            ("paper_b/heldout/selection_amended_20261016.csv", "frozen selection")):
        data = (ROOT / rel_path).read_bytes()
        t.add(f"HASH_{Path(rel_path).stem}", f"Hash of the {label}", "sha256 (hex)", _sha(data), n=len(data),
              surface=rel_path, out=rel_path, **kw)


# ------------------------------------------------------------------ C8 persona arm (strict battery, 42 countries)
def persona_rows(t: Table):
    """C8_PERSONA_DESIGN.md: E1 persona-GPS, E2 the one test, E3 descriptive differences, E4 country bootstrap,
    E5 the 16 development countries, and the G3 base-parity gap. Every value is read from persona_strict.json."""
    o, f = f"{RES}/persona/persona_strict.json", "paper_b/persona_strict.py"
    d = _read(o)
    if not d["replay_checks"]["all_pass"]:
        raise RuntimeError(f"persona analysis replay checks failed: {d['replay_checks']}")
    run = f"{d['run_id']}; {RUN_COHORT1}; {RUN_STRICT_B2}; {RUN_SP_STRICT64}"
    base = "strict 23-item battery; 42 countries"
    sp_ = f"{base}; country-named persona prompt, base model; persona-GPS Spearman"
    for s in SURFACES:
        e = d["E1"][s]
        t.add(f"PX_persona_{s}_rho", f"Persona-GPS, {s}", "Spearman rho", e["point"], ci=(e["ci_lo"], e["ci_hi"]),
              n=e["n"], surface=f"{sp_}; profile-block bootstrap (26 clusters)", run_id=d["run_id"], script=f, out=o)
        e = d["E4"]["persona"][s]
        t.add(f"PX_persona_{s}_rho_country", f"Persona-GPS, {s}, country bootstrap (sensitivity)", "Spearman rho",
              e["point"], ci=(e["ci_lo"], e["ci_hi"]), n=e["n"], surface=f"{sp_}; country bootstrap",
              run_id=d["run_id"], script=f, out=o)
        e = d["routes_vs_gps"]["SP"][s]
        t.add(f"PX_signprompt_{s}_rho", f"Sign-prompt-GPS, {s} (64 prompted profiles mapped to countries)",
              "Spearman rho", e["point"], ci=(e["ci_lo"], e["ci_hi"]), n=e["n"],
              surface=f"{base}; sign-profile prompt, base model, each country mapped to its profile; profile-block "
                      "bootstrap (26 clusters)", run_id=RUN_SP_STRICT64, script=f, out=o)
    dsurf = f"{base}; route-GPS minus persona-GPS Spearman; paired profile-block bootstrap (26 clusters)"
    e = d["E2"]
    t.add("PX_D_cohort1_trust", f"Design-locked primary contrast (C8 E2), cohort-1 adapters minus persona, "
          f"trust: {e['reading']}", "difference of Spearman rho", e["point"], ci=(e["ci_lo"], e["ci_hi"]), n=e["n"],
          surface=dsurf, run_id=run, script=f, out=o)
    e = d["E4"]["E2_country_bootstrap"]
    t.add("PX_D_cohort1_trust_country", f"Primary contrast under the country bootstrap (sensitivity): {e['reading']}",
          "difference of Spearman rho", e["point"], ci=(e["ci_lo"], e["ci_hi"]), n=e["n"],
          surface=f"{base}; route-GPS minus persona-GPS Spearman; paired country bootstrap", run_id=run, script=f,
          out=o)
    for route, name in (("C1", "cohort1"), ("B2", "bank2"), ("SP", "signprompt")):
        for s, e in d["E3"][route].items():
            t.add(f"PX_D_{name}_{s}", f"{name} minus persona, {s}", "difference of Spearman rho", e["point"],
                  ci=(e["ci_lo"], e["ci_hi"]), n=e["n"], surface=f"{dsurf}; descriptive, not a test", run_id=run,
                  script=f, out=o)
    dev = "strict battery; the 16 development-stage countries; Spearman; country bootstrap; descriptive"
    for key, rid, who in (("C1_trust", "PX_dev16_cohort1_trust_rho", "cohort-1 adapters"),
                          ("P_trust", "PX_dev16_persona_trust_rho", "persona prompt")):
        e = d["E5"][key]
        t.add(rid, f"Trust-GPS on the 16 development countries, {who}", "Spearman rho", e["point"],
              ci=(e["ci_lo"], e["ci_hi"]), n=e["n"], surface=dev, run_id=run, script=f, out=o)
    g = d["base_parity"]
    t.add("PX_G3_base_max_dlogprob", "G3: fresh base model vs the banked strict base, largest option log-probability "
          "gap", "max |delta log p|", g["max_dlogprob"], n=g["n_rows"],
          surface=f"strict battery; base model; persona run vs {g['reference_run']}", run_id=d["run_id"], script=f,
          out=o)


# ------------------------------------------------------------------ C9 descriptive rows (Amendment C9)
C9_LABEL = "DESCRIPTIVE / NOT PREREGISTERED"
C9_PARTS = {
    "a_cohort1_three_column": "cohort-1 adapters, three columns (adapter-GPS, adapter-human, human-GPS)",
    "b_bank2": "bank-2 adapters, same three columns (robustness)",
    "c_between_profile": "between-profile share of variance and one-sided permutation p, shared sign profiles",
    "c_power": "power of the grouping test (simulation over the realized 12 groups)",
    "d_sign_mate": "agreement among countries that share a sign profile (leave-one-out); not a ceiling",
    "e_gps_sign_reference": "reference scorers built from the GPS signs; mechanical, not success tests",
    "f_preprint_items": "item-level and complete-case variants of the preprint's human-agreement readouts",
}


def c9_human_agreement_rows(t: Table):
    """C9-1: every row of c9_human_agreement.json becomes one row (value, interval, n as the producer stored them)."""
    o, f = f"{RES}/c9/c9_human_agreement.json", "paper_b/c9_human_agreement.py"
    d = _read(o)
    run = f"{RUN_COHORT1}; {RUN_STRICT_B2}"
    for r in d["rows"]:
        ci = (r["ci_low"], r["ci_high"]) if r["ci_low"] is not None else None
        surf = (f"{r['surface_label_short']}; {C9_PARTS[r['part']]}; strict 23-item battery; {r['interval_type']}; "
                f"{C9_LABEL}")
        note = f"; {r['note']}" if r["note"] else ""
        if r["interval_type"].startswith("permutation null"):
            note += "; the interval is the percentile band of the permutation null, not a confidence interval"
        t.add(r["claim_id"], f"C9-1 ({r['part']}): {r['column']}, {r['surface_label_short']}{note}. Descriptive, "
              "not preregistered; the held-out and human-agreement readouts stay retrospective", r["statistic"],
              r["value"], ci=ci, n=r["n"], surface=surf, run_id=run, script=f, out=o)


def c9_tvd_rows(t: Table):
    """C9-2: TVD to the survey distribution for the base, adapter and persona cells. The adapter+persona cell is
    pending (its run is not on the Hub), so it has no row."""
    o, f = f"{RES}/c9/c9_tvd.json", "paper_b/c9_tvd.py"
    d = _read(o)
    run = f"{RUN_COHORT1}; persona-strict-v1-20261019"
    base = f"strict 23-item battery; 42 countries; total variation distance to the survey-weighted answer shares; {C9_LABEL}"
    for cell, c in d["cells"].items():
        if c["status"] != "ok":
            continue
        who = {"base": "base model", "adapter": "country adapters (cohort 1)", "persona": "country-named persona prompt"}[cell]
        kw = dict(run_id=run, script=f, out=o)
        t.add(f"C9_TVD_{cell}_mean_tvd_country_equal", f"C9-2 descriptive: mean TVD to humans, {who}; country-equal "
              "(mean of country means); lower is closer", "mean TVD, country-equal", c["mean_tvd_country_equal"],
              n=c["n_countries"], surface=f"{base}; cell {cell}", **kw)
        t.add(f"C9_TVD_{cell}_mean_tvd_pooled", f"C9-2 descriptive: mean TVD to humans, {who}; pooled over "
              "country-item cells (the preprint's aggregation)", "mean TVD, pooled", c["mean_tvd_pooled"],
              n=c["n_cells"], surface=f"{base}; cell {cell}; one cell lost to the JOR/Q178 complete case", **kw)
        for dim, v in c["per_dimension"].items():
            t.add(f"C9_TVD_{cell}_{dim}_mean_tvd_country_equal", f"C9-2 descriptive: mean TVD, {who}, {dim} items; "
                  "country-equal", "mean TVD, country-equal", v, n=d["cells"][cell]["n_countries"],
                  surface=f"{base}; cell {cell}; {dim} items", **kw)
        g = c["trust_gps"]
        if g["status"] != "ok":
            continue
        for unit, name in (("profile_block", "profile-block"), ("country", "country")):
            u = g[unit]
            t.add(f"C9_TVD_{cell}_trust_gps_{unit}", f"C9-2 descriptive: trust-GPS Spearman of the {who}; {name} "
                  "bootstrap", "Spearman rho", u["point"], ci=(u["ci_lo"], u["ci_hi"]), n=u["n"],
                  surface=f"strict 23-item battery; 42 countries; trust composite; {name} bootstrap; {C9_LABEL}", **kw)
    for name, c in d["contrasts"].items():
        a, b = name.split("_minus_")
        for unit, uname in (("profile_block", "profile-block"), ("country", "country")):
            u = c[unit]
            t.add(f"C9_TVD_{name}_{unit}", f"C9-2 descriptive: mean TVD of {a} minus {b} (negative = {a} closer to "
                  f"humans); paired {uname} bootstrap", "difference of mean TVD", u["point"],
                  ci=(u["ci_lo"], u["ci_hi"]), n=u["n"], surface=f"{base}; paired {uname} bootstrap", run_id=run,
                  script=f, out=o)


def c9_w1_rows(t: Table):
    """W1: behavioral factorial decomposition of the bank-2 adapter main effects. A decomposition of a linear model
    of model outputs, not a neural mechanism; Var(cross)/Var(full) is a ratio that can exceed one."""
    o, f = f"{RES}/c9/w1_why_trust.json", "paper_b/w1_crosstalk.py"
    w = _read(o)
    run = f"{RUN_COHORT1}; {RUN_STRICT_B2}"
    base = (f"bank-2 adapter main effects over the full 2^6 factorial (64 cells) decomposed into own-bit and "
            f"cross-bit terms; GPS z; 42 countries; model quantities only; {C9_LABEL}")
    kw = dict(run_id=run, script=f, out=o)
    use = "W1 behavioral decomposition (not a neural mechanism)"
    ncell = _read(f"{RES}/factorial/factorial_report.json")["route_contrast_64_cells"]["n_cells"]
    for blk in w["adapter"]["cohort1_observed"]:
        s, key = blk["surface"], blk["surface"].replace(":", "_")
        n = blk["n"]
        t.add(f"C9_W1_{key}_spearman_full_vs_gps", f"{use}: Spearman of the main-effects prediction (own + cross) "
              f"with GPS, {s}", "Spearman rho", blk["spearman_full_vs_gps"], n=n, surface=f"{base}; {s}", **kw)
        t.add(f"C9_W1_{key}_spearman_own_vs_gps", f"{use}: Spearman of the own-bit-only prediction with GPS, {s}; "
              "mechanical for a positive own coefficient (it is proportional to sign(z)), not an independent test",
              "Spearman rho", blk["spearman_own_vs_gps"], n=n, surface=f"{base}; {s}", **kw)
        t.add(f"C9_W1_{key}_spearman_cross_vs_gps", f"{use}: Spearman of the cross-bit-only prediction with GPS, {s}",
              "Spearman rho", blk["spearman_cross_vs_gps"], n=n, surface=f"{base}; {s}", **kw)
        t.add(f"C9_W1_{key}_cross_var_share", f"{use}: Var(cross)/Var(full), {s}; a ratio, not a share of "
              "variance explained, and it can exceed 1 through covariance", "Var(cross)/Var(full)",
              blk["cross_var_share"], n=n, surface=f"{base}; {s}", **kw)
        t.add(f"C9_W1_{key}_cross_cov_share", f"{use}: covariance share of the cross term in Var(full), {s}; "
              "bounded and additive", "Cov(cross, full)/Var(full)", blk["cross_cov_share"], n=n,
              surface=f"{base}; {s}", **kw)
        t.add(f"C9_W1_cohort1_{key}_spearman_full_vs_observed", f"{use}: Spearman of the main-effects prediction "
              f"with the observed cohort-1 composite, {s}", "Spearman rho", blk["spearman_full_vs_observed"], n=n,
              surface=f"{base}; {s}; against cohort-1 adapter composites", **kw)
    for blk in w["adapter"]["bank2_observed"]:
        s, key = blk["surface"], blk["surface"].replace(":", "_")
        t.add(f"C9_W1_{key}_main_effect_share_64", f"{use}: share of the 64-cell variance carried by the six main "
              f"effects, {s}", "main-effect share of variance", blk["main_effect_share_64"],
              n=ncell, surface=f"{base}; {s}", **kw)
        t.add(f"C9_W1_bank2_{key}_spearman_full_vs_observed", f"{use}: Spearman of the main-effects prediction with "
              f"the observed bank-2 composite, {s}", "Spearman rho", blk["spearman_full_vs_observed"], n=blk["n"],
              surface=f"{base}; {s}; against bank-2 adapter composites", **kw)
        if "spearman_main_plus_2way_vs_gps" in blk:
            t.add(f"C9_W1_{key}_spearman_main_plus_2way_vs_gps", f"{use}: Spearman of the main-plus-two-way "
                  f"prediction with GPS, {s} (interactions needed here: main effects carry too little variance)",
                  "Spearman rho", blk["spearman_main_plus_2way_vs_gps"], n=blk["n"], surface=f"{base}; {s}", **kw)
    for bank, name in (("bank2", "bank-2 composites"), ("cohort1", "cohort-1 composites")):
        r = w["adapter"][f"rank_{bank}_observed"]
        t.add(f"C9_W1_rank_cross_var_share_vs_failure_{bank}", f"{use}: rank correlation across the surfaces between "
              f"Var(cross)/Var(full) and (1 - adapter-GPS), against {name}; seven points, driven by one surface "
              "(trust) against six, not a graded relation", "Spearman rho over surfaces",
              r["spearman_share_vs_failure"], n=r["n"], surface=f"{base}; across surfaces; against {name}", **kw)
    for bank in ("bank1", "bank2"):
        lc = w["bank_composition"][bank]["label_check"]
        t.add(f"C9_W1_{bank}_label_rows_checked", f"{use}: country-pair rows checked against the sign of the pair's "
              f"own dimension, {bank}", "count of rows", lc["rows_checked"], n=lc["countries"],
              surface=f"{bank} training pairs; 42 countries; {C9_LABEL}", **kw)
        t.add(f"C9_W1_{bank}_label_mismatches", f"{use}: rows whose label departs from the pair's own-dimension "
              f"sign, {bank}", "count of rows", lc["label_mismatches_vs_own_dimension_sign"], n=lc["rows_checked"],
              surface=f"{bank} training pairs; 42 countries; {C9_LABEL}", **kw)


# ------------------------------------------------------------------ assemble
def build_rows(readout_dir: Path = READOUT_DIR) -> list[dict]:
    freeze = json.loads((ROOT / "paper_b/heldout/FREEZE.json").read_text())
    t = Table()
    screen_rows(t, freeze)
    per_dimension_rows(t, freeze)
    comparator_rows(t, freeze)
    readout_rows(t, freeze, readout_dir)
    bank2_rows(t)
    factorial_rows(t)
    replicate_rows(t)
    near_zero_rows(t)
    hash_rows(t)
    persona_rows(t)
    c9_human_agreement_rows(t)
    c9_tvd_rows(t)
    c9_w1_rows(t)
    return t.rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--readout-dir", default=str(READOUT_DIR))
    a = ap.parse_args(argv)
    rows = build_rows(Path(a.readout_dir))
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
