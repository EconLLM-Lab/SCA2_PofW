"""Layer-by-layer capture of a Llama-architecture model that never holds the model.

``llama_capture.run`` needs every weight in memory (float64 Llama-3.1-8B is 64 GB). This module
computes the same pass with one decoder layer resident at a time:

    for layer l:  read its bf16 tensors from the safetensors file  ->  upcast (exact)
                  ->  attention + MLP over all T positions  ->  summaries  ->  drop the layer

What is kept between layers: the residual stream (T x d) and the per-layer summaries the
capture@1.1 contract needs. What is never built: the embedding table (only the T prompt rows
are read), the unembedding (only the code rows, plus an optional chunked pass over the
vocabulary for the full last-position logits).

The arithmetic of a layer is ``llama_capture.run``'s, line for line (``_layer`` below). The one
algebraic reordering is the readout direction. ``run`` freezes the final RMS scale
``rho`` first and builds ``w = gamma (W_U[j+] - W_U[j-]) / rho``. ``rho`` is only known after the
last layer, so here the DLA terms are dotted with ``w_unit = gamma (W_U[j+] - W_U[j-])`` while the
layers stream, and divided by ``rho`` at the end. ``attr = (x . w_unit) / rho`` is the same number
as ``x . (w_unit / rho)`` up to one rounding; ``tests/test_stream_capture.py`` pins the agreement.

Unlike ``run``, the closure is checked after every layer: ``h^l - (h^0 + sum_{j<l} a^j + sum_{j<l} m^j)``
with the two sums kept separately (as ``run`` sums its stacks), so it is known per layer and is not
the loop's own recurrence replayed (which would be zero by construction).
"""

from __future__ import annotations

import json
import math
import resource
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from safetensors import safe_open

from sca2_workbench import llama_capture as LC
from sca2_workbench.gates import worst_step

TOPK = 16


def peak_rss_gb() -> float:
    """Peak resident set of this process so far, in GB (macOS reports bytes, Linux KB)."""
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw / (1 << 30) if sys.platform == "darwin" else raw / (1 << 20)


