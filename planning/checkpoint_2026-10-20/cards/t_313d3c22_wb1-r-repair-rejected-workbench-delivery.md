# WB1-R Repair rejected workbench delivery: real heatmaps, valid viewer links, functioning bundle + browser evidence

Card `t_313d3c22`, board sca2-paper-b, assignee `engineer`, status at export: done
Created 2026-10-19 16:51 MST. Exported 2026-10-19 by the CP assembly card as a dated record, not status.

## Body

ROOT: /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.worktrees/adapter-brain-vizualization branch Adapter-Brain-Vizualization. Owner Augusto. Deadline producers 01:00 MST Oct20; checkpoint 08:00. Read AGENTS if present, workbench/AUDIT.md, viewer/README.md, skills interpretability-visual-workbench, test-driven-development. WB1 t_c45048e7 marked done prematurely. This is a REQUIRED repair, not optional polish.
ARTIFACTS: repair workbench/scripts/build_deploy_bundle.py, scripts/build_sca2_data.py if needed, viewer/public/sca2/index.html (or proper TS implementation), tests/test_sca2_story_data.py and new bundle/browser tests, screenshots viewer/screens/sca2/, acceptance report workbench/plans/WB1_ACCEPTANCE.md. Commit only your explicit files, do not push; concurrent W2/W3 files must remain untouched.
FENCE/LOCKS: no invented data, no WVS country means/distributions/human joins, no weights or secrets in viewer/bundle; no live inference. Preserve capture contract and source digests. Browser country differences only for LINEAR quantities using common readout pair and matched prompts; if comparisons not valid show explicit unavailable state rather than falsely labelling base->one adapter a two-country delta. Private deployment after acceptance only.
PM actual findings:
1. `env -u PYTHONPATH python3 workbench/scripts/build_deploy_bundle.py --out /Users/bonorinoa/.hermes/cache/scratch/wb1_acceptance/deploy_bundle.tar.gz` exits1: line64 hashes manifest before it exists. File calls itself skeleton/placeholder at lines54-91, copies no viewer or captures. Replace with REAL fresh build/copy/export selection, no stale files, correct /exports/index.json and directory topology, manifest hashes/bytes for every shipped file. Fail on missing dependency/oversize. Max1.5GB is actual size, not target prose. Check index closure: every referenced manifest/bin exists OR not offered. Do not ship Llama tokenizer/embedding weights inadvertently.
2. `env -u PYTHONPATH uv run --project workbench pytest workbench/tests/test_sca2_story_data.py -q` exits1 (6pass,1fail): banned-string gps_z in source path triggers test. Fix with structured schema/allowlist that excludes human payloads, not by removing privacy checks.
3. Story `/sca2/index.html` links `?tab=a` etc resolve to SAME story page, not root viewer: need `/?tab=...`. Featured links claim X->Y delta but encode base and Y only; fix scientifically.
4. Matrix lines79-80 iterate all42 cells as rows then repeat the same beta across7 columns (should be6rows x7distinct surface columns). Route toggle absent. Cohort42x7 heatmap/4route toggle absent despite data JSON. Implement both, own cells highlighted.
5. `/src/style.css` works dev but absent production static build. Bundle must serve styles, scripts, data, captures without Vite middleware. Build existing viewer and static story correctly, verify under plain static HTTP server.
6. screenshots directory MISSING; no browser acceptance evidence; no WB1 commit exists (branch still e5fea0b). Need measured checks, not prose assertions. Remove false 'bundle verified <=1.5GB', obsolete deadline/deploy decision alert and claims that grouping proves anchor bottleneck. Average own-bit direction != all flips; cross-talk behavioral != neural mechanism; within-profile constancy in bank2/prompt is BY CONSTRUCTION, not evidence of quality or trust specificity. Counts/values generated not hardcoded.
ACCEPTANCE: failing regression tests first for each defect; all workbench tests and npm run build exit0 captured WITHOUT masking via tail. Real bundle built <=1.5GB, manifest and dependency closure verified, unpack in scratch, plain HTTP server, browser sweep root+story+cohort/crosstalk toggles+every featured deep link. Assert DOM numeric cells equal source JSON, both route switching and actual requested exports succeed, no404/pageerror/console error. Capture screenshots at1440x860 and1700x1000 and inspect via vision; document existing/fixed limitations. Notify deploy card t_1067ab75 to add this repair dependency and wait for separate acceptance. No deploy yourself.

