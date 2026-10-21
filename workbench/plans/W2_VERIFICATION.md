# W2 prompt-route capture: independent verification

Task t_5a3e5144 (W2-V). Verifier: Claude seat (claude-sonnet-5-5 via anthropic, as reported by the session header; not the Codex producer).
Date: 2026-10-20. Read-only: nothing under the project root was edited except this file; nothing committed. No GPU.

Artifact: `workbench/exports/phase1_promptroute_nf4_t4/` (598 unit markers, gitignored, 17 GB) and code at 74d3a06 (branch tip 7ba4d3a).
Scripts (scratch, re-runnable): `/Users/bonorinoa/.hermes/profiles/verifier/cache/scratch/w2v_check1.py`, `w2v_check1b.py`, `w2v_check234.py`, `w2v_extra.py` (+ `.out` / `.json` next to them).

## Overall verdict: PASS-WITH-NOTES

No block. Every structural, provenance and content check passes on all 598 units, not a sample.
Two notes need a human decision before the figures are shown (N1 and N2). N3 and N4 are bookkeeping.

| # | Check | Verdict |
|---|---|---|
| 1 | Faithful prompts | PASS |
| 2 | Content, not just presence | PASS |
| 3 | Archive parity | PASS-WITH-NOTES (N1) |
| 4 | Resume did not mix states | PASS |
| 5 | Wall-limit change is watchdog-only | PASS (N3) |
| 6 | Suite | PASS at the start of the run; live tree later broke in unrelated files (N2) |

## Check 1: faithful prompts: PASS

Command: `env -u PYTHONPATH uv run --project workbench python .../w2v_check1.py` (exit 0); `python3 .../w2v_check1b.py` (exit 0).
Sources read: `paper_b/sign_prompt.py`, `paper_b/score_sign_profiles.py` and `planning/sprint_2026-10-11/paper-b-signprompt/` in the main worktree (branch feat/paper-b-cohort, HEAD 918a183, those paths clean).

- Not 5 profiles but all 26: vendored `prompt` bytes == Paper B `sign_profiles.json` `prompt` bytes == `sign_prompt(signs)` regenerated from the Paper B module. 26/26 byte-equal; each `prompt_sha256` recomputed and matches; `profile_id(signs)` matches.
- `source_module_sha256` recorded in the vendored file (70ed6eeb...) equals the sha256 of `paper_b/sign_prompt.py` today.
- Each prompt has exactly the six sign lines in the order trust, risktaking, patience, altruism, posrecip, negrecip, each `positive|negative`.
- `leak_hits` (46 country-name strings + 42 ISO codes = 88 checked) returns [] for all 26. No digit appears in any prompt, so no magnitudes. No `members` key is vendored (country membership not copied).
  Note: the sentence "They are not a country and not a number." contains the word "country", but no country name; this is Paper B's own text.
- Full prompt text actually fed to the model: for all 598 units I decoded the user turn from the run manifest tokens and compared it to Paper B's own `score_sign_profiles.combined_prompt(profile.prompt, strict_spec question)`: 598/598 identical, 0 mismatches.
- The archived option log-probs in `sign_profiles.json` vs Paper B `sign_out/*_option_probabilities.csv`: 3,640 values, 0 differ.

## Check 2: content, not just presence: PASS (done for all 598, 12 random shown)

Command: `.../w2v_check234.py` (exit 0). Random sample seed 20261020, 12 units.

All 598:
- 2,438 files referenced by the markers were hashed again; 0 sha256 mismatches, 0 missing; 0 orphan files in the export directory.
- Every unit: prompted token count > base token count (598/598); the prompted ids are the base ids with one block inserted at position 30 (insertion exact 598/598; 59 tokens inserted per sign prompt); the decoded prompted text equals the decoded base text with `sign.rstrip() + "\n\n"` inserted after the user header (598/598). The sha256 of the decoded prompted text (without the readout token) equals `provenance.prompt_sha256` for 598/598, and differs from the base unit's prompt sha for 598/598.
- `base_revision` is 0e9e39f249... in both arms of all 598 units and equals `models.json` base revision. The frozen `instrument` block (device, blocksize, double_quant, all per-layer safetensors digests) is identical between arm A and arm B in every unit and takes one value over the whole run (hash 336531ca).
- Pair payload recomputed from the run `.bin` files: `d_head_attr`, `d_mlp_attr`, `d_attn_attr` equal B minus A with max absolute deviation 2.2e-7 (float32 storage). Margin closure sum(head)+sum(mlp)+embed vs margin: max relative gap 2.6e-7. Option probs equal softmax of option log-probs to 7.8e-16. 0 units with d_margin == 0, so no prompted unit is secretly the base.

