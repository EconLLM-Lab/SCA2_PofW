# Per-dimension held-out agreement (checkpoint C5)

Produced by `paper_b/heldout/per_dimension.py`; every number is read from
`heldout_per_dimension.json`, written by the same run.

- Seed 20261015, 2,000 country-bootstrap resamples, 10,000 permutation
  draws; 42 countries (GPS ∩ WVS-7), pool 223 items.
- A_d and its interval are registered (PREREGISTRATION.md sections 1 and 4): a_i is
  `screen_test.item_agreement`'s signed Spearman against GPS z, A_d its mean over the items
  the route assigns to dimension d, and the interval the 2.5/97.5 percentiles of the
  registered country bootstrap.
- The permutation p is **not registered**: it is descriptive only (card T1 step 4).
- C5 rule, quoted from `.hermes/plans/2026-10-11_233701-paper-b-journey.md`: "An imprint
  dimension whose new-battery interval includes 0 is not transport." The reading below
  applies that rule mechanically to the interval; the sign of A_d is in its own column.

## adapter primary rule (selection_amended_20261016.csv, primary_selected)

56 items over 4 dimensions.

| dimension | items | A_d | 95% country-bootstrap interval | p (perm, not registered) | C5 |
|---|---|---|---|---|---|
| trust | 12 | 0.062 | [-0.047, 0.173] | 0.2598 | interval includes 0: not transport |
| risktaking | 13 | 0.158 | [0.015, 0.290] | 0.0007 | interval excludes 0: transport |
| posrecip | 11 | -0.071 | [-0.281, 0.154] | 0.9479 | interval includes 0: not transport |
| altruism | 20 | 0.069 | [-0.036, 0.177] | 0.0262 | interval includes 0: not transport |

C5 reading, one line per dimension:

- trust: interval includes 0: not transport (A_d 0.062, n 12, interval [-0.047, 0.173])
- risktaking: interval excludes 0: transport (A_d 0.158, n 13, interval [0.015, 0.290])
- posrecip: interval includes 0: not transport (A_d -0.071, n 11, interval [-0.281, 0.154])
- altruism: interval includes 0: not transport (A_d 0.069, n 20, interval [-0.036, 0.177])

## adapter secondary rule (fixed threshold, secondary_selected)

185 items over 4 dimensions.

| dimension | items | A_d | 95% country-bootstrap interval | p (perm, not registered) | C5 |
|---|---|---|---|---|---|
| trust | 44 | 0.092 | [-0.019, 0.199] | 0.0037 | interval includes 0: not transport |
| risktaking | 50 | 0.143 | [0.045, 0.229] | 0.0000 | interval excludes 0: transport |
| posrecip | 22 | -0.049 | [-0.198, 0.117] | 0.9452 | interval includes 0: not transport |
| altruism | 69 | 0.040 | [-0.038, 0.117] | 0.0400 | interval includes 0: not transport |

C5 reading, one line per dimension:

- trust: interval includes 0: not transport (A_d 0.092, n 44, interval [-0.019, 0.199])
- risktaking: interval excludes 0: transport (A_d 0.143, n 50, interval [0.045, 0.229])
- posrecip: interval includes 0: not transport (A_d -0.049, n 22, interval [-0.198, 0.117])
- altruism: interval includes 0: not transport (A_d 0.040, n 69, interval [-0.038, 0.117])

## sign-prompt primary (signprompt_selection_20261017.csv, primary_selected)

56 items over 1 dimension.

| dimension | items | A_d | 95% country-bootstrap interval | p (perm, not registered) | C5 |
|---|---|---|---|---|---|
| trust | 56 | 0.028 | [-0.107, 0.159] | 0.5012 | interval includes 0: not transport |

C5 reading, one line per dimension:

- trust: interval includes 0: not transport (A_d 0.028, n 56, interval [-0.107, 0.159])

