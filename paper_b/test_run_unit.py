"""Cycle 7 tests: the per-unit orchestration driver.

run_unit() must, per adapter:
  resolve adapter (revision-pinned, run-record enforced)
  -> run the independent adapter-path gate (production vs reference loader,
     same weights, with switchback) BEFORE cohort scoring
  -> score via the spec (model-only)
  -> cache with fingerprint sidecar
  -> persist verified (upload -> readback hash + commit SHA)
and HALT on any failure, preserving local state. A cohort run must refuse to
start unless the adapter-path gate has been exercised (GPU-launch block).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

import score_runtime as R

FULL_SHA = "7550fd4cfe514470bb8d80918a43c9ae424d26b5"
CODE_REV = "0123456789abcdef" * 2 + "0123"


def _spec(qids=("Q57", "Q58")):
    return {"battery": "strict", "sanitized": False, "n_questions": len(qids),
            "questions": [{"question_id": q, "response_type": "single",
                           "codes": ["1", "2", "3", "4"], "labels": ["1", "2", "3", "4"],
                           "is_numeric_open": False, "is_ordered": True,
                           "gps_dimension": "trust", "question_text": f"text {q}"}
                          for q in qids]}


def _spec_sha(spec):
    from build_scoring_spec import spec_sha256
    return spec_sha256(spec)


def _good_scores(model, spec, offset=0.0):
    rows = []
    for q in spec["questions"]:
        n = len(q["codes"])
        logps = [-1.0 * (i + 1) + offset for i in range(n)]
        m = max(logps)
        import math
        exps = [math.exp(x - m) for x in logps]
        s = sum(exps)
        for i, code in enumerate(q["codes"]):
            rows.append({"model": model, "question_id": q["question_id"],
                         "option_index": i, "option_code": str(code),
                         "option_logprob": float(logps[i]),
                         "option_token_count": 1,
                         "model_prob": exps[i] / s})
    return pd.DataFrame(rows)


class FakeHub:
    def __init__(self, fail=False):
        self.files, self.commits, self.fail = {}, [], fail

    def upload_file(self, path_or_fileobj, path_in_repo, repo_id, repo_type, commit_message=None):
        if self.fail:
            raise OSError("injected hub outage")
        self.files[path_in_repo] = (path_or_fileobj if isinstance(path_or_fileobj, bytes)
                                    else Path(path_or_fileobj).read_bytes())
        self.commits.append("c" * 40)
        return {"commit_sha": "c" * 40}

    def hf_hub_download(self, repo_id, filename, repo_type, revision=None):
        return self.files[filename]

    def read_commit_sha(self):
        return self.commits[-1]


def _mk_adapter(tmp_path, cc="CHN"):
    d = R.revision_cache_dir(tmp_path / "cache", FULL_SHA) / "adapters" / cc
    d.mkdir(parents=True, exist_ok=True)
    (d / "adapter_config.json").write_text("{}")
    (d / "adapter_model.safetensors").write_bytes(b"w-" + cc.encode())
    (d / "run_record.json").write_text(json.dumps({
        "country": cc, "model_name": "meta-llama/Llama-3.1-8B-Instruct",
        "beta": 0.1, "lr": 1e-4, "epochs": 1, "n_train": 526,
        "lora": {"r": 16, "alpha": 32}, "max_length": 768, "grad_accum": 16,
        "bank_run_id": "gps_sign_relabel_all_20260816_004545Z"}))
    return d


def _loaders(tmp_path, cc="CHN", broken=False):
    """Production scorer + independent reference loader over the SAME fixture
    'weights' (the adapter dir bytes). broken=True makes them disagree."""
    d = _mk_adapter(tmp_path, cc)
    weights = (d / "adapter_model.safetensors").read_bytes()

    def prod(spec, model_name, adapter_active=True):
        off = len(weights) % 7 if adapter_active else 0.0
        return _good_scores(model_name, spec, offset=off)

    def ref(spec, model_name):
        off = (len(weights) % 7) + (0.5 if broken else 0.0)
        return _good_scores(model_name, spec, offset=off)

    def switchback(spec, model_name):
        return prod(spec, model_name, adapter_active=False)  # base after disable

    return prod, ref, switchback


class TestRunUnit:
    def test_happy_path_gates_scores_caches_persists(self, tmp_path):
        spec = _spec()
        prod, ref, sb = _loaders(tmp_path)
        hub = FakeHub()
        result = R.run_unit(
            country="CHN", spec=spec, spec_sha=_spec_sha(spec), revision=FULL_SHA,
            cache_root=tmp_path / "cache", run_id="run-1", repo=R.ARTIFACTS_REPO,
            hub=hub, code_revision=CODE_REV, local_dir=tmp_path / "out",
            downloader=None,  # adapter already in cache
            production_scorer=prod, reference_scorer=ref, switchback_scorer=sb,
            tol_logprob=1e-9, tol_prob=1e-12)
        assert result["gate"]["gate_pass"] is True
        assert result["persisted"]["verified"] is True
        assert (tmp_path / "out" / "run-1" / "synthetic" /
                "CHN_adapter_option_probabilities.csv").exists()

    def test_gate_mismatch_halts_before_scoring(self, tmp_path):
        spec = _spec()
        prod, ref, sb = _loaders(tmp_path, broken=True)
        hub = FakeHub()
        with pytest.raises(RuntimeError, match="gate"):
            R.run_unit(country="CHN", spec=spec, spec_sha=_spec_sha(spec),
                       revision=FULL_SHA, cache_root=tmp_path / "cache",
                       run_id="run-1", repo=R.ARTIFACTS_REPO, hub=hub,
                       code_revision=CODE_REV, local_dir=tmp_path / "out",
                       downloader=None, production_scorer=prod,
                       reference_scorer=ref, switchback_scorer=sb,
                       tol_logprob=1e-9, tol_prob=1e-12)
        # nothing scored, nothing persisted
        assert not (tmp_path / "out" / "run-1").exists()
        assert hub.files == {}

    def test_upload_failure_preserves_cache_and_local_copy(self, tmp_path):
        spec = _spec()
        prod, ref, sb = _loaders(tmp_path)
        hub = FakeHub(fail=True)
        with pytest.raises(RuntimeError, match="upload"):
            R.run_unit(country="CHN", spec=spec, spec_sha=_spec_sha(spec),
                       revision=FULL_SHA, cache_root=tmp_path / "cache",
                       run_id="run-1", repo=R.ARTIFACTS_REPO, hub=hub,
                       code_revision=CODE_REV, local_dir=tmp_path / "out",
                       downloader=None, production_scorer=prod,
                       reference_scorer=ref, switchback_scorer=sb,
                       tol_logprob=1e-9, tol_prob=1e-12)
        # cached locally, resumable without re-scoring
        cached, meta = R.load_cached_scores(
            tmp_path / "cache", "CHN_adapter", spec["questions"],
            R.cache_fingerprint(spec["questions"], readout=R._readout(),
                                code_revision=CODE_REV,
                                adapter_sha256=R.adapter_sha256(
                                    _mk_adapter(tmp_path, "CHN"))))
        assert meta["valid"] and cached is not None, meta

    def test_resume_uses_valid_cache_without_rescoring(self, tmp_path):
        spec = _spec()
        prod, ref, sb = _loaders(tmp_path)
        calls = []
        counting_prod = lambda spec, m, adapter_active=True: (
            calls.append(1), prod(spec, m, adapter_active))[1]
        R.run_unit(country="CHN", spec=spec, spec_sha=_spec_sha(spec),
                   revision=FULL_SHA, cache_root=tmp_path / "cache",
                   run_id="run-1", repo=R.ARTIFACTS_REPO, hub=FakeHub(),
                   code_revision=CODE_REV, local_dir=tmp_path / "out",
                   downloader=None, production_scorer=counting_prod,
                   reference_scorer=ref, switchback_scorer=sb,
                   tol_logprob=1e-9, tol_prob=1e-12)
        n_first = len(calls)
        R.run_unit(country="CHN", spec=spec, spec_sha=_spec_sha(spec),
                   revision=FULL_SHA, cache_root=tmp_path / "cache",
                   run_id="run-1", repo=R.ARTIFACTS_REPO, hub=FakeHub(),
                   code_revision=CODE_REV, local_dir=tmp_path / "out",
                   downloader=None, production_scorer=counting_prod,
                   reference_scorer=ref, switchback_scorer=sb,
                   tol_logprob=1e-9, tol_prob=1e-12)
        # second run: gate still runs once (mandatory per launch), but scoring
        # is a pure cache hit — exactly one extra production call, not two.
        assert len(calls) == n_first + 1

    def test_none_switchback_scorer_is_refused_with_a_named_error(self, tmp_path):
        """run_unit calls switchback_scorer unguarded before the gate ran; a
        None must be refused by name, not crash as 'NoneType' object is not
        callable (score_runtime.py:710)."""
        spec = _spec()
        prod, ref, sb = _loaders(tmp_path)
        with pytest.raises(TypeError, match="run_unit: switchback_scorer"):
            R.run_unit(
                country="CHN", spec=spec, spec_sha=_spec_sha(spec), revision=FULL_SHA,
                cache_root=tmp_path / "cache", run_id="run-1",
                repo=R.ARTIFACTS_REPO, hub=FakeHub(), code_revision=CODE_REV,
                local_dir=tmp_path / "out", downloader=None,
                production_scorer=prod, reference_scorer=ref,
                switchback_scorer=None, tol_logprob=1e-9, tol_prob=1e-12)


class TestGPULaunchBlock:
    def test_cohort_refuses_to_start_without_gate_marker(self, tmp_path):
        with pytest.raises(RuntimeError, match="adapter-path gate"):
            R.run_cohort(countries=["CHN"], spec=_spec(), gate_marker_path=None,
                         cache_root=tmp_path, run_id="run-1",
                         repo=R.ARTIFACTS_REPO, hub=FakeHub(),
                         code_revision=CODE_REV, local_dir=tmp_path)

    def test_cohort_starts_when_gate_marker_present(self, tmp_path):
        marker = tmp_path / "gate_marker.json"
        marker.write_text(json.dumps({"gate_pass": True, "adapter_sha256": "x" * 64}))
        prod, ref, sb = _loaders(tmp_path)
        calls = []

        def no_adapter(cc, dest, rev):
            # hermetic: the adapter is not in this cache and the downloader
            # yields nothing, so a warm (or cold) machine-level HF cache can no
            # longer decide this test's outcome — and no network is touched.
            calls.append((cc, rev))
            raise FileNotFoundError(
                f"{cc}: no adapter at revision {rev} (test downloader)")

        with pytest.raises(FileNotFoundError, match="no adapter at revision"):
            R.run_cohort(countries=["CHN"], spec=_spec(), gate_marker_path=marker,
                         cache_root=tmp_path / "empty_cache", run_id="run-1",
                         repo=R.ARTIFACTS_REPO, hub=FakeHub(),
                         code_revision=CODE_REV, local_dir=tmp_path / "out",
                         downloader=no_adapter, production_scorer=prod,
                         reference_scorer=ref, switchback_scorer=sb)
        # it got PAST the launch block: adapter resolution was reached, the
        # refusal came from there, and nothing was scored or written.
        assert [c[0] for c in calls] == ["CHN"]
        assert not (tmp_path / "out").exists()


class TestCohortScorerWiring:
    """run_cohort must ask for its three scorers explicitly: the adapter-path
    gate's switchback comparison is a design requirement, so a missing scorer
    must be refused with a named TypeError up front — never reached as a
    `None(...)` call inside run_unit."""

    @staticmethod
    def _marker(tmp_path):
        marker = tmp_path / "gate_marker.json"
        marker.write_text(json.dumps({"gate_pass": True, "adapter_sha256": "x" * 64}))
        return marker

    def _cohort(self, tmp_path, hub=None, missing=None):
        prod, ref, sb = _loaders(tmp_path)  # fixture adapter sits in cache_root,
        # so a regression here fails on the scorer wiring, never on resolution.
        return R.run_cohort(
            countries=["CHN"], spec=_spec(),
            gate_marker_path=self._marker(tmp_path),
            cache_root=tmp_path / "cache", run_id="run-1",
            repo=R.ARTIFACTS_REPO, hub=FakeHub() if hub is None else hub,
            code_revision=CODE_REV, local_dir=tmp_path / "out",
            downloader=None,
            production_scorer=None if missing == "production_scorer" else prod,
            reference_scorer=None if missing == "reference_scorer" else ref,
            switchback_scorer=None if missing == "switchback_scorer" else sb)

    @pytest.mark.parametrize("missing", ["production_scorer", "reference_scorer",
                                         "switchback_scorer"])
    def test_cohort_refuses_a_none_scorer(self, tmp_path, missing):
        hub = FakeHub()
        with pytest.raises(TypeError, match=f"run_cohort: {missing}"):
            self._cohort(tmp_path, hub=hub, missing=missing)
        # refused before anything was scored, uploaded or written
        assert hub.files == {}
        assert not (tmp_path / "out").exists()

    def test_cohort_forwards_each_scorer_to_its_own_slot(self, tmp_path):
        """The positive half of the wiring: refusing a None (above) does not by
        itself prove run_cohort hands each scorer to the slot run_unit reads, so
        a dropped or swapped argument would pass every other test in this file."""
        prod, ref, sb = _loaders(tmp_path)
        calls = {"production_scorer": 0, "reference_scorer": 0, "switchback_scorer": 0}

        def counted(name, fn):
            def wrapped(*args, **kwargs):
                calls[name] += 1
                return fn(*args, **kwargs)
            return wrapped

        results = R.run_cohort(
            countries=["CHN"], spec=_spec(),
            gate_marker_path=self._marker(tmp_path),
            cache_root=tmp_path / "cache", run_id="run-1",
            repo=R.ARTIFACTS_REPO, hub=FakeHub(), code_revision=CODE_REV,
            local_dir=tmp_path / "out", downloader=None,
            production_scorer=counted("production_scorer", prod),
            reference_scorer=counted("reference_scorer", ref),
            switchback_scorer=counted("switchback_scorer", sb),
            tol_logprob=1e-9, tol_prob=1e-12)
        assert results[0]["gate"]["gate_pass"] is True
        assert results[0]["persisted"]["verified"] is True
        # the gate asks for the switchback before and after the adapter is
        # disabled and for the independent reference loader once; production is
        # called once in the gate and once more for the cold score cache. A
        # swapped or dropped argument cannot reproduce these counts.
        assert calls == {"production_scorer": 2, "reference_scorer": 1,
                         "switchback_scorer": 2}


def test_waves_cover_the_unit_list_in_order():
    import run_cohort as RC, config as C
    assert RC.WAVES[1] + RC.WAVES[2] == list(C.COHORT)
    assert abs(len(RC.WAVES[1]) - len(RC.WAVES[2])) <= 1
    assert RC.split_waves([f"P_{i}" for i in range(64)])[1] == [f"P_{i}" for i in range(32)]
