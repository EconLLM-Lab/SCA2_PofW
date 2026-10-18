"""The block-at-a-time HF model is the HF model (SmolLM2-135M-Instruct, float32)."""

from __future__ import annotations

from pathlib import Path

import pytest
import torch

pytest.importorskip("sca2_workbench.stream_capture")
from sca2_workbench.offload_hf import build_offloaded_hf  # noqa: E402

MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"


def _snapshot():
    root = Path.home() / ".cache" / "huggingface" / "hub" / ("models--" + MODEL.replace("/", "--"))
    hits = sorted(root.glob("snapshots/*/model.safetensors"))
    return hits[0].parent if hits else None


SNAP = _snapshot()
pytestmark = pytest.mark.skipif(SNAP is None, reason=f"{MODEL} not in the local HF cache")


def test_offloaded_logits_equal_the_resident_model_and_storage_is_released():
    from transformers import AutoModelForCausalLM  # noqa: PLC0415

    resident = AutoModelForCausalLM.from_pretrained(SNAP, dtype=torch.float32,
                                                    attn_implementation="eager").eval()
    offloaded = build_offloaded_hf(SNAP, torch.float32)
    ids = torch.tensor([[1, 5, 77, 1032, 9, 400, 2, 33]])
    with torch.no_grad():
        want = resident(input_ids=ids).logits
        got = offloaded(input_ids=ids).logits
    assert got.shape == want.shape
    assert (got - want).abs().max().item() < 1e-5
    assert next(offloaded.parameters()).device.type == "cpu"
    assert sum(p.numel() for p in offloaded.parameters()) == 0     # nothing stays resident
