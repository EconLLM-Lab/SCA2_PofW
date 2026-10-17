# Workbench v2 triage (engineer memo, advisory)

Card `t_491d9eba`. Host: Apple M4 Pro, 24 GB, 8 P + 4 E cores (`sysctl`, see C0). torch 2.14.1, transformers 5.20.1, peft 0.21.2.
Nothing in `src/`, `tests/`, `viewer/` or `data/` was touched. Measurement scripts and their raw output live in
`workbench/plans/scripts/` and `workbench/plans/scripts/out/`.

**How to read the numbers.** Every number carries a tag like `[C3]`. The tag names the command in section 9 that
produced it, and the file in `plans/scripts/out/` that holds the raw output. A number marked **EST** is an estimate from
a formula or a roofline, not a measurement. Anything with no tag is my judgement.

---

## 0. Summary

1. **On-demand regeneration is cheap for the 135M models and cheap enough for 1B.** One warm (model, prompt) capture is
   0.8-1.7 s on the M4 Pro in float64 `[C1]`. One item as an A/B pair is about 3.2 s including a fresh session `[C2]`.
   A job server with a content-addressed cache is a small slice. It does not need the GPU or the cloud.
2. **Three premises in the card are wrong or need correcting** (details in section 1):
   - **Llama-3.2-1B and Llama-3.1-8B cannot be captured today.** `llama_capture._rope_theta` refuses `rope_type=llama3` `[C11]`.
     Both models use it. This is a code change in the capture core, not a configuration change.
   - **The absolute conservation gates cannot pass in float32.** The largest residual entry is about 2.6e4. One float32 ulp
     there is 1.95e-3 `[C11]`, so the residual-closure gate (< 1e-3, absolute) is below float32 round-off. The relative gap is
     fine (<= 2.1e-7) `[C3]`. The gate must become scale-aware before any float32 run can be called honest.
   - **"T = 230" is the shortest bank prompt, not a typical one.** USA bank prompts run T = 230 to 459, median 315 `[C7]`.
3. **Which dtype keeps the gates honest.** float32 compute on CPU or MPS, with gates made relative to max|h|. On the 135M models
   float32 matches float64 to 2e-5 on margins and 3e-6 on probabilities `[C3]`. bfloat16 compute does not: with bf16 matmuls
   the margin moves by up to 0.30 and the DLA gap is 0.07-0.10 `[C3]`. Weights may be stored bf16 only if the checkpoint
   is bf16 **and** no LoRA is merged into them (a merged LoRA rounded to bf16 loses its delta, section 3).
4. **Llama-3.1-8B does not fit this Mac in any honest configuration** (EST, sections 3.2 and 4.2). float32 needs 32 GB for weights alone.
   bf16 weights with float32 compute need about 17 GB, against an MPS limit of 19.07 GB `[C11]` on a machine that also runs a browser.
   It is a Colab (A100 40 GB or L4 24 GB) job. float64 8B needs 64 GB of weights `[C6]`, so it is out everywhere except an 80 GB card.
5. **Two things in the current code block anything above 135M** (section 2.4): the capture keeps every layer's tensors alive
   at once (about 18 GB of activations for 8B at T = 331, EST `[C6]`), and `load_hf` accepts a truncated adapter without an error `[C9]`.
6. **I/O limits proposed for v1:** T_max = 512 tokens (covers 100% of the 658 USA bank prompts and all 23 accepted WVS items `[C7]`),
   at most 12 options, safetensors-only adapters up to 500 MB, an HF-id allowlist, and a `lite` export (no attention arrays) for batches.
7. **Experiments.** Of 14 first-30-minutes experiments, 9 work today in some form. I ran 5 of them from Python `[C8]`. The other 4 (E5, E7, E8, E9) work
   through the CLI and the viewer for pre-exported items. None works on a prompt the user types in the UI. The single missing feature that unlocks most
   of them is the on-demand pipeline in section 2.

---

## 1. Baseline re-measured, and where the card's premises differ

Machine was quieter than during the PM's run, so every time is about 30% lower than the PM baseline.

| Quantity (CPU, float64, SmolLM2-135M-Instruct, warm, median of 5) | PM baseline | Re-measured `[C1]` |
|---|---|---|
| capture pass, T = 136 | 0.28 s | 0.196 s |
| clamped pass | 0.24 s | 0.166 s |
| two HF reference checks | 0.29 s | 0.231 s |
| Eq. 6 teacher-forced, 2 codes | 0.26 s | 0.230 s |
| whole `capture_run`, T = 136 | n/a | 0.816 s |
| capture pass, T = 306 (bank item) | "about 0.4 s at T = 230" | 0.424 s |
| whole `capture_run`, T = 306 | n/a | 1.657 s |
| both 135M models load | 4.1 s | 1.15 s (0.64 + 0.51), page cache warm `[C2]` |
| cold pair export, one item (`wvs_Q57`) | 3.8 s | 3.24 s `[C2]` |
| peak RSS of the warm loop (one model, T up to 306) | n/a | 6.54 GB `[C1]` |

Notes on the table:

- **Eq. 6 cost is linear in the number of codes.** Q57, Q43, Q81 have 2, 3, 4 codes `[C1b]` and the teacher-forced stage took
  0.230, 0.357, 0.481 s `[C1]`. That is about 0.115-0.120 s per code. Each code runs a full forward over the prompt.
- **The 4.1 s "model load" is not reproducible from the models alone.** Loading both models takes 1.15 s with a warm page cache.
  Importing torch + transformers + peft is another 1.83 s `[C2b]`, and constructing the `Session` (tokenizer) took 1.87 s `[C2]`.
  I cannot measure a cold-disk read without `sudo purge`, so the PM's 4.1 s is probably imports plus a cold cache.
- **The "cold pair export" is not model-warm.** `export_pair` builds its own `Session()` and reloads both models, so the 3.24 s
  includes tokenizer and model loads (about 1.2-1.5 s) plus 2 x 0.82 s of capture.
