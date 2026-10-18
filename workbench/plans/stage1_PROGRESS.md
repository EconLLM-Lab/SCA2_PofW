## 2026-10-17 - t* on the Llama-3 tokenizer (t_4e28ba8d, tokenizer files only, no src edits)

Report: `plans/stage1_tstar.md`. Probes ran on the real `meta-llama/Llama-3.1-8B-Instruct`
tokenizer files (downloaded with the profile token, 200). `meta-llama/Llama-3.2-1B[-Instruct]`
tokenizer files are **403** (Llama 3.2 licence not granted to this account); no mirror used.

Findings:
- `' 1'`..`' 4'` are **not** single tokens: `[220, 16] [220, 17] [220, 18] [220, 19]`
  (`Ġ` + digit). `'1'`..`'4'` alone are single tokens `16..19`.
- Structure is the same as SmolLM2: one shared prefix token `220` (`Ġ`) then one distinct
  digit token. So **t\* = T-1** on token `220`, exactly the current definition; only the ids
  change (space 220 vs 216, digits 16..24/605/806/717 vs 33..36).
- `' 10' = [220, 605]`, so **Q50 is accepted** by `readout_ids` on this tokenizer (unlike
  SmolLM2, where `' 1'`/`' 10'` differ in length). Contract sentence about Q50 is
  SmolLM2-specific.
- Joint tokenisation `tok(formatted + " " + code) == tok(formatted) + prefix + digit` holds
  on wvs_Q81, Q57, Q50. `n_base` (date pinned): Q81 147, Q57 131, Q50 162.
- Tokenizer identity: `tokenizer.json` (git oid `5cc5f00a...`, 9,085,657 B) and
  `original/tokenizer.model` (LFS sha256 `82e9d319...`) are **byte-identical** across
  3.1-8B-Instruct, 3.2-1B-Instruct and 3.2-1B. `tokenizer_config.json` **differs** (55,351
  vs 54,528 B), so the 3.2 chat template stays unverified until access lands.

Three things the capture needs (for whoever implements): pin `date_string` in
`apply_chat_template`; add a `<|start_header_id|>system<|end_header_id|>` branch to
`prompt_segments` (today the Llama-3 system block is silently labelled `template`); do not
hardcode digit ids (`"10"` is 605).

## 2026-10-17 - Llama-3 RoPE (`rope_type: llama3`) in the capture (t_31895567)

Refusal gone. `src/sca2_workbench/llama_capture.py`: `_rope_scaling` accepts `llama3` (and still
refuses `yarn`/`linear`/`dynamic`/`longrope`, a half-specified `llama3` block, and
`partial_rotary_factor != 1`); `rope_inv_freq` reproduces HF `_compute_llama3_parameters` branch for
branch, and carries the scaling into `_rope`, `_rope_native_dtype` and therefore the forward pass.
`RopeScaling` is the frozen carrier for `factor / low_freq_factor / high_freq_factor /
original_max_position_embeddings`.

New `tests/test_llama3_rope.py` (14 tests: 11 pass, 3 skip). Measured, float64, cos/sin:

| case | positions | max abs diff vs HF's own module |
|---|---|---|
| `meta-llama/Llama-3.1-8B-Instruct` config (head_dim 128, factor 8, theta 5e5) | 0..4096 and {8192, 16384, 65536, 131071} | **0.0** (exact) |
| 3.2-shaped stress config (head_dim 64, factor 32) | same | **0.0** (exact) |

Gate is 1e-12; the agreement is bit-for-bit. The HF side is HF's own `LlamaRotaryEmbedding` with
its float32 table cast switched off (`torch.float = torch.float64` for the call) -- stock HF is
**2.8e-04** away from us because it builds `inv_freq` in float32 and the phase reaches ~1e5 rad, so
1 ulp of the table moves cos/sin by O(1e-4). Positions stay below 2**24 (HF's `forward` casts
`position_ids` to float32). Also checked: rotated q/k via HF's `apply_rotary_pos_emb`, our float32
table is HF's bit for bit, our float64 table rounds into it within 4 ulp, and `_rope_native_dtype`
keeps the scaling.

