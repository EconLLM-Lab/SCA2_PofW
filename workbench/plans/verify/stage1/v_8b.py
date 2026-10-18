"""Verifier: 8B checks -- t* on the Llama-3 tokenizer, unmerged==merged with my own layer code,
0.1% corruption against the 8B float32 gates, and Paper B parity.

  python v_8b.py tok       # tokenizer + t* rule (cheap)
  python v_8b.py layer     # my own decoder layer, unmerged vs merged, layer 0 (cheap)
  python v_8b.py corrupt   # one streamed float32 8B pass, 0.1% MLP write corruption
  python v_8b.py parity    # Paper B sequence_logprob on HF float32 (offloaded), 8B
"""
import json, math, sys, time
from pathlib import Path
import torch

WB = Path(__file__).resolve().parents[3]
REPO = WB.parent
sys.path.insert(0, str(WB / "src")); sys.path.insert(0, str(WB / "plans" / "scripts")); sys.path.insert(0, str(REPO / "paper_b"))
MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"
SNAP = sorted((Path.home() / ".cache/huggingface/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots").glob("*"))[-1]
AD = Path.home() / ".cache/huggingface/hub/datasets--Bonorinoa--SCA2-paper-b-adapters/snapshots" / \
     (Path.home() / ".cache/huggingface/hub/datasets--Bonorinoa--SCA2-paper-b-adapters/refs/main").read_text().strip() / "adapters/USA"
import sca2_workbench.llama_capture as LC
import sca2_workbench.stream_capture as SC
from sca2_workbench import items as I, gates as G

cmd = sys.argv[1]
M = "meta-llama/Llama-3.1-8B-Instruct"


def tok_and_item(item_id="wvs_Q81"):
    from transformers import AutoTokenizer
    import stream8b as B
    tok = AutoTokenizer.from_pretrained(str(SNAP))
    p = B.paper_b_inputs(tok, item_id)
    return tok, p


if cmd == "tok":
    tok, p = tok_and_item("wvs_Q81")
    print("vocab", len(tok), "T", len(p["ro"]["prompt_ids"]), "n_base", len(p["ro"]["prompt_ids"]) - len(p["ro"]["prefix_ids"]))
    for s in (" 1", " 2", " 3", " 4", " 10"):
        ids = tok(s, add_special_tokens=False)["input_ids"]
        print(f"  {s!r:5s} -> {ids} {tok.convert_ids_to_tokens(ids)} single_token={len(ids)==1}")
    base = p["ro"]["prompt_ids"][:-len(p["ro"]["prefix_ids"])]
    fmt = tok.apply_chat_template(p["item"].parts and [
        {"role": "user", "content": p["item"].user_prompt}], tokenize=False,
        add_generation_prompt=True, date_string="26 Jul 2024")
    print("joint tokenisation exact:", all(
        tok(fmt + " " + c, add_special_tokens=False)["input_ids"] == base + tok(" " + c, add_special_tokens=False)["input_ids"]
        for c in p["codes"]))
    print("prompt_ids[-1] =", p["ro"]["prompt_ids"][-1], "t* =", len(p["ro"]["prompt_ids"]) - 1,
          "code_token =", p["ro"]["code_token"])

