# CP Checkpoint assembly: STATUS checkpoint + Open table with targets, workbench docs, ledger, push both branches

Card `t_5b53fef3`, board sca2-paper-b, assignee `sca`, status at export: running (this card; status at export time)
Created 2026-10-19 16:43 MST. Exported 2026-10-19 by the CP assembly card as a dated record, not status.

## Body

Checkpoint assembly for 08:00 MST 2026-10-20. Shared rules: /Users/bonorinoa/.hermes/cache/scratch/c9_explore/common.md. Deadline 07:30 MST. Augusto approved the push plan in DECISIONS.md (2026-10-19 rows).

1. **Gate.** Confirm that every SCA2 card on board `sca2-paper-b` created on 2026-10-19 is done, or explain each one that is not.
   - The W2 queue may still be running; that is fine. Record its RUN_STATUS.
   - If V or A blocked, do NOT push the paper branch. Assemble the docs and comment what is missing.
2. **STATUS.md** (main worktree, `feat/paper-b-cohort`):
   a. A new section, `## Checkpoint 2026-10-20 (co-author review)`, listing:
      - the git heads of both branches;
      - the numbers-table hash and row count;
      - Amendment C9;
      - the verifier record;
      - the private Space URL;
      - the Hub runs added (adapter+persona, label recovery);
      - the brief.
   b. Replace "Open" with `## Open after the checkpoint`. It is a table: item | owner | target date | blocked by. Start from the list below and add anything the cards surfaced.
   c. Update the Workstreams row for the workbench: it now reads Paper B artifacts, one way only.
   d. Add `planning/checkpoint_2026-10-20/` to the document map.
   Then run `paper_b/test_status_doc.py` and the full suite.
3. **Workbench documentation** (workbench worktree, branch `Adapter-Brain-Vizualization`):
   - write `workbench/README.md` (SCA2-specific: what it is, how to run, how to rebuild the bundle, the deployment, the data policy);
   - add an `AUDIT.md` §17 for W2, W3, WB1 and WB2;
   - make the root README.md of each branch point to the other.
4. **Refresh and commit.** Run `python3 planning/kanban_ledger.py`, copy the 2026-10-19 card texts into `planning/checkpoint_2026-10-20/cards/` (and the common rules file), then commit by explicit paths. Merge `feat/paper-b-cohort` into `paper/paper-b-draft` (worktree `../SCA2_PofW-paper-b-draft`). Check that both worktrees are clean: no untracked files except gitignored ones.
5. **Push** `paper/paper-b-draft`, `feat/paper-b-cohort` and `Adapter-Brain-Vizualization` to origin. Never touch `main`, never tag, never force. Verify each push with `git rev-list --left-right --count`.
6. **Comment** with every head sha, the test results, and the final Open table.

Open after the checkpoint (seed list; targets are proposals for Augusto):
- Augusto only: co-author sign-off on C7–C9 (at the co-author meeting); author list and order; OSF registration; anonymous mirror; IRB/COI/funding/compute/AI-use statements; SMR preprint policy; Overleaf page count; create the HF org and invite co-authors if WB2 could not; confirm the "recursive generalization" definition.
- Paper B: C9 section in the manuscript via the writer profile (target 2026-10-23, after sign-off); novelty audit "LM evaluation for social-science measurement" (2026-10-23).
- Workbench/SCA3: upload the W2 prompt-route captures to the Hub and run the weights-vs-prompt analysis of the risk inversion (2026-10-21); repeat W3 with the prompt route (2026-10-22); extract a general workbench repository (2026-10-23); next run version computes the parity reference in float64 (with the next capture run); live adapter chat card with cost and data-rights check (2026-10-26); public release after co-author review.
- Data review before Paper B is shared: purge or keep the git history of the untracked human-derived CSVs; the copies on `main`; tracked bank-1 `D_syn_*.jsonl`; `paper_a/country_item_scores.csv`; GPS PDFs (target: with SMR submission prep).
- Paper C candidate: magnitude-graded compiler design and preregistration, after the sign-profile evaluation is concluded (target early November).
- Housekeeping: the creative profile's false positive in the no-PAYG check; data-scientist `max_turns` and real-browser profile; the check script needs pyyaml.

## Runs

- run 79 sca: running/None  

## Comments

### default 2026-10-19 16:47