- **The checks cost more than the capture.** The two HF reference checks and Eq. 6 are 56% of `capture_run` at T = 136
  ((0.231 + 0.230) / 0.816 `[C1]`). A "fast" mode that skips them roughly halves the wait. See the formula in section 4.

**Premise problems, listed so nobody works around them quietly:**

| # | Card says | What I found | Source |
|---|---|---|---|
| P1 | Estimate Llama-3.2-1B and Llama-3.1-8B | `llama_capture._rope_theta` raises `ValueError: only default RoPE is implemented` for `rope_type=llama3`, which both use (per their public configs; neither is in the HF cache, so I tested a `LlamaConfig` built with that `rope_scaling`). `_rope_native_dtype` (the HF reference patch) ignores scaling too. Fix is about 10 lines of frequency scaling in two places, plus a test. | `[C11]` |
| P2 | float32 closure "honest" | The brief's residual gate (< 1e-3 absolute) sits below one float32 ulp (1.95e-3) at the largest residual entry (max abs h = 25,772 to 25,984 over 8 runs). 4 of 8 float32 runs fail it while their relative closure is 2e-7. | `[C3]`, `[C11]` |
| P3 | T = 230 | USA bank prompts: min 230, p50 315, p90 353, p99 385, max 459. WVS accepted items: min 115, median 143, max 253. | `[C7]` |
| P4 | Same columns as `question_map_wvs_edited.csv` is enough | 12 of the 35 rows cannot be run: 10 `scale_1_10` rows (the code "10" is two tokens under the SmolLM2 tokenizer, so the codes do not split as prefix + one token) and 2 `numeric` rows, which crash `wvs_item` with a float-conversion `ValueError` instead of a clean refusal. | `[C7]` |
| P5 | `load_hf` guards the float64 silent-zero trap | True for B = 0. But it does not detect a truncated adapter or a wrong base model (section 3.3). | `[C9]` |
| P6 | Float64 8B needs about 64 GB | Correct for the weights (64.2 GB `[C6]`). The current code needs about 100 GB at T = 331 (EST `[C6]`) because it stacks every layer's per-head outputs. | `[C6]` |

---

## 2. Q1: On-demand regeneration pipeline

### 2.1 Proposed shape

One local process, one worker, because a pass already uses all 8 cores (torch uses 8 threads `[C1]`) and two jobs would only contend.

```
 browser (viewer, :5178)                     job server (127.0.0.1 only)
 ------------------------                    ---------------------------------------------
 "New prompt" form / item file  --POST /jobs-->  validate (section 3)   -> 422 with the reason
                                                 estimate seconds (section 4)
                                <-- {job_id, est_seconds, cache_hits}
 EventSource /jobs/{id}/events <---- SSE ----    queue (FIFO, 1 worker)
    queued | tokenized T=136                          |
    load model A (skipped if resident)               v
    capture A  clamped A  checks A   (per stage)  capture_run  (existing code)
    ... same for B, then pair arrays              cache.get(key) or compute -> exports/<key>.json/.bin
    done: files + conservation pass/fail          index.json rebuilt
 viewer reads /exports/... (as today)
```

- **SSE, not a websocket.** Progress is one-way. SSE is stdlib-simple, reconnects by itself, and passes through Vite's proxy.
  A websocket buys nothing here. FastAPI + uvicorn is fine; `http.server` would also do.
- **Model residency is an LRU keyed by (model_id, revision, adapter sha, dtype, device).** One 135M float64 model is 1.1 GB.
  The four current keys are 4.4 GB resident. Budget 12 GB of the 24 GB for resident models on this Mac.
- **Cancellation is between stages only.** One pass is 0.2-2 s and is not interruptible. Say so in the UI.
- **Pairs never need two copies of the weights for LoRA.** B = A + s.B.A per layer can be applied while streaming the layers (section 2.4).
  Today `export_pair` holds both merged models.

### 2.2 Cache key

The export already records `prompt_sha256` and `adapter.sha256` in the manifest. That is not enough for a key, because two items with
the same prompt text but different `j_plus`/`j_minus` give different margins. Proposed key (SHA-256 of canonical JSON):

```
 schema ("sca2-workbench/capture@1")      model_id + revision (HF commit hash, or file sha of model.safetensors)
 formatted_prompt sha256 (post chat template)   adapter sha256 or null
 codes, j_plus, j_minus                    compute dtype + device class (cpu64 / f32)
 tokenizer id + revision                   TOPK, export mode (full | lite)
 capture-core hash (sha256 of llama_capture.py + items.py + export.py)
```

- A **run** is cached under `run__<key[:16]>`. A **pair** is cached under the two run keys.
- Items entered by the user get `item_id = "user_" + sha[:12]` so file names never contain user text.
- The capture-core hash invalidates the cache when the code changes. `git_head` alone would also invalidate it on every unrelated commit.
- Disk cap with LRU eviction. A full 135M pair of runs is 9.7-19.5 MB per item `[C12]`, so 5 GB holds about 250-500 items.

### 2.3 What exists and what it costs to wire

| Piece | State today | Effort (EST: S <= 1 day, M 2-4 days, L > 1 week) |
|---|---|---|
| Item from a form (text, options, j+/j-) | `Item` dataclass exists. No factory, no validator. `item_from_id` accepts only `wvs_*` and `bank_*`. | S |
| `readout_ids` validation as a pre-flight | Exists. It raises, but with raw token dumps in the message. | S (wrap, friendly message) |
| Cache by content key | Not present. File names are `run__<model_key>__<item_id>`. | S |
| Job server + SSE + estimate | Not present. | S-M |
| Warm `Session` that survives between jobs | `Session` exists. `export_pair` makes a new one on every call. | S |
| Per-stage progress events | `capture_run` is one call. Stage boundaries are inline (capture, clamped, ref, eq6). | S (callback argument) |
| Viewer "New prompt" panel + progress bar | Not present. `viewer/**` is fenced. Creative and the PM own it. | M, not mine |
| Any model other than the 135M family | Blocked by P1 (RoPE), dtype hard-coded to float64, activations. | M (section 2.4) |

### 2.4 Capture-core changes the server depends on (follow-up card, not this memo)

