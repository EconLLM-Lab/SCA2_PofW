"""Build the exact uncommitted, model-only launch bundle (strict allowlist)."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[4]


def members():
    wb = ROOT / "workbench"
    package = wb / "plans" / "gpu_cohort"
    paths = sorted((wb / "src" / "sca2_workbench").glob("*.py"))
    paths += sorted((package / "runner").glob("*.py"))
    paths += [package / "models.json", package / "items.json", package / "estimate.json",
              wb / "plans" / "stage1_8b_gaps.json"]
    return paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    paths = members()
    record = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    with tarfile.open(args.out, "w:gz") as tar:
        for p in paths:
            tar.add(p, arcname=str(p.relative_to(ROOT)), recursive=False)
    manifest = args.out.with_suffix("").with_suffix(".manifest.json")
    manifest.write_text(json.dumps({"files": record, "bundle_sha256": hashlib.sha256(args.out.read_bytes()).hexdigest()}, indent=1))
    print("BUNDLE", args.out, "files", len(paths), "sha256", hashlib.sha256(args.out.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