Configs, no weights. `tests/fixtures/hf/llama-3.1-8B-Instruct.config.json` is the file HF served
(sha256 `29e4c210...`, asserted by the test) -- the Llama-3 skip is **not** the only evidence:
that fixture is the Stage-1 target's real rope block. `meta-llama/Llama-3.2-1B[-Instruct]`
`config.json` is **403** for this account (re-verified 2026-10-17 with the profile token: valid
token, Llama 3.1 approved, 3.2 not in the authorized list); no mirror used. The 3.2-1B cases are
parametrised and skip until a copy of that config lands in the local HF cache, at which point they
run with no code change.

One thing the timed-out prior run left broken, fixed here: the end-to-end plumbing test asserted
that swapping in the unscaled table moves the logits by > 1e-2 on a 24-token prompt. It does not --
the band `llama3` divides is the one with `wavelength > original_max_position_embeddings /
low_freq_factor`, so against a served 8192 original context a short prompt barely rotates it
(measured 2.6e-04 at T = 24, 2.7e-03 at T = 256, 1.5e-02 only at T = 1024). The test model's
original context is now 512, which puts all three branches inside a 256-token pass, and the
measured gap is 2.9e-02. Served-config parity at real positions is the sweep tests' job.

Tests: `49 passed, 3 skipped, 1 warning in 6.63s` (52 collected = the 38 pre-existing + 14 new),
exit 0, via `env -u PYTHONPATH uv run --project workbench pytest workbench/tests -q` from the
worktree root.

## 2026-10-17 - float32 capture mode, relative gates, broken-capture demo (t_1547e1a8)

**No Llama weights were downloaded.** Per the PM re-scope (Augusto, 2026-10-17) the 3.2-1B
stepping stone is dropped and this card measures on the SmolLM2-135M family it already has.
`t_7d7ad93e` (8B) picks its own taus with the same mechanism.

### What the gate is now

`src/sca2_workbench/gates.py` states every check as `|error| / scale <= tau`, with the scale
named per check and `tau` passed in (`GateTaus`), so another model supplies its own numbers.
The brief's absolute 1e-3 closure gate cannot be met in float32: the stream's largest entry is
~8.9e2 on the base model and one float32 ulp there is 1.2e-7 x 8.9e2 = 1.1e-4, so the gate is
about nine ulps wide and the observed float64-to-float32 movement (5.6e-3 abs) is round-off.

| check | error | scale |
|---|---|---|
| residual_closure | `inf`-norm of `h^L - (h^0 + sum a + sum m)` | `inf`-norm of `h^L`, floored at 1 |
| head_closure | `inf`-norm of `a^l - sum_h o^l_h` | `inf`-norm of `a^l`, floored at 1 |
| readout | `|margin - attr_sum|` | `|margin| + 1` |
| pair_attribution | `|d_margin - (sum d_head + sum d_mlp + d_embed)|` | `|d_margin| + 1` |
| logits_reference | `max |logits_ours - logits_ref|` | `max |logits_ref|`, floored at 1 |

