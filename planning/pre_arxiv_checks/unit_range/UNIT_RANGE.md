# Unit-range composite check

Retrospective comparison of the locked raw composite with a 0-1 composite on the frozen 16-country surface. No model was called. Repository files were not modified.

## Precedence

**Label: retrospective.**

Searched for a unit-range or 0-1 WVS composite specified before outcome inspection:

- No analysis-plan file in the repository.
- `protocols/gps_sign_dpo_wvs.toml` standardizes GPS z and records June 23 scorer 0-1 ratings on synthetic pairs. That is not a WVS item-composite specification.
- `misc/position_paper/rewrite/appendix.tex` states that proposed dimension composites are unweighted averages of item means without standardizing ranges, and that unit-range recoding is a separate sensitivity in the saved audit. That sentence describes a post-outcome audit, not a pre-inspection spec.
- `misc/presentation/presentation.tex` and `presentation_20260914.tex` say composites average item means without range standardization.
- `Hermes/Projects/SCA2/PRE_ARXIV_CHECKLIST.md` (locked 2026-09-25) says no such spec was found in the draft and to treat the check as retrospective unless a file search finds one.

No dated pre-inspection specification was found. The audit bundle `Hermes/Projects/SCA2_results_audit/key_results.json` later stores normalized-scale correlations. Those are saved post-audit results, not a spec that preceded outcome inspection, and they are not the numbers reported here. This check recomputes from `analysis/phase2/outputs/paper_a/country_item_scores.csv` column `raw` and from theoretical ranges.

## Reproduction gate

Adapter-GPS trust, nine items, arm `adapter`, raw composite: **0.800000**. Absolute distance from 0.80 is 0.000000, inside 0.005. Gate passed.

Country bootstrap matches `analysis/phase2/22_paper_a_surface.py`: 2000 draws, `numpy` Generator seed 20260905, percentile interval from `np.quantile` at 0.025 and 0.975. Patience Q43 and Q50 are not pooled. Trust uses Q57-Q64 and Q73, not Q69-Q71.

## Theoretical ranges after recode

Min and max are the minimum and maximum of the paper recode applied to the instrument `ResponseCodes` in `DPO_eval_WVS/question_map_wvs_edited.csv`. They are not the sample minimum or maximum of country means. An unresolved range would be excluded from the 0-1 composite. None of the mapped items was unresolved.

| Item | Status | Response codes | Recode | Min | Max |
|---|---|---|---|---:|---:|
| Q101 | used | 2;1;0 | identity | 0 | 2 |
| Q103 | used | 2;1;0 | identity | 0 | 2 |
| Q106 | used | 1;2;3;4;5;6;7;8;9;10 | identity | 1 | 10 |
| Q107 | used | 1;2;3;4;5;6;7;8;9;10 | identity | 1 | 10 |
| Q109 | used | 1;2;3;4;5;6;7;8;9;10 | identity | 1 | 10 |
| Q176 | used | 1;2;3;4;5;6;7;8;9;10 | identity | 1 | 10 |
| Q177 | used | 1;2;3;4;5;6;7;8;9;10 | 11-v | 1 | 10 |
| Q178 | used | 1;2;3;4;5;6;7;8;9;10 | identity | 1 | 10 |
| Q179 | used | 1;2;3;4;5;6;7;8;9;10 | 11-v | 1 | 10 |
| Q195 | used | 1;2;3;4;5;6;7;8;9;10 | identity | 1 | 10 |
| Q43 | used | 1;2;3 | identity | 1 | 3 |
| Q50 | used | 1;2;3;4;5;6;7;8;9;10 | identity | 1 | 10 |
| Q57 | used | 1;2 | 1{v=1} | 0 | 1 |
| Q58 | used | 1;2;3;4 | 5-v | 1 | 4 |
| Q59 | used | 1;2;3;4 | 5-v | 1 | 4 |
| Q60 | used | 1;2;3;4 | 5-v | 1 | 4 |
| Q61 | used | 1;2;3;4 | 5-v | 1 | 4 |
| Q62 | used | 1;2;3;4 | 5-v | 1 | 4 |
| Q63 | used | 1;2;3;4 | 5-v | 1 | 4 |
| Q64 | used | 1;2;3;4 | 5-v | 1 | 4 |
| Q69 | excluded | 1;2;3;4 | 5-v | 1 | 4 |
| Q70 | excluded | 1;2;3;4 | 5-v | 1 | 4 |
| Q71 | excluded | 1;2;3;4 | 5-v | 1 | 4 |
| Q73 | used | 1;2;3;4 | 5-v | 1 | 4 |
| Q81 | used | 1;2;3;4 | 5-v | 1 | 4 |
| Q99 | used | 2;1;0 | identity | 0 | 2 |

