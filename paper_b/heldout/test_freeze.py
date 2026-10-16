"""Freeze-guard tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import freeze as FR  # noqa: E402


def _files(tmp_path):
    sel = tmp_path / "selection.csv"
    sel.write_text("question_id,primary_selected\nQ150,True\nQ151,False\n")
    pool = tmp_path / "pool_skeleton.csv"
    pool.write_text("Question\nQ150\nQ151\n")
    return sel, pool


def test_freezing_records_hashes(tmp_path):
    sel, pool = _files(tmp_path)
    fr = FR.freeze(selection_path=sel, pool_path=pool, freeze_path=tmp_path / "FREEZE.json",
                   code_revision="deadbeef", run_ids={"heldout_v1": "bank2-heldout-v1"})
    assert len(fr["selection_sha256"]) == 64 and len(fr["pool_sha256"]) == 64
    assert fr["selected_items"] == 1 and fr["n_items"] == 2


def test_refreezing_is_refused(tmp_path):
    sel, pool = _files(tmp_path)
    kw = dict(selection_path=sel, pool_path=pool, freeze_path=tmp_path / "FREEZE.json",
              code_revision="x", run_ids={})
    FR.freeze(**kw)
    with pytest.raises(RuntimeError, match="already frozen"):
        FR.freeze(**kw)


def test_human_read_refused_before_freeze(tmp_path):
    with pytest.raises(RuntimeError, match="FREEZE"):
        FR.require_freeze(tmp_path / "FREEZE.json")


def test_human_read_refused_if_selection_changed(tmp_path):
    sel, pool = _files(tmp_path)
    f = tmp_path / "FREEZE.json"
    FR.freeze(selection_path=sel, pool_path=pool, freeze_path=f, code_revision="x", run_ids={})
    sel.write_text("question_id,primary_selected\nQ150,False\nQ151,True\n")
    with pytest.raises(RuntimeError, match="changed after the freeze"):
        FR.require_freeze(f)


def test_human_read_allowed_after_freeze(tmp_path):
    sel, pool = _files(tmp_path)
    f = tmp_path / "FREEZE.json"
    FR.freeze(selection_path=sel, pool_path=pool, freeze_path=f, code_revision="x", run_ids={})
    assert FR.require_freeze(f)["selected_items"] == 1
    assert json.loads(f.read_text())["frozen_at"]


@pytest.mark.parametrize("which", ["selection", "pool"])
def test_human_read_refused_if_a_frozen_file_is_deleted(tmp_path, which):
    """The guard fails closed: a missing recorded selection or pool file blocks the read (verifier F4)."""
    sel, pool = _files(tmp_path)
    f = tmp_path / "FREEZE.json"
    FR.freeze(selection_path=sel, pool_path=pool, freeze_path=f, code_revision="x", run_ids={})
    (sel if which == "selection" else pool).unlink()
    with pytest.raises(RuntimeError, match="missing"):
        FR.require_freeze(f)