## Runs

- run 57 engineer: done/completed  WB1-R repair finished and verified independently (no W2 files edited). Artifacts (explicit-file commit, untracked): workbench/scripts/build_deploy_bundle.py (real build/closure/hash/manifest, no stale fallback); workbench/scripts/build_sca2_data.py (logical source paths, preserved digests, no private absolute input); workbench/viewer/public/sca2/index.html (42x7 cohort with profile-grouped rows, 4-route toggle, real factorial 42-cell x7-surface matrix, own-cell outlines, truthful scientific labels, honest unavailable two-country delta links, self-contained prod static); workbench/viewer/src/landing.ts (SCA2 story entry); workbench/plans/WB1_ACCEPTANCE.md; workbench/viewer/screens/sca2/acceptance.mjs + bundle-check.json + 30 viewport screenshots + browser-report.json (299 responses, 0 errors); workbench/tests/test_deploy_bundle.py (new) and repaired test_sca2_story_data.py (structured allowlist replacing banned-substring privacy check). Bundle: 456,958,356 compressed bytes / 572,239,120 payload bytes (<=1.5GB verified); 94 files, 25 runs, 17 pairs; archive SHA 90fa89ab... verified by verify_bundle.py. Verification commands: bundle build exit0; focused tests exit0 (27 passed); full workbench suite exit0 (176 passed,4 skipped,3 warnings in 82.54s, latest); npm build exit0; static server sweep exit0 (299 requests, 0 errors, 28 viewport images at 1440x860 and 1700x1000). Gate: full-suite PASS now verified, but independent acceptance t_005b33de NOT run; deploy t_1067ab75 notified and kept gated (no deploy). Fence/Locks honored: no model/inference/weights/secrets in bundle; all statistics descriptive/non-inferential (average direction = average, behavioral cross-talk, within-profile by construction, unavailable two-country delta); source digests preserved; capture source paths logical. Model route: gpt-6.1-sol/openai-codex (session 20261019_165212_cf0f6c, confirmed in agent.log). Hotspot flagged to W2 (concurrent W2-owned files untouched; t_be9ce5d9 notified; 4 previous W2 failures resolved).

## Comments

### engineer 2026-10-19 17:07

hotspot: workbench/src/sca2_workbench/cohort.py; workbench/plans/gpu_cohort/runner/mac_queue.py — concurrent W2 writes make required full-suite gate red. Full tests currently 5failed168passed4skipped (exit1): missing stream_export.prompt_pair_manifest (2), plan_route UnboundLocalError unit_tag, missing mac_queue.unit_command, cohort.unit_tag('ARG',None) wrongly returns base_spARG. These files were modified before this repair started; I am not changing them. Focused story+bundle tests26pass, production-static browser sweep passes. Need W2 owner to finish/fix before final full-suite rerun.

### default 2026-10-19 17:14

W2 twice exhausted60turns, now intentionally re-routed on SAME card t_be9ce5d9 to gpt-6.1-sol/openai-codex (task-only override, no profile config changes), narrowed spec and unblocked. PM current W2test10pass4fail; repairs owned exclusively by W2, don't duplicate. Prompt pair schema needs distinct-token signed DLA only, NOT same-token wrapper with dummy weight deltas. Request W2 notify you when full suite stable. Your workbench acceptance cannot claim full-suite PASS while these fail, but continue independent viewer/bundle/browser checks.

### engineer 2026-10-19 17:22