class SafetensorsSource:
    """Lazy reader of one Llama checkpoint directory (``config.json`` + ``*.safetensors``).

    Every method returns tensors in ``dtype`` (float32 or float64). The files are bf16 or
    float32; upcasting either to float32/float64 is exact. Nothing is cached.
    """

    def __init__(self, snapshot: str | Path, dtype: torch.dtype = torch.float64):
        from transformers import AutoConfig  # noqa: PLC0415

        if dtype not in (torch.float32, torch.float64):
            raise ValueError(f"only float32 and float64 passes are supported; got {dtype}")
        self.dir, self.dtype = Path(snapshot), dtype
        cfg = AutoConfig.from_pretrained(self.dir)
        if getattr(cfg, "attention_bias", False) or getattr(cfg, "mlp_bias", False):
            raise ValueError("biases are not supported (DLA closure assumes bias-free projections)")
        if cfg.hidden_act != "silu":
            raise ValueError(f"expected SiLU gating, got {cfg.hidden_act}")
        self.cfg = cfg
        self.n_layers = cfg.num_hidden_layers
        self.n_heads = cfg.num_attention_heads
        self.n_kv = cfg.num_key_value_heads
        self.d_model = cfg.hidden_size
        self.d_ffn = cfg.intermediate_size
        self.head_dim = getattr(cfg, "head_dim", None) or cfg.hidden_size // cfg.num_attention_heads
        self.rms_eps = float(cfg.rms_norm_eps)
        self.rope_theta = LC._rope_theta(cfg)
        self.rope_scaling = LC._rope_scaling(cfg)

        index = self.dir / "model.safetensors.index.json"
        if index.exists():
            self._file_of = json.loads(index.read_text())["weight_map"]
        else:
            with safe_open(self.dir / "model.safetensors", framework="pt") as f:
                self._file_of = {k: "model.safetensors" for k in f.keys()}  # noqa: SIM118
        self._handles: dict = {}
        self._unembed_name = "lm_head.weight" if "lm_head.weight" in self._file_of \
            else "model.embed_tokens.weight"       # tied embeddings: the table is shared

    def _handle(self, name: str):
        fname = self._file_of[name]
        if fname not in self._handles:
            self._handles[fname] = safe_open(self.dir / fname, framework="pt")
        return self._handles[fname]

    def drop_handles(self) -> None:
        """Close the open safetensors files (unmaps their pages; the next read reopens them)."""
        self._handles.clear()

    def _get(self, name: str) -> torch.Tensor:
        return self._handle(name).get_tensor(name).to(self.dtype)

    def _rows(self, name: str, ids) -> torch.Tensor:
        """Rows ``ids`` of a (V, d) matrix, read one row at a time."""
        sl = self._handle(name).get_slice(name)
        return torch.cat([sl[i:i + 1] for i in ids]).to(self.dtype)

    def embed_rows(self, ids) -> torch.Tensor:
        return self._rows("model.embed_tokens.weight", [int(i) for i in ids])

    def unembed_rows(self, token_ids) -> torch.Tensor:
        return self._rows(self._unembed_name, [int(i) for i in token_ids])

    def unembed_chunks(self, chunk: int = 16384):
        """The whole unembedding, ``chunk`` rows at a time (never all at once)."""
        sl = self._handle(self._unembed_name).get_slice(self._unembed_name)
        V = sl.get_shape()[0]
        for a in range(0, V, chunk):
            yield a, sl[a:min(a + chunk, V)].to(self.dtype)

    def final_norm(self) -> torch.Tensor:
        return self._get("model.norm.weight")

    def layer(self, l: int) -> dict:
        p = f"model.layers.{l}."
        names = {
            "in_norm": "input_layernorm.weight", "post_norm": "post_attention_layernorm.weight",
            "q": "self_attn.q_proj.weight", "k": "self_attn.k_proj.weight",
            "v": "self_attn.v_proj.weight", "o": "self_attn.o_proj.weight",
            "gate": "mlp.gate_proj.weight", "up": "mlp.up_proj.weight",
            "down": "mlp.down_proj.weight",
        }
        return {k: self._get(p + v) for k, v in names.items()}


#: LoRA module name in the adapter file -> key of ``SafetensorsSource.layer``.
LORA_MODULES = {"self_attn.q_proj": "q", "self_attn.k_proj": "k", "self_attn.v_proj": "v",
                "self_attn.o_proj": "o", "mlp.gate_proj": "gate", "mlp.up_proj": "up",
                "mlp.down_proj": "down"}


