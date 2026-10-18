"""Llama-3 RoPE (``rope_type: llama3``) in our float64 rotation, checked against HF's module.

The HF side is HF's own ``LlamaRotaryEmbedding``, called with its float32 table cast switched off
(``torch.float = torch.float64`` for the duration of the call). That switch is what makes a 1e-12
comparison meaningful: HF builds ``inv_freq`` in float32, and at position p the phase p * inv_freq
runs up to ~1e5 rad, so one float32 ulp of the table moves cos/sin by O(1). Stock HF is measured
as well and reported, for the record. Positions must stay below 2**24: HF's ``forward`` casts
``position_ids`` to float32 with ``.float()``, and above that the reference itself loses precision.

Provenance of the configs (see ``tests/fixtures/hf/README.md``):
  * the fixture is the ``config.json`` HF served for ``meta-llama/Llama-3.1-8B-Instruct``;
  * ``meta-llama/Llama-3.2-1B`` is a separate licence gate this account is not approved for: its
    config.json answers 403, so the 3.2-1B case skips unless a copy of that config is in the local
    HF cache. Nothing here needs model weights.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import replace
from pathlib import Path

import pytest
import torch

LC = pytest.importorskip("sca2_workbench.llama_capture")
from transformers import LlamaConfig, LlamaForCausalLM  # noqa: E402
from transformers.models.llama import modeling_llama as ml  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "hf"
LLAMA31_8B_INSTRUCT = FIXTURES / "llama-3.1-8B-Instruct.config.json"
#: sha256 of the bytes HF served for ``hf_hub_download("meta-llama/Llama-3.1-8B-Instruct", "config.json")``.
LLAMA31_SHA256 = "29e4c210b0d6ac178b16b2a255a568bdb23b581e50ca1ef6a6d071dd85704e6e"
LLAMA32_1B_CACHE = Path.home() / ".cache" / "huggingface" / "hub" / "models--meta-llama--Llama-3.2-1B"
LLAMA32_SKIP = ("meta-llama/Llama-3.2-1B config.json is not in the local HF cache "
                "(the repo answers 403 for this account)")

#: The parity sweep. 0..4096 spans the high-frequency band (the phase moves fast) and the
#: low-frequency band (it barely moves); the per-band counts are asserted by the coverage test.
POSITIONS = torch.arange(0, 4097, dtype=torch.long)
#: Positions past the original context, where the llama3 rescaling has its largest effect.
LONG_POSITIONS = torch.tensor([8192, 16384, 65536, 131071], dtype=torch.long)


def _load_config(source) -> LlamaConfig:
    """A ``LlamaConfig``: pass a ``Path`` to a config.json, or the config itself."""
    if isinstance(source, Path):
        return LlamaConfig.from_dict(json.loads(source.read_text()))
    return source


def _cached_llama32_config() -> Path | None:
    snapshots = sorted((LLAMA32_1B_CACHE / "snapshots").glob("*/config.json"))
    return snapshots[-1] if snapshots else None


def _synthetic_config(head_dim: int = 64, factor: float = 32.0) -> LlamaConfig:
    """A stress case for the rescaling, not a served config: Llama-3.1's rope with a wider factor."""
    return LlamaConfig(
        hidden_size=4 * head_dim, num_attention_heads=4, head_dim=head_dim, num_hidden_layers=2,
        num_key_value_heads=1, intermediate_size=8 * head_dim, max_position_embeddings=131072,
        rope_theta=500000.0,
        rope_scaling={"rope_type": "llama3", "factor": factor, "low_freq_factor": 1.0,
                      "high_freq_factor": 4.0, "original_max_position_embeddings": 8192},
    )


def _cases() -> list:
    """The llama3 configs the parity tests run on: the served 3.1 config, 3.2 if cached, a stress case."""
    cached = _cached_llama32_config()
    return [
        pytest.param(LLAMA31_8B_INSTRUCT, id="llama-3.1-8B-Instruct"),
        pytest.param(cached, id="meta-llama/Llama-3.2-1B",
                     marks=pytest.mark.skipif(cached is None, reason=LLAMA32_SKIP)),
        pytest.param(_synthetic_config(), id="synthetic-factor32-head-dim64"),
    ]


