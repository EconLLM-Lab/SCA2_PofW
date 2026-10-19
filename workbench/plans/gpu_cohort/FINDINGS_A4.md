# A4 pre-flight findings (task t_85412cb3)

Verifier: Claude Sonnet 5.5 (anthropic/claude-sonnet-5-5). Producer: GPT 6.1 Sol (first pass) + Claude Sonnet 5.5 (A3 resume pass).
Date: 2026-10-18 (MST). Root: the adapter-brain-vizualization worktree. Read-only except `$TMPDIR/a4/`, this file, and
dry-run exports in `workbench/exports/` (git-ignored). No Colab start/stop, no git write, no .env read, no card created.

## VERDICT: GO  (for LAUNCH.md step 1, the pilot only)

All six checks pass. The decision is recorded (DECISIONS.md:3, nf4_dequant, Augusto 2026-10-18) and DECISIONS.md:18-21
cites `paper_b/train_country.py:40-47`; I read those lines in the main repo and they do configure NF4, double quant,
fp16 compute and an fp16-loaded base. No finding below blocks the pilot. F1 should be fixed or acknowledged before the
full cohort (LAUNCH step 3), not before the pilot. Spending the 396 CU full-cohort budget stays gated on the pilot
review, as LAUNCH.md already says; this verdict does not approve it.

Bundle identity at review time: `cohort.tar.gz` sha256 f872391cc572275b92f6061eec8b862a68b6e799f0dd2e3795bf20de745bf16f
(equals `cohort.manifest.json`; all 34 bundled files re-hashed against the worktree: 0 stale; no .env / paper_b /
respondent / .pyc / weight names in the tar).

## Check results

1. Models: PASS. Own script (`$TMPDIR/a4/check1.py`, not `inventory.py`), exit 0.
   Hub dataset `Bonorinoa/SCA2-paper-b-adapters` resolved sha == pinned c4b0f36e... ; 42 weight files at
   `adapters/<CC>/adapter_model.safetensors`; "match 42 / 42 bad []" on sha256 (LFS), bytes, r=16, alpha=32, targets
   [k,o,q,v]_proj, read from the config fetched via /resolve/<rev>/. Also downloaded ARG weights: sha256
   b39cd5d0...499a == models.json. Base revision 0e9e39f2... is the local snapshot/ref name; the Hub itself returned 401
   unauthenticated for the gated base config and for the private artifacts repo (recorded, expected; no token file exists
   on this Mac), so the base pin is confirmed from the cache, not from the Hub.
2. Dry run: PASS. Different pair from A3's (ARG x Q57): BRA x wvs_Q176 (T=172), nf4_dequant, CPU, fresh dir.
   `verify_local.py --model BRA --item wvs_Q176 ... --publish-viewer` -> exit 0, "BYTE_IDENTICAL", real SIGKILL at layer 8
   (supervisor_exit 247 = -9), resume, verified-skip. My own `shasum` diff of baseline vs resumed immutable files (11
   files incl. index.json and unit marker): IDENTICAL. All fatal conservation checks true on both arms and the pair; peak RSS
   7.21 GiB (limit 16 GB decimal). Viewer sweep `sweep.mjs workbench/exports/index.json` (live vite on :5178, serving this
   worktree): exit 0, 24 pairs, 120 loads, 0 failures, 0 console errors.
   Test suite: `pytest workbench/tests` with bitsandbytes 0.50.2: 122 passed, 3 skipped, exit 0 (matches A3).
   `bootstrap.py --check-local`: LOCAL_PREFLIGHT_PASS, exit 0.
3. Gates through the runner path: PASS. `unit.py --corrupt-mlp-layer 15` with a test hook (`$TMPDIR/a4/sc/sitecustomize.py`,
   wraps the real `run_streamed_pair`, scales the stored MLP write of ONE token by 1.001, not all tokens).
   - token 171 of T=172 (readout token, non-zero): exit 2; run manifests fail residual_closure, step_closure and both
     clamped variants (rel 6.7e-6 .. 5.8e-4 vs tau 1e-13 / 1e-14); unit marker pass=false; runs + pair stayed in index.json.
   - token 50 (mid prompt): exit 2, same four checks fail on both run manifests.
   - Published the token-171 fixture to workbench/exports (`..._corrupt_l15` keys) and loaded it in the viewer: `#status`
     class "status bad", red border rgb(255,95,86), text "x 8 of 24", full-width red banner "8 checks failed ... do not
     read them as measurements until the export is fixed" (screenshot `$TMPDIR/a4/viewer_corrupt_bra.png`, 0 console
     errors). The same pair uncorrupted shows "status ok", "24" (`viewer_ok_bra.png`).
   - Note: the pair manifest itself reports conservation.pass true for the corrupted pair; the failure is carried by the two
     run manifests and the unit marker. Fine as long as the queue keys on the marker (it does, cohort_queue.py:72-74).
