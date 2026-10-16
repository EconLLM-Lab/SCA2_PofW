"""run_cohort.main() on bank 2 with a stateful fake Hub: resume, re-upload, loud failure, honest exit code."""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

RUN = "gps_sign_relabel_bank2_20261015_062543Z"      # must equal the pinned run id
NEEDED = ("adapter_model.safetensors", "adapter_config.json", "run_record.json")


class FakeHub:
    """Behaves like the Hub for what run_cohort touches: uploads become listable files."""

    def __init__(self, fail_uploads=False):
        self.files: set[str] = set()
        self.fail_uploads = fail_uploads
        self.folder_calls: list[str] = []

    def upload_folder(self, repo_id, repo_type, folder_path, path_in_repo, commit_message):
        if self.fail_uploads and not path_in_repo.startswith(f"bank2/{RUN}/state/"):
            raise OSError("network down")
        self.folder_calls.append(path_in_repo)
        for p in Path(folder_path).rglob("*"):
            if p.is_file():
                self.files.add(f"{path_in_repo}/{p.relative_to(folder_path).as_posix()}")

    def upload_file(self, path_or_fileobj, path_in_repo, repo_id, repo_type, commit_message):
        self.files.add(path_in_repo)

    def list_repo_files(self, repo_id, repo_type=None):
        return sorted(self.files)


def _world(tmp_path, monkeypatch, hub):  # callers request pb_config_guard
    import factorial as F
    for name, units in (("bank", None), ("profiles", F.all_units())):
        d = tmp_path / name
        d.mkdir()
        body = {"run_id": RUN, "labeling_rule": "deterministic_sign", "n_triplets": 658,
                "per_dimension_triplet_counts": {k: 109 for k in F.DIMS}}
        if units:
            body["units"] = units
        (d / "manifest.json").write_text(json.dumps(body))
    monkeypatch.setenv("SCA2_PB_PROTOCOL", "bank2")
    monkeypatch.setenv("SCA2_PB_UNITS", "profiles")
    monkeypatch.setenv("SCA2_PB_DATA_ROOT", str(tmp_path / "root"))
    monkeypatch.setenv("SCA2_PB_BANK2_DIR", str(tmp_path / "bank"))
    monkeypatch.setenv("SCA2_PB_PROFILE_DIR", str(tmp_path / "profiles"))
    monkeypatch.delenv("SCA2_PB_REPLICATE", raising=False)
    import config as C
    importlib.reload(C)
    import run_cohort as RC
    importlib.reload(RC)
    import hub_io
    import huggingface_hub
    import train_country as TC

    monkeypatch.setattr(huggingface_hub, "HfApi", lambda *a, **k: hub)
    monkeypatch.setattr(RC, "_list_hub_files", lambda: hub.list_repo_files("x"))
    trained = []

    def fake_train(cc):
        out = C.ADAPTER_DIR / cc
        out.mkdir(parents=True, exist_ok=True)
        for n in NEEDED:
            (out / n).write_text(json.dumps({"bank_run_id": RUN, "country": cc, "train_minutes": 15.0}))
        trained.append(cc)
        hub_io.upload_adapter(hub, C.HF_ADAPTER_REPO, out, C.hub_adapter_path(cc), "x",
                              sleep=lambda s: None)
        return out

    monkeypatch.setattr(TC, "train_country", fake_train)
    return C, RC, trained


def _put_on_hub(hub, C, unit):
    for n in NEEDED:
        hub.files.add(f"{C.hub_adapter_path(unit)}/{n}")


def test_resume_reupload_train_and_honest_exit(tmp_path, monkeypatch, pb_config_guard):
    hub = FakeHub()
    C, RC, trained = _world(tmp_path, monkeypatch, hub)
    done_unit, local_only, fresh = "P_0_0_0_0_0_0", "P_0_0_0_0_0_1", "P_0_0_0_0_1_0"
    _put_on_hub(hub, C, done_unit)
    out = C.ADAPTER_DIR / local_only                           # finished on disk, never reached the Hub
    out.mkdir(parents=True)
    for n in NEEDED:
        (out / n).write_text(json.dumps({"bank_run_id": RUN}))
    rc = RC.main(["--countries", done_unit, local_only, fresh, "--skip-prepare"])
    assert rc == 0
    assert trained == [fresh]                                  # only the unit with no adapter anywhere is trained
    assert f"{C.hub_adapter_path(local_only)}" in hub.folder_calls   # re-uploaded, not retrained
    assert all(f"{C.hub_adapter_path(u)}/adapter_model.safetensors" in hub.files for u in (done_unit, local_only, fresh))
    assert any(p.startswith(f"bank2/{RUN}/state/units") for p in hub.folder_calls)   # state synced


def test_failed_upload_is_loud_and_resume_reuploads_without_retraining(tmp_path, monkeypatch, capsys, pb_config_guard):
    hub = FakeHub(fail_uploads=True)
    C, RC, trained = _world(tmp_path, monkeypatch, hub)
    unit = "P_0_0_0_0_1_1"
    rc = RC.main(["--countries", unit, "--skip-prepare"])
    assert rc == 4                                             # not "done": the unit is not on the Hub
    out = capsys.readouterr().out
    assert "!!" in out and "NOT ON THE HUB" in out
    assert (C.ADAPTER_DIR / unit / "adapter_config.json").exists()        # the 15 GPU minutes are kept on disk
    manifest = json.loads(C.RUN_MANIFEST_FILE.read_text())
    assert manifest["countries"][unit]["status"] == "error"
    hub.fail_uploads = False                                   # the network comes back
    trained.clear()
    rc = RC.main(["--countries", unit, "--skip-prepare"])
    assert rc == 0 and trained == []                           # re-uploaded, not retrained
    assert f"{C.hub_adapter_path(unit)}/adapter_model.safetensors" in hub.files


def test_unpinned_bank_is_refused(tmp_path, monkeypatch, pb_config_guard):
    hub = FakeHub()
    C, RC, trained = _world(tmp_path, monkeypatch, hub)
    monkeypatch.setattr(C, "BANK_RUN_ID", "some_other_bank")
    assert RC.main(["--countries", "P_0_0_0_0_0_0", "--skip-prepare"]) == 2
    assert trained == []