1. **dtype and device as parameters.** `weights_from_hf`, `_rope`, `load_hf` and `reference_check` hard-code float64 and CPU.
   `plans/scripts/lowprec.py` is a working prototype of the pass with `(weights, matmul, stream)` dtypes and a device.
   At float64 on CPU it reproduces `LC.run` bit-for-bit on head attribution (relative error exactly 0.00 `[C3]`).
2. **llama3 RoPE** in `_rope` and `_rope_native_dtype` (P1).
3. **Stream the per-layer tensors.** `run()` appends every layer's `O`, `A`, `g`, `u`, `c` to lists and then stacks them.
   `O = torch.stack(head_out)` happens even when `keep_head_out=False`. The memory model
   `P.b + b.(2LHTd + 2LHT^2 + 7LTF + 6LTd + 3TV) + 0.5 GB` reproduces my measurements within 10%:
   predicted 4.1 GB vs measured 4.32 GB for 135M float64 at T = 306, and 14.6 GB vs 14.09 GB for 1B float64 at T = 140 `[C4]` `[C6]`.
   For 8B in float32 at T = 331 the activation term is 17.8 GB, against about 1 GB if one layer is alive at a time (EST `[C6]`).
4. **Last-row logits.** `run()` computes logits for all T positions, which is 128,256 x 4096 x T for Llama-3.1. Only the last row is
   needed for the readout. The full matrix is needed only by the float64 HF comparison.
5. **Close the adapter guard** (section 3.3).

---

## 3. Dtype and device: which one keeps the gates honest

### 3.1 Measured on SmolLM2-135M-Instruct and the e3 adapter `[C3]`

8 cases (2 models x 4 items, T = 136-306), CPU unless noted. "Closure" is residual closure, `max|h^L - (h^0 + sum a + sum m)|`.
The checker itself runs in float64, so it adds no round-off. Worst case over the 8 cases:

| Variant (weights / matmul / stream) | closure abs | closure / max abs h | DLA gap | margin error vs f64 | prob error | head-attr rel err | passes closure < 1e-3 | passes DLA < 1e-2 |
|---|---|---|---|---|---|---|---|---|
| f64 (control) | 1.3e-11 | 4.9e-16 | 9.7e-15 | 3.9e-14 | 5.4e-15 | 0 | 8/8 | 8/8 |
| **f32, CPU** | 5.3e-3 | 2.0e-7 | 4.5e-6 | 1.3e-5 | 2.8e-6 | 2.1e-5 | **4/8** | 8/8 |
| **f32, MPS** | 5.4e-3 | 2.1e-7 | 2.4e-6 | 2.2e-5 | 3.4e-6 | 2.7e-5 | **4/8** | 8/8 |
| bf16 everywhere, CPU | 233 | 9.0e-3 | 8.1e-2 | 0.175 | 3.2e-2 | 0.35 | 0/8 | 0/8 |
| bf16 everywhere, MPS | 233 | 9.0e-3 | 7.1e-2 | 0.191 | 3.5e-2 | 0.13 | 0/8 | 2/8 |
| bf16 matmul, f32 stream/norm/softmax, CPU | 1.7e-3 | 6.7e-8 | 9.0e-2 | 0.295 | 3.3e-2 | 0.28 | 4/8 | 1/8 |
| bf16 matmul, f32 stream/norm/softmax, MPS | 1.5e-3 | 5.7e-8 | 0.10 | 0.170 | 1.7e-2 | 0.33 | 0/8 | 0/8 |
| bf16 weights, f32 compute, CPU | 7.6e-3 | 2.9e-7 | 3.2e-6 | 0.161 | 1.7e-2 | 0.26 | 4/8 | 8/8 |
| bf16 weights, f32 compute, MPS | 7.7e-3 | 3.0e-7 | 2.9e-6 | 0.161 | 1.7e-2 | 0.26 | 4/8 | 8/8 |

Margins in these 8 cases are 0.04-2.9 `[C3]`. A margin error of 0.17-0.30 is 6-10% of the largest margin, and on Q43 (margin 0.039) the bf16-matmul variant's error is 0.039, which is 100% of the value. In the
f32 rows, the 4 closure failures are exactly the e3 model (closure 5.3e-3). The base model's f32 closure is 7.4e-4 and passes.

What the table says:

- **float32, CPU or MPS, is honest if the gates are relative.** Internal consistency (closure/max|h| <= 2.1e-7, DLA gap <= 4.5e-6)
  and fidelity to float64 (margin <= 2.2e-5, probabilities <= 3.4e-6, head attribution <= 2.7e-5 relative, top-50 neurons identical)
  are all at the 1e-5 level. CPU and MPS give the same gaps. MPS is 1.8-1.9x faster (section 3.4).
- **Why 1e-3 absolute fails in float32.** The residual has one very large entry (massive activation, max abs h about 2.6e4).
  One float32 add near it rounds by up to half an ulp = 0.98e-3 `[C11]`. Nothing can fix that except a relative gate.
- **bfloat16 compute is not honest.** At 2.6e4 one bf16 ulp is 128 `[C11]`, so the naive bf16 stream fails closure by 233.
  Keeping the stream and norms in float32 repairs closure but not the logit rounding, so the DLA gap is 0.07-0.10. More importantly the
  numbers change: margins move by up to 0.30. That is a different model, not a noisy readout of the same one.
  An untested variant (bf16 body, float32 head) would probably close the DLA gap, but the 0.02-0.30 margin shift from the bf16 body would remain.
- **Storing weights as bf16 is free when and only when the checkpoint is bf16 and nothing is merged.** SmolLM2 ships bf16
  (`torch_dtype: bfloat16` `[C11]`). For the base model the "bf16 weights, f32 compute" row is identical to float32 to the printed digits `[C3]`.
  Llama-3.1-8B also ships bf16 (from the public model card, not re-verified here). **A merged LoRA is the exception:** W + (alpha/r)BA is not
  representable in bf16. For e3 the bf16-weights row has margin errors up to 0.161 and probability errors up to 0.017 while the adapter
  moves margins by 0.4-1.9 (e3 minus base, 4 items) `[C3]`. Rounding the merge destroys part of the effect being measured. Keep the merged weights in float32,
  or apply the LoRA unmerged per layer.
