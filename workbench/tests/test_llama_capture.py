"""Real-model contract for the 3D views (SmolLM2-135M-Instruct from the local HF cache).

Each test pins one claim the viewer makes on screen:
  1. Our float64 decomposition IS the HF computation: with HF's three float32 casts removed,
     hidden states and logits agree to float64 round-off.
  2. The residual stream and the DLA close exactly, with and without the Quadrant-III clamp.
  3. Eq. 6 at the readout position equals the full teacher-forced Eq. 6.
  4. The clamp zeroes exactly the Quadrant-III products (cross-checked with hooks.clamp_quadrant_iii).
  5. An adapter loads for real: merged dW == (alpha/r) B A, MLP untouched, LoRA B nonzero.
     This guards the peft 0.21.2 float64 silent-zero load.
  6. Items whose codes do not split as prefix + one token (Q50: " 10") are refused.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

LC = pytest.importorskip("sca2_workbench.llama_capture")
from sca2_workbench import items as I  # noqa: E402
from sca2_workbench.hooks import clamp_quadrant_iii  # noqa: E402

MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"
ADAPTER = Path(__file__).resolve().parents[1] / "models" / "usa_e1"


def _cached(model_id: str) -> bool:
    root = Path.home() / ".cache" / "huggingface" / "hub" / ("models--" + model_id.replace("/", "--"))
    return any(root.glob("snapshots/*/model.safetensors"))


pytestmark = pytest.mark.skipif(not _cached(MODEL), reason=f"{MODEL} not in the local HF cache")


@pytest.fixture(scope="module")
def base():
    model, tok = LC.load_hf(MODEL)
    return model, tok, LC.weights_from_hf(model)


@pytest.fixture(scope="module")
def q57(base):
    _, tok, _ = base
    item = I.wvs_item("Q57")
    return item, I.readout_ids(tok, item)


def _run(W, item, ro, **kw):
    return LC.run(W, ro["prompt_ids"], j_plus=ro["code_token"][item.j_plus],
                  j_minus=ro["code_token"][item.j_minus], **kw)


def test_decomposition_is_the_hf_computation(base, q57):
    model, _, W = base
    item, ro = q57
    out = _run(W, item, ro)
    ref = LC.reference_check(model, ro["prompt_ids"], out)
    assert ref["hf64_hidden_max_rel_gap"] < 1e-12
    assert ref["hf64_logits_max_rel_gap"] < 1e-12
    # stock HF differs only by its float32 islands
    assert ref["hf_logits_max_rel_gap"] < 1e-5


@pytest.mark.parametrize("clamp", [False, True])
def test_residual_and_dla_close(base, q57, clamp):
    _, _, W = base
    item, ro = q57
    out = _run(W, item, ro, clamp_q3=clamp)
    assert out["residual_closure_inf"] < 1e-9
    assert out["head_closure_inf"] < 1e-9
    assert out["dla_gap"] < 1e-9
    # the running margin read from the final residual is the margin itself
    assert abs(out["running_margin"][-1].item() - out["margin"]) < 1e-9


def test_eq6_single_position_equals_teacher_forced(base, q57):
    model, tok, W = base
    item, ro = q57
    out = _run(W, item, ro)
    probs = LC.code_probs(out["logits_last"], ro["code_token"])
    comps = {c: tok(" " + c, add_special_tokens=False).input_ids for c in item.codes}
    base_ids = ro["prompt_ids"][: len(ro["prompt_ids"]) - len(ro["prefix_ids"])]
    tf = LC.teacher_forced_probs(model, base_ids, comps)
    assert max(abs(probs[c] - tf[c]) for c in probs) < 1e-5   # stock HF float32 floor
    assert abs(sum(probs.values()) - 1.0) < 1e-12


def test_clamp_zeroes_exactly_quadrant_iii(base, q57):
    _, _, W = base
    item, ro = q57
    out = _run(W, item, ro)
    layer = 7
    g, u, c = out["g_last"][layer], out["u_last"][layer], out["c_last"][layer]
    expected = clamp_quadrant_iii(g.tolist(), u.tolist(), eps=LC.EPS_Q3)
    q3 = (g < -LC.EPS_Q3) & (u < -LC.EPS_Q3)
    assert q3.any()
    assert all(expected[i] == 0.0 for i in torch.nonzero(q3).flatten().tolist())
    keep = ~q3
    assert torch.allclose(torch.tensor(expected, dtype=torch.float64)[keep], c[keep], atol=1e-12)
    assert int(out["q3_count"][layer, -1]) == int(q3.sum())


@pytest.mark.skipif(not (ADAPTER / "adapter_model.safetensors").exists(), reason="usa_e1 adapter not trained")
def test_adapter_merge_is_exact_and_attention_only(base):
    from safetensors.torch import load_file

    model, _, _ = base
    ft, _ = LC.load_hf(MODEL, str(ADAPTER))
    sd = load_file(str(ADAPTER / "adapter_model.safetensors"))
    cfg = json.loads((ADAPTER / "adapter_config.json").read_text())
    s = cfg["lora_alpha"] / cfg["r"]
    total = 0.0
    for l in range(model.config.num_hidden_layers):
        for p in ("q_proj", "k_proj", "v_proj", "o_proj"):
            pre = f"base_model.model.model.layers.{l}.self_attn.{p}"
            want = s * sd[pre + ".lora_B.weight"].double() @ sd[pre + ".lora_A.weight"].double()
            got = getattr(ft.model.layers[l].self_attn, p).weight - getattr(model.model.layers[l].self_attn, p).weight
            assert (got - want).abs().max().item() < 1e-12
            total += got.norm().item() ** 2
        for p in ("gate_proj", "up_proj", "down_proj"):
            assert torch.equal(getattr(ft.model.layers[l].mlp, p).weight, getattr(model.model.layers[l].mlp, p).weight)
    assert total ** 0.5 > 1e-3, "adapter merged as a no-op (LoRA B loaded as zero?)"


def test_multitoken_codes_are_refused(base):
    _, tok, _ = base
    with pytest.raises(ValueError):
        I.readout_ids(tok, I.wvs_item("Q50"))


def _damaged_adapter(tmp_path, *, drop_layer=None, config_patch=None):
    """Copy of the e1 adapter with one defect, for the guard tests."""
    import shutil

    from safetensors.torch import load_file, save_file

    d = tmp_path / "adapter"
    shutil.copytree(ADAPTER, d)
    if drop_layer is not None:
        sd = load_file(str(d / "adapter_model.safetensors"))
        sd = {k: v for k, v in sd.items() if f".layers.{drop_layer}." not in k}
        save_file(sd, str(d / "adapter_model.safetensors"))
    if config_patch:
        cfg = json.loads((d / "adapter_config.json").read_text())
        cfg.update(config_patch)
        (d / "adapter_config.json").write_text(json.dumps(cfg))
    return str(d)


@pytest.mark.parametrize("defect, match", [
    (dict(drop_layer=29), "missing from the adapter file"),
    (dict(config_patch={"base_model_name_or_path": "meta-llama/Llama-3.2-1B"}), "trained on"),
    (dict(config_patch={"bias": "all"}), "bias"),
    (dict(config_patch={"modules_to_save": ["lm_head"]}), "modules_to_save"),
])
def test_damaged_adapters_are_refused(tmp_path, defect, match):
    """A partial or mismatched adapter must not load as a quietly different model."""
    with pytest.raises(ValueError, match=match):
        LC.load_hf(MODEL, _damaged_adapter(tmp_path, **defect))
