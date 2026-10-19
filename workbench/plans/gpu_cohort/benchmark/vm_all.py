"""B0: provision + NF4 prep + benchmark on ONE Colab VM, with printed timings.

Run via `colab exec -f vm_all.py --timeout N`; expects the HF token already in the kernel env
(set by the per-run setenv file), /content/cohort.tar.gz + manifest and the benchmark scripts uploaded.
Never writes to the Hub. Never prints the token.
"""
import hashlib, json, os, shutil, subprocess, sys, tarfile, threading, time
from pathlib import Path

LABEL = os.environ.get("B0_LABEL", "vm")
ONLY = os.environ.get("B0_ONLY", "both")
MAC_FIRST = os.environ.get("B0_MAC_FIRST", "")
SHIP_NF4 = os.environ.get("B0_SHIP_NF4", "0") == "1"
T0 = time.time()
STATE = Path("/content/bench"); STATE.mkdir(exist_ok=True)
timing = {}
def stamp(name):
    timing[name] = round(time.time() - T0, 1)
    print(f"[{timing[name]:7.1f}s] {name}", flush=True)
    (STATE / "setup_timing.json").write_text(json.dumps(timing, indent=1))

def run(cmd, log, **kw):
    with open(log, "ab") as f:
        return subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, **kw).returncode

def need(rc, what, log):
    if rc != 0:
        print(f"FAILED {what} rc={rc}; tail of {log}:", flush=True)
        print(Path(log).read_text()[-2500:].replace(os.environ.get("HF_TOKEN", "\0"), "<tok>"), flush=True)
        raise SystemExit(f"FAILED {what}")

def heartbeat(stop):
    while not stop.is_set():
        time.sleep(45); print(f"  .. alive {time.time()-T0:.0f}s", flush=True)
stop = threading.Event(); threading.Thread(target=heartbeat, args=(stop,), daemon=True).start()

def finish():
    small = Path("/content/bench_small.tar.gz")
    with tarfile.open(small, "w:gz") as t:
        for p in STATE.rglob("*"):
            if p.is_file() and p.suffix in (".json", ".log", ".txt", ".jsonl") and "exports" not in p.parts[:3]:
                t.add(p, p.relative_to("/content"))
        if SHIP_NF4:
            for n in ("model.layers.0.self_attn.q_proj", "model.layers.16.mlp.gate_proj", "model.layers.31.mlp.down_proj"):
                f = Path("/content/cohort_nf4") / f"{n}.weight.safetensors"
                if f.exists():
                    t.add(f, f"bench/nf4_layers/{f.name}")
    print("TAR", small.stat().st_size, flush=True)

