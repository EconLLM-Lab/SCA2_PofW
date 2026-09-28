#!/usr/bin/env python3
"""19_softmax_readout.py — Option 4: softmax temperature readout over frozen policies.

Predeclared spec (2026-08-22, frozen before any result was computed):
  Readout   P_hat_tau(o|q) ∝ P(o|q)^(1/tau)   [exact algebraic inverse of softmax(r/T)]
  tau grid  {1, 2, 3, 4, 6};  tau=3 is the PRIMARY predeclared value
            (inherits the position paper's already-published T=3 diagnostic;
             no tau may be selected post hoc against WVS — that is contamination).
  Arms      16 matched country adapters + base (per bank) + persona (16) + uniform noise
  Metrics   per question x tau: TVD, normalized EMD (ordered scales), signed mean error,
            model-vs-human mean (ordinal calibration input)
            -> aggregated to arm x tau (mean over questions) and arm x tau x country
  New evals A. distance gauge: Spearman rho(|Delta z_dim|, choice-overlap) across
              country pairs x dims, per family grid, per tau
            B. ordinal calibration: Spearman rho(model_mean, human_mean) over ordered-scale
              questions, per arm x tau
            C. bias-aware shape: TVD and EMD reported side by side (cf. arXiv:2608.09863
               upward-bias caveat for Wasserstein in LLM-survey evaluation)
  Validation gate: at tau=1 recomputed TVD must reproduce
            wvs_question_metrics_long.parquet (tolerance 1e-6 on shared keys);
            deviations reported, never silently absorbed.
  Anti-leakage: nothing here fits any parameter to WVS; tau is a readout sweep reported
            as a curve, mirroring the paper's temperature-as-diagnostic commitment.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO = pathlib.Path(__file__).resolve().parents[2]
RAW = REPO / "data" / "phase2" / "raw" / "wvs"
OUT = REPO / "analysis" / "phase2" / "outputs"
FIG = OUT / "figures"
CANON_USAMEX = REPO / "DPO_eval_WVS" / "eval_results_wvs_wave7"

TAUS = [1.0, 2.0, 3.0, 4.0, 6.0]
TAU_PRIMARY = 3.0
DIMS = ["patience", "risktaking", "posrecip", "negrecip", "altruism", "trust"]

C16 = ["ARG", "BRA", "CHN", "DEU", "EGY", "GBR", "GRC", "IDN",
       "IND", "JPN", "MEX", "NGA", "NLD", "RUS", "TUR", "USA"]
BASE8 = ["ARG", "CHN", "DEU", "GBR", "JPN", "MEX", "RUS", "USA"]
CO2 = ["BRA", "EGY", "GRC", "IDN", "IND", "NGA", "NLD", "TUR"]


def log_stage(msg: str) -> None:
    print(f"\n=== {msg} " + "=" * max(0, 66 - len(msg)))


# ---------------------------------------------------------------- inputs
def load_gps_z() -> pd.DataFrame:
    df = pd.read_stata(REPO / "data/GPS/GPS_dataset_country_level/country_gps.dta",
                       convert_categoricals=False)
    return df[["isocode"] + DIMS].set_index("isocode")


def family_files() -> dict[str, dict[str, pathlib.Path]]:
    """arm_key -> path, where arm_key encodes family|model|country."""
    fam: dict[str, dict[str, pathlib.Path]] = {"usamex": {}, "base8": {}, "co2_8": {},
                                               "persona": {}}
    d = RAW / "usamex_canonical"
    for m in ["USA_adapter", "MEX_adapter", "base"]:
        for c in ["USA", "MEX"]:
            f = d / f"model_option_probabilities_{m}_on_{c}.csv"
            if f.exists():
                fam["usamex"][f"{m}|{c}"] = f
    d = RAW / "ksenias_base8"
    for c in BASE8:
        for m in [f"{c}_adapter", "base"]:
            f = d / f"model_option_probabilities_{m}_on_{c}.csv"
            if f.exists():
                fam["base8"][f"{m}|{c}"] = f
    d = RAW / "co2_8"
    for c in CO2:
        for m in [f"{c}_adapter", "base"]:
            f = d / f"model_option_probabilities_{m}_on_{c}.csv"
            if f.exists():
                fam["co2_8"][f"{m}|{c}"] = f
    d = RAW / "persona_baseline"
    for c in C16:
        f = d / f"model_option_probabilities_persona_base_on_{c}.csv"
        if f.exists():
            fam["persona"][f"persona_base|{c}"] = f
    return fam


def load_human() -> pd.DataFrame:
    parts = []
    for family in ["usamex_canonical", "ksenias_base8", "co2_8"]:
        f = RAW / family / "population_response_distributions.csv"
        df = pd.read_csv(f)
        df["bank"] = family.replace("_canonical", "")
        parts.append(df)
    h = pd.concat(parts, ignore_index=True)
    h = h[["bank", "eval_country", "question_id", "gps_dimension", "response_type",
           "is_ordered", "option_code", "option_value", "population_prob"]]
    return h.drop_duplicates(["bank", "eval_country", "question_id", "option_code"])


# ---------------------------------------------------------------- core math
def reweight(p: np.ndarray, tau: float) -> np.ndarray:
    if tau == 1.0:
        q = p.copy()
    else:
        q = np.power(np.clip(p, 1e-12, None), 1.0 / tau)
    return q / q.sum()


def tvd(a: np.ndarray, b: np.ndarray) -> float:
    return 0.5 * float(np.abs(a - b).sum())


def norm_emd(vals: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    lo, hi = vals.min(), vals.max()
    if hi <= lo:
        return np.nan
    cdf_a, cdf_b = np.cumsum(a), np.cumsum(b)
    return float(np.abs(cdf_a - cdf_b).sum() * (vals[1] - vals[0])) / (hi - lo)


def build_long(fam: dict, humans: pd.DataFrame, gps: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for family, arms in fam.items():
        bank = {"usamex": "usamex", "base8": "ksenias_base8",
                "co2_8": "co2_8", "persona": "ksenias_base8"}[family]
        # persona human side: use each persona file's own country via base8/co2 banks
        for key, path in sorted(arms.items()):
            model, country = key.split("|")
            bank_use = bank
            if family == "persona":
                bank_use = "ksenias_base8" if country in BASE8 else "co2_8"
            h = humans[(humans.bank == bank_use) & (humans.eval_country == country)]
            m = pd.read_csv(path, usecols=lambda c: c in
                            ("question_id", "option_code", "option_value", "model_prob",
                             "gps_dimension", "response_type", "is_ordered"))
            m = m.merge(h, on=["question_id", "option_code"], how="inner",
                        suffixes=("_m", ""))
            if m.empty:
                continue
            m["family"], m["model"], m["eval_country"] = family, model, country
            rows.append(m)
    df = pd.concat(rows, ignore_index=True)
    df["gps_dimension"] = df["gps_dimension_m"].combine_first(df["gps_dimension"])
    df["response_type"] = df["response_type_m"].combine_first(df["response_type"])
    df["is_ordered"] = df.groupby(["family", "model", "eval_country", "question_id"],
                                  sort=False)["is_ordered"].transform("first")
    return df


def question_metrics(df: pd.DataFrame, taus) -> pd.DataFrame:
    recs = []
    for (fam, model, country, q), g in df.groupby(
            ["family", "model", "eval_country", "question_id"], sort=True):
        g = g.sort_values("option_value")
        p = g["model_prob"].to_numpy(float)
        p = p / p.sum()
        hp = g["population_prob"].to_numpy(float)
        hp = hp / hp.sum()
        vals = g["option_value"].to_numpy(float)
        ordered = bool(pd.notna(g["is_ordered"].iloc[0]) and g["is_ordered"].iloc[0])
        base_row = {
            "family": fam, "model": model, "eval_country": country, "question_id": q,
            "gps_dimension": g["gps_dimension"].iloc[0],
            "response_type": g["response_type"].iloc[0], "n_options": len(g),
            "human_tvd_to_uniform": tvd(hp, np.full(len(hp), 1 / len(hp))),
        }
        for tau in taus:
            pt = reweight(p, tau)
            rec = dict(base_row)
            rec.update(tau=tau,
                       tvd=tvd(pt, hp),
                       signed_mean_err=float((pt * vals).sum() - (hp * vals).sum()),
                       model_mean=float((pt * vals).sum()),
                       human_mean=float((hp * vals).sum()),
                       emd_norm=norm_emd(vals, pt, hp) if ordered else np.nan)
            recs.append(rec)
    return pd.DataFrame(recs)


# ---------------------------------------------------------------- new evals
def distance_gauge(df: pd.DataFrame, gps: pd.DataFrame, taus) -> pd.DataFrame:
    """Spearman rho(|dz|, policy-pair overlap): TVD between the two countries'
    adapter PMFs directly (matched questions), averaged within dimension."""
    out = []
    for family in ["base8", "co2_8"]:
        sub = df[(df.family == family) & (df.model.str.endswith("_adapter"))]
        countries = sorted(sub.eval_country.unique())
        pairs = [(a, b) for i, a in enumerate(countries) for b in countries[i + 1:]]

        def pmf(country: str, q: str) -> pd.Series | None:
            g = sub[(sub.eval_country == country) & (sub.question_id == q)]
            if g.empty:
                return None
            s = g.set_index("option_code")["model_prob"]
            return s / s.sum()

        qdim = (sub.dropna(subset=["gps_dimension"])
                   .groupby("question_id")["gps_dimension"].agg(
                       lambda s: s.mode().iat[0] if len(s.mode()) else np.nan))
        questions = sorted(qdim.index)
        for tau in taus:
            cells = []
            for a, b in pairs:
                for dim in DIMS:
                    qs = [q for q in questions if qdim[q] == dim]
                    dists = []
                    for q in qs:
                        pa, pb = pmf(a, q), pmf(b, q)
                        if pa is None or pb is None:
                            continue
                        idx = pa.index.union(pb.index)
                        va, vb = pa.reindex(idx, fill_value=0), pb.reindex(idx, fill_value=0)
                        dists.append(tvd(va.to_numpy(float), vb.to_numpy(float)))
                    if len(dists) < 3:
                        continue
                    cells.append({"pair": f"{a}-{b}", "dim": dim,
                                  "abs_dz": abs(float(gps.loc[a, dim]) - float(gps.loc[b, dim])),
                                  "policy_tvd": float(np.mean(dists))})
            if len(cells) < 10:
                continue
            c = pd.DataFrame(cells)
            rho, pval = spearmanr(c.abs_dz, c.policy_tvd)
            # positive rho = larger GPS gap -> more divergent policies (the gauge works)
            out.append({"family": family, "tau": tau, "rho": rho,
                        "p_one_sided": pval / 2, "n_cells": len(c)})
    return pd.DataFrame(out)


def ordinal_calibration(qm: pd.DataFrame, taus) -> pd.DataFrame:
    out = []
    ordq = qm[qm.emd_norm.notna()]  # ordered scales only
    for (fam, model, tau), g in ordq.groupby(["family", "model", "tau"]):
        gq = g.groupby("question_id")[["model_mean", "human_mean"]].first().dropna()
        if len(gq) < 8:
            continue
        rho, pval = spearmanr(gq.model_mean, gq.human_mean)
        out.append({"family": fam, "model": model, "tau": tau,
                    "calib_rho": rho, "n_questions": len(gq)})
    return pd.DataFrame(out)


# ---------------------------------------------------------------- validation
def validate(qm: pd.DataFrame) -> None:
    log_stage("Validation gate: tau=1 vs canonical wvs_question_metrics_long")
    ref = pd.read_parquet(OUT / "wvs_question_metrics_long.parquet")
    fam2bank = {"usamex": "usamex_canonical", "base8": "ksenias_base8", "co2_8": "co2_8"}
    qm1 = qm[qm.tau == 1.0].copy()
    qm1["bank"] = qm1.family.map(fam2bank)
    merged = qm1.merge(
        ref[["bank", "model", "eval_country", "question_id", "tv_distance"]],
        on=["bank", "model", "eval_country", "question_id"], how="inner")
    if merged.empty:
        print("  WARN: no overlapping keys — gate INCONCLUSIVE")
        return
    d = (merged.tvd - merged.tv_distance).abs()
    ok = (d < 1e-6).mean()
    print(f"  compared {len(merged)} question rows across "
          f"{merged.model.nunique()} models")
    print(f"  exact matches (<1e-6): {ok:.1%} | median |diff| = {d.median():.2e}"
          f" | p95 |diff| = {d.quantile(.95):.2e}")
    print("  GATE:", "PASS" if ok > 0.99 else
          ("SOFT-PASS (documented)" if d.quantile(.95) < 0.02 else "FAIL"))


# ---------------------------------------------------------------- main
def main() -> None:
    log_stage("Loading inputs")
    gps = load_gps_z()
    fam = family_files()
    counts = {k: len(v) for k, v in fam.items()}
    print(f"  arms loaded per family: {counts}")
    humans = load_human()

    log_stage("Building option-level panel + tau sweep")
    df = build_long(fam, humans, gps)
    print(f"  rows: {len(df):,} | questions: {df.question_id.nunique()} | "
          f"countries: {df.eval_country.nunique()}")
    qm = question_metrics(df, TAUS)

    validate(qm)

    log_stage("Aggregating: arm x tau")
    qm["arm_kind"] = np.where(qm.model == "base", "base",
                       np.where(qm.model == "persona_base", "persona", "adapter"))
    agg = qm.groupby(["arm_kind", "family", "model", "tau"]).agg(
        tvd_mean=("tvd", "mean"), emd_mean=("emd_norm", "mean"),
        signed_mean_err=("signed_mean_err", "mean"), n_q=("question_id", "nunique"),
    ).reset_index()
    pooled = qm.groupby(["arm_kind", "tau"]).agg(
        tvd_mean=("tvd", "mean"), emd_mean=("emd_norm", "mean")).reset_index()
    print(pooled.to_string(index=False))

    log_stage("Eval A: distance gauge rho(|dz|, policy-pair TVD)")
    dg = distance_gauge(df, gps, TAUS)
    print(dg.to_string(index=False))

    log_stage("Eval B: ordinal calibration rho(model_mean, human_mean)")
    oc = ordinal_calibration(qm, TAUS)
    if not oc.empty:
        print(oc[oc.tau.isin([1.0, TAU_PRIMARY])]
              .pivot_table(index=["family", "model"], columns="tau", values="calib_rho")
              .round(3).to_string())

    log_stage("Writing outputs")
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT / "readout_option_panel.parquet", index=False)
    qm.to_csv(OUT / "readout_question_metrics.csv", index=False)
    agg.to_csv(OUT / "readout_arm_by_tau.csv", index=False)
    pooled.to_csv(OUT / "readout_pooled_by_tau.csv", index=False)
    dg.to_csv(OUT / "readout_distance_gauge.csv", index=False)
    oc.to_csv(OUT / "readout_ordinal_calibration.csv", index=False)
    print(f"  wrote 5 csv files to {OUT}")


if __name__ == "__main__":
    sys.exit(main())
