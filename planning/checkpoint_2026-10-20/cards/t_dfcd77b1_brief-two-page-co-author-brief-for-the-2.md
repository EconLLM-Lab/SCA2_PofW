# BRIEF Two-page co-author brief for the 2026-10-20 checkpoint (numbers only by claim id)

Card `t_dfcd77b1`, board sca2-paper-b, assignee `writer`, status at export: done
Created 2026-10-19 16:43 MST. Exported 2026-10-19 by the CP assembly card as a dated record, not status.

## Body

Write a co-author brief for the SCA2 checkpoint of 08:00 MST 2026-10-20: `planning/checkpoint_2026-10-20/COAUTHOR_BRIEF.md` in /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW (branch `feat/paper-b-cohort`). Do not commit; the assembly card commits it. Deadline 07:00 MST.

Readers: Paper B co-authors (economists) seeing the project for an initial review. Two pages at most. Plain, precise English; no hype; no "pioneer" claims (a novelty audit is pending). Number policy: every number comes from `planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv` (rebuilt by card A, Amendment C9). Write its claim id in a bracket after the number, e.g. [B2_cohort1_trust_rho]. Never type a number from anywhere else. If a number you want is not in the table, leave it out. Do not cite the arXiv preprint as prior work: Paper B is its journal version.

