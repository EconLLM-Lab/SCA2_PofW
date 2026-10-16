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
    assert pins["spec_sha256"]["heldout_v1"].startswith("4d799b029102d7e7")     # equals the preregistration


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
