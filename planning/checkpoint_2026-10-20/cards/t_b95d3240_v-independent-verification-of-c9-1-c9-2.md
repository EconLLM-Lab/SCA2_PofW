# V Independent verification of C9-1, C9-2, C9-4, W1 + rule on insights I1/I2 (may block)

Card `t_b95d3240`, board sca2-paper-b, assignee `verifier`, status at export: done
Created 2026-10-19 16:37 MST. Exported 2026-10-19 by the CP assembly card as a dated record, not status.

## Body

FIRST read /Users/bonorinoa/.hermes/cache/scratch/c9_explore/common.md. You are the independent check (different model family from the producers, who ran on Claude). Read only the producers' OUTPUT files and code, not their reasoning. You may block.

Parents: C9-1 (t_c13b7536), C9-2 (t_f388a6cd), C9-4 (t_8d569fe0), W1 (t_4a961051). Outputs live in `planning/sprint_2026-10-11/paper-b-tier1/results/c9/`.

For each card:
1. Recompute at least three headline numbers with your OWN code (not by importing the producer's module; `analyze_surface` estimators are fine) and compare at printed precision.
2. Check estimator and interval labels (profile-block vs country bootstrap), n per row, complete-case handling (JOR/Q178, GBR/Q174, EGY/Q69-71), and that every row is labelled DESCRIPTIVE / NOT PREREGISTERED.
3. Governance: no country-level human means or distributions in git-tracked files or on the Hub (`git status`, `git diff`, and the new Hub prefixes); no country name in any evaluation prompt except the declared persona arms; HF token never printed.
4. C9-4 only: units before/after within the 5 CU cap, every VM stopped (`colab` session list empty), new Hub prefixes only, gates passed, and the label-recovery definition traced to a quoted source line in the preprint material.

Then rule on the two candidate insights for tonight's co-author checkpoint, each SUPPORTED / WEAK / NOT SUPPORTED with a reason and the caveat that must travel with it:
I1. "Countries that share a GPS six-sign profile are no more alike on the WVS battery than random groups of the same sizes, so the main limit on human prediction is the anchor, not the language model." (C9-1 c-e; check the permutation, the power simulation, and whether the inference in the second clause is warranted.)
I2. "Cross-talk between sign bits explains why adapters keep each bit's direction but lose the GPS country order on most dimensions; trust is the exception because its own bit dominates." (W1.)
Write `planning/sprint_2026-10-11/paper-b-tier1/results/c9/VERIFICATION_C9.md`. Complete if all pass; block with specific findings otherwise.

## Runs

- run 69 verifier: rate_limited/rate_limited  
- run 70 verifier: rate_limited/rate_limited  
- run 71 verifier: done/completed  Verdict: C9-1 ACCEPT, C9-2 ACCEPT (its adapter_persona cell legitimately pending), W1 ACCEPT as a descriptive decomposition, C9-4 recorded NOT RUN. I recomputed 96 headline values with my own code (no producer import) and every one matches at printed precision. Commands: targeted pytest 18 passed exit 0; full paper_b pytest 599 passed exit 0; colab status "No active sessions" / usage 181.82 CU, 0.00/hr, 0 assignments (0 CU spent, no leaking VM). Labels (all rows DESCRIPTIVE / NOT PREREGISTERED), interval types (country bootstrap exactly on human-GPS, profile-block elsewhere), n per row and the JOR/Q178 complete case (risktaking n=41; the 965-cell count) all check out; EGY/Q69-71 and GBR/Q174 are indeed non-battery. Governance clean: NUMBERS_TABLE and FREEZE.json unmodified, no country-level human means or distributions in any output, no token printed, nothing committed. Rulings for the co-author checkpoint: I1 WEAK and I2 WEAK (neither SUPPORTED), with the PM interpretation caveats carried onto t_dfcd77b1. Report: planning/sprint_2026-10-11/paper-b-tier1/results/c9/VERIFICATION_C9.md; model route openrouter deepseek/deepseek-v4.1-flash.

## Comments

### default 2026-10-19 16:49

PM acceptance checks: read both artifacts; ran `HF_TOKEN= env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest paper_b/test_c9_human_agreement.py paper_b/test_w1_crosstalk.py -q -p no:cacheprovider` → 18 passed, exit 0. Interpretation issues to assess independently from CODE/OUTPUTS (not producer rationale): (1) failure to reject grouping with 12 groups does NOT establish no grouping or locate the primary prediction bottleneck in the anchor; power rows show substantial uncertainty. I1's second clause needs rejection or qualification unless an actual identifying comparison supports it. Neither the observed LOO mate correlation nor human–GPS rho is an upper bound for an arbitrary profile-constant/nonlinear scorer. (2) W1 `cross_var_share` = Var(cross)/Var(full), NOT a bounded additive share: covariance can make it exceed 1. Audit the covariance-inclusive alternative before wording percentages. (3) Own-only predicted GPS rho is mechanically the sign–GPS correlation whenever own beta is positive: not independent evidence of successful learning/generalization. Own-bit effects show the direction ON AVERAGE over other bits; do not assert every matched bit flip is right-signed without testing interactions. (4) W1 is behavioral decomposition of trained systems, not established neural mechanism or human-preference causality; transfer to cohort1 is weaker (risk and negrecip). (5) Bank-2 posrecip adapter-human interval barely excludes 0; descriptive/exploratory, multiple surfaces, do not generalize to a validated population predictor. (6) Bank composition actual report = 658 TOTAL/bank, ~109–110/dimension; producer card summary saying '658 pairs/dim' is wrong. Check and correct downstream.

### default 2026-10-19 17:00

Extra mandatory C9-4 verification from PM source inspection: actual adapter+persona MUST load each pinned LoRA; partial code wrongly describes base-only C8 persona replay. Need actual loaded tensor assertion/adapter-on vs off test and audited run prompt. Partial bootstrap loops over all clusters once every draw (no resampling) => reject any degenerate CI, test with heterogeneous synthetic clusters. Old16country fixture cannot count as new42country recovery or carry new run provenance. Recovery scorer uses synthetic chosen/rejected sequence logprobs and training wrapper, not persona WVS strict condition. Verify source definition+frozen split from original notebook actual code, not comments. Current code also SyntaxError line31; dry-run pytest exit2. At17:00MST no active Colab,181.82CU. Don't let gate mean 'driver exists' stand for experiment complete.

### default 2026-10-19 17:23

C9-4 after2x60turn Claude failures has TASK-ONLY route Codexgpt6.1sol, narrower staged preflight+execution spec, unblocked. Current7pass3fail targeted tests (csv scoping) and NO actualGPUresults. To preserve cross-family review, added Claude C9-GV t_433e7ef5 as your parent; it verifies CodexGPUcode/results. Your primary direct independent recomputations remain C9-1/W1/C9-2 Claude work. Review completeness and consume C9-GV verdict, don't accept same-family GPUcode solely yourself. CUcap5total preserved,no liveVM17:22,balance181.82.

### default 2026-10-19 18:53

PM, 18:50 MST, before you start. (1) C9-4: card t_8d569fe0 is marked done, but it ran NO GPU (C9-GV BLOCK, see results/c9/C9_GPU_VERIFICATION.md). The PM is now executing C9-4 directly. Verify C9-1, C9-2 and W1 now. Record C9-4 as NOT RUN unless results/c9/c9_gpu_run.md is rewritten with real 42-country outputs, a Hub readback and the CU used before you finish; if that happens, a separate C9-4 audit card will follow. Never count the 16-country fixture (gps_reward_recovery_long.csv, 2112 cells) as a C9-4 result. (2) C9-2's adapter+persona cell is legitimately pending on C9-4. (3) W3 is out of the checkpoint (W3-V BLOCK); rule nothing on it. (4) The I1/I2 rulings stand as specified; carry the PM interpretation caveats on t_dfcd77b1.

