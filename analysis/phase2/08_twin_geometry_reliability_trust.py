#!/usr/bin/env python3
"""08 — sign-twin geometry, twin-adapter reliability, trust-class Spearman.

Local-only. Does not fetch GDP / Inglehart–Welzel (those need new data).

1. Sign-twin geometry on the 76-country GPS bank:
   - cluster countries by sign(z) on 6 GPS dims
   - within- vs between-class Euclidean distance on GPS *magnitudes*
   - within- vs between-class CF_ST on the 42-country human WVS matrix
     (cd_country_country.csv), restricted to GPS-sign twins that also appear
     in the WVS-42 set
   - permutation null (shuffle class labels, 2000 reps) for both

2. Twin-adapter reliability / leakage:
   - CF_ST between IND/GRC and IDN/EGY adapters (cd_adapter_adapter.csv)
   - item-level |model_mean| and TVD differences on matched WVS rows
   - compare those distances to all other adapter–adapter pairs and to
     each twin vs base

3. Trust-class construct bridge:
   - human (42) and adapter (16) Spearman of class composites vs GPS trust z
   - family / ingroup / outgroup / institutions, plus Q57 alone and Q69/Q70

Run: unset PYTHONPATH && .venv/bin/python analysis/phase2/08_twin_geometry_reliability_trust.py
"""
from __future__ import annotations

import json
import pathlib
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "analysis" / "phase2" / "outputs"
GPS_DTA = REPO / "data" / "GPS" / "GPS_dataset_country_level" / "country_gps.dta"
WVS_DIR = REPO / "data" / "wvs_eval_full"

DIMS = ["patience", "risktaking", "posrecip", "negrecip", "altruism", "trust"]
RNG = np.random.default_rng(42)

TRUST_CLASS = {
    "Q58": "family",
    "Q59": "ingroup", "Q60": "ingroup",
    "Q57": "outgroup", "Q61": "outgroup", "Q62": "outgroup", "Q63": "outgroup",
    "Q64": "institutions", "Q69": "institutions", "Q70": "institutions",
    "Q71": "institutions", "Q73": "institutions",
}
INVERT_1_4 = {
    "Q59", "Q61", "Q62", "Q63", "Q64", "Q69", "Q70", "Q71", "Q58", "Q60", "Q73"
}
BINARY_TRUST = {"Q57"}
BANK_PRECEDENCE = {"usamex_canonical": 0, "ksenias_base8": 1, "co2_8": 2}


def recode_trust(raw: pd.Series, item: str) -> pd.Series:
    s = raw.astype(float)
    if item in INVERT_1_4:
        return 5.0 - s
    if item in BINARY_TRUST:
        return (s == 1.0).astype(float)
    return s


def pairwise_mean(dist: np.ndarray, labels: np.ndarray, within: bool) -> float:
    n = len(labels)
    acc, cnt = 0.0, 0
    for i in range(n):
        for j in range(i + 1, n):
            same = labels[i] == labels[j]
            if same == within:
                acc += dist[i, j]
                cnt += 1
    return acc / cnt if cnt else np.nan


def perm_ratio(dist: np.ndarray, labels: np.ndarray, obs_ratio: float, nrep: int = 2000):
    """P(perm within/between <= observed). Smaller ratio = tighter clusters."""
    ge = 0
    for _ in range(nrep):
        lab = RNG.permutation(labels)
        w = pairwise_mean(dist, lab, True)
        b = pairwise_mean(dist, lab, False)
        r = w / b if b and np.isfinite(w) else np.nan
        if np.isfinite(r) and r <= obs_ratio:
            ge += 1
    return ge / nrep


