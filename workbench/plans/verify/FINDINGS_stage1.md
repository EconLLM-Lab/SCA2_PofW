# Independent verification — Workbench stage 1 (Llama-3 support + float32 relative gates)

Verifier card `t_7bb9787f`. Read-only over the project tree; everything I ran lives in
`$TMPDIR` (= `~/.hermes/profiles/verifier/cache/scratch/`) or here.
Model route: `deepseek/deepseek-v4.1-flash-1017` on `openrouter` (pinned on the card).

Working root: `workbench/` in the repository worktree.
All probing commands: `env -u PYTHONPATH uv run --project workbench [--with pandas] python <script>`
from the worktree root; `PYTHONPATH=workbench/src` is set in-process by the scripts.

**VERDICT: ACCEPT.** No criterion fails and nothing blocks. Five documentation/consistency
findings (F1–F5, none functional) and one scope note (F6).

---

## 1. Acceptance criteria

### C1 — test suite passes, ≥38 original tests plus new ones — PASS
```
env -u PYTHONPATH uv run --project workbench pytest workbench/tests -q   (no pipe)
=> 105 passed, 3 skipped, 2 warnings in 25.81s   EXIT=0
```
Collected per file: `test_conservation` 8, `test_dpo_loss` 3, `test_export_v11` 14,
`test_forward_pass` 2, `test_llama_capture` 11 → **38 original**; plus `test_llama3_rope` 14,
`test_relative_gates` 38, `test_offload_hf` 1, `test_stream_capture` 5, `test_stream_lora` 12
→ **108 collected, 105 run, 3 skipped**.
The 3 skips are `workbench/tests/test_llama3_rope.py:163,185,206`, all
`meta-llama/Llama-3.2-1B config.json is not in the local HF cache` — the dropped 3.2 stepping
stone, not a hidden failure (`-rs` output). No `skipif` masks the RoPE parity test: it runs on
the served 3.1 config and on a synthetic factor-32 config.

### C2 — RoPE parity ≤1e-12 in float64 against HF's llama3 rotation, scaled bands exercised — PASS
Re-derived with my own table (llama3 rescaling written from the definition, scratch script
`v_rope.py`), fixture `workbench/tests/fixtures/hf/llama-3.1-8B-Instruct.config.json`
(sha256 `29e4c210…4e6e`, matches the constant pinned at `tests/test_llama3_rope.py:35`),
`rope_theta 500000`, factor 8, low 1, high 4, orig 8192, head_dim 128:
```
bands high=29 medium=6 low=29 of 64
MAX GAP my table vs HF LlamaRotaryEmbedding (torch.float=float64) p=0..4096 : 0.000e+00  PASS
MAX GAP at positions [8192,16384,65536,131071]                            : 0.000e+00  PASS
workbench rope_inv_freq == my inv_freq (torch.equal): True ; _rope vs my table: 0.0
scaled vs unscaled rotation table max gap: 1.999 (the scaling is exercised, not a no-op)
```
The three bands are populated for the served config, so `test_the_sweep_exercises_all_three_llama3_branches`
(`tests/test_llama3_rope.py:164`) is not vacuous; the parity test asserts `gap <= 1e-12` twice
(`:193`, `:199`) plus the production `_rope` entry point (`:203`), and the rotation convention is
checked through HF's `apply_rotary_pos_emb` (`:207`). Measured gap is 0.0, i.e. bit-exact, not
merely under the gate.

### C3 — every gate relative with a stated scale; τ = stated multiple of the measured max; spec numbers match the gap table — PASS
`gates.py` states `|error| / scale <= tau` with a `scale_desc` for each of the six checks
(`src/sca2_workbench/gates.py:13-26, 148-191`); the live verdict is `relative.pass`
(`export.py:204`, `stream_export.py:64`) and the legacy absolute block is retained only for
readers, flagged `legacy_absolute_applicable: false` (`stream_export.py:59-60`,
`export.py:186-187`). No absolute threshold decides any verdict.

Arithmetic re-derived (τ ÷ measured max; the rule is "10x, rounded up to a power of ten",
`TAU_MULTIPLE = 10.0` at `gates.py:71`):

