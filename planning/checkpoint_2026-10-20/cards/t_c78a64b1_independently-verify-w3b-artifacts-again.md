# Independently verify W3b artifacts against acceptance criteria

Card `t_c78a64b1`, board sca2-paper-b, assignee `verifier`, status at export: todo
Created 2026-10-19 19:13 MST. Exported 2026-10-19 by the CP assembly card as a dated record, not status.

## Body

GOAL: Independently verify the W3b run outputs. You may BLOCK. Every finding must cite evidence: file path, line or key, and the command output.

ARTIFACTS (in workbench/analysis/out/):
- W3b_results.json
- W3b_per_pair.csv
- W3b_figure.png
- W3b_figure.pdf
- W3b_REPORT.md
- W3b_run.log

REFERENCE: W3b_PREREG.md, W3b_inventory.json and W3b_pairs.json in the same directory.

CHECKS:
1. Run sha256 on every adapter listed in the inventory and compare against both the inventory and the shas recorded in the results.
2. Confirm that the sha of W3b_PREREG.md matches the one recorded in the results, i.e. it was not modified. Confirm that the aggregation, tolerance, statistic, N_perm and seed used match the pre-registration, and that every deviation is documented and also has a pre-registered result.
3. Confirm the log shows the pytest suite passing before the analysis ran.
4. Confirm that the pairs in the results equal W3b_pairs.json: same count, and all pairs present, both one-bit and non-one-bit.
5. Recompute the primary statistic from the per-pair rows. Recompute the p-value from the null samples, using the pre-registered one-sided definition. Both must match.
6. Run the documented single reproduce command in a clean checkout at the recorded commit. Confirm that it exits 0 and reproduces the primary statistic and p-value bit-for-bit, or within the stated tolerance.
7. Confirm the figure files exist and have panels A to D with the required markers (observed mean and k/d in panel A).
8. Check that every number in the report matches the JSON. Check that the report contains the non-independence caveat and the explicit NOT-a-mechanism-claim statement, and makes no unsupported claim that tests passed.

OUTPUT:
- workbench/analysis/out/W3b_VERIFICATION.md, containing PASS/BLOCK per check with evidence, and an overall verdict.
- Return the path, the verdict and the captured exit code of the reproduce run.

## Runs


## Comments