def sign_twin_geometry() -> dict:
    gps = pd.read_stata(GPS_DTA).set_index("isocode")
    sub = gps[DIMS].dropna()
    signs = np.sign(sub).astype(int)
    key = signs.astype(str).agg("".join, axis=1)
    clusters = key.groupby(key).apply(lambda s: sorted(s.index.tolist())).to_dict()
    multi = {k: v for k, v in clusters.items() if len(v) > 1}

    # GPS magnitude distances
    X = sub.values.astype(float)
    countries = list(sub.index)
    # z-score columns so dims are comparable
    Xz = (X - X.mean(0)) / X.std(0, ddof=0)
    d_gps = np.sqrt(((Xz[:, None, :] - Xz[None, :, :]) ** 2).sum(-1))
    labels = key.loc[countries].values
    w = pairwise_mean(d_gps, labels, True)
    b = pairwise_mean(d_gps, labels, False)
    ratio = w / b
    p = perm_ratio(d_gps, labels, ratio)

    # per-cluster GPS magnitude spread vs global
    cluster_rows = []
    for k, members in sorted(multi.items(), key=lambda kv: -len(kv[1])):
        idx = [countries.index(c) for c in members]
        intra = []
        for i, a in enumerate(idx):
            for bix in idx[i + 1 :]:
                intra.append(d_gps[a, bix])
        # magnitudes: max |z| gap per dim
        mag = sub.loc[members]
        cluster_rows.append({
            "signkey": k,
            "n": len(members),
            "members": ",".join(members),
            "mean_intra_gps_euclid": float(np.mean(intra)),
            "max_abs_z_gap": float((mag.max() - mag.min()).abs().max()),
            "max_gap_dim": (mag.max() - mag.min()).abs().idxmax(),
        })

    # Human CF_ST among WVS-42 countries that have a GPS sign class
    cd = pd.read_csv(OUT / "cd_country_country.csv", index_col=0)
    wvs_cc = [c for c in cd.index if c in key.index]
    cd_m = cd.loc[wvs_cc, wvs_cc].values.astype(float)
    np.fill_diagonal(cd_m, 0.0)
    lab_w = key.loc[wvs_cc].values
    w_cf = pairwise_mean(cd_m, lab_w, True)
    b_cf = pairwise_mean(cd_m, lab_w, False)
    ratio_cf = w_cf / b_cf if b_cf else np.nan
    p_cf = perm_ratio(cd_m, lab_w, ratio_cf)

    # twins that both sit in WVS-42
    wvs_twins = []
    for k, members in multi.items():
        inter = [c for c in members if c in wvs_cc]
        if len(inter) >= 2:
            # mean pairwise CF_ST among the overlapping twins
            pairs = []
            for i, a in enumerate(inter):
                for b_ in inter[i + 1 :]:
                    pairs.append(float(cd.loc[a, b_]))
            wvs_twins.append({
                "signkey": k,
                "wvs_members": ",".join(inter),
                "n_wvs": len(inter),
                "n_full_class": len(members),
                "mean_cfst": float(np.mean(pairs)),
            })

    out = {
        "n_gps_countries": int(len(sub)),
        "n_distinct_sign_profiles": int(key.nunique()),
        "n_multi_country_classes": int(len(multi)),
        "largest_class_n": int(max(len(v) for v in clusters.values())),
        "gps_within_euclid": float(w),
        "gps_between_euclid": float(b),
        "gps_within_between_ratio": float(ratio),
        "gps_perm_p_tighter": float(p),
        "wvs42_n": int(len(wvs_cc)),
        "wvs42_n_classes_present": int(pd.Series(lab_w).nunique()),
        "cfst_within": float(w_cf),
        "cfst_between": float(b_cf),
        "cfst_within_between_ratio": float(ratio_cf),
        "cfst_perm_p_tighter": float(p_cf),
    }
    pd.DataFrame(cluster_rows).to_csv(OUT / "twin_gps_clusters.csv", index=False)
    pd.DataFrame(wvs_twins).sort_values("mean_cfst").to_csv(
        OUT / "twin_wvs_cfst.csv", index=False
    )
    print("=== 1. sign-twin geometry ===")
    for k, v in out.items():
        print(f"  {k}: {v}")
    print("  multi-class GPS magnitude gaps (top 8 by n):")
    for r in sorted(cluster_rows, key=lambda x: -x["n"])[:8]:
        print(f"    n={r['n']:2d}  intra={r['mean_intra_gps_euclid']:.3f}  "
              f"max|z|gap={r['max_abs_z_gap']:.3f} on {r['max_gap_dim']:10s}  {r['members']}")
    print("  WVS-42 overlapping twins (lowest CF_ST first):")
    for r in sorted(wvs_twins, key=lambda x: x["mean_cfst"])[:10]:
        print(f"    cfst={r['mean_cfst']:.4f}  {r['wvs_members']}  "
              f"(class n={r['n_full_class']})")
    return out


