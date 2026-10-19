"""Read-only Hub cohort inventory, pinned metadata + downloaded config hashes."""
import argparse
import concurrent.futures
import hashlib
import json
import os
import re
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download

BASE = "meta-llama/Llama-3.1-8B-Instruct"
REPO = "Bonorinoa/SCA2-paper-b-adapters"
REVISION = "c4b0f36eae0c15e508f72b606861798c8359131f"
BASE_REVISION = "0e9e39f249a16976918f6564b8830bc894c89659"


def inventory():
    token = os.environ.get("HF_TOKEN") or None
    info = HfApi(token=token).repo_info(REPO, repo_type="dataset", revision=REVISION, files_metadata=True)
    files = {x.rfilename: x for x in info.siblings}
    weights = sorted(k for k in files if re.fullmatch(r"adapters/[A-Z]{3}/adapter_model\.safetensors", k))
    if len(weights) != 42:
        raise ValueError(f"expected 42 cohort-1 adapters, found {len(weights)}")

    def entry(name):
        cc = name.split("/")[1]
        config_name = f"adapters/{cc}/adapter_config.json"
        p = Path(hf_hub_download(REPO, config_name, repo_type="dataset", revision=REVISION, token=token))
        cfg = json.loads(p.read_text())
        lfs = files[name].lfs
        sha = lfs.sha256 if hasattr(lfs, "sha256") else lfs["sha256"]
        return {"key": cc, "model_id": BASE, "repo_id": REPO, "repo_type": "dataset",
                "revision": info.sha, "path": f"adapters/{cc}", "sha256": sha,
                "bytes": files[name].size, "config_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "r": cfg["r"], "alpha": cfg["lora_alpha"], "target_modules": sorted(cfg["target_modules"])}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        adapters = list(pool.map(entry, weights))
    expected = (16, 32, ["k_proj", "o_proj", "q_proj", "v_proj"])
    return {"base": {"key": "base", "model_id": BASE, "revision": BASE_REVISION},
            "adapter_revision": info.sha, "hub_listing_cohort_count": len(weights),
            "models": [{"key": "base", "model_id": BASE, "revision": BASE_REVISION}] + adapters,
            "exceptions": [x["key"] for x in adapters if (x["r"], x["alpha"], x["target_modules"]) != expected]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    result = inventory()
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"models": len(result["models"]), "adapters": result["hub_listing_cohort_count"],
                      "revision": result["adapter_revision"], "exceptions": result["exceptions"]}))
