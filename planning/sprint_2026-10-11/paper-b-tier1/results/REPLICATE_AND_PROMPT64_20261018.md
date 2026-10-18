# Replicate (unseeded retrain) and the 64-cell sign-prompt factorial (2026-10-18)

Card T6. Two results, both produced after card T4 scored the data on the Hub. Every number below
comes from a script written for this card and its output file; nothing is typed by hand.

| Result | Producer | Output |
|---|---|---|
| 64-cell sign-prompt factorial | `paper_b/analyze_factorial.py` + `paper_b/factorial_report.py` | `factorial/factorial_report.json`, `factorial/mtmm_signprompt*.csv` |
| Replicate vs original unit | `paper_b/analyze_replicate.py` | `replicate/replicate_analysis.json`, `replicate/replicate_surface_diff.csv`, `replicate/replicate_item_codes.csv` |

Inputs. `signprompt_strict_64.csv` (64 profiles x 23 strict items, `eval_country = P_<bits>`) was built
from `Bonorinoa/SCA2-paper-b-artifacts` run `bank2-signprompt-strict-v1-20261018`: 64 CSVs and 64
manifests, every manifest's `spec_sha256` equal to the strict pin `ed3bb964b606…`. The replicate CSVs
come from runs `bank2-replicate-r1-strict-v1-20261018` (pin `ed3bb964b606…`) and
`bank2-replicate-r1-heldout-v1-20261018` (pin `46447de63f7c…`); the original unit's held-out file from
run `bank2-heldout-v1-20261016` (same pin). The original unit's strict rows are the local
`adapter_strict_v1.csv` (run `bank2-strict-v1-20261016`). The builder is
`/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/fetch_t6_inputs.py` (a byte-identical copy of the
scratch original, which the scratch pruner would delete; re-run it and every sha256 below is
reproduced byte for byte, spec pins included). `signprompt_strict_64.csv`
sha256 `bf05e07739732bfb…`. The 26-profile cell already in the tree is unchanged and still reported.

## 1. The 2^6 factorial with all 64 sign-prompt cells

The 26-cell route contrast in `TIER1_ANALYSIS_20261017.md` had only the 26 cohort sign profiles on the
sign-prompt side. T4 scored all 64. `factorial_report.py` gained `--signprompt-strict-64` and a
`route_contrast_64_cells` block computed exactly like `route_contrast_26_cells` but with the full 2^6
design (`factorial_effects.fit`: intercept + six main effects + fifteen two-way interactions, error df
42). The 26-cell block is unchanged: every key of it compares equal to the previous
`factorial_report.json`.

Adapter route (64 cells) — unchanged from the 26-cell reading, as it must be, since it is the same
`bank2-strict-v1-20261016` data:

| View | Result |
|---|---|
| V5, row-wise own-surface dominance on raw main effects | **2 of 6** (altruism, negrecip), binomial p 0.207 |
| Row-wise dominance on rows standardized by the surface SD | 2 of 6 |
| Column-wise dominance (own bit the largest mover of its surface) | 1 of 7 |
| Share of the first principal component of the 7 standardized composites | 0.513 |

Own effect, OLS t (df 42) and Lenth t on the diagonal, adapter route (all seven positive, intended
direction):

| Surface | own effect | OLS t | Lenth t |
|---|---|---|---|
| trust | +0.3636 | 16.74 | 4.33 |
| negrecip | +0.6248 | 11.64 | 2.21 |
| altruism | +0.2421 | 6.32 | 2.38 |
| patience:Q50 | +0.1325 | 6.12 | 1.32 |
| risktaking | +0.1400 | 4.14 | 0.83 |
| patience:Q43 | +0.0494 | 3.63 | 0.93 |
| posrecip | +0.1242 | 3.02 | 1.02 |

Sign-prompt route (64 cells) — the 26-cell exploratory reading, now on the full design:

