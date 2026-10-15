# Paper B scored surface, 2026-10-11

Run `paper-b-20261011`. Frozen stack in `PAPER_B_STACK_FREEZE.md`. Adapter revision `7550fd4cfe514470bb8d80918a43c9ae424d26b5`. Forty-three Hub files, each SHA-256 matched to its manifest. The T4 is stopped.

The China same-weights gate passed by control flow: the scorer refuses to continue if it fails, and all 42 adapters were written. The numeric gate report was on the VM and was not uploaded, so the tolerance gaps are not quoted here.

This is a new surface. It is not a bit-level extension of Paper A's locked 0.74.

## Three columns

Country-equal Spearman. Adapter intervals are profile-block bootstrap, 2000 draws, seed 20261011. Human-GPS intervals are country bootstrap.

| Surface | Adapter–GPS | Adapter–human | Human–GPS |
|---|---|---|---|
| Trust | 0.74 [0.50, 0.86], n=42 | 0.30 [−0.04, 0.55], n=42 | 0.35 [0.09, 0.56], n=42 |
| Patience Q43 | −0.02 [−0.41, 0.45] | 0.19 [−0.17, 0.46] | −0.53 [−0.74, −0.27] |
| Patience Q50 | 0.18 [−0.31, 0.58] | 0.00 [−0.29, 0.32] | 0.39 [0.09, 0.63] |
| Risk taking | 0.43 [0.08, 0.69], n=42 | 0.12 [−0.26, 0.43], n=41 | −0.06 [−0.43, 0.31], n=41 |
| Positive reciprocity | 0.49 [0.12, 0.69] | 0.32 [−0.07, 0.62] | 0.05 [−0.27, 0.39] |
| Negative reciprocity | −0.03 [−0.42, 0.41] | 0.39 [−0.01, 0.69] | 0.42 [0.17, 0.59] |
| Altruism | 0.41 [0.02, 0.68] | 0.13 [−0.17, 0.37] | 0.03 [−0.31, 0.35] |

Profile-equal sensitivity does not change which dimensions clear zero.

## What the surface says

Adapters recover GPS order on trust, risk taking, positive reciprocity, and altruism. They do not recover GPS order on either patience item or on negative reciprocity. No adapter–human interval excludes zero.

Within a GPS-sign profile, country composites barely move. Median within-profile SD is under 0.01 on every dimension. The all-positive altruism profile sits at 2.0. Sign-mates are nearly copies of each other.

Paired mean absolute error versus humans: adapters beat the base model in 20 of 42 countries. The mean adapter-minus-base gap is +0.06, so the cohort is not closer to the surveys on average.

## Skipped cells

Strict battery: Jordan has no human Q178, so risk-taking human comparisons use 41 countries. The adapter side has Q178 for Jordan. Outside the strict battery, the local join also skipped Egypt Q69–Q71 and Britain Q174.

## Decision, 2026-10-11

Inference is better than the 16-country panel: full intersection, profile-block intervals, and some GPS-order intervals that now exclude zero. The points are not larger. The analysis checks on this surface are done. Writing and editing wait for a specialized profile.

## Analysis phase, 2026-10-11

Computed by `paper_b/analyze_phase.py` from the banked scores. Variance shares are sums of squares. The multi-member share drops the 14 singleton profiles, which would otherwise count as pure between-profile variance.

On multi-member profiles, the adapter between-profile share is 0.96 to 1.00 on every surface. The human between-profile share on those same profiles is 0.32 to 0.63. Adapters are copies of the sign profile. Humans still differ inside it.

Negative reciprocity is flat on every item. Profile-block intervals: Q176 0.06 [−0.30, 0.38], Q177 0.13 [−0.28, 0.55], Q179 0.00 [−0.38, 0.40], Q195 0.09 [−0.36, 0.50]. No item is carrying a GPS correlation the composite hid.

Ceiling hits are six cells, all in the all-positive profile (Australia, Canada, United States): altruism at 2.0 and positive reciprocity at 4.0. No other country sits on a bound.

Dimension-specific mean adapter-minus-base absolute error versus humans: risk taking −0.14 (closer in 32 of 41), negative reciprocity −0.17 (closer in 22 of 42), altruism −0.10 (closer in 22 of 42). Trust is +0.05 (closer in 18 of 42). Patience Q50 is +0.10. Tracking GPS and being closer to the survey are different facts.

Risk-taking adapter–GPS with Jordan dropped is 0.44 [0.09, 0.68], against 0.43 [0.08, 0.69] with Jordan kept.

## Log-GDP partial, 2026-10-11

Rank-residual partial Spearman of the banked composites against GPS z, controlling for log GDP per capita (WDI `gdp_pc_ppp`, 2015–2019 mean, `data/phase2/aux/wdi.csv`). Venezuela has no finite value in that cache, so every partial is n=41. This is not a new score.

| Surface | Adapter–GPS raw (n=42) | Adapter–GPS partial log GDP (n=41) | Adapter–log GDP |
|---|---|---|---|
| Trust | 0.74 | 0.75 | 0.09 |
| Patience Q43 | −0.02 | −0.05 | 0.03 |
| Patience Q50 | 0.18 | 0.15 | 0.11 |
| Risk taking | 0.43 | 0.49 | −0.21 |
| Positive reciprocity | 0.49 | 0.49 | 0.11 |
| Negative reciprocity | −0.03 | −0.14 | 0.34 |
| Altruism | 0.41 | 0.40 | 0.13 |

The four recoveries survive the partial. Adapters do not track log GDP on those surfaces. GPS patience does (0.48 on the same 41); the adapters do not. No further experiment is identified for this table.

