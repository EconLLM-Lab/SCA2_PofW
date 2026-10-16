"""Scoring plan: pinned conditions, half split, Hub-based resume, spec hashes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import factorial as F  # noqa: E402
import score_plan as SPL  # noqa: E402

RUN = "bank2-heldout-v1-X"


def test_halves_partition_the_64_units_and_base_belongs_to_half_a():
    a, b = SPL.units_for_half("A"), SPL.units_for_half("B")
    assert len(a) == len(b) == 32 and not set(a) & set(b) and sorted(a + b) == sorted(F.all_units())
    assert SPL.scores_base("A") and not SPL.scores_base("B")


def _files(run, units, base=True, manifests=True):
    out = [f"runs/{run}/synthetic/{u}_adapter_option_probabilities.csv" for u in units]
    if manifests:
        out += [f"runs/{run}/manifests/{u}_adapter_manifest.json" for u in units]
    if base:
        out += [f"runs/{run}/synthetic/base_option_probabilities.csv", f"runs/{run}/manifests/base_manifest.json"]
    return out


def test_todo_skips_only_units_with_csv_and_manifest():
    a = SPL.units_for_half("A")
    files = _files(RUN, a[:3]) + [f"runs/{RUN}/synthetic/{a[3]}_adapter_option_probabilities.csv"]  # csv without manifest
    todo = SPL.todo_units(RUN, "A", files)
    assert todo["units"] == a[3:] and todo["base"] is False
    assert SPL.todo_units(RUN, "A", [])["base"] is True and len(SPL.todo_units(RUN, "A", [])["units"]) == 32


def test_todo_for_half_b_never_asks_for_base():
    assert SPL.todo_units(RUN, "B", [])["base"] is False


def test_complete_half_has_nothing_left():
    files = _files(RUN, SPL.units_for_half("A")) 
    todo = SPL.todo_units(RUN, "A", files)
    assert todo == {"units": [], "base": False}


def test_other_runs_files_do_not_count():
    files = _files("some-other-run", SPL.units_for_half("A"))
    assert len(SPL.todo_units(RUN, "A", files)["units"]) == 32


def test_conditions_have_distinct_run_ids_and_pinned_revision():
    ids = [c["run_id"] for c in SPL.CONDITIONS.values()]
    assert len(ids) == len(set(ids))
    assert len(SPL.ADAPTER_REVISION) == 40 and int(SPL.ADAPTER_REVISION, 16) >= 0
    for c in SPL.CONDITIONS.values():
        assert c["run_id"].replace("-", "").isalnum()


def test_built_specs_match_the_pinned_hashes():
    pins = json.loads((Path(__file__).resolve().parent / "score_plan_pins.json").read_text())
    for name in SPL.CONDITIONS:
        spec = SPL.build_spec(name)
        assert SPL.spec_hash(spec) == pins["spec_sha256"][name], name
    # Amendment 1 (PREREGISTRATION.md section 11) repaired 12 item texts, which changed every held-out spec
    # hash. The pin must equal what the preregistration amendment records, so read it from there rather than
    # hard-coding a value that a later amendment would silently invalidate.
    prereg = (Path(__file__).resolve().parent / "heldout" / "PREREGISTRATION.md").read_text()
    line = next(l for l in prereg.splitlines() if l.strip().startswith("heldout_v1 spec_sha256"))
    assert pins["spec_sha256"]["heldout_v1"] == line.split()[-1]
    assert not pins["spec_sha256"]["heldout_v1"].startswith("4d799b029102d7e7")   # the superseded pre-amendment spec


def test_heldout_specs_cover_the_223_pool_items_and_none_of_the_strict_items():
    spec = SPL.build_spec("heldout_v1")
    ids = [q["question_id"] for q in spec["questions"]]
    assert len(ids) == 223 and len(set(ids)) == 223
    strict = {q["question_id"] for q in SPL.build_spec("strict_v1")["questions"]}
    assert not set(ids) & strict


def test_score_cohort_args_cover_base_only_units_only_and_both():
    both = SPL.score_cohort_args("r", "s.json", "m.json", {"units": ["P_0_0_0_0_0_0"], "base": True})
    assert both[both.index("--arms") + 1] == "base,adapter" and both[both.index("--countries") + 1] == "P_0_0_0_0_0_0"
    only_units = SPL.score_cohort_args("r", "s.json", "m.json", {"units": ["P_0_0_0_0_0_0"], "base": False})
    assert only_units[only_units.index("--arms") + 1] == "adapter"
    only_base = SPL.score_cohort_args("r", "s.json", "m.json", {"units": [], "base": True})
    assert only_base[only_base.index("--arms") + 1] == "base" and "--countries" not in only_base
    assert SPL.score_cohort_args("r", "s.json", "m.json", {"units": [], "base": False}) == []
    assert both[both.index("--adapter-revision") + 1] == SPL.ADAPTER_REVISION


# ---- verifier F1: the gate unit belongs to the half, and the marker is checked against the half
def test_gate_unit_is_in_its_own_half():
    for half in "AB":
        assert SPL.gate_unit(half) in SPL.units_for_half(half)
    assert SPL.gate_unit("A") != SPL.gate_unit("B")


def _marker(**kw):
    m = {"gate_pass": True, "unit": SPL.gate_unit("A"), "adapter_revision": SPL.ADAPTER_REVISION}
    m.update(kw)
    return m


def test_check_marker_accepts_a_matching_marker():
    SPL.check_marker(_marker(), "A")


@pytest.mark.parametrize("bad", [{"gate_pass": False}, {"unit": "P_1_1_1_1_1_1"}, {"unit": None},
                                 {"adapter_revision": "0" * 40}, {"adapter_revision": ""}])
def test_check_marker_refuses_a_marker_that_does_not_cover_the_half(bad):
    with pytest.raises(RuntimeError):
        SPL.check_marker(_marker(**bad), "A")


def test_marker_from_the_other_half_is_refused():
    with pytest.raises(RuntimeError, match="not in half"):
        SPL.check_marker(_marker(unit=SPL.gate_unit("B")), "A")