class LoraAdapter:
    """A peft LoRA adapter read from its safetensors file, applied UNMERGED by ``_layer``.

    ``layer(l, dtype)`` returns ``{"q": (A, B), ...}`` for the adapted projections of layer ``l``;
    the adapted projection is ``x W^T + scale * (x A^T) B^T`` with ``scale = alpha / r``. The A/B
    tensors come straight from the file (no peft model: peft 0.21.2 leaves LoRA B at zero under
    float64, AUDIT.md section 11). Guards: ``llama_capture.check_adapter`` (the ``load_hf`` set),
    plus the peft variants this formula does not implement.
    """

    #: config keys whose non-default value changes the forward pass away from scale * B A x.
    UNSUPPORTED = {"use_dora": False, "use_rslora": False, "rank_pattern": {}, "alpha_pattern": {},
                   "fan_in_fan_out": False, "layers_to_transform": None, "layer_replication": None,
                   "lora_bias": False}

    def __init__(self, adapter_dir, model_id: str):
        import hashlib  # noqa: PLC0415

        self.dir = Path(adapter_dir)
        cfg, sd = LC.check_adapter(self.dir, model_id)
        for key, default in self.UNSUPPORTED.items():
            if cfg.get(key) not in (default, None):
                raise ValueError(f"adapter {key}={cfg[key]!r} is not supported by the streamed LoRA")
        self.cfg, self.r, self.alpha = cfg, int(cfg["r"]), float(cfg["lora_alpha"])
        self.scale = self.alpha / self.r
        self._t: dict = {}                          # (layer, name) -> {"A": t, "B": t}
        for key, t in sd.items():
            parts = key.split(".")
            # base_model.model.model.layers.<l>.<self_attn|mlp>.<x_proj>.lora_<A|B>.weight
            if parts[:4] != ["base_model", "model", "model", "layers"] or parts[-1] != "weight" \
                    or parts[-2] not in ("lora_A", "lora_B"):
                raise ValueError(f"unexpected adapter tensor {key}")
            mod = ".".join(parts[5:7])
            if mod not in LORA_MODULES:
                raise ValueError(f"adapter targets {mod}, which the streamed capture does not adapt")
            self._t.setdefault((int(parts[4]), LORA_MODULES[mod]), {})[parts[-2][-1]] = t
        bad = [k for k, v in self._t.items() if set(v) != {"A", "B"}]
        if bad:
            raise ValueError(f"LoRA A/B pair incomplete for {bad[:3]}")
        self.targets = sorted({name for _, name in self._t})
        want = {t.rsplit(".", 1)[-1].replace("_proj", "") for t in cfg["target_modules"]}
        if set(self.targets) != want:
            raise ValueError(f"file adapts {self.targets}, config target_modules says {sorted(want)}")
        self.layers = sorted({l for l, _ in self._t})
        for (l, name), ab in self._t.items():
            if ab["A"].shape[0] != self.r or ab["B"].shape[1] != self.r:
                raise ValueError(f"layer {l} {name}: rank != r={self.r}")
        self.sha256 = hashlib.sha256((self.dir / "adapter_model.safetensors").read_bytes()).hexdigest()

    def layer(self, l: int, dtype: torch.dtype) -> dict:
        return {name: (ab["A"].to(dtype), ab["B"].to(dtype))
                for (ll, name), ab in self._t.items() if ll == l}

    def describe(self) -> dict:
        return {"dir": str(self.dir), "sha256": self.sha256, "r": self.r, "lora_alpha": self.alpha,
                "scale": self.scale, "target_modules": self.cfg["target_modules"],
                "base_model_name_or_path": self.cfg["base_model_name_or_path"],
                "applied": "unmerged: x W^T + (alpha/r) (x A^T) B^T, A/B read from the file"}


@dataclass
class _State:
    """One pass's running state: the stream and everything kept from the layers so far."""

    clamp: bool
    h: torch.Tensor
    sum_a: torch.Tensor            # sum of the attention writes so far
    sum_m: torch.Tensor            # sum of the MLP writes so far; closure = |h - (h^0 + sum_a + sum_m)|
    h0: torch.Tensor
    resid_t: list                  # h^l at t*, one (d,) row per layer boundary
    keep: dict
    lora: "LoraAdapter | None" = None
    track: bool = False            # keep this layer's (a, m, o) in ``cur`` for the pair diffs
    cur: tuple | None = None


