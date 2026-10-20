# W3b pre-registration (FROZEN at commit; see W3b_PREREG_COMMIT.txt for the commit hash)

Task t_53621092 (parent t_c2162674; rescope of W3 t_540ea9a5). Written 2026-10-19 19:08 MST (2026-10-20T02:07Z).
Author route: claude-sonnet-5-5 (anthropic), profile engineer.
Status: written and committed BEFORE any principal-angle, overlap or other subspace number has been
computed on the real bank-2 weights. Any change after this commit is a dated DEVIATION appended at the bottom,
never an edit above.

## 0. The single question

Do the column spaces of the scaled LoRA deltas of two bank-2 sign profiles that differ in exactly one sign bit
overlap more, on average, than those of two profiles that differ in two or more bits?

That is the whole test. It is NOT a mechanism claim (section 7).

## 1. Pinned inputs (derived by w3b_inventory.py, exit 0; nothing typed by hand)

  Script:     workbench/analysis/w3b_inventory.py          sha256 bfb782f9517afff51ccf7f8f6ee901f09155f87b98a09d43f047016980ec0fdf
  Inventory:  workbench/analysis/out/W3b_inventory.json    sha256 293bcd82b57c0cbc8f6a2990ebfab3c398bd96ea51de4122b97262bdf16570c1
  Pairs:      workbench/analysis/out/W3b_pairs.json        sha256 5b2bd048b4f3067ac7f13cf9d1325bb3bc9286b910f55db22a945f45fd348986
  Weights:    ~/.cache/huggingface/hub/datasets--Bonorinoa--SCA2-paper-b-adapters/snapshots/9d75cb7e467975dbca840a05622c5aa0171c015e/
              bank2/gps_sign_relabel_bank2_20261015_062543Z/profiles/<P_id>/adapter_model.safetensors
              (per-file sha256 in W3b_inventory.json; all 17 recomputed from disk with 0 mismatches; for all 17 the
              sha256 also equals the HF cache blob name, an independent check)

Derived counts (re-derived, they agree with W3-V; no discrepancy):
  profiles on disk with weights   17 of 64 (17 candidates, 17 included, 0 excluded: all load, all finite, identical module set and shapes)
  unordered pairs                 136
  one-bit pairs (Hamming 1)       30
  non-one-bit pairs (Hamming >=2) 106   (Hamming histogram: 1:30, 2:49, 3:41, 4:15, 5:1)
  modules (intersection)          128 = 32 layers x {q_proj, k_proj, v_proj, o_proj}; q,o: B 4096x16, A 16x4096; k,v: B 1024x16, A 16x4096
  r = 16 (from A shapes, equals declared); alpha = 32; alpha/r = 2.0 for all 17
  One-bit degree sequence (reuse) [5,4,4,4,4,4,4,4,4,4,4,4,3,3,3,1,1]; per-profile counts in W3b_pairs.json
  One-bit pairs by differing bit (order trust, risktaking, patience, altruism, posrecip, negrecip): 7, 0, 2, 7, 7, 7
Bit vectors come from the profile id P_<b1>_..._<b6> (same rule as paper_b/factorial.py::bits_of_unit).

Conflicts between task text and disk, surfaced and not silently resolved:
  (i)  The task says alpha is read from adapter_config. adapter_config.json does not exist in any bank-2 profile
       directory. alpha and r are read from each profile's run_record.json["lora"], and r is cross-checked against the
       A shapes. If adapter_config.json is ever supplied it takes precedence (the script already does this).
  (ii) analysis/w3b/core.py (a sibling task's code, tested only on planted synthetic subspaces, no real-weight run
       exists) has DEFAULT_REL_TOL = 1e-8. This pre-registration fixes 1e-6 (section 2). The analysis must pass
       rel_tol=1e-6 explicitly.
Known limits of the pool (descriptive, not corrected for): b_risktaking is 0 in all 17 profiles, so no one-bit pair varies
that bit and nothing here speaks to it; the 17 are a convenience subset of the 64 that happens to be on disk (not a
random sample); no same-profile replicate weights exist locally (902f262e replicates/ holds run_record.json only), so
a seed-to-seed noise floor cannot be estimated and is NOT part of this test.

## 2. Per-module object

For profile p and module m: delta = (alpha_p / r_p) * B_p A_p, kept in low-rank form. The dense d_out x d_in delta is never
formed. All arithmetic in float64 (weights cast from float32 on load). The positive scalar alpha/r does not change a column
space; it is recorded for completeness.
  1. B = Q_B R_B, thin QR (Q_B d_out x r, R_B r x r).
  2. SVD of the r x d_in matrix M = R_B A = U S V^T.
  3. k = number of singular values S_i > rel_tol * S_0, rel_tol = 1e-6 (fixed).
  4. Orthonormal basis of the column space: Q = Q_B U[:, :k].
If S_0 = 0 (delta is exactly zero) k = 0 and the module is dropped for every pair containing that profile; the number
dropped is reported. Expected: none.

## 3. Per-module statistic

