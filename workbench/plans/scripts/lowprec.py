"""Prototype: ``llama_capture.run`` with the dtype and device as parameters (memo scratch, not src/).

Three dtypes per variant:
    wdt  weights as stored
    mdt  dtype the matmuls run in (weights and inputs are cast to it at use)
    sdt  dtype of the residual stream, norms, softmax, attributions
Same arithmetic as ``llama_capture.run`` (same formulas, same order). Only the readouts the
gates need are returned. Checker arithmetic (closure, DLA sum) is done in float64 on CPU, so the
check itself adds no round-off.

Variants used in the memo:
    f32        wdt=mdt=sdt=float32
    bf16       wdt=mdt=sdt=bfloat16                 (everything bf16, the naive port)
    hfmixed    wdt=mdt=bfloat16, sdt=float32        (bf16 matmuls; fp32 stream, norm, softmax)
    w16c32     wdt=bfloat16, mdt=sdt=float32        (weights stored bf16, upcast per layer)
"""

import math
import time

import torch
import torch.nn.functional as F

from sca2_workbench import llama_capture as LC

VARIANTS = {
    "f64": (torch.float64, torch.float64, torch.float64),
    "f32": (torch.float32, torch.float32, torch.float32),
    "bf16": (torch.bfloat16, torch.bfloat16, torch.bfloat16),
    "hfmixed": (torch.bfloat16, torch.bfloat16, torch.float32),
    "w16c32": (torch.bfloat16, torch.float32, torch.float32),
}


def to_device(W: LC.LlamaWeights, wdt, device) -> dict:
    """Weights cast to wdt on device. Returns a plain dict (the layer dicts hold tensors)."""
    f = lambda t: t.to(dtype=wdt, device=device)  # noqa: E731
    return {"embed": f(W.embed), "unembed": f(W.unembed), "final_norm": f(W.final_norm),
            "layers": [{k: f(v) for k, v in lw.items()} for lw in W.layers],
            "H": W.n_heads, "KV": W.n_kv, "hd": W.head_dim, "eps": W.rms_eps,
            "theta": W.rope_theta, "d": W.d_model}


def _rms(x, w, eps):
    return w * (x / torch.sqrt((x * x).mean(-1, keepdim=True) + eps))


def _rot(x):
    h = x.shape[-1] // 2
    return torch.cat((-x[..., h:], x[..., :h]), dim=-1)


@torch.no_grad()
def run(Wd: dict, ids, jp: int, jm: int, mdt, sdt, device, clamp_q3=False, eps_q3=LC.EPS_Q3):
    ids = torch.as_tensor(ids, dtype=torch.long, device=device)
    T, H, KV, hd, eps = int(ids.shape[0]), Wd["H"], Wd["KV"], Wd["hd"], Wd["eps"]
    rep, d = H // KV, Wd["d"]
    cos, sin = LC._rope(T, hd, Wd["theta"])                      # float64 tables, then cast
    cos, sin = cos.to(sdt).to(device), sin.to(sdt).to(device)
    causal = torch.triu(torch.ones(T, T, dtype=torch.bool, device=device), diagonal=1)
    S = lambda t: t.to(sdt)  # noqa: E731
    M = lambda t: t.to(mdt)  # noqa: E731

    h = S(Wd["embed"][ids])
    resid, attn_out, mlp_out, head_out, c_used = [h], [], [], [], []
    for lw in Wd["layers"]:
        x = M(_rms(h, S(lw["in_norm"]), eps))
        q = S((x @ M(lw["q"]).T).view(T, H, hd).transpose(0, 1))
        k = S((x @ M(lw["k"]).T).view(T, KV, hd).transpose(0, 1))
        v = S((x @ M(lw["v"]).T).view(T, KV, hd).transpose(0, 1))
        q = q * cos + _rot(q) * sin
        k = (k * cos + _rot(k) * sin).repeat_interleave(rep, dim=0)
        v = v.repeat_interleave(rep, dim=0)
        A = torch.softmax(((q @ k.transpose(-1, -2)) / math.sqrt(hd)).masked_fill(causal, float("-inf")), dim=-1)
        z = A @ v
        w_o = M(lw["o"]).view(d, H, hd).permute(1, 2, 0)
        o = S(torch.einsum("htk,hkd->htd", M(z), w_o))
        a = o.sum(0)
        h = h + a
        x2 = _rms(h, S(lw["post_norm"]), eps)
        g = S(M(x2) @ M(lw["gate"]).T)
        u = S(M(x2) @ M(lw["up"]).T)
        q3 = (g < -eps_q3) & (u < -eps_q3)
        c = F.silu(g) * u
        c = c.masked_fill(q3, 0.0) if clamp_q3 else c
        c = S(M(c))                                              # the c the down-projection really sees
        m = S(M(c) @ M(lw["down"]).T)
        h = h + m
        resid.append(h); attn_out.append(a); mlp_out.append(m); head_out.append(o); c_used.append(c)
    final = _rms(h, S(Wd["final_norm"]), eps)
    logits_last = S(M(final[-1]) @ M(Wd["unembed"]).T)
    t = T - 1
    rho = torch.sqrt((h[t] * h[t]).mean() + eps)
    w = S(Wd["final_norm"]) * (S(Wd["unembed"][jp]) - S(Wd["unembed"][jm])) / rho
    margin = (logits_last[jp] - logits_last[jm]).cpu().double().item()
    # ---- the checker, in float64 on CPU
    R = torch.stack(resid).cpu().double()
    Am, Mm = torch.stack(attn_out).cpu().double(), torch.stack(mlp_out).cpu().double()
    closure = (R[-1] - (R[0] + Am.sum(0) + Mm.sum(0))).abs().max().item()
    w64 = w.cpu().double()
    O = torch.stack(head_out)[:, :, t, :].cpu().double()
    head_attr = O @ w64                                          # (L, H)
    down_w = torch.stack([M(lw["down"]).T.cpu().double() @ w64 for lw in Wd["layers"]])
    neuron_attr = torch.stack([ci[t].cpu().double() for ci in c_used]) * down_w
    embed_attr = (R[0, t] @ w64).item()
    attr_sum = embed_attr + head_attr.sum().item() + neuron_attr.sum().item()
    return {"T": T, "margin": margin, "dla_gap": abs(margin - attr_sum), "closure": closure,
            "max_h": R.abs().max().item(), "head_attr": head_attr, "neuron_attr": neuron_attr,
            "logits_last": logits_last.cpu().double()}


def timed(fn, device, reps=3):
    fn()                                                         # warm-up
    ts = []
    for _ in range(reps):
        if device == "mps":
            torch.mps.synchronize()
        t0 = time.perf_counter()
        r = fn()
        if device == "mps":
            torch.mps.synchronize()
        ts.append(time.perf_counter() - t0)
    return sorted(ts)[len(ts) // 2], r
