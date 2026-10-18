# Workbench slice 1 audit — tensor conservation hooks

Card: `t_f53c6218` (engineer desk). Parent: `t_2a139968` (RED tests + spec).
Child: `t_b0a47d75` (verifier, re-runs the acceptance command).
Root: `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.worktrees/adapter-brain-vizualization`
Date measured: 2026-10-16 (America/Phoenix, UTC-07:00), host `Augustos-MacBook-Pro.local`.

Scope: implement the frozen hook API so `workbench/tests/test_conservation.py`
passes. No frontend, no model download, no Rust, no Colab.

## 0. Deliverables

| path | what |
| --- | --- |
| `workbench/src/sca2_workbench/hooks.py` | the four frozen hooks |
| `workbench/src/sca2_workbench/__init__.py` | re-exports for later slices |
| `workbench/pyproject.toml` | uv project: `sca2_workbench` (src layout), torch, pytest |
| `workbench/.gitignore` | ignores `.venv/`, caches, build artifacts |
| `workbench/AUDIT.md` | this file |
| `workbench/uv.lock` | resolved lockfile (not ignored; reproducibility asset) |

Not deliverables: `workbench/.venv/` (untracked, ignored), `workbench/.pytest_cache/`,
`workbench/tests/__pycache__/`.

## 1. Host measurements

Raw command output from this host during this run — not a copy of the PM notes.
Commands were run from the card ROOT.

| probe | command | measured |
| --- | --- | --- |
| architecture | `uname -m` | `arm64` |
| memory | `sysctl -n hw.memsize` | `25769803776` bytes (24 GiB) |
| CPU | `sysctl -n machdep.cpu.brand_string` | `Apple M4 Pro` |
| OS | `sw_vers` | `macOS 26.6.2`, build `25G83` |
| Rust | `command -v rustc` | not found (no rustc on PATH) |
| Node | `node --version` | `v22.22.3` (`/Users/bonorinoa/.local/bin/node`) |
| Python (system) | `python3 --version` | `Python 3.9.6` (`/usr/bin/python3`) |
| uv | `uv --version` | `uv 0.10.7 (08ab1a344 2026-02-27)` (`/Users/bonorinoa/.local/bin/uv`) |
| torch (project venv) | `python -c "import torch; print(torch.__version__)"` | `2.14.1` |
| torch MPS backend | `torch.backends.mps.is_built()`, `is_available()` | `True`, `True` |
| mlx | throwaway uv env, Python 3.12 | importable, `mlx` 0.32.4, `default_device() = Device(gpu, 0)` |

The PM's numbers reproduce here: `arm64`, `Apple M4 Pro`, `25769803776` bytes,
no `rustc`, `node v22.22.3`, `python3 3.9.6`, `uv 0.10.7`. I add macOS 26.6.2 /
build 25G83, which the PM did not record.

Facts that matter for later cards:

- `rustc` is absent, so a 3D frontend needing a Rust toolchain is not buildable
  here without an install. This card did not install Rust.
- System `python3` is 3.9.6, too old for current torch wheels. The workbench pins
  its own range (`requires-python >=3.11,<3.14`) and uv resolved CPython 3.12.12
  for `workbench/.venv` instead of using `/usr/bin/python3`.
- MLX is importable and binds the Apple GPU, but it is **not** installed in the
  project venv — measured in a throwaway env on purpose, so that a Metal
  dependency never sits in the acceptance path.
- `torch` warns `Failed to initialize NumPy: No module named 'numpy'`. numpy is
  not a dependency of this slice and the hooks never need it (they use
  `.tolist()`, not `.numpy()`). If a later slice wants tensor↔numpy interop it
  must add numpy explicitly.

## 2. What was implemented

`workbench/src/sca2_workbench/hooks.py` implements the four frozen functions with
the signatures pinned in `workbench/spec/conservation.md`:

| function | returns |
| --- | --- |
| `residual_inf_norm(h0, attn_sum, mlp_sum, h_final)` | `max_i abs(h_final_i - (h0_i + attn_sum_i + mlp_sum_i))` |
| `dla_abs_gap(logit_margin, attr_sum)` | `abs(logit_margin - attr_sum)` |
| `swiglu_poles(x, w_gate, w_up)` | `dict(g_tilde, u, c, quadrant_iii)` |
| `clamp_quadrant_iii(g_tilde, u, eps=0.05)` | clamped `c_i` |

