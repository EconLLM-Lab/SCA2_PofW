# W3b: implement low-rank LoRA principal-angle module with stub-proof tests

Card `t_79a93b3e`, board sca2-paper-b, assignee `engineer`, status at export: done
Created 2026-10-19 18:54 MST. Exported 2026-10-19 by the CP assembly card as a dated record, not status.

## Body

GOAL: Implement the computational core for W3b (parent t_c2162674) and a test suite that FAILS if any component is a stub or a random-matrix substitute. The previous W3 shipped a stub. Its delta_svd was a random matrix, and it falsely reported that 8 of 8 tests passed. Read workbench/analysis/out/W3_VERIFICATION.md first.

PROJECT ROOT: workbench/analysis/. Put the code in workbench/analysis/w3b/ and the tests in workbench/analysis/w3b/tests/.

IMPLEMENT:
1. load_adapter(path, expected_sha256)
   - Verify the sha256 of the file and raise an error on a mismatch.
   - Return a per-module dict holding A (r×d_in), B (d_out×r), alpha and r, read from adapter_config.
   - Fail loudly on missing modules. Never return random or empty data as a fallback.
2. lowrank_colspace(A, B, alpha, r, rel_tol)
   - Compute the orthonormal basis Q of col((alpha/r)·B·A) without forming the d_out×d_in product: a thin QR of B, then an SVD of the r×d_in matrix R_B·A, then Q = Q_B·U_k.
   - Return Q and k.
   - Use float64 for this linear algebra.
3. principal_angles(Q1, Q2): return the singular values of Q1ᵀQ2, clipped to [0, 1], and the angles.
4. pair_overlap(adapterX, adapterY, modules): compute the per-module normalized overlap ||Q1ᵀQ2||_F² / min(k1, k2), the smallest angle, and the aggregate, as the unweighted mean over modules. Keep the aggregation function pluggable so that it can follow whatever rule W3b_PREREG.md specifies.
5. permutation_null(stat_by_pair, one_bit_pairs, non_one_bit_pairs, n_perm, seed)
   - Return the null distribution of the mean over sets of non-one-bit pairs, each set the same size as the one-bit set.
   - Return the one-sided p-value with +1 correction.
6. leave_one_profile_out(...) and per-profile reuse counts.

TESTS (pytest; each must be meaningful):
- Planted subspace. Build synthetic adapters with d_out of about 512 that share a known k-dimensional column subspace. The overlap must equal 1 within 1e-8, and the principal angles must equal the known ones within 1e-8.
- Known angles. Build a construction with analytically specified principal angles, for example rotations of a basis, and check that they are recovered.
- Random baseline. For independent Gaussian bases, the mean overlap must be close to k/d_out within a stated tolerance. This must be clearly distinguishable from the planted case.
- Low-rank equivalence. On small sizes only, compare against a dense SVD of B·A and check that the column spaces agree.
- Scaling invariance. The alpha/r scaling must not change the subspaces.
- Rank deficiency. If B·A has rank below r, k must be reduced correctly.
- Stub detector. Write a test that monkeypatches lowrank_colspace or load_adapter to return random matrices and asserts that the planted-subspace test and the sha check FAIL. The suite must be able to detect a random-matrix stub.
- Loader integrity. A wrong sha must raise an error, and a missing file must raise an error.
- Permutation null. On synthetic stat_by_pair values with a strong planted effect, p must be at most 1/(n_perm + 1) × a small factor. With no effect, p must be roughly uniform over seeds (a light check).
- Memory guard. Assert that no array of shape (d_out, d_in) is allocated for real-size modules, for example by asserting that the peak allocation is far below d_out × d_in × 8 bytes for a 4096×14336 synthetic case.

OUTPUT: The code and tests, plus pytest output captured to workbench/analysis/out/W3b_tests.log.

ACCEPTANCE:
- The full suite passes with exit code 0.
- The stub-detector test demonstrably fails when the core is replaced. Include a script, w3b/tests/run_with_stub.sh, that runs the suite with a random stub injected and exits non-zero. Capture both exit codes.
- No real adapter results are computed in this task.

## Runs

- run 73 engineer: done/completed  Implemented w3b (core.py: load_adapter with sha256 check, lowrank_colspace via QR + SVD of the r×d_in matrix, principal_angles, pair_overlap with pluggable aggregate; stats.py: permutation_null, profile_reuse_counts, leave_one_profile_out) plus 29 tests. Real suite: pytest exit 0, 29 passed. run_with_stub.sh injects random stubs: exit 1, 20 failed / 9 passed, including test_planted_subspace and test_loader_integrity. No real adapter results were computed. Nothing committed; analysis/ is untracked.

## Comments

