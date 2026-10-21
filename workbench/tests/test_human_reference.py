"""WB7-H: the descriptive human reference (script + bundle flag). Synthetic numbers only: no real survey share here."""
import csv
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from test_deploy_bundle_light import VERIFY, WORKBENCH, builder, light, read_archive  # noqa: F401  (light is a fixture)

SPEC = importlib.util.spec_from_file_location("human_ref", WORKBENCH / "scripts/build_human_reference.py")
href = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(href)
FIELDS = ["eval_country", "question_id", "response_type", "is_ordered", "option_index", "option_code", "option_value",
          "option_label", "population_prob", "n_valid"]


def synthetic_csv(path):
    # made-up cells: USA Q57 (n=500), CHN Q57 (n=40, too small), USA Q81 (4 ordered options)
    rows = []
    for cc, q, labels, probs, n in [("USA", "Q57", ["Yes", "No"], [0.3, 0.7], 500), ("CHN", "Q57", ["Yes", "No"], [0.6, 0.4], 40),
                                    ("USA", "Q81", ["a", "b", "c", "d"], [0.1, 0.2, 0.3, 0.4], 800), ("USA", "Q999", ["x", "y"], [0.5, 0.5], 900)]:
        for i, (lab, p) in enumerate(zip(labels, probs)):
            rows.append(dict(eval_country=cc, question_id=q, response_type="t", is_ordered="True", option_index=i,
                             option_code=str(i + 1), option_value=float(i + 1), option_label=lab, population_prob=p, n_valid=n))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def synthetic_index(path, items=("wvs_Q57", "wvs_Q81")):
    models = {"base": {"label": "Base"}, "usa": {"label": "Base + USA LoRA"}, "chn": {"label": "Base + CHN LoRA"}, "sp": {"label": "sign prompt 1_0_1_1_1_1"}}
    runs = [{"model": m, "item_id": it, "file": f"run__{m}__{it}.json"} for it in items for m in models]
    path.write_text(json.dumps({"models": models, "runs": runs, "pairs": []}))


def synthetic_heldout(root, pool_ids):
    root.mkdir()
    shutil.copy(href.HELDOUT / "freeze.py", root / "freeze.py")
    pool, sel = root / "pool.csv", root / "sel.csv"
    pool.write_text("Question\n" + "".join(f"{q}\n" for q in pool_ids))
    sel.write_text("question_id,primary_selected\nQ1,True\n")
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    (root / "FREEZE.json").write_text(json.dumps({"pool_path": str(pool), "pool_sha256": sha(pool),
                                                  "selection_path": str(sel), "selection_sha256": sha(sel)}))
    return root


def test_reference_cells_drops_and_privacy(tmp_path):
    synthetic_csv(tmp_path / "p.csv")
    synthetic_index(tmp_path / "index.json")
    ref = href.build(tmp_path / "p.csv", tmp_path / "index.json", items=["Q57", "Q81", "Q50"], heldout=synthetic_heldout(tmp_path / "h", ["Q7"]))
    assert ref["source"] == "World Values Survey wave 7, weighted; country-level shares"
    usa = ref["items"]["wvs_Q57"]["cells"]["USA"]
    assert usa == {"n": 500, "shares": {"1": 30, "2": 70}, "top": "2"}   # two answers: no mean
    assert ref["items"]["wvs_Q81"]["cells"]["USA"]["mean"] == 3.0
    assert "CHN" not in ref["items"]["wvs_Q57"]["cells"]                     # n=40 < 100
    assert ref["dropped_cells"] == [{"item": "wvs_Q57", "country": "CHN", "why": "n=40 < 100"},
                                    {"item": "wvs_Q81", "country": "CHN", "why": "no survey data"}]
    assert "Q50" in ref["dropped_items"]                                      # no adapter run for it
    assert set(ref["items"]["wvs_Q57"]["cells"]["USA"]) <= {"n", "shares", "top", "mean"}   # no respondent-level key


