# VM-side keep-alive: a blocking execution that keeps the Colab kernel busy while the detached jobs train.
# Colab Pro appears to reclaim a VM whose kernel has no running execution (both overnight losses fit this);
# this loop prints a one-line status every 5 minutes and exits when every launched step has an .rc file.
# colab exec -s pb-a -f paper_b/colab/vm_fact_keepalive.py --timeout 43200
import glob, os, subprocess, time
ROOT = "/content/pb_data"
t0 = time.time()
while True:
    pids = sorted(glob.glob(f"{ROOT}/logs/*.pid"))
    pending = [os.path.basename(p)[:-4] for p in pids if not os.path.exists(p[:-4] + ".rc")]
    ads = sum(len([x for x in os.listdir(d) if os.path.exists(f"{d}/{x}/adapter_config.json")]) for d in glob.glob(f"{ROOT}/adapters*") if os.path.isdir(d))
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
    print(f"{time.strftime('%H:%M')} +{(time.time()-t0)/60:.0f}m pending={pending} local_adapters={ads} gpu={gpu}", flush=True)
    if not pids:
        print("no launched job found; nothing to keep alive"); break
    if not pending:
        print("all launched steps finished:", {os.path.basename(r)[:-3]: open(r).read().strip() for r in glob.glob(f"{ROOT}/logs/*.rc")}); break
    time.sleep(300)