def _layer(st: _State, lw: dict, cfg: "SafetensorsSource", cos, sin, causal, w_unit, topk: int,
           eps_q3: float, keep_resid: bool, layer: int = -1, scale_mlp_write=None,
           lo: dict | None = None, scale: float = 0.0) -> None:
    """One decoder layer of ``llama_capture.run`` on ``st``; summaries go into ``st.keep``.

    ``lo = {"q": (A, B), ...}`` adds a LoRA, unmerged: every adapted projection is
    ``x W^T + scale (x A^T) B^T``. Per head (o_proj) and per neuron (down_proj) the adapted write
    is still linear in that head's z / that neuron's c, so the DLA split is unchanged.
    """
    T, H, KV, hd, eps = st.h.shape[0], cfg.n_heads, cfg.n_kv, cfg.head_dim, cfg.rms_eps
    rep = H // KV
    t = T - 1
    h_prev, h, k_ = st.h, st.h, st.keep
    lo = lo or {}

    def lin(x, name):
        y = x @ lw[name].T
        if name in lo:
            A, B = lo[name]
            y = y + scale * ((x @ A.T) @ B.T)
        return y

    x = LC.rms_norm(h, lw["in_norm"], eps)
    q = lin(x, "q").view(T, H, hd).transpose(0, 1)
    k = lin(x, "k").view(T, KV, hd).transpose(0, 1)
    v = lin(x, "v").view(T, KV, hd).transpose(0, 1)
    q = q * cos + LC._rotate_half(q) * sin
    k = k * cos + LC._rotate_half(k) * sin
    k = k.repeat_interleave(rep, dim=0)
    v = v.repeat_interleave(rep, dim=0)
    scores = (q @ k.transpose(-1, -2)) / math.sqrt(hd)
    A = torch.softmax(scores.masked_fill(causal, float("-inf")), dim=-1)       # (H, T, T)
    z = A @ v
    w_o = lw["o"].view(cfg.d_model, H, hd).permute(1, 2, 0)                    # (H, hd, d)
    o = torch.einsum("htk,hkd->htd", z, w_o)                                   # (H, T, d)
    if "o" in lo:                     # head h's LoRA write: scale (z_h A[:, h]^T) B^T
        la, lb = lo["o"]                                                       # (r, H*hd), (d, r)
        a_o = la.view(la.shape[0], H, hd).permute(1, 2, 0)                     # (H, hd, r)
        o = o + scale * (torch.einsum("htk,hkr->htr", z, a_o) @ lb.T)
    a = o.sum(0)
    h = h + a

    x2 = LC.rms_norm(h, lw["post_norm"], eps)
    g = lin(x2, "gate")
    u = lin(x2, "up")
    q3 = (g < -eps_q3) & (u < -eps_q3)
    c_raw = F.silu(g) * u
    c = c_raw.masked_fill(q3, 0.0) if st.clamp else c_raw
    m = lin(c, "down")
    h = h + m
    if scale_mlp_write is not None and scale_mlp_write[0] == layer:
        m = m * scale_mlp_write[1]       # test-only corruption: stored m wrong, stream right

    # --- summaries (all in the pass dtype, exactly what ``run`` stores) ---
    st.sum_a = st.sum_a + a                # summed separately, as ``run`` does (Aout.sum(0) + Mout.sum(0)),
    st.sum_m = st.sum_m + m                # so the closure is not the loop's own recurrence replayed
    st.h = h
    st.resid_t.append(h[t].clone())
    val, idx = A.topk(min(topk, T), dim=-1)
    k_["resid_norm"].append(h.norm(dim=-1))
    k_["attn_norm"].append(a.norm(dim=-1))
    k_["mlp_norm"].append(m.norm(dim=-1))
    k_["head_norm"].append(o.norm(dim=-1))
    k_["topk_val"].append(val)
    k_["topk_idx"].append(idx)
    k_["q3_count"].append(q3.sum(-1))
    k_["q3_write_norm"].append(lin(c_raw * q3, "down").norm(dim=-1))
    k_["g_last"].append(g[t])
    k_["u_last"].append(u[t])
    k_["c_last"].append(c[t])
    k_["head_t_dot"].append(o[:, t, :] @ w_unit)                               # (H,)  x . w_unit
    down_w = lw["down"].T @ w_unit                                             # (F,)
    if "down" in lo:                  # neuron i's write direction: W_down[:, i] + scale B A[:, i]
        la, lb = lo["down"]
        down_w = down_w + scale * (la.T @ (lb.T @ w_unit))
    k_["down_w_unit"].append(down_w)
    if st.track:
        st.cur = (a, m, o)
    k_["closure"].append((h - (st.h0 + st.sum_a + st.sum_m)).abs().max().item())
    k_["step_err"].append((h - h_prev - a - m).abs().amax(-1))                  # (T,)
    k_["step_scale"].append(h.abs().amax(-1))
    k_["head_closure"].append((a - o.sum(0)).abs().max().item())
    k_["attn_scale"] = max(k_["attn_scale"], a.abs().max().item())
    if keep_resid:
        k_["_resid"].append(h.clone())


