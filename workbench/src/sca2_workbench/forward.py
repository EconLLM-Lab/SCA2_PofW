"""One real SwiGLU forward pass on a local training prompt.

This is not Llama. The production weights are not in the local cache.
The residual identity is the same one the conservation hooks check:
h_final = h0 + sum(attention deltas) + sum(MLP deltas).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch
import torch.nn.functional as F

from sca2_workbench.hooks import (
    clamp_quadrant_iii,
    dla_abs_gap,
    residual_inf_norm,
    swiglu_poles,
)


@dataclass(frozen=True)
class ForwardCapture:
    h0: list
    attn_sum: list
    mlp_sum: list
    h_final: list
    g_tilde: list
    u: list
    c: list
    quadrant_iii: list
    logit_margin: float
    attr_sum: float
    n_tokens: int


class TinySwiGLU(torch.nn.Module):
    """Two-layer pre-norm-free residual SwiGLU stack.

    Every layer adds an attention delta and an MLP delta. No final RMSNorm,
    so the residual sum closes without a frozen-scale convention.
    """

    def __init__(self, d_model: int = 32, n_heads: int = 2, d_ffn: int = 64, n_layers: int = 2, vocab: int = 256):
        super().__init__()
        if d_model % n_heads != 0:
            raise ValueError("d_model must divide evenly by n_heads")
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_head = d_model // n_heads
        self.d_ffn = d_ffn
        self.n_layers = n_layers
        self.embed = torch.nn.Embedding(vocab, d_model)
        self.w_q = torch.nn.Parameter(torch.empty(n_layers, d_model, d_model))
        self.w_k = torch.nn.Parameter(torch.empty(n_layers, d_model, d_model))
        self.w_v = torch.nn.Parameter(torch.empty(n_layers, d_model, d_model))
        self.w_o = torch.nn.Parameter(torch.empty(n_layers, d_model, d_model))
        self.w_gate = torch.nn.Parameter(torch.empty(n_layers, d_model, d_ffn))
        self.w_up = torch.nn.Parameter(torch.empty(n_layers, d_model, d_ffn))
        self.w_down = torch.nn.Parameter(torch.empty(n_layers, d_ffn, d_model))
        self.w_read = torch.nn.Parameter(torch.empty(d_model, 2))
        self.reset_parameters()

    def reset_parameters(self) -> None:
        for tensor in (
            self.embed.weight,
            self.w_q,
            self.w_k,
            self.w_v,
            self.w_o,
            self.w_gate,
            self.w_up,
            self.w_down,
            self.w_read,
        ):
            torch.nn.init.normal_(tensor, std=0.02)

    def forward_capture(self, token_ids: torch.Tensor) -> ForwardCapture:
        """Run one sequence. Conservation is reported at the last token."""
        if token_ids.ndim != 1:
            raise ValueError("token_ids must be a 1-D sequence")
        h = self.embed(token_ids)
        h0 = h[-1].detach()
        attn_parts = []
        mlp_parts = []
        last_g = last_u = None
        for layer in range(self.n_layers):
            attn_delta = self._attention(h, layer)
            h = h + attn_delta
            mlp_delta, _, _ = self._mlp(h, layer)
            h = h + mlp_delta
            attn_parts.append(attn_delta[-1].detach())
            mlp_parts.append(mlp_delta[-1].detach())
        h_final = h[-1].detach()
        attn_sum = torch.stack(attn_parts).sum(dim=0)
        mlp_sum = torch.stack(mlp_parts).sum(dim=0)
        read = self.w_read[:, 1] - self.w_read[:, 0]
        logit_margin = float(torch.dot(h_final, read))
        attr_sum = float(torch.dot(h0 + attn_sum + mlp_sum, read))
        pre_mlp = (h_final - mlp_parts[-1]).tolist()
        poles = swiglu_poles(
            pre_mlp,
            self.w_gate[self.n_layers - 1].detach().tolist(),
            self.w_up[self.n_layers - 1].detach().tolist(),
        )
        return ForwardCapture(
            h0=h0.tolist(),
            attn_sum=attn_sum.tolist(),
            mlp_sum=mlp_sum.tolist(),
            h_final=h_final.tolist(),
            g_tilde=poles["g_tilde"],
            u=poles["u"],
            c=poles["c"],
            quadrant_iii=poles["quadrant_iii"],
            logit_margin=logit_margin,
            attr_sum=attr_sum,
            n_tokens=int(token_ids.shape[0]),
        )

    def _attention(self, h: torch.Tensor, layer: int) -> torch.Tensor:
        q = h @ self.w_q[layer]
        k = h @ self.w_k[layer]
        v = h @ self.w_v[layer]
        t = h.shape[0]
        q = q.view(t, self.n_heads, self.d_head).transpose(0, 1)
        k = k.view(t, self.n_heads, self.d_head).transpose(0, 1)
        v = v.view(t, self.n_heads, self.d_head).transpose(0, 1)
        scale = 1.0 / math.sqrt(self.d_head)
        scores = torch.matmul(q, k.transpose(-1, -2)) * scale
        causal = torch.triu(torch.ones(t, t, dtype=h.dtype, device=h.device), diagonal=1)
        scores = scores.masked_fill(causal.bool(), float("-inf"))
        weights = torch.softmax(scores, dim=-1)
        mixed = torch.matmul(weights, v)
        mixed = mixed.transpose(0, 1).contiguous().view(t, self.d_model)
        return mixed @ self.w_o[layer]

    def _mlp(self, h: torch.Tensor, layer: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        g = h @ self.w_gate[layer]
        u = h @ self.w_up[layer]
        c = F.silu(g) * u
        return c @ self.w_down[layer], g, u


def encode_prompt(prompt: str, max_tokens: int = 1024) -> list[int]:
    raw = list(prompt.encode("utf-8"))
    if not raw:
        raise ValueError("prompt encoded to zero tokens")
    return raw[:max_tokens]


def run_prompt(prompt: str, seed: int = 20261016) -> dict:
    torch.manual_seed(seed)
    model = TinySwiGLU().double()
    ids = torch.tensor(encode_prompt(prompt), dtype=torch.long)
    with torch.no_grad():
        cap = model.forward_capture(ids)
    residual = residual_inf_norm(cap.h0, cap.attn_sum, cap.mlp_sum, cap.h_final)
    gap = dla_abs_gap(cap.logit_margin, cap.attr_sum)
    clamped = clamp_quadrant_iii(cap.g_tilde, cap.u, eps=0.05)
    qiii = [i for i, flag in enumerate(cap.quadrant_iii) if flag]
    return {
        "model": "tiny-swiglu",
        "not_llama": True,
        "seed": seed,
        "d_model": model.d_model,
        "n_layers": model.n_layers,
        "d_ffn": model.d_ffn,
        "n_tokens": cap.n_tokens,
        "residual_inf_norm": residual,
        "dla_abs_gap": gap,
        "logit_margin": cap.logit_margin,
        "quadrant_iii_count": len(qiii),
        "quadrant_iii_positive_before_clamp": sum(1 for i in qiii if cap.c[i] > 0.0),
        "clamped_quadrant_iii_max_abs": max((abs(clamped[i]) for i in qiii), default=0.0),
    }