- **There is no float64 on MPS.** `Cannot convert a MPS Tensor to float64 dtype` `[C11]`.

Proposed float32 gates (my numbers, with margin over what I measured; Augusto owns the contract):

| Gate | float64 (today) | float32 proposal | Measured float32 worst case |
|---|---|---|---|
| residual closure | < 1e-3 abs | < 4e-6 x max abs h (about 64 float32 eps) | 2.1e-7 `[C3]` |
| DLA gap | < 1e-2 abs | < 1e-4 abs | 4.5e-6 `[C3]` |
| vs reference | hf64 logits rel gap < 1e-10 | our f32 vs stock HF f32 last-row logits rel gap < 1e-4 | 2.9e-6 `[C13]` |

For comparison, stock HF float32 is 1.9e-6 to 2.6e-6 from our float64 truth `[C13]`, so the float32 gate is as tight as the reference allows.

### 3.2 Device choice by model size (all numbers EST unless tagged)

| Model | This Mac | Colab Pro |
|---|---|---|
| SmolLM2-135M, 360M | float64 CPU as today. 0.8-1.6 s and 1.9-3.9 s per (model, prompt), 2.7-8.6 GB `[C1]` `[C6]`. | not needed |
| Llama-3.2-1B | float32 MPS (0.76-1.45 s, 7.9-10.7 GB) or float64 CPU (7-14 s, 15-21 GB, crowds the machine) | not needed |
| Llama-3.1-8B (+LoRA) | **does not fit** (see below) | A100 40 GB or L4 24 GB, bf16 weights + float32 compute + streamed activations, 17-18 GB |

Mac 8B detail: MPS recommended working set is 19.07 GB `[C11]`. bf16 weights alone are 16.1 GB `[C6]`. That leaves about 3 GB for activations
and the OS cache, with a browser open. Layer-by-layer disk streaming would work in principle, but it needs the multi-pass-per-layer design.
I would not build it for v1.

### 3.3 Adapter guard: what `load_hf` catches `[C9]`

Setup: copies of `models/usa_e1`, damaged one way at a time, loaded onto SmolLM2-135M-Instruct.

| Damage | `load_hf` today |
|---|---|
| intact adapter (control) | accepted |
| a tensor for a layer that does not exist (layer 99) | rejected (`adapter keys not in model`) |
| an all-NaN tensor | rejected, though only because `torch.equal(NaN, NaN)` is false |
| **file missing all 8 tensors of layer 29** | **accepted, with only a `UserWarning`. That layer's q_proj differs from the intact merge by 8.9e-4, so it is silently a different model** |
| **`adapter_config.json` says base = Llama-3.2-1B, loaded on 135M** | **accepted. `base_model_name_or_path` is never compared** |
| `bias: "all"` in the config while the file has no bias tensors | accepted |

This is the peft silent-zero trap in a second form. The existing guard proves "every tensor that is in the file was loaded". It does not
prove "every LoRA module the config asks for has a tensor in the file". The fix is to also check `res.missing_keys` for `lora_` keys.
It is small, and it belongs in the upload validator (section 5.2).

### 3.4 Speed by device `[C4]`

`LC.run`-equivalent pass, median of 3, random-weight models with the real architecture (see 4.1 for why random weights are fine):

| Model | T | f64 CPU | f32 CPU | f32 MPS |
|---|---|---|---|---|
| 135M | 140 / 306 | 0.156 / 0.336 s | 0.073 / 0.102 s | 0.037 / 0.054 s |
| 360M | 140 / 306 | 0.353 / 0.762 s | 0.116 / 0.231 s | 0.070 / 0.110 s |
| 1B | 140 / 306 | 1.834 s / skipped | 0.253 / 0.504 s | 0.155 / 0.262 s |
| 8B layer cost (L2 minus L1, vocab cut) | 140 / 306 | n/a | 0.065 / 0.125 s per layer | 0.035 / 0.068 s per layer |

---

## 4. Runtime-estimate formula

### 4.1 The formula

For the "this will take about N s" notice, per (model, prompt):

```
 t_total = 1.10 * [ 2 * t_pass  +  (n_ref + n_codes) * t_hf ]          (+ t_load if the model is not resident)

 t_pass  = a_p * P_pass * T / 1e9  +  b_p * L  +  c_p      our capture pass (run once, clamped once)
 t_hf    = a_h * P_hf   * T / 1e9  +  b_h * L  +  c_h      one stock HF forward (reference check or one Eq. 6 code)

 P_pass  = layer parameters (+ V*d if the pass computes all-T logits, as float64 LC.run does)
 P_hf    = layer parameters + V*d              (HF computes all-T logits)
 n_ref   = 2 in float64 (stock HF and HF with the three casts removed), 1 in float32
 n_codes = number of option codes
 1.10    = serialisation, top-k, bin writing (measured residual: -5% to +2%, see below)
```

Pair of two models for one item: 2 x t_total + about 0.3 s for the weight deltas and file writes (EST; my 3.24 s `[C2]` also holds two model loads and a tokenizer load).
"Fast" mode, which skips the HF reference checks and Eq. 6, is `1.10 * 2 * t_pass`, about 44% of `t_total` at 135M.

Coefficients, fitted by least squares on relative error to the 61 timed points in `[C4]` (the per-row point counts are in the table) (script `fit_time.py`, `[C5]`):

| Mode | a (s per Gparam.token) | b (ms per layer) | c (ms) | n points | median / max relative error |
|---|---|---|---|---|---|
| pass, f64 CPU (`LC.run`) | 0.00780 | 0.02 | 0 | 5 | 12% / 26% |
| pass, f32 CPU | 0.00153 | 1.62 | 3.4 | 10 | 6% / 28% |
| pass, f32 MPS | 0.00088 | 0.42 | 12.6 | 10 | 6% / 14% |
| pass, bf16 weights + f32 compute, MPS | 0.00101 | 0.18 | 20.1 | 10 | 8% / 29% |
| HF forward, f64 CPU | 0.00379 | 1.38 | 0 | 4 | 2% / 7% |
| HF forward, f32 CPU | 0.00101 | 1.39 | 4.5 | 10 | 8% / 27% |
| HF forward, f32 MPS | 0.00057 | 0.41 | 0 | 10 | 7% / 24% |