Equations as specified: `c_i = SiLU(g_tilde_i) * u_i` with
`g_tilde_i = x . w_gate[:, i]`, `u_i = x . w_up[:, i]`; quadrant III is
`g_tilde_i < -0.05 and u_i < -0.05`; the clamp sets those products to `0`.
`swiglu_poles` returns the *pre-clamp* product on purpose — the RED fixture
(neuron 1, `c_1 = 0.42683285859810105 > 0`) only makes sense as a positive
product before the clamp, and
`test_quadrant_iii_neuron_product_is_positive_before_clamp` asserts exactly that.

`workbench/src/sca2_workbench/__init__.py` re-exports the four hooks so later
slices can `from sca2_workbench import ...`.

## 3. Implementation decisions

1. **Hooks are framework-free (stdlib `math` only).** The card allows torch or
   numpy; neither is needed to satisfy the contract, and a pure-Python body is
   the smallest auditable change. Framework inputs still work: every entry point
   normalises through `tolist()`, so lists, tuples, numpy arrays and torch
   tensors (CPU or MPS) are accepted. torch is still installed in the venv
   because this card must *measure* MPS availability (§1).
2. **Numerically safe SiLU.** `z / (1 + exp(-z))` overflows for `z < -709`; the
   implementation splits at `z = 0` and uses `z * exp(z) / (1 + exp(z))` for
   negative `z`. The `z >= 0` branch is the very expression the fixture uses, and
   the negative branch agrees with the test's `_silu` well inside its 1e-6
   relative tolerance. Crash avoidance, not a tolerance change.
3. **Shape errors raise `ValueError` naming the offending lengths.** The contract
   only pins the happy path; silently broadcasting mismatched vectors would hide
   a real bug in a later slice that feeds model activations.
4. **Known limit, flagged not fixed.** `swiglu_poles` computes column dot
   products in Python loops, i.e. `O(n_features * n_neurons)`. Fine for fixtures
   and residual-stream-width vectors, but an 8B-class MLP layer
   (`n_neurons` in the tens of thousands) will be slow in pure Python. A later
   card that feeds real activations should vectorise *inside these same
   signatures*; this card deliberately did not, because the contract is the
   fixtures and the vectorised version is the larger change.

## 4. Environment finding: hidden `.pth` files break the editable install

This cost real time and will hit the verifier or a later card, so it is recorded
in full.

`uv run --project workbench pytest ...` first failed with
`ModuleNotFoundError: No module named 'sca2_workbench'` **even though uv reported
`Installed 1 package` for `sca2-workbench`**. Root cause, in order of evidence:

1. `ls -lO workbench/.venv/lib/python3.12/site-packages/*.pth` showed the macOS
   `hidden` flag on `_editable_impl_sca2_workbench.pth` and `_virtualenv.pth`;
   `os.lstat(...).st_flags == 32832`, i.e. `UF_HIDDEN` set.
2. CPython 3.12's `site.py` (`addpackage`, lines 176-179 of this build) skips
   hidden `.pth` files outright. A verbose interpreter start confirms it:

   ```
   $ env -u PYTHONPATH workbench/.venv/bin/python -v -c pass 2>&1 | grep hidden
   Skipping hidden .pth file: '.../workbench/.venv/lib/python3.12/site-packages/_editable_impl_sca2_workbench.pth'
   Skipping hidden .pth file: '.../workbench/.venv/lib/python3.12/site-packages/_virtualenv.pth'
   ```

3. So the editable-install path entry (`.../workbench/src`) was never added to
   `sys.path` and the installed distribution was unreachable. The `.pth` content
   itself was correct (one absolute path, no trailing bytes:
   `repr(open(pth, 'rb').read())` ends in `.../workbench/src'`), and
   `os.path.exists()` on that path was `True`.

Only `.pth` files are screened, so hidden *package directories* are harmless:
`markupsafe`, `jinja2`, `sympy`, `networkx`, `torch` and `pytest` all import fine
in the venv. A fresh `uv venv` created outside this worktree produced non-hidden
`.pth` files, so this is not blanket uv behaviour — it tracks how that particular
install was materialised.

Mitigations applied (both, deliberately):

1. `[tool.pytest.ini_options] pythonpath = ["src"]` in `workbench/pyproject.toml`
   (a built-in pytest option). The acceptance run then imports
   `workbench/src/sca2_workbench/hooks.py` from source — the artifact under test —
   regardless of what the venv's `.pth` does. Verified: the module resolved to
   `.../workbench/src/sca2_workbench/hooks.py`.