float32 is a capture mode of `llama_capture` (`load_hf(..., dtype=)`, `weights_from_hf(...,
dtype=)`, `run` follows the weights' dtype, RoPE tables built in that dtype). float64 stays the
default, and every 135M export still takes it: `Session(dtype=torch.float64)`.

### Measured gaps: `plans/stage1_f32_gaps.md` (+ `.csv`, 1207 rows)

`plans/scripts/f32_gaps.py`, rerun in 29.8 s, exit 0: 3 models x 6 items = 18 (model, prompt)
pairs at T = 136-306, same checkpoint and prompt in float64 (reference) and float32.

| check | f64 max rel | f32 max rel | tau f64 | tau f32 |
|---|---|---|---|---|
| residual closure | 5.45e-15 | 6.23e-06 | 1e-13 | 1e-4 |
| head closure | 0.0 (exact) | 0.0 (exact) | 1e-15 | 1e-5 |
| readout (DLA) | 2.13e-14 | 2.28e-05 | 1e-12 | 1e-3 |
| vs HF reference | 6.14e-15 | 4.44e-06 | 1e-13 | 1e-4 |

Per layer (float32, worst over the 18 pairs): residual closure 2.28e-07 at layer 29, head
closure 1.80e-07 at layer 16; the layer table is in the md.

**tau rule:** 10x the largest measured relative error, rounded up to the next power of ten
(`gates.TAU_MULTIPLE`). 10x is a judgement: far above the measured worst case (so the gate is
not flaky) and far below the failure that matters (a dropped head write, below: 218x and 361x
over tau in float32, 1e11x in float64). Rounding up only adds headroom. Two exceptions are
stated where they sit: `head_closure` is exactly 0 in both dtypes because the gate compares the
same sum computed twice -- its tau is 10x the round-off of that identity summed in float64
(1.80e-07 float32 / 9.1e-17 float64); `pair_attribution` keeps 1e-6, the value the pair gate
already had, because this script exports no pair (worst stored-array form 7.4e-8).

### Broken-capture demo

`run(..., drop_head_write=(layer, head))` deletes one head's write from the *stored* attention
slice while the residual stream keeps it -- what a capture bug looks like from outside. The
head is chosen as the largest write in the clean pass (L23H3 for smol_base, L29H1 for smol_inst).

| check | f32 worst ratio over tau | f64 worst ratio over tau |
|---|---|---|
| residual_closure | 218 | 2.18e+11 |
| readout | 361 | 3.61e+11 |
| head_closure | 0.004 (passes, by construction) | 0.091 (passes) |

`head_closure` does *not* catch it: both stored pieces lost the same head, so they still agree
with each other. The gates that catch it are residual closure and the readout. Pinned as a test
(`tests/test_relative_gates.py::test_a_dropped_head_write_fails_the_residual_gate_by_a_clear_margin`,
both dtypes; asserts ratio > 20 residual, > 10 readout).

### Manifest and viewer contract

`capture@1.1` is unchanged in shape: `conservation.thresholds` (legacy absolute values) and the
absolute fields stay for the existing viewers, `conservation.pass` now comes from the relative
set, and the new `conservation.relative` block carries the taus, every gate (`error`, `scale`,
`scale_desc`, `rel`, `tau`, `pass`), `tau_multiple`, `pass`, `reference_key`, plus
`legacy_absolute_applicable` (false in float32). `provenance.compute_dtype` is no longer
hardcoded. The viewer still recomputes its ✓/✗ from the *absolute* thresholds
(`viewer/src/common.ts` `checksOf`, `viewer/src/data.ts` `clientCheck`), so a float32 export will
render as failed; that reader change is out of this card's fence and is filed as `t_58fed76a`.

Tests added by this card, on top of the gates and the two capture modes: `tau` is an argument for
all five builders (same error, same scale, verdict flips with `tau` only); the same capture flips
verdict under a 1e-3x and a 100x `GateTaus`; the adapter merges in float32 as it does in float64
(the peft-silent-zero-of-LoRA-B trap, caught on the merged `q`); and the broken capture still
fails residual closure and the readout with `10x` the calibrated tau, while the clean capture
passes that loosened set. Full suite: **82 passed, 3 skipped, 85 collected, exit 0** via
`env -u PYTHONPATH uv run --project workbench pytest workbench/tests -q` from the worktree root.
The 3 skips are the Llama-3.2-1B 403 cases from `t_31895567`; the 38 pre-existing tests are
unchanged and pass (`38 passed, exit 0` when run on their own).


## 2026-10-17 - streamed capture, item a: exactness on SmolLM2-135M (t_7d7ad93e)

`src/sca2_workbench/stream_capture.py` (new). `SafetensorsSource` reads one checkpoint directory
lazily (`safe_open`; embedding rows by `get_slice`, only the T prompt rows; unembedding rows only for
the codes, or chunked over the vocabulary for full last-position logits; tied embeddings handled).
`run_streamed` loops layers, upcasts one layer, runs `llama_capture.run`'s layer arithmetic, keeps
the residual plus per-layer summaries, drops the layer. `clamps=(False, True)` runs the plain and the
Quadrant-III-clamped pass off one read of each layer. Peak RSS is logged per layer.

One reordering, stated: `run` freezes the final RMS scale `rho` first and builds
`w = gamma (W_U[j+] - W_U[j-]) / rho`. `rho` exists only after the last layer, so the DLA terms are
dotted with `w_unit = gamma (W_U[j+] - W_U[j-])` while streaming and divided by `rho` at the end.
Closure is accumulated per layer (`acc = h^0 + sum a + sum m`), so it is known per layer.

Exactness (`plans/scripts/stream_exactness.py` -> `plans/scripts/out/stream_exactness.txt`, exit 0):
2 items (Q57 T=136, Q81 T=152) x {plain, clamped}, float64, every stored array + scalar, relative to
the array's max |entry| (floored at 1; the 135M stream has a 2.6e4 massive activation, where one
float64 ulp is 3.6e-12, so a bare absolute 1e-12 is below representation error):