4. Estimate: PASS on arithmetic and storage; the time/CU inputs are pessimistic by more than 25% (direction is safe). See F5.
   - Storage: I recomputed bytes from estimate.json sizes: 43*sum(run)+42*sum(pair) = 24,498,237,328 B, identical to
     `binary_export_bytes`. Predicted per-item sizes equal real files byte for byte (Q176 run 25,776,960 / pair 796,592;
     Q57, Q81, Q107 also match). Real manifest JSON is ~51 kB (run) / 4.6 kB (pair), so the 100 kB allowance overstates
     JSON by 3.5x: 24.55 GB real vs 24.69 GB stated (0.6%).
   - Hours: (23*103.519 + 966*103.519)/3600 = 28.44 h + 0.5 setup + 1.372 sync = 30.311 h; x13.08 = 396.47 CU. Reproduces.
   - Pilot envelope: 46 units = 1.3227 h + 0.0628 h sync + 0.5 h = 1.886 h = 24.66 CU. Reproduces.
5. Safety: PASS. No respondent/human fields in `items.json` (keys: item_id, user_prompt, codes, labels, parts, archive
   {source, probs, logprobs} per model arm). `pack_inputs.py` only globs `*_option_probabilities.csv`. grep over runner/ and
   cohort.py/nf4_source.py/items.py/bank.py finds no `.env`/dotenv reads; the only secret path is Colab `userdata.get("HF_TOKEN")`.
   Every Hub write (`sync.py:45`, `bootstrap.py:76,99`, `cohort_queue.py:79`) targets `Bonorinoa/SCA2-paper-b-artifacts` under
   `workbench_cohort/<run>/` (`check_prefix` rejects anything else); the adapters repo is only read. No `adapters/<CC>` write
   exists. LAUNCH.md abort steps: every `colab` verb and flag used (`new --gpu A100 --high-mem`, `upload`, `exec -f --timeout`,
   `download`, `stop -s`, `sessions`) exists in `colab <verb> --help`. The abort sequence itself is UNTESTED (it would need a
   live stop, which the fence forbids). The per-process 8B lock works: a second `unit.py` while another 8B unit ran died with
   BlockingIOError at cohort.py:379 (cryptic traceback, but it did not run).
6. Decision: PASS. DECISIONS.md:3 "capture target: nf4_dequant, decided by Augusto 2026-10-18". No "pending Augusto" string.
   LoRA F32: `offload_hf.py` diff keeps file tensors at file dtype and compares against the file bytes (no `.to(dtype)`); test
   at `test_gpu_cohort.py:116-123` asserts float32. Both weight modes were exercised by A3 (not re-run by me; only nf4_dequant
   was re-run, which is the phase-1 target).

## Numbered findings

F1. MEDIUM. Full-cohort launch fails after a session stop, because PILOT_VERIFIED.json is never restored.
    `cohort_queue.py:47` requires a local `/content/cohort_exports/PILOT_VERIFIED.json` for the non-pilot queue; it is
    written locally at :76 and uploaded at :80, but `sync.restore()` (sync.py:21) only restores `units/*.json` markers.
    LAUNCH.md:127-131 recommends stopping the session after the pilot ("idle bills"), and LAUNCH.md:141-150 then launches
    the cohort from the same exec with no mention of this. On a fresh VM, step 3 raises "pilot verification missing"
    after paying setup. Recovery is documented only in section 5 (re-run the pilot; verified units skip). Fix: add a line to
    LAUNCH step 3 ("after a restart, run colab_pilot.py again first") or restore the marker from the Hub in `restore()`.
    Evidence: `grep -n PILOT_VERIFIED runner/*.py` -> only cohort_queue.py lines 47,76,80,81,83,85.

F2. LOW-MEDIUM. Disk guidance has a thin margin. LAUNCH.md:47 says ">=100 GB". My inferred need (not measured): 24.7 GB exports
    + ~24.7 GB HF cache, because `sync.upload_unit` reads every uploaded file back via `hf_hub_download` (sync.py:48-52) and
    those blobs stay in the cache + 16 GB base + 3.6 GB NF4 + two venvs with torch cu130 (~12-16 GB) = roughly 90-95 GB.
    ESTIMATE.md does not count the cache doubling. Suggest `df -h /content` at pilot end and extrapolate (pilot = 1.13 GB of
    exports), or purge the readback blobs.

F3. LOW. `keepalive.py` exec uses `--timeout 3600` (LAUNCH.md:103,144) but the cohort is estimated at tens of hours.
    A single keepalive therefore ends after an hour; LAUNCH.md:146-147 says "its own terminal" but not that it must be
    re-run hourly. Write the loop into LAUNCH or the operator will think the job died.

F4. LOW. Doc/code conflict, surfaced not resolved. DECISIONS.md:102-104 says archive parity is "absolute tau=1e-3"; the code
    (`cohort.py:76-103`), manifests and `spec/conservation.md:115` use tau = 4 fp16 ulp. ESTIMATE.md:36 and LAUNCH.md:122 also still
    quote 1e-3. PROGRESS.md:40 and A3_HANDOFF.md:17 state ulp. Update DECISIONS/ESTIMATE/LAUNCH so Augusto does not read the wrong threshold.

