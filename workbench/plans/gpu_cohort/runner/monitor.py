"""Absolute, model-only unit progress from the durable store (or a local test directory)."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from sca2_workbench.cohort import PACKAGE, check_prefix


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix")
    ap.add_argument("--root", type=Path, help="local read-only test instead of Hub")
    ap.add_argument("--expect-complete", action="store_true")
    args = ap.parse_args()
    if args.root:
        paths = list((args.root / "units").glob("*.json"))
    else:
        from huggingface_hub import HfApi, hf_hub_download
        prefix = check_prefix(args.prefix or "")
        token = os.environ.get("HF_TOKEN") or None
        repo = "Bonorinoa/SCA2-paper-b-artifacts"
        api = HfApi(token=token)
        revision = api.repo_info(repo, repo_type="dataset").sha
        names = [x for x in api.list_repo_files(repo, repo_type="dataset", revision=revision)
                 if x.startswith(prefix + "/exports/units/") and x.endswith(".json")]
        paths = [Path(hf_hub_download(repo, x, repo_type="dataset", revision=revision, token=token)) for x in names]
    allowed_models = {x["key"] for x in json.loads((PACKAGE / "models.json").read_text())["models"]}
    allowed_items = {x["item_id"] for x in json.loads((PACKAGE / "items.json").read_text())["items"]}
    expected = len(allowed_models) * len(allowed_items)
    records = [json.loads(p.read_text()) for p in paths]
    observed = set()
    for r in records:
        key = (r["inputs"]["model"], r["inputs"]["item"])
        if key[0] not in allowed_models or key[1] not in allowed_items or key in observed:
            raise ValueError(f"unexpected or duplicate unit: {key}")
        observed.add(key)
    done = sum(r["pass"] is True for r in records)
    failed = len(records) - done
    result = {"done": done, "failed": failed, "expected": expected,
              "complete": done == expected and failed == 0,
              "source": str(args.root) if args.root else args.prefix}
    print(json.dumps(result, indent=1))
    if failed or (args.expect_complete and not result["complete"]):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