| quantity | max gap vs in-memory `run` |
|---|---|
| residual stream, all layers and positions | **0.0** (bit-identical) |
| worst of the other 19 arrays/scalars | **9.99e-16** (`mlp_attr`) |
| gate | 1e-12 |

`q3_count` and the attention top-k indices are equal (`torch.equal`). Tests:
`tests/test_stream_capture.py`, 5 passed (equality x 2 items, chunked full-vocab logits, float32 stream
stays float32, source reads only what it is asked).

## 2026-10-17 - step_closure gate (PM audit of t_1547e1a8, folded into t_7d7ad93e before any 8B tau)

Gap reproduced (`plans/scripts/step_gap.py`, `out/step_gap.txt`, exit 0; SmolLM2-135M-Instruct, Q57/Q81,
stored MLP write x1.001 in one layer, ratio = gate rel / tau):

| corrupted layer | f32 residual closure | f32 step_closure | f64 residual closure | f64 step_closure |
|---|---|---|---|---|
| L11 (largest MLP write) | 58.6x | **99.8x** | 5.9e10 | 1.0e10 |
| L21 (median) | **0.11x (passes)** | **32.2x** | 1.1e8 | 3.2e9 |
| L5 (smallest) | **0.018x (passes)** | **21.4x** | 1.8e7 | 2.1e9 |
| readout, any layer | 0.008-0.013x | | | |

The audit's numbers are reproduced (58.6 / 0.1 / 0.0). Cause as the audit says: the global scale is
the massive activation. Fix: `gates.step_closure`, the per-layer, per-position closure
`||h^l_t - h^{l-1}_t - a^l_t - m^l_t||_inf / max(||h^l_t||_inf, 1)`, reported at the worst (l, t)
(`gates.worst_step`: numerator and denominator of the worst *ratio*, not two separate maxima).
In `gates.py` (new `GateTaus.step_closure`, `TAUS_F64/F32`, `check_capture` -> `step_closure[_clamped]`
in every manifest), in `llama_capture.run` (`step_err_inf`, `step_scale_inf`, `step_err_by_layer`;
test-only corruption `scale_mlp_write=(layer, factor)`, like `drop_head_write`) and in
`stream_capture` (computed inside the layer loop, same corruption argument). The global residual
gate stays.

Calibration on the 135M family (3 models x 6 items = 18 pairs): clean max rel **1.95e-15 (f64)**,
**2.85e-07 (f32)** -> tau **1e-13 / 1e-5** (10x, next power of ten; same rule). Clean captures pass at
0.003x / 0.023x of tau. The 8B tau is set from the 8B measurement with the same rule (below).

Pinned (`tests/test_relative_gates.py`): arithmetic of the gate; 1.001x on the median layer's stored
MLP write fails `step_closure` by >10x in float32 and float64 on `run`, and the streamed capture gives
the same verdict; the clean capture passes; the readout gate does not move (it reads the in-loop write).
Full suite: 93 passed, 3 skipped, exit 0.

