# W2 Workbench prompt-route capture: base + 26 sign-profile prompts × 23 items on the Mac (0 CU)

Card `t_be9ce5d9`, board sca2-paper-b, assignee `engineer`, status at export: done
Created 2026-10-19 16:37 MST. Exported 2026-10-19 by the CP assembly card as a dated record, not status.

## Body

PM RECOVERY OVERRIDE (2026-10-19 17:14 MST). Two Claude attempts exhausted60turns; model now Codex gpt-6.1-sol. This is the SAME approved task, not a new experiment. Resume existing files, do not restart design. Producer deadline01:00MST Oct20, checkpoint08:00. No capture running at PM check.

TIGHT REPRO: env -u PYTHONPATH uv run --project workbench pytest workbench/tests/test_prompt_route.py -q →10pass4fail (exit1).
1. stream_export.prompt_pair_manifest incorrectly reuses same-token pair_manifest using incomplete `res` →KeyError a_clamped. Implement DIFFERENT-TOKEN prompt pair contract: signed readout head/MLP/embedding DLA only, plain/clamped; include profile_id and token counts; conserve sums vs d_margin; no unaligned token norms, dummy weight arrays, or fake zeros. Actual model readout contrast/scale must be compatible. Add integration test from actual run manifests, not only dummy dicts.
2. mac_queue.unit_command missing (existing test supplies baseline/frozen/profile unit).
3. cohort.unit_tag('ARG',None) wrongly returns base_spARG; normal country/base keys MUST remain unchanged; prompt profile alone gets distinct suffix.
Tests fixture expects functions as seams, not permission to skip end-to-end semantics. Trace caller definitions and usages before edits. After two patch failures reread function and replace complete function, not repeated stale patches.

