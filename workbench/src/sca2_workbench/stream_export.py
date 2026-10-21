"""capture@1.1 ``run`` files from a streamed capture (``stream_capture.run_streamed``).

Same arrays, same names, same manifest blocks as ``export.capture_run``; the differences are the
ones the streaming forces, each stated in the manifest:

* ``reference`` is not ``llama_capture.reference_check`` (that needs the whole HF model). The
  ``logits_reference`` gate compares the last-position logits over the *whole vocabulary* with a
  float32 Hugging Face model that holds one block at a time (``offload_hf``); the Eq. 6 check is
  Paper B's own ``sequence_logprob`` softmax on that same model (``probs_teacher_forced_hf``).
* ``provenance.streaming`` records wall time and peak RSS of the pass.
"""

from __future__ import annotations

import hashlib
import platform
import time

import numpy as np
import torch

from sca2_workbench import export as EX
from sca2_workbench import gates as G
from sca2_workbench import items as I
from sca2_workbench import llama_capture as LC


def run_manifest(*, key: str, label: str, model_id: str, src, tok, item: I.Item, ro: dict,
                 plain: dict, clamped: dict, taus: G.GateTaus, hf_logits_last: torch.Tensor,
                 paper_b_probs: dict, parity_tau: float, stats: dict, chat_kwargs: dict,
                 adapter: dict | None = None) -> tuple:
    """Returns ``(manifest, BinWriter)`` for one (model, item) streamed capture.

    ``adapter`` (``LoraAdapter.describe()`` plus anything else to record) goes into
    ``model.adapter``; ``None`` for the base model."""
    ids = ro["prompt_ids"]
    probs = LC.code_probs(plain["logits_last"], ro["code_token"])
    probs_c = LC.code_probs(clamped["logits_last"], ro["code_token"])

    rel = {}
    rel.update(G.check_capture(plain, taus))
    rel.update(G.check_capture(clamped, taus, suffix="_clamped"))
    hf_scale = hf_logits_last.abs().max().item()
    ref_gap = (plain["logits_last"].double() - hf_logits_last.double()).abs().max().item()
    rel["logits_reference"] = G.logits_reference(ref_gap, hf_scale, taus.logits_reference)
    parity_gap = max(abs(probs[c] - paper_b_probs[c]) for c in probs)
    rel["paper_b_parity"] = G.Gate("paper_b_parity", parity_gap, 1.0,
                                   "probabilities are in [0, 1]: absolute", parity_tau)
    conservation = {
        "residual_closure_inf": plain["residual_closure_inf"],
        "head_closure_inf": plain["head_closure_inf"],
        "dla_gap": plain["dla_gap"],
        "dla_gap_clamped": clamped["dla_gap"],
        "residual_closure_inf_clamped": clamped["residual_closure_inf"],
        "eq6_teacher_forced_max_abs_gap": parity_gap,
        "hf_logits_max_abs_gap": ref_gap,
        "hf_logits_max_rel_gap": ref_gap / hf_scale,
        "hf_logits_scale": hf_scale,
        "thresholds": EX.THRESHOLDS,
        "legacy_absolute_applicable": False,
    }
    conservation["relative"] = G.as_manifest(rel, taus)
    conservation["relative"]["reference_key"] = "hf_logits_max_rel_gap"
    conservation["pass"] = G.all_ok(rel)

    b = EX.BinWriter()
    b.add("resid_norm", plain["resid_norm"], "||h^l_t||_2, residual entering layer l (l=L: final, pre-norm). (L+1, T)")
    b.add("attn_norm", plain["attn_norm"], "||a^l_t||_2, attention write of layer l. (L, T)")
    b.add("mlp_norm", plain["mlp_norm"], "||m^l_t||_2, MLP write of layer l. (L, T)")
    b.add("head_norm", plain["head_norm"], "||o^l_{h,t}||_2, write of head h (z_h W_O[:,h]^T). (L, H, T)")
    val, idx = plain["attn_topk_val"], plain["attn_topk_idx"]
    K = EX.TOPK
    if val.shape[-1] < K:                                     # T < K: pad as export._topk_attention
        pad = K - val.shape[-1]
        val = torch.cat([val, torch.zeros(*val.shape[:-1], pad, dtype=val.dtype)], -1)
        idx = torch.cat([idx, torch.zeros(*idx.shape[:-1], pad, dtype=idx.dtype)], -1)
    idx = torch.where(val > 0, idx, torch.full_like(idx, 65535))
    b.add("attn_topk_idx", idx.to(torch.int32).numpy().astype(np.uint16),
          f"key index of the top-{K} attention weights per (l,h,query); 65535 = none. (L,H,T,K)", np.uint16)
    b.add("attn_topk_val", val, "matching attention probabilities A^l_h[q,k]. (L,H,T,K)")
    b.add("attn_topk_mass", val.sum(-1), "sum of the stored top-k probabilities per row (1 = complete). (L,H,T)")
    b.add("q3_count", plain["q3_count"], "number of neurons with g~<-eps and u<-eps (Quadrant III). (L, T)")
    b.add("q3_write_norm", plain["q3_write_norm"], "||sum_{i in QIII} c_i W_down[:,i]||_2, the write Quadrant III makes. (L, T)")
    b.add("g_last", plain["g_last"], "g~^l_i = RMSNorm(h^{l+1/2}) W_gate[i]^T at the readout position. (L, F)")
    b.add("u_last", plain["u_last"], "u^l_i at the readout position. (L, F)")
    b.add("c_last", plain["c_last"], "c^l_i = SiLU(g~) u at the readout position (unclamped run). (L, F)")
    b.add("head_attr", plain["head_attr"], "DLA of head (l,h) to logit(j+)-logit(j-). (L, H)")
    b.add("neuron_attr", plain["neuron_attr"], "DLA of neuron (l,i) to logit(j+)-logit(j-). (L, F)")
    b.add("attn_attr", plain["attn_attr"], "sum_h head_attr[l]. (L,)")
    b.add("mlp_attr", plain["mlp_attr"], "sum_i neuron_attr[l]. (L,)")
    b.add("running_margin", plain["running_margin"], "h^l_t* . w: margin read from the residual entering layer l. (L+1,)")
    b.add("running_margin_clamped", clamped["running_margin"], "same, with the Quadrant-III clamp on during the pass. (L+1,)")
    b.add("head_attr_clamped", clamped["head_attr"], "head DLA in the clamped pass. (L, H)")
    b.add("mlp_attr_clamped", clamped["mlp_attr"], "MLP DLA per layer in the clamped pass. (L,)")

    manifest = {
        "schema": EX.SCHEMA, "kind": "run",
        "model": {"key": key, "label": label, "model_id": model_id, "adapter": adapter,
                  "n_layers": src.n_layers, "n_heads": src.n_heads, "n_kv_heads": src.n_kv,
                  "head_dim": src.head_dim, "d_model": src.d_model, "d_ffn": src.d_ffn,
                  "rms_eps": src.rms_eps, "rope_theta": src.rope_theta},
        "item": {"item_id": item.item_id, "kind": item.kind, "codes": list(item.codes),
                 "labels": list(item.labels), "j_plus": item.j_plus, "j_minus": item.j_minus,
                 "meta": item.meta},
        "tokens": [{"id": int(i), "text": tok.decode([i])} for i in ids],
        "segments": I.prompt_segments(tok, item, ro) if item.parts else None,
        "readout": {"position": len(ids) - 1, "code_token": ro["code_token"],
                    "prefix_tokens": [tok.decode([i]) for i in ro["prefix_ids"]],
                    "probs": probs, "probs_clamped": probs_c,
                    "probs_teacher_forced_hf": paper_b_probs,
                    "probs_teacher_forced_hf_source": "paper_b/score_cohort.py::sequence_logprob, "
                                                      "float32, softmax over the item's codes",
                    "margin": plain["margin"], "margin_clamped": clamped["margin"],
                    "embed_attr": plain["embed_attr"], "embed_attr_clamped": clamped["embed_attr"],
                    "rho_final": plain["rho_final"], "eps_q3": LC.EPS_Q3},
        "conservation": conservation,
        "arrays": b.meta,
        "provenance": {"prompt_sha256": hashlib.sha256(ro["formatted_prompt"].encode()).hexdigest(),
                       "tokenizer": model_id, "chat_template_kwargs": chat_kwargs,
                       "torch": torch.__version__, "python": platform.python_version(),
                       "compute_dtype": plain["dtype"], "stored_dtype": "float32",
                       "attention_storage": f"top-{K} per row + row mass",
                       "streaming": {"layer_at_a_time": True, **stats},
                       "git_head": EX._git_head(),
                       "wall_seconds": stats.get("wall_seconds"),
                       "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")},
    }
    return manifest, b


