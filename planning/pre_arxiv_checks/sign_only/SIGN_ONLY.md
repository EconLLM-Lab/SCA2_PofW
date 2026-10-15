# Sign-only trust check

Pre-arXiv check on frozen scores. Not a claim-lock amendment. No model call, no retrain, no manuscript edit.

## Sanity

Adapter–GPS Spearman on the 16×9 rectangle, matching `arm_composite` and `spearman` in `analysis/phase2/22_paper_a_surface.py`: `0.7999999999999999`.

`SURFACE_LOCK.json` records `0.7999999999999999`. Absolute difference from 0.80 is `1.1102230246251565e-16`, inside 0.005. Scores sha256 and GPS json sha256 match the lock file. New statistics below were computed only after that check.

The rectangle is 16 countries × 9 trust items (Q57–Q64, Q73), one finite adapter `raw` row per cell. The composite is the country mean of `raw`.

## Sign rule

`s = 1` if GPS trust `z >= 0`, else `0`. Exact zero, if any, is nonnegative. `z` is the `trust` coordinate in `gps_z_vectors.json`, not the adapter score.

## Counts

| Side | Rule | n | Countries |
|---|---|---:|---|
| Positive | z > 0 | 7 | CHN EGY GBR IDN NLD TUR USA |
| Negative | z < 0 | 9 | ARG BRA DEU GRC IND JPN MEX NGA RUS |
| Exact zero | z == 0 | 0 | (none) |

Positive-sign class used in the contrasts is z ≥ 0 (7 countries: CHN EGY GBR IDN NLD TUR USA). Negative-sign class is z < 0 (9 countries: ARG BRA DEU GRC IND JPN MEX NGA RUS).

Countries with |z| < 0.05: BRA (-0.0026891387533396482). Classification uses exact comparison, not a tolerance.

## Sign versus continuous z

Spearman of the binary sign with continuous GPS z on the same 16 countries: 0.8609160647753271.

This number does not use the adapter. It is a property of the threshold split of GPS z on this panel. Within each sign, z still varies, so the correlation is not 1 by construction.

Country bootstrap, same helper as `22_paper_a_surface.bootstrap_ci`: 2000 resamples, seed 20260905, percentile 2.5/97.5. Interval: [0.6829112043336851, 0.8765298530430597]. Undefined resamples: 0. Status: defined; country bootstrap matches 22_paper_a_surface.bootstrap_ci.

## Adapter contrast by sign

Mean adapter trust composite, positive-sign minus negative-sign: 0.36082470313391024.

Positive-sign mean: 2.757320076168726. Negative-sign mean: 2.3964953730348157. mean adapter trust composite, positive-sign (z>=0) minus negative-sign (z<0).

Rank-biserial correlation of the adapter composite with the sign: 0.9682539682539683. C=62; D=1; ties=0; n_sign1=7; n_sign0=9. Definition: (C − D) / (n1 × n0), C = pairs with higher adapter composite on the positive sign, D = the reverse, ties in the denominator only. Positive means the nonnegative GPS-trust side has the higher adapter composite. Pairwise inversions (positive-sign composite below a negative-sign composite): USA adapter 2.68620286057009 < ARG adapter 2.6902904861540717.

## Within-sign association with continuous z

Both are exploratory. A side with fewer than 8 countries, or with no rank variation in the adapter composite or in z, is not estimated.

- Within positive-sign (z ≥ 0): n=7; not estimated.
- Within negative-sign (z < 0): exploratory; n=9; rho=0.4666666666666666.

## What this file does not say

- It does not amend the claim lock and does not add a paper number.
- The sign-versus-z Spearman is not evidence that the adapter recovered GPS.
- The between-sign adapter difference is a descriptive contrast on this convenience panel, not a sign-retrain.