Sample of 12 (all marker sha ok, insertion exact, text equals neutral+sign, base_revision 0e9e39f249):

| unit | tokens A -> B | d_margin | parity gap nats | gap fp16 ulp |
|---|---|---|---|---|
| sp000001/Q195 | 170 -> 229 | -2.4195 | 0.0409 | 2.62 |
| sp000010/Q62 | 139 -> 198 | -8.0288 | 0.0157 | 1.00 |
| sp000110/Q59 | 137 -> 196 | -7.2590 | 0.0500 | 3.20 |
| sp001101/Q58 | 137 -> 196 | -9.8013 | 0.0665 | 4.26 |
| sp010001/Q103 | 133 -> 192 | -0.5578 | 0.0017 | 0.11 |
| sp010001/Q43 | 140 -> 199 | -1.2249 | 0.0190 | 1.22 |
| sp100000/Q99 | 127 -> 186 | +0.1600 | 0.0338 | 2.16 |
| sp100011/Q179 | 170 -> 229 | -3.8069 | 0.0485 | 3.10 |
| sp110110/Q43 | 140 -> 199 | +0.0428 | 0.0099 | 1.26 |
| sp110111/Q195 | 170 -> 229 | -2.7235 | 0.0584 | 3.74 |
| sp111001/Q103 | 133 -> 192 | +2.7880 | 0.0198 | 1.27 |
| sp111001/Q59 | 137 -> 196 | +3.6024 | 0.0337 | 2.16 |

## Check 3: archive parity: PASS-WITH-NOTES

Computed by me from the run manifests' `option_logprobs` and the `sign_profiles.json` archive (not from the manifest's own `archive_parity` flag). All 598 units.

- Max gap: 0.1124 nats (7.19 fp16 ulp at the archived value, unit sp100000/Q106). Median of per-unit max: 0.0353 nats (2.27 ulp). Max probability gap 0.0071.
- The code declares tau = 4 fp16 ulp (`cohort.archive_parity`, `fp16_ulp <= 4.`), and the note says "report-only". **102 of 598 units (17.1%) exceed 4 ulp.** The code's own flag agrees: 102 units with `archive_parity.pass == false`; 0 disagreements between my recomputation and the stored values; `fatal` is false everywhere, so the unit `pass` stays true.
- Control 1, the same statistic on the accepted phase-1 neutral base runs against their own archive: 4 of 23 over 4 ulp (17.4%), max 6.84 ulp, max 0.097 nats. The prompt route has the same rate and the same size of gap. This looks like fp16-CUDA vs float64-NF4-dequant arithmetic, not a defect in the prompt route.
- Control 2 (does the test discriminate?): scoring each unit against another profile's archive gives a minimum gap of 0.141 nats and median 1.42 nats; 598/598 exceed the worst true gap of 0.112. The match is to the right profile.
- Ranking: argmax equals the archive's in 597/598; the one miss (sp111110/Q176) is a tie in the fp16 archive (options 4 and 5 both -22.0625; the run has -22.0677 vs -22.0584). Full rank order agrees in 560/598; the 38 swaps all involve option pairs closer than 0.047 nats in the archive.

N1 (decision for Augusto, not a block): the 4-ulp tolerance is not met by 17% of units. The check is non-fatal by design and matches the base-run behaviour, so I treat it as expected numerical noise. Any figure should say "within about 0.11 nats / 7 fp16 ulp of the archived run", not "within 4 ulp".

## Check 4: resume did not mix states: PASS

- 598 distinct (profile, item) ids, 0 duplicates, exactly the 26 x 23 expected set, 0 missing, 0 extra.
- 598 markers `pass: true`; `RUN_STATUS.json` failed = []; no id both failed and passed. `attempts/*.json` (one per unit, 598) all `pass: true`; none repeated.
- The abort: `queue_detached.log` shows base_sp000001/wvs_Q101 killed at 130.19 s (rc -9, supervisor timeout 130 s), QUEUE_END aborted, done=36. That unit left no marker and no orphan files; its marker was written after the abort (rc 0, 32.3 s in `queue_resume_1845.log`).
- Markers older than the abort: 37 = 23 (sp000000) + 13 (sp000001) + 1 (sp111111/Q57). The 37th is the earlier 2-unit proof (with sp000000/Q43), matching LAUNCH_PROMPT_ROUTE.md. Markers after: 561. Total 598.
- Before vs after the abort: `source_digest` 843a4cf0 in all 598; frozen instrument hash 336531ca in all; one package-version set in all (torch 2.14.1, transformers 5.20.1, bitsandbytes 0.50.2, numpy 2.5.4, peft 0.21.2, safetensors 0.8.0). Recomputing `cohort.source_digest()` on the committed tree gives 843a4cf0, equal to every marker: the committed code is the code that produced the data.

