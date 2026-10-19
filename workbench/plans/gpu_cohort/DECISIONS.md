# Phase 1 capture decisions

capture target: nf4_dequant, decided by Augusto 2026-10-18
device: MacBook (M4 Pro CPU, float64), decided by Augusto 2026-10-18 after benchmark B0
instrument: frozen_nf4_t4/, quantized once on a Tesla T4 (the archive's device); Mac-CPU decode is
bit-identical to T4-CUDA on the 3 layers checked (C1, re-derived by the PM)

The operator's decision supersedes the earlier PENDING recommendation. Phase 1 is
one NF4-derived base plus all 42 cohort-1 adapters. `--weights unquantized` remains
working for a later precision study; it is not a second cohort authorized here.
No GPU or Colab runtime was started in this preparation task.

## Scientific instrument and readout

Use the representation from `paper_b/score_cohort.py:348-361`:
`BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)`, with the
notebook-style loader (no explicit torch_dtype, device_map="auto"). Base revision
is `0e9e39f249a16976918f6564b8830bc894c89659`.

This choice matches training as well as scoring. In the read-only main repo,
`paper_b/train_country.py:40-47` configures NF4, double quantization, fp16 compute,
and an fp16-loaded base for QLoRA. The LoRA deltas were fitted against that NF4
base, not against a dense counterfactual.

A1's recommendation is in
`planning/sprint_2026-10-11/paper-b-tier1/provenance/ARCHIVE_PROVENANCE_20261018.md:330-357`;
A2 independently supports it in `FINDINGS_A2.md:150-165`. Neither says that
high-precision dequantized algebra is bit-identical to historical CUDA execution.
The historical writer source bundle remains unresolved; this package does not
rewrite or replace any paper number.

### Production CUDA preparation versus the local diagnostic

- `runner/prepare_nf4.py` uses the frozen loader stack in its own interpreter:
  Python 3.13.15, torch 2.11.0+cu130, transformers 4.46.3,
  huggingface_hub 0.36.2, accelerate 0.34.0, bitsandbytes 0.50.2.
  It refuses non-A100 hardware or a version mismatch.
- It loads the pinned base on the A100, saves all 224 quantized Linear code arrays
  and packed quantization states, and records their SHA256 values, actual versions,
  device, CUDA, Python and nvidia-smi output. Bootstrap uploads and reads back this
  instrument before capture. Recovery restores it, not a new device's quantization.
- Capture calls `bnb.functional.dequantize_4bit` on those saved codes/states and
  upcasts the resulting effective fp16 weights to float64. Embeddings, norms and
  lm_head remain unquantized, using the production loader's fp16 representation.
  The loader asserts that non-Linear dtype instead of silently assuming it.
- The Mac diagnostic quantizes one checkpoint Linear at a time with CPU
  bitsandbytes 0.50.2 (NF4, block size 64, compressed statistics). It saves the same
  code/state serialization format. CPU codes may differ from CUDA codes. These
  exports explicitly say `quantization_device=cpu, diagnostic=true`; they are not
  relabeled as the A100 or archived instrument.
- Capture uses a separate modern workbench environment; it does not silently
  replace the frozen Paper B scorer environment. This two-environment boundary is
  deliberate. Actual capture package versions are stored in each run manifest.

The option readout is Paper B's declared Eq. 6: country-name-free v1 questionnaire
prompt, fixed option order, completion `" " + code`, summed completion logprob,
temperature 1, no length normalization, chat date `26 Jul 2024`. `readout_ids`
checks the shared prefix / single final code-token condition for every item;
therefore its probability softmax equals the teacher-forced option softmax for
this high-precision reference. The independent reference is HF modelling code in
float32 on the SAME effective weights, using that shared-prefix factorization;
it is not presented as the historical fp16 scorer.

LoRA remains unmerged. File tensors remain exact F32, then upcast directly to the
capture dtype; no fp16 round-trip. The offloaded HF reference now also keeps its
LoRA parameters at the file dtype (regression test included). `W x + (alpha/r)
B(Ax)` is applied in each layer; Gram-form weight deltas do not merge the adapter.

## Capture dtype and fatal gates

Choose float64 arithmetic, float32 stored arrays, uint16 attention top-k indices.
The alternative float32 mode remains selectable with the existing calibrated
relative gates, but Phase 1 queue requests float64.

Memory arithmetic (`memory_and_auth.log`, model geometry d=4096, F=14336,
32 query / 8 KV heads, head_dim=128):

- Dense full 8B at float64: approximately 8e9 × 8 = 64 GB; NOT resident on a
  40 GB A100.
- One decoder layer: `2*d*d + 2*d*(8*128) + 3*d*F + 2*d` = 218,112,000
  parameters; ×8 = 1,744,896,000 bytes. Stream ONE layer, not the whole model.
- One materialized head-write tensor at T=214:
  `32*214*4096*8` = 224,395,264 bytes. Four passes are sequential per layer;
  only the two plain passes retain writes briefly for B−A.
- Four residual states with four T×d buffers apiece: 112,197,632 bytes.
  Four per-layer F-length summary vectors for four passes: 58,720,256 bytes.
- An 8 GB device working budget is 20% of 40 GB; this is a sizing allowance, not a
  measured CUDA peak. The actual Mac process stays below the decimal 16 GB stop
  line. Per-row g/u/c summaries clone the selected row so they do not retain every
  T×F activation. The watchdog checks resident memory throughout every unit.
- CUDA TF32 is disabled for matmul and cudnn. Deterministic algorithms and
  `CUBLAS_WORKSPACE_CONFIG=:4096:8` are set. A100 peak memory still needs the GPU
  pilot; do not infer it from the Mac measurement.

Use `plans/stage1_8b_gaps.json` f64 taus, unchanged:
residual closure 1e-13; step closure 1e-14; head closure 1e-15;
readout 1e-13; logits reference 1e-4; pair attribution 1e-6.
Normal and clamped checks both apply. HF float32 shared-prefix option parity is
fatal at 1e-4. The relative block, not legacy absolute compatibility fields,
decides the verdict. The inherited calibration is a floor from two unquantized
8B items, NOT a claim to have calibrated the entire NF4 population; no threshold
is widened to make this cohort pass. Any CUDA pilot failure aborts.

Archive parity is SEPARATE: `archive_parity` compares captured probabilities with
packaged `paper-b-20261011/scores_for_join` rows, tau = 4 archived fp16 logprob ulp
(A2 F5; superseded the first draft's absolute probability tau=1e-3, A4 F4), `fatal=false`,
observed maximum and source shown. The absolute 1e-3 probability threshold was below the
archive's fp16 resolution on unsaturated items; probability gaps are now descriptive only. A failed report-only archive row
does not make conservation fail and must not be described as passing. The viewer
labels `weights` and the report-only probability gap. No paper table is rebuilt.

## Models, items and storage

`models.json` pins dataset `Bonorinoa/SCA2-paper-b-adapters` at
`c4b0f36eae0c15e508f72b606861798c8359131f` and contains the base plus 42 entries
matching ONLY `adapters/<CC>/adapter_model.safetensors`, not bank2/replicate paths.
The Hub listing and all 42 configs were checked: r=16, alpha=32, targets
k_proj/o_proj/q_proj/v_proj, no rank/target exceptions. Weight digests are the
Hub's LFS SHA256 metadata; downloaded ARG weights are independently hash-checked
by the runner. The inventory does not claim 42 local weight downloads.

Choose all 23 strict archive questionnaire items, listed in `items.json`:
Q43, Q50, Q57, Q58, Q59, Q60, Q61, Q62, Q63, Q64, Q73, Q81, Q99,
Q101, Q103, Q106, Q107, Q109, Q176, Q177, Q178, Q179, Q195.
Actual readout lengths are 127–214 tokens (including shared prefix). Public
questionnaire text and model-only probabilities/logprobs are packaged; no licensed
respondent records, human means, or model–human joins are read or shipped.

Storage is about 24.694 GB including manifest allowance, plus the frozen NF4
instrument (CPU diagnostic 3.601 GB, CUDA to be measured). This includes 43 run
exports per item, not merely a base plus tiny pair files: the viewer needs each
adapter's run arrays as well. `estimate.json` contains every T and byte count.
Preflight at least 100 GB free local VM disk (weights, two environments, output,
Hub cache/readback and margin); check the remote quota/write probe separately.

## Persistence and launch boundary

- `runner/unit.py --model <base|CC> --item <item_id>` is one idempotent unit.
  Files are write-once, atomically published, with collision-on-different-bytes.
  Base and pair manifests are capture@1.1. Base results are recomputed inside an
  adapter pair to obtain in-loop vector differences, but only one base export is
  stored. Source/device/frozen-instrument-qualified keys prevent representation
  or source versions from overwriting one another.
- Completion markers hash every export. Kill before completion restarts only that
  unit; kill after completion verifies and skips it. Logs/timing are separate,
  append-only attempts, so operational timestamps cannot spoil export byte identity.
- Failing run and pair gates are saved and listed, then return nonzero; queue stops
  on the first fatal failure. Test corruption has its own visibly distinct keys.
- Output destination ONLY: private dataset `Bonorinoa/SCA2-paper-b-artifacts`,
  `workbench_cohort/<run>/nf4/` and `workbench_cohort/<run>/exports/`.
  No writes to the adapter repo or `adapters/<CC>`.
- Sync restores hash-checked units from the same durable store it uploads to;
  uploads are followed by exact-commit reads and digest checks. Listing/upload
  failures abort, not masquerade as empty or successful results.
- Private destination access is 401 in this worker. Real Hub writes, frozen CUDA
  installation and CUDA timing are NOT certified locally. Bootstrap makes these
  explicit future preflight gates, using a Colab secret, not another profile's env.
- A4 reviews this package next. Scientific target is decided; GPU spending and
  empirical A100 timing are separate operational checks, not implied approval.
