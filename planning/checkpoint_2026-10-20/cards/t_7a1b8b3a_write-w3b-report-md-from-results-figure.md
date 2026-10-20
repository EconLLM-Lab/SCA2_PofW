# Write W3b_REPORT.md from results, figure and pre-registration

Card `t_7a1b8b3a`, board sca2-paper-b, assignee `writer`, status at export: todo
Created 2026-10-19 19:13 MST. Exported 2026-10-19 by the CP assembly card as a dated record, not status.

## Body

GOAL: Write a short, honest technical report at workbench/analysis/out/W3b_REPORT.md on the W3b principal-angle test. This is internal analysis documentation, not a paper section. Use a plain, precise register.

INPUTS (read only; copy numbers verbatim and do not compute or round beyond 3 to 4 significant figures):
- workbench/analysis/out/W3b_results.json
- workbench/analysis/out/W3b_per_pair.csv
- workbench/analysis/out/W3b_PREREG.md
- workbench/analysis/out/W3b_run.log
- workbench/analysis/out/W3b_figure.png

REQUIRED SECTIONS:
1. Question: what W3b tests. Do the subspaces of one-bit LoRA pairs overlap more than the null predicts?
2. Inputs: the actual counts of profiles, one-bit pairs and non-one-bit pairs; the input shas; the git commit.
3. Method: aggregation, tolerance, statistic, N_perm and seed, citing W3b_PREREG.md by section.
4. Deviations: copy any deviations from the results JSON, or state 'None'.
5. Per-pair table: pair, Hamming distance, aggregate overlap, smallest angle.
6. Null summary and p-value: null mean and SD, k/d, the observed statistic, and the one-sided p-value.
7. Pair-reuse dependence:
   - state explicitly that pairs share profiles and are NOT independent;
   - give the per-profile reuse counts;
   - give the LOPO statistic and p-value range;
   - give the degree-matched sensitivity result, or the reason it was not run.
8. Descriptive Hamming plot: describe it only, with no inference.
9. Limitations.
10. An explicit statement that this result is NOT a mechanism claim.
11. Reproduce: the exact single command from the results JSON.
12. Embed the figure, and cite the log file for the test and sha-verification evidence.

Do NOT claim that tests passed unless W3b_run.log shows it. Quote or reference the relevant log lines.

ACCEPTANCE:
- The file exists with all 12 sections.
- Every number matches W3b_results.json exactly.
- There is no causal or mechanistic language.
- The dependence caveat is present.
- Return the path.

## Runs


## Comments

