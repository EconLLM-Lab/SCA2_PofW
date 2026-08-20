#!/usr/bin/env python3
"""09_temperature_scaling.py — inference temperature sweep on WVS option probabilities.

Post-hoc temperature scaling of the already-scored option probabilities
(p_i(T) = p_i^(1/T) / sum_j p_j^(1/T); T=1 recovers the shipped run). No new
inference, no WVS in training — the sweep only reshapes the softmax.

Verified against the committed metrics (probe 2026-08-19): T=1 recomputation
matches wvs_question_metrics_long.parquet TVD to 1e-13 on every tested item.

Scope: single-choice items only (binary + ordered). Multi-select options are
independent Bernoulli probabilities (not a softmax) and numeric-open items have
no option grid — both excluded, exactly as the committed scale-family map says.

Run: unset PYTHONPATH && .venv/bin/python analysis/phase2/09_temperature_scaling.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[2]
RAW = REPO / "data" / "phase2" / "raw" / "wvs"
CANON = REPO / "DPO_eval_WVS" / "eval_results_wvs_wave7"
OUT = REPO / "analysis" / "phase2" / "outputs"
WVS_DIR = REPO / "data" / "wvs_eval_full"

DIM_ITEMS = {
    "trust": ["Q57", "Q59", "Q61", "Q62", "Q63", "Q64", "Q69", "Q70",
              "Q71", "Q58", "Q60", "Q73"],
    "patience": ["Q13", "Q14", "Q43", "Q50"],
    "risktaking": ["Q106", "Q107", "Q109", "Q178"],
    "posrecip": ["Q12", "Q174", "Q81"],
    "negrecip": ["Q176", "Q177", "Q179", "Q195"],
    "altruism": ["Q101", "Q99", "Q103"],
}
ALL_ITEMS = [q for vals in DIM_ITEMS.values() for q in vals]
ADAPTERS = [c + "_adapter" for c in [
    "CHN", "JPN", "GBR", "USA", "MEX", "ARG", "DEU", "RUS",
    "IND", "IDN", "NGA", "EGY", "TUR", "NLD", "BRA", "GRC"]]
TEMPS = [1.0, 1.25, 1.5, 2.0, 3.0]
BANK_PRECEDENCE = {"usamex_canonical": 0, "ksenias_base8": 1, "co2_8": 2}


def load_options() -> pd.DataFrame:
    fams = []
    for family, path in [
        ("usamex_canonical", CANON / "model_option_probabilities.csv"),
        ("ksenias_base8", RAW / "ksenias_base8" / "model_option_probabilities.csv"),
        ("co2_8", RAW / "co2_8" / "model_option_probabilities.csv"),
    ]:
        if not path.exists():
            print(f"WARN missing {family}: {path}")
            continue
        df = pd.read_csv(path, usecols=[
            "model", "eval_country", "question_id", "response_type",
            "is_numeric_open", "option_value", "model_prob"])
        df["bank"] = family
        fams.append(df)
    allf = pd.concat(fams, ignore_index=True)
    allf["model"] = allf["model"].replace({"US": "USA", "Mexico": "MEX"})
    allf = allf[allf["eval_country"].notna()].copy()
    allf = allf[allf["is_numeric_open"] != True].copy()  # bool dtype in CSV
    return allf


def load_population() -> pd.DataFrame:
    fams = []
    for family, path in [
        ("usamex_canonical", CANON / "population_response_distributions.csv"),
        ("ksenias_base8", RAW / "ksenias_base8" / "population_response_distributions.csv"),
        ("co2_8", RAW / "co2_8" / "population_response_distributions.csv"),
    ]:
        if not path.exists():
            continue
        df = pd.read_csv(path, usecols=[
            "eval_country", "question_id", "option_value", "population_prob"])
        df["bank"] = family
        fams.append(df)
    pop = pd.concat(fams, ignore_index=True)
    pop["bank_rank"] = pop["bank"].map(BANK_PRECEDENCE)
    return (pop.sort_values("bank_rank")
            .drop_duplicates(["eval_country", "question_id", "option_value"],
                             keep="first"))


def metrics_for_temp(opts: pd.DataFrame, pop: pd.DataFrame, T: float) -> pd.DataFrame:
    rows = []
    for (model, ec), g in opts.groupby(["model", "eval_country"]):
        for q, d in g.groupby("question_id"):
            d = d.sort_values("option_value")
            p = d["option_value"].values.astype(float)
            pm = d["model_prob"].values.astype(float)
            pm = pm / pm.sum()
            p2 = pop[(pop["eval_country"] == ec) & (pop["question_id"] == q)]
            merged = pd.DataFrame({"option_value": p, "pm": pm}).merge(
                p2[["option_value", "population_prob"]], on="option_value", how="inner")
            if len(merged) < 2:
                continue
            m = merged["option_value"].values.astype(float)
            pm = merged["pm"].values.astype(float)
            pp = merged["population_prob"].values.astype(float)
            pm = pm / pm.sum()
            pp = pp / pp.sum()
            pt = pm ** (1.0 / T)
            pt = pt / pt.sum()
            tvd = 0.5 * np.abs(pt - pp).sum()
            mj = 0.5 * (pt + pp)
            jsd = 0.5 * (np.sum(pt * np.log2(np.maximum(pt, 1e-12) / np.maximum(mj, 1e-12)))
                         + np.sum(pp * np.log2(np.maximum(pp, 1e-12) / np.maximum(mj, 1e-12))))
            ent_t = float(-np.sum(pt * np.log2(np.maximum(pt, 1e-12))))
            ent_p = float(-np.sum(pp * np.log2(np.maximum(pp, 1e-12))))
            mean_t = float((m * pt).sum())
            mean_p = float((m * pp).sum())
            std_t = float(np.sqrt((((m - mean_t) ** 2) * pt).sum()))
            std_p = float(np.sqrt((((m - mean_p) ** 2) * pp).sum()))
            top_t = float(m[np.argmax(pt)])
            top_p = float(m[np.argmax(pp)])
            rows.append({
                "model": model, "eval_country": ec, "question_id": q,
                "n_options": int(len(m)), "T": T,
                "tv_distance": tvd, "js_divergence": jsd,
                "model_entropy": ent_t, "population_entropy": ent_p,
                "entropy_error": ent_t - ent_p,
                "model_mean": mean_t, "population_mean": mean_p,
                "mean_error": mean_t - mean_p,
                "model_std": std_t, "population_std": std_p,
                "std_error": std_t - std_p,
                "top_option_match": float(top_t == top_p),
            })
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    opts = load_options()
    pop = load_population()
    print(f"option rows: {len(opts)} | population rows: {len(pop)}")

    # keep adapters + base; matched cells only (adapter on own country)
    opts = opts[opts["model"].isin(ADAPTERS + ["base"])].copy()
    opts["own"] = opts["model"].str.replace("_adapter", "", regex=False)
    # matched cells: adapter on OWN country only (CO2 combined file is a full
    # cross grid, so eval_country must equal the adapter's country)
    matched = opts[((opts["model"] == "base")
                    | ((opts["model"] == opts["own"] + "_adapter")
                       & (opts["eval_country"] == opts["own"])))].copy()
    # dedupe with bank precedence FIRST (CO2 combined file is a full cross grid;
    # USA/MEX appear in both usamex and ksenias banks), then split item scopes
    matched["bank_rank"] = matched["bank"].map(BANK_PRECEDENCE)
    matched = (matched.sort_values("bank_rank")
               .drop_duplicates(["model", "eval_country", "question_id", "option_value"],
                                keep="first"))
    # multi-select is not a softmax: exclude from the TVD sweep (family labels
    # come from the committed map), but KEEP the full item set for CF_ST below
    multi = set(pd.read_parquet(OUT / "wvs_question_metrics_long.parquet")
                .loc[lambda d: d["scale_family"] == "multi_select", "question_id"])
    matched_all = matched.copy()  # full item set (for CF_ST rank)
    matched = matched[~matched["question_id"].isin(multi)].copy()
    print(f"matched single-choice rows: {len(matched)}")
    print("models:", sorted(matched["model"].unique()))

    frames = [metrics_for_temp(matched, pop, T) for T in TEMPS]
    mdf = pd.concat(frames, ignore_index=True)

    # family labels from the committed scale map (single_choice only)
    fam = (pd.read_parquet(OUT / "wvs_question_metrics_long.parquet")
           [["question_id", "scale_family"]].drop_duplicates("question_id"))
    mdf = mdf.merge(fam, on="question_id", how="left")
    mdf["is_adapter"] = mdf["model"] != "base"

    agg_cols = {"tv_distance": "mean", "entropy_error": "mean", "std_error": "mean",
                "mean_error": "mean", "top_option_match": "mean", "js_divergence": "mean"}
    # adapter-only aggregations (base is a separate reference row at T=1)
    ad = mdf[mdf["is_adapter"]].copy()
    by_t = ad.groupby(["T"]).agg(agg_cols).round(4)
    by_fam = ad.groupby(["T", "scale_family"]).agg(agg_cols).round(4)
    by_country = ad.groupby(["T", "eval_country"]).agg(agg_cols).round(4)
    by_t.to_csv(OUT / "temp_scale_pooled.csv")
    by_fam.to_csv(OUT / "temp_scale_by_family.csv")
    by_country.to_csv(OUT / "temp_scale_by_country.csv")

    # base reference at T=1 (single-choice subset, same items)
    base1 = mdf[(mdf["model"] == "base") & (mdf["T"] == 1.0)]
    base_ref = base1.groupby("scale_family").agg(agg_cols).round(4)
    base_ref.to_csv(OUT / "temp_scale_base_reference.csv")
    print("\n=== base model reference at T=1 (same single-choice items) ===")
    print(base_ref.to_string())

    print("\n=== pooled matched metrics vs T (single-choice items) ===")
    print(by_t.to_string())
    print("\n=== by scale family ===")
    print(by_fam.to_string())
    print("\n=== per country (adapters only) ===")
    print(by_country.to_string())

    print("\n=== T minimizing |mean entropy_error| per family ===")
    tstar_rows = []
    for fam in sorted(set(mdf["scale_family"].dropna())):
        sub = mdf[mdf["scale_family"] == fam]
        best = min(TEMPS, key=lambda T: abs(sub[sub["T"] == T]["entropy_error"].mean()))
        tstar_rows.append({"scale_family": fam, "T_star": best,
                           "entropy_error_at_Tstar":
                               float(sub[sub["T"] == best]["entropy_error"].mean()),
                           "tvd_at_Tstar":
                               float(sub[sub["T"] == best]["tv_distance"].mean())})
    print(pd.DataFrame(tstar_rows).to_string(index=False))
    pd.DataFrame(tstar_rows).to_csv(OUT / "temp_scale_Tstar.csv", index=False)

    # ---- CF_ST matched rank at T=1 vs T=2 (does location move?) ----
    print("\n=== CF_ST matched-country rank at T=1 vs T=2 (location check) ===")
    countries = {}
    for f in sorted(WVS_DIR.glob("*_WVS_wave7.parquet")):
        cc = f.name.split("_")[0]
        df = pd.read_parquet(f, columns=["W_WEIGHT"] + ALL_ITEMS)
        w = df["W_WEIGHT"].fillna(0)
        dist = {}
        for it in ALL_ITEMS:
            v = df[it]
            m = (v >= 0) & (w > 0)
            if m.sum() < 50:
                continue
            p = pd.DataFrame({"v": v[m].astype(float), "w": w[m]}).groupby("v")["w"].sum()
            probs = p.values.astype(float)
            probs = probs / probs.sum()
            dist[it] = (probs, p.index.values.astype(float))
        countries[cc] = dist

    def cfst(pA, pB, vals):
        xA = float((vals * pA).sum()); xB = float((vals * pB).sum())
        x = (xA + xB) / 2.0
        vT = 0.5 * float(((pA * (vals - x) ** 2).sum() + (pB * (vals - x) ** 2).sum()))
        vG = 0.5 * ((xA - x) ** 2 + (xB - x) ** 2)
        return vG / vT if vT > 1e-12 else 0.0

    def adapter_dist_raw(model: str, T: float) -> dict:
        """Full 30-item adapter distribution; temperature applies to
        single-choice items, multi-select options stay at T=1 (no softmax)."""
        sub = matched_all[matched_all["model"] == model]
        dist = {}
        for q, g in sub.groupby("question_id"):
            g = g.sort_values("option_value")
            p = g["model_prob"].values.astype(float)
            p = p / p.sum()
            if q not in multi:
                pt = p ** (1.0 / T)
                pt = pt / pt.sum()
            else:
                pt = p
            dist[q] = (pt, g["option_value"].values.astype(float))
        return dist

    rank_rows = []
    for T in [1.0, 2.0]:
        for model in ADAPTERS:
            own = model.replace("_adapter", "")
            d = adapter_dist_raw(model, T)
            if not d:
                continue
            dists = []
            for cc, cdist in countries.items():
                items = [q for q in ALL_ITEMS if q in d and q in cdist]
                vals = []
                for q in items:
                    pA, vA = d[q]; pB, vB = cdist[q]
                    if len(pA) != len(pB) or not np.allclose(vA, vB):
                        continue
                    vals.append(cfst(pA, pB, vA))
                dists.append((cc, float(np.mean(vals)) if vals else np.nan))
            dists = [x for x in dists if np.isfinite(x[1])]
            dists.sort(key=lambda x: x[1])
            order = [c for c, _ in dists]
            rank = order.index(own) + 1 if own in order else np.nan
            rank_rows.append({"T": T, "adapter": model, "rank_of_42": rank,
                              "nearest": dists[0][0] if dists else np.nan})
    ranks = pd.DataFrame(rank_rows).pivot(index="adapter", columns="T", values="rank_of_42")
    ranks.columns = [f"rank_T{int(c)}" for c in ranks.columns]
    ranks = ranks.sort_values("rank_T1")
    ranks.to_csv(OUT / "temp_scale_cfst_rank.csv")
    print(ranks.round(1).to_string())
    print(f"median rank T=1: {ranks['rank_T1'].median()}  T=2: {ranks['rank_T2'].median()} (chance 21.5)")

    print("\nwrote temp_scale_pooled.csv, temp_scale_by_family.csv, "
          "temp_scale_by_country.csv, temp_scale_Tstar.csv, temp_scale_cfst_rank.csv")


if __name__ == "__main__":
    main()
