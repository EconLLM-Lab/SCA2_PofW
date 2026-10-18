"""Relative conservation gates, and the broken capture they must catch.

``gates.py`` states every check as ``|error| / scale <= tau`` with the scale named per check,
because the brief's absolute thresholds sit below one float32 ulp on a residual stream whose
largest entry is about 2.6e4. Two halves:

1. **The gate arithmetic**, on numbers only: the scale is the size of the quantity the error is
   an error of, the boundary is inclusive, and a degenerate zero capture does not divide by zero.
2. **The two capture modes and the corrupted capture**, on SmolLM2-135M-Instruct from the local
   HF cache: float64 passes the float64 taus, float32 passes the float32 taus, the float64 taus
   do not certify a float32 pass, and a capture that loses one head's write fails the
   residual-closure gate by orders of magnitude.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sca2_workbench import gates as G

# ---------------------------------------------------------------------------
# 1. The gate arithmetic. No torch, no model.
# ---------------------------------------------------------------------------


def test_the_gate_is_relative_so_the_same_error_passes_or_fails_by_scale():
    """1e-3 of error is nothing on a stream of 1e9 and fatal on a stream of 1."""
    small = G.residual_closure(1e-3, 1e9, tau=1e-6)
    large = G.residual_closure(1e-3, 1.0, tau=1e-6)
    assert small.rel == pytest.approx(1e-12) and small.ok
    assert large.rel == pytest.approx(1e-3) and not large.ok


def test_residual_scale_is_the_inf_norm_of_the_final_stream():
    g = G.residual_closure(closure_inf=2.6e-3, h_final_inf=2.6e4, tau=1e-4)
    assert g.scale == pytest.approx(2.6e4)
    assert g.rel == pytest.approx(1e-7)
    assert "max|h^L|" in g.scale_desc


def test_head_closure_scale_is_the_attention_write():
    g = G.head_closure(head_closure_inf=1e-9, attn_write_inf=200.0, tau=1e-6)
    assert g.scale == pytest.approx(200.0) and g.rel == pytest.approx(5e-12)


def test_readout_scale_is_the_margin_plus_one_in_either_sign():
    for margin in (2.5, -2.5):
        g = G.readout(margin, dla_gap=1e-13, tau=1e-12)
        assert g.scale == pytest.approx(3.5)
        assert g.rel == pytest.approx(1e-13 / 3.5)
    # a margin near zero does not make the gate absolute: the +1 is the floor
    assert G.readout(0.0, 1e-13, tau=1e-12).scale == pytest.approx(1.0)


def test_pair_scale_is_the_difference_of_margins_plus_one():
    g = G.pair_attribution(d_margin=-0.4, gap=1e-8, tau=1e-6)
    assert g.scale == pytest.approx(1.4) and g.rel == pytest.approx(1e-8 / 1.4)


def test_reference_scale_is_the_largest_reference_logit():
    g = G.logits_reference(max_abs_gap=1e-10, logits_inf=20.0, tau=1e-13)
    assert g.scale == pytest.approx(20.0) and g.rel == pytest.approx(5e-12)


def test_the_tau_boundary_is_inclusive():
    assert G.readout(0.0, 1e-12, tau=1e-12).ok
    assert not G.readout(0.0, 1.0000001e-12, tau=1e-12).ok


def test_every_gate_takes_its_tau_as_an_argument_not_a_constant():
    """The same error and scale pass or fail by ``tau`` alone: nothing is hard-coded per check."""
    cases = [
        lambda tau: G.residual_closure(1e-6, 1.0, tau),
        lambda tau: G.head_closure(1e-6, 1.0, tau),
        lambda tau: G.readout(0.0, 1e-6, tau),
        lambda tau: G.pair_attribution(0.0, 1e-6, tau),
        lambda tau: G.logits_reference(1e-6, 1.0, tau),
    ]
    for make in cases:
        assert make(1e-5).ok, make(1e-5)
        assert not make(1e-7).ok, make(1e-7)


def test_a_zero_capture_does_not_divide_by_zero():
    """An all-zero stream cannot partition an error; the floor turns the gate absolute."""
    g = G.residual_closure(closure_inf=0.0, h_final_inf=0.0, tau=1e-12)
    assert g.scale == 1.0 and g.rel == 0.0 and g.ok
    bad = G.residual_closure(closure_inf=1e-9, h_final_inf=0.0, tau=1e-12)
    assert not bad.ok


def test_all_ok_requires_at_least_one_gate():
    assert not G.all_ok({})
    assert G.all_ok({"a": G.readout(1.0, 0.0, tau=1e-9)})


def test_a_tau_set_can_be_scaled_for_a_sensitivity_check():
    up = G.TAUS_F32.scaled(100.0)
    assert up.residual_closure == pytest.approx(G.TAUS_F32.residual_closure * 100.0)
    assert up.readout == pytest.approx(G.TAUS_F32.readout * 100.0)


def test_the_manifest_block_carries_the_taus_and_the_verdict():
    gates = {"readout": G.readout(1.0, 1e-9, tau=1e-6)}
    block = G.as_manifest(gates, G.TAUS_F64)
    json.dumps(block)                                    # the export writes it as JSON
    assert block["pass"] is True
    assert block["taus"]["residual_closure"] == G.TAUS_F64.residual_closure
    assert block["checks"]["readout"]["scale"] == pytest.approx(2.0)
    assert block["checks"]["readout"]["pass"] is True


def test_float32_taus_are_looser_than_float64_everywhere():
    """Sanity on the calibration direction: float32 round-off is ~1e9 times float64's."""
    for name, f32 in G.TAUS_F32.as_dict().items():
        assert f32 >= G.TAUS_F64.as_dict()[name], name