2. `find workbench/.venv -name '*.pth' -exec chflags nohidden {} +` (venv-local,
   untracked). After the re-sync triggered by the pyproject edit, the reinstalled
   `.pth` was already non-hidden, and
   `uv run --project workbench python -c "import sca2_workbench"` resolved to the
   source tree, so the install path works too.

**Verifier note.** If a future `uv sync` re-creates a hidden `.pth`, the
acceptance command still passes (mitigation 1). A plain
`python -c "import sca2_workbench"` outside pytest is what would break; clear the
flag again or rely on `pythonpath`.

Environment sync command and result:

```
$ env -u PYTHONPATH uv sync --project workbench
Using CPython 3.12.12
Creating virtual environment at: workbench/.venv
Resolved 37 packages in 430ms
...
 + pytest==9.1.1
 + sca2-workbench==0.1.0 (editable)
 + torch==2.14.1
EXIT=0
```

Interpreter: `workbench/.venv/bin/python` → `Python 3.12.12`.

## 5. Acceptance run

Command, exactly as the card specifies, run from the card ROOT, **no pipe**; the
exit code below is the shell's own `$?` for that command, not a pipeline's:

```
env -u PYTHONPATH uv run --project workbench pytest workbench/tests/test_conservation.py
```

Captured output:

```
============================= test session starts ==============================
platform darwin -- Python 3.12.12, pytest-9.1.1, pluggy-1.7.0
rootdir: /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.worktrees/adapter-brain-vizualization/workbench
configfile: pyproject.toml
collected 8 items

workbench/tests/test_conservation.py ........                            [100%]

============================== 8 passed in 0.01s ===============================
EXIT=0
```

**pytest exit code: 0** (8 collected, 8 passed, 0 failed, 0 errors).

## 6. RED evidence carried over from the parent (not my run)

The parent recorded the expected RED: `ModuleNotFoundError: No module named
'sca2_workbench'` at `workbench/tests/test_conservation.py:18`, exit 2. The
parent wrote those files inside a container, so the operator copied the
attachment bytes into the host paths before this card started. I verified the
copy is byte-identical to the parent's attachments:

```
a08750fa0c095fdff2a8a6ba5a7a01dd963762f0a23677325607b083a6675d16  workbench/tests/test_conservation.py
a08750fa0c095fdff2a8a6ba5a7a01dd963762f0a23677325607b083a6675d16  <parent attachment: test_conservation.py>
d3c288310aa7d43056995aa126e6cb159ced394d1ef379cbc7f4c13fb7cb5073  workbench/spec/conservation.md
d3c288310aa7d43056995aa126e6cb159ced394d1ef379cbc7f4c13fb7cb5073  <parent attachment: conservation.md>
```

Both host paths still hash to exactly those values after my work: I did not edit
`workbench/tests/` or `workbench/spec/`, and no tolerance was changed
(`TOL_RESIDUAL = 1e-3`, `TOL_DLA = 1e-2`, `EPS = 0.05` are untouched).

## 7. Fence and locks

- Touched: `workbench/src/**`, `workbench/pyproject.toml`, `workbench/.gitignore`,
  `workbench/AUDIT.md` (plus untracked `workbench/.venv/`, `workbench/uv.lock`,
  `.pytest_cache/`, `__pycache__/`).
- Not touched: `workbench/tests/`, `workbench/spec/`, `workbench/design/`,
  `workbench/ASSET_TRIAGE.md`, `paper_b`, `data`, `analysis`, `protocols`,
  `replication`, `DPO_eval_WVS`, `DPO_train_test`, `sca2`, `planning`, `runs`.
  `git status --porcelain` reports only `?? workbench/`; `git diff --stat` on
  tracked files is empty.
- No commit, push, tag or publish. No `git checkout` / `git switch` / `git reset`.
- No Llama weights or adapters downloaded, no cached 8B model loaded, nothing
  uploaded to Colab, no WebSocket server started, no 3D view written, no Rust
  installed, no 3D frontend stack chosen, no colab CLI run.
- `data/` stayed untouched and local; this card did not read it.
- `.venv` is not tracked: `git check-ignore -v workbench/.venv` →
  `workbench/.gitignore:2:.venv/`.

