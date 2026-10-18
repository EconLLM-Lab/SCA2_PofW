"""Verifier: criterion 3 (relative gates, tau multiple), 4 (broken capture), PM step-gate re-test.

All gate arithmetic here is written from the definition in spec/conservation.md, not called
from gates.py; gates.py is used only to compare my numbers with the shipped taus.
"""
import sys
from pathlib import Path
import torch

WB = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WB / "src"))
import sca2_workbench.llama_capture as LC
import sca2_workbench.stream_capture as SC
from sca2_workbench import items as I, gates as G

MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"
TAU = {torch.float64: G.TAUS_F64, torch.float32: G.TAUS_F32}


def ratios(R, A, M):
    """Global residual closure, step closure, head closure -- written from the spec."""
    closure = (R[-1] - (R[0] + A.sum(0) + M.sum(0))).abs().max().item()
    res_scale = max(R[-1].abs().max().item(), 1.0)
    step_err = (R[1:] - R[:-1] - A - M).abs().amax(-1)        # (L, T)
    step_scale = R[1:].abs().amax(-1).clamp(min=1.0)
    r = step_err / step_scale
    i = int(r.argmax())
    L_, T_ = r.shape
    li, ti = divmod(i, T_)
    return dict(residual=closure / res_scale, step=r.flatten()[i].item(),
                step_where=(li, ti), step_err=step_err.flatten()[i].item(),
                step_scale=step_scale.flatten()[i].item(), res_scale=res_scale)


def report(tag, ratio, taus):
    print(f"   {tag:52s} residual={ratio['residual']/taus.residual_closure:9.3g}x tau  "
          f"step={ratio['step']/taus.step_closure:9.3g}x tau (worst L,T={ratio['step_where']})")


def load(dtype):
    m, tok = LC.load_hf(MODEL, dtype=dtype)
    return LC.weights_from_hf(m, dtype=dtype), tok


W64, tok = load(torch.float64)
W32, _ = load(torch.float32)
item = I.wvs_item("Q81")
ro = I.readout_ids(tok, item)
jp, jm = ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]
ids = ro["prompt_ids"]
T = len(ids)
print(f"135M-Instruct wvs_Q81: T={T}, t*={T-1}")

clean = {}
for dtype, W in ((torch.float64, W64), (torch.float32, W32)):
    out = LC.run(W, ids, j_plus=jp, j_minus=jm)
    clean[dtype] = out
    g = G.check_capture(out, TAU[dtype])
    print(f"\n clean {str(dtype).split('.')[-1]}: shipped gates "
          + " ".join(f"{k}={v.rel/v.tau:.3f}x" for k, v in g.items() if k in
                     ("residual_closure", "step_closure", "head_closure", "readout"))
          + f" all_ok={G.all_ok(g)}")
    r = ratios(out["_resid"], out["_attn"], out["_mlp"])
    print(f"   my re-derivation from the stored pieces: residual={r['residual']:.3e} "
          f"({r['residual']/TAU[dtype].residual_closure:.3f}x tau) step={r['step']:.3e} "
          f"({r['step']/TAU[dtype].step_closure:.3f}x tau) at (L,T)={r['step_where']}")

# ---------------------------------------------------------------- (4) broken capture
print("\n### (4) broken capture: drop the largest head write, clean capture passes")
R = clean[torch.float64]["_resid"]
for dtype, W in ((torch.float64, W64), (torch.float32, W32)):
    hn = clean[dtype]["head_norm"]                       # (L, H, T), ||o||_2 per (l,h,t)
    l, h = divmod(int(hn.amax(-1).argmax()), hn.shape[1])
    out = LC.run(W, ids, j_plus=jp, j_minus=jm, drop_head_write=(l, h))
    g = G.check_capture(out, TAU[dtype])
    print(f" {str(dtype).split('.')[-1]} drop_head_write=({l},{h}) "
          + " ".join(f"{k}={v.rel/v.tau:.3g}x" for k, v in g.items())
          + f" all_ok={G.all_ok(g)}")

# ---------------------------------------------------------------- PM step-gate re-test
print("\n### PM re-test: my own corruption, applied to the STORED pieces (stream keeps the truth)")
for dtype in (torch.float32, torch.float64):
    out = clean[dtype]
    R, A, M = out["_resid"], out["_attn"], out["_mlp"]
    L, Tn = A.shape[0], A.shape[1]
    base = ratios(R, A, M)
    taus = TAU[dtype]
    print(f"\n dtype {str(dtype).split('.')[-1]}  clean: residual {base['residual']:.2e} "
          f"({base['residual']/taus.residual_closure:.3f}x) step {base['step']:.2e} "
          f"({base['step']/taus.step_closure:.3f}x)")

    def corr(tag, A2=A, M2=M):
        r = ratios(R, A2, M2)
        report(tag, r, taus)

    l0, p0 = L // 2, Tn // 2
    A2 = A.clone(); A2[l0, p0] = A2[l0, p0] * (1 + 1e-3)
    corr(f"one attention write x1.001, L{l0}, pos {p0} (rel 1e-3)", A2=A2)
    A3 = A.clone(); A3[l0] = A3[l0] * (1 + 1e-3)
    corr(f"whole L{l0} attention write x1.001", A2=A3)
    M2 = M.clone(); M2[l0] = M2[l0] * 1.001
    corr(f"whole L{l0} MLP write x1.001", M2=M2)
    A4 = A.clone(); A4[l0, p0] = A4[l0, p0] * (1 + 1e-1)
    corr(f"one attention write x1.1, L{l0}, pos {p0}", A2=A4)

print("\n### same corruptions through the producer's in-pass hooks (float32)")
out = LC.run(W32, ids, j_plus=jp, j_minus=jm, scale_mlp_write=(15, 1.001))
g = G.check_capture(out, G.TAUS_F32)
print("  scale_mlp_write=(15, 1.001): " + " ".join(f"{k}={v.rel/v.tau:.3g}x" for k, v in g.items())
      + f" all_ok={G.all_ok(g)}")
out = LC.run(W32, ids, j_plus=jp, j_minus=jm, scale_mlp_write=(5, 1.001))
g = G.check_capture(out, G.TAUS_F32)
print("  scale_mlp_write=(5, 1.001):  " + " ".join(f"{k}={v.rel/v.tau:.3g}x" for k, v in g.items())
      + f" all_ok={G.all_ok(g)}")