def twin_adapter_reliability() -> dict:
    aa = pd.read_csv(OUT / "cd_adapter_adapter.csv", index_col=0)
    twins = [("IND_adapter", "GRC_adapter"), ("IDN_adapter", "EGY_adapter")]
    # also MEX/RUS as the third trained twin
    twins3 = twins + [("MEX_adapter", "RUS_adapter")]

    adapters = [c for c in aa.index if c.endswith("_adapter")]
    offdiag = []
    for i, a in enumerate(adapters):
        for b in adapters[i + 1 :]:
            offdiag.append(float(aa.loc[a, b]))
    offdiag = np.array(offdiag)

    rows = []
    for a, b in twins3:
        d = float(aa.loc[a, b])
        d_a_base = float(aa.loc[a, "base"])
        d_b_base = float(aa.loc[b, "base"])
        rank = int((offdiag < d).sum() + 1)
        rows.append({
            "pair": f"{a.replace('_adapter','')}≡{b.replace('_adapter','')}",
            "cfst_between_adapters": d,
            "cfst_a_vs_base": d_a_base,
            "cfst_b_vs_base": d_b_base,
            "rank_among_adapter_pairs": rank,
            "n_adapter_pairs": int(len(offdiag)),
            "pctile": float((offdiag <= d).mean()),
        })

    # item-level matched model_mean / TVD diffs
    wvs = pd.read_parquet(OUT / "wvs_question_metrics_long.parquet")
    m = wvs[(wvs["relationship"] == "matched") & (wvs["is_adapter"])].copy()
    m["bank_rank"] = m["bank"].map(BANK_PRECEDENCE)
    m = (m.sort_values("bank_rank")
         .drop_duplicates(subset=["model", "eval_country", "question_id"], keep="first"))

    item_rows = []
    for a, b in twins3:
        ca, cb = a.replace("_adapter", ""), b.replace("_adapter", "")
        da = m[(m["model"] == a) & (m["eval_country"] == ca)].set_index("question_id")
        db = m[(m["model"] == b) & (m["eval_country"] == cb)].set_index("question_id")
        common = da.index.intersection(db.index)
        dmean = (da.loc[common, "model_mean"] - db.loc[common, "model_mean"]).abs()
        dtvd = (da.loc[common, "tv_distance"] - db.loc[common, "tv_distance"]).abs()
        item_rows.append({
            "pair": f"{ca}≡{cb}",
            "n_items": int(len(common)),
            "mean_abs_model_mean_diff": float(dmean.mean()),
            "median_abs_model_mean_diff": float(dmean.median()),
            "max_abs_model_mean_diff": float(dmean.max()),
            "max_item": str(dmean.idxmax()) if len(dmean) else "",
            "mean_abs_tvd_diff": float(dtvd.mean()),
        })

    print("\n=== 2. twin-adapter reliability ===")
    print(f"  adapter-pair CF_ST: min={offdiag.min():.6f}  median={np.median(offdiag):.4f}  "
          f"max={offdiag.max():.4f}  n={len(offdiag)}")
    for r in rows:
        print(f"  {r['pair']}: cfst={r['cfst_between_adapters']:.6g}  "
              f"rank {r['rank_among_adapter_pairs']}/{r['n_adapter_pairs']}  "
              f"vs base {r['cfst_a_vs_base']:.3f} / {r['cfst_b_vs_base']:.3f}")
    for r in item_rows:
        print(f"  {r['pair']} items: |Δmean|={r['mean_abs_model_mean_diff']:.4f} "
              f"(med {r['median_abs_model_mean_diff']:.4f}, max {r['max_abs_model_mean_diff']:.3f} "
              f"on {r['max_item']}); |ΔTVD|={r['mean_abs_tvd_diff']:.4f}")

    pd.DataFrame(rows).to_csv(OUT / "twin_adapter_cfst.csv", index=False)
    pd.DataFrame(item_rows).to_csv(OUT / "twin_adapter_itemdiff.csv", index=False)
    return {"pairs": rows, "items": item_rows,
            "offdiag_min": float(offdiag.min()),
            "offdiag_median": float(np.median(offdiag))}


def human_trust_class_means() -> pd.DataFrame:
    gps = pd.read_stata(GPS_DTA).set_index("isocode")
    items = sorted(TRUST_CLASS)
    rows = []
    for f in sorted(WVS_DIR.glob("*_WVS_wave7.parquet")):
        cc = f.name.split("_")[0]
        if cc not in gps.index:
            continue
        cols = ["W_WEIGHT"] + [q for q in items]
        df = pd.read_parquet(f, columns=cols)
        w = df["W_WEIGHT"].fillna(0)
        for it in items:
            v = recode_trust(df[it], it)
            msk = (v >= 0) & (w > 0)
            if msk.sum() < 50:
                continue
            rows.append({
                "country": cc,
                "item": it,
                "trust_class": TRUST_CLASS[it],
                "mean": float((v[msk] * w[msk]).sum() / w[msk].sum()),
            })
    return pd.DataFrame(rows)


