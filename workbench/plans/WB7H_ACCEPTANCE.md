# WB7-H acceptance: descriptive human reference (WVS-7 country shares) next to the model

Card t_63edca34. Branch `Adapter-Brain-Vizualization` (on top of WB7-Q 624a635). Route: claude-sonnet-5-5 via anthropic (ASU seat).
Status: built and checked, **off by default**. Nothing with human figures is committed, uploaded or pushed. Augusto's written confirmation of WB7-R item 3 is still open (PM comment, E3/E6).

## What was built

| Piece | File | Notes |
|---|---|---|
| Data script | `scripts/build_human_reference.py` | stdlib only; reads the Paper A/B weighted table, writes `human_ref/human_reference.json` (gitignored: `workbench/human_ref/`). `--index` = built bundle's `exports/index.json`. `--crosscheck` recomputes cells from `WVS_wave7.dta` (needs pandas: run with the main repo `.venv`). |
| Builder | `scripts/build_deploy_bundle.py` | `--human-reference <path>`, off by default. Validates the file (schema, no extra keys, n >= 100), counts it before the byte budget, ships it as `exports/human_reference.json`, records `human_reference` in the manifest. |
| Verifier | `viewer/screens/sca2/verify_bundle.py` | accepts both modes; with the file: schema, source, item has a run, keys limited to `n shares top mean`, n >= 100, integer shares. Reports `human_reference_cells`. |
| Viewer | `viewer/src/human.ts` (new), hooks in `tab-c.ts` (3 lines), `tab-k.ts`, `cohort-model.ts` (`export` on `COUNTRY`), `style.css` | `common.ts` is untouched (merge with `wb7-words` stays clean). |
| Tests | `tests/test_human_reference.py` | synthetic numbers only; both bundle modes, verify in both modes, drop rules, held-out drop, fail-closed freeze, bad-file rejects, real held-out pool check. |
| Screen check | `scripts_verify/check_human_numbers.mjs` | serves an extracted bundle, drives headless Chrome, compares every human number on screen with `human_reference.json`. |

## Results

