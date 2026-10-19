# Conservation spec (Workbench slice 1)

Status: historical (slice 1). It was RED when written; the hooks were then implemented and the tests pass.
**Current ground truth for every gate is `spec/export_contract.md` (capture@1.1).**

Artifacts:
- `workbench/spec/conservation.md` (this file)
- `workbench/tests/test_conservation.py`

## Frozen API

Module: `workbench/src/sca2_workbench/hooks.py`

| function | signature | returns |
| --- | --- | --- |
| `residual_inf_norm` | `(h0, attn_sum, mlp_sum, h_final)` | `float` |
| `dla_abs_gap` | `(logit_margin, attr_sum)` | `float` |
| `swiglu_poles` | `(x, w_gate, w_up)` | `dict` with keys `g_tilde`, `u`, `c`, `quadrant_iii` |
| `clamp_quadrant_iii` | `(g_tilde, u, eps=0.05)` | clamped products |

## Equations

- Residual: `inf_norm(h_final - (h0 + attn_sum + mlp_sum)) < 1e-3`.
- DLA: `abs(logit_margin - attr_sum) < 1e-2`.
- SwiGLU: `c_i = SiLU(x W_gate[:, i]) * (x W_up[:, i])`.
  Quadrant III is `g_tilde_i < -0.05 and u_i < -0.05`; the clamp sets those
  products to `0`.

Convention used by the fixtures: `x` is shape `(n_features,)`; `w_gate` and
`w_up` are `(n_features, n_neurons)` so column `i` is neuron `i`.

## Hand-computed fixture (one neuron in quadrant III)

```
x      = [1.0, 1.0]
W_gate = [[1.0, -1.0], [0.0, -2.0]]
W_up   = [[1.0, -2.0], [1.0, -1.0]]

g_tilde_0 = 1*1 + 1*0   =  1.0    u_0 = 1*1 + 1*1    =  2.0
g_tilde_1 = 1*-1 + 1*-2 = -3.0    u_1 = 1*-2 + 1*-1  = -3.0

c_0 = SiLU(1.0)  *  2.0 =  1.4621171572600098
c_1 = SiLU(-3.0) * -3.0 =  0.42683285859810105   (> 0 before the clamp)

quadrant_iii = [False, True]
clamped c    = [1.4621171572600098, 0.0]           (neuron 1 -> 0)
```

`SiLU(z) = z / (1 + exp(-z))`, computed with the standard library only.

## RED evidence

Executed with no pipe.

Command (acceptance command as written in the card):

```
env -u PYTHONPATH uv run pytest workbench/tests/test_conservation.py
```

Captured output and exit code:

```
error: Failed to spawn: `pytest`
  Caused by: No such file or directory (os error 2)
EXIT=2
```

The container has no project `pyproject.toml`, so `uv run` has no environment
carrying `pytest`. The card's mid-run ruling allows installing it ad hoc. Re-run
with pytest supplied (still no pipe):

```
env -u PYTHONPATH uv run --with pytest pytest workbench/tests/test_conservation.py
```

Captured output and exit code:

```
==================================== ERRORS ====================================
____________ ERROR collecting workbench/tests/test_conservation.py _____________
ImportError while importing test module '/workspace/workbench/tests/test_conservation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
workbench/tests/test_conservation.py:18: in <module>
    from sca2_workbench.hooks import (
E   ModuleNotFoundError: No module named 'sca2_workbench'
=========================== short test summary info ============================
ERROR workbench/tests/test_conservation.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
=============================== 1 error in 0.05s ===============================
EXIT=2
```

Exact failure line (also the reason the run is RED):

```
E   ModuleNotFoundError: No module named 'sca2_workbench'
```

Raised at `workbench/tests/test_conservation.py:18`,
`from sca2_workbench.hooks import (`.

### Route

Model: `deepseek/deepseek-v4.1-flash` on provider `openrouter` (the
`model_override` / `provider_override` pinned on this card).

## Archive-parity report: distinct from conservation

For cohort captures, archive parity uses full completion logprobs, not a
probability tolerance. Per A2 F5, report each option's absolute logprob gap in
nats and in archived-fp16 ulps, with report-only tau ≤4 ulp. One ulp is positive
binary16 spacing at the absolute archived logprob. Probability gaps are
descriptive columns only. The `archive_parity` block stays outside the fatal
`conservation.relative` verdict; internal conservation and independent HF
reference checks are not relaxed. See `export_contract.md` for exact field names
and full shared-prefix completion scoring.

## float32 relative gates

Each conservation check is stated as `|error| / scale <= tau`, with `tau` supplied per model (`gates.py`). An absolute threshold cannot be kept across dtypes: on SmolLM2-135M one float32 ulp of the largest residual entry (about 8.9e2 on the base model) is 1.1e-4, so the original absolute closure bound of 1e-3 is about nine ulps wide and sits at the representation error of the stream it checks.

