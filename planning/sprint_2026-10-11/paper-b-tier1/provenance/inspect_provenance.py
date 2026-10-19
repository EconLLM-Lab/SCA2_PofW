"""Model-only archive provenance inspection. No human-data inputs or Hub writes."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import os
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
OLD = "86fbf1030db9d126b6b354d2d424f3da1f130d37"
ADAPTER_REVS = ["7550fd4cfe514470bb8d80918a43c9ae424d26b5", "c4b0f36eae0c15e508f72b606861798c8359131f"]
ARCHIVE = ROOT / "planning/sprint_2026-10-11/paper-b-20261011"


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fetch(url):
    headers = {}
    if os.environ.get("HF_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["HF_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
        return r.read()


def inspect():
    result = {"head": git("rev-parse", "HEAD").decode().strip(), "earliest_tracked_snapshot": OLD,
              "hf_token_present": bool(os.environ.get("HF_TOKEN")), "manifests": {}, "bundle_hashes": {},
              "model_only_files": {}, "hub": {}, "adapter_revisions": {}}
    for name in ["base", "USA_adapter"]:
        p = ARCHIVE / f"hub/runs/paper-b-20261011/manifests/{name}_manifest.json"
        result["manifests"][name] = json.loads(p.read_text())
        for sub in ["hub/runs/paper-b-20261011/synthetic", "scores_for_join", "scores"]:
            f = ARCHIVE / sub / f"{name}_option_probabilities.csv"
            if f.exists():
                rows = list(csv.DictReader(f.open()))
                result["model_only_files"][str(f.relative_to(ROOT))] = {"sha256":sha(f.read_bytes()), "n_rows":len(rows), "columns":list(rows[0])}
    commits = git("log", "--all", "--format=%H", "--", "paper_b").decode().splitlines()
    for rev in commits:
        h = hashlib.sha256()
        names = git("ls-tree", "-r", "--name-only", rev, "paper_b").decode().splitlines()
        for name in sorted(n for n in names if n.endswith(".py")):
            h.update(name.encode()); h.update(b"\0"); h.update(git("show", rev+":"+name))
        result["bundle_hashes"][rev] = h.hexdigest()
    for repo in ["SCA2-paper-b-artifacts", "SCA2-paper-b-adapters"]:
        for endpoint in ["tree/main?recursive=true&limit=1000", "commits/main?limit=100"]:
            key = repo+"/"+endpoint
            try:
                result["hub"][key] = json.loads(fetch("https://huggingface.co/api/datasets/Bonorinoa/"+key))
            except Exception as e:
                result["hub"][key] = {"error":type(e).__name__+": "+str(e)}
    for rev in ADAPTER_REVS:
        record = {}
        h = hashlib.sha256()
        for name in ["adapter_config.json", "adapter_model.safetensors"]:
            try:
                b = fetch(f"https://huggingface.co/datasets/Bonorinoa/SCA2-paper-b-adapters/resolve/{rev}/adapters/USA/{name}")
                record[name] = {"sha256":sha(b), "bytes":len(b)}
                if name.endswith(".json"):
                    record["config"] = json.loads(b)
                h.update(name.encode()); h.update(b"\0"); h.update(b)
            except Exception as e:
                record[name] = {"error":type(e).__name__+": "+str(e)}
        if not any("error" in record[n] for n in ["adapter_config.json", "adapter_model.safetensors"]):
            record["bundle_sha256"] = h.hexdigest()
        result["adapter_revisions"][rev] = record
    (OUT/"writer_inspection.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ["hub","bundle_hashes"]}, indent=2))
    print("matching_bundle_commits",[r for r,h in result["bundle_hashes"].items() if h==result["manifests"]["base"]["code_revision_sha256"]])


if __name__ == "__main__":
    inspect()