For two profiles with bases Q1 (d_out x k1), Q2 (d_out x k2) in the same module:
  principal angles: cos(theta_i) = singular values of Q1^T Q2 (min(k1,k2) of them).
  overlap O = ||Q1^T Q2||_F^2 / min(k1, k2) = mean_i cos^2(theta_i), in [0,1].
  smallest angle theta_min = arccos(largest singular value): DESCRIPTIVE ONLY, never tested, never used to select anything.

## 4. Aggregation over modules and reference line

Pair score S(a,b) = UNWEIGHTED mean of O over the full intersected module list (128 modules, every layer and projection
counted once, no weighting by d_out, norm or layer). This is the recommended default and it is adopted unchanged.
Reported alongside, not tested: the unweighted mean of theta_min; and per-projection-type means (q,k,v,o) as description.
Random-subspace reference: for independent uniformly random subspaces of dimensions k1,k2 in R^d_out,
E[||Q1^T Q2||_F^2] = k1 k2 / d_out, so E[O] = max(k1,k2)/d_out, which is k/d_out when k1 = k2 = k. With k = 16 expected:
q,o: 16/4096 = 0.00391; k,v: 16/1024 = 0.01563; aggregate reference over the 128 modules = 0.00977. Computed per module from
the realised k and d_out and drawn as a reference line only; no test is run against it.

## 5. Primary statistic and null

T = mean of S(a,b) over all one-bit pairs (30 pairs; each pair weighted equally).
Null: draw N_perm = 10000 sets of m = 30 pairs uniformly WITHOUT replacement from the 106 non-one-bit pairs (each set is
without replacement within the set; sets are independent draws). T*_j = mean of S over set j.
Seed: numpy.random.default_rng(20261019), single generator, draws made in order j = 1..10000 via rng.choice(106, 30, replace=False)
over the non-one-bit pairs in the order they appear in W3b_pairs.json.
One-sided p = (1 + #{j : T*_j >= T}) / (N_perm + 1)   (greater-than alternative: one-bit more overlapping).
Also reported with p: T, mean and sd of T*, the 2.5/97.5% quantiles of T*, and T minus mean(T*).
No other p-value is computed. No multiplicity adjustment is needed because there is one test.

Known weakness, stated before results: the 30 one-bit pairs reuse profiles (degrees above), so pairs are not exchangeable and
this uniform pair-level null is not a valid exact test of exchangeability; p is a descriptive reference, not a calibrated
error rate. Section 6 is the answer to that, not a replacement for the primary test.

## 6. Pair-reuse dependence analyses (secondary, descriptive; no decision rule attached)

  (1) Per-profile reuse counts: number of one-bit pairs per profile (W3b_pairs.json, already derived).
  (2) Leave-one-profile-out: for each of the 17 profiles, drop it and every pair containing it, recompute T_{-i} (mean of S
      over the remaining one-bit pairs) and the mean S of the remaining non-one-bit pairs; report the full table, the min and
      max of T_{-i} and which profile gives them. No p-value.
  (3) Degree-matched sensitivity null: FEASIBLE. The exact backtracking search in w3b_inventory.py found a 30-edge subset of
      the 106 non-one-bit pairs with exactly the one-bit degree sequence (degree_matched_null_feasible_exact_search = true in
      W3b_pairs.json). Procedure: start from that subset, run a degree-preserving edge-swap chain inside the non-one-bit pool
      (swap (a,b),(c,d) -> (a,d),(c,b) only if both new pairs are non-one-bit and not already in the set), burn-in 1000
      accepted swaps, 100 accepted swaps between recorded draws, 10000 recorded draws, seed default_rng(20261020).
      Report the same one-sided +1 p-value. The chain's connectivity and mixing are not proven, so this is a sensitivity
      check that is allowed to disagree with section 5; disagreement is reported, not resolved by picking one.

## 7. Scope (explicit)

This test answers section 0 and nothing else. It is not a mechanism claim. It does not show that sign dials are separate or
tangled, that any bit is localised to any layer or module, polysemanticity, recursive generalisation, or causation; weight
subspace overlap is not an intervention. A "greater" result would mean only: in these 17 profiles on this training recipe,
one-bit-apart pairs have more similar delta column spaces than farther pairs, and that could equally come from shared
training data, shared initialisation or shared recipe. A null result would mean only that this statistic did not show it.
It does not reach the other 47 profiles, the 42 country adapters, or the b_risktaking bit.
No additional tests, statistics, subsets, thresholds, aggregation rules or plots-as-evidence are added after results are seen.
Anything added later is labelled exploratory, dated, and may not be used to support a claim. Pre-registered outputs are
all of: T, p, the section 6 tables, per-module O and theta_min tables, the reference line.

## 8. Implementation note

Code that computes sections 2 to 6 must be committed separately and AFTER this commit, run once on the pinned files with
sha256 re-verified at load time, and must reproduce these constants (rel_tol 1e-6, N_perm 10000, seeds 20261019 / 20261020,
r=16, 128 modules, 30/106 pairs). Unit tests on planted or synthetic subspaces are allowed before the real run.

## Deviations log (append only)

(none at freeze)