## 8. Route

Session `20261016_211009_ef9b23`, from
`~/.hermes/profiles/engineer/logs/agent.log`:

```
2026-10-16 21:10:10,541 INFO [20261016_211009_ef9b23] agent.turn_context: conversation turn:
  session=20261016_211009_ef9b23 model=deepseek/deepseek-v4.1-flash provider=openrouter platform=cli
  history=0 msg='work kanban task t_f53c6218'

2026-10-16 21:13:34,425 INFO [20261016_211009_ef9b23] agent.conversation_loop: API call #21:
  model=deepseek/deepseek-v4.1-flash provider=openrouter in=83669 out=1046 total=84715
  latency=3.2s cache=81152/83669 (97%) id=gen-1792210411-9rmLl9wMWXez7Mk0uP6z upstream=BaseTen
```

So this card ran on **model `deepseek/deepseek-v4.1-flash`, provider
`openrouter`** (not a `:free` model), which is the route the operator pinned in
the card comment. The card's LOCKS note that the live default on 2026-10-16 was
`grok-4.7 / xai-oauth` describes that live *default* session, not this desk's run;
I did not change the route, and the `nous` fallback was not needed.

## 9. What a later card should pick up

1. Vectorise `swiglu_poles` in place if real 8B activations are fed through it
   (§3.4).
2. If tensor↔numpy interop is wanted, add numpy to `workbench/pyproject.toml` (§1).
3. Pick the 3D frontend stack — still unowned, and Rust is not installed (§1).
4. Re-check the hidden-`.pth` quirk after any fresh `uv sync` (§4).

## 10. Slice 3: two tiny models and the 3D views (2026-10-16)

**Models.** Four models are loaded locally from the HF cache, all with the Llama architecture: 30 layers, 9 query / 3 KV heads, d_ffn 1536.
- `SmolLM2-135M` (pretrained base)
- `SmolLM2-135M-Instruct`
- `Instruct + USA DPO LoRA`, in two versions: `usa_e1` (the paper recipe: r16/α32 on q,k,v,o, β 0.1, lr 1e-4) and `usa_e3` (3 epochs)

The adapters were trained on MPS by card `t_d20f712f` with a hand-written DPO loss and a 90/10 split; they live in `models/`. On the 66 held-out pairs, the mean of log p(chosen) − log p(rejected) is −8.95 for the base, −5.09 for e1 and +11.76 for e3.

**Core.** `llama_capture.py` runs an exact float64 decomposition. `export.py` writes exports that follow the contract in `spec/export_contract.md`. With HF's three float32 casts removed (RMSNorm, RoPE, eager softmax), HF and our pass agree to about 5e-15 relative. Stock HF differs by about 1e-6 relative, which is float32 round-off. Over all 22 runs:
- residual closure ≤ 1.3e-11
- DLA gap ≤ 4e-14, in both the normal and the clamped pass
- Eq. 6 at the readout position matches the full teacher-forced Eq. 6 to ≤ 3e-7

**Trap found.** With a float64 base model, peft 0.21.2's `PeftModel.from_pretrained` silently loads LoRA B as zero, which makes the fine-tune identical to the base. `load_hf` now sets the state dict explicitly and checks every tensor against the file. A test asserts merged dW == (α/r)·B·A to 1e-12 and that the MLP weights are untouched.

**Viewer.** `viewer/` (Vite + three.js + TS) has two views: an individual network, and side by side with either B or ‖B − A‖. One camera serves both panels, and the URL holds the full state. Each mark is a slice of an exported array. The conservation bar repeats the Python checks and adds one float32 re-sum in the browser.

**Checks.**
- The 20 workbench tests pass.
- Verifier card `t_aa85d9eb` (DeepSeek, a different model family from the producer) returned ACCEPT on all six items. It used its own `.bin` reader over all 22 runs and 16 pairs, probed each patch, and ran a negative adapter-load test.
- Creative card `t_7649c031` made presentation-only changes. The PM confirmed that every height and colour binding is unchanged.

**Not built.** View 2 (2D phase plane), View 3 (country overlap curve), View 4 (live steering) and live clamp re-runs.

**Cleanup.** Delete `.venv` (761 MB), `viewer/node_modules` (93 MB), `exports/` (141 MB) and `models/` (14 MB). The HF cache entries for `HuggingFaceTB/SmolLM2-135M` and `-Instruct` are outside the repo.