def adapter_trust_item_means() -> pd.DataFrame:
    wvs = pd.read_parquet(OUT / "wvs_question_metrics_long.parquet")
    m = wvs[(wvs["relationship"] == "matched") & (wvs["is_adapter"])].copy()
    m["bank_rank"] = m["bank"].map(BANK_PRECEDENCE)
    m = (m.sort_values("bank_rank")
         .drop_duplicates(subset=["model", "eval_country", "question_id"], keep="first"))
    m = m[m["question_id"].isin(TRUST_CLASS)]
    rows = []
    for _, r in m.iterrows():
        raw = r["model_mean"]
        it = r["question_id"]
        if it in INVERT_1_4:
            s = 5.0 - raw
        elif it in BINARY_TRUST:
            s = 1.0 if raw < 1.5 else 0.0
        else:
            s = raw
        rows.append({
            "country": r["eval_country"],
            "item": it,
            "trust_class": TRUST_CLASS[it],
            "mean": float(s),
        })
    return pd.DataFrame(rows)


def rho_vs_trust(means: pd.DataFrame, gps_z: pd.Series, min_n: int) -> list[dict]:
    out = []
    # class composites
    for cls, g in means.groupby("trust_class"):
        comp = g.groupby("country")["mean"].mean()
        joined = pd.concat([comp, gps_z], axis=1, join="inner").dropna()
        joined.columns = ["m", "z"]
        if len(joined) >= min_n and joined["m"].nunique() > 1:
            rho = float(spearmanr(joined["m"], joined["z"]).statistic)
        else:
            rho = float("nan")
        out.append({"layer_unit": cls, "rho": rho, "n": int(len(joined))})
    # spotlight items
    for it in ["Q57", "Q58", "Q69", "Q70"]:
        g = means[means["item"] == it]
        if g.empty:
            continue
        joined = g.set_index("country")[["mean"]].join(gps_z, how="inner").dropna()
        joined.columns = ["m", "z"]
        if len(joined) >= min_n and joined["m"].nunique() > 1:
            rho = float(spearmanr(joined["m"], joined["z"]).statistic)
        else:
            rho = float("nan")
        out.append({"layer_unit": it, "rho": rho, "n": int(len(joined))})
    # full composite (all 12)
    comp = means.groupby("country")["mean"].mean()
    joined = pd.concat([comp, gps_z], axis=1, join="inner").dropna()
    joined.columns = ["m", "z"]
    rho = float(spearmanr(joined["m"], joined["z"]).statistic)
    out.append({"layer_unit": "all12", "rho": rho, "n": int(len(joined))})
    return out


def trust_class_bridge() -> pd.DataFrame:
    gps = pd.read_stata(GPS_DTA).set_index("isocode")["trust"]
    h = human_trust_class_means()
    a = adapter_trust_item_means()
    hrows = rho_vs_trust(h, gps, min_n=10)
    arows = rho_vs_trust(a, gps, min_n=8)
    hdf = pd.DataFrame(hrows).rename(columns={"rho": "human_rho_42", "n": "n_human"})
    adf = pd.DataFrame(arows).rename(columns={"rho": "adapter_rho_16", "n": "n_adapter"})
    tab = hdf.merge(adf, on="layer_unit", how="outer")
    # stable order
    order = ["all12", "family", "ingroup", "outgroup", "institutions",
             "Q57", "Q58", "Q69", "Q70"]
    tab["ord"] = tab["layer_unit"].map({k: i for i, k in enumerate(order)})
    tab = tab.sort_values("ord").drop(columns="ord")
    tab.to_csv(OUT / "trust_class_bridge.csv", index=False)
    print("\n=== 5. trust-class bridge (Spearman vs GPS trust z) ===")
    print(tab.round(3).to_string(index=False))
    return tab


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    g = sign_twin_geometry()
    r = twin_adapter_reliability()
    t = trust_class_bridge()
    summary = {
        "geometry": g,
        "reliability": {
            "offdiag_min": r["offdiag_min"],
            "offdiag_median": r["offdiag_median"],
            "pairs": r["pairs"],
        },
        "trust_bridge": t.to_dict(orient="records"),
    }
    (OUT / "eval_08_summary.json").write_text(json.dumps(summary, indent=2))
    print("\nwrote twin_gps_clusters.csv, twin_wvs_cfst.csv, twin_adapter_cfst.csv,")
    print("      twin_adapter_itemdiff.csv, trust_class_bridge.csv, eval_08_summary.json")


if __name__ == "__main__":
    main()