def pair_manifest(*, key_a: str, key_b: str, item_id: str, man_a: dict, man_b: dict, res: dict,
                  d_weight_head, d_weight_mlp, run_files: dict, retain_failed: bool = False) -> tuple:
    """capture@1.1 ``pair`` file from ``stream_capture.run_streamed_pair``.

    Same arrays and gate as ``export.export_pair``: the B - A norms come from the loop
    (``res["diffs"]``), the weight deltas from the LoRA alone (``lora_weight_delta``), the B - A
    of the readout attributions from the float64 passes, gated by ``export.d_attribution_gate``.
    Raises if the attributions do not sum to the B - A of the margin.
    """
    def attr(out, clamped):
        return {**{k: out[k] for k in ("head_attr", "mlp_attr", "embed_attr", "attn_attr")},
                "_clamped_attr": {k: clamped[k] for k in ("head_attr", "mlp_attr", "embed_attr")}}

    out_a, out_b = attr(res["a"], res["a_clamped"]), attr(res["b"], res["b_clamped"])
    if [t["id"] for t in man_a["tokens"]] != [t["id"] for t in man_b["tokens"]]:
        raise ValueError(f"{item_id}: token ids differ between {key_a} and {key_b}")
    ra, rb = man_a["readout"], man_b["readout"]
    d = res["diffs"]
    b = EX.BinWriter()
    b.add("d_resid_norm", d["d_resid_norm"], "||h^l_t(B) - h^l_t(A)||_2. (L+1, T)")
    b.add("d_attn_norm", d["d_attn_norm"], "||a^l_t(B) - a^l_t(A)||_2. (L, T)")
    b.add("d_mlp_norm", d["d_mlp_norm"], "||m^l_t(B) - m^l_t(A)||_2. (L, T)")
    b.add("d_head_norm", d["d_head_norm"], "||o^l_{h,t}(B) - o^l_{h,t}(A)||_2. (L, H, T)")
    b.add("d_weight_head", d_weight_head, "||W^B - W^A||_F per (l, h, [q,k,v,o]); k,v are per KV head, shared within the group. From (alpha/r) B A of the LoRA. (L, H, 4)")
    b.add("d_weight_mlp", d_weight_mlp, "||W^B - W^A||_F per (l, [gate,up,down]). (L, 3)")
    d_arr, d_embed, chk = EX.d_attribution_gate(out_a, out_b, ra["margin"], rb["margin"])
    d_arr_c, d_embed_c, chk_c = EX.d_attribution_gate(out_a, out_b, ra["margin_clamped"],
                                                      rb["margin_clamped"], clamped=True)
    b.add("d_head_attr", d_arr["head_attr"], "head_attr(B) - head_attr(A), float64 difference. (L, H)")
    b.add("d_mlp_attr", d_arr["mlp_attr"], "mlp_attr(B) - mlp_attr(A). (L,)")
    b.add("d_attn_attr", d_arr["attn_attr"], "attn_attr(B) - attn_attr(A) = sum_h d_head_attr. Not an extra term in the gate. (L,)")
    b.add("d_head_attr_clamped", d_arr_c["head_attr"], "head_attr_clamped(B) - head_attr_clamped(A). (L, H)")
    b.add("d_mlp_attr_clamped", d_arr_c["mlp_attr"], "mlp_attr_clamped(B) - mlp_attr_clamped(A). (L,)")
    attr_gate = EX.pair_conservation(chk, chk_c)
    if not attr_gate["pass"] and not retain_failed:
        raise AssertionError(f"{key_a} -> {key_b} {item_id}: B-A attributions do not sum to d_margin: {attr_gate}")
    pa, pb = ra["probs"], rb["probs"]
    pair = {
        "schema": EX.SCHEMA, "kind": "pair", "a": key_a, "b": key_b, "item_id": item_id,
        "runs": run_files,
        "d_probs": {c: pb[c] - pa[c] for c in pa},
        "d_margin": rb["margin"] - ra["margin"],
        "d_margin_clamped": rb["margin_clamped"] - ra["margin_clamped"],
        "d_embed_attr": d_embed,
        "d_embed_attr_clamped": d_embed_c,
        "conservation": attr_gate,
        "arrays": b.meta,
        "provenance": {"capture": "stream_capture.run_streamed_pair: A and B off one read of each "
                                  "layer, LoRA unmerged, float64",
                       "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")},
    }
    return pair, b
