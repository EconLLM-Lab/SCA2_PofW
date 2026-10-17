"""Contract additions of ``sca2-workbench/capture@1.1``: prompt ``segments`` and the B - A readout
attributions (``d_head_attr``, ``d_mlp_attr``, ``d_attn_attr``, ``d_embed_attr``) with their gate.

Needs the Instruct tokenizer and weights in the local HF cache. The hand checks pin token
indices read off the real tokenisation, so a change to the prompt or the template fails here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("sca2_workbench.llama_capture")
from sca2_workbench import export as EX  # noqa: E402
from sca2_workbench import items as I  # noqa: E402

MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"
ITEM_IDS = ["wvs_Q57", "wvs_Q43", "wvs_Q81", "bank_USA_00023ac74dac",
            "bank_USA_7232414df567", "bank_USA_f48d3d37c50e"]
ROOT = Path(__file__).resolve().parents[1]


def _cached(model_id: str) -> bool:
    root = Path.home() / ".cache" / "huggingface" / "hub" / ("models--" + model_id.replace("/", "--"))
    return any(root.glob("snapshots/*/model.safetensors"))


pytestmark = pytest.mark.skipif(not _cached(MODEL), reason=f"{MODEL} not in the local HF cache")


@pytest.fixture(scope="module")
def tok():
    from transformers import AutoTokenizer  # noqa: PLC0415
    return AutoTokenizer.from_pretrained(EX.TOKENIZER_ID)


def _segs(tok, item_id):
    item = EX.item_from_id(item_id)
    ro = I.readout_ids(tok, item)
    return item, ro, I.prompt_segments(tok, item, ro)


def _text(tok, ro, seg):
    return tok.decode(ro["prompt_ids"][seg["a"]:seg["b"]])


def test_prompt_is_unchanged_by_the_parts_refactor():
    """The parts concatenate to the verbatim v1 prompt (pinned for one WVS item)."""
    expected = (
        "Answer this questionnaire as an individual person. Respond naturally and sincerely, as someone "
        "would in real life. Do not mention being an AI or assistant.\n\n"
        "Question:\nGenerally speaking, would you say that most people can be trusted or that you need "
        "to be very careful in dealing with people?\n\n"
        "Select exactly one response code from the options below.\n"
        "1: Most people can be trusted\n2: Need to be very careful\n\n"
        "Return only the response code, with no words or explanation.\n\nAnswer:")
    item = I.wvs_item("Q57")
    assert item.user_prompt == expected
    assert "".join(t for _, _, t in item.parts) == expected


@pytest.mark.parametrize("item_id", ITEM_IDS)
def test_segments_cover_every_token_once(tok, item_id):
    _, ro, segs = _segs(tok, item_id)
    T = len(ro["prompt_ids"])
    assert segs[0]["a"] == 0 and segs[-1]["b"] == T
    assert all(x["b"] == y["a"] for x, y in zip(segs, segs[1:]))      # no gap, no overlap
    assert all(s["b"] > s["a"] for s in segs)
    assert sorted({s["kind"] for s in segs}) == sorted(I.SEGMENT_KINDS)
    assert segs[-1]["kind"] == "readout" and segs[-1]["b"] - 1 == T - 1   # t* is the last token


def test_wvs_q57_segments_by_hand(tok):
    """Token indices read off the tokenisation: T = 136, t* = 135."""
    _, ro, segs = _segs(tok, "wvs_Q57")
    by = {s["kind"]: s for s in segs if s["kind"] in ("question", "options", "system", "answer_cue", "readout")}
    assert (by["system"]["a"], by["system"]["b"]) == (3, 19)
    assert (by["question"]["a"], by["question"]["b"]) == (55, 85)        # "Question:" + stem + blank line
    assert _text(tok, ro, by["question"]) == (
        "Question:\nGenerally speaking, would you say that most people can be trusted or that you need "
        "to be very careful in dealing with people?\n\n")
    assert (by["options"]["a"], by["options"]["b"]) == (96, 113)
    assert _text(tok, ro, by["options"]) == "1: Most people can be trusted\n2: Need to be very careful\n\n"
    assert by["options"]["label"] == "options 1\u20132"
    assert (by["answer_cue"]["a"], by["answer_cue"]["b"]) == (127, 129)
    assert (by["readout"]["a"], by["readout"]["b"]) == (135, 136)


def test_bank_scenario_is_one_question_segment(tok):
    """The 92-token scenario paragraph that the browser heuristic left collapsed."""
    item, ro, segs = _segs(tok, "bank_USA_00023ac74dac")
    question = [s for s in segs if s["kind"] == "question"]
    assert len(question) == 1 and question[0]["label"] == "scenario"
    assert (question[0]["a"], question[0]["b"]) == (55, 147) and question[0]["b"] - question[0]["a"] == 92
    text = _text(tok, ro, question[0])
    assert text.startswith("Question:\nA fellow student tutored me for free") and text.endswith("performance.\n\n")
    options = [s for s in segs if s["kind"] == "options"]
    assert len(options) == 1 and (options[0]["a"], options[0]["b"]) == (158, 283)
    assert _text(tok, ro, options[0]) == f"1: {item.labels[0]}\n2: {item.labels[1]}\n\n"


def test_segment_check_refuses_gaps_and_overlaps():
    ok = [{"a": 0, "b": 2, "kind": "template", "label": ""}, {"a": 2, "b": 3, "kind": "readout", "label": ""}]
    I.check_segments(ok, 3)
    for bad in ([ok[0]], [ok[0], {**ok[1], "a": 1}], [ok[0], {**ok[1], "a": 3, "b": 4}]):
        with pytest.raises(ValueError):
            I.check_segments(bad, 3)


@pytest.fixture(scope="module")
def pair_q57():
    sess = EX.Session()
    man_a, _, out_a = EX.capture_run(sess, "smol_inst", EX.item_from_id("wvs_Q57"), keep_head_out=True)
    man_b, _, out_b = EX.capture_run(sess, "smol_inst_usa_e1", EX.item_from_id("wvs_Q57"), keep_head_out=True)
    return man_a, man_b, out_a, out_b


def test_run_manifest_carries_segments(pair_q57):
    man_a, man_b, _, _ = pair_q57
    for man in (man_a, man_b):
        I.check_segments(man["segments"], len(man["tokens"]))
    assert man_a["segments"] == man_b["segments"]       # same token ids across a pair


def test_d_attribution_sums_hit_the_gate(pair_q57):
    man_a, man_b, out_a, out_b = pair_q57
    ra, rb = man_a["readout"], man_b["readout"]
    arrays, d_embed, chk = EX.d_attribution_gate(out_a, out_b, ra["margin"], rb["margin"])
    assert chk["pass"] and chk["gap_f64"] < 1e-12 and chk["gap_f32"] < EX.PAIR_THRESHOLDS["d_attr_gap"]
    assert tuple(arrays["head_attr"].shape) == (30, 9) and tuple(arrays["mlp_attr"].shape) == (30,)
    assert abs(arrays["head_attr"].double().sum(1) - arrays["attn_attr"].double()).max() < 1e-6
    arrays_c, d_embed_c, chk_c = EX.d_attribution_gate(
        out_a, out_b, ra["margin_clamped"], rb["margin_clamped"], clamped=True)
    assert chk_c["pass"] and "attn_attr" not in arrays_c
    assert abs(d_embed - (rb["embed_attr"] - ra["embed_attr"])) == 0.0


def test_gate_fails_when_the_margin_is_off(pair_q57):
    man_a, man_b, out_a, out_b = pair_q57
    ra, rb = man_a["readout"], man_b["readout"]
    assert not EX.d_attribution_gate(out_a, out_b, ra["margin"], rb["margin"] + 1e-5)[2]["pass"]


def test_existing_exports_are_consistent_if_present():
    """Every written 1.1 run has covering segments, and every written 1.1 pair passes its gate."""
    seen = 0
    for path in sorted((ROOT / "exports").glob("*.json")):
        if path.name == "index.json":
            continue
        m = json.loads(path.read_text())
        if m.get("schema") != "sca2-workbench/capture@1.1":
            continue
        seen += 1
        if m["kind"] == "run":
            I.check_segments(m["segments"], len(m["tokens"]))
        else:
            assert m["conservation"]["pass"] and m["conservation"]["d_attr_gap_float32"] < 1e-6
            assert {"d_head_attr", "d_mlp_attr", "d_attn_attr"} <= set(m["arrays"])
    if not seen:
        pytest.skip("no @1.1 exports written yet")
