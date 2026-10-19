"""Durable, model-only artifact bus: restore once; commit and read back every unit."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from sca2_workbench.cohort import check_prefix, digest, publish

REPO = "Bonorinoa/SCA2-paper-b-artifacts"


def restore(root, prefix):
    from huggingface_hub import HfApi, hf_hub_download
    token = os.environ["HF_TOKEN"]
    prefix = check_prefix(prefix)
    api = HfApi(token=token)
    # A listing error must abort, never masquerade as an empty durable store.
    files = api.list_repo_files(REPO, repo_type="dataset")
    markers = sorted(x for x in files if x.startswith(prefix + "/exports/units/") and x.endswith(".json"))
    for name in markers:
        p = Path(hf_hub_download(REPO, name, repo_type="dataset", token=token))
        rec = json.loads(p.read_text())
        for relative, expected in rec["files"].items():
            downloaded = Path(hf_hub_download(REPO, prefix + "/exports/" + relative,
                                                repo_type="dataset", token=token))
            if digest(downloaded) != expected:
                raise ValueError("durable export digest mismatch")
            publish(root / relative, downloaded.read_bytes())
        publish(root / "units" / Path(name).name, p.read_bytes())
    if markers:
        from sca2_workbench.cohort import update_index
        update_index(root)
    print("RESTORED_UNITS", len(markers), flush=True)


def upload_unit(root, marker, prefix):
    from huggingface_hub import HfApi, hf_hub_download
    token = os.environ["HF_TOKEN"]
    api = HfApi(token=token)
    prefix = check_prefix(prefix)
    rec = json.loads(marker.read_text())
    names = [*rec["files"], str(marker.relative_to(root)), "index.json", "attempts/*"]
    commit = api.upload_folder(repo_id=REPO, repo_type="dataset", folder_path=root,
                               path_in_repo=prefix + "/exports", allow_patterns=names,
                               commit_message=f"workbench unit {marker.stem}")
    # Read the exact newly committed remote bytes, not mutable main or local export paths.
    for name in [*rec["files"], str(marker.relative_to(root))]:
        remote = Path(hf_hub_download(REPO, prefix + "/exports/" + name, repo_type="dataset",
                                     revision=commit.oid, token=token))
        if digest(remote) != digest(root / name):
            raise ValueError(f"uploaded digest mismatch: {name}")
    print("REMOTE_VERIFIED", commit.oid, marker.name, flush=True)
    return commit.oid


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["restore", "upload"])
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--marker", type=Path)
    args = ap.parse_args()
    if args.mode == "restore":
        restore(args.root, args.prefix)
    else:
        upload_unit(args.root, args.marker, args.prefix)
