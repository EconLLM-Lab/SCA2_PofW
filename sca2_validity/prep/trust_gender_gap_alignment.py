"""Cross-country alignment of the WVS trust gender gradient with the GPS trust
gender gradient (Stream B extension).

For every country with both WVS wave-7 respondents and GPS individual data,
estimate the female coefficient on (a) each WVS trust facet and (b) GPS trust.
Correlate these per-country gender gaps across countries: if the two
instruments share the trust construct's demographic structure, countries
where women are more trusting in GPS should also be countries where women are
more trusting in WVS (same sign, positively correlated gaps).

Economic-model relevance: instruments that disagree on demographic structure
will disagree on any trust coefficient interacted with gender/composition.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
WVS = REPO / "data" / "WVS" / "WVS_wave7.dta"
GPS = REPO / "data" / "GPS" / "GPS_dataset_individual_level" / "individual_new.dta"

# load Stream B helper
spec = importlib.util.spec_from_file_location(
    "bwg", REPO / "sca2_validity" / "prep" / "build_wvs_gradients.py"
)
bwg = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(bwg)

TRUST_FACETS = [
    "m_trust_general",
    "m_trust_in_group",
    "m_trust_out_group",
    "m_trust_institution",
]


def per_country_wvs_female(df: pd.DataFrame, facet: str, min_n: int = 200) -> dict[str, float]:
    out: dict[str, float] = {}
    for iso, g in df.groupby("iso"):
        d = g[["female", "age100", "age2", "educ", facet]].dropna()
        if len(d) < min_n:
            continue
        X = np.column_stack(
            [np.ones(len(d)), d[["female", "age100", "age2", "educ"]].values]
        )
        b, *_ = np.linalg.lstsq(X, d[facet].values, rcond=None)
        out[iso] = float(b[1])
    return out


def per_country_gps_female(df: pd.DataFrame, dim: str, min_n: int = 150) -> dict[str, float]:
    out: dict[str, float] = {}
    for iso, g in df.groupby("iso"):
        d = g[["gender", "age", "subj_math_skills", dim]].dropna().copy()
        if len(d) < min_n:
            continue
        d["age100"] = d["age"] / 100.0
        d["age2"] = d["age100"] ** 2
        X = np.column_stack(
            [np.ones(len(d)), d[["gender", "age100", "age2", "subj_math_skills"]].values]
        )
        b, *_ = np.linalg.lstsq(X, d[dim].values, rcond=None)
        out[iso] = float(b[1])
    return out


def main() -> None:
    print("loading data ...")
    wvs = pd.read_stata(WVS, convert_categoricals=False)
    facets = bwg.add_demographics(
        bwg.build_respondent_facets(wvs, bwg.load_protocol(bwg.PROTOCOL)), wvs
    )
    gps = pd.read_stata(GPS, convert_categoricals=False)
    gps["iso"] = gps["isocode"].astype(str).str.strip()

    facets["m_trust_survivor_composite"] = facets[
        ["m_trust_in_group", "m_trust_out_group", "m_trust_institution"]
    ].mean(axis=1)

    g_gps = per_country_gps_female(gps, "trust")
    print(f"GPS trust gender gap available for {len(g_gps)} countries")

    print(f"\n{'WVS facet':28s} {'n_ctry':>6} {'corr(gaps)':>11} {'same-sign':>10} "
          f"{'USA(wvs,gps)':>16} {'MEX(wvs,gps)':>16}")
    for f in TRUST_FACETS + ["m_trust_survivor_composite"]:
        w = per_country_wvs_female(facets, f)
        common = sorted(set(w) & set(g_gps))
        if len(common) < 5:
            continue
        wv = np.array([w[c] for c in common])
        gv = np.array([g_gps[c] for c in common])
        r = float(np.corrcoef(wv, gv)[0, 1])
        same = int(sum(1 for c in common if (w[c] > 0) == (g_gps[c] > 0)))
        usa = (round(w.get("USA", float("nan")), 3), round(g_gps.get("USA", float("nan")), 3))
        mex = (round(w.get("MEX", float("nan")), 3), round(g_gps.get("MEX", float("nan")), 3))
        print(f"{f:28s} {len(common):6d} {r:11.3f} {same:3d}/{len(common):<4d} "
              f"{str(usa):>16} {str(mex):>16}")


if __name__ == "__main__":
    main()
