"""LoRA applied unmerged inside the streamed layer loop (SmolLM2-135M-Instruct + models/usa_e1).

The streamed capture never forms ``W + (alpha/r) B A``: every adapted projection is
``x W^T + (alpha/r) (x A^T) B^T``. These tests pin that this is the merged model:

* one layer, float64: unmerged == merged on every value the layer keeps (<= 1e-12 relative);
* the whole model: ``run_streamed_pair`` == ``llama_capture.run`` on the peft-merged float64
  weights (``load_hf``), for A (base) and B (base + adapter), and the in-loop B - A norms equal
  the differences of the in-memory stacks;
* the weight deltas from A and B alone (Gram form) == ``export._weight_delta`` on merged weights;
* the guards of ``llama_capture.check_adapter`` refuse what they refused inside ``load_hf``.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import torch

LC = pytest.importorskip("sca2_workbench.llama_capture")
SC = pytest.importorskip("sca2_workbench.stream_capture")
from sca2_workbench import export as EX  # noqa: E402
from sca2_workbench import items as I  # noqa: E402

MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"
ADAPTER = Path(__file__).resolve().parents[1] / "models" / "usa_e1"
GATE = 1e-12


def _snapshot(model_id: str):
    root = Path.home() / ".cache" / "huggingface" / "hub" / ("models--" + model_id.replace("/", "--"))
    hits = sorted(root.glob("snapshots/*/model.safetensors"))
    return hits[0].parent if hits else None


SNAP = _snapshot(MODEL)
pytestmark = pytest.mark.skipif(SNAP is None or not ADAPTER.exists(),
                                reason=f"{MODEL} or {ADAPTER} not available locally")


def _rel(a, b) -> float:
    a, b = torch.as_tensor(a).double(), torch.as_tensor(b).double()
    return ((a - b).abs().max() / max(b.abs().max().item(), 1.0)).item()


@pytest.fixture(scope="module")
def models():
    base, tok = LC.load_hf(MODEL)
    tuned, _ = LC.load_hf(MODEL, str(ADAPTER))
    return LC.weights_from_hf(base), LC.weights_from_hf(tuned), tok


def _item(tok, qid="Q81"):
    item = I.wvs_item(qid)
    ro = I.readout_ids(tok, item)
    return item, ro, ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]


# ---------------------------------------------------------------- guards
def _copy_adapter(tmp_path: Path, **cfg_changes) -> Path:
    d = tmp_path / "ad"
    shutil.copytree(ADAPTER, d)
    cfg = json.loads((d / "adapter_config.json").read_text())
    cfg.update(cfg_changes)
    (d / "adapter_config.json").write_text(json.dumps(cfg))
    return d


@pytest.mark.parametrize("change,msg", [
    ({"base_model_name_or_path": "other/model"}, "trained on"),
    ({"bias": "all"}, "bias"),
    ({"modules_to_save": ["lm_head"]}, "modules_to_save"),
])
def test_check_adapter_refuses_what_load_hf_refused(tmp_path, change, msg):
    with pytest.raises(ValueError, match=msg):
        LC.check_adapter(_copy_adapter(tmp_path, **change), MODEL)


@pytest.mark.parametrize("change,msg", [
    ({"use_dora": True}, "use_dora"),
    ({"use_rslora": True}, "use_rslora"),
    ({"rank_pattern": {"q_proj": 4}}, "rank_pattern"),
])
def test_stream_adapter_refuses_variants_it_does_not_implement(tmp_path, change, msg):
    with pytest.raises(ValueError, match=msg):
        SC.LoraAdapter(_copy_adapter(tmp_path, **change), MODEL)


def test_stream_adapter_reads_config_and_every_tensor():
    lo = SC.LoraAdapter(ADAPTER, MODEL)
    cfg = json.loads((ADAPTER / "adapter_config.json").read_text())
    assert lo.r == cfg["r"] and lo.alpha == cfg["lora_alpha"]
    assert lo.scale == cfg["lora_alpha"] / cfg["r"]
    assert sorted(lo.targets) == sorted(t.replace("_proj", "") for t in cfg["target_modules"])
    from safetensors.torch import load_file
    sd = load_file(str(ADAPTER / "adapter_model.safetensors"))
    got = lo.layer(3, torch.float64)
    A, B = got["q"]
    assert torch.equal(A, sd["base_model.model.model.layers.3.self_attn.q_proj.lora_A.weight"].double())
    assert torch.equal(B, sd["base_model.model.model.layers.3.self_attn.q_proj.lora_B.weight"].double())
    assert B.abs().max() > 0           # the trained B is not the zero init


# ---------------------------------------------------------------- one layer
@pytest.mark.parametrize("layer", [0, 17])
def test_one_layer_unmerged_equals_merged_float64(models, layer):
    _, _, tok = models
    item, ro, jp, jm = _item(tok)
    src = SC.SafetensorsSource(SNAP)
    lora = SC.LoraAdapter(ADAPTER, MODEL)
    lw, lo = src.layer(layer), lora.layer(layer, torch.float64)
    merged = dict(lw)
    for name, (A, B) in lo.items():
        merged[name] = lw[name] + lora.scale * (B @ A)
    gaps = SC.unmerged_vs_merged(src, ro["prompt_ids"], layer, lw, lo, merged, lora.scale,
                                 j_plus=jp, j_minus=jm)
    changed = gaps.pop("h_out (unmerged vs base)")
    worst = max(gaps, key=gaps.get)
    assert gaps[worst] <= GATE, f"layer {layer} {worst}: {gaps[worst]:.2e}"
    assert changed > 1e-6                                # the adapter changes the layer


# ---------------------------------------------------------------- whole model + pair
SAME = ["resid_norm", "attn_norm", "mlp_norm", "head_norm", "q3_write_norm", "g_last", "u_last",
        "c_last", "head_attr", "neuron_attr", "attn_attr", "mlp_attr", "running_margin"]
SCALARS = ["margin", "embed_attr", "rho_final", "attr_sum"]


def test_streamed_pair_equals_in_memory_merged(models):
    Wa, Wb, tok = models
    item, ro, jp, jm = _item(tok)
    ids = ro["prompt_ids"]
    src = SC.SafetensorsSource(SNAP)
    res = SC.run_streamed_pair(src, ids, SC.LoraAdapter(ADAPTER, MODEL), j_plus=jp, j_minus=jm,
                               full_logits=True)
    refs = {}
    for name, W in (("a", Wa), ("b", Wb)):
        for clamp in (False, True):
            ref = LC.run(W, ids, j_plus=jp, j_minus=jm, clamp_q3=clamp, keep_head_out=not clamp)
            got = res[name + ("_clamped" if clamp else "")]
            gaps = {k: _rel(got[k], ref[k]) for k in SAME}
            gaps.update({k: _rel(got[k], ref[k]) for k in SCALARS})
            gaps["logits_last"] = _rel(got["logits_last"], ref["logits_last"])
            worst = max(gaps, key=gaps.get)
            assert gaps[worst] <= GATE, f"{name} clamp={clamp} {worst}: {gaps[worst]:.2e}"
            assert torch.equal(got["q3_count"], ref["q3_count"])
            if not clamp:
                refs[name] = ref
    a, b, d = refs["a"], refs["b"], res["diffs"]
    expect = {"d_resid_norm": (b["_resid"] - a["_resid"]).norm(dim=-1),
              "d_attn_norm": (b["_attn"] - a["_attn"]).norm(dim=-1),
              "d_mlp_norm": (b["_mlp"] - a["_mlp"]).norm(dim=-1),
              "d_head_norm": (b["_head_out"] - a["_head_out"]).norm(dim=-1)}
    for k, v in expect.items():
        assert d[k].shape == v.shape, k
        assert _rel(d[k], v) <= GATE, f"{k}: {_rel(d[k], v):.2e}"
    assert res["b"]["margin"] != res["a"]["margin"]


def test_weight_delta_from_lora_equals_merged_difference(models):
    Wa, Wb, _ = models
    src = SC.SafetensorsSource(SNAP)
    dh, dm = SC.lora_weight_delta(SC.LoraAdapter(ADAPTER, MODEL), src)
    ref_h, ref_m = EX._weight_delta(Wa, Wb), EX._mlp_weight_delta(Wa, Wb)
    assert dh.shape == ref_h.shape and dm.shape == ref_m.shape
    # merged W^B - W^A carries the rounding of W^B (|W| ~ 1 vs |dW| ~ 1e-3), so the gate is
    # relative to the largest delta and loose by that ratio; the Gram form is exact otherwise.
    assert _rel(dh, ref_h) < 1e-9 and _rel(dm, ref_m) < 1e-9


# ---------------------------------------------------------------- Paper B reference with an adapter
def test_offloaded_peft_model_equals_resident_merged_model_float32():
    """The parity reference for B: HF + peft (unmerged LoRA, float32), one block resident at a time."""
    from sca2_workbench.offload_hf import build_offloaded_hf

    ref, tk = LC.load_hf(MODEL, str(ADAPTER), dtype=torch.float32)
    off = build_offloaded_hf(SNAP, torch.float32, adapter_dir=ADAPTER, model_id=MODEL)
    item, ro, _, _ = _item(tk)
    ids = torch.tensor([ro["prompt_ids"]])
    with torch.no_grad():
        want, got = ref(input_ids=ids).logits, off(input_ids=ids).logits
    assert _rel(got, want) < 1e-5
    base, _ = LC.load_hf(MODEL, dtype=torch.float32)
    with torch.no_grad():
        assert _rel(got, base(input_ids=ids).logits) > 1e-4         # the adapter is on
    # only the LoRA tensors stay resident between forwards
    resident = [n for n, p in off.named_parameters() if p.numel() > 0]
    assert resident and all("lora_" in n for n in resident)
