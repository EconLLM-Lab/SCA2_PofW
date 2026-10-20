# C9-2: 2x2 TVD on the 42 cohort countries

DESCRIPTIVE / NOT PREREGISTERED. Produced by `paper_b/c9_tvd.py`; aggregates only (no per-country human values).

## Step 1: the preprint's TVD definition (source lines, as found)

Per cell (country c, item q), `misc/arxiv-submission-2026-10-05/methodology.tex:72`:

    \mathrm{TVD}_{cq}=\tfrac12\sum_j|\widehat P_c(j\mid x_q)-P_c^{H}(j\mid q)|,

with P^H "the survey-weighted share of valid human answers to item q in group c that equal code j" (methodology.tex:73).

Producer of `analysis/phase2/outputs/2x2_tvd.csv`: `analysis/phase2/18_2x2_analysis.py`.
- Join (line 195): model and population probabilities are merged on `option_value` with `how="inner"`; a cell with
  fewer than 2 matched options is dropped (line 196: `if len(merged) < 2: continue`).
- Renormalisation (lines 201-202): both vectors are divided by their sums after the inner join.
- TVD (line 203): `tvd = 0.5 * np.abs(pm - pp).sum()`.
- Aggregation (lines 222-223): `metrics.groupby("cell")[["tv_distance","top_option_match"]].mean()`, i.e. a POOLED
  mean over all (country, item) rows of a cell. Countries are not weighted equally when the item counts differ.
- Item set: the script applies no item filter; it averages whatever items the score files hold. The paper text says
  "TVD averages 368 country-item cells" (results.tex:54), which is 16 countries x 23 strict items.
- Skipped cells: a (country, item) without a human distribution is absent from the population file and is dropped by
  the inner join with no ledger. In the 42-country stack the ledger `local_eval/skipped_population_questions.csv` lists
  EGY/Q69, EGY/Q70, EGY/Q71, GBR/Q174 and JOR/Q178 (no valid responses); Q69-71 and Q174 are not strict-battery items,
  so only JOR/Q178 removes a battery cell here.

Differences in this Paper B re-run (declared, not silent):
- Headline mean TVD is COUNTRY-EQUAL (mean of country means), as the card asks; the preprint's pooled mean is reported
  beside it as `mean_tvd_pooled`. With one skipped cell the two differ only through JOR.
- Join is on `option_code` over the UNION of codes (a code missing on one side has mass 0), with no renormalisation;
  both sides must already sum to 1. This is the repo's audited convention (`eval_lib.calculate_question_metrics`) and is
  checked against `local_eval/survey_question_metrics_all_models.csv` (see the test).
- The adapter cell is each country's own adapter evaluated on that country (relationship "matched").
- Every number comes from the frozen Paper B stack; no preprint value is carried over.

## Inputs

- cohort1_model_probs: `planning/sprint_2026-10-11/paper-b-20261011/model_probs.csv` sha256 `02390efff036`
- persona_run: `persona-strict-v1-20261019 via persona_strict.csv` sha256 `efd663a50af3`
- adapter_persona_run: `adapter-persona-strict-v1-20261019` sha256 `-`
- human_distributions: `planning/sprint_2026-10-11/paper-b-20261011/local_eval/population_response_distributions.csv (local-only, not committed)` sha256 `ec88fe9f1c4d`
- gps_z: `synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json` sha256 `02972f0ec4a8`

Bootstrap: 2000 draws; profile-block seed 20261011, country seed 20260905; percentile 95%. Persona cells are not profile-constant, so both resampling units are shown.

## Cells

| Cell | Status | Countries | Cells | Mean TVD (country-equal) | Mean TVD (pooled) | Trust-GPS rho, profile-block | Trust-GPS rho, country |
|---|---|---|---|---|---|---|---|
| base | ok | 42 | 965 | 0.470 | 0.470 | trust composite is constant across countries | - |
| adapter | ok | 42 | 965 | 0.515 | 0.515 | 0.744 [0.500, 0.865] | 0.744 [0.577, 0.847] |
| persona | ok | 42 | 965 | 0.365 | 0.365 | 0.028 [-0.339, 0.381] | 0.028 [-0.273, 0.330] |
| adapter_persona | pending | - | - | - | - | - | - |

Skipped cells (no human distribution): JOR/Q178.

## Mean TVD by GPS dimension (country-equal within dimension)

| Cell | trust | patience | risktaking | posrecip | negrecip | altruism |
|---|---|---|---|---|---|---|
| base | 0.413 | 0.664 | 0.565 | 0.384 | 0.411 | 0.494 |
| adapter | 0.479 | 0.655 | 0.614 | 0.436 | 0.508 | 0.439 |
| persona | 0.315 | 0.541 | 0.524 | 0.244 | 0.352 | 0.244 |
| adapter_persona | - | - | - | - | - | - |

## Paired differences (country means of per-item TVD differences; negative = first cell closer to humans)

| Contrast | Profile-block 95% | Country 95% | n |
|---|---|---|---|
| adapter_minus_base | 0.045 [0.006, 0.093] | 0.045 [0.017, 0.079] | 42 |
| persona_minus_base | -0.105 [-0.122, -0.086] | -0.105 [-0.119, -0.091] | 42 |

The adapter+persona cell is PENDING (run `adapter-persona-strict-v1-20261019` is not available). Re-running this script fills it and adds the adapter_persona_* and interaction contrasts, with no code change.

Base trust-GPS is undefined: the base model has no country conditioning, so its trust composite is the same for every country.
