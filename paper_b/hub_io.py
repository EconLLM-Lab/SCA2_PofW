"""Hugging Face Hub as the only durable artifact bus for the Paper B runs.

Why this module exists: Google Drive needed an interactive OAuth click per VM, uploaded lazily
(7 of 17 finished adapters reached Drive before both VMs were reclaimed) and hid failures. Every
artifact now goes to the Hub over HTTPS, and every failure is loud.

Rules enforced here:
  * an adapter upload is retried and then raises HubUploadError; it is never swallowed;
  * nothing may ever be written under adapters/<CC> (cohort-1 weights);
  * a downloaded input is trusted only after its SHA-256 matches a pin kept in git;
  * run state (logs, wave manifest, ledger) is synced per wave, never the reference cache or weights.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import time
from pathlib import Path

BACKOFF_SECONDS = (10, 20)          # waits after attempt 1 and 2; attempt 3 raises


class HubUploadError(RuntimeError):
    pass


class PinMismatch(RuntimeError):
    pass


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_pins() -> dict:
    return json.loads((Path(__file__).resolve().parent / "bank2_pins.json").read_text())


def _guard(path_in_repo: str, allow_cohort1: bool = False) -> None:
    p = str(path_in_repo).strip("/")
    if not allow_cohort1 and (p == "adapters" or p.startswith("adapters/")):
        raise HubUploadError(f"refusing to write under adapters/ ({p}); cohort-1 weights are never overwritten")


def _retry(fn, what: str, sleep=time.sleep, tries: int = 3):
    last = None
    for k in range(1, tries + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - any transport error is retried
            last = exc
            print(f"  hub: {what} attempt {k}/{tries} failed: {type(exc).__name__}: {str(exc)[:160]}")
            if k < tries:
                sleep(BACKOFF_SECONDS[min(k - 1, len(BACKOFF_SECONDS) - 1)])
    raise HubUploadError(f"{what}: failed after {tries} attempts ({type(last).__name__}: {str(last)[:160]})") from last


def upload_adapter(api, repo: str, folder, path_in_repo: str, message: str, sleep=time.sleep,
                   allow_cohort1: bool = False) -> None:
    """allow_cohort1 is True only for the frozen 42-country protocol, never for bank 2."""
    _guard(path_in_repo, allow_cohort1)
    _retry(lambda: api.upload_folder(repo_id=repo, repo_type="dataset", folder_path=str(folder),
                                     path_in_repo=path_in_repo, commit_message=message),
           f"upload {path_in_repo}", sleep=sleep)


def verify_pin(path, expected_sha256: str) -> None:
    got = sha256_file(path)
    if got != expected_sha256:
        raise PinMismatch(f"{path}: sha256 {got[:12]}... != pinned {expected_sha256[:12]}...")


def pull_pinned(downloader, repo: str, hub_path: str, dest, expected_sha256: str) -> Path:
    """downloader(repo, hub_path, dest) writes the file; a mismatch removes it and raises."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    downloader(repo, hub_path, dest)
    try:
        verify_pin(dest, expected_sha256)
    except PinMismatch:
        dest.unlink(missing_ok=True)
        raise
    return dest


# files that describe a run; weights and the big reference cache are deliberately excluded
_STATE_GLOBS = ("logs/*", "run_manifest*.json", "compute_ledger.jsonl")


def sync_state(api, repo: str, data_root, run_id: str, tag: str, strict: bool = False,
               sleep=time.sleep) -> bool:
    """Upload logs, wave manifest and ledger to bank2/<run>/state/<tag>/ in ONE commit."""
    root = Path(data_root)
    dest = f"bank2/{run_id}/state/{tag}"
    _guard(dest)
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "s"
        n = 0
        for pattern in _STATE_GLOBS:
            for src in root.glob(pattern):
                if src.is_file():
                    out = stage / src.relative_to(root)
                    out.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, out)
                    n += 1
        if n == 0:
            return True
        try:
            _retry(lambda: api.upload_folder(repo_id=repo, repo_type="dataset", folder_path=str(stage),
                                             path_in_repo=dest, commit_message=f"state {tag}"),
                   f"state sync {tag}", sleep=sleep)
            return True
        except HubUploadError as exc:
            if strict:
                raise
            print(f"  hub: state sync FAILED for {tag} (will retry after the next unit): {exc}")
            return False


def write_probe(api, repo: str, run_id: str, name: str | None = None) -> str:
    """Write a tiny file and require it to appear in the listing; proves the destination takes writes."""
    name = name or time.strftime("%Y%m%dT%H%M%S")
    path = f"bank2/{run_id}/state/_probe/{name}.txt"
    _guard(path)
    _retry(lambda: api.upload_file(path_or_fileobj=f"probe {name}".encode(), path_in_repo=path,
                                   repo_id=repo, repo_type="dataset", commit_message="write probe"),
           "write probe")
    if path not in set(api.list_repo_files(repo_id=repo, repo_type="dataset")):
        raise HubUploadError(f"write probe not visible in the Hub listing: {path}")
    return path