| View | Result |
|---|---|
| V5, row-wise own-surface dominance on raw main effects | **2 of 6** (trust, patience), binomial p 0.207 |
| Row-wise dominance on rows standardized by the surface SD | 1 of 6 |
| Column-wise dominance | 1 of 7 |
| Surfaces whose largest mover is the trust bit | **7 of 7** |
| Own effects in the wrong direction | **3 of 7** |
| Share of the first principal component | **0.835** |

Sign-prompt diagonal: trust +1.7797 (t 394.46, Lenth 94.84), patience:Q50 +0.4211 (17.63, 3.99),
altruism +0.3644 (11.99, 13.27), posrecip +0.1031 (5.66, 1.51), risktaking **−0.4567** (−22.31, −3.73),
patience:Q43 **−0.0692** (−19.75, −1.54), negrecip **−0.0233** (−1.80, −1.55).

Reading. Both routes fail the plan's V5 rule (2 of 6, ≥ 4 required) and neither dominates column-wise
(1 of 7). What separates them is the common direction: on the sign-prompt route one direction explains
83.5 % of the variance of the seven surfaces and the trust bit is the largest mover of every surface,
with three of the seven own effects pointing the wrong way; the adapter route's common direction is
0.513 and every own effect points the intended way. This is the same contrast the 26-cell exploratory
block reported (60 % vs 88 %, 3 of 7 vs 7 of 7, 0 of 7 vs 3 of 7 wrong-signed), now on all 64 cells.

## 2. The replicate: an unseeded retrain

`P_1_0_1_1_0_1` was retrained from the same recipe with no seed fixed. It is called **an unseeded
retrain**; no weight-space cosine is computed or cited (verifier finding F8), and a test fails if the
module ever calls one. Same bits means the same scored cells:

| Quantity | Strict battery (23 items) | Held-out pool v1 (223 items) |
|---|---|---|
| scored cells compared | 140 | 1087 |
| grids identical | yes (0 cells on one side only) | yes (0 cells on one side only) |
| max abs probability difference | 0.05151 | 0.09163 |
| mean abs probability difference | 0.006047 | 0.005553 |
| Pearson of expected codes over the items | **0.99981** (n 23) | **0.99961** (n 223) |
| Pearson of E[recode] over the items | 0.99989 (n 23) | not defined off the battery |

Expected code is `sum_k p_k * code_k` (`build_probe_input.expected_code`); the E[recode] variant
applies the frozen instrument recode (`analyze_surface.recode_value`) and is reported beside it for the
strict battery only, because the held-out route uses no recodes. Per-item pairs are in
`replicate/replicate_item_codes.csv`.

Strict-surface differences, replicate minus original, divided by that surface's SD over the 64 profile
composites of the bank-2 strict run (the same SDs as `factorial_report.json` →
`surface_sd_over_units`):

| Surface | replicate | original | difference | SD over 64 profiles | difference (SD units) |
|---|---|---|---|---|---|
| trust | 2.73925 | 2.74477 | −0.005524 | 0.22212 | −0.0249 |
| patience:Q43 | 1.99457 | 1.99386 | +0.000710 | 0.11040 | +0.0064 |
| patience:Q50 | 6.38744 | 6.42260 | −0.035167 | 0.31471 | **−0.1117** |
| risktaking | 5.29287 | 5.30174 | −0.008873 | 0.29837 | −0.0297 |
| posrecip | 3.02604 | 3.02969 | −0.003652 | 0.32138 | −0.0114 |
| negrecip | 7.65000 | 7.62845 | +0.021550 | 0.64397 | +0.0335 |
| altruism | 0.93640 | 0.94130 | −0.004898 | 0.62354 | −0.0079 |

Every strict-surface difference is smaller than 0.12 of a profile SD (largest |difference| 0.1117
SD, patience:Q50 — past one ninth, so the bound is stated as 0.12 and not as 1/9). The largest
single-cell probability difference is 0.0515 (strict) and 0.0916 (held-out); the expected codes over
items track at r ≥ 0.9996 in both batteries.

