"""Execute this file with `colab exec -f ...` AFTER uploading the bundle.

Edit PREFIX before packing only if a new namespace is required. Never reuse a namespace
for changed code, dtype, device, item set, or quantization instrument.
"""
import json
from pathlib import Path
import runpy
import sys
import tarfile

PREFIX = "workbench_cohort/phase1_nf4_20261018_a3"
if __name__ == "__main__":
    bundle = Path("/content/cohort.tar.gz")
    manifest = Path("/content/cohort.manifest.json")
    import hashlib
    expected = json.loads(manifest.read_text())
    assert hashlib.sha256(bundle.read_bytes()).hexdigest() == expected["bundle_sha256"]
    with tarfile.open(bundle) as tar:
        tar.extractall("/content", filter="data")
    for name, sha in expected["files"].items():
        assert hashlib.sha256((Path("/content") / name).read_bytes()).hexdigest() == sha, name
    Path("/content/cohort_prefix.txt").write_text(PREFIX)
    boot = "/content/workbench/plans/gpu_cohort/runner/bootstrap.py"
    sys.argv = [boot, "--prefix", PREFIX]
    runpy.run_path(boot, run_name="__main__")
