# W3b: run principal-angle test on real one-bit pairs vs null, produce figure

Card `t_221883a2`, board sca2-paper-b, assignee `engineer`, status at export: todo
Created 2026-10-19 18:54 MST. Exported 2026-10-19 by the CP assembly card as a dated record, not status.

## Body

GOAL: Execute the pre-registered W3b test on the real bank-2 LoRA weights and produce the results and a figure (parent t_c2162674). This is POST-CHECKPOINT work, not for 2026-10-20.

INPUTS (from prior tasks):
- workbench/analysis/out/W3b_inventory.json, which pins the sha256 of each adapter;
- workbench/analysis/out/W3b_pairs.json;
- workbench/analysis/out/W3b_PREREG.md, which is binding;
- the code in workbench/analysis/w3b/, with its tests passing.

STEPS:
1. Run the pytest suite first and abort if it fails.
2. Load every inventoried adapter through load_adapter with sha verification. Log, for each profile: path, sha, module count, r and alpha.
3. Compute the aggregated overlap and the per-module values for EVERY pair, both one-bit and non-one-bit. Use exactly the aggregation, tolerance and statistic declared in W3b_PREREG.md. Do not alter the pre-registration. If a deviation is unavoidable, record it in a DEVIATIONS section with the reason, and also report the pre-registered result.
4. Compute the primary statistic, the mean over one-bit pairs. Compute the permutation null with the pre-registered N_perm and seed, and the one-sided p-value.
5. Run the pair-reuse analyses:
   - per-profile reuse counts;
   - the leave-one-profile-out primary statistic and p-value range;
   - the degree-matched sensitivity null, if the pre-registration declared it feasible.
6. As a descriptive measure only, compute the overlap against Hamming distance for all pairs.

OUTPUTS in workbench/analysis/out/:
- W3b_results.json. This must contain:
  - the per-pair rows (pair, Hamming distance, aggregate overlap, smallest angle, per-module overlaps);
  - the primary statistic and the full null samples;
  - the p-value and the reuse analyses;
  - the input shas and the git commit hash.
- W3b_per_pair.csv.
- W3b_figure.png and W3b_figure.pdf. Panels:
  - (A) A histogram of the null distribution with the observed one-bit mean marked and the random-subspace expectation k/d marked.
  - (B) A strip or dot plot of each one-bit pair's aggregate overlap next to the non-one-bit pairs.
  - (C) The leave-one-profile-out statistics.
  - (D) A descriptive plot of overlap against Hamming distance.
- W3b_REPORT.md. A short report covering:
  - the question;
  - the inputs, with their counts (actual one-bit pairs and profiles);
  - the method, citing the pre-registration;
  - the per-pair table;
  - the null summary and p-value;
  - the pair-reuse dependence, stated honestly (pairs share profiles and are not independent);
  - the limitations;
  - an explicit statement that this is NOT a mechanism claim.
  Do not claim that tests pass without the attached logs.
- W3b_run.log.

ACCEPTANCE:
- All numbers come from real weights whose shas match the inventory.
- The run is reproducible from a single command, documented in the report.
- The figure exists.
- The exit code is captured and returned along with the artifact paths.

## Runs

- run 75 engineer: blocked/blocked  PM hold. W3b is post-checkpoint, and the auto-decomposer started it anyway. It is also not ready to run: t_79a93b3e reports that W3b_PREREG.md does not exist even though t_53621092 says the pre-registration is frozen, the aggregation rule defaulted to the unweighted mean, and rel_tol is unresolved. Those choices must be frozen before any real angles are computed. Resume after the 08:00 checkpoint, once the PM has reconciled the prereg.
- run 76 engineer: blocked/blocked  The PM hold is still in force: W3b is post-checkpoint work, and the PM said it will unblock this card after the 08:00 checkpoint. The card was re-promoted to todo with no author and no PM comment. The Mac is also loaded (load average 13 to 14 at 19:12, with W2 nf4_t4 and a paper_b pytest run active). Nothing was run and no results were written. Unblock only after the checkpoint. Run with rel_tol=1e-6 passed explicitly, N_perm 10000, seeds 20261019 and 20261020.

## Comments

### engineer 2026-10-19 19:09

From W3b prereg (t_53621092), frozen in commit eec05a6 (pointer 2135a3c) on branch Adapter-Brain-Vizualization: analysis/w3b/core.py has DEFAULT_REL_TOL = 1e-8, but the prereg fixes rel_tol = 1e-6. Pass rel_tol=1e-6 explicitly, or change the default and log it as a deviation. Other constants: N_perm 10000, seeds 20261019 (primary) / 20261020 (degree-matched), 128 modules, 30 one-bit / 106 non-one-bit pairs. Inputs: out/W3b_inventory.json and out/W3b_pairs.json. alpha comes from run_record.json (no adapter_config.json exists for bank-2 profiles).

### default 2026-10-19 19:10

PM correction, 19:15: my block reason (2) was stale. The module card (19:00) ran before the prereg card (19:09). W3b_PREREG.md now exists, committed locally at eec05a6 + 2135a3c (not pushed). It fixes rel_tol = 1e-6 and declares the unweighted mean over 128 modules as the aggregation rule, plus a degree-matched sensitivity null. Both of my concerns are resolved. The hold stays for one reason only: scope and CPU. W2 must finish by ~05:00 on the same Mac, and its first abort was caused by load. I will unblock t_221883a2 after the 08:00 checkpoint; it must use the prereg constants exactly.

### engineer 2026-10-19 19:12

engineer, run 76, 19:12 MST: I did not start W3b. Three reasons. (1) The PM comment (about 19:15 by task time) keeps the hold until after the 08:00 checkpoint and says the PM will unblock this card. I see no unblock comment from the PM. The status flip to todo at 1792462330 has no author and no comment, and it looks like an automatic re-promotion. (2) The card body says POST-CHECKPOINT, not for 2026-10-20. (3) The Mac is loaded now: load average is 13 to 14, with the W2 nf4_t4 unit.py run and a paper_b pytest run both active. The PM named CPU contention with W2 as the reason W2 aborted earlier. No pytest, no adapter loading and no angle computation has been run, and no results files were written. Prereg constants are ready for the resumed run: rel_tol=1e-6 passed explicitly (core.py default is 1e-8), N_perm=10000, seeds 20261019 (primary) and 20261020 (degree-matched), 128 modules, 30 one-bit and 106 non-one-bit pairs, unweighted mean over modules. Please unblock only after the checkpoint.

### default 2026-10-19 19:13

PM, 19:14: board automation moved this card back to todo at 19:12, overriding my hold, and it is running again. I will let it run instead of fighting the automation: the CPU risk is small (W2 units take ~32 s against a 260 s limit). Hard constraints for this run: (1) at most 2 CPU threads (OMP/MKL/torch set_num_threads=2); W2 shares this Mac until ~05:00. (2) Use the W3b_PREREG.md constants exactly (rel_tol 1e-6, unweighted 128-module mean, N_perm 10000, seeds 20261019/20261020); add no test, subset or threshold after you see results. (3) Do NOT edit workbench/src/, pyproject.toml, uv.lock or plans/gpu_cohort/; those would break the W2 resume digest. (4) Exploratory/SCA3 only. Not in the checkpoint brief unless W3b-V (t_98c738f5) passes. No push.

### auto-decomposer 2026-10-19 19:13

Decomposed into t_7fd92a07, t_171a74ce, t_7a1b8b3a, t_c78a64b1. Root will wake when all children complete.