| Check | Result |
|---|---|
| `tsc --noEmit` | exit 0 |
| `pytest tests` | exit 0, 201 passed, 4 skipped (WB7-Q: 191/4; +10 new) |
| Builder + `verify_bundle.py`, **flag off** | exit 0 / exit 0, `pass: true`, 375 files, payload 949,404,238 B = 0.9494 GB, `human_reference_cells: null` |
| Builder + `verify_bundle.py`, **flag on** | exit 0 / exit 0, `pass: true`, 376 files, payload 949,413,858 B = 0.9494 GB (cap 950,000,000), `human_reference_cells: 56`. The file costs 9,620 B; the light-run allocation is unchanged. |
| v1.4 identity (`check_bundle_identity.py`) | exit 0 in both modes: 143 checked, 138 identical, same 5 allowed changes, 0 violations |
| Screen numbers vs file, flag on | **656 checks, 0 failed**: 56 Ladder pages (every wvs_ adapter pair shipped), 5 Cohort questions (68 + 4 + 8 + 4 + 4 rows), `sort=survey` order, legend, column header |
| Flag off | **129 checks, 0 failed**: Ladder line stays hidden, no tick, no column, no legend entry, no "Closer to the survey" sort, no console or page error; the only failed request is the missing file itself |
| Cross-check against `WVS_wave7.dta` (weighted, `W_WEIGHT`, answer in the item's codes) | 16 cells (first 3 countries of each item, sorted by code), shares, n and mean: 0 differ |

What the screen check compares: Ladder headline numbers, every cell of the all-answers table, each Cohort tick position (`left:` = the file's share of the named answer), each yes/no marker (recomputed from `index.json` probabilities with the stated rule), and the share quoted in each row's tooltip. Respondent rows are never read or printed.

## Held-out check (Paper B pool)

`build_human_reference.py` calls `freeze.require_freeze(paper_b/heldout/FREEZE.json)` and reads only the pool's question ids (`pool_skeleton.csv`, 223 ids) and the frozen selection's ids (`selection_amended_20261016.csv`). Q43, Q50, Q57, Q81, Q99, Q106, Q176: **none is in the pool or the selection**. No item dropped. `test_no_shipped_item_is_in_the_real_heldout_pool` also checks every `wvs_` item in `exports/index.json`, so a later shipped item fails the suite if it enters the pool.

## n < 100 drop list

**Empty.** The smallest cell has n = 931 (all 56 cells are above 100). The drop logic is tested with a synthetic n = 40 cell. Items with no shipped adapter run would be listed under `dropped_items`; none occurred (the bundle ships adapters for all seven).

Coverage: Q57 42 countries; Q99 4; Q43, Q50, Q81, Q106, Q176 2 each (the countries with a shipped adapter run). A country with an adapter run and no cell renders "no survey data".

## Display rules, as built

- Ladder, country adapter B on a `wvs_` item: tag "Survey, descriptive", then "In the World Values Survey (wave 7), 64% of respondents in China chose “Most people can be trusted”. The model gives it a probability of 26% (base model) and 99% (China adapter)." plus the marker "closer to the survey than the base model" or "further from …", and a collapsible table of every answer (respondents, base model, adapter, n and the source line).
- Questions with 3+ answers: "respondents in X chose “…” most often (N%); their mean answer was M. The model's expected answer is E (base model) and F (adapter)."
- Cohort, adapter rows only: a pink tick on the probability axis at the survey share of the named answer; legend "people in that country (WVS-7)"; column "closer to survey than base?" (yes / no / "no survey data"; sign prompts show "–"); sort "Closer to the survey". No tick on sign-prompt rows.
- Fixed rule (stated in the tooltip): 2 answers compare the probability of the named answer with the survey share; 3+ answers compare the expected answer with the survey mean. Smaller gap wins. Ties read "no" in the Cohort and "as far from the survey as the base model" in the Ladder.
- No aggregate across countries or items is drawn (the "N of 42 adapters" line is dropped, PM E5.2). No Paper B statistic on screen. Banned words (accuracy, validation, correct, TVD, Spearman, total variation) are scanned in the human elements and row labels: none.
- Tooltip: "Descriptive comparison, not a Paper B result."

Screenshots (scratch, pruned after about 24 h): `~/.hermes/cache/scratch/wb7/human/`: `ladder-on-CHN-1440.png`, `ladder-on-BGD-1440.png`, `cohort-on-q57-1440.png`, `cohort-on-survey-sort-1440.png`, and the same four for `-off-` (no human element).

## Open items for the PM (conflicts surfaced, not resolved)

1. **WB7-W's `groundTruth` text (branch `wb7-words`, `common.ts:534`) conflicts with the display rules.** It says two summary numbers can appear, one of them the "total variation distance". PM E5 and this card forbid any Paper B statistic on screen. It also says "Each set adds to 100%" (whole-percent rounding may give 99 or 101) and "no data", where the rule is "no survey data". It does not state the closer/further rule that E5.3 wants in the help text. Fix the text on `wb7-words` before the merge; I did not edit it.
2. The "how to read this" button appears only when `learnText(D, "groundTruth")` exists, so before the merge there is no button and after it the WB7-W pop-up opens. I did not write a details-pop-up section of my own (PM E5.6 overrides the card's step 3). The "not a Paper B result" wording lives in tooltips.
3. The Ladder human line ignores the clamped run (it uses the unclamped probabilities).
4. A tied marker reads "no" in the Cohort column (yes/no was the spec). It never occurs in the shipped data.
5. Shipping needs Augusto's written confirmation of WB7-R (item 3, with the WVS-7 citation shown and emailed to the WVSA Secretariat) and the "Built with Llama" line. This build shows no WVS citation on screen; the source line is in the all-answers panel only.
6. The `check_human_numbers.mjs` run needs an extracted bundle: `node scripts_verify/check_human_numbers.mjs <extracted> on|off <shots> [human_reference.json]`.