Validation against the independent whole-`capture_run` timings `[C1]` (135M, f64 CPU, 2 codes, n_ref = 2):

| T | formula | measured |
|---|---|---|
| 136 | 0.80 s | 0.816 s |
| 306 | 1.57 s | 1.657 s |

- **Random weights are fine for timing.** Matmul cost does not depend on the values. Real vs random 135M: 0.196 s (real, `[C1]`) vs 0.156 s (random, `[C4]`)
  at T = 136-140. That 25% gap is within the run-to-run drift of this machine, not a systematic difference, but treat the formula as +/- 30%.
- **The 1B float64 fit under-predicts.** It says 1.35 s at T = 140 against 1.834 s measured, because the float64 1B pass is memory-bound.
  Use the measured value for that one cell. All 8B rows are extrapolations of per-layer timing from 1-2-layer probes at real layer widths.
- **Not covered.** Cold model load from disk, first-call MPS kernel compilation (the first call is discarded in every timing here), and thermal throttling.

### 4.2 Estimates by model (EST, from `estimates.py` `[C6]`; n_codes = 2)

The 8B and Llama prompts add about 25 template tokens (EST: the Llama-3.1 chat template carries a system block with dates; the tokenizer is not in the HF cache, so I could not count them).

**Mac M4 Pro, time per (model, prompt) and peak RAM with the current un-streamed code:**

| Model | T | f64 CPU | f32 CPU | f32 MPS | bf16-w / f32 compute, streamed |
|---|---|---|---|---|---|
| SmolLM2-135M | 140 / 306 | 0.82 s, 2.7 GB / 1.58 s, 4.1 GB | 0.38 s / 0.51 s, 1.6-2.3 GB | 0.16 s / 0.24 s | 0.18-0.27 s, 0.9-1.0 GB |
| SmolLM2-360M | 140 / 306 | 1.9 s, 5.6 GB / 3.9 s, 8.6 GB | 0.60 s / 0.97 s, 3.0-4.5 GB | 0.28 s / 0.49 s | 0.32-0.57 s, 1.3-1.5 GB |
| Llama-3.2-1B | 165 / 331 | 7.0 s, 15 GB / 13.9 s, 21 GB | 1.4 s / 2.6 s, 7.9-10.7 GB | 0.76 s / 1.45 s | 0.87-1.67 s, 3.4-3.8 GB |
| Llama-3.1-8B | 165 / 331 | 42 s / 84 s, 82-100 GB (no fit) | 8.3 s / 16.3 s, 41-50 GB (no fit) | 4.6 s / 9.2 s, 41-50 GB (no fit) | 5.3 s / 10.6 s, **17-18 GB (borderline, 19.07 GB limit)** |

Measured anchors inside this table: 135M f64 peak 2.83 GB at T = 140 and 4.32 GB at T = 306; 360M f64 6.41 GB and 8.64 GB; 1B f64 14.09 GB at T = 140 `[C4]`.
MPS driver memory for 1B float32 was 7.49 GB at T = 140 and 9.87 GB at T = 306 `[C4]`.

**Colab Pro (roofline EST, not measured).** Peak fp32 FLOP/s from vendor spec sheets (T4 8.1 T, L4 30.3 T, A100 19.5 T fp32, 9.7 T fp64, TF32 off because
TF32 has a 10-bit mantissa and would break the gates), with an assumed 30-50% efficiency and 1 ms per layer. The efficiency is a guess. Treat as +/- 2x.

| Model | T | T4 16 GB f32 | L4 24 GB f32 | A100 40 GB f32 | A100 40 GB f64 |
|---|---|---|---|---|---|
| 135M | 140 / 306 | 0.19 / 0.24 s | 0.16 / 0.18 s | 0.16 / 0.19 s | 0.21 / 0.25 s |
| 360M | 140 / 306 | 0.29 / 0.44 s | 0.20 / 0.26 s | 0.21 / 0.27 s | 0.29 / 0.41 s |
| 1B | 165 / 331 | 0.56 / 1.04 s | 0.25 / 0.42 s | 0.28 / 0.48 s | 0.47 / 0.85 s |
| 8B (bf16 weights, f32 compute) | 165 / 331 | 3.6 / 7.1 s, **no fit (17 GB)** | 1.4 / 2.6 s, fits | 1.6 / 3.0 s, fits | 2.9 / 5.6 s, **no fit (66 GB)** |

8B on Colab is a latency of a few seconds per (model, prompt). A pair with an unmerged LoRA is about 2x that. The Colab session start, model download
(16 GB) and Drive mount will dominate: minutes, not seconds. Data governance: survey item text that is already public is fine to send to Colab. Respondent-level
or unpublished-licence data is not, per the ASU rule on third-party processing.

### 4.3 Export sizes (bytes formula verified against 22 real runs and 16 pairs)

`run bytes = T.(L.H.104 + 20.L + 4) + 16.L.F + small`, `pair bytes = 4.T.(3L + 1 + L.H) + 16.L.H + 12.L`.
Measured vs formula, 135M `[C12]`, `[C6b]`:

| T | run measured | run formula | pair measured | pair formula |
|---|---|---|---|---|
| 136 | 4,641,080 | 4,641,192 | 201,064 | 201,064 |
| 306 | 9,517,360 | 9,517,472 | 446,544 | 446,544 |

The whole `exports/` folder is 141 MB in 77 files `[C12]`. **93% of a run is the attention top-16** (`L.H.16.(2+4)` of `L.H.104` bytes per token). Estimates:

| Model | T | run | pair | A + B + pair per item |
|---|---|---|---|---|
| 135M | 140 / 306 | 4.8 / 9.5 MB | 0.21 / 0.45 MB | 9.7 / 19.5 MB |
| 360M | 140 / 306 | 8.4 / 16.8 MB | 0.33 / 0.71 MB | 17 / 34 MB |
| 1B | 165 / 331 | 10.9 / 19.8 MB | 0.38 / 0.75 MB | 22 / 40 MB |
| 8B | 165 / 331 | 25.0 / 42.8 MB | 0.76 / 1.50 MB | 51 / 87 MB |

LoRA file size, paper recipe (r16 on q, k, v, o, float32): 7.4 MB for 135M (file on disk is 7.1 MiB `[C12]`), 13.1 MB for 360M, 13.6 MB for 1B,
54.5 MB for 8B (EST `[C6]`). A `lite` export (no attention arrays) is about 2.9 KB per token plus 16.L.F, which is about 1.6 MB for a 135M run at T = 306 (EST).

---

## 5. Q2: I/O formats and limits for a first version

### 5.1 Prompts

**Single-question form** (what the scientist types):

| Field | Rule |
|---|---|
| question text | 1-1,600 characters (EST: leaves T <= 512 once the fixed prompt, about 100 tokens, is added) |
| options | 2-12 rows of (code, label); code is 1-3 characters, unique; label 1-200 characters |
| j+ / j- | default first and last code (same as `wvs_item`); both selectable |
| persona | none (today); country list is a follow-up (section 6, E3) |
| prompt template | v1 verbatim from `paper_b` (as `survey_prompt_v1`). No free-form template editing in v1: editing breaks the "verbatim paper prompt" lock |

**Item file.** CSV or JSONL, one row per item, using the existing `question_map_wvs_edited.csv` columns that `wvs_item` reads:

| Column | Meaning | Rule |
|---|---|---|
| `Question` | item id | unique, `[A-Za-z0-9_-]{1,40}` |
| `StandaloneQuestion` | question text | as above |
| `ResponseType` | e.g. `single_choice_4` | informational; `numeric` rows are refused with a clear message (P4) |
| `ResponseLabels` | `;`-separated | same count as codes |
| `ResponseCodes` | `;`-separated | each must parse as an integer today (`str(int(float(c)))`); keep that |
| `gps_dimension` | optional, may be empty (it is empty for some rows `[C7]`) | one of altruism, negrecip, patience, posrecip, risktaking, trust, or empty |

JSONL uses the same keys. Today the CSV path is the constant `items.QUESTION_MAP`, so `wvs_item` cannot read an uploaded file: that is the missing piece (S).

**Readout validation rule** (what `items.readout_ids` enforces, to be run as a pre-flight and reported per item):

1. Every code, as `" " + code`, must tokenize to the same number of tokens.
2. All codes must share the same prefix tokens.
3. The final tokens must be pairwise distinct.

With the SmolLM2 tokenizer this accepts 23 of the 35 sample rows and refuses 12 `[C7]`: the 10 `scale_1_10` rows (the code "10" is two tokens, `Ġ`,`1`,`0` against `Ġ`,`1`),
Q261 and Q262 (`numeric`, crash with a float-conversion error rather than a refusal). **The 1-10 scales are the most common item type in the social sciences,
and v1 would refuse all of them.** Options: (a) accept and say so; (b) restrict to 0-9 and let the user recode; (c) letter codes A-J, which changes the prompt away from
the verbatim paper form. (b) and (c) are the paper-prompt decision for Augusto. Under the Llama-3 tokenizer digits group in threes, so " 10" is probably
`Ġ` + `10` and would pass the rule, but the tokenizer is not in the HF cache (only `tokenizer_config.json` is), so I did not verify it (EST).

**Prompt length limit.** T_max = 512 after the chat template (hard stop 1,024). Evidence: WVS accepted max 253, USA bank max 459, p99 385 `[C7]`; Llama adds about 25 (EST).
The `attn_topk_idx` array is uint16, so T < 65,535 is a hard format limit. Rendering cost for the viewer at T = 512 was not measured (viewer is fenced); the
instance count scales as T x L x 11 marks, so 512 is 3.8x the T = 136 case.

### 5.2 Models

| Source | v1 policy |
|---|---|
| HF id allowlist | the 4 current keys plus SmolLM2-360M and Llama-3.2-1B/3.1-8B **after** the llama3 RoPE fix. No free HF ids: an arbitrary id can be a different architecture (the code raises on biases and non-SiLU) or a download of tens of GB. `trust_remote_code=False` always. |
| LoRA upload | `adapter_config.json` + `adapter_model.safetensors` only. **Reject `.bin`** (pickle). Cap 500 MB (r64 all-linear on 8B is about 670 MB float32, EST `[C6]`; r16 qkvo is 54.5 MB). |
| Base-model match | `base_model_name_or_path` must equal the selected base id (today it is never compared `[C9]`). Layer count, `hidden_size`, target-module shapes must also match the base. |
| Tensor completeness | every `lora_A`/`lora_B` the config implies must be present (`res.missing_keys`), none extra. Fixes the 8.9e-4 silent difference `[C9]`. |
| Config sanity | `peft_type == LORA`; `r <= 64`; `use_dora`/`use_rslora` allowed (merge is plain weights afterwards) but `bias != "none"` and `modules_to_save` rejected; no NaN/Inf. |
| dtype of the file | float32 or bf16. Load into float32 (or float64 for the 135M path), never into a bf16 base for merging (section 3.1). |
| The peft float64 trap | `PeftModel.from_pretrained` leaves every LoRA B at zero in a float64 base. `load_hf` sets the state dict explicitly and compares every tensor with the file (`llama_capture.py:260-282`). A test asserts merged dW equals (alpha/r)BA to 1e-12 (`tests/test_llama_capture.py`; 20 tests pass `[C10]`). Keep that guard when dtype becomes a parameter: in float32 the trap may not occur, but the check is still the proof. |
| Upload size and disk | 500 MB per adapter, 5 GB adapter cache, LRU. SHA-256 of the safetensors file is already the adapter id in the manifest. |

### 5.3 Exports and batch limits