def _bands(cfg: LlamaConfig) -> tuple:
    """Which of HF's three llama3 branches each unscaled frequency falls in."""
    scaling = LC._rope_scaling(cfg)
    assert scaling.scaled, "this helper is for scaled configs"
    inv_freq = LC.rope_inv_freq(cfg.head_dim, LC._rope_theta(cfg))
    wavelen = 2 * math.pi / inv_freq
    low = scaling.original_max_position_embeddings / scaling.low_freq_factor
    high = scaling.original_max_position_embeddings / scaling.high_freq_factor
    return wavelen < high, (wavelen >= high) & (wavelen <= low), wavelen > low


def _hf_rope_float64(cfg: LlamaConfig, positions: torch.Tensor) -> tuple:
    """(cos, sin) from HF's own module with its float32 table cast switched off."""
    saved = torch.float
    torch.float = torch.float64
    try:
        module = ml.LlamaRotaryEmbedding(cfg)
        assert module.inv_freq.dtype == torch.float64, "the torch.float switch did not reach HF"
        x = torch.zeros(1, positions.numel(), cfg.head_dim, dtype=torch.float64)
        cos, sin = module(x, positions[None])
    finally:
        torch.float = saved
    return cos, sin


def _our_rope_at(cfg: LlamaConfig, positions: torch.Tensor) -> tuple:
    """Our rotation at arbitrary positions, through the production inverse frequencies."""
    inv_freq = LC.rope_inv_freq(cfg.head_dim, LC._rope_theta(cfg), LC._rope_scaling(cfg))
    freqs = positions[:, None].to(torch.float64) * inv_freq[None, :]
    emb = torch.cat((freqs, freqs), dim=-1)
    return emb.cos()[None], emb.sin()[None]


def test_fixture_is_the_config_hf_served():
    """The config under test is the bytes HF served, not a hand-typed table."""
    assert hashlib.sha256(LLAMA31_8B_INSTRUCT.read_bytes()).hexdigest() == LLAMA31_SHA256
    cfg = _load_config(LLAMA31_8B_INSTRUCT)
    assert cfg.rope_scaling["rope_type"] == "llama3"
    assert cfg.rope_scaling["factor"] == 8.0
    # transformers 5.x moves rope_theta into ``rope_parameters``; ``cfg.rope_theta`` no longer exists.
    assert cfg.rope_parameters["rope_theta"] == 500000.0
    assert LC._rope_theta(cfg) == 500000.0
    assert cfg.head_dim == 128


def test_llama3_is_accepted_and_unimplemented_types_are_still_refused():
    """The llama3 refusal is gone; the guard that refuses an unimplemented scheme is not."""
    cfg = _load_config(LLAMA31_8B_INSTRUCT)
    assert LC._rope_theta(cfg) == 500000.0
    scaling = LC._rope_scaling(cfg)
    assert (scaling.rope_type, scaling.factor, scaling.low_freq_factor) == ("llama3", 8.0, 1.0)
    assert scaling.high_freq_factor == 4.0
    assert scaling.original_max_position_embeddings == 8192
    assert scaling.scaled

    # A plain config keeps the unscaled table.
    plain = LlamaConfig()
    assert not LC._rope_scaling(plain).scaled
    assert LC._rope_theta(plain) == plain.rope_parameters["rope_theta"]

    # yarn stops the load.
    yarn = LlamaConfig(rope_scaling={"rope_type": "yarn", "factor": 8.0,
                                     "original_max_position_embeddings": 8192})
    with pytest.raises(ValueError, match="only default and llama3 RoPE"):
        LC._rope_scaling(yarn)

    # A half-specified llama3 never reaches a HF config (its own validator raises there first), so
    # the guard is exercised through a config-shaped stand-in: if such a block ever arrives, we
    # refuse instead of silently rotating with the unscaled table.
    class _Bare:
        rope_parameters = {"rope_type": "llama3", "factor": 8.0}

    with pytest.raises(ValueError, match="llama3 RoPE needs"):
        LC._rope_scaling(_Bare())
    partial = LlamaConfig(rope_scaling={"rope_type": "llama3", "factor": 8.0, "low_freq_factor": 1.0,
                                        "high_freq_factor": 4.0,
                                        "original_max_position_embeddings": 8192,
                                        "partial_rotary_factor": 0.5})
    with pytest.raises(ValueError, match="partial_rotary_factor"):
        LC._rope_scaling(partial)


