"""Colab bootstrap, secret authentication, frozen NF4 restore/prepare, and Hub durability.

LOCAL --check-local is read-only and never installs or provisions anything.
Without --check-local this script must run INSIDE an already user-created A100 VM.
"""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE.parents[1] / "src"))
from sca2_workbench.cohort import check_prefix, digest, json_bytes, publish, supervise


def local_check():
    registry = json.loads((PACKAGE / "models.json").read_text())
    items = json.loads((PACKAGE / "items.json").read_text())["items"]
    assert len(registry["models"]) == 43 and registry["hub_listing_cohort_count"] == 42
    assert len(items) == 23
    for name in ("unit.py", "prepare_nf4.py", "cohort_queue.py", "sync.py", "bundle.py", "keepalive.py"):
        assert (PACKAGE / "runner" / name).is_file(), name
    print("LOCAL_PREFLIGHT_PASS", "43 models; 23 model-only items; required runners present")


def setup(prefix):
    from google.colab import userdata
    os.environ["HF_TOKEN"] = userdata.get("HF_TOKEN")  # never print or persist this value
    if not os.environ["HF_TOKEN"]:
        raise ValueError("Colab secret HF_TOKEN missing")
    print("HF_SECRET_PRESENT", flush=True)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    os.environ.pop("PYTHONPATH", None)
    check_prefix(prefix)
    gpu = subprocess.check_output(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], text=True)
    if "A100" not in gpu:
        raise ValueError("expected an A100; stop this runtime rather than silently switching GPU")
    print("GPU", gpu.strip(), flush=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "uv==0.10.7", "psutil==7.2.2"], check=True)
    import shutil
    uv = shutil.which("uv")
    if not uv:
        raise ValueError("uv executable not found after install")
    quant = Path("/content/cohort-quant")
    capture = Path("/content/cohort-capture")
    for env, python in ((quant, "3.13.15"), (capture, "3.12.12")):
        if not (env / "bin/python").exists():
            subprocess.run([uv, "venv", "--python", python, str(env)], check=True)
        subprocess.run([uv, "pip", "install", "--python", str(env / "bin/python"),
                        "torch==2.11.0", "--index-url", "https://download.pytorch.org/whl/cu130"], check=True)
    common = ["bitsandbytes==0.50.2", "safetensors==0.8.0", "numpy==2.5.4", "psutil==7.2.2"]
    subprocess.run([uv, "pip", "install", "--python", str(quant / "bin/python"), *common,
                    "transformers==4.46.3", "huggingface_hub==0.36.2", "accelerate==0.34.0"], check=True)
    subprocess.run([uv, "pip", "install", "--python", str(capture / "bin/python"), *common,
                    "transformers==5.20.1", "huggingface_hub==2.2.0", "peft==0.21.2"], check=True)
    # A subprocess ensures installs are not shadowed by stale imports in the Colab kernel.
    boot = PACKAGE / "runner" / "bootstrap.py"
    subprocess.run([str(capture / "bin/python"), str(boot), "--durable", "--prefix", prefix], check=True)
    print("PROVISION_DONE", flush=True)


def durable(prefix):
    from huggingface_hub import HfApi, hf_hub_download
    api = HfApi(token=os.environ["HF_TOKEN"])
    repo = "Bonorinoa/SCA2-paper-b-artifacts"
    api.whoami()  # never print the returned identity or credentials
    print("HF_WHOAMI_OK", flush=True)
    files = api.list_repo_files(repo, repo_type="dataset")
    # Destination write probe before any model load. New run namespace only.
    probe = PACKAGE / "destination_probe.json"
    publish(probe, json_bytes({"kind": "model-only workbench store probe", "prefix": prefix}))
    commit = api.upload_file(repo_id=repo, repo_type="dataset", path_or_fileobj=probe,
                             path_in_repo=prefix + "/destination_probe.json")
    remote = hf_hub_download(repo, prefix + "/destination_probe.json", repo_type="dataset", revision=commit.oid)
    assert digest(remote) == digest(probe)
    frozen = Path("/content/cohort_nf4")
    instrument_path = prefix + "/nf4/instrument.json"
    if instrument_path in files:
        meta_path = hf_hub_download(repo, instrument_path, repo_type="dataset")
        record = json.loads(Path(meta_path).read_text())
        for name, expected in record["files"].items():
            cached = Path(hf_hub_download(repo, prefix + "/nf4/" + name, repo_type="dataset"))
            if digest(cached) != expected:
                raise ValueError(f"frozen quantized codes digest mismatch: {name}")
            publish(frozen / name, cached.read_bytes())
        publish(frozen / "instrument.json", Path(meta_path).read_bytes())
        print("NF4_RESTORED", len(record["files"]), flush=True)
    else:
        # Production full loader is in a separate, historically pinned interpreter.
        rc = supervise(["/content/cohort-quant/bin/python", str(PACKAGE / "runner" / "prepare_nf4.py"),
                        "--frozen", str(frozen)], timeout=1800, log_path=Path("/content/nf4_prepare.log"))
        if rc != 0:
            raise RuntimeError(f"NF4 preparation failed rc={rc}; inspect /content/nf4_prepare.log")
        record = json.loads((frozen / "instrument.json").read_text())
        commit = api.upload_folder(repo_id=repo, repo_type="dataset", folder_path=frozen,
                                   path_in_repo=prefix + "/nf4", commit_message="freeze A100 NF4 instrument")
        for name, expected in {**record["files"], "instrument.json": digest(frozen / "instrument.json")}.items():
            cached = hf_hub_download(repo, prefix + "/nf4/" + name, repo_type="dataset", revision=commit.oid,
                                     force_download=True)
            if digest(cached) != expected:
                raise ValueError(f"remote frozen instrument mismatch: {name}")
        print("NF4_REMOTE_VERIFIED", commit.oid, flush=True)
    print("DURABLE_PREFLIGHT_PASS", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-local", action="store_true")
    ap.add_argument("--durable", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--prefix")
    args = ap.parse_args()
    local_check()
    if not args.check_local:
        check_prefix(args.prefix or "")
        durable(args.prefix) if args.durable else setup(args.prefix)
