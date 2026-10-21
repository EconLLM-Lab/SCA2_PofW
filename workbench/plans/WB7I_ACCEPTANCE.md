# WB7-I acceptance: v1.5 candidate (integration of WB7-Q, WB7-H, WB7-W). Not deployed.

Branch Adapter-Brain-Vizualization. Code head at build time: 0bc4772 (merge b774e97 of wb7-words, then 429c062 integration fixes, then 0bc4772 story footer). The acceptance commit follows it and changes only this file.

## Decision: human layer is IN the deploy candidate
Augusto confirmed "ship human layer" on 2026-10-21. dist/deploy_bundle.tar.gz is built with --human-reference. human_reference.json is gitignored and never committed; the tarball is gitignored.

## Build and verify
| Mode | Files | Payload bytes (cap 950,000,000) | Archive sha256 | verify_bundle | v1.4 identity |
|---|---|---|---|---|---|
| WITH human layer (dist/, candidate) | 376 | 949,436,898 | d46cc98436a7a4da483cecd8bc250218977f70e1be64fe2f73b29146a6057481 | pass, human_reference_cells 56 | exit 0, 0 violations |
| Panel OFF (scratch, not deployed) | 375 | 949,428,139 | a7c806d7ee1c8dd939255ee7b5d03116f19f6c8b2c5252e42e1906aa3479a24c | pass, human_reference_cells null | exit 0, 0 violations |

Also: tsc exit 0; suite (HF_TOKEN blank) 201 passed, 4 skipped.

## Independent recompute (ASU seat)
A script written in this card (scratch, recompute_human.py) recomputes every cell of human_reference.json from the local WVS-7 .dta (weights W_WEIGHT, valid codes only): 56 cells checked, 0 mismatches (shares, n, top answer, mean presence and value, ordered flags).

## Decisions
- Ordered items (carry a survey mean, compared on the expected answer): Q50, Q106, Q176, Q81 (assumed ordered, as in WB7-W).
- Unordered items Q43 and Q99: the panel compares the named answer's share (two-answer rule on the shown answer); no mean is written. UNORDERED_ITEMS in build_human_reference.py enforces it, with a test.
- The groundTruth pop-up states the rule actually on screen (one marker, both gaps shown); the TVD bullet was removed (E5). Marker text carries both gaps (PM edit in human.ts).
- Cohort axis title now: "Probability each model gives this answer · share of respondents who chose it (pink)".
- Attribution added word for word from WB7_DATA_RIGHTS.md: SPACE_README.md, landing footer, story-page footer (viewer/public/sca2/index.html): Built with Llama, WVS-7 citation, both GPS citations with CC BY-NC-SA 4.0.

## Parity vs v1.4 (7b3a563), 33 parity URLs, WITH human layer, local range servers (stopped afterwards)
0 page errors. Explained differences against the WB7-W allow-list:
- Tokens only in v1.4 appear on one URL, /?tab=k (Cohort). Cause: WB7-Q rebuilt the Cohort for 68 comparators (default view, matched-pair layout, question-picker chips); it was accepted in WB7-Q with its own parity table. Not a WB7-W or WB7-H change.
- Landing page and every page with the footer or help: new tokens from the attribution citations (years, DOI, page numbers, "3.1", "4.0").
- Every comparator page with a human cell: new tokens from the survey panel (WVS "7", survey share, expected/mean, two gaps). Compared with the WB7-W-only build, nothing was removed anywhere and every added token is a survey figure or a gap.
- Items with more than two codes: headline changes per the allow-list (WB7-W).
- Identical to v1.4: the two sign-prompt Q57 pages (no country, so no survey cell).
Human-layer numbers are checked against the file by the WB7-H screen-number check (656/656 on, run at WB7-H) and by the recompute above.
Note: the story page (sca2/index.html) still says "no human means or distributions" in its intro. The workbench now shows survey shares; WB7-V should decide if that sentence needs an edit.

## Screenshots (own look), ~/.hermes/cache/scratch/wb7/final/
q57-china-ladder.png, q57-cohort.png (Q57), q176-usa-ladder.png checked: no clipping, question wording and axis title above the profile blocks, pink survey tick visible, markers read "closer to the survey than the base model (35 vs 38 percentage points)" (China Q57) and "further from the survey than the base model (0.7 vs 0.1 points from the survey mean)" (USA Q176).
Not retaken in this retry (done in earlier runs or by WB7-H/WB7-Q): landing, light-comparator 3D tab, details pop-up. WB7-V should look at those.
Residual minor: Cohort axis ticks sit above the explainer paragraph, a little away from the first block (cosmetic).