## 2026-10-17 - Llama-3.1-8B-Instruct streamed capture, items b-d (t_7d7ad93e)

Weights: official bf16 safetensors (4 shards, ~16 GB) in the HF cache. `plans/scripts/run8b.sh` ran
every pass in its own process (log `plans/scripts/out/run8b.log`; raw `.pt` in the profile scratch dir,
not in the repo). Items `wvs_Q81` (T=148) and `bank_USA_00023ac74dac` (T=299), base model only. Each
pass = plain + Quadrant-III-clamped capture off one read of every layer + chunked full-vocab logits at t*.

| pass | wall (s) | peak RSS (GB) |
|---|---|---|
| wvs_Q81 f64 | 28.2 | 10.31 |
| wvs_Q81 f32 | 22.2 | 10.84 |
| bank f64 | 38.7 | 10.61 |
| bank f32 | 19.8 | 11.48 |
| Paper B parity (HF f32, block at a time, 6 sequence_logprob + 2 forwards) | 141.4 | 12.91 |

**RSS is above the 8 GB target and below the 16 GB stop line.** It climbs ~0.25 GB per layer (2.98 GB at layer 1,
~11 GB at layer 32) instead of staying flat, so something retains each layer. Likely cause (not
verified): the `safe_open` handle stays open for the whole pass and keeps mmap'd shard pages resident (reclaimable
page cache, counted by `ru_maxrss`). Untested fix: reopen the handle per layer. Not done in this card.

**Paper B parity (PASS).** Input ids from Paper B's `prepare_prompt_for_model` (date 26 Jul 2024, no truncation) equal
the workbench ids (`items.readout_ids(..., chat_kwargs={"date_string": ...})`), asserted per item. Reference =
`score_cohort.sequence_logprob` unmodified, on a float32 HF model with the real modelling code that holds one block
at a time (`offload_hf.py`, equal to the resident model on 135M, < 1e-5 on logits). Max |prob gap| over codes and items:
**7.27e-6** (f64 stream vs Paper B), 6.92e-6 (f32 stream); tau_parity = 1e-4 (10x worst, next power of ten).
wvs_Q81 Paper B probs from scores -21.68 / -16.51 / -17.86 / -21.93 (codes 1..4); bank scores -13.24 / -11.98.