| check | f32 max | τ | x | f64 max | τ | x |
|---|---|---|---|---|---|---|
| residual | 6.23e-06 | 1e-4 | 16.1 | 5.45e-15 | 1e-13 | 18.3 |
| step | 2.85e-07 | 1e-5 | 35.1 | 1.95e-15 | 1e-13 | 51.3 |
| head | 1.80e-07* | 1e-5 | 55.6 | 9.10e-17* | 1e-15 | 11.0 |
| readout | 2.28e-05 | 1e-3 | 43.9 | 2.13e-14 | 1e-12 | 46.9 |
| reference | 4.44e-06 | 1e-4 | 22.5 | 6.14e-15 | 1e-13 | 16.3 |

(*`head_closure` is exactly 0 in the shipped form; the float64 form of the same identity is
used, documented at `spec/conservation.md:129` and `plans/stage1_f32_gaps.md:67`.)
Every x ≥ 10, every τ is the next power of ten above 10x. `spec/conservation.md:121-139` matches
`plans/stage1_f32_gaps.md:12-17,57-62` number for number, and the 8B rows match the export
manifests and `plans/stage1_8b_gaps.json` (see C6). `pair_attribution` (1e-6) is documented as
not measured (`plans/stage1_f32_gaps.md:73`), which is honest rather than dressed up.
Clean-pass headroom I measured myself (135M-Instruct wvs_Q81, `v_corrupt.py`): f32
residual 0.001x / step 0.023x / readout 0.013x; f64 0.008x / 0.002x / 0.014x of τ.

### C4 — broken capture removes a head's write and fails by a clear margin; clean float32 passes — PASS
My own run (`v_corrupt.py`), largest stored head write chosen from `head_norm`
(→ L29H1 here), `drop_head_write` zeroes `o[h]` and subtracts from `a` *after* the stream took
the full `a` (`llama_capture.py:274-280`), so the pieces stop adding up to the stream:
```
f64 drop(29,1): residual 4.7e+10x tau, step 1.39e+12x, head_closure 0.073x (passes), readout 6.22e+10x  all_ok=False
f32 drop(29,1): residual 4.7e+01x tau, step 1.39e+04x, head_closure 0.004x (passes), readout 6.22e+01x  all_ok=False
clean f32: residual 0.001x, step 0.023x, head 0.000x, readout 0.013x -> all_ok=True
```
`head_closure` survives by construction and the test says so (`tests/test_relative_gates.py:275-278`);
the test also re-checks the demo with 10x the τ (`:295-308`), so it is not a threshold artefact.

### C5 — float64 remains the default; 135M behaviour unchanged — PASS
Defaults: `Session.__init__(dtype=torch.float64)` (`export.py:141`), `load_hf`,
`weights_from_hf`, `_rope`, `rope_inv_freq` (`llama_capture.py:140,169,221,412`),
`SafetensorsSource.__init__(dtype=torch.float64)` (`stream_capture.py:60`). Only
`offload_hf.build_offloaded_hf` defaults to float32, which is the HF reference model by design.
Fresh float64 re-runs vs the exports on disk:
```
smol_base/wvs_Q81  resid_norm 4.40e-08  attn_norm 3.60e-08  mlp_norm 3.84e-08  head_norm 3.25e-08 (float32 storage)
                   probs identical to 8 dp, margin 2.5083948746 both
smol_inst/wvs_Q43  resid_norm 3.67e-08  attn_norm 3.35e-08  mlp_norm 2.22e-08  head_norm 3.58e-08
                   probs identical to 8 dp, margin 0.0391862944 both
```
135M exports still carry the old absolute-only block (no `relative`), i.e. they were not
regenerated; the producer states this as a caveat and it matches what is on disk.

### C6 — export conforms to capture@1.1; manifest records the float32 dtype, the gates and τ — PASS
Read from the files with my own reader — script `plans/verify/stage1/v_export.py`, output
`plans/verify/stage1/v_export.out`, last line `### no conformance problems found` — no producer code:
- 28 run manifests (26 top-level + 2 in `exports/llama31_8b/`): `schema` `sca2-workbench/capture@1.1`,
  `segments` partition `[0,T)` with the 11 contract kinds in order, `readout` = `[T-1,T)`,
  `readout.position == T-1`, and every array matches a contract shape for its own
  (L, H, F, T, k) — checked for 135M (30/9/1536, 4 items) and 8B (32/32/14336, T = 148 and 299),
  with no `attn_probs` and the required top-16 `attn_topk_*` storage. Offsets are contiguous
  modulo an **undocumented 8-byte alignment pad** (4-byte gaps before 3 arrays per file); bin
  sizes equal the end of the last array; all values finite.