# ---------------------------------------------------------------------------
# 2. The two capture modes, and the capture that loses a head.
# ---------------------------------------------------------------------------
MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"
ADAPTER = Path(__file__).resolve().parents[1] / "models" / "usa_e1"

torch = pytest.importorskip("torch")
LC = pytest.importorskip("sca2_workbench.llama_capture")
from sca2_workbench import export as EX  # noqa: E402
from sca2_workbench import items as I  # noqa: E402


def _cached(model_id: str) -> bool:
    root = Path.home() / ".cache" / "huggingface" / "hub" / ("models--" + model_id.replace("/", "--"))
    return any(root.glob("snapshots/*/model.safetensors"))


needs_model = pytest.mark.skipif(not _cached(MODEL), reason=f"{MODEL} not in the local HF cache")

DTYPES = {"float64": (torch.float64, G.TAUS_F64), "float32": (torch.float32, G.TAUS_F32)}


@pytest.fixture(scope="module")
def prompt():
    from transformers import AutoTokenizer  # noqa: PLC0415
    tok = AutoTokenizer.from_pretrained(EX.TOKENIZER_ID)
    item = I.wvs_item("Q57")
    ro = I.readout_ids(tok, item)
    return item, ro


@pytest.fixture(scope="module")
def weights():
    loaded = {}
    for name, (dtype, _) in DTYPES.items():
        hf, _ = LC.load_hf(MODEL, dtype=dtype)
        loaded[name] = LC.weights_from_hf(hf, dtype=dtype)

    def get(name: str):
        return loaded[name]
    return get


@pytest.fixture(scope="module")
def adapted():
    """The ``usa_e1`` fine-tune merged onto the same base, in both dtypes."""
    loaded = {}
    for name, (dtype, _) in DTYPES.items():
        hf, _ = LC.load_hf(MODEL, str(ADAPTER), dtype=dtype)
        loaded[name] = LC.weights_from_hf(hf, dtype=dtype)

    def get(name: str):
        return loaded[name]
    return get


def _run(W, prompt, **kw):
    item, ro = prompt
    return LC.run(W, ro["prompt_ids"], j_plus=ro["code_token"][item.j_plus],
                  j_minus=ro["code_token"][item.j_minus], keep_head_out=True, **kw)


@pytest.mark.parametrize("mode", list(DTYPES))
@pytest.mark.parametrize("clamp", [False, True])
@needs_model
def test_a_clean_capture_passes_its_own_gate_set(weights, prompt, mode, clamp):
    _, taus = DTYPES[mode]
    out = _run(weights(mode), prompt, clamp_q3=clamp)
    suffix = "_clamped" if clamp else ""
    gates = G.check_capture(out, taus, suffix=suffix)
    assert G.all_ok(gates), {k: (g.rel, g.tau) for k, g in gates.items()}