def run_streamed(src: SafetensorsSource, ids, *, j_plus: int, j_minus: int,
                 clamps: tuple = (False,), eps_q3: float = LC.EPS_Q3, topk: int = TOPK,
                 full_logits: bool = False, keep_resid: bool = False, log=None,
                 scale_mlp_write: tuple | None = None) -> list:
    """Stream ``ids`` through the model once; one output dict per entry of ``clamps``.

    ``clamps=(False, True)`` runs the plain pass and the Quadrant-III-clamped pass over the same
    layer read (each layer is read and upcast once). The returned dicts carry the keys of
    ``llama_capture.run`` that the export uses, with ``attn_topk_val/idx`` (L, H, T, k) in place
    of the full ``attn_probs``, and ``code_logits`` (the two code logits at t*).
    ``full_logits=True`` adds ``logits_last`` over the whole vocabulary by a chunked pass over
    the unembedding. ``log(str)`` is called after each layer if given. ``scale_mlp_write`` is the
    test-only corruption of ``llama_capture.run`` (the stored MLP write of one layer is scaled).
    """
    outs, _ = _stream(src, ids, [(None, c) for c in clamps], j_plus=j_plus, j_minus=j_minus,
                      eps_q3=eps_q3, topk=topk, full_logits=full_logits, keep_resid=keep_resid,
                      log=log, scale_mlp_write=scale_mlp_write)
    return outs


def run_streamed_pair(src: SafetensorsSource, ids, lora: LoraAdapter, *, j_plus: int, j_minus: int,
                      eps_q3: float = LC.EPS_Q3, topk: int = TOPK, full_logits: bool = False,
                      keep_resid: bool = False, log=None) -> dict:
    """A = the checkpoint, B = checkpoint + ``lora`` (unmerged), off ONE read of each layer.

    Four passes share every layer read: A, A clamped, B, B clamped. Returns
    ``{"a", "a_clamped", "b", "b_clamped", "diffs"}``; ``diffs`` holds the B - A norms of the
    pair contract, computed inside the loop (the (L, H, T, d) head writes are never stored):
    ``d_resid_norm`` (L+1, T), ``d_attn_norm`` / ``d_mlp_norm`` (L, T), ``d_head_norm`` (L, H, T).
    """
    specs = [(None, False), (None, True), (lora, False), (lora, True)]
    outs, diffs = _stream(src, ids, specs, j_plus=j_plus, j_minus=j_minus, eps_q3=eps_q3,
                          topk=topk, full_logits=full_logits, keep_resid=keep_resid, log=log,
                          pair=(0, 2))
    return {"a": outs[0], "a_clamped": outs[1], "b": outs[2], "b_clamped": outs[3], "diffs": diffs}