Q69-Q71 are listed only to record that they are outside the headline trust composite. They are not in either composite in this check.

Saved-column check: max |recomputed unit - saved normalized| = 3.331e-16 on 3312 cells (saved column is a check only, not the estimator).

Unit score for a used item is `(raw - min) / (max - min)`. The 0-1 composite is the unweighted country mean of those unit scores, on the same items as the raw composite.

Within every non-trust mapped set, every used item has the same theoretical post-recode range, so the 0-1 map is a common affine transform and Spearman rank correlation is invariant. Trust is the only mapped composite that mixes ranges (Q57 on [0, 1]; Q58-Q64 and Q73 on [1, 4]).

## Associations

Spearman country-rank correlations. Intervals are reported for trust adapter-GPS only, as specified. Other arms present in the frozen file are in `unit_range_comparison.csv`.

| Dimension | Association | Raw rho | 0-1 rho | Raw 95% interval | 0-1 95% interval |
|---|---|---:|---:|---|---|
| trust | adapter-gps | 0.8000 | 0.8588 | [0.5462, 0.9277] | [0.6119, 0.9522] |
| trust | human-gps | 0.3912 | 0.4294 |  |  |
| trust | adapter-human | 0.3265 | 0.3676 |  |  |
| Q43 | adapter-gps | 0.0059 | 0.0059 |  |  |
| Q43 | human-gps | -0.5647 | -0.5647 |  |  |
| Q43 | adapter-human | 0.2941 | 0.2941 |  |  |
| Q50 | adapter-gps | 0.4353 | 0.4353 |  |  |
| Q50 | human-gps | 0.6206 | 0.6206 |  |  |
| Q50 | adapter-human | 0.2500 | 0.2500 |  |  |
| risktaking | adapter-gps | 0.5735 | 0.5735 |  |  |
| risktaking | human-gps | -0.1500 | -0.1500 |  |  |
| risktaking | adapter-human | 0.0000 | 0.0000 |  |  |
| posrecip | adapter-gps | 0.5676 | 0.5676 |  |  |
| posrecip | human-gps | 0.2500 | 0.2500 |  |  |
| posrecip | adapter-human | 0.3500 | 0.3500 |  |  |
| negrecip | adapter-gps | 0.0618 | 0.0618 |  |  |
| negrecip | human-gps | 0.2353 | 0.2353 |  |  |
| negrecip | adapter-human | 0.1647 | 0.1647 |  |  |
| altruism | adapter-gps | 0.2353 | 0.2353 |  |  |
| altruism | human-gps | -0.0971 | -0.0971 |  |  |
| altruism | adapter-human | 0.1147 | 0.1147 |  |  |

## Trust adapter-GPS materiality

- Raw: 0.800000 [0.546241, 0.927719]; rounded to two decimals: 0.80; excludes zero: True.
- 0-1: 0.858824 [0.611928, 0.952173]; rounded to two decimals: 0.86; excludes zero: True.
- Sign flip: False.
- Two-decimal move of 0.10 or more: False (absolute move of rounded estimates = 0.06).
- Interval changes whether it excludes zero: False.
- **Material: false.**
- No materiality flag fired. The 0-1 trust adapter-GPS estimate stays positive. The two-decimal point estimate moves from 0.80 to 0.86, a change of 0.06, which is below 0.10. Both intervals exclude zero.

Finite bootstrap draws: raw 2000/2000; unit 2000/2000.

## Files

- Script: `/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/unit_range/unit_range_check.py`
- Comparison: `/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/unit_range/unit_range_comparison.csv`
- This note: `/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/unit_range/UNIT_RANGE.md`