## 11. v2 triage and the adapter-guard gap (2026-10-17)

- Engineer card `t_491d9eba` (Sonnet) wrote `plans/engineer_triage.md`; scripts and raw outputs are in `plans/scripts/`. The PM re-checked four claims against the code and raw outputs: the llama3 RoPE refusal (`llama_capture.py:68`), the adapter-guard probe, the option-order result and the fence (no edits to `src/`, `tests/` or `viewer/`). All four hold.
- **Guard gap closed.** `load_hf` accepted an adapter missing a whole layer (only a peft `UserWarning`; layer 29 then differed by 8.9e-4) and never compared `base_model_name_or_path`. It now refuses missing `lora_` keys, a base mismatch, `bias != "none"` and `modules_to_save`. The test `test_damaged_adapters_are_refused` covers the four defects with damaged copies of `usa_e1`. 24 tests pass. The existing e1/e3 exports are unaffected: both adapters are complete, and the verifier had already compared every tensor with its file.


## 12. Workbench v2 exporter: prompt segments and B − A attributions (2026-10-17, card `t_aa4ef15a`)

**Contract:** `sca2-workbench/capture@1` → `@1.1`, additive only (`spec/export_contract.md`, "Changes from @1").

**What changed.**
- `src/sca2_workbench/items.py`: `Item.parts` (the user prompt as `(kind, label, text)` parts), `survey_prompt_parts`, `prompt_segments`, `check_segments`. `survey_prompt_v1` is now the concatenation of the parts. The text is unchanged: the prompt hashes below are identical to the old manifests.
- `src/sca2_workbench/export.py`: `segments` in each run manifest; `d_attribution_gate`; pair arrays `d_head_attr`, `d_mlp_attr`, `d_attn_attr`, `d_head_attr_clamped`, `d_mlp_attr_clamped`; pair manifest `d_embed_attr`, `d_embed_attr_clamped`, `d_margin_clamped`, `conservation`. The exporter raises before it writes a pair whose gate fails.
- `tests/test_export_v11.py` (14 new tests). `spec/export_contract.md`. This section.
- Not touched: `viewer/**`, `design/**`, `data/`, existing array semantics and gates. No commit. (`workbench/` is entirely untracked in git, so there is no diff to show.)

**How segments are derived.** The chat template inserts the user prompt verbatim, so its character span is an exact `str.find`. Inside it the spans come from `Item.parts`. The template's own `<|im_start|>system\n…<|im_end|>` gives the system turn. Characters map to tokens through the tokenizer's offset mapping. A token that straddles a span edge raises, and none did. The completion prefix `Ġ` is not in the formatted text; it is the `readout` segment, and t* is its only token.

**Premise check.** Every kind exists for both item families, so no kind was dropped. Two points the card did not state:
- The SmolLM2 template inserts a default system prompt (16 tokens, "You are a helpful AI assistant named SmolLM …"), so `system` is real for every item, but it is the template's text and not the survey's.
- `attn_attr_clamped` is not a run array, so there is no `d_attn_attr_clamped`.

**Commands and outputs.** All run from `workbench/`; `P = env -u PYTHONPATH PYTHONPATH=src uv run --project .`

Baseline before the change: `P python -m pytest tests -q` → `24 passed`, exit 0. The old exports were copied to `$TMPDIR/exports_old/` (77 files).

After the change, `P python -m pytest tests -q -p no:warnings`, exit 0:
```
38 passed in 6.95s
```

