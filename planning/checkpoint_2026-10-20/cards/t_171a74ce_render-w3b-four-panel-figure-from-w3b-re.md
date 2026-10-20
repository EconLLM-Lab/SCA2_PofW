# Render W3b four-panel figure from W3b_results.json

Card `t_171a74ce`, board sca2-paper-b, assignee `engineer`, status at export: todo
Created 2026-10-19 19:13 MST. Exported 2026-10-19 by the CP assembly card as a dated record, not status.

## Body

GOAL: Produce the W3b figure as both PNG and PDF, built strictly from workbench/analysis/out/W3b_results.json. Do not recompute any statistics from the weights.

PROJECT ROOT: workbench/analysis/. Add a plotting script, e.g. w3b/plot_w3b.py, and hook it into the same single reproduce command used for the analysis if one exists.

INPUTS:
- workbench/analysis/out/W3b_results.json
- workbench/analysis/out/W3b_per_pair.csv

PANELS:
- (A) A histogram of the full permutation null samples, with:
  - a vertical line marking the observed one-bit mean (primary statistic);
  - a vertical line marking the random-subspace expectation k/d;
  - the p-value annotated.
- (B) A strip or dot plot of the aggregate overlap for each one-bit pair, shown next to the non-one-bit pairs, with jitter. Label one-bit pairs where legible.
- (C) The leave-one-profile-out primary statistic for each dropped profile, with the full-data statistic shown as a reference line. Annotate the LOPO p-values or their range.
- (D) A descriptive scatter of aggregate overlap against Hamming distance for all pairs. The title or caption must mark it as descriptive and non-inferential.

OUTPUTS:
- workbench/analysis/out/W3b_figure.png (at least 200 dpi)
- workbench/analysis/out/W3b_figure.pdf
- Append the plotting step's output to workbench/analysis/out/W3b_run.log.

ACCEPTANCE:
- Both files exist and contain all four labeled panels A to D.
- Every plotted value traces to W3b_results.json.
- Axes are labeled.
- The script runs non-interactively.
- Return the artifact paths and the captured exit code.

## Runs


## Comments

