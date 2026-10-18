"""Exact float64 forward pass of a Llama-architecture model, kept in pieces.

The view layer draws only quantities this module returns. Every number is a slice of a
tensor in the real forward pass of the loaded checkpoint. ``reference_check`` compares
the pass with the Hugging Face implementation of the same model.

Notation (one sequence, T tokens, L layers, H query heads, F MLP neurons, d model width):

    h^0          = E[ids]                                   embedding (residual at layer 0)
    a^l          = sum_h o^l_h,  o^l_h = softmax(q k^T/sqrt(hd) + causal) v  W_O[:, h]^T
    h^l+1/2      = h^l + a^l
    c^l_i        = SiLU(g~^l_i) * u^l_i,  g~ = RMSNorm(h^l+1/2) W_gate^T,  u = ... W_up^T
    m^l          = sum_i c^l_i W_down[:, i]
    h^l+1        = h^l+1/2 + m^l
    logits_t     = RMSNorm_final(h^L_t) W_U^T

Residual conservation: ``h^L = h^0 + sum_l a^l + sum_l m^l``. This holds by construction.
It is checked anyway, because every stored piece must add back to the stream.

DLA at the readout position t*: freeze the final RMS scale ``rho = sqrt(mean(h^L_t*^2) + eps)``.
Then ``logit(j+) - logit(j-) = h^L_t* . w`` with ``w = gamma_final * (W_U[j+] - W_U[j-]) / rho``.
That is a linear map, so it splits exactly over the embedding, every head (l, h) and every
neuron (l, i): ``attr(l, i) = c^l_i * (W_down[:, i] . w)``. All the pieces sum to the margin.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn.functional as F

from sca2_workbench.gates import worst_step

#: Quadrant III threshold (Cammarata): both poles below -EPS.
EPS_Q3 = 0.05


@dataclass(frozen=True)
class RopeScaling:
    """The RoPE frequency scaling a config asks for, restricted to what we reproduce exactly.

    ``rope_type="default"`` is the unscaled table. ``"llama3"`` is the Llama-3.x scheme: the
    low-frequency end of the table is divided by ``factor``, the middle band is blended between
    the two ends, and ``original_max_position_embeddings`` is the length the bands are measured
    against. Both types have ``attention_scaling`` 1.0 in HF, so the cos/sin are not rescaled.
    Any other type is refused by ``_rope_scaling``: the rotation would silently be the unscaled one.
    """

    rope_type: str = "default"
    factor: float = 1.0
    low_freq_factor: float = 1.0
    high_freq_factor: float = 4.0
    original_max_position_embeddings: int = 8192

    @property
    def scaled(self) -> bool:
        return self.rope_type != "default"


@dataclass
class LlamaWeights:
    embed: torch.Tensor          # (V, d)
    unembed: torch.Tensor        # (V, d)
    final_norm: torch.Tensor     # (d,)
    layers: list                 # dicts of float64 tensors, nn.Linear layout (out, in)
    n_heads: int
    n_kv: int
    head_dim: int
    rms_eps: float
    rope_theta: float
    rope_scaling: RopeScaling = RopeScaling()

    @property
    def n_layers(self) -> int:
        return len(self.layers)

    @property
    def d_model(self) -> int:
        return int(self.embed.shape[1])

    @property
    def d_ffn(self) -> int:
        return int(self.layers[0]["gate"].shape[0])


#: The ``rope_scaling`` keys the llama3 scheme needs (HF ``_compute_llama3_parameters``).
_LLAMA3_KEYS = ("factor", "low_freq_factor", "high_freq_factor", "original_max_position_embeddings")


def _rope_block(cfg) -> dict:
    """The rope dict HF reads: transformers 5.x ``rope_parameters``, else 4.x ``rope_scaling``."""
    for source in (getattr(cfg, "rope_parameters", None), getattr(cfg, "rope_scaling", None)):
        if isinstance(source, dict) and source:
            return source
    return {}


def _rope_theta(cfg) -> float:
    """The RoPE base HF reads from this config."""
    block = _rope_block(cfg)
    if "rope_theta" in block:
        return float(block["rope_theta"])
    theta = getattr(cfg, "rope_theta", None)
    if theta is None:
        raise ValueError("config carries no rope_theta")
    return float(theta)


def _rope_scaling(cfg) -> RopeScaling:
    """The frequency scaling HF applies to ``cfg``. Only what we reproduce exactly is accepted.

    A refusal here is what keeps a model with an unimplemented scheme (yarn, linear, dynamic,
    longrope) from being captured with an unscaled rotation, which would be a different model.
    """
    block = _rope_block(cfg)
    rope_type = block.get("rope_type") or getattr(cfg, "rope_type", None) or "default"
    if rope_type == "default":
        return RopeScaling()
    if rope_type != "llama3":
        raise ValueError(f"only default and llama3 RoPE are implemented; got {rope_type!r} in {block}")
    missing = [k for k in _LLAMA3_KEYS if k not in block]
    if missing:
        raise ValueError(f"llama3 RoPE needs {list(missing)}; config carries {block}")
    partial = float(block.get("partial_rotary_factor", 1.0))
    if partial != 1.0:
        raise ValueError(f"partial_rotary_factor={partial} is not implemented")
    return RopeScaling(
        rope_type="llama3",
        factor=float(block["factor"]),
        low_freq_factor=float(block["low_freq_factor"]),
        high_freq_factor=float(block["high_freq_factor"]),
        original_max_position_embeddings=int(block["original_max_position_embeddings"]),
    )


def rope_inv_freq(head_dim: int, theta: float, scaling: RopeScaling = RopeScaling(),
                  *, dtype: torch.dtype = torch.float64) -> torch.Tensor:
    """HF's inverse frequencies for ``head_dim``, built in ``dtype``.

    The base table is ``LlamaRotaryEmbedding.compute_default_rope_parameters``; the rescaling is
    ``modeling_rope_utils._compute_llama3_parameters``, branch for branch:

      * wavelength > ``original_max_position_embeddings / low_freq_factor``: divide by ``factor``;
      * wavelength < ``original_max_position_embeddings / high_freq_factor``: leave alone;
      * between the two: blend the divided and undivided values with the smooth factor.

    ``tests/test_llama3_rope.py`` checks this against HF's own module in HF's own code, so the
    branches are not a transcription on trust.
    """
    inv_freq = 1.0 / (theta ** (torch.arange(0, head_dim, 2, dtype=dtype) / head_dim))
    if not scaling.scaled:
        return inv_freq
    old_context_len = float(scaling.original_max_position_embeddings)
    low_freq_wavelen = old_context_len / scaling.low_freq_factor
    high_freq_wavelen = old_context_len / scaling.high_freq_factor

    wavelen = 2 * math.pi / inv_freq
    inv_llama = torch.where(wavelen > low_freq_wavelen, inv_freq / scaling.factor, inv_freq)
    smooth_factor = (old_context_len / wavelen - scaling.low_freq_factor) / (
        scaling.high_freq_factor - scaling.low_freq_factor)
    smoothed = (1 - smooth_factor) * inv_llama / scaling.factor + smooth_factor * inv_llama
    is_medium_freq = ~(wavelen < high_freq_wavelen) * ~(wavelen > low_freq_wavelen)
    return torch.where(is_medium_freq, smoothed, inv_llama)


def weights_from_hf(model, *, dtype: torch.dtype = torch.float64) -> LlamaWeights:
    """Views of a ``LlamaForCausalLM`` in ``dtype``. Biases must be absent, because DLA assumes none.

    ``dtype`` is the precision the whole pass runs in: the weights, the residual stream, the norm
    and the softmax. float64 is the default and the only mode the 135M exports use; float32 is the
    mode for models whose float64 copy does not fit, and it is gated relatively (see ``gates.py``).
    """
    cfg = model.config
    if getattr(cfg, "attention_bias", False) or getattr(cfg, "mlp_bias", False):
        raise ValueError("biases are not supported (DLA closure assumes bias-free projections)")
    if cfg.hidden_act != "silu":
        raise ValueError(f"expected SiLU gating, got {cfg.hidden_act}")
    if dtype not in (torch.float32, torch.float64):
        raise ValueError(f"only float32 and float64 passes are supported; got {dtype}")
    core = model.model
    f = lambda t: t.detach().to(device="cpu", dtype=dtype)  # noqa: E731
    layers = []
    for blk in core.layers:
        att, mlp = blk.self_attn, blk.mlp
        layers.append({
            "in_norm": f(blk.input_layernorm.weight),
            "q": f(att.q_proj.weight), "k": f(att.k_proj.weight),
            "v": f(att.v_proj.weight), "o": f(att.o_proj.weight),
            "post_norm": f(blk.post_attention_layernorm.weight),
            "gate": f(mlp.gate_proj.weight), "up": f(mlp.up_proj.weight),
            "down": f(mlp.down_proj.weight),
        })
    n_heads = cfg.num_attention_heads
    return LlamaWeights(
        embed=f(core.embed_tokens.weight),
        unembed=f(model.lm_head.weight),
        final_norm=f(core.norm.weight),
        layers=layers,
        n_heads=n_heads,
        n_kv=cfg.num_key_value_heads,
        head_dim=getattr(cfg, "head_dim", None) or cfg.hidden_size // n_heads,
        rms_eps=float(cfg.rms_norm_eps),
        rope_theta=_rope_theta(cfg),
        rope_scaling=_rope_scaling(cfg),
    )


def rms_norm(x: torch.Tensor, weight: torch.Tensor, eps: float) -> torch.Tensor:
    return weight * (x / torch.sqrt((x * x).mean(-1, keepdim=True) + eps))


def _rotate_half(x: torch.Tensor) -> torch.Tensor:
    half = x.shape[-1] // 2
    return torch.cat((-x[..., half:], x[..., :half]), dim=-1)


def _rope(T: int, head_dim: int, theta: float, scaling: RopeScaling = RopeScaling(),
          *, dtype: torch.dtype = torch.float64) -> tuple:
    """The rotation tables for positions 0..T-1, built in ``dtype``.

    The tables must be built in the pass's dtype: ``q * cos`` over a float32 ``q`` and a
    float64 ``cos`` promotes the whole stream to float64, which would turn a float32 pass into
    a slow float64 one without saying so.
    """
    inv_freq = rope_inv_freq(head_dim, theta, scaling, dtype=dtype)
    freqs = torch.arange(T, dtype=dtype)[:, None] * inv_freq[None, :]
    emb = torch.cat((freqs, freqs), dim=-1)
    return emb.cos(), emb.sin()


def run(W: LlamaWeights, ids, *, j_plus: int | None = None, j_minus: int | None = None,
        clamp_q3: bool = False, eps_q3: float = EPS_Q3, keep_head_out: bool = False,
        drop_head_write: tuple[int, int] | None = None,
        scale_mlp_write: tuple[int, float] | None = None) -> dict:
    """One forward pass over ``ids`` in the weights' dtype. Readout and DLA sit at the last position.

    With ``clamp_q3`` the Quadrant-III products are set to zero in every layer at every
    position *during* the pass, so the effect propagates downstream.

    ``drop_head_write=(layer, head)`` is a corruption for the conservation-gate tests only:
    that head's write is removed from the *stored* attention slice while the residual stream
    keeps it, which is what a capture bug looks like from the outside. Nothing in the export
    path sets it. The returned ``residual_closure_inf`` then fails its gate, by design.
    """
    ids = torch.as_tensor(ids, dtype=torch.long)
    dtype = W.embed.dtype
    T, H, KV, hd, eps = int(ids.shape[0]), W.n_heads, W.n_kv, W.head_dim, W.rms_eps
    rep = H // KV
    cos, sin = _rope(T, hd, W.rope_theta, W.rope_scaling, dtype=dtype)
    causal = torch.triu(torch.ones(T, T, dtype=torch.bool), diagonal=1)

    h = W.embed[ids].clone()
    resid, attn_out, mlp_out, head_out, probs = [h], [], [], [], []
    g_all, u_all, c_all, q3_mask, q3_write = [], [], [], [], []
    for layer, lw in enumerate(W.layers):
        x = rms_norm(h, lw["in_norm"], eps)
        q = (x @ lw["q"].T).view(T, H, hd).transpose(0, 1)
        k = (x @ lw["k"].T).view(T, KV, hd).transpose(0, 1)
        v = (x @ lw["v"].T).view(T, KV, hd).transpose(0, 1)
        q = q * cos + _rotate_half(q) * sin
        k = k * cos + _rotate_half(k) * sin
        k = k.repeat_interleave(rep, dim=0)          # head h reads kv head h // rep (HF repeat_kv)
        v = v.repeat_interleave(rep, dim=0)
        scores = (q @ k.transpose(-1, -2)) / math.sqrt(hd)
        A = torch.softmax(scores.masked_fill(causal, float("-inf")), dim=-1)   # (H, T, T)
        z = A @ v                                                              # (H, T, hd)
        w_o = lw["o"].view(W.d_model, H, hd).permute(1, 2, 0)                  # (H, hd, d)
        o = torch.einsum("htk,hkd->htd", z, w_o)                               # (H, T, d)
        a = o.sum(0)
        h = h + a
        if drop_head_write is not None and drop_head_write[0] == layer:
            # Both stored pieces lose the head (the exporter forgot to write it down); the
            # residual stream above keeps it, because the addition already happened.
            dropped = o[drop_head_write[1]]
            o = o.clone()
            o[drop_head_write[1]] = 0.0
            a = a - dropped

        x2 = rms_norm(h, lw["post_norm"], eps)
        g = x2 @ lw["gate"].T
        u = x2 @ lw["up"].T
        q3 = (g < -eps_q3) & (u < -eps_q3)
        c_raw = F.silu(g) * u
        c = c_raw.masked_fill(q3, 0.0) if clamp_q3 else c_raw
        m = c @ lw["down"].T
        h = h + m
        if scale_mlp_write is not None and scale_mlp_write[0] == layer:
            m = m * scale_mlp_write[1]            # the stream above already added the true m

        resid.append(h)
        attn_out.append(a)
        mlp_out.append(m)
        head_out.append(o)
        probs.append(A)
        g_all.append(g)
        u_all.append(u)
        c_all.append(c)
        q3_mask.append(q3)
        q3_write.append((c_raw * q3) @ lw["down"].T)   # the write Quadrant III makes (or would make)

    hL = h
    final = rms_norm(hL, W.final_norm, eps)
    logits = final @ W.unembed.T                        # (T, V)

    R = torch.stack(resid)                              # (L+1, T, d)
    Aout = torch.stack(attn_out)                        # (L, T, d)
    Mout = torch.stack(mlp_out)
    O = torch.stack(head_out)                           # (L, H, T, d)
    C = torch.stack(c_all)                              # (L, T, F)
    Q3 = torch.stack(q3_mask)

    closure = (R[-1] - (R[0] + Aout.sum(0) + Mout.sum(0))).abs().max().item()
    head_closure = (Aout - O.sum(1)).abs().max().item()
    # Scales the relative gates divide by (``gates.py``): the size of the quantity the error is
    # an error of. Both are inf-norms of what the stream and the attention write actually are.
    resid_scale = R[-1].abs().max().item()
    attn_scale = Aout.abs().max().item()

    # Step closure: each layer's addition at its own grain (see ``gates.py``), in the pass dtype.
    step_err = (R[1:] - R[:-1] - Aout - Mout).abs().amax(-1)                   # (L, T)
    step_scale = R[1:].abs().amax(-1)                                          # (L, T)
    step_err_inf, step_scale_inf = worst_step(step_err, step_scale)

    out = {
        "T": T,
        "dtype": str(dtype).replace("torch.", ""),
        "step_err_inf": step_err_inf,
        "step_scale_inf": step_scale_inf,
        "step_err_by_layer": step_err.amax(-1),                                 # (L,)
        "resid_norm": R.norm(dim=-1),                       # (L+1, T)
        "attn_norm": Aout.norm(dim=-1),                     # (L, T)
        "mlp_norm": Mout.norm(dim=-1),
        "head_norm": O.norm(dim=-1),                        # (L, H, T)
        "attn_probs": torch.stack(probs),                   # (L, H, T, T)
        "q3_count": Q3.sum(-1),                             # (L, T)
        "q3_write_norm": torch.stack(q3_write).norm(dim=-1),  # (L, T)
        "g_last": torch.stack(g_all)[:, -1, :],             # (L, F)
        "u_last": torch.stack(u_all)[:, -1, :],
        "c_last": C[:, -1, :],
        "logits": logits,
        "logits_last": logits[-1],
        "residual_closure_inf": closure,
        "residual_scale_inf": resid_scale,
        "head_closure_inf": head_closure,
        "attn_scale_inf": attn_scale,
        "_resid": R, "_attn": Aout, "_mlp": Mout,
    }
    if keep_head_out:
        out["_head_out"] = O

    if j_plus is not None and j_minus is not None:
        t = T - 1
        rho = torch.sqrt((hL[t] * hL[t]).mean() + eps)
        w = W.final_norm * (W.unembed[j_plus] - W.unembed[j_minus]) / rho      # (d,)
        margin = (logits[t, j_plus] - logits[t, j_minus]).item()
        embed_attr = (R[0, t] @ w).item()
        head_attr = O[:, :, t, :] @ w                                          # (L, H)
        down_w = torch.stack([lw["down"].T @ w for lw in W.layers])            # (L, F)
        neuron_attr = C[:, t, :] * down_w                                      # (L, F)
        attr_sum = embed_attr + head_attr.sum().item() + neuron_attr.sum().item()
        out.update({
            "margin": margin,
            "embed_attr": embed_attr,
            "head_attr": head_attr,
            "neuron_attr": neuron_attr,
            "attn_attr": head_attr.sum(1),                                     # (L,)
            "mlp_attr": neuron_attr.sum(1),                                    # (L,)
            "running_margin": R[:, t, :] @ w,                                  # (L+1,)
            "attr_sum": attr_sum,
            "dla_gap": abs(margin - attr_sum),
            "rho_final": rho.item(),
        })
    return out


def code_probs(logits_last: torch.Tensor, code_token: dict) -> dict:
    """Eq. 6 at the readout position: softmax over the code-token logits."""
    codes = list(code_token)
    vals = torch.stack([logits_last[code_token[c]] for c in codes])
    p = torch.softmax(vals, dim=0)
    return {c: float(p[i]) for i, c in enumerate(codes)}


def check_adapter(adapter_dir, model_id: str) -> tuple:
    """The guards every adapter passes before it is applied. Returns ``(config, file state dict)``.

    The config must describe a plain LoRA for THIS base, otherwise the model built from it is
    not the one the adapter was trained on; and the file must hold LoRA tensors.
    """
    import json  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    from safetensors.torch import load_file  # noqa: PLC0415

    cfg = json.loads((Path(adapter_dir) / "adapter_config.json").read_text())
    if cfg.get("base_model_name_or_path") != model_id:
        raise ValueError(f"adapter was trained on {cfg.get('base_model_name_or_path')!r}, "
                         f"not {model_id!r}")
    if cfg.get("bias", "none") != "none":
        raise ValueError(f"adapter bias={cfg['bias']!r} is not supported (only 'none')")
    if cfg.get("modules_to_save"):
        raise ValueError(f"adapter modules_to_save={cfg['modules_to_save']} is not supported")
    file_sd = load_file(str(Path(adapter_dir) / "adapter_model.safetensors"))
    if not any("lora_" in k for k in file_sd):
        raise ValueError("adapter file holds no lora_ tensors")
    return cfg, file_sd


def load_hf(model_id: str, adapter_dir: str | None = None, *, dtype: torch.dtype = torch.float64):
    """Eager HF model on CPU in ``dtype``. An adapter is merged in (W + (alpha/r) B A) by peft.

    float64 is the default (the 135M path). ``dtype=torch.float32`` loads and merges in float32,
    which is what a model whose float64 copy does not fit needs; the adapter merge keeps the same
    guards in both modes.

    peft 0.21.2 ``PeftModel.from_pretrained`` silently leaves every LoRA B at zero when the
    base model is float64, which turns the fine-tune into the base model. So the adapter
    state dict is set explicitly. Every LoRA tensor in the module is then checked against
    the file, and the load raises if any differ.
    """
    from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: PLC0415

    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, dtype=dtype,
                                                 attn_implementation="eager")
    if adapter_dir:
        from peft import PeftModel, set_peft_model_state_dict  # noqa: PLC0415

        _, file_sd = check_adapter(adapter_dir, model_id)
        model = PeftModel.from_pretrained(model, adapter_dir)
        res = set_peft_model_state_dict(model, file_sd)
        if res.unexpected_keys:
            raise ValueError(f"adapter keys not in model: {list(res.unexpected_keys)[:3]}")
        # Every LoRA module the config creates needs its A and B in the file. peft only warns
        # here, and a missing pair keeps its random A / zero B: a quietly different model.
        missing = [k for k in res.missing_keys if "lora_" in k]
        if missing:
            raise ValueError(f"{len(missing)} LoRA tensors missing from the adapter file, "
                             f"e.g. {missing[:2]}")
        params = dict(model.named_parameters())
        n_checked = 0
        for key, value in file_sd.items():
            name = key.replace(".weight", ".default.weight")
            if name not in params:
                raise ValueError(f"adapter tensor {key} has no module parameter {name}")
            if not torch.equal(params[name].detach().to(value.dtype), value):
                raise ValueError(f"adapter tensor {key} did not load (module != file)")
            n_checked += 1
        if n_checked == 0 or n_checked != len(file_sd):
            raise ValueError(f"checked {n_checked} of {len(file_sd)} adapter tensors")
        model = model.merge_and_unload()
    model.eval()
    return model, tok


def _rmsnorm_native_dtype(self, hidden_states):
    """``LlamaRMSNorm.forward`` without the float32 round trip (same formula, input dtype)."""
    variance = hidden_states.pow(2).mean(-1, keepdim=True)
    return self.weight * (hidden_states * torch.rsqrt(variance + self.variance_epsilon))


def _rope_native_dtype(self, x, position_ids):
    """``LlamaRotaryEmbedding.forward`` with the tables built in x's dtype, not float32.

    HF builds ``inv_freq`` in float32 at init and casts it to float32 again in ``forward``. This
    keeps its formula, including the llama3 rescaling, but removes that cast: the table is built
    in the precision the rest of the pass uses.
    """
    cfg = self.config
    dim = getattr(cfg, "head_dim", None) or cfg.hidden_size // cfg.num_attention_heads
    theta = _rope_theta(cfg)
    # HF computes the table in float32 and casts it to x.dtype; keep x's precision when it is
    # the wider one (the float64 case this patch exists for), else keep HF's float32 table.
    table_dtype = x.dtype if x.dtype in (torch.float32, torch.float64) else torch.float32
    inv_freq = rope_inv_freq(dim, theta, _rope_scaling(cfg), dtype=table_dtype).to(x.dtype)
    freqs = position_ids[..., None].to(x.dtype) * inv_freq
    emb = torch.cat((freqs, freqs), dim=-1)
    return emb.cos() * self.attention_scaling, emb.sin() * self.attention_scaling


def _eager_attention_native_dtype(module, query, key, value, attention_mask, scaling,
                                  dropout=0.0, **kwargs):
    """``eager_attention_forward`` with the softmax in the query dtype, not float32."""
    from transformers.models.llama.modeling_llama import repeat_kv  # noqa: PLC0415

    k = repeat_kv(key, module.num_key_value_groups)
    v = repeat_kv(value, module.num_key_value_groups)
    w = torch.matmul(query, k.transpose(2, 3)) * scaling
    if attention_mask is not None:
        w = w + attention_mask
    w = torch.softmax(w, dim=-1)
    return torch.matmul(w, v).transpose(1, 2).contiguous(), w


@torch.no_grad()
def reference_check(model, ids, ours: dict) -> dict:
    """Compare our pass with the Hugging Face forward on the same weights.

    HF returns the residual entering each layer (indices 0..L-1). Its last hidden state is
    already final-normed, so the last pre-norm residual is checked through the logits. Gaps
    are max |difference|, absolute and relative to the largest |entry| of the reference.

    Stock HF computes three steps in float32 even for a float64 model:
    ``LlamaRMSNorm`` (cast), ``LlamaRotaryEmbedding`` (float32 tables) and
    ``eager_attention_forward`` (softmax ``dtype=torch.float32``). Two comparisons follow:
      * ``hf_*``: stock HF. This gap is float32 round-off from those three steps.
      * ``hf64_*``: HF with exactly those three casts removed, patched only for this call.
        This gap must be float64 round-off. If it is, the three casts explain all of the
        stock gap, and our decomposition is the HF computation.

    On a float32 pass those three casts are no-ops, so ``hf_*`` and ``hf64_*`` measure the same
    gap; either one is what ``gates.logits_reference`` divides by. ``hf_logits_scale`` is the
    max |logit| of the reference, i.e. that gate's scale.
    """
    from transformers.models.llama import modeling_llama as ml  # noqa: PLC0415

    ids_t = torch.as_tensor(ids, dtype=torch.long)[None]

    def gaps(ref):
        hs = ref.hidden_states
        L = len(hs) - 1
        hid = max((hs[l][0] - ours["_resid"][l]).abs().max().item() for l in range(L))
        hid_scale = max(hs[l][0].abs().max().item() for l in range(L))
        lg = (ref.logits[0] - ours["logits"]).abs().max().item()
        lg_scale = ref.logits[0].abs().max().item()
        return hid, hid / hid_scale, lg, lg / lg_scale, lg_scale

    stock = gaps(model(input_ids=ids_t, output_hidden_states=True))
    saved = (ml.LlamaRMSNorm.forward, ml.LlamaRotaryEmbedding.forward, ml.eager_attention_forward)
    ml.LlamaRMSNorm.forward = _rmsnorm_native_dtype
    ml.LlamaRotaryEmbedding.forward = _rope_native_dtype
    ml.eager_attention_forward = _eager_attention_native_dtype
    try:
        exact = gaps(model(input_ids=ids_t, output_hidden_states=True))
    finally:
        ml.LlamaRMSNorm.forward, ml.LlamaRotaryEmbedding.forward, ml.eager_attention_forward = saved
    return {
        "hf_hidden_max_abs_gap": stock[0], "hf_hidden_max_rel_gap": stock[1],
        "hf_logits_max_abs_gap": stock[2], "hf_logits_max_rel_gap": stock[3],
        "hf64_hidden_max_abs_gap": exact[0], "hf64_hidden_max_rel_gap": exact[1],
        "hf64_logits_max_abs_gap": exact[2], "hf64_logits_max_rel_gap": exact[3],
        "hf_logits_scale": stock[4],
    }


@torch.no_grad()
def teacher_forced_probs(model, base_ids: list, completions: dict) -> dict:
    """Eq. 6 the long way: sum the completion log-probs under the HF model, then softmax over codes."""
    logps = {}
    for code, comp in completions.items():
        ids = torch.tensor([list(base_ids) + list(comp)])
        lp = torch.log_softmax(model(input_ids=ids).logits[0, :-1], dim=-1)
        tgt = ids[0, 1:]
        tok_lp = lp.gather(1, tgt[:, None])[:, 0]
        logps[code] = float(tok_lp[-len(comp):].sum())
    vals = np.array(list(logps.values()))
    p = np.exp(vals - vals.max())
    p /= p.sum()
    return dict(zip(logps, p.tolist()))
