# Held-out screen result (2026-10-17) — the preregistered primary test

First read of the human criterion. It runs only through `require_freeze()`, against the frozen amended
selection (`selection_sha256 782b7d21…`, pool `19241f6f…`, code revision `357adde`, scoring revision
`2126045`). Command: `python paper_b/heldout/run_screen.py`. Output: `paper_b/heldout/screen_result.json`.

## Inputs

- Selection: 223 pool items, 56 primary, item signs from the probe's `t_top`.
- Human surface: WVS wave 7, survey-weighted country means of the **raw** code, one cell per
  country-item pair, `W_WEIGHT`, floor of 50 valid weighted respondents. 66 countries have coverage.
  174 item-country cells fall below the floor and enter as missing.
- GPS: `country_gps.dta` indexed by `isocode`, six dimensions, loaded as the phase-2 pipeline loads it.
- Countries used: **42** (WVS-7 coverage intersected with GPS).

## Result

| Statistic | Value |
|---|---|
| A (mean of `sign_i × Spearman(human_i, GPS[dim_i])` over the 56 selected items) | **0.0606** |
| Permutation p (one-sided, 10,000 draws, seed 20261015) | **0.0097** |
| Null mean / 95th percentile | 0.0119 / 0.0463 |
| Country bootstrap 95% interval (2,000 draws) | **[-0.0067, 0.1265]** |

## Verdict against the preregistered branches (section 9)

1. "A not above the permutation null at one-sided 0.05" — **not the case.** A = 0.0606 exceeds the null's
   95th percentile (0.0463) with p = 0.0097. The adapters screen held-out items better than random
   assignment, and that is the primary claim.
2. "A above the null but below one-third of the wave-6/7 ceiling → screening signal exists but is weak" —
   **this is the case.** The human ceiling by surface is trust 0.743, patience 0.783 and 0.716,
   risktaking 0.608, posrecip 0.446, altruism 0.761, negrecip 0.736, mean **0.685**. One-third of the mean
   is 0.228, and A = 0.061 is far below it: **A is 8.8 % of the human ceiling.**

So the registered reading is: the screening signal is present and statistically distinguishable from
chance, and it is **weak** in magnitude.

## Caveats to state with this number

- The bootstrap interval includes zero. The permutation test rejects the null, the country-resampling
  interval does not, so the magnitude is imprecise even where the sign of the finding is not.
- The two statistics are constructed differently and the ratio is a benchmark, not a fraction of
  achievable signal: the ceiling is a per-surface correlation between two human waves over 28 countries,
  while A is a per-item sign-weighted correlation over 42 countries. The preregistration asks for the
  comparison, so it is reported, with that difference named.
- 174 item-country cells below the 50-respondent floor enter as missing. They are not imputed.
- The screen was run once, against the frozen selection. No analysis choice was made after seeing it.
