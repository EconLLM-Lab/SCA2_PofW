# A3 progress

Route: openai-codex / gpt-6.1-sol. No commit, GPU launch, Colab start/stop, or paper-number edits authorized.

## Orientation
- Read capture@1.1, calibrated gates including step_closure, Stage 1 log, A1 memo, A2 findings, PM steering, and Colab mechanics.
- HEAD 0469f80e3d80803a9bee4873766869c2362a4425; worktree initially clean.
- Capture target remains pending Augusto; implement both modes without choosing the scientific target. Archive probability parity remains report-only at 1e-3 (A2 resolution-floor caveat applies).
- HF_TOKEN absent as expected. Public adapter metadata listing succeeds without credentials; only USA is cached initially. No credential files read. Dataset snapshot c4b0f36eae0c15e508f72b606861798c8359131f exposes cohort adapters at adapters/<CC>, separately from bank2/replicates.
- A4 pre-created reviewer child t_85412cb3 inspected; implementation completion will release it, not request duplicate same-card review.

## Item 2 — pinned model inventory completed
- `runner/inventory.py` re-listed Hub metadata and downloaded all 42 cohort configs. `models.json`: 43 models, 42 adapters; all r=16, alpha=32, q/k/v/o targets; no exceptions. Weight SHA256 values are Hub LFS digests, not a claim that all 42 weight blobs were downloaded. ARG's actual downloaded bytes were checked by the runner.
- Command in `inventory.log` returned exit 0. Dataset revision c4b0f36eae0c15e508f72b606861798c8359131f; base 0e9e39f249a16976918f6564b8830bc894c89659.

## Item 3 — runner implemented RED then GREEN
- `test_gpu_cohort.py` was written first; `RED.log` records the missing-module failure, exit 2. Initial GREEN: exit 0; later tests cover real NF4 serialization, exact F32 LoRA, immutable persistence, retained failed pairs, exact-commit sync, listing failures and CLI imports.
- `runner/pack_inputs.py` packages all 23 strict questionnaire items and 43 model-only archive arms in `items.json`; no respondent data or paper modules enter the runtime bundle. First attempt exposed the hidden editable-install `.pth` problem; wrappers now explicitly add workbench/src, and the rerun exited 0.
- A real CLI failure caught `queue.py` shadowing the Python stdlib; renamed it to `cohort_queue.py` and added a subprocess regression. Failed evidence is retained in `dry_run_nf4_v1` / `dry_run_nf4.log`.
- Exports are immutable; only the index is atomically replaceable. Source/device/instrument-qualified keys allow different capture versions to coexist. Unit restart recomputes only the interrupted unit, verifies existing bytes, and skips only a hash-checked passing marker.
- HF float32 reference uses the same effective weights but independent HF modelling code. Archive parity is separate and report-only. CUDA NF4 preparation uses a separate historically pinned loader environment, preserving codes and quantization state before any capture.

## Augusto decision received during work
- The operator superseded PENDING: Phase 1 is nf4_dequant for base + all 42 adapters; unquantized remains a tested Phase-2 hook, not a cohort run now.
- Read main-repo `paper_b/train_country.py:40-47`: QLoRA training itself uses NF4/double quant/fp16 compute. No edits there.
- HF default token resolution is allowed; neither an env token nor a default token is available here. Private artifact metadata returned 401 (`memory_and_auth.log`); no remote write was attempted. Colab must obtain HF_TOKEN from a secret. Public model inputs/caches suffice for the local proof.

## Item 5 — local proof completed, final namespace check in progress
- Real ARG (not USA) × wvs_Q57 captures pass every fatal gate. Both weight modes passed SIGKILL-at-layer-8 / resume / verified-skip byte comparisons (8 files each, including index and unit marker). Raw timing/hash evidence is in the dry_run directories; each source-version iteration is retained.
- Viewer sweep exited 0. The added visible-label probe verifies nf4_dequant and report-only archive text, then captures an actual screenshot (`viewer_nf4.png`).
- Runner-path layer-15 MLP write ×1.001 returned expected exit 2; failed run manifests stayed indexed. `viewer_corruption.log` records a red status with zero console errors; screenshot retained.

## Item 4 — first complete estimate computed
- `estimate.json` sizes every item's array layout: 43 run sets plus 42 pair sets per item (adapter run arrays are also needed by the viewer). Initial total 24.694 GB including a 100 kB/manifest allowance, plus the frozen NF4 instrument (~3.601 GB CPU diagnostic).
- A100 has NOT been benchmarked. Conservative no-speedup, longest-item-for-every-unit budget is ~30.31 GPU h / ~396.47 CU at an assumed 13.08 CU/h (corrected 2026-10-18 by the resume pass: an earlier draft here said 32.7 h / 427 CU; `runner/estimate.py` reproduces 30.31 / 396.47 byte-identically in `estimate.json`), including setup and 10 MB/s upload/readback. This is an intentionally pessimistic planning envelope, not measured A100 performance; an actual GPU pilot must replace it before committing the cohort budget.

## Resume pass (claude-sonnet-5-5, 2026-10-18 ~11:25-11:50) — verify and finish

- Inkling-era base-unit rerun (`dry_run_base_f5/`): the unit had finished (marker `pass: true`, rc 0) but its stdout log was incomplete, so it was deleted and rerun with the same F5 code. New output is byte-identical to the GPT-era NF4 baseline base run (`.bin` sha256 f6f8cd3f...677f5, `.json` sha256 cab0e9e4...7652e; 21,491,360 + 46,030 B). Capture 21.65 s, total 32.26 s, peak RSS 7.15 GiB.
- Parity block in ulp confirmed in the manifests: `unit: archived fp16 logprob ulp`, `tau: 4.0`, `fatal: false`. Base Q57 max 2.985 ulp / 0.0466 nats; ARG Q57 max 2.591 ulp / 0.0405 nats.
- Test count: 119 passed / 3 skipped after F5 (`GREEN_F5.log`); the "117" in the earlier handoff predates F5. Plain `pytest` without bitsandbytes skips one more test.
- Estimate/LAUNCH agree: 30.31 GPU h / 396.47 CU. PROGRESS draft corrected (above).
- LAUNCH step 1 is now an A100 pilot: base + ARG x all 23 items (46 units), queue CU cap 35 in code, 50 CU session cap by the operator. Source change RED first (`RED_pilot.log`, exit 1) then GREEN: 122 passed / 3 skipped (`tests_resume_final.log`). Pilot envelope 24.66 CU in `ESTIMATE.md`.