- dtype: `provenance.compute_dtype` = `float64` for the f64 runs and **`float32`** for
  `exports/llama31_8b/run__llama31_8b_f32__{wvs_Q81,bank_USA_…}.json`; `stored_dtype` float32 everywhere.
- gates and τ: `conservation.relative.taus` + per-check `{error, scale, scale_desc, rel, tau, pass}`
  in every 8B run manifest. 8B f64 τ = residual 1e-13, step 1e-14, head 1e-15, readout 1e-13,
  logits_reference 1e-4, pair 1e-6; 8B f32 τ = 1e-4, 1e-5, 1e-5, 1e-4, 1e-4, 1e-6. These equal
  `plans/stage1_8b_gaps.json[taus][f64|f32][tau]` and the measured maxima in that file reproduce
  the observed rel values (e.g. f32 residual 3.5717e-06/1e-4 = 0.0357x, which I also measured).
- pair manifests: 11 contract arrays, `d_embed_attr`, `d_embed_attr_clamped`, `d_margin_clamped`,
  and a `relative` block with τ = 1e-6 for both forms. Recomputed the float32 gate myself from
  the stored arrays + the float64 `d_embed_attr`: 18/18 agree with the manifest to the last digit
  (worst 1.33e-07 at `pair__llama31_8b__llama31_8b_usa__wvs_Q81`, τ 1e-6).
- `index.json`: 6 models, 26 runs, 18 pairs; every listed file exists and its probs match.

### C7 — fence respected (nothing in `data/`, `viewer/`, Paper B files) — PASS for the stage-1 producers
- `data/`: 58 files, newest mtime **Oct 16 20:03** (checkout time) — untouched.
- `paper_b/`: every `*.py` mtime Oct 16 20:03 — no source touched. The only writes inside the
  tree are `paper_b/__pycache__/*.pyc` at **19:04** (bytecode from importing Paper B for the
  parity check). Report as an observation, not a source edit.
- `workbench/viewer/`: files *were* written at 19:03–19:21 (`src/common.ts`, `dist/*`,
  `screens/f32-gates/*`, `README.md`). By time and scope these belong to `t_58fed76a` — "Viewer:
  read capture@1.1 relative gates so a float32 export does not render as failed" (engineer,
  18:49 → 19:21), a card whose job is exactly `viewer/` — not to the stage-1 cards I verify.
  I cannot attribute writes per process, so this is an attribution from the board and the
  directory contents, not proof; nothing in the three producers' handoffs claims a viewer change.
- No `workbench/data/` exists in the worktree.

## 2. PM's extra checks

- **(a) streaming is exact** — PASS. SmolLM2-135M-Instruct f64, Q57 and Q81, plain and clamped,
  my own key list (`v_135.py`): residual stream **bit-identical** (`torch.equal` True), every other
  array ≤ 2.3e-14 relative; the largest scalar gap is 5.5e-12 on `residual_closure_inf`, whose
  scale is 2.4e3 (2.3e-15 relative); `q3_count` and `attn_topk_idx` equal; `code_logits` vs the
  in-memory `logits_last[[jp,jm]]` ≤ 1.1e-15.
- **(b) unmerged LoRA == merged on a real 8B layer** — PASS, my own code. I wrote the decoder layer
  myself (rms_norm, q/k/v, llama3 rope, causal softmax, o_proj, SwiGLU, down_proj) and ran it on
  Llama-3.1-8B-Instruct layer 0, T=148, f64, adapter r=16 α=32 scale=2.0 on q/k/v/o:
  `a` 5.0e-16, `m` 1.0e-15, `o` 3.4e-16, `h` 9.6e-16 relative (gate 1e-12). The adapter moves
  `h_out` by 4.0e-3 relative, so the comparison is not comparing a no-op.