@pytest.mark.parametrize("mode", list(DTYPES))
@needs_model
def test_the_capture_runs_in_the_dtype_it_was_asked_for(weights, prompt, mode):
    dtype, _ = DTYPES[mode]
    out = _run(weights(mode), prompt)
    assert out["dtype"] == mode
    assert out["logits_last"].dtype == dtype
    assert out["_resid"].dtype == dtype


@pytest.mark.parametrize("mode", list(DTYPES))
@needs_model
def test_an_adapter_merges_in_float32_too(adapted, weights, prompt, mode):
    """peft once left every LoRA B at zero in float64; a merged adapter must not vanish in float32.

    The tell is the weight itself: the merged ``q`` differs from the base ``q`` by ~8e-4 at the
    largest entry (one float32 ulp of the weight scale is ~6e-7), and a dropped adapter reads 0.
    """
    dtype, taus = DTYPES[mode]
    base, tuned = weights(mode), adapted(mode)
    assert tuned.embed.dtype == dtype
    delta = (tuned.layers[0]["q"].double() - base.layers[0]["q"].double()).abs().max().item()
    assert delta > 1e-4, f"{mode}: the adapter merged to nothing"
    gates = G.check_capture(_run(tuned, prompt), taus)
    assert G.all_ok(gates), {k: (g.rel, g.tau) for k, g in gates.items()}


@needs_model
def test_the_float32_adapter_merge_is_the_float64_one(adapted, weights, prompt):
    deltas = {m: adapted(m).layers[0]["q"].double() - weights(m).layers[0]["q"].double()
              for m in DTYPES}
    # The delta is a small difference of large weights, so its own float32 resolution is ~1e-6:
    # judge parity there, not relative to the delta.
    assert (deltas["float32"] - deltas["float64"]).abs().max().item() < 1e-6
    shift = {m: _run(adapted(m), prompt)["margin"] - _run(weights(m), prompt)["margin"]
             for m in DTYPES}
    assert abs(shift["float64"]) > 1e-3                       # measured 0.182 on wvs_Q57
    assert abs(shift["float32"] - shift["float64"]) < 1e-4 * (abs(shift["float64"]) + 1.0)


@needs_model
def test_the_float64_gate_set_does_not_certify_a_float32_pass(weights, prompt):
    """Why the taus are per dtype: the same clean float32 capture is 7 orders over the
    float64 residual gate -- it is round-off, not a bug, and only the scale says so."""
    out = _run(weights("float32"), prompt)
    g64 = G.check_capture(out, G.TAUS_F64)["residual_closure"]
    g32 = G.check_capture(out, G.TAUS_F32)["residual_closure"]
    assert not g64.ok and g32.ok
    assert g64.rel > 1e3 * G.TAUS_F64.residual_closure
    # One float32 ulp at the largest residual entry is 1.2e-7 * max|h| ~ 5e-4 here: the brief's
    # absolute 1e-3 gate is about an ulp wide on this model, and narrower than that on the
    # adapter's (5.3e-3 measured, plans/stage1_f32_gaps.md).
    assert out["residual_scale_inf"] > 1e3
    assert 1.2e-7 * out["residual_scale_inf"] > 1e-4


@pytest.mark.parametrize("mode", list(DTYPES))
@needs_model
def test_a_dropped_head_write_fails_the_residual_gate_by_a_clear_margin(weights, prompt, mode):
    """The broken-capture demo: one head's write is missing from the stored pieces.

    The residual stream keeps the head (the addition happened before the capture dropped it),
    so the pieces no longer add up to the stream. ``run`` picks the head with the largest write
    in the capture, which is the strongest version of the bug.
    """
    _, taus = DTYPES[mode]
    W = weights(mode)
    clean = _run(W, prompt)
    head_norm = clean["head_norm"].amax(dim=-1)                       # (L, H) over positions
    layer, head = torch.nonzero(head_norm == head_norm.max())[0].tolist()
    broken = _run(W, prompt, drop_head_write=(layer, head))

    gates = G.check_capture(broken, taus)
    ratio = {k: g.rel / g.tau for k, g in gates.items()}

    # the gate the card asks for: residual closure, far over its tau
    assert not gates["residual_closure"].ok
    assert ratio["residual_closure"] > 20, ratio
    # the readout gate fails too: the head's attribution is gone from the DLA sum
    assert not gates["readout"].ok and ratio["readout"] > 10, ratio
    # head closure does NOT fail, and that is the point: both stored pieces lost the same head,
    # so they still agree with each other; only the stream disagrees.
    assert gates["head_closure"].ok
    assert gates["head_closure"].rel < 1e-6, gates["head_closure"].rel
    # the sizes involved, pinned so the demo stays a demo: the write is large, the stream larger
    assert head_norm[layer, head].item() > 10.0
    assert clean["residual_scale_inf"] > 1e3


