# Export contract: `sca2-workbench/capture@1.1`

`@1.1` adds fields only (see "Changes from @1"). A reader of `@1` files keeps working, and a reader of `@1.1` must tolerate their absence in `@1` files.

The 3D viewer (`workbench/viewer/`) draws only what this contract carries. Each mark on screen is one entry of one array below.

## Producer and checks

- **Producer:** `src/sca2_workbench/export.py`, which calls `llama_capture.run` (a float64 pass) once per (model, prompt).
- **Contract tests:** `tests/test_llama_capture.py` (the `@1` contract) and `tests/test_export_v11.py` (segments and the B − A attributions). All must pass.

## Files

The files live in `workbench/exports/`. That folder is gitignored and stays on this machine. The viewer reads it through the Vite dev server at `/exports`.

| File | Content |
|---|---|
| `index.json` | Every run and pair, with the model registry |
| `run__<model>__<item>.json` + `.bin` | One model × one prompt |
| `pair__<a>__<b>__<item>.json` + `.bin` | Exact differences between two runs of the same prompt |

The manifest maps each array name to `{dtype, shape, offset, nbytes, desc}` inside the `.bin`. Arrays are little-endian and C-ordered. Values are computed in float64 and stored as float32. The only exception is the uint16 top-k attention index.

## Run manifest: `segments` (new in @1.1)

`segments` is a list of `{a, b, kind, label}`. `[a, b)` is a half-open token range. The ranges cover `[0, T)` exactly once and in order, with no gap and no overlap. The exporter checks this and raises otherwise. The value is `null` for an ad-hoc prompt that was not built from parts; the export never contains one.

The exporter derives the ranges from how `items.py` builds the prompt, not from token text. `Item.parts` lists the user prompt as `(kind, label, text)` parts. The chat template inserts the user prompt verbatim, so its character span is found exactly. The template's own text gives the system turn and the closing markers. Character spans map to tokens through the tokenizer's offset mapping, and a token that straddles a span edge is an error.

| `kind` | What it covers | WVS | bank |
|---|---|---|---|
| `template` | Chat markers and their newlines: `<\|im_start\|>system\n`, `<\|im_end\|>\n<\|im_start\|>user\n`, `<\|im_end\|>\n<\|im_start\|>assistant\n` | yes | yes |
| `system` | The template's default system text (SmolLM2 inserts one, because the prompt has no system message) | yes | yes |
| `instruction` | Persona and tone; the response rule ("Select exactly one …"); the output rule ("Return only the response code …"). Each is its own segment | yes | yes |
| `question` | `Question:\n` + the stem, with the blank line after it. Label `WVS question` or `scenario` | the WVS stem | the bank scenario paragraph |
| `options` | The option lines `1: …\n2: …`, with the blank line after them. Label `options <first>–<last>` | yes | yes |
| `answer_cue` | `Answer:` | yes | yes |
| `readout` | The shared completion prefix, which is the lone `Ġ` token. Its last token is t* | yes | yes |

Rules:
- A blank-line separator belongs to the segment before it.
- **t\* is its own segment.** `readout` is `[T−1, T)` whenever the completion prefix is one token, as it is for every current item. If a prefix were empty, there would be no `readout` segment, and t* would be the last token of the final `template` segment. If it were longer than one token, `readout` would hold all of the prefix and t* would be its last token. A reader should use `readout.position` for t* and treat the `readout` segment as the place it sits.
- `kind` has no `scenario`. A bank scenario is a `question`, and only the label differs.
- Both item families produce the same 11 segments, in the same order: template, system, template, instruction, question, instruction, options, instruction, answer_cue, template, readout. Two runs of a pair share the same list.
- The old browser heuristic (`segments()` in `design/layout-v2/common.js`) is replaced by this field. It missed the 92-token scenario of `bank_USA_00023ac74dac`: here it is `question`, `[55, 147)`.

## Run arrays

Shapes use L = 30 layers, H = 9 query heads (3 KV heads), F = 1536 neurons and T = number of tokens. t* = T − 1 is the readout position.

| Name | Shape | Tensor slice |
|---|---|---|
| `resid_norm` | (L+1, T) | ‖h^l_t‖₂. The residual entering layer l; l = L is the final state, before the norm. |
| `attn_norm`, `mlp_norm` | (L, T) | ‖a^l_t‖₂ and ‖m^l_t‖₂ |
| `head_norm` | (L, H, T) | ‖o^l_{h,t}‖₂, where o_h = A_h V_{kv(h)} W_O[:, h]ᵀ |
| `attn_topk_idx` / `_val` / `_mass` | (L, H, T, 16) / (L, H, T, 16) / (L, H, T) | Top-16 keys of each attention row, their probabilities, and the stored mass. 65535 marks an empty slot. |
| `q3_count` | (L, T) | Number of neurons with g̃ < −0.05 and u < −0.05 |
| `q3_write_norm` | (L, T) | ‖Σ_{i∈QIII} c_i W_down[:, i]‖₂ |
| `g_last`, `u_last`, `c_last` | (L, F) | SwiGLU poles and product at t* (unclamped pass) |
| `head_attr`, `neuron_attr` | (L, H), (L, F) | DLA to logit(j₊) − logit(j₋) at t* |
| `attn_attr`, `mlp_attr` | (L,) | Per-layer sums of the two arrays above |
| `running_margin` | (L+1,) | h^l_{t*} · w, the margin read from the residual entering layer l. Its last entry equals the margin. |
| `*_clamped` | as above | The same quantities from the pass with Quadrant III clamped. The clamp is applied in every layer and at every position, during the pass. |

DLA uses w = γ_final ⊙ (W_U[j₊] − W_U[j₋]) / ρ, where ρ = √(mean(h^L_{t*}²) + ε) is frozen. That is the standard frozen-scale convention. With it, the embedding, all heads and all neurons sum exactly to the margin.

