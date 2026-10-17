# Paper B Tier 1 — analysis results (2026-10-17)

Every number below was produced by a committed script from committed or Hub-pinned inputs. Human held-out
data were read only after the freeze (`FREEZE.json`, commit `5982544`), through `freeze.require_freeze`.

| Artifact | Producer | Output |
|---|---|---|
| Primary screen | `paper_b/heldout/run_screen.py` | `paper_b/heldout/screen_result.json` |
| Sections 4, 6, 7, 8 | `paper_b/heldout/analyze_heldout.py` | `heldout_analysis.json`, `heldout_items.csv` |
| Item-level ceiling | `paper_b/heldout/ceiling.py --items ceiling_heldout/items.json` | `ceiling_heldout/` |
| Sign-prompt probe | `build_probe_input.py --arm signprompt` + `probe_select.py` | selection sha `ed20902c…` |
| Factorial (plan F2) | `paper_b/analyze_factorial.py` | `factorial/mtmm_*`, `bank_robustness.csv` |
| Factorial views | `paper_b/factorial_report.py` | `factorial/factorial_report.json` |

Inputs: held-out run `bank2-heldout-v1-20261016` (spec `46447de6…`), sign-prompt run
`bank2-signprompt-heldout-v1-20261016` (same spec), strict run `bank2-strict-v1-20261016` (spec
`ed3bb964…`), cohort-1 run `paper-b-20261011`, strict sign-prompt cell `sign-prompt-20261011` (26 profiles).
Rebuilding the adapter items table after the loader change reproduces the frozen input byte for byte
(`47387b23…`).

## 1. The held-out screen (preregistered)

| | Value |
|---|---|
| A, 56 selected items, 42 countries | **0.0606** |
| Permutation p (10,000 draws, one-sided) | **0.0097** (null mean 0.012, 95th pct 0.046) |
| Country bootstrap 95% interval | [−0.007, 0.127] |
| Items with a_i > 0 | 34 of 56 (0.61) |
| Registered ceiling (wave 6 vs 7, 34 items fielded in both, 28 countries) | mean 0.746, median 0.767 |
| A as a share of the ceiling | 8.1 % (one-third would be 0.249) |

Section 9 reading: **the null is rejected and the signal is weak** (branch 2).

A per dimension: risktaking 0.158 (13 items, 92 % positive), altruism 0.069 (20, 65 %), trust 0.062
(12, 58 %), **posrecip −0.071 (11, 18 %)**. The adapter's positive-reciprocity assignments point the wrong
way more often than not; the other three dimensions carry the signal, risktaking most of it.

## 2. Planned sensitivity (section 8)

| Check | Result |
|---|---|
| Secondary rule (fixed threshold, reliability check) | A 0.070 over 185 items, p < 0.0001 (0 of 10,000), null 95th pct 0.034 |
| Leave one country out | A ranges 0.051 (drop RUS) to 0.072 (drop CHN) |
| Readout variants, share of (d_i, s_i) unchanged | reverse 39/56, para_a 39/56, para_b 30/56 — no variant changes more than half |
| Sign-prompt arm, same probe on the 64 prompts | A 0.028, p 0.51, interval [−0.109, 0.158] — **not above the null** |

The sign-prompt probe assigns **all 56** of its selected items to trust: under prompts, the trust bit is the
largest effect on 167 of 223 held-out items. The adapter probe spreads over all six dimensions (altruism
69, risktaking 50, trust 44, negrecip 32, posrecip 22, patience 6). The two selections share 16 items and
agree on dimension and sign for 6. Paired contrast adapter − prompt: D 0.033, interval [−0.083, 0.143]
(own items); D 0.004, interval [−0.065, 0.075] (16 shared items). The adapter route passes the null and
the prompt route does not, but the direct difference between them is not resolved.

## 3. Comparators (section 6, with Amendment 2)

Amendment 2 removed Q82 from both routes (the only repaired item either comparator had assigned).

| Route | Items (imprint) | A (imprint items) | D_common (registered primary) | D on own items |
|---|---|---|---|---|
| Face-valid reader | 25 | 0.095 | 5 shared items, D +0.020 [−0.181, 0.215] | −0.034 [−0.242, 0.169] |
| Jev System One | 40 | 0.128 | 9 shared items, D −0.002 [−0.064, 0.061] | −0.067 [−0.237, 0.103] |