@needs_model
@pytest.mark.parametrize("mode", list(DTYPES))
def test_the_same_capture_flips_verdict_when_the_tau_is_passed_in(weights, prompt, mode):
    """The gate set is an argument too: a clean capture fails a 1000x tighter set, passes a 100x looser one."""
    out = _run(weights(mode), prompt)
    assert not G.all_ok(G.check_capture(out, DTYPES[mode][1].scaled(1e-3)))
    assert G.all_ok(G.check_capture(out, DTYPES[mode][1].scaled(100.0)))


@needs_model
@pytest.mark.parametrize("mode", list(DTYPES))
def test_the_broken_capture_fails_even_with_ten_times_the_tau(weights, prompt, mode):
    """The corruption is not a threshold artefact: 10x the calibrated tau still catches it,
    while the clean capture passes the same loosened set."""
    _, taus = DTYPES[mode]
    W = weights(mode)
    clean = _run(W, prompt)
    head_norm = clean["head_norm"].amax(dim=-1)
    layer, head = torch.nonzero(head_norm == head_norm.max())[0].tolist()
    broken = _run(W, prompt, drop_head_write=(layer, head))
    loose = taus.scaled(G.TAU_MULTIPLE)
    gb = G.check_capture(broken, loose)
    assert not gb["residual_closure"].ok and not gb["readout"].ok, {
        k: (g.rel / g.tau) for k, g in gb.items()}
    assert G.all_ok(G.check_capture(clean, loose))


@needs_model
def test_a_clean_float64_capture_is_unchanged_by_the_relative_gate_refactor(weights, prompt):
    """Pins the float64 numbers the exported 135M runs already carry."""
    out = _run(weights("float64"), prompt)
    assert out["residual_closure_inf"] < 1e-9
    assert out["head_closure_inf"] == 0.0                 # a = sum_h o, computed once
    assert out["dla_gap"] < 1e-9
    assert abs(out["running_margin"][-1].item() - out["margin"]) < 1e-9


# ---------------------------------------------------------------------------
# 3. The exporter carries the new mechanism.
# ---------------------------------------------------------------------------


@needs_model
def test_the_run_manifest_carries_the_relative_gate_block():
    sess = EX.Session(torch.float64)
    man, _, _ = EX.capture_run(sess, "smol_inst", EX.item_from_id("wvs_Q57"))
    c = man["conservation"]
    assert c["pass"] is True
    assert c["legacy_absolute_applicable"] is True
    assert c["relative"]["pass"] is True
    assert c["relative"]["taus"] == G.TAUS_F64.as_dict()
    assert {"residual_closure", "residual_closure_clamped", "head_closure",
            "readout", "readout_clamped", "logits_reference"} <= set(c["relative"]["checks"])
    for name, gate in c["relative"]["checks"].items():
        assert {"error", "scale", "scale_desc", "rel", "tau", "pass"} <= set(gate), name
        assert gate["rel"] <= gate["tau"], name
    # the legacy fields the viewer still reads are untouched
    assert set(c["thresholds"]) == set(EX.THRESHOLDS)
    assert man["provenance"]["compute_dtype"] == "float64"


@needs_model
def test_the_float32_capture_mode_is_reachable_and_passes_the_relative_gates():
    sess = EX.Session(torch.float32)
    man, _, _ = EX.capture_run(sess, "smol_inst", EX.item_from_id("wvs_Q57"))
    c = man["conservation"]
    assert man["provenance"]["compute_dtype"] == "float32"
    assert c["relative"]["pass"] is True
    assert c["pass"] is True
    # the brief's absolute gate is about one ulp wide at this scale, which is why the verdict
    # moved: one float32 ulp of the largest residual entry, against the 1e-3 absolute gate
    assert c["legacy_absolute_applicable"] is False
    scale = c["relative"]["checks"]["residual_closure"]["scale"]
    assert scale > 1e3 and 1.2e-7 * scale > 0.3 * c["thresholds"]["residual_closure_inf"]


