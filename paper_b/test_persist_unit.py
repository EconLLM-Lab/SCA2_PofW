"""Cycle 6 tests: verified per-unit persistence to the private artifacts repo.

FAKE NETWORK FIXTURE notice: `InMemoryHub` below is a deterministic in-memory
stand-in for the huggingface_hub API surface. These tests never contact
huggingface.co and never fabricate real API results; they pin OUR contract:
upload -> readback-hash + commit-SHA verification -> halt on failure with the
local copy preserved.
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


class InMemoryHub:
    """FAKE NETWORK FIXTURE (labeled). Mimics upload_file / list_repo_files /
    hf_hub_download / commit reads for one dataset repo."""

    def __init__(self):
        self.files: dict[str, bytes] = {}
        self.commits: list[str] = []
        self.fail_on: set[str] = set()

    def upload_file(self, path_or_fileobj, path_in_repo, repo_id, repo_type,
                    commit_message=None):
        if repo_id != R.ARTIFACTS_REPO or repo_type != R.ARTIFACTS_REPO_TYPE:
            raise AssertionError(f"wrong destination {repo_id}/{repo_type}")
        if path_in_repo in self.fail_on:
            raise OSError(f"injected failure for {path_in_repo}")
        data = path_or_fileobj if isinstance(path_or_fileobj, bytes) else Path(path_or_fileobj).read_bytes()
        self.files[path_in_repo] = data
        sha = hashlib.sha256(json.dumps(sorted(self.files)).encode()).hexdigest()
        self.commits.append(sha)
        return {"commit_sha": self.commits[-1]}

    # readback surface
    def list_repo_files(self, repo_id, repo_type):
        return sorted(self.files)

    def hf_hub_download(self, repo_id, filename, repo_type, revision=None):
        return self.files[filename]

    def read_commit_sha(self):
        return self.commits[-1] if self.commits else None


def _scores():
    return pd.DataFrame({
        "run_id": "run-20261011", "model": "CHN_adapter",
        "adapter_revision": FULL_SHA,
        "question_id": ["Q57", "Q57"], "option_index": [0, 1],
        "option_code": ["1", "2"], "option_logprob": [-1.0, -2.0],
        "option_token_count": [1, 1], "model_prob": [0.6, 0.4],
        "question_text": ["text Q57", "text Q57"],  # must NOT be persisted
        "prompt_text": ["PROMPT", "PROMPT"],        # must NOT be persisted
    })


def test_persist_requires_run_id_and_repo(tmp_path):
    with pytest.raises(ValueError, match="run_id"):
        R.persist_unit_scores(scores=_scores(), model_name="CHN_adapter",
                              run_id="", repo=R.ARTIFACTS_REPO, hub=InMemoryHub(),
                              adapter_sha256="a" * 64, code_revision=CODE_REV,
                              local_dir=tmp_path)
    with pytest.raises(ValueError, match="repo"):
        R.persist_unit_scores(scores=_scores(), model_name="CHN_adapter",
                              run_id="r", repo="", hub=InMemoryHub(),
                              adapter_sha256="a" * 64, code_revision=CODE_REV,
                              local_dir=tmp_path)
    with pytest.raises(ValueError, match="destination repo must be"):
        R.persist_unit_scores(scores=_scores(), model_name="CHN_adapter",
                              run_id="r", repo="Someone/else", hub=InMemoryHub(),
                              adapter_sha256="a" * 64, code_revision=CODE_REV,
                              local_dir=tmp_path)


def test_persisted_csv_is_sanitized_and_allowlisted(tmp_path):
    hub = InMemoryHub()
    result = R.persist_unit_scores(scores=_scores(), model_name="CHN_adapter",
                                   run_id="run-20261011", repo=R.ARTIFACTS_REPO,
                                   hub=hub, adapter_sha256="a" * 64,
                                   code_revision=CODE_REV,
                                   local_dir=tmp_path)
    # local durable copy (with question_text retained for the later rights-cleared join)
    assert Path(result["local_copy"]).exists()
    local_df = pd.read_csv(result["local_copy"], dtype={"option_code": str})
    assert "question_text" in local_df.columns
    # remote copy: allowlisted columns only, question_text dropped
    remote_name = f"runs/run-20261011/synthetic/CHN_adapter_option_probabilities.csv"
    remote_df = pd.read_csv(__import__("io").BytesIO(hub.files[remote_name]),
                            dtype={"option_code": str})
    assert set(remote_df.columns) == set(R.PERSISTED_COLUMNS)
    assert "question_text" not in remote_df.columns
    assert "prompt_text" not in remote_df.columns
    assert remote_df["option_code"].tolist() == ["1", "2"]


def test_sidecar_manifest_uploaded_with_provenance(tmp_path):
    hub = InMemoryHub()
    R.persist_unit_scores(scores=_scores(), model_name="CHN_adapter",
                          run_id="run-20261011", repo=R.ARTIFACTS_REPO,
                          hub=hub, adapter_sha256="a" * 64,
                          code_revision=CODE_REV, local_dir=tmp_path)
    man_name = "runs/run-20261011/manifests/CHN_adapter_manifest.json"
    man = json.loads(hub.files[man_name])
    assert man["adapter_sha256"] == "a" * 64
    assert man["code_revision_sha256"] == CODE_REV
    assert man["csv_sha256"] == hashlib.sha256(
        hub.files["runs/run-20261011/synthetic/CHN_adapter_option_probabilities.csv"]).hexdigest()
    # no human-data provenance in the manifest
    blob = json.dumps(man)
    assert "question_text" not in blob


def test_readback_hash_and_commit_sha_verified(tmp_path):
    hub = InMemoryHub()
    result = R.persist_unit_scores(scores=_scores(), model_name="CHN_adapter",
                                   run_id="run-20261011", repo=R.ARTIFACTS_REPO,
                                   hub=hub, adapter_sha256="a" * 64,
                                   code_revision=CODE_REV, local_dir=tmp_path)
    assert result["verified"] is True
    assert result["commit_sha"] == hub.read_commit_sha()
    assert len(result["csv_sha256"]) == 64


def test_readback_mismatch_fails_loudly(tmp_path):
    class CorruptReadbackHub(InMemoryHub):
        def hf_hub_download(self, repo_id, filename, repo_type, revision=None):
            data = dict(self.files)[filename]
            return data[:-4] + b"XXXX"  # tampered readback

    hub = CorruptReadbackHub()
    with pytest.raises(RuntimeError, match="readback"):
        R.persist_unit_scores(scores=_scores(), model_name="CHN_adapter",
                              run_id="run-20261011", repo=R.ARTIFACTS_REPO,
                              hub=hub, adapter_sha256="a" * 64,
                              code_revision=CODE_REV, local_dir=tmp_path)


def test_upload_failure_preserves_local_copy_and_raises(tmp_path):
    hub = InMemoryHub()
    hub.fail_on.add("runs/run-20261011/synthetic/CHN_adapter_option_probabilities.csv")
    with pytest.raises(RuntimeError, match="upload"):
        R.persist_unit_scores(scores=_scores(), model_name="CHN_adapter",
                              run_id="run-20261011", repo=R.ARTIFACTS_REPO,
                              hub=hub, adapter_sha256="a" * 64,
                              code_revision=CODE_REV, local_dir=tmp_path)
    # the durable LOCAL copy survived, ready for a later upload attempt
    assert (tmp_path / "run-20261011" / "synthetic" /
            "CHN_adapter_option_probabilities.csv").exists()


def test_no_human_columns_can_be_persisted(tmp_path):
    """Any column outside the allowlist is a hard error, not silently dropped."""
    scores = _scores()
    scores["population_prob"] = [0.1, 0.9]  # human-derived column sneaks in
    hub = InMemoryHub()
    with pytest.raises(ValueError, match="allowlist|population_prob"):
        R.persist_unit_scores(scores=scores, model_name="CHN_adapter",
                              run_id="run-20261011", repo=R.ARTIFACTS_REPO,
                              hub=hub, adapter_sha256="a" * 64,
                              code_revision=CODE_REV, local_dir=tmp_path)
