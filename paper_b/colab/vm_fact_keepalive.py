# VM-side keep-alive: a blocking execution that keeps the Colab kernel busy while detached jobs run.
# Colab Pro appears to reclaim a VM whose kernel has no running execution (it held two T4s for 7 hours when
# this was attached). Prints one status line every 5 minutes and exits only when every launched step has an
# .rc file AND no launcher shell is alive. Steps are tracked by their .log, so chained steps (training, then
# replicate; scoring gate, then conditions) are all covered.
# colab exec -s pb-a -f paper_b/colab/vm_fact_keepalive.py --timeout 43200
import glob, os, subprocess, time
ROOT = os.environ.get("KEEPALIVE_ROOT", "/content/pb_data")
INTERVAL = int(os.environ.get("KEEPALIVE_INTERVAL", "300"))


def alive(pid_file):
    """True while the launcher shell runs. A finished child that its parent has not reaped is a zombie
    (state Z): kill(pid, 0) still succeeds for it, so ask ps for the state instead."""
    try:
        pid = int(open(pid_file).read())
        state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    except (OSError, ValueError):
        return False
    return bool(state) and not state.startswith("Z")


t0 = time.time()
while True:
    logs = sorted(p for p in glob.glob(f"{ROOT}/logs/*.log") if not p.endswith("fact_gates.log"))
    pending = [os.path.basename(p)[:-4] for p in logs if not os.path.exists(p[:-4] + ".rc")]
    shells = [os.path.basename(p)[:-4] for p in glob.glob(f"{ROOT}/logs/*.pid") if alive(p)]
    ads = sum(len([x for x in os.listdir(d) if os.path.exists(f"{d}/{x}/adapter_config.json")])
              for d in glob.glob(f"{ROOT}/adapters*") if os.path.isdir(d))
    try:
        gpu = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader"],
                             capture_output=True, text=True).stdout.strip()
    except OSError:
        gpu = "n/a"
    print(f"{time.strftime('%H:%M')} +{(time.time()-t0)/60:.0f}m pending={pending} shells={shells} local_adapters={ads} gpu={gpu}", flush=True)
    if not logs and not shells:
        print("no launched job found; nothing to keep alive"); break
    if not pending and not shells:
        print("all launched steps finished:", {os.path.basename(r)[:-3]: open(r).read().strip() for r in sorted(glob.glob(f"{ROOT}/logs/*.rc"))}); break
    time.sleep(INTERVAL)
