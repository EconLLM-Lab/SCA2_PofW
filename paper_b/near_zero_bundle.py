#!/usr/bin/env python3
"""Paper B, C6 — pack the four reduced banks into one archive, upload it to the artifacts repo, pin its SHA-256.

Only the four unit directories (bank file + manifest) go in. No logs, no subset declaration, no human data: a
bank row carries the profile unit's synthetic labels and its own +-1 z, never a country's real z.

    env -u PYTHONPATH .venv/bin/python paper_b/near_zero_bundle.py build  --nz-dir <dir> --out <file.tgz>
    env -u PYTHONPATH .venv/bin/python paper_b/near_zero_bundle.py upload --nz-dir <dir> [--out <file.tgz>]

`upload` builds the archive and writes it to banks/near_zero_<bank run id>/near_zero_banks.tgz in
Bonorinoa/SCA2-paper-b-artifacts (the same banks/ folder as the bank-2 bundle; never adapters/). It reads the token
from the sca profile .env in code, refuses to overwrite an existing path, reads the file back from the Hub and
compares SHA-256, then appends the pin to score_plan_pins.json (append-only).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import protocol_bank2 as P2  # noqa: E402

ARTIFACTS_REPO = "Bonorinoa/SCA2-paper-b-artifacts"
ENV_FILE = Path("/Users/bonorinoa/.hermes/profiles/sca/.env")


def bundle_members(nz_dir: Path) -> list[tuple[str, Path]]:
    """(archive name, file) for each unit's manifest and bank file, in a fixed order."""
    out = []
    for unit in P2.NEARZERO_UNITS:
        mpath = Path(nz_dir) / unit / "manifest.json"
        if not mpath.is_file():
            raise RuntimeError(f"unit {unit}: manifest missing at {mpath}")
        m = json.loads(mpath.read_text())
        out.append((f"{unit}/manifest.json", mpath))
        out.append((f"{unit}/{m['file']}", Path(nz_dir) / unit / m["file"]))
    return out


def build_bundle(nz_dir: Path, out: Path) -> str:
    """Write the archive (fixed order, zeroed mtime and owner, so the bytes depend on the files only); return its SHA-256."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", compresslevel=6) as tf:
        for name, path in bundle_members(nz_dir):
            data = path.read_bytes()
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tf.addfile(info, io.BytesIO(data))
    raw = buf.getvalue()
    raw = raw[:4] + b"\x00\x00\x00\x00" + raw[8:]       # the gzip header carries a timestamp: zero it
    Path(out).write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def hub_path_for(bank_run_id: str) -> str:
    return f"banks/near_zero_{bank_run_id}/near_zero_banks.tgz"


def _token() -> str:
    return next(l.split("=", 1)[1].strip().strip("'\"") for l in ENV_FILE.read_text().splitlines()
                if l.startswith("HF_TOKEN="))


def upload(nz_dir: Path, out: Path) -> dict:
    import score_plan as SPL
    from huggingface_hub import HfApi, hf_hub_download
    run_id = json.loads((Path(nz_dir) / "GBR" / "manifest.json").read_text())["bank_run_id"]
    pinned = json.loads((Path(__file__).resolve().parent / "bank2_pins.json").read_text())["relabel_run_id"]
    if run_id != pinned:
        raise RuntimeError(f"near-zero banks were built from {run_id}, not the pinned bank-2 run {pinned}")
    sha = build_bundle(nz_dir, out)
    path = hub_path_for(run_id)
    if path.startswith("adapters/"):
        raise RuntimeError("refusing to write under adapters/")
    tok = _token()
    api = HfApi(token=tok)
    if path in set(api.list_repo_files(ARTIFACTS_REPO, repo_type="dataset")):
        raise RuntimeError(f"{path} already exists on the Hub; refusing to overwrite")
    api.upload_file(path_or_fileobj=str(out), path_in_repo=path, repo_id=ARTIFACTS_REPO, repo_type="dataset",
                    commit_message="near-zero reduced banks (card T5, C6)")
    back = hf_hub_download(ARTIFACTS_REPO, path, repo_type="dataset", token=tok, force_download=True)
    got = hashlib.sha256(Path(back).read_bytes()).hexdigest()
    if got != sha:
        raise RuntimeError(f"read-back SHA-256 {got} differs from the local archive {sha}")
    SPL.pin_nearzero_bundle(path, sha)
    return {"hub_path": path, "sha256": sha, "bytes": Path(out).stat().st_size}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["build", "upload"])
    ap.add_argument("--nz-dir", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = Path(a.out) if a.out else Path(a.nz_dir).parent / "near_zero_banks.tgz"
    if a.cmd == "build":
        print(json.dumps({"sha256": build_bundle(Path(a.nz_dir), out), "out": str(out)}))
    else:
        print(json.dumps(upload(Path(a.nz_dir), out), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