Sources to read: `STATUS.md`, `planning/TWO_PAPER_CLAIM_LOCK.md` (Amendments C7, C7.1, C8, C9), `results/c9/VERIFICATION_C9.md` (the verifier's rulings on insights I1 and I2), `results/c9/w1_why_trust.md`, the WB2 card comment (the private Space URL), and `workbench/analysis/out/w3_mechanisms.md` in the workbench worktree (`.worktrees/adapter-brain-vizualization`). W3 is EXPLORATORY and belongs to SCA3, never to Paper B evidence.

Structure:
1. What Paper B is now: a preregistered evaluation of the sign compiler as a scoring instrument.
2. What holds, what fails, what is untested, with numbers.
3. One methodological insight. Use I1 or I2, whichever the verifier ruled SUPPORTED, with its caveat. If neither is SUPPORTED, say what we learned and why it is not yet an insight.
4. How to explore the workbench: 4 steps, link, and what each view shows.
5. What we ask of co-authors: sign-off on Amendments C7–C9, and comments on the framing.
6. What happens next, with target dates: copy the "Open after checkpoint" list the assembly card writes, or ask the PM.
Run your own check that every bracketed claim id exists in the table and that the printed values match it at the precision shown. Report the result of that check in the card comment.

## Runs

- run 78 writer: done/completed  Co-author brief written at planning/checkpoint_2026-10-20/COAUTHOR_BRIEF.md (untracked; two pages at 10 pt). Own claim-id check exits 0: 25 distinct ids all in the table, 49 values/intervals/n match at printed precision, 0 failures. Section 3 uses the neither-SUPPORTED branch with the verifier's caveats; W3 carries no numbers.

## Comments

### default 2026-10-19 16:49

Interpretation correction from PM: previous chat overstated I1/I2. Human grouping is NOT distinguishable from random grouping in a small, low-powered multi-member subset; this is not evidence that humans have no profile structure or that the anchor is the primary bottleneck. W1 supports a behavioral cross-talk explanation (especially bank2), not a neural mechanism or a complete explanation across banks. 'Own-only sign-copier' GPS alignment is mechanical, not new predictive evidence. Await V and carry its qualifications. No figure from raw C9 outputs is claim-locked yet. Also do not use 'directions hold' as EVERY profile-pair contrast: current main-effect evidence is average over other sign bits.

### default 2026-10-19 16:59

W3 first attempt reached45turn cap, retry active. PM found partial w3_mechanisms.md/json INVALID for dissemination: code hardcodes ARG only then claims cohort/twins missing although966pair files cover42x23. DLA-array SVD is not weight-space rank, cross-item variance is not twin noise floor, null reuse estimate cannot support within>between, W2 prompt route cannot supply weight adapters. Recovery handoff posted to W3. Do not cite current W3 outputs or treat them as mechanism findings; independent acceptance will be added before brief.

### verifier 2026-10-19 19:01

Verifier (t_b95d3240) — rulings for your §3, and the PM caveats to carry.

REPORT: `planning/sprint_2026-10-11/paper-b-tier1/results/c9/VERIFICATION_C9.md` (§5 for the rulings, §1 for my commands/exit codes). Verified: C9-1 ACCEPT, C9-2 ACCEPT (adapter_persona cell legitimately pending), W1 ACCEPT as a descriptive decomposition, C9-4 recorded NOT RUN (no GPU; the 16-country fixture is not a C9-4 result).

**Decisive for your §3: neither I1 nor I2 is SUPPORTED. Both are WEAK. So take the "if neither is SUPPORTED" branch — say what we learned and why it is not yet an insight.** Do not present either as a methodological insight.

- I1 (profile grouping / anchor bottleneck) = WEAK. The non-rejection reproduces exactly, but it is a power limit, not a null: with the realized 12 multi-member groups you need a true between-share of ~0.57 for 80% power (my independent power run: min detectable 0.60, interpolated 0.568), and the observed shares are 0.318-0.626 against chance ~0.406 (one-sided p 0.059-0.738). The second clause ("the anchor, not the language model") is an interpretation no test in the card identifies.
- I2 (cross-talk / trust is the exception) = WEAK. The descriptive core reproduces elementwise (the own bit is the largest |beta| in its column on trust alone, 1 of 7; main-effects GPS order survives only on trust, 0.834). What blocks it: "explains/why" overreaches a linear-model decomposition; `cross_var_share` is NOT a bounded share (1.049 on patience:Q43) — quote `cross_cov_share` instead (trust 0.287 vs 0.727-0.985); the cross-share-vs-failure rank correlation is 0.821 on bank-2 but 0.286 on cohort-1 and rides on one surface; own-only GPS alignment is mechanical.

PM caveats that must travel (their 16:49 comment, which my rulings support): human grouping is not distinguishable from random grouping in a small low-powered subset and is not evidence of no profile structure or of the anchor being the primary bottleneck; W1 is a behavioral cross-talk explanation (stronger on bank2), not a neural mechanism and not a complete cross-bank explanation; "own-only sign-copier" alignment is mechanical, not new predictive evidence; do not use "directions hold" as EVERY profile-pair contrast — the main-effect evidence is an average over the other sign bits. No C9 figure is claim-locked yet, and W3 stays out of Paper B evidence.

### writer 2026-10-19 19:22

BRIEF written: /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/planning/checkpoint_2026-10-20/COAUTHOR_BRIEF.md (untracked, not committed; the assembly card commits it).

CLAIM-ID CHECK (own script: ~/.hermes/profiles/writer/cache/scratch/check_brief.py; output check_brief.out in the same folder; exit code 0, captured directly, no pipe).
- 26 bracketed ids cited, 25 distinct (B2_cohort1_trust_rho appears twice: once for n=42). All 25 exist in NUMBERS_TABLE.csv.
- 49 printed values, interval ends and n's compared with the table at the printed precision: 49 pass, 0 fail.
- Every other numeral was listed for review. They are interval ends of cited rows, design counts (42 countries, 7 surfaces, 6 signs, "all seven adapter-human intervals include 0", which I confirmed from the 7 C9_a_adapter_human rows), hyphens in "cohort-1"/"bank-2", and dates. No number comes from outside the table. I removed one I had typed (the row count) because it is not a table claim.

Choices to check:
- Section 3 takes the "neither SUPPORTED" branch, per the verifier: it says what we learned and why it is not yet an insight. It quotes cross_cov_share and never cross_var_share. It carries the power-limit caveat, the "behavioral decomposition, not neural mechanism" caveat, the "rests on trust alone" caveat and the "bit-only predictor is mechanical" caveat. "Directions hold" is written as an average over the other sign bits.
- W3 appears only as "no accepted result, SCA3, not Paper B". Its outputs were discarded and I read none. I did not use w1_why_trust.md (untracked producer prose, flagged by V); the table rows and Amendment C9 wording govern.
- The preprint is not cited as prior work and its arXiv id is not in the brief.
- Length: 2 pages at 10 pt with 1 in margins (pandoc to PDF, 2 pages). At 11 pt it runs to 3, because the long claim ids do not wrap. Trim if the printed copy must be 11 pt.
- Section 6 copies the seed list from the CP card, because the assembly card has not written "Open after the checkpoint" yet. W2 and W3 items carry no dates ("to be reset by the PM"), since W2 aborted and W3 was blocked. Please overwrite section 6 with the final STATUS.md list if it differs.

Issues for the PM:
1. The workbench landing footer (workbench/viewer/src/landing.ts:82) says "Paper B extends the method to a 42-country cohort" and cites the preprint. That contradicts the journal-version framing. The brief tells co-authors to ignore it. Fix it in the next bundle build.
2. Co-authors cannot open the Space yet: it is private under the Bonorinoa user account and no HF org exists (WB2 caveat). Augusto must create the org, invite them and transfer the Space. The brief says so and warns that the URL may change.
3. Sign-off wording follows STATUS.md: C7, C7.1, C8 and C9.

Model route: anthropic / claude-sonnet-5-5.

