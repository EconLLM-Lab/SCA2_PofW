"""Cycle 5 tests: spec-driven model-only scorer + adapter-path gate.

The scorer must consume a spec file (question grids only), never touch survey
frames or population joins. The gate consumes the archive spec with NaN
rejection and a one-to-one keyed match against reference probabilities.
The adapter-path gate verifies that the PRODUCTION switch path and an
INDEPENDENT reference loader produce identical outputs from THE SAME weights,
plus adapter disable/switch-back checks. Tolerances are pinned constants, not
widened per comparison.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import build_scoring_spec as B
import score_runtime as R

TOL_LOGPROB = 1e-6
TOL_PROB = 1e-9


def _archive_spec():
    qm_rows = []
    for q in ["Q57", "Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73",
              "Q43", "Q50", "Q106", "Q107", "Q109", "Q178", "Q81",
              "Q176", "Q177", "Q179", "Q195", "Q99", "Q101", "Q103",
              "Q69", "Q70", "Q71"]:
        qm_rows.append({"Question": q, "StandaloneQuestion": f"text {q}",
                        "ResponseType": "single", "ResponseCodes": "1;2;3;4",
                        "ResponseLabels": "a;b;c;d", "gps_dimension": "trust"})
    qm_rows.append({"Question": "Q262", "StandaloneQuestion": "text Q262",
                    "ResponseType": "numeric_open", "ResponseCodes": "",
                    "ResponseLabels": "", "gps_dimension": "trust"})
    return B.build_scoring_spec(pd.DataFrame(qm_rows),
                                numeric_support={"Q262": ["15", "110"]},
                                battery="archive")


def _fake_scores(model, spec, offset=0.0):
    """Deterministic stand-in for score_model_questions output."""
    rows = []
    for s in spec["questions"]:
        n = len(s["codes"])
        logps = np.array([-1.0 * (i + 1) + offset for i in range(n)])
        probs = np.exp(logps - logps.max())
        probs /= probs.sum()
        for i, code in enumerate(s["codes"]):
            rows.append({"model": model, "question_id": s["question_id"],
                         "option_index": i, "option_code": str(code),
                         "option_logprob": float(logps[i]),
                         "model_prob": float(probs[i])})
    return pd.DataFrame(rows)


# ------------------------------------------------------- score from spec file
class TestSpecDrivenScoring:
    def test_score_from_spec_needs_no_survey_frames(self, tmp_path):
        spec = _archive_spec()
        spec_path = tmp_path / "spec.json"
        B.write_spec(spec, spec_path)
        # scorer gets ONLY the spec path; there is no survey/population input
        got = R.score_model_only(spec_path, model_name="base",
                                 scorer=lambda spec, model: _fake_scores(model, spec))
        assert got["model"].unique().tolist() == ["base"]
        assert set(got["question_id"]) == {q["question_id"] for q in spec["questions"]}

    def test_probability_sums_verified_after_scoring(self, tmp_path):
        spec = _archive_spec()
        spec_path = tmp_path / "spec.json"
        B.write_spec(spec, spec_path)
        bad = _fake_scores("base", spec)
        bad.loc[0, "model_prob"] = 0.5
        with pytest.raises(AssertionError, match="sum to one"):
            R.score_model_only(spec_path, model_name="base",
                               scorer=lambda spec, model: bad)

    def test_string_option_codes_survive(self, tmp_path):
        spec = _archive_spec()
        p = tmp_path / "spec.json"
        B.write_spec(spec, p)
        got = R.score_model_only(p, model_name="base",
                                 scorer=lambda spec, model: _fake_scores(model, spec))
        assert got["option_code"].map(type).eq(str).all()
        assert got["option_code"].tolist() == [str(c) for q in spec["questions"]
                                               for c in q["codes"]]


# ------------------------------------------------------------ gate comparison
class TestGateMatching:
    def test_exact_match_passes(self):
        spec = _archive_spec()
        ref = _fake_scores("ref", spec)
        got = _fake_scores("got", spec)
        ok, report = R.compare_gate_scores(got, ref, spec,
                                           tol_logprob=TOL_LOGPROB, tol_prob=TOL_PROB)
        assert ok and report["n_compared"] == sum(len(q["codes"]) for q in spec["questions"])

    def test_mismatch_fails_with_max_diff(self):
        spec = _archive_spec()
        ref = _fake_scores("ref", spec)
        got = _fake_scores("got", spec, offset=0.05)
        ok, report = R.compare_gate_scores(got, ref, spec,
                                           tol_logprob=TOL_LOGPROB, tol_prob=TOL_PROB)
        assert not ok and report["max_dlogprob"] > TOL_LOGPROB

    def test_nan_in_reference_rejected(self):
        spec = _archive_spec()
        ref = _fake_scores("ref", spec)
        ref.loc[0, "option_logprob"] = float("nan")
        got = _fake_scores("got", spec)
        with pytest.raises(ValueError, match="NaN"):
            R.compare_gate_scores(got, ref, spec,
                                  tol_logprob=TOL_LOGPROB, tol_prob=TOL_PROB)

    def test_missing_key_is_fatal_not_dropped(self):
        spec = _archive_spec()
        ref = _fake_scores("ref", spec)
        got = _fake_scores("got", spec).iloc[1:]  # drop one row
        with pytest.raises(ValueError, match="one-to-one"):
            R.compare_gate_scores(got, ref, spec,
                                  tol_logprob=TOL_LOGPROB, tol_prob=TOL_PROB)

    def test_duplicate_keys_rejected(self):
        spec = _archive_spec()
        ref = _fake_scores("ref", spec)
        got = pd.concat([_fake_scores("got", spec).iloc[:1],
                         _fake_scores("got", spec)], ignore_index=True)
        with pytest.raises(ValueError, match="duplicate"):
            R.compare_gate_scores(got, ref, spec,
                                  tol_logprob=TOL_LOGPROB, tol_prob=TOL_PROB)


# ------------------------------------------------------------ adapter gate
class TestAdapterPathGate:
    """Independent reference loader vs production switch path, SAME weights."""

    def _paths(self, spec):
        return {q["question_id"]: [str(c) for c in q["codes"]] for q in spec["questions"]}

    def test_same_weights_both_paths_identical(self):
        spec = _archive_spec()
        prod = _fake_scores("prod", spec)
        ref = _fake_scores("ref", spec)  # same weights -> identical outputs
        sb = _fake_scores("prod", spec)  # unchanged after switch-back
        ok, report = R.run_adapter_path_gate(prod_scores=prod, ref_scores=ref,
                                             switchback_scores=sb, spec=spec,
                                             tol_logprob=TOL_LOGPROB, tol_prob=TOL_PROB)
        assert ok and report["gate_pass"]

    def test_production_vs_independent_diff_fails(self):
        spec = _archive_spec()
        prod = _fake_scores("prod", spec)
        ref = _fake_scores("ref", spec, offset=0.01)
        sb = _fake_scores("prod", spec)
        ok, report = R.run_adapter_path_gate(prod_scores=prod, ref_scores=ref,
                                             switchback_scores=sb, spec=spec,
                                             tol_logprob=TOL_LOGPROB, tol_prob=TOL_PROB)
        assert not ok and not report["gate_pass"]

    def test_switchback_must_match_production(self):
        spec = _archive_spec()
        prod = _fake_scores("prod", spec)
        ref = _fake_scores("ref", spec)
        sb = _fake_scores("prod", spec, offset=0.5)  # drifted after switching back
        ok, report = R.run_adapter_path_gate(prod_scores=prod, ref_scores=ref,
                                             switchback_scores=sb, spec=spec,
                                             tol_logprob=TOL_LOGPROB, tol_prob=TOL_PROB)
        assert not ok
        assert "switchback" in json.dumps(report)

    def test_gate_requires_switchback_scores(self):
        spec = _archive_spec()
        prod = _fake_scores("prod", spec)
        ref = _fake_scores("ref", spec)
        with pytest.raises(ValueError, match="switchback"):
            R.run_adapter_path_gate(prod_scores=prod, ref_scores=ref,
                                    switchback_scores=None, spec=spec,
                                    tol_logprob=TOL_LOGPROB, tol_prob=TOL_PROB,
                                    require_switchback=True)


# ------------------------------------------------- the held-out battery is a loadable spec
class TestHeldoutSpecLoads:
    def _heldout_spec(self, variant="v1"):
        qm = pd.DataFrame([{"Question": q, "StandaloneQuestion": f"text {q} about something real",
                            "ResponseType": "scale_1_4", "ResponseCodes": "1; 2; 3; 4",
                            "ResponseLabels": "", "gps_dimension": ""} for q in ("Q150", "Q151")])
        return B.build_scoring_spec(qm, numeric_support={}, battery="heldout",
                                    heldout_items=["Q150", "Q151"], prompt_variant=variant)

    def test_load_spec_accepts_heldout_and_keeps_its_hash(self, tmp_path):
        spec = self._heldout_spec()
        path = tmp_path / "h.json"
        B.write_spec(spec, path)
        got = R.load_spec(path)
        assert got["battery"] == "heldout" and got["n_questions"] == 2

    def test_load_spec_still_rejects_unknown_batteries_and_tampering(self, tmp_path):
        spec = self._heldout_spec()
        path = tmp_path / "h.json"
        B.write_spec(spec, path)
        body = json.loads(path.read_text())
        body["battery"] = "mystery"
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps(body))
        with pytest.raises(ValueError):
            R.load_spec(bad)
        tampered = json.loads(path.read_text())
        tampered["questions"][0]["question_text"] += " edited"
        edited = tmp_path / "edited.json"
        edited.write_text(json.dumps(tampered))
        with pytest.raises(ValueError, match="hash mismatch"):
            R.load_spec(edited)
