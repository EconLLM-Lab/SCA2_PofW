"""CLI and real Hugging Face client contract. No GPU and no network."""
from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from huggingface_hub import CommitOperationAdd, HfApi

import score_runtime as R

REPO = Path(__file__).resolve().parents[1]
PY = REPO / ".venv" / "bin" / "python"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(PY), "paper_b/score_cohort.py", *args],
        cwd=REPO, text=True, capture_output=True, check=False,
    )


def test_default_cli_refuses_legacy_population_join():
    result = _run()
    assert result.returncode == 2
    assert "model-only" in result.stdout + result.stderr
    assert "MyDrive" not in result.stdout + result.stderr


def test_model_only_refuses_without_spec_and_does_not_score():
    result = _run("--model-only")
    assert result.returncode == 2
    assert "spec-file" in result.stdout + result.stderr


def test_dry_run_spec_does_not_require_a_gate_or_gpu(tmp_path):
    spec = {
        "battery": "strict", "sanitized": False, "n_questions": 1,
        "questions": [{
            "question_id": "Q57", "question_text": "local only",
            "response_type": "single_choice_2", "codes": ["1", "2"],
            "labels": ["a", "b"], "is_numeric_open": False,
            "is_ordered": True, "gps_dimension": "trust",
        }],
    }
    from build_scoring_spec import spec_sha256
    payload = {"spec_sha256": spec_sha256(spec), **spec}
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(payload))
    result = _run("--model-only", "--spec-file", str(path), "--run-id", "run-dry",
                  "--dry-run-spec")
    assert result.returncode == 0, result.stderr
    assert "spec ok" in result.stdout


def test_model_only_blocks_before_gpu_without_gate_marker(tmp_path):
    spec = {
        "battery": "strict", "sanitized": False, "n_questions": 1,
        "questions": [{
            "question_id": "Q57", "question_text": "local only",
            "response_type": "single_choice_2", "codes": ["1", "2"],
            "labels": ["a", "b"], "is_numeric_open": False,
            "is_ordered": True, "gps_dimension": "trust",
        }],
    }
    from build_scoring_spec import spec_sha256
    path = tmp_path / "spec.json"
    path.write_text(json.dumps({"spec_sha256": spec_sha256(spec), **spec}))
    result = _run("--model-only", "--spec-file", str(path), "--run-id", "run-blocked")
    assert result.returncode == 2
    assert "BLOCKED" in result.stdout + result.stderr


def test_artifact_store_uses_one_create_commit_and_real_signatures():
    upload = inspect.signature(HfApi.upload_file)
    assert upload.parameters["path_or_fileobj"].kind is inspect.Parameter.KEYWORD_ONLY
    assert "operations" in inspect.signature(HfApi.create_commit).parameters

    class FakeApi:
        def __init__(self):
            self.kwargs = None

        def create_commit(self, *, repo_id, operations, commit_message, repo_type):
            self.kwargs = {
                "repo_id": repo_id, "operations": list(operations),
                "commit_message": commit_message, "repo_type": repo_type,
            }
            return SimpleNamespace(oid="a" * 40)

    api = FakeApi()
    store = R.HuggingFaceArtifactStore(api=api)
    sha = store.commit_files(
        {"runs/r/synthetic/x.csv": b"csv", "runs/r/manifests/x.json": b"man"},
        repo_id=R.ARTIFACTS_REPO, repo_type="dataset", commit_message="one commit",
    )
    assert sha == "a" * 40
    assert len(api.kwargs["operations"]) == 2
    assert all(isinstance(op, CommitOperationAdd) for op in api.kwargs["operations"])
    assert store.read_commit_sha() == sha


def test_vm_wrapper_has_no_drive_path():
    text = (REPO / "paper_b" / "colab" / "vm_score.py").read_text()
    assert "MyDrive" not in text
    assert "--model-only" in text
    assert "HF_TOKEN" in text
