# PLACEBO REPORT — restricted permutation test (G0: E[recode], 2026-08-23)
Null: country->anchor assignment without replacement from the 16 observed anchors (N=1000, seed=20260820).
Construction: E[recode(V)] / P(option 1) on Q57; must match script 13 adapter trust.
Real-anchor trust bridge rho: 0.782
Real-anchor dev-trust rho: nan
Real-anchor median own-rank (42-country): 15.0

p-values (one-sided; lower_better for rank):
- trust_bridge: real=0.782, null median=-0.006, q95=0.453, p=0.0010 -> SUPPORTED
- dev_trust: real=nan, null median=nan, q95=nan, p=nan -> NOT SUPPORTED
- median_own_rank: real=15.000, null median=15.000, q95=15.000, p=1.0000 -> NOT SUPPORTED