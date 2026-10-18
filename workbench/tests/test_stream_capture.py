"""The streamed capture IS the in-memory capture (SmolLM2-135M-Instruct, float64).

``stream_capture.run_streamed`` reads one decoder layer at a time from the safetensors file.
``llama_capture.run`` holds the whole float64 model. On the same ids they must agree on every
array the export stores. The gap is reported relative to the largest |entry| of the array
(floored at 1): the 135M residual stream carries a massive activation of ~2.6e4, where one
float64 ulp is already 3.6e-12, so a bare absolute 1e-12 is below representation error there.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import torch

LC = pytest.importorskip("sca2_workbench.llama_capture")
SC = pytest.importorskip("sca2_workbench.stream_capture")
from sca2_workbench import items as I  # noqa: E402

MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"
GATE = 1e-12


def _snapshot(model_id: str):
    root = Path.home() / ".cache" / "huggingface" / "hub" / ("models--" + model_id.replace("/", "--"))
    hits = sorted(root.glob("snapshots/*/model.safetensors"))
    return hits[0].parent if hits else None


SNAP = _snapshot(MODEL)
pytestmark = pytest.mark.skipif(SNAP is None, reason=f"{MODEL} not in the local HF cache")


def _rel(a: torch.Tensor, b: torch.Tensor) -> float:
    a, b = a.double(), b.double()
    return ((a - b).abs().max() / max(b.abs().max().item(), 1.0)).item()


@pytest.fixture(scope="module")
def base():
    model, tok = LC.load_hf(MODEL)
    return LC.weights_from_hf(model), tok


#: streamed key -> in-memory key, for every array the export stores.
SAME_NAME = ["resid_norm", "attn_norm", "mlp_norm", "head_norm", "q3_write_norm", "g_last",
             "u_last", "c_last", "head_attr", "neuron_attr", "attn_attr", "mlp_attr",
             "running_margin"]
SCALARS = ["margin", "embed_attr", "rho_final", "attr_sum", "residual_scale_inf", "attn_scale_inf"]


@pytest.mark.parametrize("qid", ["Q57", "Q81"])
def test_streamed_capture_equals_in_memory_capture(base, qid):
    W, tok = base
    item = I.wvs_item(qid)
    ro = I.readout_ids(tok, item)
    jp, jm = ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]
    src = SC.SafetensorsSource(SNAP)
    plain, clamped = SC.run_streamed(src, ro["prompt_ids"], j_plus=jp, j_minus=jm,
                                     clamps=(False, True), keep_resid=True)
    for got, clamp in ((plain, False), (clamped, True)):
        ref = LC.run(W, ro["prompt_ids"], j_plus=jp, j_minus=jm, clamp_q3=clamp)
        gaps = {k: _rel(got[k], ref[k]) for k in SAME_NAME}
        gaps.update({k: _rel(torch.tensor(got[k]), torch.tensor(ref[k])) for k in SCALARS})
        gaps["resid(all layers, all positions)"] = _rel(got["_resid"], ref["_resid"])
        gaps["attn_topk_val"] = _rel(got["attn_topk_val"], ref["attn_probs"].topk(SC.TOPK, -1)[0])
        worst = max(gaps, key=gaps.get)
        assert gaps[worst] <= GATE, f"clamp={clamp} {worst}: {gaps[worst]:.2e}"
        # discrete outputs are equal, not close
        assert torch.equal(got["q3_count"], ref["q3_count"])
        assert torch.equal(got["attn_topk_idx"], ref["attn_probs"].topk(SC.TOPK, -1)[1])
        # code logits agree with the full-vocabulary logits of the in-memory pass
        assert _rel(got["code_logits"], ref["logits_last"][[jp, jm]]) <= GATE
        # and the streamed pass closes on its own terms
        assert got["residual_closure_inf"] / got["residual_scale_inf"] < 1e-13
        assert got["dla_gap"] / (abs(got["margin"]) + 1) < 1e-12


def test_full_vocabulary_logits_are_chunked_and_exact(base):
    W, tok = base
    item = I.wvs_item("Q57")
    ro = I.readout_ids(tok, item)
    jp, jm = ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]
    src = SC.SafetensorsSource(SNAP)
    (got,) = SC.run_streamed(src, ro["prompt_ids"], j_plus=jp, j_minus=jm,
                             full_logits=True)
    assert src._handles == {}  # every layer and the chunked unembedding release their mmap handles
    ref = LC.run(W, ro["prompt_ids"], j_plus=jp, j_minus=jm)
    assert got["logits_last"].shape == ref["logits_last"].shape
    assert _rel(got["logits_last"], ref["logits_last"]) <= GATE


def test_float32_stream_stays_float32_and_close(base):
    W, tok = base
    item = I.wvs_item("Q57")
    ro = I.readout_ids(tok, item)
    jp, jm = ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]
    (f32,) = SC.run_streamed(SC.SafetensorsSource(SNAP, torch.float32), ro["prompt_ids"],
                             j_plus=jp, j_minus=jm)
    ref = LC.run(W, ro["prompt_ids"], j_plus=jp, j_minus=jm)
    assert f32["resid_norm"].dtype == torch.float32 and f32["dtype"] == "float32"
    assert _rel(f32["head_attr"], ref["head_attr"]) < 1e-3
    assert abs(f32["margin"] - ref["margin"]) / (abs(ref["margin"]) + 1) < 1e-3


def test_the_source_reads_only_what_it_is_asked_for():
    src = SC.SafetensorsSource(SNAP)
    assert src.embed_rows([5, 5, 7]).shape == (3, src.d_model)       # prompt rows, not the table
    assert src.unembed_rows([3, 4]).shape == (2, src.d_model)        # code rows, not the table
    assert src._unembed_name == "model.embed_tokens.weight"          # 135M ties its embeddings
    assert set(src.layer(0)) == {"in_norm", "post_norm", "q", "k", "v", "o", "gate", "up", "down"}