if cmd == "layer":
    tok, p = tok_and_item("wvs_Q81")
    item, ro = p["item"], p["ro"]
    ids = ro["prompt_ids"]
    src = SC.SafetensorsSource(SNAP, torch.float64)
    lora = SC.LoraAdapter(str(AD), M)
    lw, lo = src.layer(0), lora.layer(0, torch.float64)
    h = src.embed_rows(ids)
    T, H, KV, hd, eps = len(ids), src.n_heads, src.n_kv, src.head_dim, src.rms_eps
    rep = H // KV
    # --- my own llama3 rope table (same code as my independent parity check) ---
    theta, sc = src.rope_theta, src.rope_scaling
    inv = 1.0 / (theta ** (torch.arange(0, hd, 2, dtype=torch.float64) / hd))
    wav = 2 * math.pi / inv
    low_w, high_w = sc.original_max_position_embeddings / sc.low_freq_factor, sc.original_max_position_embeddings / sc.high_freq_factor
    outv = inv.clone(); outv[wav > low_w] = inv[wav > low_w] / sc.factor
    mid = (wav >= high_w) & (wav <= low_w)
    sm = (sc.original_max_position_embeddings / wav[mid] - sc.low_freq_factor) / (sc.high_freq_factor - sc.low_freq_factor)
    outv[mid] = (1 - sm) * outv[mid] / sc.factor + sm * outv[mid]
    freqs = torch.arange(T, dtype=torch.float64)[:, None] * outv[None, :]
    emb = torch.cat((freqs, freqs), -1)
    cos, sin = emb.cos(), emb.sin()
    causal = torch.triu(torch.ones(T, T, dtype=torch.bool), diagonal=1)

    def rot(t):  # t: (T, H, hd) -> half rotation
        x1, x2 = t[..., :hd // 2], t[..., hd // 2:]
        return torch.cat((-x2, x1), dim=-1)

    def rms(x, w):
        return x / torch.sqrt((x * x).mean(-1, keepdim=True) + eps) * w

    def forward(Wd, lo_d, scale):
        def lin(x, name):
            y = x @ Wd[name].T
            if name in lo_d:
                A, Bm = lo_d[name]
                y = y + scale * ((x @ A.T) @ Bm.T)
            return y
        q = lin(rms(h, Wd["in_norm"]), "q").view(T, H, hd).transpose(0, 1)
        k = lin(rms(h, Wd["in_norm"]), "k").view(T, KV, hd).transpose(0, 1)
        v = lin(rms(h, Wd["in_norm"]), "v").view(T, KV, hd).transpose(0, 1)
        q = q * cos + rot(q) * sin
        k = k * cos + rot(k) * sin
        k = k.repeat_interleave(rep, 0); v = v.repeat_interleave(rep, 0)
        A = torch.softmax((q @ k.transpose(-1, -2)) / math.sqrt(hd) - 1e9 * causal, -1)
        z = A @ v
        wo = Wd["o"].view(src.d_model, H, hd).permute(1, 2, 0)
        o = torch.einsum("htk,hkd->htd", z, wo)
        if "o" in lo_d:
            Aa, Bb = lo_d["o"]
            a_o = Aa.view(Aa.shape[0], H, hd).permute(1, 2, 0)
            o = o + scale * (torch.einsum("htk,hkr->htr", z, a_o) @ Bb.T)
        a = o.sum(0); h1 = h + a
        x2 = rms(h1, Wd["post_norm"])
        g, u = lin(x2, "gate"), lin(x2, "up")
        c = torch.nn.functional.silu(g) * u
        m = lin(c, "down")
        return dict(a=a, m=m, o=o, h=h1 + m)

    un = forward(lw, lo, lora.scale)
    merged_w = dict(lw)
    for name, (Aa, Bb) in lo.items():
        merged_w[name] = lw[name] + lora.scale * (Bb @ Aa)
    mg = forward(merged_w, {}, 0.0)
    print(f"layer 0, 8B f64, T={T}, H={H}, KV={KV}, hd={hd}, rms_eps={eps}")
    print(f"  adapter: r={lora.describe().get('r')} alpha={lora.describe().get('lora_alpha')} scale={lora.scale} modules={list(lo)}")
    for k in ("a", "m", "o", "h"):
        x, y = un[k], mg[k]
        gap = ((x - y).abs().max() / max(y.abs().max().item(), 1.0)).item()
        print(f"  {k}: max|unmerged-merged| = {(x-y).abs().max().item():.3e}  rel = {gap:.3e} "
              f"(|x|={x.abs().max().item():.3g})  gate 1e-12 -> {'PASS' if gap<=1e-12 else 'FAIL'}")
    # and the adapter actually moves the layer
    base = forward(lw, {}, 0.0)
    print(f"  adapter moves h_out by rel {((un['h']-base['h']).abs().max()/base['h'].abs().max()).item():.3e}")

if cmd == "corrupt":
    tok, p = tok_and_item("wvs_Q81")
    item, ro = p["item"], p["ro"]
    jp, jm = ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]
    taus = G.GateTaus(**json.loads((WB / "plans/stage1_8b_gaps.json").read_text())["taus"]["f32"]["tau"])
    print("8B float32 taus:", taus.as_dict())
    for lbl, corrupt in (("clean", None), ("0.1% MLP write at L15", (15, 1.001)),
                         ("0.1% MLP write at L21 (median of 32)", (21, 1.001))):
        t0 = time.time()
        src = SC.SafetensorsSource(SNAP, torch.float32)
        (out,) = SC.run_streamed(src, ro["prompt_ids"], j_plus=jp, j_minus=jm, scale_mlp_write=corrupt)
        g = G.check_capture(out, taus)
        print(f"  {lbl:34s} " + " ".join(f"{k}={v.rel/v.tau:8.3g}x tau" for k, v in g.items())
              + f"  all_ok={G.all_ok(g)}  ({time.time()-t0:.0f}s)")

if cmd == "parity":
    import eval_config as E, eval_lib as L, score_cohort as S
    from sca2_workbench.offload_hf import build_offloaded_hf
    tok, p = tok_and_item("wvs_Q81")
    t0 = time.time()
    model = build_offloaded_hf(SNAP, torch.float32, adapter_dir=str(AD), model_id=M)
    print(f"HF float32 model (one block resident) loaded in {time.time()-t0:.0f}s", flush=True)
    scores = []
    for code in p["codes"]:
        lp, n = S.sequence_logprob(model, tok, p["prompt_text"], f"{E.COMPLETION_PREFIX}{code}")
        scores.append(lp)
        print(f"  code {code}: logprob {lp:.6f} ({n} tok)  {time.time()-t0:.0f}s", flush=True)
    probs = L.stable_softmax(scores, E.OPTION_SCORE_TEMPERATURE)
    man = json.loads((WB / "exports/pair__llama31_8b__llama31_8b_usa__wvs_Q81.json").read_text())
    run_b = json.loads((WB / "exports" / man["runs"]["b"]).read_text())
    stored = run_b["readout"]["probs"]
    print("  paper-b probs :", {c: round(float(x), 8) for c, x in zip(p["codes"], probs)})
    print("  export B probs:", {c: round(v, 8) for c, v in stored.items()})
    gap = max(abs(float(x) - stored[c]) for c, x in zip(p["codes"], probs))
    print(f"  MAX |paperB - export| = {gap:.3e}  tau 1e-4 -> {'PASS' if gap <= 1e-4 else 'FAIL'}")
    print(f"  manifest recorded parity: {json.dumps(run_b['conservation'].get('relative', {}).get('checks', {}).get('paper_b_parity'))}")
