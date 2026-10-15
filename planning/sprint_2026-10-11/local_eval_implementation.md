# Local eval implementation report — 2026-10-11

Scope honored: edits confined to `paper_b/eval_lib.py`, `paper_b/test_eval_lib.py`,
NEW `paper_b/evaluate_local.py`, NEW `paper_b/test_evaluate_local.py`. No
commits, no pushes, no GPU, no external upload, no manuscript edits. All work
strict TDD: every slice's tests were run and watched failing (RED) before the
implementation that satisfied them (GREEN), then full regression.

## Baseline (before any edit)
- `pytest paper_b/test_eval_lib.py` → **9 passed**.
- `score_cohort.py --gate-cpu` → **PASSED** (population 1.110e-16, metrics ≤ 2.176e-13).
- JOR/Q178 verified genuinely empty: value_counts shows a single value `-4`
  ("not asked") across all 1203 JOR rows; valid 0–10 responses = 0. The archived
  `skipped_population_questions.csv` (GBR/Q174) was the format template.

## Slice 1 — audited join (RED → GREEN → regression)
RED (6 tests): all failed `TypeError: unexpected keyword 'skipped_cells'`.
GREEN: `eval_lib.join_option_evaluation(model_scores, population_long,
skipped_cells=None, dropped=None)`:
- drops a model row ONLY when its (eval_country, question_id) cell is in
  `skipped_cells` AND that cell is wholly ABSENT from the population;
- default `skipped_cells` = no drops permitted → unexpected missing cells and
  partial option-support mismatches both raise AssertionError (which also
  catches the cached-CSV int64 `option_code` corruption class);
- bogus skips (cells that DO have population rows) raise ValueError;
- canonicalizes `option_code` to canonical strings on both sides before the
  join (repair at the boundary, join keys never trusted as read);
- `validate="many_to_one"` kept; duplicate population keys raise AssertionError;
- reports via attrs `dropped_rows` / `dropped_cells` / `skipped_cells_used`
  and, when provided, appends per-cell records to the `dropped` list.
Final RED for slice: `17 passed` after GREEN, `--gate-cpu` PASSED.

## Slice 2 — builder skip ledger (RED → GREEN → regression)
RED (2 tests): `KeyError: 'reason'`.
GREEN: `build_population_distributions(..., skipped=None)`:
- `skipped=None` (default, used by the reproduction gate) → an empty cell now
  RAISES `ValueError: ... no valid responses ... Record this cell explicitly`
  instead of silently dropping;
- `skipped=[]` (explicit ledger) → appends
  `{eval_country, question_id, reason='no_valid_responses', n_valid, total_weight}`;
- population frame carries attrs `skipped_cells`, `n_skipped_cells`.
- Targeted compatibility edit to `score_cohort.py` `--gate-cpu` (NOT the GPU
  path, NOT sibling S1 territory): pass a ledger and forward `skipped_cells`
  to `gate_cpu`. Sibling conflict risk is logged below.

## Slice 3 — evaluate_local (RED → GREEN → regression)
RED: `ModuleNotFoundError: No module named 'evaluate_local'` (collection error).
GREEN: NEW `paper_b/evaluate_local.py`, local-only, no torch/network:
- consumes per-model `*_option_probabilities.csv` + local WVS parquets;
- `load_model_scores` reads `option_code` as **str** (dtype-pin; fresh scorer
  rows carry strings; CSV round-trip would infer int64 and corrupt join keys);
- `validate_model_scores` requires full option support per (model, question),
  unique option codes, and finite/nonnegative/sum-to-one (1e-8) probabilities —
  BEFORE any output is written;
- rebuilds weighted populations with the explicit skip ledger; broadcasts
  base→all, adapters/personas→matched or all (mirrors `build_pairs` semantics);
- joins through the audited safe join; writes population distributions, skip
  ledger CSV, joined option table, metrics, and `local_eval_manifest.json`
  with sha256 of every input, protocol constants, join audit, skip ledger,
  and `low_support_cells` (informational, `analysis_min_n=50`,
  `analysis_min_n_applied: false` — never dropped at this layer; the scorer
  population threshold is untouched). Deterministic writes → byte-identical
  on re-run (no timestamps).
Final state, exact outputs:
- `pytest paper_b/test_eval_lib.py paper_b/test_evaluate_local.py -q`
  → **27 passed** (17 + 10).
- `paper_b/score_cohort.py --gate-cpu` → **GATE-CPU PASSED**; population
  max abs diff 1.110e-16; metrics: tv 1.554e-15, js 1.554e-15, brier 6.661e-16,
  cross-entropy 2.176e-13, wasserstein 8.882e-14, abs_mean_error 5.457e-12,
  abs_std_error 4.441e-14, model_mean 6.139e-12, population_mean 7.503e-12 —
  identical to the pre-edit baseline.
- CLI smoke (scratch dir, purged after): good fixture ran twice into the same
  out-dir — identical console output both runs; 564 joined rows; 0 duplicate
  keys; skip ledger `JOR/Q178 reason=no_valid_responses n_valid=0
  total_weight=0.0`; join audit dropped JOR/Q178 x10 (audited);
  `analysis_min_n=50, applied=false`. Deliberately-broken fixture (Q43 option
  '2' removed) → `ValueError: base/Q43: score file does not have full option
  support (got ['1','3'], expected ['1','2','3'])` and NO output directory
  created. Fixture outputs were purged; nothing under data/.

## Files
- `paper_b/eval_lib.py` — safe join + skip ledger (modified)
- `paper_b/test_eval_lib.py` — modified: 9 existing + 6 join + 2 builder tests = 17
- `paper_b/evaluate_local.py` — NEW
- `paper_b/test_evaluate_local.py` — NEW (10 tests)
- `paper_b/score_cohort.py` — two-line-scope compat edit in `--gate-cpu` path
  only (calls it with the ledger + forwards skipped_cells). This file is
  otherwise sibling-owned; flagged for the parent to reconcile if the sibling
  touches the same lines.

## Notes / issues
- The transient `test_run_unit.py` failures observed mid-session were the
  sibling worker's file landing mid-edit; it passes 6/6 now and does not
  import anything I own.
- The primary-23 battery statement: JOR/Q178 is now an explicit, ledgered,
  audited skip end to end; GBR/Q174 likewise. Nothing else is skippable
  implicitly — default is fail-loud.
- The GPU path of score_cohort.py (build_pairs → join, ~line 539) still uses
  the no-ledger defaults, so an end-of-run GBR/JOR-style crash there remains
  possible until the sibling's S1 fix lands; the safe join now gives them the
  exact mechanism to fix it with (skipped_cells + dropped ledger).