All four intervals cover 0, so the registered reading is **"the adapters match a careful reader."** Three
facts qualify it. The coverage-matched contrasts rest on 5 and 9 items. Where adapter and Jev both assign,
they agree on dimension and sign for 7 of 9 items and reach the same A (0.120 vs 0.122). And both
comparators' point estimates on their own items are higher than the adapter's, because both concentrate
on the trust battery (trust A 0.110 face-valid, 0.151 Jev, vs 0.062 for the adapter's trust items), which
is the limitation section 6 named in advance.

## 4. The 2^6 factorial on the strict battery (Tier 1 item 1)

Every sign bit moves its own surface in the intended direction:

| Surface | Own effect (composite units) | OLS t (df 42) | Lenth t |
|---|---|---|---|
| trust | +0.36 | 16.7 | 4.33 |
| negrecip | +0.62 | 11.6 | 2.21 |
| altruism | +0.24 | 6.3 | 2.38 |
| patience:Q50 | +0.13 | 6.1 | 1.32 |
| risktaking | +0.14 | 4.1 | 0.83 |
| patience:Q43 | +0.05 | 3.6 | 0.93 |
| posrecip | +0.12 | 3.0 | 1.02 |

**The plan's V5 check fails**: own-surface dominance holds for 2 of 6 bits (altruism, negrecip; ≥ 4
required; binomial p 0.21). The two scale-free views added beside it agree: 2 of 6 on standardized rows,
1 of 7 on columns (only trust's own bit is the largest mover of the trust surface). Cross-talk is
concentrated: the risktaking bit is the largest effect on altruism (+0.98), negrecip (−0.67) and
patience:Q43, and the trust bit is the largest on patience:Q50 and posrecip. One common direction explains
51 % of the variance of the seven surfaces over the 64 units.

Route contrast on the 26 cells where the strict sign-prompt cell exists (exploratory, main effects only):

| | Adapter | Sign prompt |
|---|---|---|
| Variance on the first common direction | 60 % | 88 % |
| Surfaces whose largest mover is the trust bit | 3 of 7 | **7 of 7** |
| Own effects in the wrong direction | 0 of 7 | 3 of 7 (risktaking −0.73, patience:Q43 −0.58, negrecip −0.10 SD) |

Bank robustness, bank 2 (64 profiles) vs cohort 1 (sign-mate country means), 26 shared cells, Pearson:
altruism 0.95, patience:Q50 0.94, trust 0.91, posrecip 0.90, patience:Q43 0.81, negrecip 0.71,
risktaking 0.60.

## 5. Acceptance checks (plan F3)

| # | Check | Result |
|---|---|---|
| V1 | Bank 2 gates | pass (658 triplets, earlier audit) |
| V2 | 64/64 adapters | pass (64 units on the pinned strict spec) |
| V3 | Readout determinism | pass: 4 gate-run units reproduce strict_v1 exactly (max abs diff 0, 140 rows each); `P_1_1_1_1_1_1` reproduces on both VMs |
| V4 | Blinding | pass: freeze committed 15:40, first human held-out read 15:43; the pre-freeze ceiling read the 23 battery items only |
| V5 | Factorial informative (≥ 4 of 6 dominant) | **fail**: 2 of 6 |

## 6. Exploratory, labelled

- Effect sizes: the adapter's top effect on its 56 selected items has median 0.47 response-code units
  (median |t| 17); the prompt route's, 0.71 (median |t| 70).
- A in another human wave: over the 28 countries with both waves and the 34 items fielded in both, A is
  0.043 on wave-6 means and 0.047 on wave-7 means. The signal is small and stable across waves.

## 7. What this supports, in one paragraph

Sign-trained adapters screen held-out WVS items better than random assignment (p 0.01), robustly to any
single country, to the looser selection rule and to readout wording, and the effect replicates on an
earlier human wave; but the signal is weak, about 8 % of what two human waves achieve, and its interval
touches zero. On the items where they overlap, the adapters match a careful reader of the questionnaire.
Prompting with the same sign profile does not pass the null, because the prompted trust sign shifts
nearly every item at once. The factorial shows why the adapters are better than prompts and also why they
are not a clean compiler: each bit moves its own surface in the right direction, but the bits also move
each other's surfaces, often more.
