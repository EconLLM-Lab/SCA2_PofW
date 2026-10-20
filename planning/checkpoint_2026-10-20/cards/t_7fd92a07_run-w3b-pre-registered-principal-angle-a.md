# Run W3b pre-registered principal-angle analysis on real bank-2 adapters

Card `t_7fd92a07`, board sca2-paper-b, assignee `engineer`, status at export: running
Created 2026-10-19 19:13 MST. Exported 2026-10-19 by the CP assembly card as a dated record, not status.

## Body

GOAL: Run the pre-registered W3b principal-angle test on the real bank-2 LoRA adapter weights. Produce machine-readable results. This is POST-CHECKPOINT work (parent t_c2162674), not for 2026-10-20.

PROJECT ROOT: workbench/analysis/ (code lives in workbench/analysis/w3b/).

INPUTS:
- workbench/analysis/out/W3b_inventory.json (pins the sha256 of each adapter)
- workbench/analysis/out/W3b_pairs.json
- workbench/analysis/out/W3b_PREREG.md (BINDING; read it fully before running)
- the existing code and tests in workbench/analysis/w3b/

STEPS:
1. Run the pytest suite for workbench/analysis/w3b/. Tee the full output into W3b_run.log. If any test fails, ABORT: write nothing else and return the nonzero exit code plus the log path.
2. Load every inventoried adapter with load_adapter, with sha verification enabled. If any sha mismatches, abort. For each profile, log: path, sha256, module count, r and alpha.
3. For EVERY pair in W3b_pairs.json (one-bit and non-one-bit), compute:
   - the aggregate overlap;
   - the smallest principal angle;
   - the per-module overlaps.
   Use exactly the aggregation, tolerance and statistic declared in W3b_PREREG.md. Do NOT edit the pre-registration. If a deviation is unavoidable:
   - record it in a 'deviations' array in the results, with the reason;
   - still compute and report the pre-registered result alongside it.
4. Compute the primary statistic, which is the mean aggregate overlap over the one-bit pairs. Then compute the permutation null using the pre-registered N_perm and seed, keeping all null samples. Then compute the one-sided p-value.
5. Run the pair-reuse analyses:
   - per-profile reuse counts (how many one-bit pairs each profile appears in);
   - the leave-one-profile-out primary statistic and p-value for each profile, plus their range;
   - the degree-matched sensitivity null, ONLY if the pre-registration declares it feasible. Otherwise record it as not run, with the pre-registration's reason.
6. As a descriptive measure only (not inferential), compute aggregate overlap against Hamming distance for all pairs.
7. Record the random-subspace expectation k/d, as defined in the pre-registration, for use by the figure.

OUTPUTS (all in workbench/analysis/out/):
- W3b_results.json containing:
  - per-pair rows: pair ids, Hamming distance, one_bit flag, aggregate overlap, smallest angle, per-module overlaps;
  - the primary statistic;
  - the full null samples array, plus N_perm and seed;
  - the p-value;
  - the reuse analyses (counts, LOPO table, LOPO range, degree-matched result or not-run reason);
  - the k/d expectation;
  - the hamming-vs-overlap data;
  - the input file sha256s (inventory, pairs, prereg, and each adapter);
  - the git commit hash;
  - the deviations array (empty if none);
  - the exact command used.
- W3b_per_pair.csv, with one row per pair and the same per-pair fields (per-module overlaps as columns or a serialized field).
- W3b_run.log, holding the pytest output, the adapter load log, progress, and the final summary.
- A single entry-point command that reproduces everything, e.g. `python -m w3b.run_w3b --out workbench/analysis/out` or a make target. Commit any new runner script.

ACCEPTANCE:
- Tests passed, as shown in the log.
- Every adapter sha matches the inventory.
- All numbers come from the real weights.
- The pre-registration file is unmodified (its sha is recorded).
- The results JSON contains every field listed above.
- Return the artifact paths, the reproduce command and the captured exit code.

## Runs

- run 77 engineer: running/None  

## Comments

