# A1 progress — t_ef474f3c

## Orientation
- Root HEAD confirmed: 26146b303e23625205f9b7822cb6da84b6166e60, feat/paper-b-cohort; pre-existing untracked .worktrees/.
- No paper, model–human join, or human-mean file opened. Only model-only scores, source code, and permitted claim/aggregate tables will be read.
- Material premise qualification: archive loader is NF4/double-quantized with float16 compute; workbench reference is unquantized float32/float64. Comparing the same sequence_logprob function does not compare the same weight representation.
- Archive manifests record code bundle digest f3279d6c85524a14dc0d591c1d169553e2380d839dd28062f5214b4984f1ba12, not a commit SHA. Earliest tracked snapshot found: 86fbf1030db9d126b6b354d2d424f3da1f130d37, after the archived run.
- Process HF_TOKEN is absent. Do not access any credential file; cached model and public unauthenticated metadata remain available.
- Terminal TMPDIR initially pointed at system temp; explicitly reset to /Users/bonorinoa/.hermes/profiles/engineer/cache/scratch for all subsequent temporary work.
- Downstream A2 review card inspected; completion of A1 releases it, if acceptance can be met.

## Step 1 — writer investigation
- Ran inspect_provenance.py (exit 0), outputs writer_inspection.json/.log. Raw Hub model-only CSVs match manifest hashes; scores_for_join adds option_value (numeric equality verification follows).
- Writer is consistent with paper_b/colab/vm_cohort.py, strict scoring spec ed3bb964b606a163c792a68eea2ea9e6cc679bb724ead6726c173f36d9a1fbf6 and frozen NF4/fp16 loader. The earliest tracked snapshot is NOT a verified producing commit: none of the 67 available paper_b-changing commits matches the archived Python-bundle digest.
- Public downloads reverified both adapter revisions byte-identically, including config; weight-file hash 7329c4a1e621d86fdc32c55b47b5fda047830404dc0d697ec468febe19717eef; bundle hash a35edd11a52d4a5fa49eece7e64b53112123e4a6691f6a87cd2df8611a197d3c matches manifest.
- Private artifacts Hub returned HTTP 401 without a process HF_TOKEN. No credential-file fallback attempted. Exact historical bundle remains unavailable.

## Step 2 — model-free diff
- Created detached temporary worktree at the earliest source snapshot (worktree_add exit 0); explicitly a proxy, not a claim that the archive was generated at that commit.
- render_prompts.py old and new runs exit 0 (initial KeyError corrected; logs now hold successful runs). Full UTF-8 hex, prompt IDs, completion IDs and source functions saved in prompts_old.json/prompts_new.json; comparison in prompt_comparison.json.
- Strict specs hash-identical to the archived manifest. All five rendered prompts/completion grids byte-identical; no truncation; base and USA use the same unconditioned prompt. sequence_logprob, prepare_prompt_for_model, and loader source are identical. Prompt builder gained optional variants, but v1 output is unchanged.
- Q262 is absent from the cohort-1 strict archive. Selected Q57, Q58, Q81, Q106, Q107; the separate August/bank-2 archive-gate discrepancy is not silently substituted for a cohort-1 row.

## Step 3 — one-difference-at-a-time isolation (running)
- CPU bitsandbytes 0.50.2 NF4 plus compressed-statistics probe succeeded (exit 0), allowing a diagnostic NF4 replay without CUDA. It is NOT the historical CUDA image.
- Baseline Q81 base prefix factorization checked against unmodified sequence_logprob, exit 0; reproduced the workbench's current float32 scores exactly. Initial RSS hook returned an integer and was corrected to return None before successful scoring; no model outputs from that failed attempt are used.
- run_replays.py now runs one child at a time: unquantized float32, then unquantized float16, then NF4/dequantized float16 linear algebra, both base/USA, all five items. Each also saves separate fp32/fp16 score-reduction results. Every module hook checks peak RSS against 16,000,000,000 bytes. All tensors are CPU-only. Raw commands and exit codes accumulate in replay_commands.json.

## Resume — run 33
- Rechecked live processes: previous NF4 base process had exited; its command ledger records exit 0. No duplicate 8B process started.
- Resumed run_replays.py, which skipped the five completed variants and ran only NF4 USA, then supplemental Q262 variants serially. NF4 USA exit 0; supplemental variants still running.
- Added bounded diagnostic CLI controls for double quantization, Linear compute dtype, and quantization type; model-free regression tests failed first (cli_red.log, exit 1), then passed after the change (cli_green.log, exit 0). Only provenance scripts changed.
- Source trace confirms today's Colab drivers still call the NF4/double-quant/fp16 loader, including the sign-prompt cell. The workbench supplies the unquantized reference; it is not today's Colab loader configuration.