Re-export (exit codes are the shell's `$?` of each command, written to a log, not through a pipe):
```
P python -m sca2_workbench.export --pair smol_base smol_inst
P python -m sca2_workbench.export --pair smol_inst smol_inst_usa_e1 --items wvs_Q57 wvs_Q43 wvs_Q81 bank_USA_00023ac74dac bank_USA_7232414df567 bank_USA_f48d3d37c50e
P python -m sca2_workbench.export --pair smol_inst smol_inst_usa_e3 --items (the same six)
wvs_Q57: A pass=True B pass=True margin +1.229 -> +0.755
wvs_Q43: A pass=True B pass=True margin +2.302 -> +0.039
wvs_Q81: A pass=True B pass=True margin +2.508 -> +1.059
bank_USA_00023ac74dac: A pass=True B pass=True margin +0.733 -> +1.075
exit1=0
wvs_Q57: A pass=True B pass=True margin +0.755 -> +0.938
wvs_Q43: A pass=True B pass=True margin +0.039 -> +0.126
wvs_Q81: A pass=True B pass=True margin +1.059 -> +1.366
bank_USA_00023ac74dac: A pass=True B pass=True margin +1.075 -> +1.133
bank_USA_7232414df567: A pass=True B pass=True margin -0.986 -> -1.105
bank_USA_f48d3d37c50e: A pass=True B pass=True margin +0.776 -> +0.865
exit2=0
wvs_Q57: A pass=True B pass=True margin +0.755 -> +1.777
wvs_Q43: A pass=True B pass=True margin +0.039 -> +0.419
wvs_Q81: A pass=True B pass=True margin +1.059 -> +2.920
bank_USA_00023ac74dac: A pass=True B pass=True margin +1.075 -> +1.647
bank_USA_7232414df567: A pass=True B pass=True margin -0.986 -> -1.764
bank_USA_f48d3d37c50e: A pass=True B pass=True margin +0.776 -> +1.410
exit3=0
```

Comparison of every file listed in the old `exports/index.json` against the new one (script: `$TMPDIR/compare.py`; it also re-sums the written `.bin` files and the run manifests, independently of the exporter's own numbers). Exit 0:
```
index runs/pairs old: 22 16  new: 22 16
same file set: True
index schema: sca2-workbench/capture@1.1
runs compared: 22  pairs compared: 16
worst: {'run_closure': '1.273e-11', 'dla': '4.041e-14', 'dla_c': '4.308e-14', 'hf64': '6.142e-15', 'd_gap64': '4.569e-14', 'd_gap32': '7.431e-08', 'd_gap64c': '5.274e-14', 'd_gap32c': '7.238e-08', 'margin_diff': '0.000e+00', 'dmargin_diff': '0.000e+00', 'maxdiff_arr': '1.006e-07'}
problems: []
```
Reading it: all 22 runs and 16 pairs were rewritten, with the same file set. Every margin and `d_margin` is bit-identical. Every `@1` array is byte-identical (same offset, shape and bytes). Token ids, prompt hashes, probabilities and the old conservation numbers are unchanged. The worst new gap is 7.4e-8 against a 1e-6 threshold (float32 sums), and 4.6e-14 in float64. `maxdiff_arr` is the largest difference between the stored `d_head_attr` / `d_attn_attr` and the float32 difference of the two stored run arrays, 1.0e-7, which is float32 round-off.

**Hand check, bank_USA_00023ac74dac** (T = 306, t* = 305): `question` = `[55, 147)`, 92 tokens, label `scenario`. It starts with `Question:\nA fellow student tutored me for free` and ends with `performance.\n\n`. `options` = `[158, 283)`. The browser heuristic left that 92-token paragraph collapsed.

**Open.**
- The viewer and `design/layout-v2/common.js` still use the old heuristic and the browser B − A. Creative's port should read `segments` and `d_*_attr`, and tolerate their absence in `@1` files.
- `prompt_segments` assumes the ChatML turn markers of the four SmolLM2 models. Another template with a different system block would need its own span rule. It raises when the user prompt is not found exactly once; the ChatML system-turn regex finds nothing in that case and the span falls back to a single `template`.
- Ad-hoc items built without `parts` (for example the proofs of concept in `plans/scripts/`) export `segments: null`.
- Route: this card ran on model `claude-sonnet-5-5`, provider `anthropic`.

## 13. v2 port and independent check (2026-10-17)

- **Cards:** writer `t_c6d0a437` produced COPY.md (the PM corrected two glosses: float64 is binary, not decimal; the adapter was trained on synthetic GPS-sign scenarios, not on survey answers). Creative `t_0fc4d4f8` ported the landing page plus tabs C (default), B and A into `viewer/src`; the PM finished its screenshots and probe after creative hit its 60-step budget.
- **Verifier `t_ebb2173c`** (DeepSeek, a different model family from all three producers): **ACCEPT, no blockers.** It re-derived results with its own reader. Tests: 38 pass. The segments cover [0,T) in 22/22 runs. The d_*_attr gate holds to ≤7.4e-8. Across the re-export, 536 arrays are byte-identical, and 3 runs were recomputed. Bindings were checked by hover in all three tabs. Collapsed attention is declared on screen, not dropped. tsc exits 0. The leak check is flat over 40 and 80 rebuilds. The sweep made 64 loads with 0 console errors. Every copy ruling holds.
- **One PM issue refuted:** the ladder inspector does separate ‖B−A‖ (gold, with a footnote) from signed B−A. The PM accepts this; an in-cell "‖Δ‖" prefix is optional polish.
- **Fix-later items** go to polish card `t_20471cca`. The verifier's findings are in `plans/verify/FINDINGS.md`.
- **Routing:** `agent.max_turns` for the verifier was raised from 60 to 120 after a run exhausted its budget. The backup is in `~/.hermes/config-backups/2026-10-16-viz-reroute/`.

## 14. float32 relative gates: the global closure gate is blind to small corruptions (2026-10-17, PM)

`t_1547e1a8` added `gates.py` (|error|/scale <= tau, tau = 10x the measured f32-vs-f64 maximum)
and a drop-one-head demo, which the gates catch (218x over tau in float32). The PM's independent
test was different: an in-memory copy of `run()` stores `m*1.001` for a single layer while the
stream keeps `m`. On SmolLM2-135M-Instruct (Q57, Q81) the float32 residual-closure gate catches it
only at the largest-write layer (L11, 58.6x tau). It passes at the median (L21, 0.1x) and smallest
(L5, 0.0x) layers. Float64 catches every case (1e7x tau or more). The readout gate never moves,
because DLA uses the in-loop write.

Cause: the scale is the global inf-norm of h^L (4429). One massive-activation feature on
position 0 sets it, so tau_f32 = 1e-4 allows 0.44 in absolute terms. Fix, routed to
`t_7d7ad93e`: a per-layer, per-position step-closure gate,
||h^l_t - h^{l-1}_t - a^l_t - m^l_t||_inf / max(||h^l_t||_inf, 1) <= tau_step, plus a pinned test
in which a 0.1% corruption at the median layer fails it by more than 10x. The verifier
(`t_7bb9787f`) re-tests with its own corruption and may block.

## 15. streamed Llama-3.1-8B capture and first Paper B adapter pair (2026-10-17)

- **Artifacts:** `stream_capture.py` streams one decoder layer at a time; `offload_hf.py` provides an independent HF reference with one resident block; `stream_export.py` writes capture@1.1. The official bf16 weights are upcast to float32/64. The USA LoRA stays unmerged and is applied as `(alpha/r) B(Ax)`.
- **Exactness:** on SmolLM2-135M, streamed vs in-memory float64 is bit-identical for the residual and at most 2.3e-14 relative for every other exported array. On real 8B layers 0 and 15, unmerged vs explicitly merged LoRA is at most 1.7e-14.
- **Relative gates:** the step-closure fix from §14 catches an independent 0.1% attention-write corruption at a nonzero token position by 13.7x tau in float32. On 8B, 0.1% MLP corruptions at L15/L21 fail by 72x/113x; a clean pass uses 0.033x tau.
- **Paper B parity:** the streamed USA pair matches the current `score_cohort.sequence_logprob` path to 4.33e-6 in probability (tau 1e-4). The archived 2026-10-11 Q81 scores do **not** reproduce: the USA max probability gap is 0.305 and the base row also differs, while adapter bytes match. This is escalated as a Paper B pipeline-provenance issue; it is not resolved or hidden by the workbench.
- **Verifier `t_7bb9787f`: ACCEPT, no block.** DeepSeek independently re-derived RoPE, gate calibration, streamed exactness, unmerged LoRA parity, Paper B parity, export shapes and two independent corruptions. Evidence: `plans/verify/FINDINGS_stage1.md`.
- **Final PM review:** 105 tests pass, 3 gated Llama-3.2 fixture checks skip; TypeScript passes; the browser sweep loads 90 views with zero errors; the WebGL check stays flat at 10 geometries / 76 textures over 80 steps. `SafetensorsSource.drop_handles()` runs after embedding lookup, each streamed layer and chunked unembedding, with a regression test, reducing the demonstrated reference-path RSS from 16.6 GB to 4.14 GB and bounding the main capture's mapped pages too. A fresh code/security review found no tensor or gate errors; its stale-index credential warning was resolved by confirming the staged downloader accepts only an environment-provided token. Its valid pair-manifest finding was fixed by giving all four pair-attribution gates the canonical `conservation.relative.checks` shape, which the viewer now renders rather than silently falling back to one legacy absolute row.
