"""Tests for hashing + cache-fingerprint safety (parent blockers #2/#5).

The fingerprint must cover EVERYTHING that can change model output:
spec grid INCLUDING question_text and labels, readout, the real (possibly
dirty) code hashes, base-model and tokenizer revisions, and the adapter SHA.
Text never leaves the process: only its SHA-256 does.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

import score_runtime as R

FULL_SHA = "7550fd4cfe514470bb8d80918a43c9ae424d26b5"
CODE_REV = "0123456789abcdef" * 2 + "0123"


class TestHashing:
    def test_adapter_sha256_is_deterministic_and_content_sensitive(self, tmp_path):
        d = tmp_path / "CHN"
        d.mkdir()
        (d / "adapter_model.safetensors").write_bytes(b"weights-v1")
        (d / "adapter_config.json").write_text("{}")
        a = R.adapter_sha256(d)
        assert len(a) == 64
        assert a == R.adapter_sha256(d)
        (d / "adapter_model.safetensors").write_bytes(b"weights-v2")
        assert R.adapter_sha256(d) != a

    def test_adapter_sha256_ignores_run_record_only_changes(self, tmp_path):
        """run_record.json is provenance metadata, not weights: rewriting it
        must not change the weights hash (it changes nothing about the model)."""
        d = tmp_path / "CHN"
        d.mkdir()
        (d / "adapter_model.safetensors").write_bytes(b"w")
        (d / "adapter_config.json").write_text("{}")
        (d / "run_record.json").write_text('{"a": 1}')
        before = R.adapter_sha256(d)
        (d / "run_record.json").write_text('{"a": 2}')
        assert R.adapter_sha256(d) == before

    def test_code_revision_full_sha_from_git(self):
        rev = R.code_revision(Path(__file__).resolve().parent.parent)
        assert len(rev) == 40 and all(c in "0123456789abcdef" for c in rev)


def _spec(qid="Q57", codes=("1", "2", "3", "4"), text="original text",
          labels=None):
    return {"question_id": qid, "question_text": text,
            "response_type": "single", "codes": list(codes),
            "labels": list(labels or codes), "is_numeric_open": False,
            "is_ordered": True, "gps_dimension": "trust"}


def _readout(**over):
    r = {"temperature": 1.0, "completion_prefix": " ", "max_prompt_tokens": 768,
         "max_completion_tokens": 16, "length_normalize": False}
    r.update(over)
    return r


def _fp(specs, code_rev=CODE_REV, adapter_sha=FULL_SHA, code_hashes=None,
        base_revision="", tokenizer_revision="", readout=None):
    return R.cache_fingerprint(
        specs=specs, readout=readout or _readout(), code_revision=code_rev,
        adapter_sha256=adapter_sha, code_hashes=code_hashes,
        base_revision=base_revision, tokenizer_revision=tokenizer_revision)


class TestFingerprintCoverage:
    def test_deterministic_and_sha256(self):
        fp = _fp([_spec()])
        assert fp == _fp([_spec()]) and len(fp) == 64

    def test_changed_question_text_invalidates(self):
        """A silent prompt change (question_text) must never reuse the cache."""
        assert _fp([_spec(text="original")]) != _fp([_spec(text="EDITED")])

    def test_changed_labels_invalidate(self):
        assert _fp([_spec(labels=list("wxyz"))]) != _fp([_spec()])

    def test_changed_code_hashes_invalidate(self):
        """Dirty working-tree code must invalidate even with the same git HEAD."""
        base = _fp([_spec()], code_hashes={"eval_lib.py": "a" * 64})
        dirty = _fp([_spec()], code_hashes={"eval_lib.py": "b" * 64})
        assert base != dirty
        # and a hash map that GROWS (new file tracked) also invalidates
        grown = _fp([_spec()], code_hashes={"eval_lib.py": "a" * 64,
                                            "config.py": "c" * 64})
        assert grown not in (base, dirty)

    def test_base_and_tokenizer_revisions_invalidate(self):
        base = _fp([_spec()], base_revision="r1", tokenizer_revision="t1")
        assert _fp([_spec()], base_revision="r2", tokenizer_revision="t1") != base
        assert _fp([_spec()], base_revision="r1", tokenizer_revision="t2") != base

    def test_readout_changes_invalidate(self):
        assert _fp([_spec()], readout=_readout(temperature=2.0)) != _fp([_spec()])

    def test_fingerprint_is_text_free(self):
        """Only digests may be persisted; the raw question text must not be
        recoverable from anything the fingerprint writes out."""
        secret = "SECRET-QUESTION-WORDING-XYZ"
        fp = _fp([_spec(text=secret)])
        assert secret not in fp and len(fp) == 64


class TestDirtyCodeHashes:
    def test_hashes_actual_file_contents(self, tmp_path):
        (tmp_path / "score_cohort.py").write_text("print('v1')\n")
        h1 = R.dirty_code_hashes(tmp_path)
        (tmp_path / "score_cohort.py").write_text("print('v2')\n")
        h2 = R.dirty_code_hashes(tmp_path)
        assert h1["score_cohort.py"] != h2["score_cohort.py"]
        assert h2["score_cohort.py"] == hashlib.sha256(
            b"print('v2')\n").hexdigest()

    def test_missing_files_skipped_not_fatal(self, tmp_path):
        (tmp_path / "config.py").write_text("X = 1\n")
        h = R.dirty_code_hashes(tmp_path)
        assert set(h) == {"config.py"}


class TestRunRecordNTrain:
    """Parent blocker #2: n_train must equal the frozen 526 exactly."""

    def _rec(self, n_train):
        return {"country": "CHN",
                "model_name": "meta-llama/Llama-3.1-8B-Instruct",
                "beta": 0.1, "lr": 1e-4, "epochs": 1, "max_length": 768,
                "grad_accum": 16,
                "bank_run_id": "gps_sign_relabel_all_20260816_004545Z",
                "n_train": n_train, "lora": {"r": 16, "alpha": 32}}

    def test_n_train_not_526_is_invalid(self):
        for bad in (525, 527, 10, None):
            rec = self._rec(bad)
            rec.pop("n_train", None) if bad is None else None
            with pytest.raises(ValueError, match="n_train"):
                R.validate_run_record(rec, country="CHN")

    def test_n_train_526_accepted(self):
        assert R.validate_run_record(self._rec(526), country="CHN") is True

    def test_n_train_bool_rejected(self):
        with pytest.raises(ValueError, match="n_train"):
            R.validate_run_record(self._rec(True), country="CHN")