def prompt_pair_manifest(*, key_a: str, key_b: str, item_id: str, man_a: dict, man_b: dict,
                              out_a: dict, out_b: dict, out_a_clamped: dict, out_b_clamped: dict,
                              run_files: dict, profile_id: str, retain_failed: bool = False) -> tuple:
    """Signed readout DLA differences only: token positions in A and B are NOT aligned.

    Each arm uses its own final RMS denominator, exactly as its raw logit margin does.
    No common-rho rescaling, token-norm subtraction, or invented weight delta is valid here.
    The existing four pair-conservation gates apply unchanged, including stored-f32 sums.
    """
    for section, fields in (("item", ("item_id", "codes", "j_plus", "j_minus")),
                            ("readout", ("code_token", "prefix_tokens")),
                            ("model", ("model_id", "n_layers", "n_heads", "adapter"))):
        for field in fields:
            if man_a.get(section, {}).get(field) != man_b.get(section, {}).get(field):
                raise ValueError(f"{item_id}: incompatible readout {section}.{field}")

    def attr(out, clamped):
        return {**{k: out[k] for k in ("head_attr", "mlp_attr", "embed_attr", "attn_attr")},
                "_clamped_attr": {k: clamped[k] for k in ("head_attr", "mlp_attr", "embed_attr")}}
    a, b = attr(out_a, out_a_clamped), attr(out_b, out_b_clamped)
    for name in ("head_attr", "mlp_attr", "attn_attr"):
        if a[name].shape != b[name].shape:
            raise ValueError(f"{item_id}: incompatible readout shape {name}")
    ra, rb = man_a["readout"], man_b["readout"]
    d, embed, chk = EX.d_attribution_gate(a, b, ra["margin"], rb["margin"])
    dc, embed_c, chk_c = EX.d_attribution_gate(a, b, ra["margin_clamped"], rb["margin_clamped"], clamped=True)
    conservation = EX.pair_conservation(chk, chk_c)
    if not conservation["pass"] and not retain_failed:
        raise AssertionError(f"{key_a} -> {key_b} {item_id}: prompt attributions do not sum to d_margin: {conservation}")
    bw = EX.BinWriter()
    for name in ("head_attr", "mlp_attr", "attn_attr"):
        bw.add("d_" + name, d[name], f"Signed {name}(prompt B) - {name}(neutral A) at each arm's readout.")
    for name in ("head_attr", "mlp_attr"):
        bw.add("d_" + name + "_clamped", dc[name], f"Signed clamped {name}(B) - {name}(A).")
    pair = {
        "schema": EX.SCHEMA, "kind": "pair", "route": "prompt", "prompt_profile": profile_id,
        "a": key_a, "b": key_b, "item_id": item_id, "runs": run_files,
        "tokens": {"a": len(man_a["tokens"]), "b": len(man_b["tokens"])},
        "d_probs": {c: rb["probs"][c] - ra["probs"][c] for c in ra["probs"]},
        "d_margin": rb["margin"] - ra["margin"],
        "d_margin_clamped": rb["margin_clamped"] - ra["margin_clamped"],
        "d_embed_attr": embed, "d_embed_attr_clamped": embed_c,
        "conservation": conservation, "arrays": bw.meta,
        "provenance": {"capture": "prompt B minus neutral A; signed readout DLA only",
                       "readout_scale": "raw logit(j+) - logit(j-); each arm's own final RMS denominator",
                       "baseline_attribution_storage": "float32 widened to float64 before subtraction",
                       "unaligned_token_differences": "not defined; omitted",
                       "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")},
    }
    return pair, bw