try:
    # --- S1 bundle ---------------------------------------------------------
    man = json.loads(Path("/content/cohort.manifest.json").read_text())
    assert hashlib.sha256(Path("/content/cohort.tar.gz").read_bytes()).hexdigest() == man["bundle_sha256"]
    with tarfile.open("/content/cohort.tar.gz") as t:
        t.extractall("/content", filter="data")
    for name, sha in man["files"].items():
        assert hashlib.sha256((Path("/content") / name).read_bytes()).hexdigest() == sha, name
    ROOT = Path("/content/workbench/plans/gpu_cohort")
    (ROOT / "benchmark").mkdir(exist_ok=True)
    for f in ("bench_units.py", "prepare_nf4_bench.py"):
        shutil.copy(f"/content/{f}", ROOT / "benchmark" / f)
    stamp("bundle_verified")
    assert os.environ.get("HF_TOKEN"), "HF token not in kernel env"
    gpu = subprocess.check_output(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"], text=True).strip()
    print("GPU", gpu, flush=True)
    (STATE / "gpu.txt").write_text(gpu + "\n" + subprocess.check_output(["nvidia-smi"], text=True))
    print("RAM_GB", int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1e9), "CPUS", os.cpu_count(), flush=True)
    stamp("gpu_probe")
    # --- S2 installs (two interpreters, in parallel) + model download -----------
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", CUBLAS_WORKSPACE_CONFIG=":4096:8"); env.pop("PYTHONPATH", None)
    need(run([sys.executable, "-m", "pip", "install", "-q", "uv==0.10.7", "psutil==7.2.2"], STATE / "pip_uv.log"), "pip uv", STATE / "pip_uv.log")
    uv = shutil.which("uv"); assert uv
    quant, capture = Path("/content/cohort-quant"), Path("/content/cohort-capture")
    common = ["bitsandbytes==0.50.2", "safetensors==0.8.0", "numpy==2.5.4", "psutil==7.2.2"]
    errs = {}
    def build(venv, py, extra, name, post=None):
        log = STATE / f"{name}.log"
        try:
            for cmd in ([uv, "venv", "--python", py, str(venv)],
                        [uv, "pip", "install", "--python", str(venv / "bin/python"), "torch==2.11.0", "--index-url", "https://download.pytorch.org/whl/cu130"],
                        [uv, "pip", "install", "--python", str(venv / "bin/python"), *common, *extra]):
                rc = run(cmd, log, env=env)
                if rc: errs[name] = f"rc={rc} {cmd[1:3]}"; return
            if post: post(log)
        except Exception as e:
            errs[name] = repr(e)
    def download(log):
        code = ("import json,os\nfrom pathlib import Path\nfrom sca2_workbench.cohort import fetch_inputs\n"
                "reg=json.loads(Path('/content/workbench/plans/gpu_cohort/models.json').read_text())\n"
                "fetch_inputs(reg,'base'); fetch_inputs(reg,'ARG'); print('DOWNLOADED')\n")
        rc = run([str(capture / "bin/python"), "-c", code], log, env=dict(env, PYTHONPATH="/content/workbench/src"))
        if rc: errs["download"] = f"rc={rc}"
    th = [threading.Thread(target=build, args=(quant, "3.13.15", ["transformers==4.46.3", "huggingface_hub==0.36.2", "accelerate==0.34.0"], "install_quant")),
          threading.Thread(target=build, args=(capture, "3.12.12", ["transformers==5.20.1", "huggingface_hub==2.2.0", "peft==0.21.2"], "install_capture", download))]
    for t in th: t.start()
    for t in th: t.join()
    stamp("installs_and_download_done")
    if errs:
        for n in errs: print("ERR", n, errs[n], Path(STATE / (n.replace("download", "install_capture") + ".log")).read_text()[-1500:], flush=True)
        raise SystemExit(f"FAILED install/download {errs}")
    probe = ("import torch,bitsandbytes,transformers,importlib.metadata as m;"
             "print(torch.__version__,torch.cuda.is_available(),torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,"
             "bitsandbytes.__version__,transformers.__version__)")
    for n, v in (("quant", quant), ("capture", capture)):
        out = subprocess.run([str(v / "bin/python"), "-c", probe], capture_output=True, text=True, env=env)
        print("PROBE", n, out.stdout.strip(), out.stderr.strip()[-300:], flush=True)
        if "True" not in out.stdout:
            raise SystemExit(f"FAILED cuda not usable in {n} env")
    versions = {"quant": "pinned", "capture": "pinned"}
    # --- S3 NF4 prep (production loader, CUDA) --------------------------------
    frozen = Path("/content/cohort_nf4")
    rc = run([str(quant / "bin/python"), str(ROOT / "benchmark" / "prepare_nf4_bench.py"), "--frozen", str(frozen)], STATE / "nf4_prepare.log", env=env)
    need(rc, "NF4 prepare", STATE / "nf4_prepare.log")
    shutil.copy(frozen / "instrument.json", STATE / "nf4_instrument.json")
    stamp("nf4_prepared")
    print("SETUP_MINUTES", round(timing["nf4_prepared"] / 60, 2), flush=True)
    # --- S4 benchmark ---------------------------------------------------------
    cmd = [str(capture / "bin/python"), "-u", str(ROOT / "benchmark/bench_units.py"), "--root", str(ROOT), "--out", str(STATE / "out"),
           "--frozen", str(frozen), "--device", "cuda", "--label", LABEL, "--only", ONLY]
    if MAC_FIRST: cmd += ["--mac-f64-first", MAC_FIRST]
    with open(STATE / "bench.log", "ab") as f:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, text=True)
        for line in p.stdout:
            f.write(line.encode())
            if line.startswith(("UNIT_", "BENCH", "SKIP", "F64")):
                print(line.rstrip(), flush=True)
        rc = p.wait()
    stamp("bench_done")
    print("BENCH_RC", rc, flush=True)
finally:
    stop.set()
    try: finish()
    except Exception as e: print("finish error", e, flush=True)
    print("VM_ALL_END", flush=True)
