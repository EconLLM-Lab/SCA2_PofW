"""Cell-mean design for trust (demographic_gradient_protocol.md, section 6).

Units: sex x age-band cells (2 x 6 = 12) per country.
For each country with both WVS and GPS individual samples:
  - WVS cell means of trust facets + survivor composite (protocol recipe)
  - GPS cell means of the trust preference composite
  - within-country correlation across cells (demographic structure alignment)

Pooling: country-demeaned cell means -> pooled correlation (kills the
cross-country development confound; this is the ecological-fallacy control).

Bootstrap: country-cluster resampling for CIs and for P(composite > Q57).

Unweighted primary (SCA2 convention); GPS-weighted cell means as sensitivity.

No new inference. Local data only.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]

spec1 = importlib.util.spec_from_file_location(
    "bwg", REPO / "sca2_validity" / "prep" / "build_wvs_gradients.py"
)
bwg = importlib.util.module_from_spec(spec1)
assert spec1.loader is not None
spec1.loader.exec_module(bwg)

WVS = REPO / "data" / "WVS" / "WVS_wave7.dta"
GPS = REPO / "data" / "GPS" / "GPS_dataset_individual_level" / "individual_new.dta"

AGE_BANDS = [(18, 24), (25, 34), (35, 44), (45, 54), (55, 64), (65, 120)]
BAND_NAMES = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
MIN_CELL_N = 20
MIN_CELLS = 6
RNG = np.random.default_rng(42)
N_BOOT = 2000

TRUST_FACETS = [
    "m_trust_general",
    "m_trust_in_group",
    "m_trust_out_group",
    "m_trust_institution",
]


def age_band(age: pd.Series) -> pd.Series:
    out = pd.Series(index=age.index, dtype=float)
    for i, (lo, hi) in enumerate(AGE_BANDS):
        out[(age >= lo) & (age <= hi)] = i
    return out


def build_wvs_cells(facets: pd.DataFrame) -> pd.DataFrame:
    """sex x age-band cell means of trust facets (unweighted)."""
    d = facets[facets["age100"].notna()].copy()
    d["age_years"] = d["age100"] * 100.0
    d["band"] = age_band(d["age_years"])
    d = d[(d["band"].notna()) & (d["age_years"] >= 18)]
    d["sex"] = d["female"].astype(int)
    cols = TRUST_FACETS + ["m_trust_survivor_composite"]
    cell = d.groupby(["iso", "sex", "band"])[cols].mean().reset_index()
    return cell


def build_gps_cells(gps: pd.DataFrame, weighted: bool = False) -> pd.DataFrame:
    """sex x age-band cell means of GPS trust (optionally wgt-weighted)."""
    d = gps[["iso", "gender", "age", "trust", "wgt"]].dropna(subset=["trust", "age"]).copy()
    d["band"] = age_band(d["age"])
    d = d[(d["band"].notna()) & (d["age"] >= 18)]
    d["sex"] = d["gender"].astype(int)
    if weighted:
        g = d.groupby(["iso", "sex", "band"])
        cell = (g.apply(lambda x: np.average(x["trust"], weights=x["wgt"]))
                .rename("gps_trust").reset_index())
    else:
        cell = d.groupby(["iso", "sex", "band"])["trust"].mean().rename("gps_trust").reset_index()
    return cell


def within_country_corr(w: pd.DataFrame, g: pd.DataFrame, facet: str) -> dict:
    """Correlation across cells within each country; return per-country r."""
    m = w.merge(g, on=["iso", "sex", "band"])
    m = m[m["gps_trust"].notna() & m[facet].notna()]
    out: dict[str, float] = {}
    for iso, grp in m.groupby("iso"):
        if grp[facet].nunique() < 3 or grp["gps_trust"].nunique() < 3:
            continue
        r = np.corrcoef(grp[facet], grp["gps_trust"])[0, 1]
        if np.isfinite(r):
            out[iso] = float(r)
    return out


def pooled_corr(w: pd.DataFrame, g: pd.DataFrame, facet: str) -> float:
    """Country-demeaned pooled correlation across cells."""
    m = w.merge(g, on=["iso", "sex", "band"])
    m = m[m["gps_trust"].notna() & m[facet].notna()].copy()
    for col in (facet, "gps_trust"):
        m[col] = m[col] - m.groupby("iso")[col].transform("mean")
    if len(m) < 10 or m[facet].std() == 0 or m["gps_trust"].std() == 0:
        return float("nan")
    return float(np.corrcoef(m[facet], m["gps_trust"])[0, 1])


def main() -> None:
    print("loading data ...")
    wvs = pd.read_stata(WVS, convert_categoricals=False)
    facets = bwg.add_demographics(
        bwg.build_respondent_facets(wvs, bwg.load_protocol(bwg.PROTOCOL)), wvs
    )
    facets["m_trust_survivor_composite"] = facets[
        ["m_trust_in_group", "m_trust_out_group", "m_trust_institution"]
    ].mean(axis=1)
    gps = pd.read_stata(GPS, convert_categoricals=False)
    gps["iso"] = gps["isocode"].astype(str).str.strip()

    w_cells = build_wvs_cells(facets)
    # require min cell n on WVS side
    n_counts = facets[facets["age100"].notna()].copy()
    n_counts["age_years"] = n_counts["age100"] * 100.0
    n_counts["band"] = age_band(n_counts["age_years"])
    n_counts = n_counts[(n_counts["band"].notna()) & (n_counts["age_years"] >= 18)]
    n_counts["sex"] = n_counts["female"].astype(int)
    cell_n = n_counts.groupby(["iso", "sex", "band"]).size().rename("n").reset_index()
    w_cells = w_cells.merge(cell_n, on=["iso", "sex", "band"])
    w_cells = w_cells[w_cells["n"] >= MIN_CELL_N]

    g_unw = build_gps_cells(gps, weighted=False)
    g_w = build_gps_cells(gps, weighted=True)

    measures = TRUST_FACETS + ["m_trust_survivor_composite"]

    print(f"\n=== Cell-mean design: trust (WVS cell means vs GPS trust cell means) ===")
    print(f"cells: sex x {len(AGE_BANDS)} age bands; min cell n = {MIN_CELL_N}; "
          f"min cells/country = {MIN_CELLS}\n")

    print(f"{'measure':28s} {'n_ctry':>6} {'median r':>9} {'% r>0':>7} "
          f"{'pooled r':>9} {'95% CI':>18} {'P(>Q57)':>8}")

    w_general = None
    for m in measures:
        within = within_country_corr(w_cells, g_unw, m)
        n_ctry = len(within)
        if n_ctry < MIN_CELLS:
            print(f"{m:28s} {n_ctry:6d}  (insufficient countries)")
            continue
        rs = np.array(list(within.values()))
        med = float(np.median(rs))
        frac_pos = float((rs > 0).mean())
        pooled = pooled_corr(w_cells, g_unw, m)
        # bootstrap CI on pooled r (country-cluster)
        countries = w_cells["iso"].unique()
        reps = []
        idx = np.arange(len(countries))
        for _ in range(N_BOOT):
            b = RNG.choice(idx, size=len(countries), replace=True)
            cset = set(countries[b])
            wb = w_cells[w_cells["iso"].isin(cset)]
            gb = g_unw[g_unw["iso"].isin(cset)]
            reps.append(pooled_corr(wb, gb, m))
        reps = np.array([x for x in reps if np.isfinite(x)])
        lo, hi = np.percentile(reps, 2.5), np.percentile(reps, 97.5)
        if m == "m_trust_general":
            w_general = reps
        if w_general is not None and m == "m_trust_survivor_composite":
            p = float((reps > w_general).mean())
        else:
            p = float("nan")
        print(f"{m:28s} {n_ctry:6d} {med:+9.3f} {frac_pos:7.2f} {pooled:+9.3f} "
              f"[{lo:+8.3f}, {hi:+8.3f}] {p:8.3f}")

    # weighted sensitivity for the composite
    print("\n--- sensitivity: GPS cell means weighted by wgt ---")
    for m in ["m_trust_general", "m_trust_survivor_composite"]:
        pooled = pooled_corr(w_cells, g_w, m)
        countries = w_cells["iso"].unique()
        reps = []
        idx = np.arange(len(countries))
        for _ in range(N_BOOT):
            b = RNG.choice(idx, size=len(countries), replace=True)
            cset = set(countries[b])
            reps.append(pooled_corr(w_cells[w_cells["iso"].isin(cset)],
                                    g_w[g_w["iso"].isin(cset)], m))
        reps = np.array([x for x in reps if np.isfinite(x)])
        print(f"{m:28s} pooled r = {pooled:+.3f}  95% CI "
              f"[{np.percentile(reps,2.5):+.3f}, {np.percentile(reps,97.5):+.3f}]")


if __name__ == "__main__":
    main()
