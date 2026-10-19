"""B0 benchmark driver: runs the 8 benchmark units serially through runner/unit.py.

Same driver on the Mac (device cpu) and on Colab VMs (device cuda). It never edits the
package; it only calls runner/unit.py and records wall time, VRAM/RSS and file paths.
Order: ARG x Q57 first (it is the A3 reference unit and the 3x f64 slowdown gate).
"""
import argparse, json, os, subprocess, sys, threading, time
from pathlib import Path

F64 = [("ARG", "wvs_Q57"), ("base", "wvs_Q57"), ("ARG", "wvs_Q81"), ("base", "wvs_Q81"),
       ("ARG", "wvs_Q107"), ("base", "wvs_Q107")]
F32 = [("ARG", "wvs_Q57"), ("ARG", "wvs_Q107")]


class Vram(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.peak, self.stop = 0, False

    def run(self):
        while not self.stop:
            try:
                out = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], text=True)
                self.peak = max(self.peak, max(int(x) for x in out.split()))
            except Exception:
                pass
            time.sleep(0.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True, help="workbench/plans/gpu_cohort of the bundle in use")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--frozen", type=Path, required=True)
    ap.add_argument("--device", choices=["cpu", "cuda"], required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--mac-f64-first", type=float, help="Mac wall s of ARG x Q57 f64; skip rest of f64 if first > 3x")
    ap.add_argument("--only", choices=["f64", "f32", "both"], default="both")
    ap.add_argument("--timeout", type=float, default=3600)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    results = a.out / "bench_results.jsonl"
    plan = ([("float64", *u) for u in F64] if a.only in ("f64", "both") else []) + \
           ([("float32", *u) for u in F32] if a.only in ("f32", "both") else [])
    skip_f64 = False
    first_f64_wall = None
    for dtype, model, item in plan:
        rec = {"label": a.label, "device": a.device, "dtype": dtype, "model": model, "item": item}
        if dtype == "float64" and skip_f64:
            rec["status"] = "skipped_f64_over_3x_mac"
            results.open("a").write(json.dumps(rec) + "\n")
            print("SKIP", rec, flush=True)
            continue
        before = {p.name for p in (a.out / "attempts").glob("*")} if (a.out / "attempts").exists() else set()
        cmd = [sys.executable, str(a.root / "runner" / "unit.py"), "--model", model, "--item", item,
               "--weights", "nf4_dequant", "--dtype", dtype, "--device", a.device, "--output", str(a.out),
               "--frozen", str(a.frozen), "--timeout", str(a.timeout)]
        v = Vram()
        if a.device == "cuda":
            v.start()
        print("UNIT_START", dtype, model, item, flush=True)
        t0 = time.monotonic()
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", CUBLAS_WORKSPACE_CONFIG=":4096:8")
        env.pop("PYTHONPATH", None)
        rc = subprocess.run(cmd, env=env).returncode
        wall = time.monotonic() - t0
        v.stop = True
        rec.update(status="ok" if rc == 0 else "failed", exit_code=rc, wall_seconds=wall,
                   peak_vram_mib_nvidia_smi=v.peak if a.device == "cuda" else None)
        new = sorted(p for p in (a.out / "attempts").glob("*") if p.name not in before)
        for p in new:
            if p.name.endswith(".rc.json"):
                rec["supervisor"] = json.loads(p.read_text())
            elif p.suffix == ".json":
                rec["timings"] = json.loads(p.read_text())
        results.open("a").write(json.dumps(rec) + "\n")
        print("UNIT_RESULT", json.dumps({k: rec.get(k) for k in ("dtype", "model", "item", "status", "wall_seconds", "peak_vram_mib_nvidia_smi")}), flush=True)
        if dtype == "float64" and first_f64_wall is None:
            first_f64_wall = wall
            if a.mac_f64_first and wall > 3 * a.mac_f64_first:
                skip_f64 = True
                print("F64_SLOW: first unit > 3x Mac; skipping remaining f64 units", flush=True)
        if rc != 0:
            print("UNIT_FAILED continuing to next unit", flush=True)
    print("BENCH_DONE", a.label, flush=True)


if __name__ == "__main__":
    main()