def _stream(src, ids, specs, *, j_plus, j_minus, eps_q3, topk, full_logits, keep_resid, log,
            scale_mlp_write=None, pair=None):
    """The layer loop. ``specs = [(lora or None, clamp), ...]``, one state each; ``pair = (i, j)``
    computes the B - A norms between states i (A) and j (B) after every layer."""
    ids = torch.as_tensor(ids, dtype=torch.long)
    dtype, T = src.dtype, int(ids.shape[0])
    cos, sin = LC._rope(T, src.head_dim, src.rope_theta, src.rope_scaling, dtype=dtype)
    causal = torch.triu(torch.ones(T, T, dtype=torch.bool), diagonal=1)
    final_norm = src.final_norm()
    codes = src.unembed_rows([j_plus, j_minus])                    # (2, d): the only rows needed
    w_unit = final_norm * (codes[0] - codes[1])                    # (d,)

    h0 = src.embed_rows(ids)
    # The rows above are copied out of the memory map by the dtype conversion.  Release its shard
    # before the decoder loop; otherwise touched pages accumulate across layers on macOS.
    src.drop_handles()
    keys = ("resid_norm", "attn_norm", "mlp_norm", "head_norm", "topk_val", "topk_idx", "q3_count",
            "q3_write_norm", "g_last", "u_last", "c_last", "head_t_dot", "down_w_unit",
            "closure", "head_closure", "step_err", "step_scale", "_resid")
    states = [_State(clamp=c, h=h0.clone(), sum_a=torch.zeros_like(h0), sum_m=torch.zeros_like(h0), h0=h0, resid_t=[h0[-1].clone()],
                     keep={**{k: [] for k in keys}, "attn_scale": 0.0}, lora=lo,
                     track=pair is not None and i in pair) for i, (lo, c) in enumerate(specs)]
    for st in states:
        st.keep["resid_norm"].append(h0.norm(dim=-1))
        if keep_resid:
            st.keep["_resid"].append(h0.clone())
    diffs = None
    if pair is not None:
        sa, sb = states[pair[0]], states[pair[1]]
        if sa.clamp or sb.clamp:
            raise ValueError("the pair diffs compare the unclamped passes")
        diffs = {"d_resid_norm": [(sb.h - sa.h).norm(dim=-1)], "d_attn_norm": [], "d_mlp_norm": [],
                 "d_head_norm": []}

    loras = {id(st.lora): st.lora for st in states if st.lora is not None}
    t0 = time.time()
    for l in range(src.n_layers):
        lw = src.layer(l)
        los = {k: lo.layer(l, dtype) for k, lo in loras.items()}
        for st in states:
            lo = st.lora
            _layer(st, lw, src, cos, sin, causal, w_unit, topk, eps_q3, keep_resid, l,
                   scale_mlp_write, lo=los[id(lo)] if lo is not None else None,
                   scale=lo.scale if lo is not None else 0.0)
        if diffs is not None:
            (aa, ma, oa), (ab, mb, ob) = sa.cur, sb.cur
            diffs["d_resid_norm"].append((sb.h - sa.h).norm(dim=-1))
            diffs["d_attn_norm"].append((ab - aa).norm(dim=-1))
            diffs["d_mlp_norm"].append((mb - ma).norm(dim=-1))
            diffs["d_head_norm"].append((ob - oa).norm(dim=-1))
            sa.cur = sb.cur = None
        del lw, los
        # ``safe_open`` retains each touched shard.  The upcast tensors above own their storage, so
        # closing the handles here is safe and keeps RSS bounded instead of growing ~0.25 GB/layer.
        src.drop_handles()
        if log:
            log(f"layer {l + 1:2d}/{src.n_layers}  {time.time() - t0:7.1f}s  peak RSS {peak_rss_gb():.2f} GB")

    outs = []
    for st in states:
        outs.append(_finish(src, st, ids, final_norm, codes, w_unit, j_plus, j_minus, full_logits,
                            keep_resid))
    if diffs is not None:
        diffs = {k: torch.stack(v) for k, v in diffs.items()}
    # ``full_logits`` may have reopened the unembedding shard.
    src.drop_handles()
    return outs, diffs


