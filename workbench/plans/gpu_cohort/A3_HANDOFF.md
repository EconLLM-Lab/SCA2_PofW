# A3 handoff (for A4 review and Augusto)

Task t_d65297a1. Route: first pass openai-codex/gpt-6.1-sol, resume pass
anthropic/claude-sonnet-5-5. Root: the `Adapter-Brain-Vizualization` worktree.
Nothing is committed. No GPU or Colab runtime was started (`colab sessions`:
"No active sessions", `colab_sessions_resume.log`). No Hub write. No .env read.

## Verdict

Package is ready for review. Nothing here is a measured A100 result. The only
CUDA-side figures are assumptions, and LAUNCH step 1 is the pilot that replaces them.

## What is decided

- Capture target: nf4_dequant, decided by Augusto 2026-10-18 (DECISIONS.md).
  Training also used NF4 (`paper_b/train_country.py:40-47`, cited there).
- Parity unit per A2 F5: report-only, <= 4 archived fp16 logprob ulp, probability
  gap descriptive. Conservation gates stay fatal.
- Phase 2 (`--weights unquantized`) works and is tested, not scheduled.

## Numbers and their source

- 30.31 GPU h / 396.47 CU, no-speedup envelope at an assumed 13.08 CU/h:
  `estimate.json`, rebuilt by `runner/estimate.py` (exit 0, output identical to
  the stored file). ESTIMATE.md and LAUNCH.md agree. PROGRESS.md had 32.7 h /
  427 CU in an early draft; that was wrong and is fixed.
- Pilot envelope (new): 46 units, 1.3227 h compute + 0.0628 h sync + 0.5 h setup
  = 1.886 h = 24.66 CU (ESTIMATE.md "A100 pilot", arithmetic shown).
- Storage 24.694 GB binary exports + 3.601 GB frozen NF4 (`estimate.json`).
- 42/42 adapters, all r=16 alpha=32 q/k/v/o, none exceptional; dataset revision
  c4b0f36eae0c15e508f72b606861798c8359131f, base
  0e9e39f249a16976918f6564b8830bc894c89659 (`models.json`, `inventory.log`).
- Tests: 122 passed / 3 skipped (`tests_resume_final.log`, command in LAUNCH.md
  step 0). The 3 skips are Llama-3.2-1B configs not in the cache (403).
  Without `--with bitsandbytes` one more test skips.
- Local dry run (CPU, bnb 0.50.2): ARG x wvs_Q57, SIGKILL at layer 8, resume,
  byte-identical, for nf4_dequant and unquantized (`dry_run_nf4_f5*`,
  `dry_run_unquantized_f5*`). Base-unit rerun this pass: byte-identical to the
  baseline base run (sha256 in PROGRESS.md). Peak RSS 7.15-8.28 GB, under 16 GB.
  CPU codes can differ from CUDA codes; this is diagnostic, not a CUDA replay.

## Source changes: who wrote what (A4: look harder at the Claude lines)

Written by GPT 6.1 Sol (first pass): `git status` shows modified
`workbench/spec/conservation.md`, `workbench/spec/export_contract.md`,
`workbench/src/sca2_workbench/offload_hf.py`, `stream_capture.py`,
`stream_export.py`, `workbench/viewer/src/common.ts`, `data.ts`; new
`workbench/src/sca2_workbench/cohort.py`, `nf4_source.py`,
`workbench/tests/test_gpu_cohort.py`, `workbench/viewer/screens/v3/cohort_probe.mjs`,
and everything under `workbench/plans/gpu_cohort/runner/`.

Written by Claude Sonnet 5.5 (this pass), by file and line:

- `workbench/plans/gpu_cohort/runner/cohort_queue.py`
  - lines 15-19 `plan()`: pilot is now base + ARG x every item (was Q57 only);
  - lines 22-26 `check_cu_budget()`: raises once elapsed queue time x rate > cap;
  - lines 35-37: `--pilot` help text, new `--max-cu`, `--cu-per-hour`;
  - lines 46-48: use `plan()`; the PILOT_VERIFIED requirement is unchanged;
  - lines 49-52: `started` timer and the cap check before each unit.
- `workbench/plans/gpu_cohort/runner/vm_job.py`
  - line 10 `PILOT_MAX_CU = 35`;
  - lines 36-43 `queue_command()` extracted from `driver()`; pilot adds
    `--pilot --max-cu 35 --cu-per-hour <assumed_cu_per_hour>`;
  - line 48 `driver()` calls it. The cohort command is unchanged.
- `workbench/tests/test_gpu_cohort.py` lines 210-245: `_load_runner` plus three
  tests (pilot plan, CU cap, pilot command carries cap). RED first
  (`RED_pilot.log`, exit 1), then GREEN.
- Docs: `LAUNCH.md` (step 1 is the pilot; preflight adds the HF_TOKEN secret +
  whoami check; abort criteria add the pilot CU caps), `ESTIMATE.md` (pilot
  section), `PROGRESS.md` (number fix, resume pass), this file.

Not enforced in code: the 50 CU session cap, and any CU cap on the full cohort.
Both are operator checks against the Colab balance. The 35 CU queue cap counts
elapsed queue time at the planning rate 13.08 CU/h, not the real Colab rate.
`vm_job.py` and the queue cannot run here (they need `google.colab` and a CUDA
VM); only the pure functions are tested.

## Verified limitations and open items

1. No A100 pilot yet. The cohort budget stays uncommitted until it runs.
2. The private artifacts repo returns 401 from the Mac (expected, no token). The
   Hub upload/readback path is exercised only by a mocked test plus the VM
   preflight. Treat the first VM minutes as the real test.
3. The base 8B was not freshly downloaded through the Hub this pass; it came
   from the local cache.
4. The Colab CU rate (13.08/h) is a planning assumption, not a quote.
5. A2 findings F3/F4 (claim-table row, four .pyc files under paper_b) do not
   affect A3 and are the PM's to close.
6. The viewer was not re-swept this pass. Its source is unchanged since the
   sweep (exit 0) and corruption check (exit 2, red) recorded in PROGRESS.md.
7. The Inkling-era `dry_run_base_f5` directory was deleted and rebuilt. Other
   `dry_run_*` directories are kept as evidence and are git-ignored.