@pytest.mark.parametrize("source", _cases())
def test_the_sweep_exercises_all_three_llama3_branches(source):
    """Every branch of the rescaling must have frequencies behind it, and act only where it should."""
    cfg = _load_config(source)
    high_band, medium_band, low_band = _bands(cfg)
    assert high_band.any() and medium_band.any() and low_band.any(), (
        f"band counts high={int(high_band.sum())} medium={int(medium_band.sum())} "
        f"low={int(low_band.sum())} of {cfg.head_dim // 2} frequencies")

    head_dim, theta = cfg.head_dim, LC._rope_theta(cfg)
    scaling = LC._rope_scaling(cfg)
    plain = LC.rope_inv_freq(head_dim, theta)
    scaled = LC.rope_inv_freq(head_dim, theta, scaling)
    # short wavelengths: untouched, bit for bit
    assert torch.equal(scaled[high_band], plain[high_band])
    # long wavelengths: exactly the unscaled value over the factor
    assert torch.equal(scaled[low_band], plain[low_band] / scaling.factor)
    # the blend sits strictly between the two ends
    assert bool((scaled[medium_band] > plain[medium_band] / scaling.factor).all())
    assert bool((scaled[medium_band] < plain[medium_band]).all())


@pytest.mark.parametrize("source", _cases())
def test_rotation_matches_hf_float64_to_1e_12(source):
    """The card's gate: our float64 rotation vs HF's own, over both frequency bands."""
    cfg = _load_config(source)

    hf_cos, hf_sin = _hf_rope_float64(cfg, POSITIONS)
    ours_cos, ours_sin = _our_rope_at(cfg, POSITIONS)
    gap = max((ours_cos - hf_cos).abs().max().item(), (ours_sin - hf_sin).abs().max().item())
    assert gap <= 1e-12, f"cos/sin gap {gap:.3e}"

    hf_cos_long, hf_sin_long = _hf_rope_float64(cfg, LONG_POSITIONS)
    ours_cos_long, ours_sin_long = _our_rope_at(cfg, LONG_POSITIONS)
    gap_long = max((ours_cos_long - hf_cos_long).abs().max().item(),
                   (ours_sin_long - hf_sin_long).abs().max().item())
    assert gap_long <= 1e-12, f"cos/sin gap at long positions {gap_long:.3e}"

    # The production entry point (positions 0..T-1) reads the same table.
    cos, sin = LC._rope(POSITIONS.numel(), cfg.head_dim, LC._rope_theta(cfg), LC._rope_scaling(cfg))
    assert max((cos - hf_cos[0]).abs().max().item(), (sin - hf_sin[0]).abs().max().item()) <= 1e-12


@pytest.mark.parametrize("source", _cases())
def test_rotated_qk_matches_hf_apply_rotary_pos_emb(source):
    """The rotated q and k agree, so our half-rotation convention is HF's too."""
    cfg = _load_config(source)
    torch.manual_seed(0)
    q = torch.randn(1, 4, POSITIONS.numel(), cfg.head_dim, dtype=torch.float64)
    k = torch.randn(1, 2, POSITIONS.numel(), cfg.head_dim, dtype=torch.float64)
    cos, sin = _hf_rope_float64(cfg, POSITIONS)
    hf_q, hf_k = ml.apply_rotary_pos_emb(q, k, cos, sin, unsqueeze_dim=1)
    assert (q * cos + LC._rotate_half(q) * sin - hf_q).abs().max().item() <= 1e-12
    assert (k * cos + LC._rotate_half(k) * sin - hf_k).abs().max().item() <= 1e-12


def test_our_table_is_hf_s_table_in_every_precision():
    """HF ships the table in float32. Our float32 table must be HF's bit for bit, and our float64
    table must round to it within one ulp -- that is what makes the float64 table the right one."""
    cfg = _load_config(LLAMA31_8B_INSTRUCT)
    head_dim, theta = cfg.head_dim, LC._rope_theta(cfg)
    scaling = LC._rope_scaling(cfg)
    hf_table = ml.LlamaRotaryEmbedding(cfg).inv_freq                      # float32, built by HF
    ours32 = LC.rope_inv_freq(head_dim, theta, scaling, dtype=torch.float32)
    assert torch.equal(ours32, hf_table), "our float32 table is not HF's"
    ours64 = LC.rope_inv_freq(head_dim, theta, scaling)
    ulp_ratio = ((ours64.to(torch.float32) - hf_table).abs() / hf_table.abs()).max().item()
    # The float64 table rounds into HF's float32 table: at most a couple of ulp, because the
    # float32 table is itself a rounded computation. Measured here: 2.34 ulp (bound: 4 ulp).
    assert ulp_ratio <= 2 ** -21, f"float64 table is {ulp_ratio / 2 ** -23:.2f} ulp from HF's"


