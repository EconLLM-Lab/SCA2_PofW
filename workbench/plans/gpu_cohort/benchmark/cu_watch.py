"""Poll `colab usage`; log balance/rate; stop SESSION when its spend reaches the cap.

usage: cu_watch.py SESSION OUTDIR CAP_CU [GLOBAL_STOP_BALANCE]
Exits when OUTDIR/STOPPED exists. Before stopping at the cap it tries to download the VM logs.
"""
import os, re, subprocess, sys, time
from pathlib import Path

session, out, cap = sys.argv[1], Path(sys.argv[2]), float(sys.argv[3])
floor = float(sys.argv[4]) if len(sys.argv) > 4 else None
env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
env["PATH"] = os.path.expanduser("~/.local/bin") + ":" + env["PATH"]

def usage():
    o = subprocess.run(["colab", "usage"], capture_output=True, text=True, env=env, timeout=60).stdout
    b = float(re.search(r"balance:\s*([\d.]+)", o).group(1)); r = float(re.search(r"rate:\s*([\d.]+)", o).group(1))
    return b, r

start, _ = usage()
log = out / "cu_watch.log"
log.open("a").write(f"{time.strftime('%H:%M:%S')} start_balance={start}\n")
while not (out / "STOPPED").exists():
    time.sleep(60)
    try:
        b, r = usage()
    except Exception as e:
        log.open("a").write(f"{time.strftime('%H:%M:%S')} usage error {e!r}\n"); continue
    spent = start - b
    log.open("a").write(f"{time.strftime('%H:%M:%S')} balance={b} rate={r} session_spent={spent:.2f}\n")
    if spent >= cap or (floor is not None and b <= floor):
        log.open("a").write("CAP REACHED: rescuing logs then stopping session\n")
        for f in ("bench.log", "setup_timing.json", "gpu.txt", "nf4_prepare.log", "install_quant.log", "install_capture.log"):
            subprocess.run(["colab", "download", "-s", session, f"/content/bench/{f}", str(out / f"capcut_{f}")], env=env, timeout=120)
        subprocess.run(["colab", "stop", "-s", session], env=env, timeout=120)
        (out / "CAP_STOPPED").write_text(str(spent))
        break