## Check 5: wall-limit change: PASS (N3)

`git show 74d3a06 -- workbench/plans/gpu_cohort/runner/mac_queue.py`: the wall-limit change is `B0_SECONDS["prompt"] = 65.0` plus a `base_sp*` branch in `wall_limit()`; with WALL_FACTOR 4 that is 260 s. `wall_limit` is used in exactly two places: the queue's abort rule (`res.wall > wall_limit(key)`) and the `--timeout` passed to the unit supervisor (`cohort.supervise`: kill after timeout). Neither touches a gate, tau, or a manifest value. `mac_queue.py` is not in `source_digest`, consistent with it being a watchdog. The same commit also adds the prompt-route plumbing in the same file (`plan_route`, `unit_command`, `--prompt-route`, `--baseline`); that is new capability, not a change to existing checks. Tests: `test_gpu_cohort.py` (base 4 x 32.5, adapter 4 x 65.3 unchanged) and `test_prompt_route.py:231` pass.

N3 (provenance, not scientific): the committed parent (74d3a06^) sends `base_sp*` keys to the adapter limit (4 x 65.3 = 261 s), but the first 36 units ran under a 130 s limit (log: "above 4x B0 (130 s)"). So the in-run code was an uncommitted intermediate version of `wall_limit`. The commit message ("the plain-base limit aborted at 36/598") describes that intermediate state. It does not affect the data (the aborted unit was discarded and rerun, 598/598 pass), but the exact watchdog code for the first segment is not in git.

## Check 6: suite: PASS as asked, with a caveat (N2)

- `env -u PYTHONPATH HF_TOKEN= uv run --project workbench pytest workbench/tests -q` (run at the start of this verification): **176 passed, 4 skipped, exit 0** (23.13 s). Log: `.../scratch/w2v_pytest.log`.
- Re-run later in the same session: exit 1, 5 failed (test_deploy_bundle::test_real_archive_closure_and_manifest and four in test_sca2_story_data). All are in the two viewer test files that now show as modified (`git status`: `workbench/tests/test_deploy_bundle.py`, `test_sca2_story_data.py`, plus `workbench/scripts/build_deploy_bundle.py`, `build_sca2_data.py`, `workbench/viewer/public/sca2/index.html`). Another session is editing the viewer in this worktree. `test_prompt_route.py` + `test_gpu_cohort.py` alone: 44 passed, 1 skipped, exit 0. The failures are not in any W2 code path.

N2: the live worktree is not at a clean 7ba4d3a, so the full-suite number is only reproducible from a clean checkout. I could not make a clean-export rerun work (gitignored data is needed by some tests), so I am not claiming one.

## Notes summary
- N1: 17% of units exceed the declared 4-ulp parity tau (max 0.112 nats / 7.2 ulp); same rate as the accepted base runs; describe as ~0.11 nats, not 4 ulp.
- N2: concurrent uncommitted viewer edits break 5 viewer tests in the live tree; unrelated to W2; recheck on a clean commit.
- N3: the first-segment watchdog code (130 s limit) was never committed; no effect on data.
- N4: the commit message says "598 unit manifests, all pass ... unverified"; this report is the verification. The 17 GB output is gitignored and exists only on this Mac.

## Reproduce
```
env -u PYTHONPATH uv run --project workbench python <scratch>/w2v_check1.py          # exit 0
python3 <scratch>/w2v_check1b.py                                                      # exit 0
env -u PYTHONPATH uv run --project workbench python <scratch>/w2v_check234.py         # exit 0
env -u PYTHONPATH uv run --project workbench python <scratch>/w2v_extra.py            # exit 0
env -u PYTHONPATH HF_TOKEN= uv run --project workbench pytest workbench/tests -q      # exit 0 at start (176 passed, 4 skipped)
```