class TestGateKeyStrictness:
    """Parent blocker #4: gate keys include option_code; finite check catches
    inf; tolerances must be positive and finite."""

    def _frame(self, spec, model="m"):
        rows = []
        for q in spec["questions"]:
            for i, code in enumerate(q["codes"]):
                rows.append({"model": model, "question_id": q["question_id"],
                             "option_index": i, "option_code": str(code),
                             "option_logprob": -1.0 - i, "model_prob": 0.25})
        return pd.DataFrame(rows)

    def _spec(self):
        return {"battery": "strict", "n_questions": 1, "questions": [
            {"question_id": "Q57", "codes": ["1", "2", "3", "4"],
             "labels": ["1", "2", "3", "4"]}]}

    def test_inf_logprob_is_fatal_not_pass(self):
        got = self._frame(self._spec())
        got.loc[0, "option_logprob"] = float("inf")
        with pytest.raises(ValueError, match="finite"):
            R.compare_gate_scores(got, self._frame(self._spec()), self._spec(),
                                  tol_logprob=1e-6, tol_prob=1e-4)

    def test_wrong_option_code_pairing_is_fatal(self):
        spec = self._spec()
        got = self._frame(spec)
        got.loc[0, "option_code"] = "9"  # (Q57, 0) now pairs with code 9
        with pytest.raises(ValueError, match="one-to-one"):
            R.compare_gate_scores(got, self._frame(spec), spec,
                                  tol_logprob=1e-6, tol_prob=1e-4)

    def test_tolerances_must_be_positive_finite(self):
        spec = self._spec()
        for bad in (0.0, -1e-6, float("nan"), float("inf")):
            with pytest.raises(ValueError, match="tolerance"):
                R.compare_gate_scores(self._frame(spec), self._frame(spec),
                                      spec, tol_logprob=bad, tol_prob=1e-4)
            with pytest.raises(ValueError, match="tolerance"):
                R.compare_gate_scores(self._frame(spec), self._frame(spec),
                                      spec, tol_logprob=1e-6, tol_prob=bad)

    def test_duplicate_keys_rejected(self):
        spec = self._spec()
        dup = pd.concat([self._frame(spec).iloc[:1], self._frame(spec)],
                        ignore_index=True)
        with pytest.raises(ValueError, match="duplicate"):
            R.compare_gate_scores(dup, self._frame(spec), spec,
                                  tol_logprob=1e-6, tol_prob=1e-4)