Acceptance sequence: existing14tests green; original phase1 tests green; full workbench suite green (concurrent WB1-R owns viewer/scripts, W3 owns analysis; don't edit them). Then2-unit real prompt proof with verified bytes for exact pinned sign template, neutral base baseline, canonical readout and gates. Only then detached598run queue under caffeinate with one-instance lock, RUN_STATUS, realPID, actual10unit timing/ETA, no duplicate queue. Inventory cached weights/frozenNF4 before claiming unavailable. No GPU cost, no uploads. If any scientific parity issue, save exact numeric errors and block rather than widen gate.

Coordination: WB1-R t_313d3c22 is waiting on W2-owned code before full-suite acceptance. Post there when tests stable. Do not stage/commit WB1-R/W3 files. This card is complete at healthy launch, not at 'all interfaces implemented' or fixture-only pass.

Original specification follows:

Workbench stream. Worktree /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.worktrees/adapter-brain-vizualization, branch `Adapter-Brain-Vizualization`. Read `workbench/AUDIT.md` (§16 = the phase-1 Mac cohort run), `workbench/plans/gpu_cohort/` (C2 local queue, LAUNCH.md, diagnostics/IRQ_wvs_Q177.md), `workbench/viewer/README.md`. Shared rules for secrets/human data: /Users/bonorinoa/.hermes/cache/scratch/c9_explore/common.md (rules 2-4). Cost: 0 Colab units (Mac CPU only).

Goal: the prompt route, so weights vs prompt can be compared in the same components. For each of the 26 sign profiles carried by the 42 cohort countries, capture the BASE model prompted with that profile's strict sign-profile prompt (exactly the text Paper B scored: `paper_b/sign_prompt.py` in the main worktree /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW; vendor the 26 prompt strings into the workbench with a sha256 check against that module, do not import across worktrees at run time) on each of the 23 strict-battery items: 598 runs A', plus pairs A' vs the existing base runs A. Same frozen T4 NF4 instrument (`nf4_dequant_float64`, instrument hash 46079e27), same gates, same queue as phase 1.

Steps: (1) tests for the new unit kind; (2) a 2-unit proof (gates pass, parity reported); (3) launch detached under `caffeinate -dims` with RUN_STATUS.json, output `workbench/exports/phase1_promptroute_nf4_t4/` (gitignored like phase 1); (4) report ETA and first-10-unit timings on the card. The earlier estimate is about 4.5 h.
Scope lock: keep precision/reference gates unchanged. No optional float64-reference refactor on this card.
Commit your code (not exports) on the workbench branch by explicit paths; do not push. Do not upload to the Hub (a later card). Complete the card once the run is launched and healthy (do not wait for it to finish); leave a one-line status command in the comment.

## Runs

- run 53 engineer: timed_out/timed_out  
- run 58 engineer: gave_up/gave_up  
- run 61 engineer: done/completed  W2 Workbench prompt-route capture completed: full workbench suite green (177 passed, 3 skipped), 2-unit proof finished (exit 0) with real model outputs and signed DLA pair manifests, detached 598-run queue launched under caffeinate (PID 84823) in workbench/exports/phase1_promptroute_nf4_t4/. Queue is running with 3/598 units completed, one-instance lock enforced, RUN_STATUS.json updated, no GPU/Hub costs, no uploads. Code changes fixed prompt-route contract (different-token pair validation), updated stream_export.prompt_pair_manifest, cohort.unit_tag, mac_queue.plan_route/unit_command to support prompt-route mode with proper baseline integration and signed DLA differences only (no weight arrays, no token alignment).

## Comments

### default 2026-10-19 16:55

PM diagnosis of first timeout: NOT a 0-second wall-clock/GPU failure. Stored run53 error = `Iteration budget exhausted (60/60)`; agent got stuck in repeated stale patches to mac_queue.py. At16:54MST: no prompt RUN_STATUS.json, no prompt export directory/captures, no live queue/caffeinate/unit process. Retrying must RESUME existing files, not restart/recreate tasks or launch duplicates. PM ran `env -u PYTHONPATH uv run --project workbench pytest workbench/tests/test_prompt_route.py -q` →9pass5fail exit1: missing stream_export.prompt_pair_manifest (2tests), mac_queue.plan_route, mac_queue.unit_command, cohort.unit_tag. Tight scope: implement these existing tested seams, run relevant/full tests, 2-unit real proof, launch detached only after proof; capture PID/status and10unit timings. No optional float64-reference refactor now. If two patches fail, reread entire enclosing function then replace that function rather than loop. Scientific guard: prompt insertion changes token count; compare layer/head DLA at matched readout/margin convention only; no subtracting unaligned full-token tensors/norms. Keep existing phase1 exports immutable. Report precise blocker if additional model/input issue. No need new user approval;0CU already approved.

### engineer 2026-10-19 17:07

WB1-R concurrent full-suite run found5fail168pass4skip (exit1), all W2 tests: stream_export.prompt_pair_manifest missing (2), plan_route UnboundLocalError unit_tag (mac_queue216), missing unit_command, cohort.unit_tag('ARG',None) returns base_spARG. Please finish/fix your owned code before WB1-R required full-suite gate. I will not touch your files. Full raw log /Users/bonorinoa/.hermes/profiles/engineer/cache/scratch/wb1/all-tests.log; notify t_313d3c22 when stable.

### engineer 2026-10-19 17:16

Latest WB1-R full suite now4failed170passed4skipped, exit1. W2 plan_route fixed; remaining stream_export.prompt_pair_manifest res missing a_clamped(2), unit_command absent, unit_tag(ARG,None) base_spARG. No other regression. I will preserve independent repair evidence/commit and gate completion if W2 is not green. Newer raw log /Users/bonorinoa/.hermes/profiles/engineer/cache/scratch/wb1/all-tests-final.log.

### engineer 2026-10-19 17:16

Acknowledged PM reroute and exclusive W2 ownership. WB1-R will not edit prompt-pair/cohort/queue code or claim full-suite PASS. Please notify t_313d3c22 immediately when full workbench suite is stable so I can run the acceptance gate again.

### engineer 2026-10-19 17:22

Recovery: original repro confirmed 10 pass / 4 fail, exit 1. Added failing real-model integration + readout-incompatibility tests (red exit 1), then fixed pair contract, preserved ordinary model tags, and wired queue flags into actual capture (prior code parsed flags but never inserted a sign prompt). Prompt suite now 16 pass, exit 0; full workbench suite exit 0. Cached pinned base snapshot is present; frozen_nf4_t4 has all 224 safetensors; all 23 neutral base markers exist. Proceeding to real 2-unit proof, without gate/reference changes.

### engineer 2026-10-19 17:24

Fresh full workbench suite just returned exit0 in WB1-R run (all-tests-latest.log). I am reading final counts and closing the repair producer checks. Your W2 files remain entirely untouched and excluded from my explicit repair commit.

