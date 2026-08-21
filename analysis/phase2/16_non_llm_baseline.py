#!/usr/bin/env python3
"""16_non_llm_baseline.py -- non-LLM aggregate baseline (RESOLVED #2, locked 2026-08-20).

Named non-LLM aggregate benchmark for the position paper's mandatory baseline (iii),
computed on the canonical Table-1 surface so every cell is directly comparable.

PREDECLARED CONSTRUCTION (fixed before any outcome inspection, 2026-08-21):
  b = 0.5.  z-to-moment mapping:  mu(c,q) = midpoint(recoded grid of q) + b * z[c][dim(q)]
  Max-entropy moment-constrained predictor (equivalently IPF/raking from a uniform seed;
  Deming & Stephan 1940; Jaynes 1957; Golan-Judge-Miller 1996): the flattest distribution
  over q's option grid whose (recoded) first moment equals mu.
      p_k ∝ exp(theta * r_k),  r_k = recoded option values,  theta solves sum r_k p_k = mu
      (bisection on theta; numpy only).
  CLAMPING (declared a priori): if mu falls outside the grid support, clamp mu to the
  nearest boundary; the max-entropy solution at the boundary is the degenerate point mass
  at the boundary option (= sign-follower for that cell). Audit found exactly 1 such cell:
  MEX x Q174 (posrecip, binary recoded grid {0,1}, z=-1.038 -> mu=-0.019 -> clamped to 0).
  Arm B (sign-follower, degenerate): all mass on the option whose recoded value is max if
  z >= 0 else min -- the hard-DPO label rule (chosen = high side iff z >= 0) realized
  mechanically.

  Information budget: declared GPS anchors only. No WVS, no microdata, no LLM, never fit
  to WVS. Recodes (INVERT_1_4 / INVERT_10 / BINARY_TRUST) and metrics are byte-identical
  to 13_unified_comparison.py / the canonical eval notebook.

Outputs (analysis/phase2/outputs/):
  nonllm_baseline_summary_by_country.csv   per (arm, country) pooled TVD/JSD/ent/err/top
  nonllm_baseline_pooled.csv               pooled over 16 countries per arm
  nonllm_baseline_table1_extension.csv     like-for-like 27-item table: adapter/base/
                                           persona/noise (re-pooled from the canonical
                                           item-level long file) + armA + armB
  nonllm_baseline_cross_rank.csv           42-country own-rank for armA/armB (parquet pop)
  nonllm_baseline_bridge.csv               composite rho vs GPS z per dim (diagnostic)

Run: env -u PYTHONPATH .venv/bin/python analysis/phase2/16_non_llm_baseline.py
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "analysis" / "phase2" / "outputs"
CANON = REPO / "DPO_eval_WVS" / "eval_results_wvs_wave7"
RAW = REPO / "data" / "phase2" / "raw" / "wvs"
WVS_DIR = REPO / "data" / "wvs_eval_full"
GPS_JSON = REPO / "synthetic_generation" / "outputs" / "gps_sign_relabel_all" / "gps_z_vectors.json"

B = 0.5  # PREDECLARED slope, locked 2026-08-21
CLAMP = True  # PREDECLARED: clamp mu to grid support; boundary -> point mass

DIMS = ["patience", "risktaking", "posrecip", "negrecip", "altruism", "trust"]
DIM_ITEMS = {
    "trust": ["Q57", "Q59", "Q61", "Q62", "Q63", "Q64", "Q69", "Q70", "Q71", "Q58", "Q60", "Q73"],
    "patience": ["Q13", "Q14", "Q43", "Q50"],
    "risktaking": ["Q106", "Q107", "Q109", "Q178"],
    "posrecip": ["Q12", "Q174", "Q81"],
    "negrecip": ["Q176", "Q177", "Q179", "Q195"],
    "altruism": ["Q101", "Q99", "Q103"],
}
ALL_ITEMS = [q for vals in DIM_ITEMS.values() for q in vals]
MULTI_SELECT = {"Q12", "Q13", "Q14"}  # excluded from the single-choice universe
UNIVERSE = [q for q in ALL_ITEMS if q not in MULTI_SELECT]  # 27 mapped single-choice items
ITEM_DIM = {q: d for d, items in DIM_ITEMS.items() for q in items}

INVERT_1_4 = {"Q59", "Q61", "Q62", "Q63", "Q64", "Q69", "Q70", "Q71", "Q58", "Q60", "Q73", "Q81"}
INVERT_10 = {"Q177", "Q179"}
BINARY_TRUST = {"Q57", "Q12", "Q13", "Q14", "Q174"}

BANK_PRECEDENCE = {"usamex_canonical": 0, "ksenias_base8": 1, "co2_8": 2}
ADAPTERS = ["ARG", "BRA", "CHN", "DEU", "EGY", "GBR", "GRC", "IDN", "IND", "JPN",
            "MEX", "NGA", "NLD", "RUS", "TUR", "USA"]


def recode(raw: float, item: str) -> float:
    s = float(raw)
    if item in INVERT_1_4:
        return 5.0 - s
    if item in INVERT_10:
        return 11.0 - s
    if item in BINARY_TRUST:
        return 1.0 if s == 1.0 else 0.0
    return s


def load_z() -> pd.DataFrame:
    """GPS z per (country, dim) for the 16 adapter countries."""
    z = json.loads(GPS_JSON.read_text())
    rows = [{"country": c, "dim": d, "z": z[c][d]} for c in ADAPTERS for d in DIMS]
    return pd.DataFrame(rows)


def load_population() -> pd.DataFrame:
    """Harmonized population option distributions, bank precedence (as script 13/15)."""
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
            .drop_duplicates(["eval_country", "question_id", "option_value"], keep="first"))


def max_entropy_on_grid(r_grid: np.ndarray, mu: float) -> np.ndarray:
    """Max-entropy distribution over recoded grid r_grid with mean mu (numpy only).

    p_k ∝ exp(theta * r_k), theta by bisection on m(theta) = sum r_k p_k.
    mu is clamped to [r_min, r_max] by the caller when CLAMP is set; at the exact
    boundary the solution is the degenerate point mass.
    """
    r = np.asarray(r_grid, dtype=float)
    rmin, rmax = r.min(), r.max()
    if mu <= rmin:
        p = np.zeros_like(r)
        p[np.argmin(r)] = 1.0
        return p
    if mu >= rmax:
        p = np.zeros_like(r)
        p[np.argmax(r)] = 1.0
        return p

    def mean_at(theta: float) -> float:
        w = np.exp(theta * (r - rmin))  # stabilized
        w = w / w.sum()
        return float((r * w).sum())

    lo, hi = -60.0, 60.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if mean_at(mid) < mu:
            lo = mid
        else:
            hi = mid
    theta = 0.5 * (lo + hi)
    w = np.exp(theta * (r - rmin))
    return w / w.sum()


def sign_follower(z: float, r_grid: np.ndarray) -> np.ndarray:
    """All mass on the option with max recoded value if z>=0 else min."""
    p = np.zeros_like(np.asarray(r_grid, dtype=float))
    idx = int(np.argmax(r_grid)) if z >= 0 else int(np.argmin(r_grid))
    p[idx] = 1.0
    return p


def arm_distributions(z_df: pd.DataFrame, pop: pd.DataFrame, arm: str) -> pd.DataFrame:
    """Per (country, item, raw option_value) baseline option probabilities."""
    rows = []
    clamped = []
    for c in ADAPTERS:
        zc = z_df[z_df["country"] == c].set_index("dim")["z"]
        for q in UNIVERSE:
            dim = ITEM_DIM[q]
            g = pop[(pop["eval_country"] == c) & (pop["question_id"] == q)].sort_values("option_value")
            if g.empty:
                continue
            raw_vals = g["option_value"].values.astype(float)
            r_grid = np.array([recode(v, q) for v in raw_vals], dtype=float)
            z = float(zc[dim])
            if arm == "armA":
                mu = float(r_grid.mean()) + B * z  # midpoint of recoded grid
                mu_orig = mu
                if CLAMP:
                    mu = float(np.clip(mu, r_grid.min(), r_grid.max()))
                    if mu != mu_orig:
                        clamped.append((c, q, mu_orig, mu))
                p = max_entropy_on_grid(r_grid, mu)
            else:  # armB
                p = sign_follower(z, r_grid)
            for v, pr in zip(raw_vals, p):
                rows.append({"model": f"{arm}_{c}", "eval_country": c, "question_id": q,
                             "option_value": float(v), "model_prob": float(pr)})
    print(f"  {arm}: {len(rows)} option rows; clamped cells: {clamped}")
    return pd.DataFrame(rows)


def item_metrics(opts: pd.DataFrame, pop: pd.DataFrame) -> pd.DataFrame:
    """Byte-identical metric construction to 13_unified_comparison.py."""
    rows = []
    for (model, ec), g in opts.groupby(["model", "eval_country"]):
        for q, d in g.groupby("question_id"):
            d = d.sort_values("option_value")
            p2 = pop[(pop["eval_country"] == ec) & (pop["question_id"] == q)]
            merged = pd.DataFrame({
                "option_value": d["option_value"].values.astype(float),
                "pm": d["model_prob"].values.astype(float),
            }).merge(p2[["option_value", "population_prob"]], on="option_value", how="inner")
            if len(merged) < 2:
                continue
            m = merged["option_value"].values.astype(float)
            pm = merged["pm"].values.astype(float)
            pp = merged["population_prob"].values.astype(float)
            pm = pm / pm.sum()
            pp = pp / pp.sum()
            tvd = 0.5 * np.abs(pm - pp).sum()
            mj = 0.5 * (pm + pp)
            jsd = 0.5 * (np.sum(pm * np.log2(np.maximum(pm, 1e-12) / np.maximum(mj, 1e-12)))
                         + np.sum(pp * np.log2(np.maximum(pp, 1e-12) / np.maximum(mj, 1e-12))))
            ent = float(-np.sum(pm * np.log2(np.maximum(pm, 1e-12))))
            ent_p = float(-np.sum(pp * np.log2(np.maximum(pp, 1e-12))))
            mean = float((m * pm).sum())
            mean_p = float((m * pp).sum())
            std = float(np.sqrt((((m - mean) ** 2) * pm).sum()))
            std_p = float(np.sqrt((((m - mean_p) ** 2) * pp).sum()))
            top = float(m[np.argmax(pm)])
            top_p = float(m[np.argmax(pp)])
            rows.append({
                "model": model, "eval_country": ec, "question_id": q,
                "n_options": int(len(m)), "tv_distance": tvd, "js_divergence": jsd,
                "entropy_error": ent - ent_p, "std_error": std - std_p,
                "mean_error": mean - mean_p, "top_option_match": float(top == top_p),
            })
    return pd.DataFrame(rows)


def pooled_summary(metrics: pd.DataFrame) -> pd.DataFrame:
    """Per (model, country) pooled; then per model over countries (canonical pooling)."""
    by_country = (metrics.groupby(["model", "eval_country"])
                  [["tv_distance", "js_divergence", "entropy_error", "std_error", "top_option_match"]]
                  .mean().reset_index())
    pooled = (metrics.groupby("model")
              [["tv_distance", "js_divergence", "entropy_error", "std_error", "top_option_match"]]
              .mean().reset_index())
    return by_country, pooled


def cross_rank(arm_df: pd.DataFrame, pop42: pd.DataFrame) -> pd.DataFrame:
    """Own-country rank of the baseline arms on the 42-country parquet surface.

    Vectorized: merge model option probs against every country's population on
    (question_id, option_value), renormalize within (model, question) and
    (target, question), per-item TVD (n>=2 merged options), pooled per
    (model, origin, target). No NaNs by construction.
    """
    arm = (arm_df[["model", "eval_country", "question_id", "option_value", "model_prob"]]
           .rename(columns={"eval_country": "origin"}))
    pop = (pop42[["eval_country", "question_id", "option_value", "population_prob"]]
           .rename(columns={"eval_country": "target"}))
    mg = arm.merge(pop, on=["question_id", "option_value"], how="inner")
    if mg.empty:
        return pd.DataFrame()
    sm = mg.groupby(["model", "origin", "target", "question_id"])["model_prob"].transform("sum")
    sp = mg.groupby(["model", "origin", "target", "question_id"])["population_prob"].transform("sum")
    mg = mg[(sm > 0) & (sp > 0)].copy()
    mg["pm"] = mg["model_prob"] / mg.groupby(["model", "origin", "target", "question_id"])["model_prob"].transform("sum")
    mg["pp"] = mg["population_prob"] / mg.groupby(["model", "origin", "target", "question_id"])["population_prob"].transform("sum")
    mg["absdiff"] = (mg["pm"] - mg["pp"]).abs()
    item = (mg.groupby(["model", "origin", "target", "question_id"])
            .agg(tvd=("absdiff", "sum"), n=("option_value", "size")).reset_index())
    item = item[item["n"] >= 2].copy()
    item["tvd"] = 0.5 * item["tvd"]
    pooled = item.groupby(["model", "origin", "target"])["tvd"].mean().reset_index()
    rows = []
    for model in sorted(pooled["model"].unique()):
        sub = pooled[pooled["model"] == model]
        origin = sub["origin"].iloc[0]
        row = sub.set_index("target")["tvd"].dropna()
        if origin not in row.index:
            continue
        own = row[origin]
        rows.append({"model": model, "own_country": origin, "own_tvd": float(own),
                     "own_rank_of_42": int((row < own).sum()) + 1,
                     "nearest": str(row.idxmin())})
    return pd.DataFrame(rows)


def bridge_rho(arm_df: pd.DataFrame, z_df: pd.DataFrame) -> pd.DataFrame:
    """Composite (mean recoded value per country-dim) vs GPS z; Spearman rho (numpy)."""
    rows = []
    for model in sorted(arm_df["model"].unique()):
        c = model.split("_", 1)[1]
        comps = {}
        for dim, items in DIM_ITEMS.items():
            means = []
            for q in items:
                d = arm_df[(arm_df["model"] == model) & (arm_df["question_id"] == q)]
                if d.empty:
                    continue
                pm = d["model_prob"].values.astype(float)
                raw = d["option_value"].values.astype(float)
                pm = pm / pm.sum()
                means.append(recode(float((raw * pm).sum()), q))
            if means:
                comps[dim] = float(np.mean(means))
        for dim in DIMS:
            if dim not in comps:
                continue
            zs = z_df[(z_df["country"] == c) & (z_df["dim"] == dim)]["z"].iloc[0]
            rows.append({"model": model, "eval_country": c, "gps_dimension": dim,
                         "composite": comps[dim], "z": zs})
    comp = pd.DataFrame(rows)
    out = []
    for dim in DIMS:
        sub = comp[comp["gps_dimension"] == dim]
        if len(sub) >= 5:
            out.append({"gps_dimension": dim,
                        "spearman_rho": _spearman(sub["composite"].values, sub["z"].values),
                        "n": len(sub)})
    return pd.DataFrame(out)


def _spearman(a, b):
    """Spearman rho via rank transform + Pearson (numpy only)."""
    ra = pd.Series(a).rank().values
    rb = pd.Series(b).rank().values
    return float(np.corrcoef(ra, rb)[0, 1])


def load_population_parquet(min_n: int = 50) -> pd.DataFrame:
    """42-country survey-weighted option distributions from raw parquet, normalized
    per (country, question); zero-total groups dropped (no NaN downstream)."""
    rows = []
    for f in sorted(WVS_DIR.glob("*_WVS_wave7.parquet")):
        cc = f.name.split("_")[0]
        df = pd.read_parquet(f, columns=["W_WEIGHT"] + UNIVERSE)
        w = df["W_WEIGHT"].fillna(0)
        for q in UNIVERSE:
            v = df[q].dropna()
            wq = w.reindex(v.index)
            keep = (v != -1) & (v != -2) & (v != -3) & (v != -4) & (v != -5) & (wq > 0)
            v, wq = v[keep], wq[keep]
            if len(v) < min_n:
                continue
            sub = pd.DataFrame({"option_value": v.values.astype(float),
                                "w": wq.values.astype(float)})
            agg = sub.groupby("option_value")["w"].sum().reset_index()
            tot = float(agg["w"].sum())
            if tot <= 0:
                continue
            agg["population_prob"] = agg["w"] / tot
            for _, r in agg.iterrows():
                rows.append({"eval_country": cc, "question_id": q,
                             "option_value": float(r["option_value"]),
                             "population_prob": float(r["population_prob"])})
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    z_df = load_z()
    pop = load_population()
    print(f"population surface: {pop['eval_country'].nunique()} countries, "
          f"{pop['question_id'].nunique()} questions (bank precedence)")

    # ---- baseline arms on the canonical 16-country surface ----
    armA = arm_distributions(z_df, pop, "armA")
    armB = arm_distributions(z_df, pop, "armB")
    bas_opts = pd.concat([armA, armB], ignore_index=True)
    bas_metrics = item_metrics(bas_opts, pop)
    bas_by_country, bas_pooled = pooled_summary(bas_metrics)
    bas_by_country.to_csv(OUT / "nonllm_baseline_summary_by_country.csv", index=False)
    bas_pooled.to_csv(OUT / "nonllm_baseline_pooled.csv", index=False)
    print("\n=== baseline arms, pooled over 16 countries (canonical surface) ===")
    print(bas_pooled.round(4).to_string(index=False))

    # ---- like-for-like Table-1 extension: re-pool ALL models on the same 27 items ----
    long = pd.read_csv(OUT / "unified_metrics_long.csv")
    long27 = long[long["question_id"].isin(UNIVERSE)].copy()
    _, pooled27 = pooled_summary(long27)
    ref = pooled27[pooled27["model"].isin(["base", "noise", "persona"])].copy()
    adapter27 = pooled27[pooled27["model"].str.endswith("_adapter")]
    adapter_row = {"model": "adapter", "tv_distance": adapter27["tv_distance"].mean(),
                   "js_divergence": adapter27["js_divergence"].mean(),
                   "entropy_error": adapter27["entropy_error"].mean(),
                   "std_error": adapter27["std_error"].mean(),
                   "top_option_match": adapter27["top_option_match"].mean()}
    bas_pooled["arm"] = bas_pooled["model"].str.split("_", n=1).str[0]
    arm_pooled = (bas_pooled.groupby("arm")[["tv_distance", "js_divergence", "entropy_error",
                                             "std_error", "top_option_match"]].mean()
                  .reset_index().rename(columns={"arm": "model"}))
    ext = pd.concat([ref, pd.DataFrame([adapter_row]), arm_pooled], ignore_index=True)
    ext = ext.rename(columns={"tv_distance": "tvd", "js_divergence": "jsd",
                              "top_option_match": "top_match"})
    ext.to_csv(OUT / "nonllm_baseline_table1_extension.csv", index=False)
    print("\n=== like-for-like 27-item table (adapter/base/persona/noise re-pooled + baseline) ===")
    print(ext.round(4).to_string(index=False))

    # ---- 42-country cross rank (parquet surface) ----
    pop42 = load_population_parquet()
    cr = cross_rank(armA, pop42)
    crB = cross_rank(armB, pop42)
    cr = pd.concat([cr, crB], ignore_index=True)
    cr.to_csv(OUT / "nonllm_baseline_cross_rank.csv", index=False)
    print("\n=== 42-country own-rank (parquet surface) ===")
    print(cr.sort_values(["model"]).to_string(index=False))

    # ---- bridge diagnostic ----
    br = bridge_rho(armA, z_df)
    br.to_csv(OUT / "nonllm_baseline_bridge.csv", index=False)
    print("\n=== armA composite vs GPS z, Spearman rho (diagnostic) ===")
    print(br.groupby("gps_dimension")["spearman_rho"].mean().round(3).to_string())

    # ---- self-check: clamped cell equals sign-follower ----
    mex174A = armA[(armA["eval_country"] == "MEX") & (armA["question_id"] == "Q174")]
    mex174B = armB[(armB["eval_country"] == "MEX") & (armB["question_id"] == "Q174")]
    ok = np.allclose(mex174A["model_prob"].values, mex174B["model_prob"].values)
    print(f"\nself-check: MEX x Q174 armA == armB (clamped boundary): {ok}")
    assert ok

    print("\noutputs written.")


if __name__ == "__main__":
    main()