## face-valid reader (imprint set, Amendment 2 repaired items removed)

25 items over 3 dimensions.

| dimension | items | A_d | 95% country-bootstrap interval | p (perm, not registered) | C5 |
|---|---|---|---|---|---|
| trust | 19 | 0.110 | [-0.154, 0.379] | 0.0283 | interval includes 0: not transport |
| risktaking | 4 | 0.044 | [-0.170, 0.243] | 0.2007 | interval includes 0: not transport |
| altruism | 2 | 0.055 | [-0.163, 0.265] | 0.4060 | interval includes 0: not transport |

C5 reading, one line per dimension:

- trust: interval includes 0: not transport (A_d 0.110, n 19, interval [-0.154, 0.379])
- risktaking: interval includes 0: not transport (A_d 0.044, n 4, interval [-0.170, 0.243])
- altruism: interval includes 0: not transport (A_d 0.055, n 2, interval [-0.163, 0.265])

## Jev majority (imprint set, Amendment 2 repaired items removed)

40 items over 3 dimensions.

| dimension | items | A_d | 95% country-bootstrap interval | p (perm, not registered) | C5 |
|---|---|---|---|---|---|
| trust | 32 | 0.151 | [-0.076, 0.370] | 0.0000 | interval includes 0: not transport |
| risktaking | 1 | -0.074 | [-0.398, 0.239] | 0.5302 | interval includes 0: not transport |
| altruism | 7 | 0.049 | [-0.078, 0.165] | 0.2200 | interval includes 0: not transport |

C5 reading, one line per dimension:

- trust: interval includes 0: not transport (A_d 0.151, n 32, interval [-0.076, 0.370])
- risktaking: interval includes 0: not transport (A_d -0.074, n 1, interval [-0.398, 0.239])
- altruism: interval includes 0: not transport (A_d 0.049, n 7, interval [-0.078, 0.165])

## Exploratory: Bonferroni-adjusted intervals (not registered)

Added 2026-10-18 by the orchestrator for SMR's multiplicity request. Bonferroni over the 4 imprint dimensions,
read off the same 2,000 draws: percentiles 0.625 and 99.375. The registered 95% intervals above are unchanged.

| route | dimension | items | A_d | registered 95% | Bonferroni |
|---|---|---|---|---|---|
| adapter_primary | trust | 12 | 0.062 | [-0.047, 0.173] | [-0.088, 0.199] |
| adapter_primary | risktaking | 13 | 0.158 | [0.015, 0.290] | [-0.026, 0.326] |
| adapter_primary | posrecip | 11 | -0.071 | [-0.281, 0.154] | [-0.332, 0.205] |
| adapter_primary | altruism | 20 | 0.069 | [-0.036, 0.177] | [-0.058, 0.198] |
| adapter_secondary | trust | 44 | 0.092 | [-0.019, 0.199] | [-0.049, 0.236] |
| adapter_secondary | risktaking | 50 | 0.143 | [0.045, 0.229] | [0.017, 0.253] |
| adapter_secondary | posrecip | 22 | -0.049 | [-0.198, 0.117] | [-0.227, 0.154] |
| adapter_secondary | altruism | 69 | 0.040 | [-0.038, 0.117] | [-0.054, 0.133] |

## Sanity check against the committed point estimates

`planning/sprint_2026-10-11/paper-b-tier1/results/heldout_analysis.json` reports the same A_d without intervals. Largest absolute difference here:
0.00e+00; item counts all match: True.

- altruism: A_d 0.0688 (committed 0.0688), n 20
- posrecip: A_d -0.0706 (committed -0.0706), n 11
- risktaking: A_d 0.1576 (committed 0.1576), n 13
- trust: A_d 0.0620 (committed 0.0620), n 12

Amendment 2: the repaired items leave both comparator routes in code; present in the
frozen comparator files and excluded here: ['Q82'] (face-valid),
['Q82'] (Jev).