- **(c) Paper B parity** — PASS. My own run of Paper B's `score_cohort.sequence_logprob` on
  HF float32 (`build_offloaded_hf`, one block resident) + peft adapter, wvs_Q81:
  probs `{1: 0.69482377, 2: 0.30517613, 3: 9e-08, 4: 1e-08}` vs the export's
  `{1: 0.6948281, 2: 0.3051718, 3: 9e-08, 4: 1e-08}`; **max gap 4.328e-06**, τ 1e-4.
  This reproduces the manifest's `paper_b_parity.error` (4.328225e-06) exactly.
- **(d) τ separates rounding from a real 0.1% error at 8B** — PASS, and stronger than at 135M.
  Three streamed float32 8B passes (`v_8b.py corrupt`):
  ```
  clean                     residual 0.0357x  step 0.0331x  head 0x  readout 0.0116x  all_ok=True
  0.1% MLP write at L15     residual 1.79x    step 72.3x    head 0x  readout 0.0116x  all_ok=False
  0.1% MLP write at L21     residual 1.44x    step 113x     head 0x  readout 0.0116x  all_ok=False
  ```
  Step closure separates them by 3 orders of magnitude, and at 8B the *global* residual gate also
  fails (1.4-1.8x), which it did not at 135M.

## 3. PM finding re-test: the step gate and my own corruption

The step gate exists in all three places: `gates.py:154-168`, computed in `llama_capture.run`
(`:322-325`) and in `stream_capture._layer`/`_finish` (`:299-300`, `:502-503`). It is the error at
the worst (layer, position) over `||h^l_t||_inf` there (`gates.py:17-19`).

My own corruption (not the producer's 1.001x MLP demo): the stored attention write at **layer 15,
position 76** (T=152, so not position 0) scaled by 1.001, i.e. 1e-3 relative, applied to the
stored pieces while the stream keeps the truth:
```
float32:  global residual 0.0284x tau -> PASSES (the PM's original finding, reproduced)
          step closure    13.7x  tau -> FAILS
float64:  global residual 2.83e+07x tau, step 1.37e+09x tau
```
Whole-layer 1.001 variants: attention 0.0712x / 31.4x, MLP 0.0619x / 29.4x (float32), and the
producer's in-pass hook on 135M reproduces it (`scale_mlp_write=(15,1.001)` → step 29.4x,
`(5,1.001)` → 22.7x; `all_ok=False` both times). **No BLOCK**: a 0.1% corruption does not pass in
float32 once the step gate is present.

## 4. Findings (none blocking)

**F1 — doc/code conflict: the contract still states absolute thresholds. (medium-low)**
`spec/export_contract.md:99-107` documents the `conservation` block as
`Residual closure < 1e-3 (brief)` / `DLA gap < 1e-2 (brief)` / `hf64_logits_max_rel_gap < 1e-10`.
The manifests now carry those keys under `thresholds` with `legacy_absolute_applicable: false`, and
the verdict is `relative.pass` (`export.py:204`). A reader of the contract alone would gate the wrong
numbers. The `spec/conservation.md` section that was written in this stage does say this, but the
contract — "the current ground truth for every gate" per `conservation.md:4` — was not updated.

**F2 — `legacy_absolute_applicable` means two different things. (low)**
`export.py:187` sets it to `sess.dtype == torch.float64` (so `true` for 135M f64 exports, pinned by
`tests/test_relative_gates.py:332`), while `stream_export.py:60` hardcodes `False` — so the 8B f64
runs, same compute dtype, say `false`. One of the two is wrong about what the flag means.

