# WB7-W acceptance: how to read each view, clamped run, many-option headline

Card t_91b4bfea, branch `wb7-words` from `af11b21`. Spec edits that bind this card: WB7-0 triage (comment 149 on t_65abd013), E7, E9, E11, and the operator note delivered during the run.

## What changed
- `viewer/src/common.ts`: answer strip (many-option headline), details pop-up, `howto-c`, `howto-b`, `howto-a`, `howto-k`, `clamp`, new unused `groundTruth` key, glossary (5 new or changed entries), links "What is the clamped run?" at the purple tick, the clamped chip, the clamped checks and the MLP pop-up.
- `viewer/src/tab-c.ts`, `tab-a.ts`, `tab-b.ts`: labels and tooltips only (the "Log-odds by layer" chart, the clamped run button plus a "what is this?" link).
- `viewer/src/style.css`: seven lines for the strip layout and the headed pop-up sections.
- `viewer/GLOSSARY.md`, `plans/WB7_PARITY_ALLOWLIST.txt`.
- Not touched: `public/sca2/index.html` (no sentence contradicts the new headline: the story page speaks of the adapter-minus-base log-odds, which is still what the charts split), `sca2_data.json`, `build_deploy_bundle.py`, `data.ts`, `main.ts`, Cohort files, the landing footer.

## Headline rule (more than two answer codes)
1. Ordered item: "Average answer on the lo–hi scale: A x → B y (higher = ...)", then "Most likely answer: A ... → B ...".
2. Not ordered: "Most likely answer: A ... → B ...".
3. Second line, always: "The charts below split the log-odds of “j+” over “j−” (the two end answers): A a → B b, change d".
4. Warning when both end probabilities are below 1% in A or B. Second warning, naming both numbers and their directions, when the average answer (or the most likely code) and the end-answer log-odds move in opposite directions. No single arrow.
5. Two-answer items keep today's sentence (verified: wvs_Q57, four URLs, number tokens identical).

Which items are ordered (the export records `meta.response_type`, not "ordered"):
- recorded: `scale_1_10`: wvs_Q106, wvs_Q50, wvs_Q176.
- ASSUMED: `single_choice_4` with text labels at both ends: wvs_Q81 (the 4-code item; in this bundle it has four codes, not two).
- not ordered: `single_choice_3`: wvs_Q43, wvs_Q99.
- bank items: two codes, today's headline.

## Checks
See the card summary for the exit codes and paths. Evidence files are in `~/.hermes/cache/scratch/wb7/` (`parity.json`, `parity.log`, `pytest.log`, `words/*.png`, `words/*.txt`, `build_bundle.log`).