**What each gate checks.** Residual closure: inf-norm of `h^L - (h^0 + sum a + sum m)`, over the inf-norm of `h^L` (floored at 1). Step closure: inf-norm of `h^l_t - h^{l-1}_t - a^l_t - m^l_t` at the worst layer and position, over `||h^l_t||_inf` at that point (floored at 1). Head closure: inf-norm of `a^l - sum_h o^l_h`, over the inf-norm of `a^l` (floored at 1). Readout: `|margin - attr_sum|` over `|margin| + 1`. Reference: `max|logits_ours - logits_ref|` over `max|logits_ref|` (floored at 1). Step closure exists because the global residual scale is a single massive activation (4,429 in SmolLM2-135M-Instruct). A 1.001x error in one layer's stored MLP write passes the global float32 gate at 0.11x of tau in the median layer and 0.018x in the smallest, and fails step closure at 32.2x and 21.4x. Both gates are kept: step closure catches a wrong piece, the global one catches accumulated drift.

**Reference.** The same checkpoint and prompt run in float64 by the same code (`llama_capture`), and, for the logits check, the Hugging Face float32 model. Measured on the SmolLM2-135M family (base, instruct, instruct+usa_e3) x 6 items = 18 pairs, T = 136-306, and on Llama-3.1-8B-Instruct, base model, 2 items (`wvs_Q81`, `bank_USA_00023ac74dac`), streamed one layer at a time. Llama-3.2-1B was not measured: its weights return 403 for this account, and the 3.2-1B stepping stone was dropped.

**Measured gaps and tau.** Max relative error over all pairs; x is tau over that max. Rule: tau = 10x the largest observed error, rounded up to the next power of ten, so x is at least 10.

| check | 135M f32 max | tau | x | 135M f64 max | tau | x |
|---|---|---|---|---|---|---|
| residual closure | 6.23e-06 | 1e-4 | 16 | 5.45e-15 | 1e-13 | 18 |
| step closure | 2.85e-07 | 1e-5 | 35 | 1.95e-15 | 1e-13 | 51 |
| head closure | 0 (1.80e-07)* | 1e-5 | 56 | 0 (9.1e-17)* | 1e-15 | 11 |
| readout | 2.28e-05 | 1e-3 | 44 | 2.13e-14 | 1e-12 | 47 |
| reference | 4.44e-06 | 1e-4 | 23 | 6.14e-15 | 1e-13 | 16 |

* Head closure compares one sum with itself and is exactly 0; the value in brackets is the same identity summed in float64, used as the measured error.

Llama-3.1-8B-Instruct (2 items, so a floor and not a population estimate):

| check | f32 max | tau | x | f64 max | tau | x |
|---|---|---|---|---|---|---|
| residual closure | 3.57e-06 | 1e-4 | 28 | 2.74e-15 | 1e-13 | 36 |
| step closure | 3.83e-07 | 1e-5 | 26 | 6.37e-16 | 1e-14 | 16 |
| head closure | 0 | 1e-5 | n/a | 0 | 1e-15 | n/a |
| readout | 1.16e-06 | 1e-4 | 86 | 4.32e-15 | 1e-13 | 23 |
| reference | 2.64e-06 | 1e-4 | 38 | 3.01e-06 | 1e-4 | 33 |

The 8B head-closure taus are the 135M values (measured 0). The f64 reference tau is bounded by the float32 Hugging Face model, not by our float64 arithmetic. The 8B taus are recorded in `plans/stage1_8b_gaps.json` and each export manifest, not in `gates.TAUS_*`. Per layer, the 135M float32 residual closure runs from 1.2e-08 (layer 12) to 2.3e-07 (layer 29). Across the two 8B prompts, float32 residual closure runs from 0 to 3.57e-06 and step closure from 9.27e-09 to 1.73e-07; neither series has an isolated failing layer.

**Why tau separates rounding from bugs.** Rounding stays below tau by 11x to 86x in the tables above; the bugs tested sit far above it. Dropping the largest head write (L23H3 in smol_base, L29H1 in smol_inst) from the stored attention slice while the stream keeps it fails residual closure at 218x tau in float32 and 2.18e+11x in float64, and readout at 361x and 3.61e+11x. Head closure does not catch it (0.004x float32, 0.091x float64), because both stored pieces lose the same head and still agree. Scaling one stored MLP write by 1.001x fails step closure at 21.4x to 99.8x in float32 and 2.1e9x to 1e10x in float64. Clean captures pass step closure at 0.023x (float32) and 0.003x (float64) of tau. On Llama-3.1-8B, independent streamed tests scaled the L15 and L21 MLP writes by 1.001: the clean float32 pass used 0.033x of the step tau, while the corruptions used 72x and 113x and failed. The margin is two to three orders of magnitude in float32; the 10x multiple is a judgement, not a law. CUDA float32 passes must disable TF32 (`allow_tf32 = False` for matmul and cudnn), which would otherwise void every float32 tau.