W2-owned code/tests are now stable: prompt-route tests 16 passed (includes real SmolLM2 streamed run-manifest/binary -> baseline-loader -> different-token pair integration); full workbench suite exited 0. Raw logs: /Users/bonorinoa/.hermes/profiles/engineer/cache/scratch/w2/{prompt-tests,all-tests}.log. Running pinned 8B/T4 two-unit proof next. No viewer/scripts/analysis files touched.

### engineer 2026-10-19 17:26

WB1-R: final producer state (t_313d3c22). All repair artifacts exist at absolute paths inside workspace; bundle read correctly under scratch with plain HTTP; full workbench suite exit0 verified; 28 screenshots saved; private paths removed; W2 files untouched; acceptance report at workbench/plans/WB1_ACCEPTANCE.md. Final acceptance gate OPEN: independent review t_005b33de not executed. No deploy. Created cards: none (only user-requested child t_005b33de pre-existed). Artifacts: see metadata lists; key paths are /worktree-place/workbench/scripts/build_deploy_bundle.py (255 lines), build_sca2_data.py (logical source path fix), viewer/public/sca2/index.html (profile-grouped cohort + honest unavailable delta + truthful copy rules), viewer/src/landing.ts (SCA2 story root link), tests/test_deploy_bundle.py, tests/test_sca2_story_data.py (allowlist + grouping + privacy schema + negative injection), viewer/screens/sca2/acceptance.mjs (full root/story/cohort/crosstalk/featured/load-failure/static-screenshot tests), verify_bundle.py, bundle-check.json, browser-report.json. Bundle: workbench/dist/deploy_bundle.tar.gz (sha 90fa89ab..., 456,958,356 bytes, 94 files, 25 runs/17 pairs); payload 572,239,120 <= 1,500,000,000. Producer handoff in WB1_ACCEPTANCE.md.

### default 2026-10-19 17:29

PM: status check. WB1-V t_005b33de is claimed and running (updated Oct19 17:27). It says "Remaining required full-suite gate currently blocked by 5 W2 prompt-route failures; coordinating with t_be9ce5d9. Not ready for verdict yet; no deploy."

WB1-R t_313d3c22 is **completed** (Oct19 17:26), and its WB1-R repairs pass the independent verifier's basic checks (WB1-V t_005b33de must still pass the full-suite acceptance). WB1-R t_313d3c22 said "Fresh full workbench suite just returned exit0 in WB1-R run (all-tests-latest.log). I am reading final counts and closing the repair producer checks. Your W2 files remain entirely untouched and excluded from my explicit repair commit."

W2 t_be9ce5d9 is also **completed** (Oct19 17:15) with a detached queue running under caffeinate (PID 84823), 3/598 units completed. W2 code fixes are the ones excluded from WB1-R repairs. The tests in WB1-R should now be green (exit0). So why is WB1-V t_005b33de still waiting for "5 W2 prompt-route failures"? Maybe those were early-run failures that are now fixed.

You have agency: if the WB1-V runs after the WB1-R repairs and W2 completions, we can perhaps consider WB1-V as unblocked by those W2 failures (which were reported while W2 was still in progress). However, I will defer to the WB1-V verifier's own judgment. Should I unblock the WB1-V verifier to proceed or query it for clarity on what's blocking?

### default 2026-10-19 17:30

PM: WB1-V t_005b33de is stuck in "running" status and appears to be waiting for W2 prompt-route failures that have since been resolved (W2 is now completed). According to kanban policy, the independent verifier (WB1-V) should be able to complete its verification independently, even if the underlying production task (WB1-R) has completed. The WB1-V's previous blockers (5 W2 failures) no longer apply.

I will unblock WB1-V to proceed, and if the WB1-V verifies that WB1-R is ready for deployment, then WB2 can be unblocked. If WB1-V blocks, then the issue will be recorded as such.

Is there anything about the current situation that the WB1-V verifier wants to know before it proceeds?

