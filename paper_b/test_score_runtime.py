"""Tests for cache safety + provenance sidecar (Cycle 2)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import score_runtime as R

FULL_SHA = "7550fd4cfe514470bb8d80918a43c9ae424d26b5"
CODE_REV = "38ed2ee" * 6 + "abcd"  # any 40-hex stand-in for the code revision
CODE_REV = "0123456789abcdef" * 2 + "0123"  # exactly 40 hex


def _spec(qid="Q57", codes=("1", "2", "3", "4")):
    return {"question_id": qid, "question_text": "text", "response_type": "single",
            "codes": list(codes), "labels": list(codes), "is_numeric_open": False,
            "is_ordered": True, "gps_dimension": "trust"}


def _scored_df(model="CHN_adapter", specs=None):
    specs = specs or [_spec()]
    rows = []
    for s in specs:
        n = len(s["codes"])
        probs = np.full(n, 1.0 / n)
        for idx, code in enumerate(s["codes"]):
            rows.append({"model": model, "question_id": s["question_id"],
                         "option_index": idx, "option_code": code,
                         "option_logprob": -1.0, "option_token_count": 1,
                         "model_prob": probs[idx]})
    return pd.DataFrame(rows)


def _fingerprint(specs, code_rev=CODE_REV, adapter_sha=FULL_SHA):
    return R.cache_fingerprint(specs=specs, readout={"temperature": 1.0},
                               code_revision=code_rev, adapter_sha256=adapter_sha)


def _adapter_sha(tmp_path):
    """Deterministic fake 'weights' hash for the fixture adapter dir."""
    blob = json.dumps({"adapter": "fixture"}).encode()
    return hashlib.sha256(blob).hexdigest()


class TestCacheFingerprint:
    def test_fingerprint_is_deterministic_sha256(self, tmp_path):
        specs = [_spec()]
        fp1 = _fingerprint(specs)
        fp2 = _fingerprint(specs)
        assert fp1 == fp2 and len(fp1) == 64

    def test_fingerprint_changes_with_each_input(self, tmp_path):
        specs = [_spec()]
        base = _fingerprint(specs)
        assert _fingerprint([_spec("Q43")]) != base                       # spec
        assert _fingerprint(specs, adapter_sha="a" * 64) != base          # adapter
        assert _fingerprint(specs, code_rev="b" * 40) != base             # code
        other = R.cache_fingerprint(specs=specs, readout={"temperature": 2.0},
                                    code_revision=CODE_REV, adapter_sha256=FULL_SHA)
        assert other != base                                              # readout


class TestCacheRoundTrip:
    def test_save_then_load_round_trips_string_codes(self, tmp_path):
        specs = [_spec()]
        df = _scored_df(specs=specs)
        fp = _fingerprint(specs)
        R.save_cached_scores(tmp_path, "CHN_adapter", df, fingerprint=fp)
        loaded, meta = R.load_cached_scores(tmp_path, "CHN_adapter", specs,
                                            fingerprint=fp)
        assert meta["valid"]
        # the regression the parent found: option_code must survive as string
        assert loaded["option_code"].tolist() == ["1", "2", "3", "4"]
        assert loaded["option_code"].map(type).eq(str).all()
        pd.testing.assert_frame_equal(loaded, df, check_dtype=False)

    def test_row_count_alone_is_not_acceptance(self, tmp_path):
        specs = [_spec()]
        df = _scored_df(specs=specs)
        fp = _fingerprint(specs)
        R.save_cached_scores(tmp_path, "m", df, fingerprint=fp)
        # same row count, WRONG fingerprint -> must reject
        _, meta = R.load_cached_scores(tmp_path, "m", specs,
                                       fingerprint=_fingerprint([_spec("Q43")]))
        assert not meta["valid"]
        assert "fingerprint" in meta["reason"]

    def test_partial_cache_rejected(self, tmp_path):
        specs = [_spec()]
        df = _scored_df(specs=specs).iloc[:-1]  # drop one option row
        fp = _fingerprint(specs)
        R.save_cached_scores(tmp_path, "m", df, fingerprint=fp)
        _, meta = R.load_cached_scores(tmp_path, "m", specs, fingerprint=fp)
        assert not meta["valid"] and "incomplete" in meta["reason"]

    def test_corrupt_cache_rejected_loudly(self, tmp_path):
        specs = [_spec()]
        fp = _fingerprint(specs)
        R.save_cached_scores(tmp_path, "m", _scored_df(specs=specs), fingerprint=fp)
        (tmp_path / "m_option_probabilities.csv").write_text("not,a,real\n1,2,3\n")
        _, meta = R.load_cached_scores(tmp_path, "m", specs, fingerprint=fp)
        assert not meta["valid"] and "corrupt" in meta["reason"]

    def test_missing_sidecar_rejected(self, tmp_path):
        specs = [_spec()]
        df = _scored_df(specs=specs)
        df.to_csv(tmp_path / "m_option_probabilities.csv", index=False)
        _, meta = R.load_cached_scores(tmp_path, "m", specs,
                                       fingerprint=_fingerprint(specs))
        assert not meta["valid"] and "sidecar" in meta["reason"]

    def test_missing_option_code_row_rejected(self, tmp_path):
        """Complete grid: every (question, option_code) from the spec must be
        present — a code missing (or a string/int mismatch) fails even if the
        row count coincidentally matches."""
        specs = [_spec()]
        df = _scored_df(specs=specs)
        df.loc[df.index[-1], "option_code"] = "999"  # wrong code, right count
        fp = _fingerprint(specs)
        R.save_cached_scores(tmp_path, "m", df, fingerprint=fp)
        _, meta = R.load_cached_scores(tmp_path, "m", specs, fingerprint=fp)
        assert not meta["valid"] and "incomplete" in meta["reason"]

    def test_nonfinite_probabilities_rejected(self, tmp_path):
        specs = [_spec()]
        df = _scored_df(specs=specs)
        df.loc[df.index[0], "model_prob"] = float("nan")
        fp = _fingerprint(specs)
        R.save_cached_scores(tmp_path, "m", df, fingerprint=fp)
        _, meta = R.load_cached_scores(tmp_path, "m", specs, fingerprint=fp)
        assert not meta["valid"] and "finite" in meta["reason"]

    def test_probability_sums_enforced_per_question(self, tmp_path):
        specs = [_spec()]
        df = _scored_df(specs=specs)
        df["model_prob"] = 0.3  # sums to 1.2, not 1.0
        fp = _fingerprint(specs)
        R.save_cached_scores(tmp_path, "m", df, fingerprint=fp)
        _, meta = R.load_cached_scores(tmp_path, "m", specs, fingerprint=fp)
        assert not meta["valid"] and "sum" in meta["reason"]

    # ------------------------------------------------ hostile cached frames
    def test_inf_probabilities_rejected(self, tmp_path):
        """The finite check must catch inf, not just NaN."""
        specs = [_spec()]
        df = _scored_df(specs=specs)
        df.loc[df.index[0], "model_prob"] = float("inf")
        fp = _fingerprint(specs)
        R.save_cached_scores(tmp_path, "m", df, fingerprint=fp)
        _, meta = R.load_cached_scores(tmp_path, "m", specs, fingerprint=fp)
        assert not meta["valid"] and "finite" in meta["reason"]

    def test_negative_probabilities_rejected(self, tmp_path):
        specs = [_spec()]
        df = _scored_df(specs=specs)
        df.loc[df.index[0], "model_prob"] = -0.25  # sums still 1.0
        fp = _fingerprint(specs)
        R.save_cached_scores(tmp_path, "m", df, fingerprint=fp)
        _, meta = R.load_cached_scores(tmp_path, "m", specs, fingerprint=fp)
        assert not meta["valid"] and "negative" in meta["reason"]

    def test_duplicate_option_keys_rejected(self, tmp_path):
        specs = [_spec()]
        df = pd.concat([_scored_df(specs=specs).iloc[:1],
                        _scored_df(specs=specs)], ignore_index=True)
        # renormalise so the sum check would pass: only the duplicate key must trip
        df.loc[df.index[-1], "model_prob"] = 0.0
        fp = _fingerprint(specs)
        R.save_cached_scores(tmp_path, "m", df, fingerprint=fp)
        _, meta = R.load_cached_scores(tmp_path, "m", specs, fingerprint=fp)
        assert not meta["valid"] and "duplicate" in meta["reason"]

    def test_index_code_alignment_rejected(self, tmp_path):
        """option_index i must carry spec codes[i] — a swapped pairing is fatal."""
        specs = [_spec()]
        df = _scored_df(specs=specs)
        df.loc[df.index[0], "option_index"] = 3  # code "1" labelled index 3
        fp = _fingerprint(specs)
        R.save_cached_scores(tmp_path, "m", df, fingerprint=fp)
        _, meta = R.load_cached_scores(tmp_path, "m", specs, fingerprint=fp)
        assert not meta["valid"] and "align" in meta["reason"]

    def test_wrong_model_rejected(self, tmp_path):
        specs = [_spec()]
        df = _scored_df(specs=specs, model="JPN_adapter")
        fp = _fingerprint(specs)
        R.save_cached_scores(tmp_path, "CHN_adapter", df, fingerprint=fp)
        _, meta = R.load_cached_scores(
            tmp_path, "CHN_adapter", specs, fingerprint=fp)
        assert not meta["valid"] and "model" in meta["reason"]

    def test_mixed_models_rejected(self, tmp_path):
        specs = [_spec()]
        df = _scored_df(specs=specs)
        df.loc[df.index[-1], "model"] = "JPN_adapter"
        fp = _fingerprint(specs)
        R.save_cached_scores(tmp_path, "m", df, fingerprint=fp)
        _, meta = R.load_cached_scores(tmp_path, "m", specs, fingerprint=fp)
        assert not meta["valid"] and "model" in meta["reason"]

    def test_sidecar_records_provenance(self, tmp_path):
        specs = [_spec()]
        fp = _fingerprint(specs)
        R.save_cached_scores(tmp_path, "m", _scored_df(specs=specs), fingerprint=fp,
                             code_revision=CODE_REV, adapter_sha256=FULL_SHA)
        sidecar = json.loads((tmp_path / "m_option_probabilities.sidecar.json").read_text())
        assert sidecar["fingerprint_sha256"] == fp
        assert sidecar["code_revision_sha256"] == CODE_REV
        assert sidecar["adapter_sha256"] == FULL_SHA
