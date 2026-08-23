#!/usr/bin/env python3
"""17_anchor_permutation_placebo.py — restricted permutation placebo (final).

PREDECLARED BEFORE OUTCOME INSPECTION (2026-08-20):
  Null: the real country->anchor assignment is one draw from the observed
  anchor multiset (permute the 16 observed anchors among the 16 countries
  without replacement).
  Primary statistic:  trust construct-bridge Spearman rho — Spearman between
    the 16 (adapter trust composite, GPS country z) pairs under the pairing.
    Composite = mean of E[recode(V)] over the trust items (G0 freeze,
    script 13): binary Q57 is P(option 1); Likert inversions are linear.
    recode(E[V]) is forbidden — it zeros Q57. Canonical files, bank
    precedence, matched cells.
  Secondary: median own-country rank (canonical 42-country matrix, script 15);
             development-trust rho (unified development table).
  Margin: real value > 95th percentile of null (p<=0.05, one-sided).
  N = 1000, seed 20260820.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "analysis" / "phase2" / "outputs"
RAW = REPO / "data" / "phase2" / "raw" / "wvs"
CANON = REPO / "DPO_eval_WVS" / "eval_results_wvs_wave7"

ADAPTERS = ["ARG", "BRA", "CHN", "DEU", "EGY", "GBR", "GRC", "IDN", "IND", "JPN",
            "MEX", "NGA", "NLD", "RUS", "TUR", "USA"]
TRUST_ITEMS = ["Q57", "Q59", "Q61", "Q62", "Q63", "Q64", "Q69", "Q70",
               "Q71", "Q58", "Q60", "Q73"]
INVERT_1_4 = {"Q59", "Q61", "Q62", "Q63", "Q64", "Q69", "Q70", "Q71", "Q58", "Q60", "Q73"}
BINARY_TRUST = {"Q57"}
BANK_PRECEDENCE = {"usamex_canonical": 0, "ksenias_base8": 1, "co2_8": 2}
N_PERM = 1000
SEED = 20260820


def recode(raw, item):
    s = float(raw)
    if item in INVERT_1_4:
        return 5.0 - s
    if item in BINARY_TRUST:
        return 1.0 if s == 1.0 else 0.0
    return s


def adapter_trust_composites() -> dict[str, float]:
    """Mean of E[recode(V)] over the 12 trust items (frozen G0, matches script 13).

    Binary Q57 is P(option 1). Likert inversions are linear, so they commute.
    Do not recode the raw mean: recode(E[V]) with ==1 zeros Q57 in every country.
    """
    fams = []
    for family, path in [
        ("usamex_canonical", CANON / "model_option_probabilities.csv"),
        ("ksenias_base8", RAW / "ksenias_base8" / "model_option_probabilities.csv"),
        ("co2_8", RAW / "co2_8" / "model_option_probabilities.csv"),
    ]:
        if not path.exists():
            continue
        df = pd.read_csv(path, usecols=[
            "model", "eval_country", "question_id", "option_value", "model_prob"])
        df["bank"] = family
        fams.append(df)
    allf = pd.concat(fams, ignore_index=True)
    allf["model"] = allf["model"].replace({"US": "USA", "Mexico": "MEX"})
    allf["own"] = allf["model"].str.replace("_adapter", "", regex=False)
    matched = allf[((allf["model"] == "base")
                    | ((allf["model"] == allf["own"] + "_adapter")
                       & (allf["eval_country"] == allf["own"])))].copy()
    matched["bank_rank"] = matched["bank"].map(BANK_PRECEDENCE)
    matched = (matched.sort_values("bank_rank")
               .drop_duplicates(["model", "eval_country", "question_id", "option_value"],
                                keep="first"))
    comps = {}
    for model in sorted(matched["model"].unique()):
        mo = matched[matched["model"] == model]
        item_means = []
        for q in TRUST_ITEMS:
            d = mo[mo["question_id"] == q]
            if d.empty:
                continue
            pm = d["model_prob"].values.astype(float)
            raw = d["option_value"].values.astype(float)
            if pm.sum() <= 0:
                continue
            pm = pm / pm.sum()
            rec = np.array([recode(v, q) for v in raw])
            item_means.append(float((rec * pm).sum()))
        if item_means:
            comps[model] = float(np.mean(item_means))
    return comps


def main() -> None:
    import json
    z = json.loads((REPO / "synthetic_generation" / "outputs" / "gps_sign_relabel_all"
                    / "gps_z_vectors.json").read_text())
    z_trust = {c: z[c]["trust"] for c in ADAPTERS}
    comps = adapter_trust_composites()

    nn = pd.read_csv(OUT / "cross_nearest_neighbor.csv").set_index("model")
    rank_of = {m: nn.loc[m, "own_rank_of_42"] for m in nn.index}
    dev = pd.read_csv(OUT / "unified_development.csv")
    dev_trust = {r["model"]: r["rho_gdp"]
                 for _, r in dev[(dev["gps_dimension"] == "trust")
                                 & (dev["model"].str.endswith("_adapter"))].iterrows()}

    def spearman(a, b):
        ra = pd.Series(a).rank().values
        rb = pd.Series(b).rank().values
        return float(np.corrcoef(ra, rb)[0, 1])

    def assignment_stats(assign: dict[str, str]) -> dict:
        comp_vals = [comps[assign[c]] for c in ADAPTERS if assign[c] in comps]
        zs = [z_trust[c] for c in ADAPTERS if assign[c] in comps]
        rho = spearman(comp_vals, zs) if len(comp_vals) == 16 else np.nan
        ranks = [rank_of[assign[c]] for c in ADAPTERS if assign[c] in rank_of]
        devs = [dev_trust.get(assign[c], np.nan) for c in ADAPTERS]
        return {"trust_bridge": rho,
                "median_own_rank": float(np.median(ranks)) if ranks else np.nan,
                "dev_trust": float(np.mean(devs)) if devs else np.nan}

    real = assignment_stats({c: f"{c}_adapter" for c in ADAPTERS})
    bridge13 = pd.read_csv(OUT / "unified_construct_bridge.csv")
    rho13 = float(bridge13.loc[
        (bridge13["model"] == "adapter") & (bridge13["gps_dimension"] == "trust"),
        "rho"].iloc[0])
    if abs(real["trust_bridge"] - rho13) > 5e-3:
        raise SystemExit(
            f"G0 self-check FAIL: placebo real {real['trust_bridge']:.4f} "
            f"!= script-13 adapter trust {rho13:.4f}")
    print("G0 self-check: placebo real == script-13 adapter trust",
          round(real["trust_bridge"], 4), round(rho13, 4))
    print("REAL-ANCHOR:", {k: round(v, 4) if pd.notna(v) else None
                           for k, v in real.items()})

    rng = np.random.default_rng(SEED)
    keys = list(ADAPTERS)
    null_b, null_r, null_d = [], [], []
    for _ in range(N_PERM):
        perm = rng.permutation(keys)
        assign = {keys[i]: f"{perm[i]}_adapter" for i in range(len(keys))}
        s = assignment_stats(assign)
        null_b.append(s["trust_bridge"]); null_r.append(s["median_own_rank"])
        null_d.append(s["dev_trust"])
    null_b, null_r, null_d = map(np.array, (null_b, null_r, null_d))

    def pval(real_v, null, lower_better=False):
        if pd.isna(real_v):
            return float("nan")
        return float((null <= real_v if lower_better else null >= real_v).mean())

    print(f"\nN={N_PERM} permutations (seed {SEED})")
    results = []
    for name, rv, null, lb in [
        ("trust_bridge", real["trust_bridge"], null_b, False),
        ("dev_trust", real["dev_trust"], null_d, False),
        ("median_own_rank", real["median_own_rank"], null_r, True),
    ]:
        p = pval(rv, null, lb)
        q = np.percentile(null, 5 if lb else 95)
        verdict = "SUPPORTED" if p <= 0.05 else "not supported"
        print(f"  {name:18s} real={rv:.3f} null_med={np.median(null):.3f} "
              f"q95={q:.3f} p={p:.4f} {verdict}")
        results.append((name, rv, np.median(null), q, p, verdict))

    pd.DataFrame({"trust_bridge": null_b, "dev_trust": null_d,
                  "median_own_rank": null_r}).to_csv(
        OUT / "placebo_null_distributions.csv", index=False)

    lines = [
        "# PLACEBO REPORT — restricted permutation test (G0: E[recode], 2026-08-23)",
        f"Null: country->anchor assignment without replacement from the 16 observed anchors (N={N_PERM}, seed={SEED}).",
        "Construction: E[recode(V)] / P(option 1) on Q57; must match script 13 adapter trust.",
        f"Real-anchor trust bridge rho: {real['trust_bridge']:.3f}",
        f"Real-anchor dev-trust rho: {real['dev_trust']:.3f}",
        f"Real-anchor median own-rank (42-country): {real['median_own_rank']:.1f}",
        "",
        "p-values (one-sided; lower_better for rank):",
    ]
    for name, rv, nm, q, p, v in results:
        lines.append(f"- {name}: real={rv:.3f}, null median={nm:.3f}, q95={q:.3f}, "
                     f"p={p:.4f} -> {v.upper()}")
    (REPO / "analysis" / "phase2" / "PLACEBO_REPORT.md").write_text("\n".join(lines))
    print("\nreport written.")


if __name__ == "__main__":
    main()
