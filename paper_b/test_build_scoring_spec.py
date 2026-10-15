"""Tests for build_scoring_spec: model-only spec JSON, no human frames."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

import build_scoring_spec as B


QMAP_COLS = ["Question", "StandaloneQuestion", "ResponseType",
             "ResponseCodes", "ResponseLabels", "gps_dimension"]


def _qmap_row(qid, codes="1;2;3;4", labels="a;b;c;d", rtype="single"):
    return {"Question": qid, "StandaloneQuestion": f"text {qid}",
            "ResponseType": rtype, "ResponseCodes": codes,
            "ResponseLabels": labels, "gps_dimension": "trust"}


def _question_map():
    rows = [_qmap_row(q) for q in
            ["Q57", "Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73",  # trust 9
             "Q43", "Q50",                                                    # patience
             "Q106", "Q107", "Q109", "Q178",                                  # risktaking
             "Q81",                                                           # posrecip
             "Q176", "Q177", "Q179", "Q195",                                  # negrecip
             "Q99", "Q101", "Q103",                                           # altruism
             "Q69", "Q70", "Q71"]]                                            # secondary
    return pd.DataFrame(rows, columns=QMAP_COLS)


class TestStrictBattery:
    def test_primary_spec_is_23_strict_items(self):
        spec = B.build_scoring_spec(_question_map(), numeric_support={})
        ids = [s["question_id"] for s in spec["questions"]]
        strict = B.strict_item_ids()
        assert len(ids) == 23
        assert set(ids) == strict
        assert "Q69" not in ids and "Q262" not in ids

    def test_archive_spec_includes_gate_questions(self):
        qm = _question_map()
        qm.loc[len(qm)] = _qmap_row("Q262", codes="", labels="", rtype="numeric_open")
        spec = B.build_scoring_spec(qm, numeric_support={"Q262": ["15", "110"]},
                                    battery="archive")
        ids = {s["question_id"] for s in spec["questions"]}
        assert {"Q69", "Q70", "Q71", "Q262"} <= ids
        assert len(ids) == 27  # 23 strict + 3 secondary + Q262
        q262 = next(q for q in spec["questions"] if q["question_id"] == "Q262")
        assert q262["codes"] == ["15", "110"]

    def test_numeric_open_requires_supplied_grid(self):
        qm = _question_map()
        qm.loc[len(qm)] = _qmap_row("Q262", codes="", labels="", rtype="numeric_open")
        with pytest.raises(ValueError, match="numeric"):
            # archive battery includes numeric Q262; no grid supplied
            B.build_scoring_spec(qm, numeric_support={}, battery="archive")

    def test_no_question_text_in_spec_when_sanitized(self):
        spec = B.build_scoring_spec(_question_map(), numeric_support={},
                                    sanitized=True)
        assert all("question_text" not in q for q in spec["questions"])

    def test_question_text_present_locally(self):
        spec = B.build_scoring_spec(_question_map(), numeric_support={})
        assert all(q["question_text"] == f"text {q['question_id']}"
                   for q in spec["questions"])

    def test_spec_is_json_serializable_and_hashable(self, tmp_path):
        spec = B.build_scoring_spec(_question_map(), numeric_support={"Q262": ["15", "110"]})
        path = B.write_spec(spec, tmp_path / "spec.json")
        loaded = json.loads(Path(path).read_text())
        assert loaded["questions"][0]["codes"] == ["1", "2", "3", "4"]
        h = B.spec_sha256(spec)
        assert len(h) == 64 and h == B.spec_sha256(spec)

    def test_codes_are_strings_not_ints(self):
        spec = B.build_scoring_spec(_question_map(), numeric_support={})
        q57 = next(q for q in spec["questions"] if q["question_id"] == "Q57")
        assert all(isinstance(c, str) for c in q57["codes"])


class TestSpecIntegrity:
    def test_negative_gate_question_ids_enforced(self):
        spec = B.build_scoring_spec(_question_map(), numeric_support={})
        ids = {q["question_id"] for q in spec["questions"]}
        assert ids.isdisjoint({"Q69", "Q70", "Q71", "Q261", "Q262"})

    def test_strict_item_missing_from_map_raises(self):
        bad = _question_map()
        bad = bad[bad.Question != "Q81"]  # strict battery item absent
        with pytest.raises(ValueError, match="Q81"):
            B.build_scoring_spec(bad, numeric_support={}, battery="strict")