Checkpoint 08:00 MST Tue 10-20 (user confirmed 2026-10-19). Common.md deadlines updated: producer cards by 01:00 MST; verifier V by 04:00; deploy WB2 / amendment A by 06:00; assembly CP by 07:30. Cards: C9-1 (running, sca), C9-2 (scheduled, engineer, ≤5 CU), C9-4 (running, engineer, GPU ≤5 CU), W1 (running, sca, CPU), V (queued, gated on four), W2 (scheduled, engineer, 0 CU, detached Mac run), WB1 (running, engineer, SCA2-specific), WB2 (scheduled, sca, private HF Space, no deploy yet), A (queued, gated on V), BRIEF (queued, writer, 2 pages, claim-id for every number), CP (queued, sca, assembly). Decision log: workbench = one-way (workbench reads Paper B artifacts; Paper B claims never depend on workbench); private HF Space for co-authors; live adapter chat deferred; no new instrument (relabeling deferred); push approved at checkpoint (paper/paper-b-draft + Adapter-Brain-Vizualization; main untouched). Open items: recursive generalization definition; co-author HF org; verification and deploy at 06:00.

### default 2026-10-19 16:51

WB1 marked done was rejected by PM real acceptance tests. Production bundle exits1, explicitly skeleton; story test1fail6pass; cohort UI/valid matrix/deep links incomplete, no screenshots or commit. Repair t_313d3c22 and cross-family acceptance t_005b33de now mandatory before WB2 deployment/brief/checkpoint. Do not treat board done alone as acceptance; checkpoint must record PASS or outstanding blocker. Other analyses unaffected.

### default 2026-10-19 17:00

C9-4 timeout is60turn iteration budget, retry running;17:00MST no active Colab, balance181.82CU. PM reproduced syntax collection failure and found substantive partial-code errors (base-only labelled adapter+persona; non-resampling bootstrap). Recovery requirements posted to worker+V. C9-4 GPU results not produced/accepted yet; checkpoint time is a target, not a guarantee. Keep actual missing experiments visible, don't substitute fixture data for results or ask Augusto to manually run delegated experiment.

### default 2026-10-19 17:14

W2 recovery changed, not blind retry: after two60turn Claude attempts, task-only model pin set to gpt-6.1-sol/openai-codex, body narrowed to four remaining test failures + actual2unitproof + launch, optional precision work removed, unblocked (ready). At17:14 no prompt queue/captures; targeted tests10pass4fail. The original approved26x23experiment remains pending until real PID/status. W2 has no completion dependency in CP original graph; record actual run health and tests, do not infer finished from launcher card done.

### default 2026-10-19 17:21

W3 recovered after two45turnClaude failures: task reassigned engineer, pinned Codex gpt-6.1-sol, now RUNNING (not a blind retry); narrowed stage-wise spec, genuine42x23 input census and realLoRA tests, no stale proxies. Independent W3-V repinned Claude. Original partial reports remain INVALID until regenerated and verified. W2 also Codex recovery; do not conflate program limits with compute experiments failing. Checkpoint08:00 target unchanged but report actual incompleteness.

### default 2026-10-19 17:23

C9-4 now recovered deliberately after2x60turn failures: routeCodexgpt6.1sol, body staged CPUpreflight->realGPUjobs->readback&cleanup, ready. Current7pass3fail,no completedGPUoutputs17:22,noColabVM,balance181.82. Claude C9-GV t_433e7ef5 added before V for cross-family audit; downstreamA/brief gated. Do not count fixture/no-adapterpersona replay as new42country results. Budget5CU TOTAL unchanged.08:00stilltarget, allremainingexperimentsmust show actualstatus.

### default 2026-10-19 17:27

Checkpoint 08:00 MST Tue 10-20 (new DECISIONS.md 2026-10-19 rows). User confirmed: deploy private HF Space; no live adapter chat tonight; workbench is SCA2-specific, reads Paper B artifacts one-way; co-author sign-off + OSF + SMR items (STATUS.md Open) remain; model-independent verification and C9 amendment depend on verification results; number audit (test_status_doc.py) stays green; update STATUS.md Open after verification.

### default 2026-10-19 18:44

PM correction (18:45 MST). Ignore PM comments 95/96 on t_313d3c22: WB1-V was not stuck, it was running normally and later PASSED (17:58). State for assembly: WB1-V PASS; WB2 deployed a private Space, Bonorinoa/sca2-workbench (remote = manifest); C9-2 done (adapter+persona cell pending). C9-4: the producer card is marked done, but NO GPU run happened, and C9-GV ruled BLOCK. Its 16-country fixture output must not be reported as a 42-country result. W3: the producer card is marked done, but W3-V ruled BLOCK. The code is a stub, and it falsely claimed 8/8 tests pass. Quote no W3 numbers. W2 queue: ABORTED at 36/598 by its watchdog. One unit hit 130 s, against a limit that was calibrated for unprompted base units. Nothing has been pushed.

