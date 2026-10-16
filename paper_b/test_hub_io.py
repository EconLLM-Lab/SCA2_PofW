"""Hub as the single artifact bus: retried uploads that fail loudly, pinned downloads, state sync."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hub_io as H  # noqa: E402

RUN = "gps_sign_relabel_bank2_TEST"


class FakeApi:
    def __init__(self, fail_first=0, listed=None):
        self.fail_first = fail_first
        self.calls = []
        self.listed = listed if listed is not None else []

    def upload_folder(self, **kw):
        # snapshot what is staged at call time; the temp folder is deleted when sync_state returns
        kw = dict(kw, staged=sorted(p.relative_to(kw["folder_path"]).as_posix()
                                    for p in Path(kw["folder_path"]).rglob("*") if p.is_file()))
        self.calls.append(("folder", kw))
        if len(self.calls) <= self.fail_first:
            raise OSError("connection reset")

    def upload_file(self, **kw):
        self.calls.append(("file", kw))
        if len(self.calls) <= self.fail_first:
            raise OSError("connection reset")

    def list_repo_files(self, repo_id, repo_type=None):
        return list(self.listed)


def test_retry_then_success(tmp_path):
    api, sleeps = FakeApi(fail_first=2), []
    H.upload_adapter(api, "repo", tmp_path, "bank2/R/profiles/P_0", "msg", sleep=sleeps.append)
    assert len(api.calls) == 3 and sleeps == [10, 20]


def test_upload_failure_is_loud_and_names_the_unit(tmp_path):
    api = FakeApi(fail_first=99)
    with pytest.raises(H.HubUploadError, match="P_0.*3 attempts"):
        H.upload_adapter(api, "repo", tmp_path, "bank2/R/profiles/P_0", "msg", sleep=lambda s: None)
    assert len(api.calls) == 3


def test_adapters_prefix_is_never_a_target(tmp_path):
    with pytest.raises(H.HubUploadError, match="adapters/"):
        H.upload_adapter(FakeApi(), "repo", tmp_path, "adapters/ARG", "msg", sleep=lambda s: None)


def test_verify_pin(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"abc")
    good = hashlib.sha256(b"abc").hexdigest()
    H.verify_pin(f, good)
    with pytest.raises(H.PinMismatch):
        H.verify_pin(f, "0" * 64)


def test_pull_pinned_removes_a_bad_download(tmp_path):
    def dl(repo, name, dest):
        Path(dest).write_bytes(b"corrupt")

    dest = tmp_path / "cache.jsonl"
    with pytest.raises(H.PinMismatch):
        H.pull_pinned(dl, "repo", "x/cache.jsonl", dest, hashlib.sha256(b"real").hexdigest())
    assert not dest.exists()                      # never leave an unverified file for training to read

    def dl_ok(repo, name, dest):
        Path(dest).write_bytes(b"real")

    H.pull_pinned(dl_ok, "repo", "x/cache.jsonl", dest, hashlib.sha256(b"real").hexdigest())
    assert dest.read_bytes() == b"real"


def test_sync_state_uploads_logs_manifest_ledger_under_the_wave_tag(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "fact_wave1.log").write_text("log")
    (tmp_path / "run_manifest_wave1.json").write_text("{}")
    (tmp_path / "compute_ledger.jsonl").write_text("{}\n")
    (tmp_path / "shared_reference_logps.jsonl").write_text("big")       # must not be re-uploaded
    (tmp_path / "adapters").mkdir()
    (tmp_path / "adapters" / "w.bin").write_bytes(b"w")                  # adapters never go in state
    api = FakeApi()
    H.sync_state(api, "art", tmp_path, RUN, "wave1", sleep=lambda s: None)
    kind, kw = api.calls[0]
    assert kw["path_in_repo"] == f"bank2/{RUN}/state/wave1"
    assert kw["staged"] == ["compute_ledger.jsonl", "logs/fact_wave1.log", "run_manifest_wave1.json"]


def test_sync_state_strict_raises_but_nonstrict_warns(tmp_path, capsys):
    (tmp_path / "compute_ledger.jsonl").write_text("{}\n")
    api = FakeApi(fail_first=99)
    assert H.sync_state(api, "art", tmp_path, RUN, "wave1", strict=False, sleep=lambda s: None) is False
    assert "state sync FAILED" in capsys.readouterr().out
    with pytest.raises(H.HubUploadError):
        H.sync_state(api, "art", tmp_path, RUN, "wave1", strict=True, sleep=lambda s: None)


def test_write_probe_requires_the_file_to_be_listed(tmp_path):
    ok = FakeApi(listed=[f"bank2/{RUN}/state/_probe/p1.txt"])
    assert H.write_probe(ok, "art", RUN, "p1") == f"bank2/{RUN}/state/_probe/p1.txt"
    with pytest.raises(H.HubUploadError, match="probe"):
        H.write_probe(FakeApi(listed=[]), "art", RUN, "p1")


def test_pins_file_is_complete_and_hex():
    pins = json.loads((Path(__file__).resolve().parent / "bank2_pins.json").read_text())
    for k in ("relabel_run_id", "artifacts_repo", "adapters_repo", "bundle", "refcache", "refcache_manifest"):
        assert k in pins, k
    for k in ("bundle", "refcache", "refcache_manifest"):
        assert len(pins[k]["sha256"]) == 64 and int(pins[k]["sha256"], 16) >= 0
        assert pins[k]["hub_path"].startswith(f"bank2/{pins['relabel_run_id']}") or pins[k]["hub_path"].startswith("banks/")