F5. LOW (safe direction). Time and CU inputs are above measurements by more than 25%:
    - per-unit allowance 103.52 s vs measured Mac max 78.2 s at the longest item (B0 bench, `benchmark/mac/out`) = +32%;
      base units are budgeted like adapter units but measure 30-36 s on the Mac (3x).
    - Mac-measured recompute (966 x 65 s + 23 x 33 s, +0.5 h +1.37 h) = 19.5 h; stated 30.31 h = +55%.
    - In-flight A100 numbers from the B0 benchmark session (another card; not reviewed by me, logs only:
      `benchmark/a100/vm_all.out`, `cu_watch.log`): setup 2.62 min (assumed 30 min), ARG unit ~80 s, base unit ~59 s, 80 GB
      A100, usage 6.77 CU/h (assumed 13.08). With those: ~23.3 h and ~158 CU, so stated 30.3 h is +30%, 396 CU is +150%.
    The 35 CU pilot cap in code counts at 13.08 CU/h, so it fires at ~2.7 h of queue time, which is about 18 real CU at 6.77 CU/h;
    it will not trip early. After the pilot, replace the assumptions (estimate.py takes `--cu-per-hour`; the seconds are
    hard-wired to the Mac evidence files) as LAUNCH step 2 already says.

F6. INFO. Hub commit rate is unverified. Each unit is one `upload_folder` commit (sync.py:45), 989 in the cohort, with 3
    attempts and 2 s/4 s backoff (cohort_queue.py:62-68). HF documents per-action commit limits but does not publish the number
    (hub docs, rate-limits page). At ~60-100 s/unit this is ~35-60 commits/h. If the pilot shows a much faster unit, watch for 429s.
    A rate-limit failure aborts the queue after retries rather than corrupting data.

F7. INFO. Archive parity (report-only) will fail on some units. In my BRA x Q176 run: max 4.125 ulp (base arm) and
    4.107 ulp (BRA arm) vs tau 4, `archive_parity.pass false`, `fatal false`; conservation stays true. LAUNCH.md:122 already warns.
    The pilot's "failed: 0" counts conservation, not parity; do not describe a parity-false unit as matching the archive.

F8. INFO. The package changed while under review. A new `benchmark/` directory (bench_units.py, vm_all.py, prepare_nf4_bench.py, ...)
    appeared at 11:58-12:01 from another card (B0), which also ran an 8B unit on the Mac (it held `.cohort-8b.lock` until ~12:04; I
    waited and then ran mine) and started an A100 session named `b0-a100` (visible in `colab sessions`; I did not touch it). The 34
    bundled files and the bundle hash are unchanged, so this verdict covers the bundle above. `benchmark/` is not in the bundle.

F9. LOW. `benchmark/` (246 MB, including `benchmark/mac/out/*.bin`) is not covered by the package `.gitignore`, which lists
    `local_nf4/`, `debug_capture/`, `dry_run*/`, `*.tar.gz`, `.cohort-8b.lock`, `test_tmp*/` only. `git add` of the package would take it.
    Not mine to edit; flagging for whoever commits.

F10. INFO. Coverage notes. (a) `cohort_probe.mjs` hard-codes item `wvs_Q57`; I used my own copy for Q176. (b) The CUDA path was not
    exercised by A3 (no A100); the in-flight B0 log shows float64 ARG/base units finishing "ok" on an A100 (peak ~5.7 GB VRAM),
    which is not my evidence. (c) I did not run `npm run build` (writes dist/); A3's `viewer_build_f5.log` is the record, and my
    sweep ran against the current source through the vite dev server.

## Commands and exit codes (all run from the worktree root, `env -u PYTHONPATH uv run --project workbench ...`)

    check1.py (own Hub re-list)                         exit 0   $TMPDIR/a4/check1.out
    verify_local.py --model BRA --item wvs_Q176 ...     exit 0   $TMPDIR/a4/dry_BRA_Q176.log (killed_exit 247, BYTE_IDENTICAL)
    shasum baseline vs resumed (diff)                   exit 0   IDENTICAL
    node sweep.mjs workbench/exports/index.json         exit 0   $TMPDIR/a4/sweep.out (24 pairs, 120 loads, 0 errors)
    unit.py --corrupt-mlp-layer 15 + hook token -1      exit 2 (expected)  $TMPDIR/a4/corrupt_last/
    unit.py --corrupt-mlp-layer 15 + hook token 50      exit 2 (expected)  $TMPDIR/a4/corrupt_mid/
    node probe.mjs (corrupt pair / ok pair)             exit 0 / 0   status bad (red) / status ok
    pytest workbench/tests (+bitsandbytes, psutil)      exit 0   122 passed, 3 skipped, 28.79 s
    bootstrap.py --check-local                          exit 0   LOCAL_PREFLIGHT_PASS
    peak RSS of my 3 captures: 7.21 / 6.78 / 7.74 GiB (max 8.31 GB decimal), under the 16 GB stop line.

Files I added under the project root: 12 files in `workbench/exports/` (BRA x Q176 ok pair + corrupt fixture; git-ignored) and this
file. The corrupt fixture is intentionally red and is not a production input.