**Gap table (f32 vs f64 stream, plus each pass's own gates).** Relative errors, gate scales as in `gates.py`;
`plans/stage1_8b_gaps.json` has everything including per-layer series.

| check | f64 max rel | f32 max rel | tau f64 (8B) | tau f32 (8B) | tau f64 / f32 (135M) |
|---|---|---|---|---|---|
| residual closure | 2.74e-15 | 3.57e-06 | 1e-13 | 1e-4 | 1e-13 / 1e-4 |
| step closure (new) | 6.37e-16 | 3.83e-07 | 1e-14 | 1e-5 | 1e-13 / 1e-5 |
| head closure | 0.0 | 0.0 | 1e-15 | 1e-5 | 1e-15 / 1e-5 (kept: measured 0) |
| readout (DLA) | 4.32e-15 | 1.16e-06 | 1e-13 | 1e-4 | 1e-12 / 1e-3 |
| logits vs HF f32 (block-at-a-time) | 3.01e-06 | 2.64e-06 | 1e-4 | 1e-4 | 1e-13 / 1e-4 |

tau = 10x the largest observed of the two items, next power of ten (same rule). Only 2 items, so these are
a floor, not a population estimate. The f64 `logits_reference` is bounded by the float32 reference model, not by
our f64 arithmetic; do not read 1e-4 as an f64-grade tolerance. f32-vs-f64: margin rel 2.06e-5 / 6.9e-7, logits at t*
2.5e-6 / 3.1e-6, head_attr 5.1e-6 / 1.1e-5, neuron_attr 8.9e-6 / 2.5e-6, code-prob gap 1.7e-6 / 6.2e-7.
The 8B f32 gaps are the same order as the 135M f32 gaps (residual 3.6e-6 vs 6.2e-6, readout 1.2e-6 vs 2.3e-5), so the
135M f32 taus would also have passed at 8B. **The 8B taus are not written into `gates.TAUS_*`** (those stay the 135M set);
the export carries them in each manifest. Conservation in f64 against the existing 135M relative taus: {"wvs_Q81": {"residual_closure": true, "step_closure": true, "head_closure": true, "readout": true}, "bank_USA_00023ac74dac": {"residual_closure": true, "step_closure": true, "head_closure": true, "readout": true}}.

**Contract requirement for the Colab stage:** CUDA float32 passes need `torch.backends.cuda.matmul.allow_tf32 = False`
and `torch.backends.cudnn.allow_tf32 = False`; TF32 (10-bit mantissa) would void every float32 tau above.

**Export (item d)** under `workbench/exports/llama31_8b/` (a subdirectory: `index.json` and the viewer's data
are untouched; no `rebuild_index`): `run__llama31_8b__{wvs_Q81,bank_USA_00023ac74dac}.{json,bin}` (f64 capture) and
`run__llama31_8b_f32__...` (f32). Bins 23,205,600 B (Q81) and 39,383,744 B (bank), each of the four; manifests
carry `compute_dtype`, the 8B taus, every gate (`conservation.relative`: residual / step / head / readout, plain and
clamped, `logits_reference`, `paper_b_parity`), `provenance.streaming` (wall, peak RSS) and the Llama-3 system
segment. All four `conservation.pass` = True. `stream_export.py` writes them. Not done: viewer rendering of an 8B run
(out of fence), `index.json` entry.

Also changed: `items.readout_ids(chat_kwargs=)` (pins `date_string`) and the Llama-3 `system` branch in
`prompt_segments`; `offload_hf.py`; `stream_export.py`; `gates.py`/`llama_capture.py` step gate.
Streamed closure now sums attention and MLP writes separately (as `run` does): the first version replayed the loop's
own recurrence and was zero by construction.

## 2026-10-17 - spec/conservation.md: "float32 relative gates" section (t_c646e31a)

Appended the section to `spec/conservation.md` (writer, prose only; no code, data or viewer touched). Numbers are copied from `plans/stage1_f32_gaps.md`, this file and `plans/stage1_8b_gaps.json`; multiples (tau / max) were computed from them. Flags: the brief named Llama-3.2-1B as the reference, but it was never measured (403), so the section states the 135M family and Llama-3.1-8B-Instruct. TODO: 8B per-layer table and an 8B broken-capture demo. `plans/stage1_f32_gaps.md` section 4 still says a dropped head is "50x over tau in float32"; its own section 5 and this file say 218x residual / 361x readout.

## 2026-10-17 - first real 8B pair: Instruct vs Instruct + Paper B USA LoRA, unmerged, streamed (t_df388a80)

**Adapter.** `Bonorinoa/SCA2-paper-b-adapters` (dataset), `adapters/USA` (USA was present), only that
directory downloaded (HF cache, repo `main` = c4b0f36). `adapter_model.safetensors` sha256 `7329c4a1...7eef`;
the same blob as at revision `7550fd4`, the `adapter_revision` of Paper B's archived scores (checked by
`get_paths_info`, metadata only). Config: r = 16, lora_alpha = 32 (scale 2.0), targets q/k/v/o_proj (no MLP),
bias none, modules_to_save null, dora/rslora off, patterns empty; 256 tensors = 32 layers x 4 modules x A,B, float32.
The guards come from `llama_capture.check_adapter`: the `load_hf` guard block was moved into it, and `load_hf`
calls it, so the behaviour is unchanged. It also requires lora_ keys. `stream_capture.LoraAdapter` adds refusals
for peft variants the formula does not implement. It also checks: the A/B pairs are complete, the rank equals r,
and the file's modules equal `target_modules`.