| Limit | Proposal | Basis |
|---|---|---|
| T_max | 512 (hard 1,024) | section 5.1 |
| options per item | 12 | `attn_topk` unaffected; Eq. 6 cost is linear in codes (0.115-0.120 s per code at 135M f64 `[C1]`) |
| items per batch | whichever is smaller: 200 items, or 300 s of estimated compute (section 4), or 1 GB of exports | 135M f64: about 100 items per 300 s (pair). 1B f32 MPS: about 40. 8B Colab: about 40. |
| export mode | `full` for 1-5 items, `lite` (no attention top-k) above that | attention is 93% of bytes `[C12]` |
| disk cache | 5 GB LRU | 135M: about 250-500 full items |
| concurrency | 1 job, queue depth 10 | pass already uses 8 threads `[C1]` |
| resident models | 12 GB budget on this Mac, LRU | section 2.1 |

---

## 6. Q3: What a non-technical social scientist or economist tries in the first 30 minutes

"Works today" means: runs with the shipped code from a Python session or the CLI. "UI" means the viewer. None of these works on a prompt typed into the UI. Effort is
EST: S <= 1 day, M 2-4 days, L > 1 week, counted on top of the section-2 pipeline (which is itself S-M and is the shared prerequisite).

Evidence from `experiments_poc.py` `[C8]` is on **one 135M model, single items, n = 4 per group**. It shows the experiment runs. It is not a finding about the model.

| # | Their question | Works today? | Missing | Effort |
|---|---|---|---|---|
| E1 | "If I reword the question, does the answer change?" (paraphrase) | Python: build an `Item` with other text and call `capture_run`. Ran: Q57 original P(trusted) 0.68, hand paraphrase 0.717, T 136 -> 132, conservation pass `[C8]`. | form + variants table (margin, probs, per variant) | M |
| E2 | "If I flip the order of the options, does the answer follow the label or the position?" | Python, with j+ following the label. Ran: Q57 P(trusted) 0.68 original vs 0.443 reversed, margin +0.755 -> -0.227 `[C8]`. For this model that is position bias, an effect of about 24 points. | one click "run both orders" plus a position-bias summary (mean of the two orders) | S |
| E3 | "Does telling it 'you are a typical adult in Argentina' change the answer?" (country persona vs none) | Python string replacement of the persona sentence (the verbatim `paper_b` persona text). Ran: P(trusted) 0.68 -> 0.747, T 136 -> 139 `[C8]`. `items.py` implements only `prompt_country=None`. | persona selector with the paper's country list | S |
| E4 | "Which words in my question does the answer depend on?" | Python leave-one-word-out: 23 variants in 4.9 s, largest shifts `you` 0.159, `would` 0.133, `most` 0.127 `[C8]`. Attention arcs at the readout row exist in the viewer but show where heads look, not what the answer depends on. | occlusion strip over tokens (replace, not delete, so T and positions stay fixed), plus a caveat that it is causal on the input, not on the weights | M |
| E5 | "Does more training move the answer further?" (dose-response: base, e1, e3) | Yes via the CLI and the viewer for the 6 exported items: three models, two pairs. Held-out margins: e1 vs e3 differ strongly in the audit (the log-ratio goes from -5.09 to +11.76 on held-out pairs, `AUDIT.md` §10). | small multiples of margin by model for one item, from `index.json` | S |
| E6 | "Does the fine-tune move every dimension of the GPS or only some?" | Python loop: 6 dimensions x 4 held-out USA bank items x 2 models = 48 passes in 24 s `[C8]`. d_margin (e3 minus base): trust +0.52 (4 of 4 positive), patience -0.63 (4 of 4 negative), altruism -0.40 and negrecip -0.27 (3 of 4 negative each), posrecip +0.16 and risktaking +0.05 (mixed signs). n = 4, an anecdote. | batch runner + per-dimension table with intervals; a margin-only fast path (0.2 s vs 0.8 s per run); must use held-out items only | M |
| E7 | "Is an anchor-aligned scenario easier than a misaligned one?" | Bank items put j+ on the anchor-aligned answer, so the margin's sign is the alignment. "Misaligned" by swapping j+ is just the negated margin, so it is not a new measurement. The real contrast is a scenario from another country's anchor on the USA adapter: works via CLI `bank_<CC>_<triplet>` ids. | country picker for bank items; wording in the UI that margin sign = alignment | S |
| E8 | "Does it behave sensibly on a question it never saw?" (bank-trained adapter on WVS items) | Yes: `wvs_Q57`, `Q43`, `Q81` with e1/e3 are exported. 23 of 35 WVS rows are runnable `[C7]`. | item browser listing the 23 accepted items and the 12 refused with reasons | S |
| E9 | "Where in the network is the answer decided?" | Yes in the viewer: running margin polyline, DLA of heads and MLP per layer, for exported items. | on-demand items (the pipeline) | S given pipeline |
| E10 | "Type my own survey question and see what the model says and how sure it is." | No. `item_from_id` accepts only `wvs_*`/`bank_*`. Python with a hand-built `Item` works. | the section-2 pipeline | M |
| E11 | "Run my 40-question instrument and give me a table of P(option) per model." | No. `QUESTION_MAP` is a constant. 10 of 35 sample rows are 1-10 scales that are refused `[C7]`. | item-file loader, table (CSV) export, per-item pass/fail, refusal report; the 1-10 policy (section 5.1) | M |
| E12 | "Compare two fine-tunes (say a USA and an Argentina adapter) on the same questions." | No: only the USA e1/e3 adapters exist locally and the registry is a hard-coded dict in `export.py`. | adapter upload + validator (section 5.2) + arbitrary (A, B) pair choice | M |
| E13 | "Does adding age, gender or income to the persona change it?" | Technically as E3. But the paper has only the country persona, so new personas leave the verbatim paper prompt. | scope decision first | S (code), decision for Augusto |
| E14 | "Let it answer in words and show me why." | No, and the premise is off: the workbench reads P(code) at one position (Eq. 6) and decomposes that logit gap. It does not generate text. | out of scope for v2; say so in the UI | L, recommend no |

---

## 7. Recommended sequence