## 3. How to reproduce

```
env -u PYTHONPATH .venv/bin/python paper_b/analyze_factorial.py \
  --adapter /Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/adapter_strict_v1.csv \
  --signprompt /Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/signprompt_strict_64.csv \
  --out planning/sprint_2026-10-11/paper-b-tier1/results/factorial

env -u PYTHONPATH .venv/bin/python paper_b/factorial_report.py \
  --adapter .../adapter_strict_v1.csv \
  --signprompt-strict .../signprompt_strict_raw.csv \
  --signprompt-strict-64 .../signprompt_strict_64.csv \
  --results planning/sprint_2026-10-11/paper-b-tier1/results/factorial

env -u PYTHONPATH .venv/bin/python paper_b/analyze_replicate.py \
  --replicate-strict  <scratch>/t6/replicate_strict_v1.csv \
  --original-strict   .../adapter_strict_v1.csv \
  --replicate-heldout <scratch>/t6/replicate_heldout_v1.csv \
  --original-heldout  <scratch>/t6/original_heldout_unit.csv \
  --out planning/sprint_2026-10-11/paper-b-tier1/results/replicate
```

Tests: `env -u PYTHONPATH -u VIRTUAL_ENV .venv/bin/python -m pytest -q paper_b/test_analyze_replicate.py`
(12 passed) and, for the additive change to `factorial_report.py`, a scratch test at
`/Users/bonorinoa/.hermes/profiles/engineer/cache/scratch/t6/test_factorial_report_64.py` (4 passed,
RED first). That scratch test exists because T6's write boundary names `factorial_report.py` and its
test only "if one exists", and none did; the boundary was respected rather than widened — if a durable
in-tree test for the 64-cell path is wanted, the boundary has to name `paper_b/test_factorial_report.py`.

Verified, not just written (each re-run, exit codes captured without a pipe):

| Step | Command | Exit |
|---|---|---|
| inputs re-fetched from the Hub | `env -u PYTHONPATH .venv/bin/python paper_b_inputs/fetch_t6_inputs.py` | 0, all five sha256 unchanged |
| factorial 64 cells | `analyze_factorial.py --adapter …/adapter_strict_v1.csv --signprompt …/signprompt_strict_64.csv --out results/factorial` | 0 |
| report, both routes | `factorial_report.py --adapter … --signprompt-strict …/signprompt_strict_raw.csv --signprompt-strict-64 …/signprompt_strict_64.csv --results results/factorial` | 0 |
| replicate | `analyze_replicate.py --replicate-strict … --original-strict … --replicate-heldout … --original-heldout … --out <scratch>/t6/replicate_out2` | 0, outputs byte-identical to `results/replicate/` |
| every number in this note | `<scratch>/t6/t6_note_claims_check.py` (124 claims) | 0, 124 pass, log `<scratch>/t6/t6_claims_check.out` |

The re-run `factorial_report.json` leaves all seven top-level keys and `route_contrast_26_cells`
bit-for-bit equal to the committed version and only adds `route_contrast_64_cells` (254 inserted
lines, 0 deleted; `<scratch>/t6/t6_verify_report.py`).

## 4. Not certain, or deliberately not claimed

- The two routes are compared on the same 64 cells, but the sign-prompt route's items are prompted
  rather than trained; the contrast measures the two instruments, not two training recipes.
- The replicate is one unit out of 64. A single retrain bounds the retraining noise for that unit only;
  it is not an estimate of the across-unit retraining variance.
- `results/replicate/` is a directory the T6 write boundary did not name (it names `results/factorial/`
  and the note). Filing the replicate outputs under `results/factorial/` would have misattributed them,
  so they went in their own directory; flagged on the card.
- Lenth t on the sign-prompt diagonal is large (94.84 for trust) because Lenth's pseudo standard error
  is built from the fifteen interaction coefficients, which are near zero on that route.