def unmerged_vs_merged(src, ids, layer: int, lw: dict, lo: dict, merged: dict, scale: float, *,
                       j_plus: int, j_minus: int) -> dict:
    """One decoder layer three ways on the same input (the real embedding of ``ids`` pushed
    through the BASE layers below ``layer``): base, LoRA unmerged (``lo``), LoRA merged into the
    weights (``merged``). Returns the relative gap (to max |entry|, floored at 1) of every value
    the layer keeps, unmerged vs merged, plus ``h_out (unmerged vs base)`` to show it is not 0."""
    ids = torch.as_tensor(ids, dtype=torch.long)
    T = int(ids.shape[0])
    cos, sin = LC._rope(T, src.head_dim, src.rope_theta, src.rope_scaling, dtype=src.dtype)
    causal = torch.triu(torch.ones(T, T, dtype=torch.bool), diagonal=1)
    codes = src.unembed_rows([j_plus, j_minus])
    w_unit = src.final_norm() * (codes[0] - codes[1])
    keys = ("resid_norm", "attn_norm", "mlp_norm", "head_norm", "topk_val", "topk_idx", "q3_count",
            "q3_write_norm", "g_last", "u_last", "c_last", "head_t_dot", "down_w_unit",
            "closure", "head_closure", "step_err", "step_scale", "_resid")

    def fresh(h):
        return _State(clamp=False, h=h.clone(), sum_a=torch.zeros_like(h), sum_m=torch.zeros_like(h),
                      h0=h.clone(), resid_t=[], keep={**{k: [] for k in keys}, "attn_scale": 0.0},
                      track=True)

    h = src.embed_rows(ids)
    for l in range(layer):                                      # base layers below
        st = fresh(h)
        _layer(st, src.layer(l), src, cos, sin, causal, w_unit, TOPK, LC.EPS_Q3, False)
        h = st.h
    runs = {}
    for name, (weights, lo_, s) in {"base": (lw, None, 0.0), "unmerged": (lw, lo, scale),
                                    "merged": (merged, None, 0.0)}.items():
        st = fresh(h)
        _layer(st, weights, src, cos, sin, causal, w_unit, TOPK, LC.EPS_Q3, False, layer,
               lo=lo_, scale=s)
        runs[name] = st

    def rel(a, b):
        a, b = torch.as_tensor(a).double(), torch.as_tensor(b).double()
        return ((a - b).abs().max() / max(b.abs().max().item(), 1.0)).item()

    u, m = runs["unmerged"], runs["merged"]
    gaps = {"h_out": rel(u.h, m.h), "attn_write a": rel(u.cur[0], m.cur[0]),
            "mlp_write m": rel(u.cur[1], m.cur[1]), "head_writes o": rel(u.cur[2], m.cur[2])}
    for k in ("attn_norm", "mlp_norm", "head_norm", "topk_val", "q3_write_norm", "g_last",
              "u_last", "c_last", "head_t_dot", "down_w_unit"):
        gaps[k] = rel(u.keep[k][0], m.keep[k][0])
    gaps["q3_count (exact: 0 or 1)"] = float(not torch.equal(u.keep["q3_count"][0], m.keep["q3_count"][0]))
    gaps["h_out (unmerged vs base)"] = rel(u.h, runs["base"].h)
    return gaps


def lora_weight_delta(lora: LoraAdapter, src: SafetensorsSource) -> tuple:
    """``||W^B - W^A||_F`` per (layer, head, [q,k,v,o]) and per (layer, [gate,up,down]) from the
    LoRA alone, in float64: ``W^B - W^A = s B A``, and ``||s B_rows A||_F^2 = s^2 sum((B_rows^T
    B_rows) * (A A^T))`` (rows of B for q/k/v heads, columns of A for o heads). Same layout as
    ``export._weight_delta`` / ``_mlp_weight_delta``; modules the adapter does not touch are 0."""
    L, H, hd, rep = src.n_layers, src.n_heads, src.head_dim, src.n_heads // src.n_kv
    s = lora.scale
    dh, dm = np.zeros((L, H, 4)), np.zeros((L, 3))

    def fro(Bp, Ap):                                   # ||Bp Ap||_F without forming the product
        return float(torch.sqrt(((Bp.T @ Bp) * (Ap @ Ap.T)).sum().clamp(min=0.0)))

    for l in range(L):
        lo = lora.layer(l, torch.float64)
        for j, name in enumerate(("q", "k", "v")):
            if name in lo:
                A, B = lo[name]
                for h in range(H):
                    g = h if name == "q" else h // rep
                    dh[l, h, j] = s * fro(B[g * hd:(g + 1) * hd], A)
        if "o" in lo:
            A, B = lo["o"]
            for h in range(H):
                dh[l, h, 3] = s * fro(B, A[:, h * hd:(h + 1) * hd])
        for j, name in enumerate(("gate", "up", "down")):
            if name in lo:
                A, B = lo[name]
                dm[l, j] = s * fro(B, A)
    return dh, dm