def test_heldout_item_is_dropped(tmp_path):
    synthetic_csv(tmp_path / "p.csv")
    synthetic_index(tmp_path / "index.json")
    ref = href.build(tmp_path / "p.csv", tmp_path / "index.json", items=["Q57", "Q81"], heldout=synthetic_heldout(tmp_path / "h", ["Q57"]))
    assert "wvs_Q57" not in ref["items"] and "Q57" in ref["dropped_items"] and "wvs_Q81" in ref["items"]


def test_missing_freeze_fails_closed(tmp_path):
    root = synthetic_heldout(tmp_path / "h", ["Q7"])
    (root / "FREEZE.json").unlink()
    with pytest.raises(RuntimeError, match="BLOCKED"):
        href.heldout_ids(root)


def test_no_shipped_item_is_in_the_real_heldout_pool():
    """Spec rule 5: the real Paper B pool and FREEZE. Every item this workbench ships or selects for the human layer is outside it."""
    if not (href.HELDOUT / "FREEZE.json").is_file():
        pytest.skip("Paper B held-out folder is not on this machine")
    pool = href.heldout_ids()
    index = json.loads((WORKBENCH / "exports/index.json").read_text())
    shipped = {r["item_id"].split("_", 1)[1] for r in index["runs"] if r["item_id"].startswith("wvs_")}
    assert shipped, "no wvs item found in exports/index.json"
    assert not (set(href.ITEMS) | shipped) & pool


def human_file(path, items=("wvs_Q57",)):
    ref = {"schema": "sca2-workbench/human-reference@1", "source": href.SOURCE, "dropped_cells": [], "dropped_items": {},
           "items": {it: {"codes": ["1", "2"], "labels": ["Yes", "No"], "ordered": True,
                          "cells": {"USA": {"n": 500, "shares": {"1": 40, "2": 60}, "top": "2", "mean": 1.6}}} for it in items}}
    path.write_text(json.dumps(ref))
    return path


def test_bundle_without_the_flag_has_no_human_file(light):
    w, args = light
    assert builder.build_bundle(args) == 0
    out = w / "dist/deploy_bundle.tar.gz"
    assert "exports/human_reference.json" not in read_archive(out)
    assert json.loads(out.with_suffix(".manifest.json").read_text())["human_reference"] is None


def test_bundle_with_the_flag_copies_the_file_and_verify_accepts_both(light, monkeypatch, tmp_path):
    w, args = light
    ref = human_file(tmp_path / "h.json")
    args.human_reference = ref
    assert builder.build_bundle(args) == 0
    out = w / "dist/deploy_bundle.tar.gz"
    files = read_archive(out)
    assert files["exports/human_reference.json"] == ref.read_bytes()
    manifest = json.loads(out.with_suffix(".manifest.json").read_text())
    assert manifest["human_reference"]["cells"] == 1
    assert any(e["file"] == "exports/human_reference.json" for e in manifest["files"]) and manifest["payload_bytes"] <= builder.MAX_BYTES
    monkeypatch.undo()
    report = w / "dist/verify-report.json"
    result = subprocess.run([sys.executable, str(VERIFY), str(out), str(w / "dist/extracted_h"), "--report", str(report)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(report.read_text())["human_reference_cells"] == 1


def test_verify_accepts_a_bundle_without_the_file(light, monkeypatch):
    w, args = light
    assert builder.build_bundle(args) == 0
    monkeypatch.undo()
    report = w / "dist/verify-report.json"
    result = subprocess.run([sys.executable, str(VERIFY), str(w / "dist/deploy_bundle.tar.gz"), str(w / "dist/extracted_n"), "--report", str(report)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(report.read_text())["human_reference_cells"] is None


@pytest.mark.parametrize("edit", [lambda c: c.update(n=99), lambda c: c.update(respondent_id=7), lambda c: c["shares"].pop("2")])
def test_builder_rejects_a_bad_human_file(light, tmp_path, edit):
    w, args = light
    path = human_file(tmp_path / "h.json")
    ref = json.loads(path.read_text())
    edit(ref["items"]["wvs_Q57"]["cells"]["USA"])
    path.write_text(json.dumps(ref))
    args.human_reference = path
    with pytest.raises(ValueError, match="bad cell"):
        builder.build_bundle(args)
