"""Country-cluster bootstrap for the trust gender-gap alignment contrasts.

Puts honest uncertainty on the Stream B extension result:
  - corr(gender gaps) for Q57 vs survivor composite vs GPS trust
  - probability that the composite correlation exceeds the Q57 correlation

This is ANALYSIS (bootstrap over countries, no new inference).
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

spec2 = importlib.util.spec_from_file_location(
    "tg", REPO / "sca2_validity" / "prep" / "trust_gender_gap_alignment.py"
)
tg = importlib.util.module_from_spec(spec2)
assert spec2.loader is not None
spec2.loader.exec_module(tg)

RNG = np.random.default_rng(42)
N_BOOT = 2000

MEASURES = ["m_trust_general", "m_trust_in_group", "m_trust_out_group",
            "m_trust_institution", "m_trust_survivor_composite"]


def main() -> None:
    wvs = pd.read_stata(tg.WVS, convert_categoricals=False)
    facets = bwg.add_demographics(
        bwg.build_respondent_facets(wvs, bwg.load_protocol(bwg.PROTOCOL)), wvs
    )
    gps = pd.read_stata(tg.GPS, convert_categoricals=False)
    gps["iso"] = gps["isocode"].astype(str).str.strip()
    facets["m_trust_survivor_composite"] = facets[
        ["m_trust_in_group", "m_trust_out_group", "m_trust_institution"]
    ].mean(axis=1)

    g_gps = tg.per_country_gps_female(gps, "trust")
    w_vals = {m: tg.per_country_wvs_female(facets, m) for m in MEASURES}
    common = {m: sorted(set(w_vals[m]) & set(g_gps)) for m in MEASURES}
    wv = {m: np.array([w_vals[m][c] for c in common[m]]) for m in MEASURES}
    gv = {m: np.array([g_gps[c] for c in common[m]]) for m in MEASURES}

    print("Country-cluster bootstrap of corr(WVS gender gap, GPS gender gap):")
    print(f"{'measure':28s} {'n':>4} {'r':>7} {'95% CI':>18}")
    for m in MEASURES:
        n = len(common[m])
        r_orig = float(np.corrcoef(wv[m], gv[m])[0, 1])
        reps = []
        idx = np.arange(n)
        for _ in range(N_BOOT):
            b = RNG.choice(idx, size=n, replace=True)
            reps.append(np.corrcoef(wv[m][b], gv[m][b])[0, 1])
        reps = np.array(reps)
        lo, hi = np.percentile(reps, 2.5), np.percentile(reps, 97.5)
        print(f"{m:28s} {n:4d} {r_orig:+7.3f} [{lo:+8.3f}, {hi:+8.3f}]")

    # contrast: P(r_composite > r_general)
    i1 = MEASURES.index("m_trust_general")
    i2 = MEASURES.index("m_trust_survivor_composite")
    w1, g1 = wv[MEASURES[i1]], gv[MEASURES[i1]]
    w2, g2 = wv[MEASURES[i2]], gv[MEASURES[i2]]
    n1, n2 = len(w1), len(w2)
    idx1, idx2 = np.arange(n1), np.arange(n2)
    cnt = 0
    diffs = []
    for _ in range(N_BOOT):
        b1 = RNG.choice(idx1, size=n1, replace=True)
        b2 = RNG.choice(idx2, size=n2, replace=True)
        r1 = np.corrcoef(w1[b1], g1[b1])[0, 1]
        r2 = np.corrcoef(w2[b2], g2[b2])[0, 1]
        diffs.append(r2 - r1)
        cnt += int(r2 > r1)
    diffs = np.array(diffs)
    print(f"\nP(r_composite > r_Q57): {cnt / N_BOOT:.3f}")
    print(f"mean(r_composite - r_Q57): {np.mean(diffs):+.3f}  "
          f"95% CI [{np.percentile(diffs, 2.5):+.3f}, {np.percentile(diffs, 97.5):+.3f}]")


if __name__ == "__main__":
    main()
