"""Card C8: the country-named persona arm on the 42 cohort countries (design: planning/.../C8_PERSONA_DESIGN.md).

New conditions are additive: every earlier condition keeps its run id, its spec pin and its place in the orders.
"""
from __future__ import annotations

import ast
import json
import sys
import types
from pathlib import Path

import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import factorial as F  # noqa: E402
import protocol_bank2 as P2  # noqa: E402
import score_plan as SPL  # noqa: E402

NAME = "persona_strict_v1"
PINS_BEFORE = {   # literal copy of score_plan_pins.json before card C8; append-only means these never move
    "strict_v1": "ed3bb964b606a163c792a68eea2ea9e6cc679bb724ead6726c173f36d9a1fbf6",
    "heldout_v1": "46447de63f7cc161c016bdc38a3a7c9e8d351be308c44cf1ccd28d9091d13b38",
    "heldout_reverse": "d30bc4aa67d15430e52e09fdd2f8dd621a4b6aeee1559b6e26abf61a22d87e6c",
    "heldout_para_a": "cbd63283b4d99f6b41a6119148821a56093acb2296845f0662c4185c2f115f47",
    "heldout_para_b": "0680dffbf3d5c67bdf040a93d8454fc3de1ec08e04afdd8fd49360a6d8b30934",
    "signprompt_heldout_v1": "46447de63f7cc161c016bdc38a3a7c9e8d351be308c44cf1ccd28d9091d13b38",
    "signprompt_strict_v1": "ed3bb964b606a163c792a68eea2ea9e6cc679bb724ead6726c173f36d9a1fbf6",
    "replicate_strict_v1": "ed3bb964b606a163c792a68eea2ea9e6cc679bb724ead6726c173f36d9a1fbf6",
    "replicate_heldout_v1": "46447de63f7cc161c016bdc38a3a7c9e8d351be308c44cf1ccd28d9091d13b38",
    "nearzero_strict_v1": "ed3bb964b606a163c792a68eea2ea9e6cc679bb724ead6726c173f36d9a1fbf6",
}
RUN_IDS_BEFORE = {
    "strict_v1": "bank2-strict-v1-20261016", "heldout_v1": "bank2-heldout-v1-20261016",
    "heldout_reverse": "bank2-heldout-reverse-20261016", "heldout_para_a": "bank2-heldout-para-a-20261016",
    "heldout_para_b": "bank2-heldout-para-b-20261016", "signprompt_heldout_v1": "bank2-signprompt-heldout-v1-20261016",
    "signprompt_strict_v1": "bank2-signprompt-strict-v1-20261018",
    "replicate_strict_v1": "bank2-replicate-r1-strict-v1-20261018",
    "replicate_heldout_v1": "bank2-replicate-r1-heldout-v1-20261018",
    "nearzero_strict_v1": "bank2-nearzero-strict-v1-20261018",
}


def _pins():
    return json.loads(SPL.PINS.read_text())