All sizes EST. Owners are suggestions for the PM.

| Slice | Content | Owner | Effort |
|---|---|---|---|
| A | Item factory + readout pre-flight with friendly errors + `numeric`/`scale_1_10` refusal messages + content cache key + `Session` that persists | engineer | S |
| B | Job server (SSE), per-stage progress callback, estimate endpoint using the section-4 formula | engineer | S-M |
| C | "New prompt" panel, progress bar, estimate notice, variants table (E1, E2) | creative / PM (`viewer/**`) | M |
| D | Capture core generalisation: dtype/device parameters, float32 gates, llama3 RoPE, last-row logits, layer streaming, unmerged LoRA | engineer | M |
| E | Adapter upload + validator (section 5.2) | engineer | M |
| F | Batch runner, `lite` export, per-dimension table (E6, E11) | engineer + creative | M |

Why this order: A + B + C deliver E1-E4, E9, E10 on the 135M models with no change to the capture core and no change to any gate. D is needed before any model above
135M and changes the contract thresholds, which makes it the first thing that needs Augusto.

## 8. Decisions that belong to Augusto (not made here)

1. **Float32 gates.** Adopt a second, scale-aware gate set for float32 (section 3.1), or keep float64-only and restrict v2 to 135M-1B.
   This changes `spec/export_contract.md`. The gates are "from the brief".
2. **1-10 scale items** (section 5.1): refuse, restrict to 0-9, or letter codes. Letter codes leave the verbatim paper prompt.
3. **Personas beyond country** (E13): leave the verbatim paper prompt or not.
4. **Llama support** (P1): touches the capture core, so it is scope. It is also the only route to the 8B model and a Colab dependency.
5. **Colab for 8B**: acceptable data path for items and adapters (section 4.2 note).
6. **Anything touching paper numbers**: none of this does. The workbench exports are explanatory and none of the above changes a number in a paper pipeline.

## 9. Commands and files

All run from `workbench/` unless noted. Prefix for every Python call: `env -u PYTHONPATH PYTHONPATH=src uv run python ...`
Raw output of each is in `plans/scripts/out/`.

| Tag | Command | Output | Exit |
|---|---|---|---|
| C0 | `sysctl -n machdep.cpu.brand_string hw.memsize hw.perflevel0.physicalcpu hw.perflevel1.physicalcpu` | Apple M4 Pro, 25769803776, 8, 4 | 0 |
| C1 | `plans/scripts/bench_baseline.py` | `out/bench_warm.txt` | 0 |
| C1b | `python -c "from sca2_workbench import items as I; ..."` (code counts of Q57, Q43, Q81) | 2, 3, 4 codes | 0 |
| C2 | `plans/scripts/bench_baseline.py --cold` (EXPORTS redirected to `$TMPDIR`) | `out/bench_cold.txt` | 0 |
| C2b | `python -c "import time; t=time.time(); import torch, transformers, peft; ..."` | 1.83 s | 0 |
| C3 | `plans/scripts/dtype_gaps.py` (72 rows) | `out/dtype_gaps.txt`, `out/dtype_gaps.jsonl` | 0 |
| C4 | `plans/scripts/scale_bench.py <model> <modes>` for 135m, 360m, 1b, 8bv-L1, 8bv-L2 (one process each; 1b f64 separately) | `out/scale.jsonl` | 0 each |
| C5 | `env -u PYTHONPATH uv run python plans/scripts/fit_time.py` | `out/fit_time.txt`, `out/fit_coef.json` | 0 |
| C6 | `env -u PYTHONPATH uv run python plans/scripts/estimates.py` | `out/estimates.txt` | 0 |
| C6b | `python -c "import estimates as E; ..."` (formula vs file bytes for 4 runs and 4 pairs) | within 112 bytes of 4.6-9.5 MB; pairs exact | 0 |
| C7 | `plans/scripts/validate_items.py` | `out/validate_items.txt` | 0 |
| C8 | `plans/scripts/experiments_poc.py` | `out/experiments_poc.txt` | 0 |
| C9 | `plans/scripts/adapter_guard_probe.py` | `out/adapter_guard_probe.txt` | 0 |
| C10 | `cd .. && env -u PYTHONPATH uv run --project workbench pytest workbench/tests -q` | `out/pytest.txt`: 20 passed in 5.49 s | 0 |
| C11 | `plans/scripts/probes.py` (llama3 RoPE refusal, MPS limit and float64 error, ulp values, stored dtype) | `out/probes.txt` | 0 |
| C12 | `ls -l exports/*.bin`, `du -sh exports`, `ls exports \| wc -l` | 141 MB, 77 files, byte sizes quoted in 4.3 | 0 |
| C13 | `plans/scripts/f32_ref_gap.py` | `out/f32_ref_gap.txt` | 0 |

Exit codes were read from the process, not through a pipe, except where the output was only `cat`ed afterwards. Where I wrote output to a file with `> file; echo "exit $?" >> file`, the exit is in the file.

**Caveats on method.**
- `scale_bench.py` peak RSS is the process peak and is cumulative across modes within one process. Only the first mode of each process (f64 CPU for 135M, 360M, 1B) is a clean per-mode value; those are the ones quoted.
- 360M, 1B and 8B-layer timings are on random-weight models with the real architecture (no such checkpoint is in the HF cache). RoPE is the default one there because `llama_capture` refuses the real Llama-3 scaling (P1). That does not change timing.
- The 8B numbers are per-layer timings from 1- and 2-layer probes at the real layer widths (vocab cut to 32,000 so a float64 copy fits in RAM), extrapolated to 32 layers. No 8B was run.
- `lowprec.py` is a prototype copy of `llama_capture.run`. At float64 on CPU its head attribution is identical to `LC.run`; I did not compare its other outputs bit-for-bit.
- `bank_*` items read `synthetic_generation/outputs/gps_sign_relabel_all/D_syn_USA.jsonl` (the same path `items.py` uses). Nothing under `data/` was read.
- No git commit or push. The whole `workbench/` folder is untracked in this worktree (`git status`: `?? workbench/`).
