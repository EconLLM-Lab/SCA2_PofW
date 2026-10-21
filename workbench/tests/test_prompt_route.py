"""W2 prompt route: base model + a sign-profile prompt (A') paired against the phase-1 base run (A).

The unit kind is `base` + `--prompt-profile <id>`. Tests cover the vendored prompts, the Item built from
them, the unit tag/marker, the A-side loader, the prompt pair gate and the queue plan.
"""
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pytest
import torch

from sca2_workbench import cohort as C
from sca2_workbench import items as I
from sca2_workbench import sign_route as SR
from sca2_workbench import stream_export as SE

MAIN_SIGN_PROMPT = Path(os.environ.get(
    "SCA2_MAIN_WORKTREE", "/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")) / "paper_b" / "sign_prompt.py"


def _items():
    return json.loads((C.PACKAGE / "items.json").read_text())["items"]


# ---- the 26 vendored prompts ----

def test_vendored_profiles_are_26_unique_hash_checked_and_carry_no_country_membership():
    profiles = SR.load_profiles()
    assert len(profiles) == 26
    for pid, p in profiles.items():
        assert hashlib.sha256(p["prompt"].encode()).hexdigest() == p["prompt_sha256"]
        assert set(p) == {"profile_id", "signs", "prompt", "prompt_sha256", "archive"}   # no "members"
        assert {x["item_id"] for x in _items()} == set(p["archive"])
    assert len({p["prompt"] for p in profiles.values()}) == 26
    raw = (C.PACKAGE / "sign_profiles.json").read_text()
    assert "members" not in raw


def test_load_refuses_a_prompt_whose_hash_differs(tmp_path):
    doc = json.loads((C.PACKAGE / "sign_profiles.json").read_text())
    doc["profiles"][0]["prompt"] += " "
    path = tmp_path / "p.json"
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="sha256"):
        SR.load_profiles(path)