def _config_cohort_literal() -> list[str]:
    """The COHORT list as written in config.py (the module value is rebound under SCA2_PB_UNITS=profiles)."""
    tree = ast.parse((HERE / "config.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "COHORT" for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("COHORT literal not found in config.py")


# ---- additivity
def test_earlier_conditions_keep_run_ids_pins_and_orders():
    for name, run_id in RUN_IDS_BEFORE.items():
        assert SPL.CONDITIONS[name]["run_id"] == run_id
        assert _pins()["spec_sha256"][name] == PINS_BEFORE[name], name
    assert _pins()["adapter_revision"] == SPL.ADAPTER_REVISION
    assert SPL.ORDER == ["strict_v1", "heldout_v1", "signprompt_heldout_v1", "heldout_reverse", "heldout_para_a",
                         "heldout_para_b"]
    assert SPL.T4_ORDER == ["replicate_strict_v1", "replicate_heldout_v1", "signprompt_strict_v1"]
    assert NAME not in SPL.ORDER and NAME not in SPL.T4_ORDER


# ---- the condition
def test_persona_condition_is_the_design_lock():
    c = SPL.CONDITIONS[NAME]
    assert c == {"run_id": "persona-strict-v1-20261019", "battery": "strict", "variant": "v1", "kind": "persona",
                 "units": SPL.PERSONA_COUNTRIES}
    assert len({x["run_id"] for x in SPL.CONDITIONS.values()}) == len(SPL.CONDITIONS)


def test_persona_units_are_the_42_cohort_countries_and_all_have_a_name():
    import eval_config as E
    assert SPL.condition_units(NAME) == _config_cohort_literal()
    assert len(SPL.PERSONA_COUNTRIES) == 42 == len(set(SPL.PERSONA_COUNTRIES))
    assert set(SPL.PERSONA_COUNTRIES) == set(E.COUNTRY_NAMES)
    assert not set(SPL.PERSONA_COUNTRIES) & set(F.all_units())


def test_persona_spec_is_the_strict_pin():
    pins = _pins()["spec_sha256"]
    assert pins[NAME] == PINS_BEFORE["strict_v1"] == SPL.spec_hash(SPL.build_spec(NAME))


def test_persona_prompt_is_the_preprint_sentence_and_only_the_first_sentence_changes():
    import eval_lib as L
    spec = SPL.build_spec(NAME)["questions"][0]
    plain = L.build_survey_user_prompt(spec)
    named = L.build_survey_user_prompt(spec, prompt_country="USA")
    assert named.startswith("Answer this questionnaire as a typical adult living in the United States. ")
    assert plain.startswith("Answer this questionnaire as an individual person. ")
    assert named.split(". ", 1)[1] == plain.split(". ", 1)[1]


# ---- environment: persona units are countries, never the 64 profiles
def _fake_config(tmp_path, monkeypatch, extra_env):
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
    monkeypatch.delenv("SCA2_PB_NEARZERO", raising=False)
    for k, v in extra_env.items():
        monkeypatch.setenv(k, v)
    cfg = types.SimpleNamespace(REPO=tmp_path, TRAIN_FRAC=0.8, COHORT=list(_config_cohort_literal()))
    P2.apply(cfg)
    return cfg


def test_persona_env_switches_units_back_to_countries(tmp_path, monkeypatch):
    env = SPL.condition_env(NAME)
    assert env == {"SCA2_PB_UNITS": "countries"}
    cfg = _fake_config(tmp_path, monkeypatch, env)
    assert cfg.UNITS == "countries" and cfg.COHORT == SPL.PERSONA_COUNTRIES


def test_without_the_switch_the_vm_default_would_make_the_personas_unknown(tmp_path, monkeypatch):
    cfg = _fake_config(tmp_path, monkeypatch, {})                 # the VM's child_env default is profiles
    assert cfg.COHORT == F.all_units()
    assert not set(SPL.PERSONA_COUNTRIES) & set(cfg.COHORT)


# ---- resume
def _files(run, models, manifests=True):
    out = [f"runs/{run}/synthetic/{m}_option_probabilities.csv" for m in models]
    if manifests:
        out += [f"runs/{run}/manifests/{m}_manifest.json" for m in models]
    return out


def _reader(sha):
    return lambda run_id, model: {"spec_sha256": sha}


def test_todo_persona_names_the_persona_models_and_needs_the_spec():
    run = SPL.CONDITIONS[NAME]["run_id"]
    units = SPL.PERSONA_COUNTRIES
    assert SPL.todo_condition(NAME, [], "s", _reader("s")) == units
    done = _files(run, [f"persona_{u}" for u in units[:5]])
    assert SPL.todo_condition(NAME, done, "s", _reader("s")) == units[5:]
    assert SPL.todo_condition(NAME, done, "s", _reader("x")) == units
    assert SPL.todo_condition(NAME, _files(run, units), "s", _reader("s")) == units          # bare unit names
    assert SPL.todo_condition(NAME, _files(run, [f"persona_{u}" for u in units], manifests=False), "s",
                              _reader("s")) == units
    assert SPL.todo_condition(NAME, _files(run, [f"persona_{u}" for u in units]), "s", _reader("s")) == []


# ---- marker
def _marker(**kw):
    m = {"gate_pass": True, "unit": SPL.PERSONA_GATE_UNIT, "adapter_revision": SPL.ADAPTER_REVISION,
         "adapter_sha256": "abc"}
    m.update(kw)
    return m


def test_persona_marker_needs_a_pass_the_pinned_revision_and_a_real_profile_unit():
    assert SPL.PERSONA_GATE_UNIT in F.all_units()
    SPL.check_marker_for(NAME, _marker())
    for bad in ({"gate_pass": False}, {"adapter_revision": "0" * 40}, {"unit": "P_2_0_0_0_0_0"}, {"unit": None},
                {"unit": "USA"}):
        with pytest.raises(RuntimeError):
            SPL.check_marker_for(NAME, _marker(**bad))


# ---- score_cohort arguments
def test_score_cohort_args_persona_arm():
    args = SPL.score_cohort_args("r", "s.json", "m.json", {"units": ["ARG", "USA"], "base": False}, arm="persona")
    assert args[args.index("--arms") + 1] == "persona"
    assert args[args.index("--countries") + 1:args.index("--countries") + 3] == ["ARG", "USA"]
    base_only = SPL.score_cohort_args("r", "s.json", "m.json", {"units": [], "base": True}, arm="persona")
    assert base_only[base_only.index("--arms") + 1] == "base" and "--countries" not in base_only
    with pytest.raises(ValueError):
        SPL.score_cohort_args("r", "s.json", "m.json", {"units": ["ARG"], "base": False}, arm="nonsense")
    default = SPL.score_cohort_args("r", "s.json", "m.json", {"units": ["P_0_0_0_0_0_0"], "base": True})
    assert default[default.index("--arms") + 1] == "base,adapter"


# ---- chain
def test_persona_steps_gate_first_then_score_with_the_country_switch():
    steps = SPL.persona_steps()
    assert [s[0] for s in steps] == ["persona_gate", "persona_score"]
    _, gate_args, gate_env = steps[0]
    assert gate_args == ["paper_b/colab/vm_gate_factorial.py"]
    assert gate_env["GATE_UNIT"] == SPL.PERSONA_GATE_UNIT
    assert gate_env["SCA2_PB_ADAPTER_REVISION"] == SPL.ADAPTER_REVISION
    assert gate_env["SCORE_RUN_ID"] == SPL.GATE_RUN_ID_PERSONA
    assert SPL.GATE_RUN_ID_PERSONA not in {c["run_id"] for c in SPL.CONDITIONS.values()}
    assert "SCA2_PB_UNITS" not in gate_env and "SCA2_PB_REPLICATE" not in gate_env   # the gate needs profiles
    _, score_args, score_env = steps[1]
    assert score_args == ["paper_b/colab/vm_score_t4.py", NAME]
    assert score_env == SPL.condition_env(NAME)


# ---- G3 base parity
def _base(n_q=3, n_opt=4):
    rows = []
    for q in range(n_q):
        lps = [-1.0 - 0.5 * j - q for j in range(n_opt)]
        z = sum(pow(2.718281828459045, v) for v in lps)
        for j, lp in enumerate(lps):
            rows.append({"question_id": f"Q{q + 1}", "option_code": str(j + 1), "option_logprob": lp,
                         "model_prob": pow(2.718281828459045, lp) / z})
    return pd.DataFrame(rows)


def test_base_parity_passes_on_identical_scores_and_records_zero():
    r = SPL.base_parity(_base(), _base())
    assert r["pass"] and r["max_dlogprob"] == 0.0 and r["max_dprob"] == 0.0 and r["n_rows"] == 12


def test_base_parity_fails_beyond_the_base_tolerance_and_passes_inside_it():
    new = _base()
    new.loc[0, "option_logprob"] += 0.02
    assert not SPL.base_parity(new, _base())["pass"]
    new = _base()
    new.loc[0, "option_logprob"] += 0.001
    r = SPL.base_parity(new, _base())
    assert r["pass"] and abs(r["max_dlogprob"] - 0.001) < 1e-12
    new = _base()
    new.loc[0, "model_prob"] += 0.001
    assert not SPL.base_parity(new, _base())["pass"]


def test_base_parity_refuses_different_option_grids():
    with pytest.raises(ValueError):
        SPL.base_parity(_base().iloc[1:], _base())
    other = _base()
    other.loc[0, "option_code"] = "9"
    with pytest.raises(ValueError):
        SPL.base_parity(other, _base())


def test_base_parity_fails_on_a_missing_value():
    new = _base()
    new.loc[3, "option_logprob"] = float("nan")
    r = SPL.base_parity(new, _base())
    assert not r["pass"] and r["n_nan"] == 1


def test_base_parity_reference_is_the_banked_strict_base():
    assert SPL.PERSONA_BASE_REFERENCE_RUN == SPL.CONDITIONS["strict_v1"]["run_id"]


# ---- the driver wires the switch into its children and runs G3 before any persona
def test_driver_passes_the_condition_env_to_children_and_checks_parity_before_personas():
    src = (HERE / "colab" / "vm_score_t4.py").read_text()
    assert "child_env(SCA2_PB_ADAPTER_REVISION=rev, **SPL.condition_env(cond))" in src
    assert src.index("SPL.base_parity(") < src.index('arm="persona"')
