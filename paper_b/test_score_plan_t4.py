"""Card T4: the sign-prompt strict cell over all 64 profiles, and the scored unseeded replicate (r1).

New conditions are additive: every earlier condition keeps its run id, its spec pin and its place in ORDER.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import factorial as F  # noqa: E402
import protocol_bank2 as P2  # noqa: E402
import score_plan as SPL  # noqa: E402

NEW = {
    "signprompt_strict_v1": "bank2-signprompt-strict-v1-20261018",
    "replicate_strict_v1": "bank2-replicate-r1-strict-v1-20261018",
    "replicate_heldout_v1": "bank2-replicate-r1-heldout-v1-20261018",
}
OLD_RUN_IDS = {
    "strict_v1": "bank2-strict-v1-20261016",
    "heldout_v1": "bank2-heldout-v1-20261016",
    "heldout_reverse": "bank2-heldout-reverse-20261016",
    "heldout_para_a": "bank2-heldout-para-a-20261016",
    "heldout_para_b": "bank2-heldout-para-b-20261016",
    "signprompt_heldout_v1": "bank2-signprompt-heldout-v1-20261016",
}
OLD_PINS = {   # literal copy of score_plan_pins.json before this card; append-only means these never move
    "strict_v1": "ed3bb964b606a163c792a68eea2ea9e6cc679bb724ead6726c173f36d9a1fbf6",
    "heldout_v1": "46447de63f7cc161c016bdc38a3a7c9e8d351be308c44cf1ccd28d9091d13b38",
    "heldout_reverse": "d30bc4aa67d15430e52e09fdd2f8dd621a4b6aeee1559b6e26abf61a22d87e6c",
    "heldout_para_a": "cbd63283b4d99f6b41a6119148821a56093acb2296845f0662c4185c2f115f47",
    "heldout_para_b": "0680dffbf3d5c67bdf040a93d8454fc3de1ec08e04afdd8fd49360a6d8b30934",
    "signprompt_heldout_v1": "46447de63f7cc161c016bdc38a3a7c9e8d351be308c44cf1ccd28d9091d13b38",
}
ORDER_BEFORE = ["strict_v1", "heldout_v1", "signprompt_heldout_v1", "heldout_reverse", "heldout_para_a",
                "heldout_para_b"]


def _pins():
    return json.loads(SPL.PINS.read_text())


def test_existing_conditions_keep_run_ids_order_and_pins():
    for name, run_id in OLD_RUN_IDS.items():
        assert SPL.CONDITIONS[name]["run_id"] == run_id
        assert _pins()["spec_sha256"][name] == OLD_PINS[name]
    assert SPL.ORDER == ORDER_BEFORE                      # the half-A / half-B launchers read ORDER


def test_new_conditions_have_the_card_run_ids():
    for name, run_id in NEW.items():
        assert SPL.CONDITIONS[name]["run_id"] == run_id
    assert len({c["run_id"] for c in SPL.CONDITIONS.values()}) == len(SPL.CONDITIONS)


def test_new_conditions_resolve_to_the_pinned_spec_hashes():
    pins = _pins()["spec_sha256"]
    for name in NEW:
        assert pins[name] == SPL.spec_hash(SPL.build_spec(name)), name
    assert pins["signprompt_strict_v1"].startswith("ed3bb964")
    assert pins["replicate_strict_v1"].startswith("ed3bb964")
    assert pins["replicate_heldout_v1"].startswith("46447de6")
    assert pins["signprompt_strict_v1"] == pins["strict_v1"]
    assert pins["replicate_heldout_v1"] == pins["heldout_v1"]


def test_signprompt_covers_all_64_units_and_replicate_exactly_one():
    assert SPL.condition_units("signprompt_strict_v1") == F.all_units()
    assert SPL.CONDITIONS["signprompt_strict_v1"]["kind"] == "signprompt"
    for name in ("replicate_strict_v1", "replicate_heldout_v1"):
        assert SPL.condition_units(name) == [SPL.REPLICATE_UNIT]
        assert SPL.CONDITIONS[name]["kind"] == "adapter" and SPL.CONDITIONS[name]["replicate"] == "r1"
    assert SPL.REPLICATE_UNIT in F.all_units()
    with pytest.raises(ValueError):
        SPL.condition_units("strict_v1")                  # half-split conditions have no unit list of their own


def _fake_config(tmp_path, monkeypatch, replicate_env):
    run_id = "gps_sign_relabel_bank2_test"
    for name, units in (("bank", None), ("profiles", F.all_units())):
        d = tmp_path / name
        d.mkdir()
        body = {"run_id": run_id, "labeling_rule": "deterministic_sign", "n_triplets": 650,
                "per_dimension_triplet_counts": {k: 108 for k in F.DIMS}}
        if units:
            body["units"] = units
        (d / "manifest.json").write_text(json.dumps(body))
    for k, v in {"SCA2_PB_PROTOCOL": "bank2", "SCA2_PB_UNITS": "profiles", "SCA2_PB_DATA_ROOT": str(tmp_path / "root"),
                 "SCA2_PB_BANK2_DIR": str(tmp_path / "bank"), "SCA2_PB_PROFILE_DIR": str(tmp_path / "profiles")}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("SCA2_PB_REPLICATE", raising=False)
    for k, v in replicate_env.items():
        monkeypatch.setenv(k, v)
    cfg = types.SimpleNamespace(REPO=tmp_path, TRAIN_FRAC=0.8)
    P2.apply(cfg)
    return run_id, cfg


def test_replicate_conditions_resolve_to_the_replicates_r1_hub_prefix(tmp_path, monkeypatch):
    env = SPL.condition_env("replicate_strict_v1")
    assert env == {"SCA2_PB_REPLICATE": "r1"} == SPL.condition_env("replicate_heldout_v1")
    run_id, cfg = _fake_config(tmp_path, monkeypatch, env)
    assert cfg.HF_ADAPTER_PREFIX == f"bank2/{run_id}/replicates/r1/profiles"
    assert P2.hub_adapter_path_from_prefix(cfg.HF_ADAPTER_PREFIX, SPL.REPLICATE_UNIT) == (
        f"bank2/{run_id}/replicates/r1/profiles/{SPL.REPLICATE_UNIT}")


def test_other_conditions_never_get_the_replicate_switch(tmp_path, monkeypatch):
    for name in ("strict_v1", "heldout_v1", "signprompt_strict_v1"):
        assert SPL.condition_env(name) == {}
    run_id, cfg = _fake_config(tmp_path, monkeypatch, SPL.condition_env("signprompt_strict_v1"))
    assert cfg.HF_ADAPTER_PREFIX == f"bank2/{run_id}/profiles"


# ---- resume: spec-aware, per unit
def _files(run, units, model=lambda u: u, manifests=True):
    out = [f"runs/{run}/synthetic/{model(u)}_option_probabilities.csv" for u in units]
    if manifests:
        out += [f"runs/{run}/manifests/{model(u)}_manifest.json" for u in units]
    return out


def _reader(sha):
    return lambda run_id, model: {"spec_sha256": sha}


def test_todo_condition_signprompt_needs_csv_manifest_and_the_spec():
    run = SPL.CONDITIONS["signprompt_strict_v1"]["run_id"]
    units = F.all_units()
    assert SPL.todo_condition("signprompt_strict_v1", [], "s", _reader("s")) == units
    done = _files(run, units[:10])
    assert SPL.todo_condition("signprompt_strict_v1", done, "s", _reader("s")) == units[10:]
    assert SPL.todo_condition("signprompt_strict_v1", done, "s", _reader("other")) == units   # wrong spec: redo
    assert SPL.todo_condition("signprompt_strict_v1", _files(run, units, manifests=False), "s", _reader("s")) == units
    assert SPL.todo_condition("signprompt_strict_v1", _files(run, units), "s", _reader("s")) == []


def test_todo_condition_replicate_names_the_adapter_model():
    name = "replicate_strict_v1"
    run = SPL.CONDITIONS[name]["run_id"]
    files = _files(run, [SPL.REPLICATE_UNIT], model=lambda u: f"{u}_adapter")
    assert SPL.todo_condition(name, files, "s", _reader("s")) == []
    assert SPL.todo_condition(name, files, "s", _reader("x")) == [SPL.REPLICATE_UNIT]
    assert SPL.todo_condition(name, _files(run, [SPL.REPLICATE_UNIT]), "s", _reader("s")) == [SPL.REPLICATE_UNIT]
    with pytest.raises(ValueError, match="manifest reader"):
        SPL.todo_condition(name, files, "s", None)


# ---- the gate marker must name the work it authorises
def _marker(**kw):
    m = {"gate_pass": True, "unit": SPL.REPLICATE_UNIT, "adapter_revision": SPL.ADAPTER_REVISION,
         "adapter_sha256": "abc"}
    m.update(kw)
    return m


def test_replicate_marker_must_carry_the_replicate_weights():
    SPL.check_marker_for("replicate_strict_v1", _marker(), replicate_adapter_sha="abc")
    for bad, sha in (({"adapter_sha256": "zzz"}, "abc"),            # marker gated other weights (the original unit)
                     ({}, None),                                    # nothing to compare against: refuse
                     ({"unit": F.all_units()[0]}, "abc"),
                     ({"gate_pass": False}, "abc"),
                     ({"adapter_revision": "0" * 40}, "abc")):
        with pytest.raises(RuntimeError):
            SPL.check_marker_for("replicate_heldout_v1", _marker(**bad), replicate_adapter_sha=sha)


def test_signprompt_marker_needs_a_pass_the_pinned_revision_and_a_real_unit():
    SPL.check_marker_for("signprompt_strict_v1", _marker())
    for bad in ({"gate_pass": False}, {"adapter_revision": ""}, {"unit": "P_2_0_0_0_0_0"}, {"unit": None}):
        with pytest.raises(RuntimeError):
            SPL.check_marker_for("signprompt_strict_v1", _marker(**bad))


# ---- the launch chain
def test_t4_steps_gate_the_replicate_first_and_give_each_condition_its_own_env():
    steps = SPL.t4_steps()
    names = [s[0] for s in steps]
    assert names == ["t4_gate"] + [f"t4_{c}" for c in SPL.T4_ORDER]
    assert sorted(SPL.T4_ORDER) == sorted(NEW)
    gate_name, gate_args, gate_env = steps[0]
    assert gate_args == ["paper_b/colab/vm_gate_factorial.py"]
    assert gate_env["GATE_UNIT"] == SPL.REPLICATE_UNIT and gate_env["SCA2_PB_REPLICATE"] == "r1"
    assert gate_env["SCA2_PB_ADAPTER_REVISION"] == SPL.ADAPTER_REVISION
    assert gate_env["SCORE_RUN_ID"] not in {c["run_id"] for c in SPL.CONDITIONS.values()}   # never a scoring run id
    for (n, args, env), cond in zip(steps[1:], SPL.T4_ORDER):
        assert args == ["paper_b/colab/vm_score_t4.py", cond]
        assert env == SPL.condition_env(cond)
    assert "SCA2_PB_REPLICATE" not in steps[names.index("t4_signprompt_strict_v1")][2]