def test_an_unknown_capture_dtype_is_refused():
    with pytest.raises(ValueError, match="capture dtype"):
        EX.Session(torch.bfloat16)


# ---------------------------------------------------------------------------
# 3. Step closure: a 0.1% error in one stored MLP write (audit of t_1547e1a8).
# ---------------------------------------------------------------------------
def test_step_closure_scale_is_the_local_stream_not_the_global_one():
    """The worst ratio is the gate; 0.4 of error is huge next to a local 100, tiny next to 4,429."""
    local = G.step_closure(step_err_inf=0.4, step_scale_inf=100.0, tau=1e-5)
    assert local.rel == pytest.approx(4e-3) and not local.ok
    glob = G.residual_closure(0.4, 4429.0, tau=1e-4)
    assert glob.ok                       # the global gate lets the same 0.4 through (the audit's gap)


def test_worst_step_returns_numerator_and_denominator_of_the_worst_ratio():
    import torch as _t
    err = _t.tensor([[1.0, 4.0], [0.5, 0.1]])
    scale = _t.tensor([[100.0, 1000.0], [2.0, 50.0]])
    # ratios 0.01, 0.004, 0.25, 0.002 -> the worst is the (1, 0) entry
    assert G.worst_step(err, scale) == (0.5, 2.0)
    # a scale below the floor is floored at 1
    assert G.step_closure(0.5, 0.1, tau=1.0).rel == pytest.approx(0.5)


@pytest.mark.parametrize("mode", list(DTYPES))
@needs_model
def test_a_scaled_mlp_write_in_the_median_layer_fails_step_closure_by_over_10x(weights, prompt, mode):
    """1.001x on the stored MLP write of the median-size layer. Clean capture passes.

    The audit found the global residual gate passes this in float32 (0.1x of tau). The step gate
    must fail it by more than 10x of its tau, in both dtypes, on the layer that is hardest to see.
    """
    _, taus = DTYPES[mode]
    W = weights(mode)
    clean = _run(W, prompt)
    assert G.check_capture(clean, taus)["step_closure"].ok

    size = clean["mlp_norm"].amax(-1)                                  # (L,)
    layer = int(size.argsort()[len(size) // 2])                        # median MLP write
    bad = _run(W, prompt, scale_mlp_write=(layer, 1.001))
    g = G.check_capture(bad, taus)["step_closure"]
    assert not g.ok and g.rel / g.tau > 10, (layer, g.rel / g.tau)
    # and the readout does not see it at all (DLA reads the in-loop write): that is why the
    # step gate exists, not a reason to drop it
    assert G.check_capture(bad, taus)["readout"].ok


@needs_model
def test_the_streamed_capture_carries_the_same_step_gate():
    """``stream_capture`` computes the gate inside its layer loop; same corruption, same verdict."""
    SC = pytest.importorskip("sca2_workbench.stream_capture")
    from transformers import AutoTokenizer  # noqa: PLC0415
    root = Path.home() / ".cache" / "huggingface" / "hub" / ("models--" + MODEL.replace("/", "--"))
    snap = sorted(root.glob("snapshots/*/model.safetensors"))[0].parent
    tok = AutoTokenizer.from_pretrained(EX.TOKENIZER_ID)
    item = I.wvs_item("Q81")
    ro = I.readout_ids(tok, item)
    jp, jm = ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]
    for dtype, taus in DTYPES.values():
        src = SC.SafetensorsSource(snap, dtype)
        kw = dict(j_plus=jp, j_minus=jm)
        (clean,) = SC.run_streamed(src, ro["prompt_ids"], **kw)
        assert G.check_capture(clean, taus)["step_closure"].ok
        size = clean["mlp_norm"].amax(-1)
        layer = int(size.argsort()[len(size) // 2])
        (bad,) = SC.run_streamed(src, ro["prompt_ids"], scale_mlp_write=(layer, 1.001), **kw)
        g = G.check_capture(bad, taus)["step_closure"]
        assert not g.ok and g.rel / g.tau > 10, (dtype, layer, g.rel / g.tau)