## Pair arrays

| Name | Shape | Meaning |
|---|---|---|
| `d_resid_norm`, `d_attn_norm`, `d_mlp_norm` | (L+1, T), (L, T), (L, T) | ‖x_B − x_A‖₂ of the same slice, computed from both passes in float64 |
| `d_head_norm` | (L, H, T) | ‖o_B − o_A‖₂ per head |
| `d_weight_head` | (L, H, 4) | ‖W_B − W_A‖_F for the head slices of q, k, v, o. The k and v slices belong to a KV head, so the 3 query heads of a group share them. |
| `d_weight_mlp` | (L, 3) | ‖W_B − W_A‖_F for gate, up and down. This is exactly 0 for a q,k,v,o LoRA. |

### Readout attributions B − A (new in @1.1)

Each is computed as B − A in float64 from the two float64 passes, then stored as float32. Each comes from the matching run array.

| Name | Shape | Meaning |
|---|---|---|
| `d_head_attr` | (L, H) | `head_attr(B) − head_attr(A)` |
| `d_mlp_attr` | (L,) | `mlp_attr(B) − mlp_attr(A)` |
| `d_attn_attr` | (L,) | `attn_attr(B) − attn_attr(A)`, which equals `Σ_h d_head_attr`. It is a convenience and not an extra term of the gate. |
| `d_head_attr_clamped`, `d_mlp_attr_clamped` | as above | The same from the clamped passes. There is no `d_attn_attr_clamped`, because the run arrays have no `attn_attr_clamped`. |

The pair manifest adds these top-level scalars, all float64:

| Key | Meaning |
|---|---|
| `d_embed_attr`, `d_embed_attr_clamped` | `embed_attr(B) − embed_attr(A)`, from `readout.embed_attr` and `readout.embed_attr_clamped` |
| `d_margin_clamped` | `margin_clamped(B) − margin_clamped(A)`. `d_margin` was already there. |

## Manifest `conservation` block

The block of a **pair** manifest is new in @1.1 and is described after the run table below.


The block lists each check, its threshold, and the `pass` flag.

| Check | Threshold |
|---|---|
| Residual closure | < 1e-3 (brief) |
| DLA gap | < 1e-2 (brief) |
| `hf64_logits_max_rel_gap` | < 1e-10 |
| `hf_*` (HF as shipped) | none; listed for information |
| Eq. 6 teacher-forced gap | none; listed for information |

The DLA gap is checked in both the normal and the clamped pass.

**Pair `conservation` block (new in @1.1).** The B − A of the readout attributions sums to the B − A of the margin:

    Σ d_head_attr + Σ d_mlp_attr + d_embed_attr = d_margin           (and the same with _clamped, d_margin_clamped)

| Check | Threshold |
|---|---|
| `d_attr_gap`, `d_attr_gap_clamped` (float64 sums of the differences) | < 1e-6 |
| `d_attr_gap_float32`, `d_attr_gap_float32_clamped` (sums of the stored float32 arrays, in float64, plus the float64 `d_embed_attr`) | < 1e-6 |

`pass` is true only when all four hold, and the exporter raises before it writes the pair if one fails. The float32 gap is what a viewer can add up. Over the 16 exported pairs its worst value is 7.4e-8.

The `hf64` check compares our pass with HF after removing HF's three float32 casts: RMSNorm, RoPE and the eager softmax. That gap is about 5e-15 relative. With the casts left in, HF differs from our pass by about 1e-6 relative. That difference is float32 round-off in HF, and the `hf_*` gaps record it.

## Readout (Eq. 6)

The prompt comes from `paper_b` v1 (verbatim, no country name) and is wrapped in the Instruct chat template. Each completion is " " + code.

SmolLM2 splits " 1" into `Ġ` + `1`. The code tokens therefore diverge one position after the template, at the shared `Ġ`. That position is t*. At t*, a softmax over the code-token logits equals the full teacher-forced Eq. 6, and a test checks this.

Items whose codes do not split as a shared prefix plus one token are refused. Q50 is one, because " 10" shares a prefix with " 1".

Bank items are the anchor scenario posed as a two-option question. The option order comes from a hash of `triplet_id`. j₊ is always the chosen (GPS-sign-aligned) code. For an adapter run, `model.adapter.item_split` records whether the scenario was in the adapter's training split.

## Changes from @1

Additive only. No array, shape, offset or gate of @1 changed. After re-export, every @1 array is byte-identical and every margin is bit-identical.

- Run manifest: `segments`, and `schema` is `@1.1`.
- Pair arrays: `d_head_attr`, `d_mlp_attr`, `d_attn_attr`, `d_head_attr_clamped`, `d_mlp_attr_clamped`.
- Pair manifest: `d_embed_attr`, `d_embed_attr_clamped`, `d_margin_clamped`, `conservation`.
- A viewer reads `@1` files without these fields. It should fall back or hide the feature when `segments`, `conservation` or a `d_*_attr` array is absent.

## Models

| Key | Model |
|---|---|
| `smol_base` | HuggingFaceTB/SmolLM2-135M |
| `smol_inst` | HuggingFaceTB/SmolLM2-135M-Instruct |
| `smol_inst_usa_e1` | smol_inst + `models/usa_e1` (USA DPO LoRA, paper recipe, 1 epoch) |
| `smol_inst_usa_e3` | smol_inst + `models/usa_e3` (3 epochs) |

All four use the Instruct tokenizer; the vocabulary is identical across them.

Adapters are merged after an explicit state-dict load, and every LoRA tensor is checked against the file. This works around peft 0.21.2, which silently loads LoRA B as zero into a float64 base.