def test_native_dtype_reference_keeps_the_scaling():
    """``_rope_native_dtype`` (the export's reference patch) is HF's call in float64, llama3 included."""
    cfg = _load_config(LLAMA31_8B_INSTRUCT)
    hf_cos, hf_sin = _hf_rope_float64(cfg, POSITIONS)
    module = ml.LlamaRotaryEmbedding(cfg)
    x = torch.zeros(1, POSITIONS.numel(), cfg.head_dim, dtype=torch.float64)
    patched_cos, patched_sin = LC._rope_native_dtype(module, x, POSITIONS[None])
    assert patched_cos.dtype == torch.float64
    assert (patched_cos - hf_cos).abs().max().item() <= 1e-12
    assert (patched_sin - hf_sin).abs().max().item() <= 1e-12


def test_forward_pass_on_a_llama3_config_uses_the_scaled_rotation():
    """End to end, no weights: our pass over a tiny llama3 model, against HF's, in float64.

    This is a plumbing test, not the 1e-12 rope contract: it proves the rescaling reaches the pass
    (``W.rope_scaling``) and that the pass is HF's pass to float32-rope precision. The saved
    reference gaps here (hidden 1.6e-07 absolute / 4.9e-07 relative, logits 1.1e-06) do not move
    when HF's three float32 casts (RMSNorm, RoPE, eager softmax) are removed, so they are not those
    casts; the exact 1e-12 agreement with HF is the asserted property of the rope table itself, in
    the tests above. The residual gap is left for the float32-gaps card to place (it measures
    exactly this on a 1B model).

    The original context is 512, not a served 8192, and that is the point of this config: the band
    ``llama3`` divides is ``wavelength > original_max_position_embeddings/low_freq_factor``, so with
    a served original context a 256-token prompt leaves that band almost unrotated -- at 8192 the
    scaled and unscaled logits differ by 2.7e-03 at T = 256, and only reach 1.5e-02 at T = 1024.
    Shortening the original context to 512 puts all three branches inside a 256-token pass (4 high /
    2 medium / 10 low of the 16 frequencies), where the measured gap is 2.9e-02. The served-config
    behaviour at real positions is what the sweep tests above measure.
    """
    cfg = LlamaConfig(vocab_size=256, hidden_size=256, intermediate_size=512, num_hidden_layers=2,
                      num_attention_heads=8, num_key_value_heads=2, head_dim=32,
                      max_position_embeddings=131072, rope_theta=500000.0,
                      rope_scaling={"rope_type": "llama3", "factor": 8.0, "low_freq_factor": 1.0,
                                    "high_freq_factor": 4.0, "original_max_position_embeddings": 512})
    # The reference check patches HF's eager attention, so ask for it: transformers 5.x gives a
    # fresh model sdpa by default, which would not go through the patch. Same choice as load_hf.
    cfg._attn_implementation = "eager"
    torch.manual_seed(0)
    model = LlamaForCausalLM(cfg).eval()
    assert model.config._attn_implementation == "eager"
    W = LC.weights_from_hf(model)
    assert W.rope_scaling.scaled and W.rope_scaling.factor == 8.0

    ids = [i % 256 for i in range(256)]
    out = LC.run(W, ids)
    # The pass is internally consistent, which no reference is needed for.
    assert out["residual_closure_inf"] < 1e-9
    ref = LC.reference_check(model, ids, out)
    assert ref["hf_hidden_max_abs_gap"] < 1e-5, ref["hf_hidden_max_abs_gap"]
    assert ref["hf_logits_max_abs_gap"] < 1e-5, ref["hf_logits_max_abs_gap"]

    # The load, not just the arithmetic, is what carries the rescaling: the same pass with the
    # unscaled table moves the logits by 2.9e-02 here. This is the assertion that fails if the
    # llama3 table ever stops reaching the forward pass.
    unscaled = LC.run(replace(W, rope_scaling=LC.RopeScaling()), ids)
    assert (unscaled["logits"] - out["logits"]).abs().max().item() > 1e-2
