# Cohort cost and storage estimate

This is a measured Mac dry run plus an explicitly conservative A100 planning
model, NOT an A100 benchmark. No GPU runtime was started or charged by A3.
Numbers below are rebuilt by `runner/estimate.py`; machine-readable ground truth
is `estimate.json`. Do not turn an assumed speedup or CU rate into a measured fact.

## Measured local execution

ARG (a new adapter, not USA), wvs_Q57, T=132, float64 arithmetic, 8 CPU threads.
Each adapter unit streams base/plain, base/clamped, adapter/plain and
adapter/clamped, then performs two independent float32 HF reference forwards.

| Mode | Capture only | Capture + reference/export | End-to-end baseline | Resume execution | Observed peak RSS |
|---|---:|---:|---:|---:|---:|
| nf4_dequant | 36.965 s | 56.944 s | 63.853 s | 54.075 s | 8,282,439,680 B |
| unquantized functional hook | 39.868 s | 81.301 s | 88.500 s | 84.382 s | 7,631,290,368 B |

Sources: `dry_run_summary.json`, `dry_run_nf4_release/verification.json`,
`dry_run_unquantized_release/verification.json`, and their `attempts/*.rc.json`.
RSS here is the watchdog's observed process RSS, not a mislabeled GiB value.
Both modes pass 24 fatal run/pair checks; all eight immutable files (two runs,
one pair, index and unit marker) are byte-identical after a real SIGKILL at layer
8 and resume. Attempt logs/timing are intentionally separate and not identical.
Standalone NF4 base unit: 22.396 s capture, 31.732 s through reference/export,
38.651 s supervised wall, peak 7,639,236,608 B; its run JSON/bin are byte-identical
to the base embedded in the adapter pair (`storage_and_base.log`,
`estimate_crosscheck.log`).

The first cold CPU diagnostic prepared the 224 NF4 code/state files as it streamed:
113.931 s capture, 144.899 s through export, 166.175 s supervised wall
(`debug_capture/attempts/ARG_wvs_Q57_1792340545115599000*`). That is not a CUDA
quantization timing. Warm measurements above reuse those frozen codes.

Archive probability parity is NOT all green: on the NF4 local proof, base max
|Δp|=0.0014449538807423945, ARG
max |Δp|=0.00016150858384700317 (absolute probability gaps, descriptive only; the
report-only parity verdict is tau = 4 fp16 ulp, A4 F4, and can fail). Conservation remains green.
CPU codes/kernels are not claimed equal to CUDA's historical instrument.

## A100 seconds per item: basis and uncertainty

For an auditable pre-pilot budget, assume NO speedup versus the slower of the two
measured Mac baseline/resume executions, scale to the longest item, and charge
that longest-item budget to every unit:

    NF4 unit seconds = max(63.85310175, 54.07510454) * 214 / 132
                     = 103.51942253 s
    unquantized unit = max(88.49997725, 84.38249925) * 214 / 132
                     = 143.47723584 s

The base gets the same 103.519 s allowance even though it has two rather than four
capture passes. The A100 float64 hardware should be much faster at dense algebra,
but this implementation also streams/dequantizes weights, materializes head
writes, starts a Python process per unit and synchronizes artifacts. No measured
CUDA factor exists, so a hardware-peak ratio would be false precision. These are
conservative planning seconds, not a best-guess empirical A100 throughput claim.
The watchdog stops a unit above 2× its configured estimate. Re-measure the actual
A100 pilot before approving the full cohort's budget; use its measured wall time,
including references and synchronization, not only its GEMM time.

Cost assumptions, all explicit:

- 43 models × 23 items = 989 logical units: 23 base and 966 adapter/item units.
- Setup/freeze/download allowance: 0.5 A100 h, including install and durable
  quantized-instrument readback. Actual setup can exceed this; stop and revise.
- Export upload AND exact-commit verification download: 10 MB/s each, assumed,
  1.371874296 h total for the estimated export volume. Cache reuse prevents repeated
  transfer of the same base blob during pair synchronization.
- Rate: 13.08 CU/A100 h is a PLANNING ASSUMPTION, not a current Colab quote.
  Read the actual runtime rate/balance before spending; multiply by that rate.
- Reclamation/reprovisioning is not zero-cost. Add measured setup/re-gate time for
  every loss; per-unit persistence caps lost capture work at one in-flight unit.

| Scenario | GPU hours, including assumptions above | CU at assumed 13.08/h | Export GB |
|---|---:|---:|---:|
| Phase 1: NF4 base + 42 adapters | 30.311 | 396.47 | 24.694 |
| Phase 1 + one unquantized base across all 23 items | 31.258 | 408.86 | 25.247 |
| Phase 2: unquantized base + 42 adapters, standalone | 41.288 | 540.05 | 24.694 |

The conservative Phase-1 envelope exceeds a nominal 100-CU allowance. It is NOT
permission to spend ~396 CU. Do the pilot, replace the pessimistic no-speedup
budget with measured CUDA timing, and have Augusto approve the resulting spend.
What-if pipeline speedup sensitivity, leaving setup and transfer unchanged:
4× gives 8.982 h / 117.48 CU; 10× gives 4.716 h / 61.68 CU
(`estimate_crosscheck.log`). These are scenarios, NOT observed A100 results.
No live balance, destination quota, or network speed is available in this worker.