**Unmerged LoRA in the stream.** `_layer(lo=..., scale=...)`: every adapted projection is
`x W^T + (a/r)(x A^T) B^T`, with A/B read from the file (no peft model, AUDIT.md section 11). The per-head o_proj
write is `z_h W_O[:,h]^T + (a/r)(z_h A[:,h]^T) B^T`, so the head DLA split is unchanged. down_proj (unused here)
is handled the same way per neuron. `run_streamed_pair` runs A, A clamped, B, B clamped off one read of each layer.
The B - A norms (`d_resid/attn/mlp/head_norm`) are computed inside the loop, so the (L,H,T,d) head writes are
never stored. `lora_weight_delta` gives `||W^B - W^A||_F` per head/projection from `(a/r) B A` in Gram form.

| check (float64) | result | gate |
|---|---|---|
| one layer, real 8B + real adapter, wvs_Q81 input, unmerged vs merged `(W + (a/r)BA) x`: layer 0 | worst 7.5e-15 (topk_val); h_out 9.6e-16 | 1e-12 |
| same, layer 15 (input pushed through 15 base layers) | worst 1.7e-14 (topk_val); h_out 2.2e-17 | 1e-12 |
| the adapter does move the layer (h_out unmerged vs base) | 4.0e-3 (L0), 6.4e-5 (L15) | > 0 |
| 135M + models/usa_e1, whole model, A and B (plain + clamped) vs `llama_capture.run` on peft-merged f64 weights | all arrays <= 1e-12 | 1e-12 |
| 135M, in-loop B - A norms vs differences of the in-memory stacks | <= 1e-12 | 1e-12 |
| 135M, Gram weight delta vs `export._weight_delta` on merged weights | < 1e-9 (merged side carries W's rounding) | 1e-9 |

**Paper B parity for B.** The reference is `score_cohort.sequence_logprob`, unmodified. It runs on HF + peft
(`get_peft_model` with the adapter's own `LoraConfig`: unmerged peft forward, float32, one base block resident).
The LoRA tensors are set from the file and compared to it. The new `offload_hf.build_offloaded_hf(adapter_dir=)`
equals resident `load_hf(..., adapter, float32)` on 135M (< 1e-5).
Max |prob gap| over codes, our f64 stream vs Paper B: **4.33e-6 (wvs_Q81)** and **1.06e-10 (bank)**, tau 1e-4 -> PASS.
Paper B scores for B: Q81 -28.16 / -28.98 / -44.01 / -46.08; bank -27.86 / -41.02. Logits vs the same HF+peft model:
1.8e-6 / 2.3e-6 relative (tau 1e-4).

**Archived Paper B score (`planning/.../paper-b-20261011/scores_for_join/USA_adapter_option_probabilities.csv`,
read only).** Q81 exists; bank items are not in Paper B's scored WVS outputs. Archived USA Q81 probs: 0.999995 / 5.2e-6 / 6.6e-10 / 1.9e-10
(logprobs -27.92 / -40.09 / -49.06 / -50.31, on a 1/64 grid, so probably bf16). Ours: 0.6948 / 0.3052 / 1e-7 / 0.
**Max gap 0.305: MISMATCH, not resolved here.** The archived base row misses too (0.069 / 0.801 / 0.129 / 0.001,
logprobs -20.0 / -17.55 / -19.38 / -24.13, vs ours -21.68 / -16.51 / -17.86 / -21.93). So the cause is shared
by both models: the archived scoring pipeline (dtype, prompt or chat date) differs from the current
`prepare_prompt_for_model` path. The adapter bytes are identical, and code 1 agrees within 0.24 nats, but code 2
differs by 11 nats. Escalated: this touches paper numbers.

**RSS.** The first parity attempt hit the 16 GB stop line (16.6 GB at code 2). The cause is the one stage 1b
suspected: persistent `safe_open` handles keep the mmap'd shard pages resident. Fix: `SafetensorsSource.drop_handles()`,
called after every offloaded block. Peak 16.6 GB -> **4.14 GB**, scores identical. The streamed capture loop does
not call it yet (its passes stayed at 10.6-11.5 GB). It is a one-line follow-up.

| pass | wall (s) | peak RSS (GB) |
|---|---|---|
| layer check (L0, L15) | 0.9 + 9.9 | 11.07 |
| pair capture wvs_Q81 (T=148, 4 passes) | 33.2 | 10.56 |
| pair capture bank (T=299, 4 passes) | 61.7 | 11.50 |
| Paper B parity with adapter (6 sequence_logprob + 2 forwards) | 96.7 | 4.14 |
| weight deltas (Gram) | 0.2 | - |

**Exports** (top level of `exports/`, because the viewer loads `/exports/run__<key>__<item>.json`).
`index.json` is rebuilt; `rebuild_index` now also lists models found in run manifests that are not in `MODELS`.
Keys are `llama31_8b` (A) and `llama31_8b_usa` (B). A is bit-identical (0.0) to stage 1b's float64 base capture
on head_attr, neuron_attr, logits_last and running_margin. All 4 runs pass every gate against the 8B f64 taus:
residual <= 6.8e-15, step <= 1.2e-15, head 0, readout <= 4.3e-15.

| file | bytes |
|---|---|
| run__llama31_8b__wvs_Q81 .bin/.json | 23,205,600 / 16,936 |
| run__llama31_8b_usa__wvs_Q81 .bin/.json | 23,205,600 / 17,851 |
| pair__llama31_8b__llama31_8b_usa__wvs_Q81 .bin/.json | 688,976 / 4,008 |
| run__llama31_8b__bank_USA_00023ac74dac .bin/.json | 39,383,744 / 23,826 |
| run__llama31_8b_usa__bank_USA_00023ac74dac .bin/.json | 39,383,744 / 24,746 |
| pair__llama31_8b__llama31_8b_usa__bank_USA_00023ac74dac .bin/.json | 1,366,064 / 4,016 |

Pair gate (`d_attr_gap`, relative to |d_margin| + 1, tau 1e-6), f64 / stored f32:
- Q81: 1.4e-14 / 1.3e-7, d_margin +17.66;
- bank: 1.8e-15 / 6.7e-8, d_margin +14.42.

Clamped: <= 4.9e-15 / 3.0e-8. Probabilities, A -> B:
- Q81: 0.004 / 0.789 / 0.203 / 0.003 -> 0.695 / 0.305 / 0 / 0;
- bank: 0.221 / 0.779 -> 1.000 / 2e-6.

**Shapes the viewer must handle (8B):** L = 32, H = 32 (8 KV heads, head_dim 128), F = 14,336, d = 4,096.
T is 148 (Q81) or 299 (bank). Run arrays:
- `head_norm` (32,32,T);
- `attn_topk_*` (32,32,T,16);
- `g/u/c_last` and `neuron_attr` (32,14336);
- `resid_norm` (33,T).

Pair arrays:
- `d_head_norm` (32,32,T);
- `d_weight_head` (32,32,4): k/v shared across the 4 query heads of a KV group;
- `d_weight_mlp` (32,3): all zero, because the adapter has no MLP targets;
- `d_mlp_attr` is non-zero through the changed stream.

Bank item split under this adapter: unknown (needs data/, out of fence).

Files:
- `stream_capture.py` (LoraAdapter, `_layer` LoRA, `_stream`/`run_streamed_pair`, `unmerged_vs_merged`,
  `lora_weight_delta`, `drop_handles`);
- `llama_capture.py` (`check_adapter`);
- `offload_hf.py` (peft adapter, drop_handles);
- `stream_export.py` (`adapter=`, `pair_manifest`);
- `export.py` (`rebuild_index` models);
- `tests/test_stream_lora.py` (12 tests);
- `plans/scripts/pair8b.py`, `runpair8b.sh`;
- `plans/stage1_8b_pair.json`;
- `plans/scripts/out/pair8b.log`, `pair8b_layercheck.json`.

Full suite: **105 passed, 3 skipped, exit 0**.
