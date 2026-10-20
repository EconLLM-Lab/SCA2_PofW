# W3b-V: independently verify W3b results are real, pre-registered, stub-proof

Card `t_98c738f5`, board sca2-paper-b, assignee `verifier`, status at export: todo
Created 2026-10-19 18:54 MST. Exported 2026-10-19 by the CP assembly card as a dated record, not status.

## Body

GOAL: Independently verify the W3b artifact (parent t_c2162674). You may BLOCK it. Every finding must cite evidence: a file path, a line, a command and its output. This task is the successor check to W3-V (t_346b11d5), which blocked W3 for four reasons:
- the producer was a stub;
- the loader read 0 of 966 pairs;
- delta_svd was random;
- the summary falsely claimed that 8 of 8 tests passed.

ARTIFACTS:
- workbench/analysis/w3b/, including the code, the tests and tests/run_with_stub.sh;
- workbench/analysis/out/W3b_inventory.json, W3b_pairs.json, W3b_PREREG.md, W3b_results.json, W3b_per_pair.csv, W3b_figure.png and .pdf, W3b_REPORT.md, W3b_tests.log and W3b_run.log;
- workbench/analysis/out/_discarded_W3/.

ACCEPTANCE CRITERION TO CHECK: The artifact must contain real numbers, produced by a test that fails on a random-matrix stub, plus a figure. The scope is one test only, and the artifact must make no mechanism claim.

CHECKS:
1. Recompute sha256 for a sample of at least 5 adapters, and for all of them if that is cheap. Confirm that the values match the inventory and the results.
2. Re-derive the one-bit pair list independently from the bit vectors. Confirm the pair count and the per-profile reuse counts.
3. Run pytest yourself and record the exit code. Run tests/run_with_stub.sh and confirm that it exits non-zero. Inspect the tests: confirm that they would actually catch a random or stub substitution and are not tautological.
4. Independently recompute the aggregate overlap for at least 2 one-bit pairs and 2 non-one-bit pairs, using your own minimal code: QR of B, then SVD of R·A, then Q1ᵀQ2. Confirm that the values match W3b_results.json within 1e-6.
5. Confirm that the pre-registration commit timestamp precedes the results files. Confirm that the aggregation, null, N_perm and seed used match the pre-registration, or that any deviations are disclosed.
6. Recompute the p-value from the stored null samples.
7. Confirm that no dense d_out×d_in delta is materialized, by code inspection.
8. Confirm that the figure exists and matches the numbers.
9. Confirm that no w3_mechanisms.* file remains in active out/.
10. Confirm that the report makes no mechanism claim and handles pair-reuse dependence honestly.

OUTPUT: workbench/analysis/out/W3b_VERIFICATION.md. It must give a verdict of PASS or BLOCK, a numbered list of findings each with evidence, and the commands you ran with their exit codes.

## Runs


## Comments

