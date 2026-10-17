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

#: Quadrant III threshold (Cammarata): both poles below -EPS.
EPS_Q3 = 0.05


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

    @property
    def n_layers(self) -> int:
        return len(self.layers)

    @property
    def d_model(self) -> int:
        return int(self.embed.shape[1])

    @property
    def d_ffn(self) -> int:
        return int(self.layers[0]["gate"].shape[0])


def _rope_theta(cfg) -> float:
    for source in (getattr(cfg, "rope_parameters", None), getattr(cfg, "rope_scaling", None)):
        if isinstance(source, dict) and "rope_theta" in source:
            if source.get("rope_type", "default") != "default":
                raise ValueError(f"only default RoPE is implemented; got {source}")
            return float(source["rope_theta"])
    theta = getattr(cfg, "rope_theta", None)
    if theta is None:
        raise ValueError("config carries no rope_theta")
    return float(theta)


def weights_from_hf(model) -> LlamaWeights:
    """float64 views of a ``LlamaForCausalLM``. Biases must be absent, because DLA assumes none."""
    cfg = model.config
    if getattr(cfg, "attention_bias", False) or getattr(cfg, "mlp_bias", False):
        raise ValueError("biases are not supported (DLA closure assumes bias-free projections)")
    if cfg.hidden_act != "silu":
        raise ValueError(f"expected SiLU gating, got {cfg.hidden_act}")
    core = model.model
    f64 = lambda t: t.detach().to(device="cpu", dtype=torch.float64)  # noqa: E731
    layers = []
    for blk in core.layers:
        att, mlp = blk.self_attn, blk.mlp
        layers.append({
            "in_norm": f64(blk.input_layernorm.weight),
            "q": f64(att.q_proj.weight), "k": f64(att.k_proj.weight),
            "v": f64(att.v_proj.weight), "o": f64(att.o_proj.weight),
            "post_norm": f64(blk.post_attention_layernorm.weight),
            "gate": f64(mlp.gate_proj.weight), "up": f64(mlp.up_proj.weight),
            "down": f64(mlp.down_proj.weight),
        })
    n_heads = cfg.num_attention_heads
    return LlamaWeights(
        embed=f64(core.embed_tokens.weight),
        unembed=f64(model.lm_head.weight),
        final_norm=f64(core.norm.weight),
        layers=layers,
        n_heads=n_heads,
        n_kv=cfg.num_key_value_heads,
        head_dim=getattr(cfg, "head_dim", None) or cfg.hidden_size // n_heads,
        rms_eps=float(cfg.rms_norm_eps),
        rope_theta=_rope_theta(cfg),
    )


def rms_norm(x: torch.Tensor, weight: torch.Tensor, eps: float) -> torch.Tensor:
    return weight * (x / torch.sqrt((x * x).mean(-1, keepdim=True) + eps))


def _rotate_half(x: torch.Tensor) -> torch.Tensor:
    half = x.shape[-1] // 2
    return torch.cat((-x[..., half:], x[..., :half]), dim=-1)


def _rope(T: int, head_dim: int, theta: float) -> tuple:
    inv_freq = 1.0 / (theta ** (torch.arange(0, head_dim, 2, dtype=torch.float64) / head_dim))
    freqs = torch.arange(T, dtype=torch.float64)[:, None] * inv_freq[None, :]
    emb = torch.cat((freqs, freqs), dim=-1)
    return emb.cos(), emb.sin()


def run(W: LlamaWeights, ids, *, j_plus: int | None = None, j_minus: int | None = None,
        clamp_q3: bool = False, eps_q3: float = EPS_Q3, keep_head_out: bool = False) -> dict:
    """One float64 forward pass over ``ids``. Readout and DLA sit at the last position.

    With ``clamp_q3`` the Quadrant-III products are set to zero in every layer at every
    position *during* the pass, so the effect propagates downstream.
    """
    ids = torch.as_tensor(ids, dtype=torch.long)
    T, H, KV, hd, eps = int(ids.shape[0]), W.n_heads, W.n_kv, W.head_dim, W.rms_eps
    rep = H // KV
    cos, sin = _rope(T, hd, W.rope_theta)
    causal = torch.triu(torch.ones(T, T, dtype=torch.bool), diagonal=1)

    h = W.embed[ids].clone()
    resid, attn_out, mlp_out, head_out, probs = [h], [], [], [], []
    g_all, u_all, c_all, q3_mask, q3_write = [], [], [], [], []
    for lw in W.layers:
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

        x2 = rms_norm(h, lw["post_norm"], eps)
        g = x2 @ lw["gate"].T
        u = x2 @ lw["up"].T
        q3 = (g < -eps_q3) & (u < -eps_q3)
        c_raw = F.silu(g) * u
        c = c_raw.masked_fill(q3, 0.0) if clamp_q3 else c_raw
        m = c @ lw["down"].T
        h = h + m

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

    out = {
        "T": T,
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
        "head_closure_inf": head_closure,
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


def load_hf(model_id: str, adapter_dir: str | None = None):
    """float64 eager HF model on CPU. An adapter is merged in (W + (alpha/r) B A) by peft.

    peft 0.21.2 ``PeftModel.from_pretrained`` silently leaves every LoRA B at zero when the
    base model is float64, which turns the fine-tune into the base model. So the adapter
    state dict is set explicitly. Every LoRA tensor in the module is then checked against
    the file, and the load raises if any differ.
    """
    from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: PLC0415

    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, dtype=torch.float64,
                                                 attn_implementation="eager")
    if adapter_dir:
        import json  # noqa: PLC0415
        from pathlib import Path  # noqa: PLC0415

        from peft import PeftModel, set_peft_model_state_dict  # noqa: PLC0415
        from safetensors.torch import load_file  # noqa: PLC0415

        # The config must describe a plain LoRA for THIS base. Otherwise the merge below is a
        # different model than the one the adapter was trained on.
        cfg = json.loads((Path(adapter_dir) / "adapter_config.json").read_text())
        if cfg.get("base_model_name_or_path") != model_id:
            raise ValueError(f"adapter was trained on {cfg.get('base_model_name_or_path')!r}, "
                             f"not {model_id!r}")
        if cfg.get("bias", "none") != "none":
            raise ValueError(f"adapter bias={cfg['bias']!r} is not supported (only 'none')")
        if cfg.get("modules_to_save"):
            raise ValueError(f"adapter modules_to_save={cfg['modules_to_save']} is not supported")

        file_sd = load_file(str(Path(adapter_dir) / "adapter_model.safetensors"))
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
    """``LlamaRotaryEmbedding.forward`` with the tables built in x's dtype, not float32."""
    cfg = self.config
    dim = getattr(cfg, "head_dim", None) or cfg.hidden_size // cfg.num_attention_heads
    theta = _rope_theta(cfg)
    inv_freq = 1.0 / (theta ** (torch.arange(0, dim, 2, dtype=x.dtype, device=x.device) / dim))
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
    """
    from transformers.models.llama import modeling_llama as ml  # noqa: PLC0415

    ids_t = torch.as_tensor(ids, dtype=torch.long)[None]

    def gaps(ref):
        hs = ref.hidden_states
        L = len(hs) - 1
        hid = max((hs[l][0] - ours["_resid"][l]).abs().max().item() for l in range(L))
        hid_scale = max(hs[l][0].abs().max().item() for l in range(L))
        lg = (ref.logits[0] - ours["logits"]).abs().max().item()
        return hid, hid / hid_scale, lg, lg / ref.logits[0].abs().max().item()

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
