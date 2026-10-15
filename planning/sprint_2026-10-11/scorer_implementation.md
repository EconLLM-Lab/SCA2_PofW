# Scorer worker implementation report — 2026-10-11

Worker scope: `paper_b/score_cohort.py` (read-only context), plus new files below.
Other worker's files (`eval_lib.py`, `test_eval_lib.py`, local population evaluator)
untouched. No commits, no GPU, no external uploads, no secrets. Branch
`feat/paper-b-cohort` @ 38ed2ee; repo state otherwise shared/untracked.

## Files created (all new, all test-first)
- `paper_b/score_runtime.py` — the repaired scoring runtime
- `paper_b/test_score_runtime.py` (11 tests), `test_score_hashing.py` (3),
  `test_build_scoring_spec.py` (9), `test_score_model_only.py` (12),
  `test_persist_unit.py` (7), `test_run_unit.py` (6)
- `paper_b/build_scoring_spec.py` — model-only spec exporter (strict 23-item
  battery / archive battery; sanitized variant omits question_text)

## What is enforced (each with a RED→GREEN cycle)
1. **Revision pinning**: full 40-hex SHA required (CLI → env `SCA2_PB_ADAPTER_REVISION`
   → parent-pinned `7550fd4cfe514470bb8d80918a43c9ae424d26b5`). Revision-specific
   cache dirs; cache hits re-validated; **no Drive fallback** — hub failure raises loudly.
2. **Run-record/provenance gate**: `run_record.json` required per adapter; country must
   match cohort and request; frozen training settings enforced (model, beta 0.1, lr 1e-4,
   epochs 1, LoRA r16/α32, max_length 768, grad_accum 16, bank_run_id, integer n_train).
3. **Cache safety**: CSV keys read with explicit string dtypes (`option_code`,
   `question_id`); fingerprint sidecar = SHA-256(spec grid + readout + code revision +
   adapter weights SHA). Row count is never acceptance: complete grid match, finite
   probabilities, per-question sum≈1 enforced; stale/partial/corrupt → rejected with
   reason and rescoring.
4. **Model-only scoring**: `score_model_only(spec_path, …)` consumes the spec file only
   (hash-verified against `spec_sha256`); no survey frames, no question map, no
   population joins, no Drive.
5. **Strict battery**: `build_scoring_spec --battery strict` yields exactly the 23
   STRICT_ITEMS from the real question map (verified locally, sha ed3bb964b606a163…);
   `--battery archive` adds Q69–71 + numeric grids for the gate. Sanitized spec drops
   question_text.
6. **Adapter-path gate** (`run_adapter_path_gate`): production PEFT switch path vs an
   INDEPENDENT reference loader over THE SAME weights, plus adapter
   disable/switch-back check (base path before-enabling vs after-disable). One-to-one
   keyed match, NaN/duplicate/missing keys fatal, tolerances pinned by caller (never
   widened inside). Never compares fresh PB CHN to PA.
7. **GPU-launch block**: `run_cohort` refuses to start without a gate marker file
   (`gate_pass: true`) proving the adapter-path gate was exercised.
8. **Verified persistence** (`persist_unit_scores`): run-id + explicit destination repo
   (`Bonorinoa/SCA2-paper-b-artifacts` only); full local copy written first (retains
   question_text for later join); upload = sanitized allowlisted columns only
   (no question_text/prompt/human data; any other extra column is a hard error) to
   `runs/<run_id>/synthetic/` + `runs/<run_id>/manifests/`; readback SHA-256 must equal
   the uploaded bytes plus destination commit SHA; any failure raises and halts the
   next adapter with the local copy preserved.

## Test results
- All 48 new tests + 9 existing `test_eval_lib.py` + 8 other-worker tests: **65 passed**
  (`.venv/bin/python -m pytest paper_b/test_* -q`).
- Every cycle ran RED (collection/AttributeError/AssertionError on the missing
  behavior) before implementation, then GREEN.
- Network boundary: persistence/gate tests use a clearly-labeled `InMemoryHub` /
  `FakeHub` in-memory fixture — no real API results fabricated, no external calls.
- No real data contaminated: no writes under `data/`; fixtures in pytest tmp dirs,
  purged from /tmp after the dry-run.

## Blockers / flagged
- **GPU gate not yet exercised on real weights**: the adapter-path gate function is
  implemented and fixture-tested, but the mandatory real-weights exercise (production
  vs independent reference loader on an actual frozen adapter, GPU) has not run, so
  per the parent decision the GPU cohort launch remains BLOCKED (`run_cohort` enforces
  this via the gate marker).
- `score_cohort.py` main() still contains the old Drive-fallback resolver and row-count
  cache; I did not rewrite its orchestration (out of my ownership boundary beyond the
  file itself) — the new runtime supersedes it and `run_cohort`/`run_unit` are the
  entry points for the next GPU session. A small follow-up is needed to wire
  `score_cohort.py` CLI onto `score_runtime.run_cohort`.
- Tolerances default `tol_logprob=1e-6, tol_prob=1e-4` for the real-weights gate are
  provisional pending the parent's pinned values; they are caller-pinned, not widened
  internally.
- No worker uploads performed (parent-only per STORAGE_VERIFICATION.md).
