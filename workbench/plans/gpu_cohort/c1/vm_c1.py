"""C1 on ONE T4 VM: install pinned quant stack, quantize base (production loader), manifest, decode-equality, tar.
Run via colab exec -f. Token must already be in kernel env. Never writes to the Hub; never prints the token."""
import hashlib, json, os, shutil, subprocess, sys, tarfile, threading, time
from pathlib import Path
T0 = time.time()
OUT = Path("/content/c1_out"); OUT.mkdir(exist_ok=True)
def stamp(n): print(f"[{time.time()-T0:7.1f}s] {n}", flush=True)
def run(cmd, log, **kw):
    with open(log, "ab") as f: return subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, **kw).returncode
def need(rc, what, log):
    if rc:
        print(f"FAILED {what} rc={rc}; tail:", Path(log).read_text()[-2500:].replace(os.environ.get("HF_TOKEN", "\0"), "<tok>"), flush=True)
        raise SystemExit(f"FAILED {what}")
stop = threading.Event()
def hb():
    while not stop.is_set(): time.sleep(45); print(f"  .. alive {time.time()-T0:.0f}s", flush=True)
threading.Thread(target=hb, daemon=True).start()
try:
    man = json.loads(Path("/content/cohort.manifest.json").read_text())
    assert hashlib.sha256(Path("/content/cohort.tar.gz").read_bytes()).hexdigest() == man["bundle_sha256"]
    with tarfile.open("/content/cohort.tar.gz") as t: t.extractall("/content", filter="data")
    ROOT = Path("/content/workbench/plans/gpu_cohort"); (ROOT / "benchmark").mkdir(exist_ok=True)
    shutil.copy("/content/prepare_nf4_bench.py", ROOT / "benchmark/prepare_nf4_bench.py")
    shutil.copy("/content/decode_check.py", ROOT / "decode_check.py")
    assert os.environ.get("HF_TOKEN"), "no token"
    smi = subprocess.check_output(["nvidia-smi"], text=True); (OUT / "nvidia_smi.txt").write_text(smi)
    gpu = subprocess.check_output(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], text=True).strip()
    print("GPU", gpu, flush=True)
    assert "T4" in gpu, f"NOT A T4: {gpu}"
    stamp("bundle+gpu ok")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", CUBLAS_WORKSPACE_CONFIG=":4096:8"); env.pop("PYTHONPATH", None)
    L = OUT / "install.log"
    need(run([sys.executable, "-m", "pip", "install", "-q", "uv==0.10.7", "psutil==7.2.2"], L), "pip uv", L)
    uv = shutil.which("uv"); venv = Path("/content/cohort-quant")
    for cmd in ([uv, "venv", "--python", "3.13.15", str(venv)],
                [uv, "pip", "install", "--python", str(venv/"bin/python"), "torch==2.11.0", "--index-url", "https://download.pytorch.org/whl/cu130"],
                [uv, "pip", "install", "--python", str(venv/"bin/python"), "bitsandbytes==0.50.2", "safetensors==0.8.0", "numpy==2.5.4", "psutil==7.2.2",
                 "transformers==4.46.3", "huggingface_hub==0.36.2", "accelerate==0.34.0"]):
        need(run(cmd, L, env=env), "install " + " ".join(cmd[1:3]), L)
    stamp("installed")
    py = str(venv/"bin/python")
    probe = subprocess.run([py, "-c", "import torch,bitsandbytes,transformers;print(torch.__version__,torch.cuda.is_available(),torch.cuda.get_device_name(0),bitsandbytes.__version__,transformers.__version__)"],
                           capture_output=True, text=True, env=env)
    print("PROBE", probe.stdout.strip(), probe.stderr.strip()[-300:], flush=True)
    assert "True Tesla T4 0.50.2 4.46.3" in probe.stdout, "probe failed"
    frozen = Path("/content/frozen_nf4_t4")
    PL = OUT / "nf4_prepare.log"
    need(run([py, str(ROOT/"benchmark/prepare_nf4_bench.py"), "--frozen", str(frozen)], PL, env=env), "NF4 prepare", PL)
    stamp("nf4_prepared")
    inst = json.loads((frozen/"instrument.json").read_text())
    assert "T4" in inst["device_name"] and inst["base_snapshot"] == "0e9e39f249a16976918f6564b8830bc894c89659" and not inst["diagnostic"]
    files = sorted(p.name for p in frozen.iterdir() if p.is_file())
    assert len([f for f in files if f.endswith(".safetensors")]) == 224, len(files)
    manifest = {"what": "frozen T4-CUDA NF4 instrument (C1, card t_cb68fe78)", "device": inst["device_name"], "quantization_device": "cuda",
                "versions": inst["versions"], "python": inst["python"], "cuda": inst["cuda"], "base_model": "meta-llama/Llama-3.1-8B-Instruct",
                "base_revision": inst["base_snapshot"], "quant_type": "nf4", "double_quant": True, "compute_dtype": "float16", "blocksize": 64,
                "n_files": len(files), "nvidia_smi": smi, "files": {f: hashlib.sha256((frozen/f).read_bytes()).hexdigest() for f in files}}
    (frozen/"MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    stamp("manifest")
    dl = OUT / "decode_check.log"
    rc = run([py, str(ROOT/"decode_check.py"), str(frozen), str(OUT/"decode_vm.json"), "cuda", "cpu"], dl, env=env)
    print(Path(dl).read_text()[-1500:], flush=True)
    print("DECODE_RC", rc, flush=True)
    stamp("decode_checked")
    with tarfile.open("/content/frozen_nf4_t4.tar", "w") as t: t.add(frozen, "frozen_nf4_t4")
    print("TAR", os.path.getsize("/content/frozen_nf4_t4.tar"), flush=True)
    # Contents API 500s on a single multi-GB file (observed): ship 64 MB parts + a part manifest.
    parts = Path("/content/c1_parts"); parts.mkdir(exist_ok=True); plist = {}
    with open("/content/frozen_nf4_t4.tar", "rb") as src:
        i = 0
        while True:
            blk = src.read(64 << 20)
            if not blk: break
            n = f"part_{i:04d}"; (parts / n).write_bytes(blk); plist[n] = hashlib.sha256(blk).hexdigest(); i += 1
    (parts / "PARTS.json").write_text(json.dumps({"tar_bytes": os.path.getsize("/content/frozen_nf4_t4.tar"), "parts": plist}, indent=1))
    print("PARTS", len(plist), flush=True)
    subprocess.run(["tar", "czf", "/content/c1_records.tar.gz", "-C", "/content", "c1_out"])
    print("C1_VM_DONE", flush=True)
finally:
    stop.set()
