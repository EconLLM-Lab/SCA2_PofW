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