**F3 — two numbers for the same "massive activation". (low)**
`gates.py:4-6` (and `tests/test_stream_capture.py:6`) say the 135M stream "carries an entry of about
2.6e4" with a float32 ulp of 1.95e-3; `spec/conservation.md:115` says the global residual scale is
4,429. Both are real, but of different quantities: I measured max|h| over all layers = 2.598e+04 and
max|h^L| (the gate's scale) = 4,429 for 135M-Instruct/wvs_Q81. Neither text says which, and the
1.95e-3 ulp belongs to the all-layer number, not to the gate's scale.

**F4 — stale "50x" in the gap table. (low)**
`plans/stage1_f32_gaps.md:54` says the dropped-head bug fails "50x over tau in float32"; §5 of the
same file (`:85-87`) and `spec/conservation.md:141` say 218x (residual) / 361x (readout). The writer
flagged this in the handoff; it is still in the text. My own single-item measurement is 47x/62x
(smol_inst/wvs_Q81), so the direction is right but "50x" is not the calibrated worst case.

**F5 — "Two of the five" over a six-field dataclass. (nit)**
`gates.py:58` and `:103` say five checks; `GateTaus` has six fields (the step gate made it six).

**F6 — scope note, `index.json` completeness. (nit)**
`exports/index.json` lists 26 runs; 28 run manifests exist on disk. The two omitted are the 8B
float32 diagnostic runs in `exports/llama31_8b/`, alongside stale f64 copies of the same runs whose
bins the viewer cannot resolve. The pair card's caveat already says so; the contract's "`index.json`:
Every run and pair" is then not literally true.

## 5. Consolidated handoff summary

Files changed by the stage (mtimes in `workbench/`): `src/sca2_workbench/{gates,llama_capture,
stream_capture,stream_export,offload_hf,items,export}.py`, `tests/{test_llama3_rope,
test_relative_gates,test_stream_capture,test_stream_lora,test_offload_hf}.py`,
`spec/conservation.md`, `plans/stage1_{PROGRESS,f32_gaps.md,f32_gaps.csv,tstar,8b_gaps.json,8b_pair.json}`,
`plans/scripts/*`.

Tests: **108 collected / 105 passed / 3 skipped (3.2-1B config absent), exit 0**; 38 original.

Gap table (SmolLM2-135M family, 18 pairs) — f32 / f64 maxima: residual 6.23e-06 / 5.45e-15,
step 2.85e-07 / 1.95e-15, head 0 (1.80e-07) / 0 (9.10e-17), readout 2.28e-05 / 2.13e-14,
reference 4.44e-06 / 6.14e-15. Llama-3.1-8B (2 items): 3.57e-06/2.74e-15, 3.83e-07/6.37e-16,
0/0, 1.16e-06/4.32e-15, 2.64e-06/3.01e-06.

τ per gate, 135M family and Llama-3.1-8B (the 8B values live in `plans/stage1_8b_gaps.json`
and each manifest, not in `gates.TAUS_*`):

| check | 135M f32 | 135M f64 | 8B f32 | 8B f64 |
|---|---|---|---|---|
| residual | 1e-4 | 1e-13 | 1e-4 | 1e-13 |
| step | 1e-5 | 1e-13 | 1e-5 | 1e-14 |
| head | 1e-5 | 1e-15 | 1e-5 | 1e-15 |
| readout | 1e-3 | 1e-12 | 1e-4 | 1e-13 |
| reference | 1e-4 | 1e-13 | 1e-4 | 1e-4 (bounded by the float32 HF model) |
| pair | 1e-6 | 1e-6 | 1e-6 | 1e-6 |

Broken demo: dropped L29H1 write → f32 residual 47x τ, readout 62x τ, head closure 0.004x (survives);
f64 4.7e10x / 6.2e10x. Clean float32 passes at 0.001x / 0.023x.

t*: Llama-3.1 tokenizer, `T=148`, `n_base=147`, `prompt_ids[-1]=220` (`Ġ`), `t* = 147 = T-1`,
code tokens 16/17/18/19; `" 1".." 4" = [220, digit]`, `" 10" = [220, 605]`, joint tokenisation exact
for all four codes. 3.2 tokenizer is byte-identical (not re-fetched; 403).

Export paths, sizes, timings: `workbench/exports/` —
`run__llama31_8b__wvs_Q81` 23,205,600 B bin + 16,936 B json, `…bank_USA_00023ac74dac`
39,383,744 + 23,826; `run__llama31_8b_usa__*` same sizes; `pair__llama31_8b__llama31_8b_usa__wvs_Q81`
688,976 + 4,008, `…bank_…` 1,366,064 + 4,016; f32 diagnostics in `exports/llama31_8b/`
(23,205,600 / 39,383,744). Producer timings: f64 28.2 s and 38.7 s per streamed base pass,
f32 22.2 s and 19.8 s, pair 4 passes off one read, parity 141.4 s, peak RSS 10.3–12.9 GB.
My re-runs: streamed f32 8B pass 10–15 s, HF float32 offloaded parity 63 s for 4 codes.