@pytest.mark.skipif(not MAIN_SIGN_PROMPT.exists(), reason="main worktree not on this machine")
def test_vendored_prompts_are_byte_identical_to_the_paper_b_module():
    """Build-time check only: the capture never imports across worktrees."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("paper_b_sign_prompt_check", MAIN_SIGN_PROMPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    doc = json.loads((C.PACKAGE / "sign_profiles.json").read_text())
    assert doc["source_module_sha256"] == hashlib.sha256(MAIN_SIGN_PROMPT.read_bytes()).hexdigest()
    for p in doc["profiles"]:
        assert mod.sign_prompt(p["signs"]) == p["prompt"]
        assert mod.profile_id(p["signs"]) == p["profile_id"]
        assert not mod.leak_hits(p["prompt"])


# ---- tag, marker, item ----

def test_unit_tag_roundtrips_and_marker_names_are_unique_over_the_598_units():
    profiles = SR.load_profiles()
    tags = {SR.unit_tag(pid): pid for pid in profiles}
    assert len(tags) == 26 and all(t.startswith("base_sp") for t in tags)
    assert all(SR.profile_of_tag(t) == pid for t, pid in tags.items())
    assert SR.profile_of_tag("base") is None and SR.profile_of_tag("ARG") is None
    markers = {f"nf4_dequant_float64_{t}_{i['item_id']}.json" for t in tags for i in _items()}
    assert len(markers) == 26 * 23 == 598


def test_sign_item_is_the_paper_b_combined_prompt_and_keeps_item_identity():
    profile = next(iter(SR.load_profiles().values()))
    base = I.Item(item_id="wvs_Q57", kind="wvs", user_prompt=I.survey_prompt_v1("Q?", ("1", "2"), ("a", "b")),
                  codes=("1", "2"), labels=("a", "b"), j_plus="1", j_minus="2",
                  parts=I.survey_prompt_parts("Q?", ("1", "2"), ("a", "b"), "WVS question"))
    got = SR.sign_item(base, profile)
    assert got.user_prompt == profile["prompt"].rstrip() + "\n\n" + base.user_prompt
    assert "".join(t for _, _, t in got.parts) == got.user_prompt
    assert got.parts[0][0] == "instruction" and got.parts[1:] == base.parts
    assert (got.item_id, got.codes, got.j_plus, got.j_minus) == (base.item_id, base.codes, "1", "2")
    assert got.meta["prompt_profile"] == profile["profile_id"]


def _llama_tokenizer():
    from transformers import AutoTokenizer
    try:
        return AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B-Instruct", local_files_only=True)
    except Exception:
        pytest.skip("Llama-3.1 tokenizer not cached")


def test_every_profile_item_prompt_has_clean_segments_and_a_one_token_readout():
    tok = _llama_tokenizer()
    profiles = SR.load_profiles()
    for rec in _items()[:3]:
        base = I.Item(**{**{k: v for k, v in rec.items() if k != "archive"}, "codes": tuple(rec["codes"]),
                         "labels": tuple(rec["labels"]), "parts": tuple(tuple(x) for x in rec["parts"])})
        plain = I.readout_ids(tok, base, {"date_string": "26 Jul 2024"})
        for p in profiles.values():
            item = SR.sign_item(base, p)
            ro = I.readout_ids(tok, item, {"date_string": "26 Jul 2024"})
            segs = I.prompt_segments(tok, item, ro)          # raises on a straddling token or a gap
            assert [s["label"] for s in segs if s["label"] == "sign profile"] == ["sign profile"]
            assert ro["code_token"] == plain["code_token"] and ro["prefix_ids"] == plain["prefix_ids"]
            # the item's own tokens are the tail of A' (only the sign text is inserted)
            assert ro["prompt_ids"][-8:] == plain["prompt_ids"][-8:]


def test_archive_for_returns_the_paper_b_sign_prompt_scores_on_the_fp16_grid():
    pid, p = next(iter(SR.load_profiles().items()))
    got = SR.archive_for(pid, "wvs_Q43")
    assert set(got) == {"source", "probs", "logprobs"} and set(got["probs"]) == {"1", "2", "3"}
    assert all(float(np.float16(v)) == v for v in got["logprobs"].values())
    with pytest.raises(KeyError):
        SR.archive_for("9_9_9_9_9_9", "wvs_Q43")


# ---- the A side: the phase-1 base run ----

def _fake_phase1_base(root, item="q1", passed=True, L=2, H=2):
    key = "llama31_8b_nf4_dequant_float64_cpu_deadbeef_46079e27"
    from sca2_workbench import export as EX
    b = EX.BinWriter()
    arrs = {"head_attr": np.arange(L * H, dtype=np.float32).reshape(L, H) / 10,
            "mlp_attr": np.array([.5, -.25], np.float32), "attn_attr": np.array([.6, .4], np.float32),
            "head_attr_clamped": np.ones((L, H), np.float32) / 7, "mlp_attr_clamped": np.array([.1, .2], np.float32)}
    for name, a in arrs.items():
        b.add(name, a, name)
    man = {"kind": "run", "model": {"key": key}, "item": {"item_id": item}, "tokens": [{"id": 1}, {"id": 2}],
           "readout": {"margin": 1., "margin_clamped": 2., "embed_attr": .125, "embed_attr_clamped": .25,
                       "probs": {"1": .5, "2": .5}}, "arrays": b.meta, "bin": f"run__{key}__{item}.bin",
           "provenance": {"instrument": {"files": {"x": "y"}}}, "conservation": {"pass": True}}
    C.publish(root / f"run__{key}__{item}.json", C.json_bytes(man))
    C.publish(root / f"run__{key}__{item}.bin", b"".join(b.parts))
    names = [f"run__{key}__{item}.json", f"run__{key}__{item}.bin"]
    rec = {"identity": "i", "pass": passed, "inputs": {"source_digest": "S"},
           "files": {n: C.digest(root / n) for n in names}}
    C.publish(root / "units" / f"nf4_dequant_float64_base_{item}.json", C.json_bytes(rec))
    return key, arrs


def test_baseline_loader_returns_float64_attributions_and_checks_every_digest(tmp_path):
    key, arrs = _fake_phase1_base(tmp_path)
    got = SR.load_baseline(tmp_path, "q1")
    assert got["key"] == key and got["manifest"]["model"]["key"] == key
    assert got["out"]["head_attr"].dtype == torch.float64
    np.testing.assert_array_equal(got["out"]["head_attr"].numpy(), arrs["head_attr"].astype(np.float64))
    assert got["out"]["embed_attr"] == .125 and got["out"]["_clamped_attr"]["embed_attr"] == .25
    assert set(got["files"]) == {f"run__{key}__q1.json", f"run__{key}__q1.bin"}
    (tmp_path / f"run__{key}__q1.bin").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="digest"):
        SR.load_baseline(tmp_path, "q1")


def test_baseline_loader_refuses_a_missing_or_failed_base_unit(tmp_path):
    with pytest.raises(ValueError, match="baseline"):
        SR.load_baseline(tmp_path, "q1")
    _fake_phase1_base(tmp_path, passed=False)
    with pytest.raises(ValueError, match="baseline"):
        SR.load_baseline(tmp_path, "q1")


# ---- the prompt pair ----

def _out(head, mlp, embed, attn=None):
    return {"head_attr": torch.tensor(head, dtype=torch.float64), "mlp_attr": torch.tensor(mlp, dtype=torch.float64),
            "embed_attr": embed, "attn_attr": torch.tensor(attn or [sum(r) for r in head], dtype=torch.float64)}


def _pair(margin_b, tokens_b=(1, 2, 3, 4)):
    a, ac = _out([[.1, .2]], [.3], .4), _out([[.0, .1]], [.2], .3)
    b, bc = _out([[.2, .2]], [.5], .6), _out([[.1, .1]], [.3], .5)
    man_a = {"tokens": [{"id": 1}, {"id": 2}], "readout": {"margin": 1.0, "margin_clamped": .6, "probs": {"1": .5, "2": .5}}}
    man_b = {"tokens": [{"id": t} for t in tokens_b],
             "readout": {"margin": margin_b, "margin_clamped": 1.0, "probs": {"1": .7, "2": .3}}}
    return SE.prompt_pair_manifest(key_a="a", key_b="b", item_id="q1", man_a=man_a, man_b=man_b,
                                   out_a=a, out_a_clamped=ac, out_b=b, out_b_clamped=bc,
                                   run_files={"a": "run__a__q1.json", "b": "run__b__q1.json"},
                                   profile_id="0_1_0_1_0_1", retain_failed=True)


def test_prompt_pair_allows_different_token_streams_and_records_the_route():
    # A attrs sum 1.0, A' attrs sum 1.5; clamped sums .6 and 1.0
    man, binary = _pair(1.5)
    assert man["kind"] == "pair" and man["route"] == "prompt" and man["prompt_profile"] == "0_1_0_1_0_1"
    assert man["conservation"]["pass"] is True
    assert man["d_probs"] == {"1": pytest.approx(.2), "2": pytest.approx(-.2)}
    assert man["d_margin"] == pytest.approx(.5) and man["d_margin_clamped"] == pytest.approx(.4)
    assert set(man["arrays"]) == {"d_head_attr", "d_mlp_attr", "d_attn_attr", "d_head_attr_clamped",
                                  "d_mlp_attr_clamped"}      # no per-token norms, no weight deltas: A and A' differ in T
    assert man["tokens"] == {"a": 2, "b": 4}


def test_prompt_pair_gate_is_not_weakened_a_wrong_sum_fails():
    man, _ = _pair(1.7)             # attributions still sum to 1.5, so the B - A margin is 0.2 off
    assert man["conservation"]["pass"] is False
    with pytest.raises(AssertionError, match="attributions"):
        SE.prompt_pair_manifest(key_a="a", key_b="b", item_id="q1",
                                man_a={"tokens": [], "readout": {"margin": 1., "margin_clamped": .6, "probs": {"1": .5}}},
                                man_b={"tokens": [], "readout": {"margin": 9., "margin_clamped": .9, "probs": {"1": .5}}},
                                out_a=_out([[.1]], [.1], .1), out_a_clamped=_out([[.1]], [.1], .1),
                                out_b=_out([[.1]], [.1], .1), out_b_clamped=_out([[.1]], [.1], .1),
                                run_files={}, profile_id="x")


# ---- queue ----

def _queue():
    import importlib.util
    import sys
    sys.path.insert(0, str(C.PACKAGE / "runner"))        # the runner scripts import their siblings
    spec = importlib.util.spec_from_file_location("mac_queue_route_test", C.PACKAGE / "runner" / "mac_queue.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_route_plan_is_26_profiles_by_23_items_and_each_unit_is_a_base_unit():
    q = _queue()
    items = _items()
    keys, got = q.plan_route(SR.load_profiles(), items)
    assert len(keys) == 26 and len(got) == 23 and len(keys) * len(got) == 598
    assert all(SR.profile_of_tag(k) for k in keys)
    assert q.wall_limit(keys[0]) == pytest.approx(4 * 65.0) and q.wall_limit("base") == pytest.approx(4 * 32.5) and q.wall_limit("ARG") == pytest.approx(4 * 65.3)


def test_route_unit_command_carries_the_profile_and_the_baseline(tmp_path):
    q = _queue()
    pid = sorted(SR.load_profiles())[3]
    cmd = q.unit_command("base_sp" + pid.replace("_", ""), "wvs_Q57", root=tmp_path, frozen=tmp_path / "f",
                         baseline=tmp_path / "phase1")
    assert cmd[cmd.index("--model") + 1] == "base" and cmd[cmd.index("--prompt-profile") + 1] == pid
    assert cmd[cmd.index("--baseline") + 1] == str(tmp_path / "phase1")
    plain = q.unit_command("ARG", "wvs_Q57", root=tmp_path, frozen=tmp_path / "f", baseline=None)
    assert "--prompt-profile" not in plain and "--baseline" not in plain


def test_unit_tag_function_gives_the_marker_stem_for_both_kinds():
    pid = sorted(SR.load_profiles())[0]
    assert C.unit_tag("ARG", None) == "ARG" and C.unit_tag("base", None) == "base"
    assert C.unit_tag("base", pid) == SR.unit_tag(pid)
    with pytest.raises(ValueError, match="base"):
        C.unit_tag("ARG", pid)           # a prompt route unit is the base model, never an adapter


def test_prompt_pair_rejects_an_incompatible_readout():
    a = _out([[.1]], [.2], .3)
    ma = {"tokens": [], "item": {"item_id": "q1", "j_plus": "1", "j_minus": "2"},
          "readout": {"code_token": {"1": 16, "2": 17}, "margin": .6,
                      "margin_clamped": .6, "probs": {"1": .5, "2": .5}}}
    import copy
    mb = copy.deepcopy(ma)
    mb["readout"]["code_token"]["1"] = 18
    with pytest.raises(ValueError, match="readout"):
        SE.prompt_pair_manifest(key_a="a", key_b="b", item_id="q1", man_a=ma, man_b=mb,
                                out_a=a, out_b=a, out_a_clamped=a, out_b_clamped=a,
                                run_files={}, profile_id="x")


def test_real_streamed_run_manifests_form_a_different_token_prompt_pair(tmp_path):
    """Exercise actual model outputs -> run manifests/binaries -> baseline loader -> pair."""
    from transformers import AutoTokenizer
    from sca2_workbench import stream_capture as SC, gates as G, llama_capture as LC
    snaps = sorted((Path.home() / ".cache/huggingface/hub/models--HuggingFaceTB--SmolLM2-135M-Instruct").glob(
        "snapshots/*/model.safetensors"))
    if not snaps:
        pytest.skip("SmolLM2 fixture weights not cached")
    tok = AutoTokenizer.from_pretrained(snaps[0].parent, local_files_only=True)
    rec = _items()[0]
    base = I.Item(**{**{k: v for k, v in rec.items() if k != "archive"}, "codes": tuple(rec["codes"]),
                     "labels": tuple(rec["labels"]), "parts": tuple(tuple(x) for x in rec["parts"])})
    profile = next(iter(SR.load_profiles().values()))
    runs, outs, files = {}, {}, {}
    for arm, item in (("a", base), ("b", SR.sign_item(base, profile))):
        ro = I.readout_ids(tok, item)
        src = SC.SafetensorsSource(snaps[0].parent)
        plain, clamped = SC.run_streamed(src, ro["prompt_ids"], j_plus=ro["code_token"][item.j_plus],
                                         j_minus=ro["code_token"][item.j_minus], clamps=(False, True), full_logits=True)
        man, bw = SE.run_manifest(key=arm, label=arm, model_id="SmolLM2 fixture", src=src, tok=tok,
                                 item=item, ro=ro, plain=plain, clamped=clamped, taus=G.TAUS_F64,
                                 hf_logits_last=plain["logits_last"],
                                 paper_b_probs=LC.code_probs(plain["logits_last"], ro["code_token"]),
                                 parity_tau=1e-4, stats={}, chat_kwargs={})
        man["bin"] = f"run__{arm}__{item.item_id}.bin"
        name = f"run__{arm}__{item.item_id}.json"
        C.publish(tmp_path / name, C.json_bytes(man))
        C.publish(tmp_path / man["bin"], b"".join(bw.parts))
        runs[arm], outs[arm], files[arm] = man, (plain, clamped), name
    names = [files["a"], runs["a"]["bin"]]
    C.publish(tmp_path / "units" / f"nf4_dequant_float64_base_{base.item_id}.json",
              C.json_bytes({"pass": True, "files": {n: C.digest(tmp_path / n) for n in names}}))
    a = SR.load_baseline(tmp_path, base.item_id)
    pair, bw = SE.prompt_pair_manifest(key_a="a", key_b="b", item_id=base.item_id,
                                      man_a=a["manifest"], man_b=runs["b"], out_a=a["out"],
                                      out_a_clamped=a["out"]["_clamped_attr"], out_b=outs["b"][0],
                                      out_b_clamped=outs["b"][1], run_files=files, profile_id=profile["profile_id"])
    assert pair["conservation"]["pass"]
    assert pair["tokens"]["b"] > pair["tokens"]["a"]
    assert len(b"".join(bw.parts)) > 0
    assert not any("norm" in name or "weight" in name for name in pair["arrays"])