## Step 5 — blast radius refresh
- Refreshed coverage for the new C7 status table at HEAD a1d75aec34837b6a3ba4dbac93786fc5bdb2447d. Model-free regression tests first caught headers/status rows being treated as legacy Paper A inference (trace_red.log, exit 1), then passed with explicit status provenance (trace_green.log, exit 0).
- NUMBERS_TABLE currently contains 212 rows; C7 declares 220 and a different digest. This conflict is reported on the card, not repaired. All original aggregate table cells are preserved in blast_radius_numbers.csv. No human means or model–human joins were opened.
- Exact archive writer commit remains unresolved; the proxy worktree must still be removed before completion.

## Step 3/4 — bounded follow-up
- NF4 USA and Q262 f32/f16/NF4 all completed, run_replays.py exit 0. No candidate yet reproduces the full five-item × two-arm panel at 1e-3. Q81 USA is close under NF4, but Q107 USA remains outside tolerance.
- Launched only the predeclared no-double-quant, float32 Linear compute, and FP4 swaps on Q57/Q81 × base/USA (one child at a time). These are diagnostics, not candidate fitting; default full-panel NF4 output stays unchanged.
- Removed the clean detached proxy worktree with git worktree remove (exit 0), without --force. Raw command/readback evidence: worktree_cleanup.json.
- Runtime evidence initially failed because the pair8b source path was mislocated; corrected to the discovered plans/scripts/pair8b.py. Successful inspect_runtime.py exit 0; no model output came from the failed inspection.
- External update resolved the earlier C7/table mismatch: refreshed blast_radius_summary.json now records 220 rows and sha256 90f0f467ccd9f92e762d906d434059f4105c7c5e5522eaa731a42a8aeff0ec1f, matching the lock. A1 made no table/lock edit. Claim-lock table body coverage is 23 rows.

## Diagnostic self-review and correction
- Initial bounded swaps finished with exit 0 (isolations.log / isolation_commands.json). Every swap fails a base-model Q81 row at 1e-3, so expanding those failed configurations to the full panel is unnecessary.
- Found an additional diagnostic error: offload_hf casts LoRA weights to forward dtype; the saved adapter has 256 F32 tensors. Promoting a half-rounded copy back to float32 is not the production file. Base/f32 runs are unaffected.
- Added restore_lora.py and a small-tensor, no-8B regression. Exact file equality failed under the original promotion-only behavior (lora_red.log, exit 1), passed with explicit file restoration (lora_green.log, exit 0).
- After the first isolation runner exited, changed only provenance/evaluate_stream.py to restore exact file tensors. run_exact_lora_repair.py now preserves rounded raw USA outputs and reruns the affected f16/NF4/full-panel and parameter swaps, one process at a time. Do not use rounded_lora_replay_* in the canonical memo table.
- build_report.py and finalize_evidence.py are ready but must run only after repairs complete. Planned verdict is NOT REPRODUCED, with the exact source-bundle/CPU-CUDA limits explicit; no false producing-commit claim.

## Final result / stop rule
- Exact-LoRA repair finished, exit 0. Canonical comparison uses restored adapter-file values; superseded rounded outputs and hashes are retained. No more model search is authorized or needed for the elimination memo.
- Wrote ARCHIVE_PROVENANCE_20261018.md, comparison_panel.csv, report_summary.json and raw evidence. Verdict NOT REPRODUCED: Q81 USA NF4 probability gap is 8.020551878207272e-08, but 6/10 full-panel rows fail 1e-3; worst is Q107 USA at 0.011411074867888338. See replay_nf4_USA_adapter.json and report_summary.json.
- All 220 NUMBERS_TABLE rows and 23 claim-lock table body rows traced; the final table matches C7. Today's production Colab paths remain NF4; the workbench is unquantized. Recommending a production-NF4-derived explanation reference, with parity plus conservation gates, for Augusto's decision.
- Finalize command: env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python planning/sprint_2026-10-11/paper-b-tier1/provenance/finalize_evidence.py — exit 0. Each child command/exit is in final_commands.json; verify_provenance.py passes 9/9 evidence checks. No reproduction pass is implied.
- Important fence exception: the first A1 imports refreshed four Python 3.12 __pycache__ files in paper_b. protected_mtime_audit.json/.log and the memo disclose this; no outside-fence cleanup attempted. Future launchers disable bytecode writes. A2 must distinguish those from concurrent C7 source edits and Python 3.14 caches; clean git diff is not a zero-write claim.
- Exact writer commit/source tarball and local copier identity remain unresolved. No HF_TOKEN, no private Hub audit, no historical CUDA replay. Proxy worktree removed. No commit/push or paper-number/source change by A1. Model route: openai-codex / gpt-6.1-sol.
