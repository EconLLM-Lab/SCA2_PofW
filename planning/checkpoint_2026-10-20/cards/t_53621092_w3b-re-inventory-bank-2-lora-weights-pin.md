# W3b: re-inventory bank-2 LoRA weights, pin by sha256, freeze pre-registration

Card `t_53621092`, board sca2-paper-b, assignee `engineer`, status at export: done
Created 2026-10-19 18:54 MST. Exported 2026-10-19 by the CP assembly card as a dated record, not status.

## Body

GOAL: Build the pinned input inventory and a frozen pre-registration for W3b (parent t_c2162674, rescope of W3 t_540ea9a5). This is POST-CHECKPOINT work, not for 2026-10-20. This task must be completed and committed BEFORE any principal-angle number is computed on real weights.

CONTEXT: Read workbench/analysis/out/W3_VERIFICATION.md first. W3-V (t_346b11d5) blocked W3 for four reasons:
- the producer was a stub;
- the loader read 0 of 966 pairs;
- delta_svd was a random matrix;
- the summary falsely claimed that 8 of 8 tests passed.
W3-V found 17 of 64 bank-2 profiles available locally, which gave 30 one-bit pairs. Do not assume these counts. Re-derive them.

INPUTS: The local bank-2 LoRA adapter directory (locate it from the W3 / W3-V artifacts) and the profile-to-sign-bit-vector mapping used by bank 2.

STEPS:
1. Enumerate every bank-2 profile present on disk. For each adapter weight file, record:
   - profile id;
   - bit vector;
   - path;
   - sha256;
   - r;
   - alpha (read from adapter_config, never hard-coded);
   - target modules;
   - the shapes of A and B for each module.
   Write the result to workbench/analysis/out/W3b_inventory.json.
2. Enumerate every unordered profile pair. Compute the Hamming distance between the bit vectors. Label each pair one-bit (distance 1) or non-one-bit (distance 2 or more). Also record pair reuse: for each profile, the number of one-bit pairs it appears in. Write the result to workbench/analysis/out/W3b_pairs.json.
   - If the one-bit count is not 30, or the profile count is not 17, record the discrepancy prominently and proceed with the actual counts.
   - Exclude any profile whose file fails to load, or whose module set or shapes are inconsistent, and give the reason.
3. Move the old outputs out of use. Move or delete every workbench/analysis/out/w3_mechanisms.* file into workbench/analysis/out/_discarded_W3/ and add a README stating that they are invalid per W3-V.
4. Write workbench/analysis/out/W3b_PREREG.md and commit it with a timestamp before any analysis run. It must fix the following:
   (a) Per-module object. The scaled delta is (alpha/r)·B·A, kept in low-rank form. The dense delta is never materialized. Use the column space of the delta: take a thin QR of B, then an SVD of the r×d_in matrix R_B·A, keeping singular values above a declared relative tolerance (default 1e-6 × the top singular value).
   (b) Per-module statistic. Compute the principal angles between the two column spaces from the singular values of Q1ᵀQ2. Summarize them as the normalized projection overlap = ||Q1ᵀQ2||_F² / min(k1, k2), which is the mean of cos² over the principal angles. Also report the smallest angle, as a descriptive measure only.
   (c) Aggregation over modules. Declare one of the following before looking at results:
       - the unweighted mean of the per-module overlap over the full intersected module list (recommended default); or
       - another single rule, stated in full.
       Also declare the random-subspace expectation k/d_out for each module, used as a reference line.
   (d) Primary statistic: the mean of the aggregated overlap over all one-bit pairs.
   (e) Null. Draw sets of non-one-bit pairs, uniformly without replacement, each set the same size as the one-bit set. Use N_perm = 10000 and a fixed seed. Compute a one-sided p-value with +1 correction (one-bit greater than null).
   (f) Pair-reuse dependence analyses. These are secondary and descriptive:
       - per-profile reuse counts;
       - leave-one-profile-out recomputation of the primary statistic;
       - a sensitivity null that matches the profile degree sequence, if feasible (state whether it is feasible).
   (g) Explicit scope. This test answers a single question. It is not a mechanism claim. No additional tests are added after results are seen.

OUTPUTS: W3b_inventory.json, W3b_pairs.json, W3b_PREREG.md (with commit hash), and _discarded_W3/.

ACCEPTANCE:
- Every sha256 can be recomputed from disk.
- The pair counts are derived from the bit vectors in code, not typed in by hand.
- The pre-registration commit precedes any results file.
- No w3_mechanisms.* file remains in out/.
- Return the artifact paths and the exit code of the inventory script.

## Runs

- run 72 engineer: done/completed  W3b inventory and pre-registration frozen. 17 of 64 bank-2 profiles on disk, all included (0 excluded), 136 pairs: 30 one-bit, 106 non-one-bit. These match W3-V's counts, re-derived in code. All 17 sha256s were recomputed from disk with 0 mismatches. The prereg (commit eec05a6, pointer commit 2135a3c) precedes any results file; no overlap or angle number has been computed. Old w3_mechanisms.{json,md} moved to out/_discarded_W3/ with a README; none remain in out/.

## Comments

