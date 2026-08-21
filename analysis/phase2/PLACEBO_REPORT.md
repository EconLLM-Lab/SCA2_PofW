# PLACEBO REPORT — restricted permutation test (2026-08-20)

## Predeclared (before outcome inspection)
- Null: country->anchor assignment drawn without replacement from the 16
  observed anchors (permuted among the 16 countries).
- Primary statistic: trust construct-bridge Spearman rho (adapter composite
  vs GPS country z-score, 16 countries; unified construction, script 13).
- Secondary: median own-country rank (canonical 42-country matrix).
- Margin: real > 95th percentile of null (p<=0.05 one-sided).
- N = 1000, seed 20260820.

## Results
- trust_bridge: real = 0.703, null median = -0.003,
  95th pct = 0.438, p = 0.0030
  -> SUPPORTED (p <= 0.05): the real anchor assignment carries information
  beyond generic synthetic tuning on the primary statistic.
- median_own_rank: real = 15.0, null = 15.0 (degenerate: std 0.0).
  The rank is INVARIANT under this null by construction: 16 countries
  instantiate 13 sign profiles (3 twin pairs), so permuting the observed
  anchors never changes the set of profile-adapters, hence never changes
  the median own-rank. The rank statistic is uninformative under the
  observed-anchor-multiset null; it cannot discriminate anchor relevance.
- dev_trust (descriptive, real only): rho = 0.132 (per-adapter
  trust composite vs log GDP pc, n=16). Not a predeclared permutation
  statistic (per-adapter development values were not precomputed);
  reported as context. The unified dev table's pooled adapter row is
  +0.13 (partial +0.56).

## Interpretation
- Anchor relevance PASSES on the predeclared primary (trust bridge, p=0.003).
- The rank degeneracy is itself a finding: sign-profile collapse makes
  location-rank tests insensitive to anchor permutation; the bridge (which
  uses magnitudes, not just signs) is the right test. This motivates the
  extended-35-profile arm (22 additional adapters) if rank-level power is
  ever needed.
- Table 2 anchor-relevance row: PENDING -> PASSED (trust bridge); rank arm
  uninformative by construction.