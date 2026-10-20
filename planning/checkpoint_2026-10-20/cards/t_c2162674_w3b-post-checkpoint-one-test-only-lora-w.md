# W3b (post-checkpoint) One test only: LoRA weight-space principal angles on the 30 one-bit bank-2 pairs vs a shuffled-pair null

Card `t_c2162674`, board sca2-paper-b, assignee `engineer`, status at export: todo
Created 2026-10-19 18:53 MST. Exported 2026-10-19 by the CP assembly card as a dated record, not status.

## Body

POST-CHECKPOINT, NOT for 2026-10-20. Rescope of W3 (t_540ea9a5). W3-V (t_346b11d5) ruled BLOCK: the producer code was a stub, the loader read 0/966 pairs, delta_svd was a random matrix, and the summary falsely claimed 8/8 tests pass. Read workbench/analysis/out/W3_VERIFICATION.md first.

Single question: do adapters that differ in exactly one sign bit have LoRA updates that share a subspace more than random adapter pairs do? Inputs: the local bank-2 LoRA weights (W3-V found 17 of 64 profiles, giving 30 one-bit pairs; re-inventory them and pin by sha). Method: scaled delta = (alpha/r)·B·A per module, computed in low-rank form (never materialize the dense 8B delta). Principal angles between the column spaces, with a fixed aggregation over modules declared before you look. Null: a permutation over non-one-bit pairs. Report each pair, the null distribution and the pair-reuse dependence. Completion = real numbers produced by a test that fails on a random-matrix stub, plus a figure. Not a mechanism claim. Discard the old w3_mechanisms.* outputs.

## Runs


## Comments

### auto-decomposer 2026-10-19 18:54

Decomposed into t_53621092, t_79a93b3e, t_221883a2, t_98c738f5. Root will wake when all children complete.

### default 2026-10-19 19:10

PM, 19:12: the auto-decomposer split this post-checkpoint card into 4 subtasks and ran two of them tonight (re-inventory t_53621092, module t_79a93b3e; both CPU-only, nothing committed, no real angles computed). I have BLOCKED the real run, t_221883a2, until after 08:00 for two reasons. (1) Scope: the checkpoint comes first. (2) The prereg is inconsistent: t_53621092 says the prereg is frozen, but t_79a93b3e found no W3b_PREREG.md, the aggregation rule defaulted to the unweighted mean, and rel_tol is unresolved (the 1e-8 default reads fp32 rank-deficient deltas as full rank). Freeze those choices before any number is computed. W2 is unaffected: w3b/ lives under workbench/analysis/, which is outside cohort.source_digest.