def _finish(src, st, ids, final_norm, codes, w_unit, j_plus, j_minus, full_logits, keep_resid):
    """Readout at t* and the DLA terms, from the kept summaries (see the module docstring)."""
    k, h, eps, T = st.keep, st.h, src.rms_eps, int(ids.shape[0])
    t = T - 1
    L = src.n_layers
    rho = torch.sqrt((h[t] * h[t]).mean() + eps)
    final_t = final_norm * (h[t] / torch.sqrt((h[t] * h[t]).mean() + eps))     # rms_norm of row t*
    code_logits = codes @ final_t                                              # (2,)
    margin = (code_logits[0] - code_logits[1]).item()

    R_t = torch.stack(st.resid_t)                                              # (L+1, d)
    embed_attr = (R_t[0] @ w_unit / rho).item()
    head_attr = torch.stack(k["head_t_dot"]) / rho                             # (L, H)
    c_last = torch.stack(k["c_last"])                                          # (L, F)
    neuron_attr = c_last * torch.stack(k["down_w_unit"]) / rho                 # (L, F)
    attr_sum = embed_attr + head_attr.sum().item() + neuron_attr.sum().item()

    step_err, step_scale = torch.stack(k["step_err"]), torch.stack(k["step_scale"])   # (L, T)
    step_err_inf, step_scale_inf = worst_step(step_err, step_scale)

    out = {
        "T": T,
        "dtype": str(src.dtype).replace("torch.", ""),
        "step_err_inf": step_err_inf,
        "step_scale_inf": step_scale_inf,
        "step_err_by_layer": step_err.amax(-1),
        "resid_norm": torch.stack(k["resid_norm"]),                            # (L+1, T)
        "attn_norm": torch.stack(k["attn_norm"]),
        "mlp_norm": torch.stack(k["mlp_norm"]),
        "head_norm": torch.stack(k["head_norm"]),                              # (L, H, T)
        "attn_topk_val": torch.stack(k["topk_val"]),                           # (L, H, T, k)
        "attn_topk_idx": torch.stack(k["topk_idx"]),
        "q3_count": torch.stack(k["q3_count"]),
        "q3_write_norm": torch.stack(k["q3_write_norm"]),
        "g_last": torch.stack(k["g_last"]),
        "u_last": torch.stack(k["u_last"]),
        "c_last": c_last,
        "code_logits": code_logits,
        "residual_closure_inf": k["closure"][-1],
        "residual_closure_by_layer": k["closure"],
        "residual_scale_inf": h.abs().max().item(),
        "head_closure_inf": max(k["head_closure"]),
        "attn_scale_inf": k["attn_scale"],
        "margin": margin,
        "embed_attr": embed_attr,
        "head_attr": head_attr,
        "neuron_attr": neuron_attr,
        "attn_attr": head_attr.sum(1),
        "mlp_attr": neuron_attr.sum(1),
        "running_margin": R_t @ w_unit / rho,
        "attr_sum": attr_sum,
        "dla_gap": abs(margin - attr_sum),
        "rho_final": rho.item(),
    }
    if keep_resid:
        out["_resid"] = torch.stack(k["_resid"])                               # (L+1, T, d)
    if full_logits:
        out["logits_last"] = torch.cat([final_t @ rows.T for _, rows in src.unembed_chunks()])
    return out