## A100 pilot (LAUNCH step 2): ARG x all 23 items, with CU caps

Pilot = NF4 base x 23 items + ARG (non-USA adapter) x 23 items = 46 units, same
queue, same prefix. Pair exports need the base run per item, so the base is part
of the pilot. Units that pass are skipped by the full run, so pilot cost is not
wasted. Arithmetic at the same no-speedup allowance (planning, not measured):

    compute  = 46 * 103.51942253 s / 3600           = 1.3227 h = 17.30 CU
    export   = 2 * 553,442,608 + 16,671,552 + 3*23*100,000 B = 1,130,456,768 B
    sync     = 1,130,456,768 / 10 MB/s / 3600 * 2   = 0.0628 h
    setup    = 0.5 h (assumption, outside the queue)
    total    = 1.8856 h = 24.66 CU at the assumed 13.08 CU/h

Caps (both are abort criteria in LAUNCH.md):

- Queue cap, enforced in code: `--max-cu 35` (`runner/vm_job.py` PILOT_MAX_CU) stops
  the pilot between units once queue compute+sync time costs more than 35 CU
  (planning rate; 1.93x the 18.1 CU queue envelope = 1.3227 h + 0.0628 h).
- Session cap, enforced by the operator: stop the runtime if the Colab balance
  has dropped by more than 50 CU since `colab new` (2x the 24.66 CU total).

What the pilot must report before the cohort budget is committed: measured
seconds per base unit and per adapter unit (from the unit `.rc.json` and timing
files), measured setup time, measured upload/readback MB/s, and the CU balance
delta. The full-run estimate is then recomputed from those, replacing the
no-speedup envelope.

## Exact binary sizing and destination

`estimate.json` tokenizes every packaged item with the pinned real tokenizer
(T=127–214), then applies actual array layouts/alignment from the successful Q57
capture. It includes attention top-16 indices/values/mass, F=14336 neuron arrays,
normal/clamped attribution arrays, all pair arrays and 8-byte buffer alignment.
The Q57 layout exactly matches measured .bin sizes: each run 21,491,360 B, each
pair 617,232 B. JSON size varies with token text, option count and provenance;
100,000 bytes per run/pair manifest is reserved.

    Sum over 23 base run binaries = 553,442,608 B
    Sum over 23 pair binaries     = 16,671,552 B
    All run binaries             = 43 * 553,442,608 B
    All pair binaries            = 42 * 16,671,552 B
    Binary total                 = 24,498,237,328 B
    JSON allowance               = (43+42) * 23 * 100,000 = 195,500,000 B
    Export total                 = 24,693,737,328 B = 24.693737328 decimal GB

Breakdown: base runs 0.553443 GB; adapter runs 23.244590 GB; pairs 0.700205 GB;
JSON allowance 0.1955 GB. Counting only the base and pair files would miss almost
all storage: the current viewer also needs each adapter's run arrays.

The frozen NF4 code/state corpus is separately 3,600,804,413 bytes on the CPU
diagnostic; CUDA size must be recorded by the GPU preflight. Original bf16 model
shards, downloaded adapter weights, two software environments and the Hub's
readback cache are NOT part of the export figure. Require at least 100 GB free
VM disk and verify remote quota/write capability before loading a model.

Durable outputs ONLY in the private dataset `Bonorinoa/SCA2-paper-b-artifacts`:

    workbench_cohort/phase1_nf4_20261018_a3/nf4/
    workbench_cohort/phase1_nf4_20261018_a3/exports/

The nf4 directory preserves codes, scales/state and `instrument.json`. The exports
directory holds run/pair JSON/bin, units/, attempts/ and index.json. Every unit
uploads then reads its exact commit back. No adapter-repo writes, respondent
files, human summaries, or joins are involved. Private metadata returns 401
locally (`memory_and_auth.log`), so actual upload/quota certification is a future
bootstrap gate, not something this report pretends to have measured.

## Phase 2 precision study — not run now

The unquantized hook is exercised only as a one-item functional regression, not a
43-model precision study. The projected later study costs above cover one dense
checkpoint base plus 42 adapters on the same 23 items, with identical prompts,
readout, export storage and conservation accounting.

It would measure how the explanation and adapter effect (B−A margins, head/MLP
attributions, vector-change norms and clamp response) depend on weight precision.
Because the adapters were trained against NF4, applying them to the unquantized
checkpoint is a counterfactual intervention, not a cleaner reproduction of the
paper. Greater arithmetic precision can improve conservation headroom, but it
does not remove that scientific target change. No Phase-2 cohort was launched,
no cross-precision paper statistic was computed, and no paper number was amended.

Rebuild from the worktree root:

    env -u PYTHONPATH uv run --project workbench python workbench/plans/gpu_cohort/runner/estimate.py --verification workbench/plans/gpu_cohort/dry_run_nf4_release/verification.json --unquantized-verification workbench/plans/gpu_cohort/dry_run_unquantized_release/verification.json

Captured exit: 0. Full per-item sizes and assumptions are in `estimate.json`.
