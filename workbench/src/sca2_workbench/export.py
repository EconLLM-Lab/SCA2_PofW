"""Write capture runs to disk for the 3D views (contract: ``spec/export_contract.md``).

Layout under ``workbench/exports/`` (gitignored, local only):

    index.json                                   every run and pair, with conservation results
    run__<model_key>__<item_id>.json / .bin      one model x one prompt
    pair__<a>__<b>__<item_id>.json / .bin        exact differences between two runs

Each ``.json`` manifest names its arrays: dtype, shape, byte offset into the ``.bin``, and a
plain description of the tensor slice. The ``.bin`` is little-endian and C-ordered.
Everything is computed in float64 and stored as float32. The one exception is the attention
top-k index (uint16).

CLI:  PYTHONPATH=src uv run python -m sca2_workbench.export --pair smol_inst smol_inst_usa_e3
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

import numpy as np
import torch

from sca2_workbench import gates as G
from sca2_workbench import items as I
from sca2_workbench import llama_capture as LC

WORKBENCH = Path(__file__).resolve().parents[2]
EXPORTS = WORKBENCH / "exports"
SCHEMA = "sca2-workbench/capture@1.1"
TOPK = 16

#: Thresholds of the legacy absolute gate set. The first two come from the brief. They stay in
#: the manifest because ``capture@1.1`` readers (the viewer) compare `conservation[k]` against
#: `conservation.thresholds[k]`. They are NOT the gate any more: below one ulp of the stream
#: they cannot be met (see `gates.py`), so the verdict is `conservation.relative.pass`.
THRESHOLDS = {"residual_closure_inf": 1e-3, "dla_gap": 1e-2, "hf64_logits_max_rel_gap": 1e-10}

#: The live gate set, chosen by the compute dtype. Calibrated in `plans/stage1_f32_gaps.md`.
TAUS = {torch.float64: G.TAUS_F64, torch.float32: G.TAUS_F32}

#: Pair gate: the B - A of the readout attributions sums to the B - A of the margin, relative
#: to |d_margin| + 1. Same value as the absolute gate it replaces (worst measured 7.4e-8).
PAIR_THRESHOLDS = {"d_attr_gap": G.TAUS_F64.pair_attribution}

MODELS = {
    "smol_base": {"model_id": "HuggingFaceTB/SmolLM2-135M", "adapter": None,
                  "label": "SmolLM2-135M (pretrained base)"},
    "smol_inst": {"model_id": "HuggingFaceTB/SmolLM2-135M-Instruct", "adapter": None,
                  "label": "SmolLM2-135M-Instruct"},
    "smol_inst_usa_e1": {"model_id": "HuggingFaceTB/SmolLM2-135M-Instruct",
                         "adapter": "models/usa_e1",
                         "label": "Instruct + USA DPO LoRA (1 epoch, paper recipe)"},
    "smol_inst_usa_e3": {"model_id": "HuggingFaceTB/SmolLM2-135M-Instruct",
                         "adapter": "models/usa_e3",
                         "label": "Instruct + USA DPO LoRA (3 epochs)"},
}
#: The base model has no chat template. Same vocabulary (checked), so every model formats
#: prompts with the Instruct tokenizer, and the token ids are identical across a pair.
TOKENIZER_ID = "HuggingFaceTB/SmolLM2-135M-Instruct"

DEFAULT_ITEMS = ["wvs_Q57", "wvs_Q43", "wvs_Q81", "bank_USA_00023ac74dac"]


def item_from_id(item_id: str) -> I.Item:
    if item_id.startswith("wvs_"):
        return I.wvs_item(item_id[4:])
    if item_id.startswith("bank_"):
        _, country, triplet = item_id.split("_", 2)
        return I.bank_forced_choice(country, triplet)
    raise ValueError(item_id)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_head() -> str | None:
    try:
        return subprocess.run(["git", "-C", str(WORKBENCH), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


class BinWriter:
    """Append numpy arrays to one buffer and record where each one landed."""

    def __init__(self):
        self.parts, self.meta, self.offset = [], {}, 0

    def add(self, name: str, array, desc: str, dtype=np.float32):
        if isinstance(array, torch.Tensor):
            array = array.detach().cpu().numpy()
        a = np.ascontiguousarray(np.asarray(array), dtype=dtype)
        pad = (-self.offset) % 8
        if pad:
            self.parts.append(b"\0" * pad)
            self.offset += pad
        raw = a.astype(a.dtype.newbyteorder("<"), copy=False).tobytes(order="C")
        self.meta[name] = {"dtype": np.dtype(dtype).name, "shape": list(a.shape),
                           "offset": self.offset, "nbytes": len(raw), "desc": desc}
        self.parts.append(raw)
        self.offset += len(raw)

    def write(self, path: Path):
        path.write_bytes(b"".join(self.parts))


def _topk_attention(probs: torch.Tensor, k: int):
    """Top-k keys per (layer, head, query). Returns idx (uint16, 65535 = padding), val, mass."""
    L, H, T, _ = probs.shape
    kk = min(k, T)
    val, idx = probs.topk(kk, dim=-1)
    if kk < k:
        val = torch.cat([val, torch.zeros(L, H, T, k - kk, dtype=val.dtype)], -1)
        idx = torch.cat([idx, torch.full((L, H, T, k - kk), 65535)], -1)
    # causal rows have fewer than k nonzero keys; mark zero-weight slots as padding
    idx = torch.where(val > 0, idx, torch.full_like(idx, 65535))
    return idx.to(torch.int32).numpy().astype(np.uint16), val, val.sum(-1)


class Session:
    """Loads each model once and runs every item through it.

    ``dtype`` is the capture mode: float64 (default, every 135M export) or float32 (models whose
    float64 copy does not fit). It selects the gate set too -- the two are calibrated separately
    in ``plans/stage1_f32_gaps.md``.
    """

    def __init__(self, dtype=torch.float64):
        from transformers import AutoTokenizer  # noqa: PLC0415
        if dtype not in TAUS:
            raise ValueError(f"capture dtype must be one of {list(TAUS)}; got {dtype}")
        self.dtype = dtype
        self.taus = TAUS[dtype]
        self.tok = AutoTokenizer.from_pretrained(TOKENIZER_ID)
        self._loaded: dict = {}

    def model(self, key: str):
        if key not in self._loaded:
            spec = MODELS[key]
            adapter = str(WORKBENCH / spec["adapter"]) if spec["adapter"] else None
            if adapter and not Path(adapter).exists():
                raise FileNotFoundError(f"{key}: adapter dir {adapter} is missing")
            hf, _ = LC.load_hf(spec["model_id"], adapter, dtype=self.dtype)
            self._loaded[key] = (hf, LC.weights_from_hf(hf, dtype=self.dtype), adapter)
        return self._loaded[key]


def capture_run(sess: Session, key: str, item: I.Item, keep_head_out: bool = False) -> tuple:
    """Run, check and serialise one (model, item). Returns (manifest, bin, raw capture)."""
    hf, W, adapter = sess.model(key)
    ro = I.readout_ids(sess.tok, item)
    ids = ro["prompt_ids"]
    jp, jm = ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]
    t0 = time.time()
    out = LC.run(W, ids, j_plus=jp, j_minus=jm, keep_head_out=keep_head_out)
    clamped = LC.run(W, ids, j_plus=jp, j_minus=jm, clamp_q3=True)
    ref = LC.reference_check(hf, ids, out)
    comps = {c: sess.tok(" " + c, add_special_tokens=False).input_ids for c in item.codes}
    base_ids = ids[: len(ids) - len(ro["prefix_ids"])]
    tf = LC.teacher_forced_probs(hf, base_ids, comps)
    probs = LC.code_probs(out["logits_last"], ro["code_token"])
    probs_c = LC.code_probs(clamped["logits_last"], ro["code_token"])
    wall = time.time() - t0

    conservation = {
        "residual_closure_inf": out["residual_closure_inf"],
        "head_closure_inf": out["head_closure_inf"],
        "dla_gap": out["dla_gap"],
        "dla_gap_clamped": clamped["dla_gap"],
        "residual_closure_inf_clamped": clamped["residual_closure_inf"],
        "eq6_teacher_forced_max_abs_gap": max(abs(probs[c] - tf[c]) for c in probs),
        **ref,
        "thresholds": THRESHOLDS,
        "legacy_absolute_applicable": sess.dtype == torch.float64,
    }
    # The live gate set (``gates.py``): every check is |error| / scale <= tau, with the scale
    # stated per check. The float64 report above is kept for capture@1.1 readers; the verdict is
    # this block, because an absolute threshold below one ulp of the stream cannot be met.
    rel = {}
    rel.update(G.check_capture(out, sess.taus))
    rel.update(G.check_capture(clamped, sess.taus, suffix="_clamped"))
    # The reference gap is already relative (to the largest reference logit); name its scale.
    # float64: HF with its three float32 casts removed (the cast-free pass IS our computation).
    # float32: HF as shipped -- at that dtype its casts are no-ops, so both are the same gap.
    ref_abs = ref["hf64_logits_max_abs_gap"] if sess.dtype == torch.float64 else ref["hf_logits_max_abs_gap"]
    rel["logits_reference"] = G.logits_reference(ref_abs, ref["hf_logits_scale"],
                                                 sess.taus.logits_reference)
    conservation["relative"] = G.as_manifest(rel, sess.taus)
    conservation["relative"]["reference_key"] = (
        "hf64_logits_max_rel_gap" if sess.dtype == torch.float64 else "hf_logits_max_rel_gap")
    conservation["pass"] = G.all_ok(rel)

    b = BinWriter()
    b.add("resid_norm", out["resid_norm"], "||h^l_t||_2, residual entering layer l (l=L: final, pre-norm). (L+1, T)")
    b.add("attn_norm", out["attn_norm"], "||a^l_t||_2, attention write of layer l. (L, T)")
    b.add("mlp_norm", out["mlp_norm"], "||m^l_t||_2, MLP write of layer l. (L, T)")
    b.add("head_norm", out["head_norm"], "||o^l_{h,t}||_2, write of head h (z_h W_O[:,h]^T). (L, H, T)")
    idx, val, mass = _topk_attention(out["attn_probs"], TOPK)
    b.add("attn_topk_idx", idx, f"key index of the top-{TOPK} attention weights per (l,h,query); 65535 = none. (L,H,T,K)", np.uint16)
    b.add("attn_topk_val", val, "matching attention probabilities A^l_h[q,k]. (L,H,T,K)")
    b.add("attn_topk_mass", mass, "sum of the stored top-k probabilities per row (1 = complete). (L,H,T)")
    b.add("q3_count", out["q3_count"], "number of neurons with g~<-eps and u<-eps (Quadrant III). (L, T)")
    b.add("q3_write_norm", out["q3_write_norm"], "||sum_{i in QIII} c_i W_down[:,i]||_2, the write Quadrant III makes. (L, T)")
    b.add("g_last", out["g_last"], "g~^l_i = RMSNorm(h^{l+1/2}) W_gate[i]^T at the readout position. (L, F)")
    b.add("u_last", out["u_last"], "u^l_i at the readout position. (L, F)")
    b.add("c_last", out["c_last"], "c^l_i = SiLU(g~) u at the readout position (unclamped run). (L, F)")
    b.add("head_attr", out["head_attr"], "DLA of head (l,h) to logit(j+)-logit(j-). (L, H)")
    b.add("neuron_attr", out["neuron_attr"], "DLA of neuron (l,i) to logit(j+)-logit(j-). (L, F)")
    b.add("attn_attr", out["attn_attr"], "sum_h head_attr[l]. (L,)")
    b.add("mlp_attr", out["mlp_attr"], "sum_i neuron_attr[l]. (L,)")
    b.add("running_margin", out["running_margin"], "h^l_t* . w: margin read from the residual entering layer l. (L+1,)")
    b.add("running_margin_clamped", clamped["running_margin"], "same, with the Quadrant-III clamp on during the pass. (L+1,)")
    b.add("head_attr_clamped", clamped["head_attr"], "head DLA in the clamped pass. (L, H)")
    b.add("mlp_attr_clamped", clamped["mlp_attr"], "MLP DLA per layer in the clamped pass. (L,)")

    segments = I.prompt_segments(sess.tok, item, ro) if item.parts else None   # null for ad-hoc prompts
    out["_clamped_attr"] = {k: clamped[k] for k in ("head_attr", "mlp_attr", "embed_attr")}

    spec = MODELS[key]
    item_split = None   # for a bank item under an adapter: was this scenario in its training split?
    if adapter and item.kind == "bank":
        log = json.loads((Path(adapter) / "train_log.json").read_text())
        item_split = "heldout" if item.meta["triplet_id"] in set(log["heldout_triplet_ids"]) else "train"
    manifest = {
        "schema": SCHEMA,
        "kind": "run",
        "model": {"key": key, "label": spec["label"], "model_id": spec["model_id"],
                  "adapter": ({"dir": spec["adapter"],
                               "sha256": _sha256(Path(adapter) / "adapter_model.safetensors"),
                               "item_split": item_split}
                              if adapter else None),
                  "n_layers": W.n_layers, "n_heads": W.n_heads, "n_kv_heads": W.n_kv,
                  "head_dim": W.head_dim, "d_model": W.d_model, "d_ffn": W.d_ffn,
                  "rms_eps": W.rms_eps, "rope_theta": W.rope_theta},
        "item": {"item_id": item.item_id, "kind": item.kind, "codes": list(item.codes),
                 "labels": list(item.labels), "j_plus": item.j_plus, "j_minus": item.j_minus,
                 "meta": item.meta},
        "tokens": [{"id": int(i), "text": sess.tok.decode([i])} for i in ids],
        "segments": segments,
        "readout": {"position": len(ids) - 1, "code_token": ro["code_token"],
                    "prefix_tokens": [sess.tok.decode([i]) for i in ro["prefix_ids"]],
                    "probs": probs, "probs_clamped": probs_c,
                    "probs_teacher_forced_hf": tf,
                    "margin": out["margin"], "margin_clamped": clamped["margin"],
                    "embed_attr": out["embed_attr"], "embed_attr_clamped": clamped["embed_attr"],
                    "rho_final": out["rho_final"], "eps_q3": LC.EPS_Q3},
        "conservation": conservation,
        "arrays": b.meta,
        "provenance": {"prompt_sha256": hashlib.sha256(ro["formatted_prompt"].encode()).hexdigest(),
                       "tokenizer": TOKENIZER_ID, "git_head": _git_head(),
                       "torch": torch.__version__, "python": platform.python_version(),
                       "compute_dtype": str(sess.dtype).replace("torch.", ""), "stored_dtype": "float32",
                       "attention_storage": f"top-{TOPK} per row + row mass",
                       "wall_seconds": round(wall, 2),
                       "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")},
    }
    return manifest, b, out


def _write(stem: str, manifest: dict, b: BinWriter):
    EXPORTS.mkdir(parents=True, exist_ok=True)
    manifest["bin"] = f"{stem}.bin"
    b.write(EXPORTS / f"{stem}.bin")
    (EXPORTS / f"{stem}.json").write_text(json.dumps(manifest, indent=1))


def _weight_delta(Wa: LC.LlamaWeights, Wb: LC.LlamaWeights) -> np.ndarray:
    """||W^B - W^A||_F per (layer, head, projection q,k,v,o). k and v belong to a KV head.
    Every query head in that KV group gets the same k/v value."""
    L, H, hd, rep = Wa.n_layers, Wa.n_heads, Wa.head_dim, Wa.n_heads // Wa.n_kv
    out = np.zeros((L, H, 4))
    for l, (la, lb) in enumerate(zip(Wa.layers, Wb.layers)):
        for h in range(H):
            kv = h // rep
            out[l, h, 0] = (lb["q"][h*hd:(h+1)*hd] - la["q"][h*hd:(h+1)*hd]).norm()
            out[l, h, 1] = (lb["k"][kv*hd:(kv+1)*hd] - la["k"][kv*hd:(kv+1)*hd]).norm()
            out[l, h, 2] = (lb["v"][kv*hd:(kv+1)*hd] - la["v"][kv*hd:(kv+1)*hd]).norm()
            out[l, h, 3] = (lb["o"][:, h*hd:(h+1)*hd] - la["o"][:, h*hd:(h+1)*hd]).norm()
    return out


def _mlp_weight_delta(Wa: LC.LlamaWeights, Wb: LC.LlamaWeights) -> np.ndarray:
    return np.array([[(lb[k] - la[k]).norm().item() for k in ("gate", "up", "down")]
                     for la, lb in zip(Wa.layers, Wb.layers)])


def d_attribution_gate(out_a: dict, out_b: dict, margin_a: float, margin_b: float, clamped: bool = False):
    """B - A of the readout attributions, and the gate that they sum to B - A of the margin.

    Differences are taken in float64 from the float64 passes. Returns ``(arrays, scalar, check)``:
    the float32 arrays to store, the float64 ``d_embed_attr``, and the gap in two forms. ``gap_f64``
    sums the float64 differences. ``gap_f32`` sums the stored float32 arrays, which is what a
    viewer can add up. Both must be below ``PAIR_THRESHOLDS["d_attr_gap"]``.
    """
    a, b = (out_a["_clamped_attr"], out_b["_clamped_attr"]) if clamped else (out_a, out_b)
    d_head = b["head_attr"] - a["head_attr"]                                   # (L, H) float64
    d_mlp = b["mlp_attr"] - a["mlp_attr"]                                      # (L,)
    d_embed = float(b["embed_attr"] - a["embed_attr"])
    d_margin = margin_b - margin_a
    gap_f64 = abs(d_head.sum().item() + d_mlp.sum().item() + d_embed - d_margin)
    arrays = {"head_attr": d_head.to(torch.float32), "mlp_attr": d_mlp.to(torch.float32)}
    if not clamped:    # attn_attr is a run array only for the unclamped pass
        arrays["attn_attr"] = (b["attn_attr"] - a["attn_attr"]).to(torch.float32)
    gap_f32 = abs(arrays["head_attr"].double().sum().item() + arrays["mlp_attr"].double().sum().item()
                  + d_embed - d_margin)
    tau = PAIR_THRESHOLDS["d_attr_gap"]
    gates = {"gap_f64": G.pair_attribution(d_margin, gap_f64, tau),
             "gap_f32": G.pair_attribution(d_margin, gap_f32, tau)}
    return arrays, d_embed, {"gap_f64": gap_f64, "gap_f32": gap_f32,
                             "scale": abs(d_margin) + 1.0, "tau": tau,
                             "relative": {k: g.as_dict() for k, g in gates.items()},
                             "pass": all(g.ok for g in gates.values())}


def pair_conservation(chk: dict, chk_c: dict) -> dict:
    """Canonical pair conservation block with four live relative checks."""
    checks = {
        "d_attr_gap": chk["relative"]["gap_f64"],
        "d_attr_gap_float32": chk["relative"]["gap_f32"],
        "d_attr_gap_clamped": chk_c["relative"]["gap_f64"],
        "d_attr_gap_float32_clamped": chk_c["relative"]["gap_f32"],
    }
    passed = all(g["pass"] for g in checks.values())
    return {
        "d_attr_gap": chk["gap_f64"],
        "d_attr_gap_float32": chk["gap_f32"],
        "d_attr_gap_clamped": chk_c["gap_f64"],
        "d_attr_gap_float32_clamped": chk_c["gap_f32"],
        "thresholds": PAIR_THRESHOLDS,
        "relative": {"taus": {"pair_attribution": PAIR_THRESHOLDS["d_attr_gap"]},
                     "checks": checks, "pass": passed},
        "pass": passed,
    }


def export_pair(key_a: str, key_b: str, item_ids: list) -> list:
    sess = Session()
    written = []
    for item_id in item_ids:
        item = item_from_id(item_id)
        man_a, bin_a, out_a = capture_run(sess, key_a, item, keep_head_out=True)
        Wa = sess.model(key_a)[1]
        _write(f"run__{key_a}__{item_id}", man_a, bin_a)
        man_b, bin_b, out_b = capture_run(sess, key_b, item, keep_head_out=True)
        Wb = sess.model(key_b)[1]
        _write(f"run__{key_b}__{item_id}", man_b, bin_b)
        if [t["id"] for t in man_a["tokens"]] != [t["id"] for t in man_b["tokens"]]:
            raise ValueError(f"{item_id}: token ids differ between {key_a} and {key_b}")

        b = BinWriter()
        b.add("d_resid_norm", (out_b["_resid"] - out_a["_resid"]).norm(dim=-1), "||h^l_t(B) - h^l_t(A)||_2. (L+1, T)")
        b.add("d_attn_norm", (out_b["_attn"] - out_a["_attn"]).norm(dim=-1), "||a^l_t(B) - a^l_t(A)||_2. (L, T)")
        b.add("d_mlp_norm", (out_b["_mlp"] - out_a["_mlp"]).norm(dim=-1), "||m^l_t(B) - m^l_t(A)||_2. (L, T)")
        b.add("d_head_norm", (out_b["_head_out"] - out_a["_head_out"]).norm(dim=-1), "||o^l_{h,t}(B) - o^l_{h,t}(A)||_2. (L, H, T)")
        b.add("d_weight_head", _weight_delta(Wa, Wb), "||W^B - W^A||_F per (l, h, [q,k,v,o]); k,v are per KV head, shared within the group. (L, H, 4)")
        b.add("d_weight_mlp", _mlp_weight_delta(Wa, Wb), "||W^B - W^A||_F per (l, [gate,up,down]). (L, 3)")
        ra, rb = man_a["readout"], man_b["readout"]
        d_arr, d_embed, chk = d_attribution_gate(out_a, out_b, ra["margin"], rb["margin"])
        d_arr_c, d_embed_c, chk_c = d_attribution_gate(out_a, out_b, ra["margin_clamped"], rb["margin_clamped"], clamped=True)
        b.add("d_head_attr", d_arr["head_attr"], "head_attr(B) - head_attr(A), float64 difference. (L, H)")
        b.add("d_mlp_attr", d_arr["mlp_attr"], "mlp_attr(B) - mlp_attr(A). (L,)")
        b.add("d_attn_attr", d_arr["attn_attr"], "attn_attr(B) - attn_attr(A) = sum_h d_head_attr. Not an extra term in the gate. (L,)")
        b.add("d_head_attr_clamped", d_arr_c["head_attr"], "head_attr_clamped(B) - head_attr_clamped(A). (L, H)")
        b.add("d_mlp_attr_clamped", d_arr_c["mlp_attr"], "mlp_attr_clamped(B) - mlp_attr_clamped(A). (L,)")
        attr_gate = pair_conservation(chk, chk_c)
        if not attr_gate["pass"]:
            raise AssertionError(f"{key_a} -> {key_b} {item_id}: B-A attributions do not sum to d_margin: {attr_gate}")
        pa, pb = ra["probs"], rb["probs"]
        pair = {
            "schema": SCHEMA, "kind": "pair", "a": key_a, "b": key_b, "item_id": item_id,
            "runs": {"a": f"run__{key_a}__{item_id}.json", "b": f"run__{key_b}__{item_id}.json"},
            "d_probs": {c: pb[c] - pa[c] for c in pa},
            "d_margin": rb["margin"] - ra["margin"],
            "d_margin_clamped": rb["margin_clamped"] - ra["margin_clamped"],
            "d_embed_attr": d_embed,
            "d_embed_attr_clamped": d_embed_c,
            "conservation": attr_gate,
            "arrays": b.meta,
        }
        _write(f"pair__{key_a}__{key_b}__{item_id}", pair, b)
        written.append((man_a, man_b, pair))
        print(f"{item_id}: A pass={man_a['conservation']['pass']} B pass={man_b['conservation']['pass']} "
              f"margin {man_a['readout']['margin']:+.3f} -> {man_b['readout']['margin']:+.3f}")
        del out_a, out_b
    rebuild_index()
    return written


def rebuild_index():
    runs, pairs = [], []
    models = dict(MODELS)        # plus models exported by other paths (the streamed 8B runs)
    for path in sorted(EXPORTS.glob("*.json")):
        if path.name == "index.json":
            continue
        m = json.loads(path.read_text())
        if m.get("kind") == "run":
            ad = m["model"].get("adapter")
            models.setdefault(m["model"]["key"], {"model_id": m["model"]["model_id"],
                                                  "adapter": ad.get("dir") if ad else None,
                                                  "label": m["model"]["label"]})
            runs.append({"file": path.name, "model": m["model"]["key"], "label": m["model"]["label"],
                         "item_id": m["item"]["item_id"], "T": len(m["tokens"]),
                         "pass": m["conservation"]["pass"], "margin": m["readout"]["margin"],
                         "probs": m["readout"]["probs"]})
        elif m.get("kind") == "pair":
            pairs.append({"file": path.name, "a": m["a"], "b": m["b"], "item_id": m["item_id"],
                          "d_margin": m["d_margin"]})
    (EXPORTS / "index.json").write_text(json.dumps(
        {"schema": SCHEMA, "models": models, "runs": runs, "pairs": pairs}, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", nargs=2, metavar=("A", "B"), required=True, choices=list(MODELS))
    ap.add_argument("--items", nargs="*", default=DEFAULT_ITEMS)
    args = ap.parse_args()
    torch.set_num_threads(max(1, torch.get_num_threads()))
    export_pair(args.pair[0], args.pair[1], args.items)


if __name__ == "__main__":
    main()
