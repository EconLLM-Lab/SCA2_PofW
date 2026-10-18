"""Independent RoPE parity check (verifier). Written from the llama3 scaling definition,
not from the producer's code. Compares: my table vs HF's module vs the workbench's table."""
import json, math, hashlib
from pathlib import Path
import torch

WB = Path(__file__).resolve().parents[3]
FIX = WB / "tests" / "fixtures" / "hf" / "llama-3.1-8B-Instruct.config.json"
print("fixture sha256:", hashlib.sha256(FIX.read_bytes()).hexdigest())
cfg_d = json.loads(FIX.read_text())
print("rope_scaling:", cfg_d.get("rope_scaling"))
print("rope_theta:", cfg_d.get("rope_theta"), "rope_parameters:", cfg_d.get("rope_parameters"))
head_dim = cfg_d.get("head_dim") or cfg_d["hidden_size"] // cfg_d["num_attention_heads"]
theta = (cfg_d.get("rope_parameters") or {}).get("rope_theta") or cfg_d["rope_theta"]
rs = cfg_d.get("rope_scaling") or cfg_d["rope_parameters"]
factor, lf, hf_, orig = rs["factor"], rs["low_freq_factor"], rs["high_freq_factor"], rs["original_max_position_embeddings"]
print("factor", factor, "low", lf, "high", hf_, "orig", orig)

dim = head_dim
# --- my own float64 table, written from the paper / HF _compute_llama3_parameters ---
inv_freq = 1.0 / (theta ** (torch.arange(0, dim, 2, dtype=torch.float64) / dim))
wavelen = 2 * math.pi / inv_freq
low_w = orig / lf
high_w = orig / hf_
out = inv_freq.clone()
out[wavelen > low_w] = inv_freq[wavelen > low_w] / factor
mid = (wavelen >= high_w) & (wavelen <= low_w)
# HF blend: smooth_factor = (orig/wavelen - low_freq_factor)/(high_freq_factor - low_freq_factor)
smooth = (orig / wavelen[mid] - lf) / (hf_ - lf)
blended = (1 - smooth) * out[mid] / factor + smooth * out[mid]
out[mid] = blended
nhi, nmid, nlo = int((wavelen < high_w).sum()), int(mid.sum()), int((wavelen > low_w).sum())
print(f"bands high={nhi} medium={nmid} low={nlo} of {len(wavelen)}")
assert nhi and nmid and nlo, "not all bands populated"

# --- HF module, float32 table cast switched off ---
from transformers.models.llama import modeling_llama as ml
import transformers
print("transformers", transformers.__version__)
cfg = transformers.LlamaConfig.from_dict(cfg_d)
saved = torch.float
torch.float = torch.float64
try:
    mod = ml.LlamaRotaryEmbedding(cfg)
    assert mod.inv_freq.dtype == torch.float64
    P = torch.arange(0, 4097, dtype=torch.long)
    x = torch.zeros(1, P.numel(), dim, dtype=torch.float64)
    hf_cos, hf_sin = mod(x, P[None])
    LP = torch.tensor([8192, 16384, 65536, 131071], dtype=torch.long)
    xl = torch.zeros(1, LP.numel(), dim, dtype=torch.float64)
    hf_cos_l, hf_sin_l = mod(xl, LP[None])
finally:
    torch.float = saved

def table(inv):
    freqs = P[:, None].to(torch.float64) * inv[None, :]
    emb = torch.cat((freqs, freqs), dim=-1)
    return emb.cos()[None], emb.sin()[None]

my_cos, my_sin = table(out)
g = max((my_cos - hf_cos).abs().max().item(), (my_sin - hf_sin).abs().max().item())
print(f"MAX GAP my table vs HF(f64) over p=0..4096: {g:.3e}  gate 1e-12 -> {'PASS' if g<=1e-12 else 'FAIL'}")

def table_at(inv, pos):
    freqs = pos[:, None].to(torch.float64) * inv[None, :]
    emb = torch.cat((freqs, freqs), dim=-1)
    return emb.cos()[None], emb.sin()[None]
lcos, lsin = table_at(out, LP)
gl = max((lcos - hf_cos_l).abs().max().item(), (lsin - hf_sin_l).abs().max().item())
print(f"MAX GAP at long positions {LP.tolist()}: {gl:.3e} -> {'PASS' if gl<=1e-12 else 'FAIL'}")

# --- is the scaling actually exercised? diff against the unscaled table ---
plain_cos, plain_sin = table(inv_freq)
rot_gap = max((my_cos - plain_cos).abs().max().item(), (my_sin - plain_sin).abs().max().item())
print(f"scaled vs unscaled rotation table max gap: {rot_gap:.3e} (must be >> 1e-12)")
low_idx = (wavelen > low_w).nonzero().flatten()
mid_idx = mid.nonzero().flatten()
print("low-band freqs:", low_idx.tolist()[:5], "count", len(low_idx))
print("medium-band freqs:", mid_idx.tolist()[:8], "count", len(mid_idx))
print("ratio low band out/plain:", (out[low_idx] / inv_freq[low_idx]).unique().tolist()[:3])

# --- does the workbench table equal mine / HF's? ---
import sys
sys.path.insert(0, str(WB / "src"))
import sca2_workbench.llama_capture as LC
wb_scaling = LC._rope_scaling(cfg)
wb_inv = LC.rope_inv_freq(dim, theta, wb_scaling)
print("workbench inv_freq == my inv_freq (torch.equal):", torch.equal(wb_inv, out))
print("workbench inv_freq vs my: max rel", ((wb_inv - out).abs() / out.abs()).max().item())
cos, sin = LC._rope(P.numel(), dim, theta, wb_scaling)
print("workbench _rope vs my table: max gap", max((cos - my_cos[0]).abs().max().item(), (sin - my_sin[0]).abs().max().item()))
