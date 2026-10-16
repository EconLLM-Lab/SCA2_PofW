# VM-side status (the kernel is free because jobs are detached): colab exec -s pb-a -f paper_b/colab/vm_fact_status.py
import glob, os, subprocess
ROOT = "/content/pb_data"
for rc in sorted(glob.glob(f"{ROOT}/logs/*.rc")):
    print("finished:", os.path.basename(rc)[:-3], "rc =", open(rc).read().strip())
for pid in sorted(glob.glob(f"{ROOT}/logs/*.pid")):
    name = os.path.basename(pid)[:-4]
    alive = not os.path.exists(f"{ROOT}/logs/{name}.rc")
    print("running:" if alive else "ended:  ", name, "| pid", open(pid).read())
for d in sorted(glob.glob(f"{ROOT}/adapters*")):
    print(os.path.basename(d), "->", len([x for x in os.listdir(d) if os.path.exists(f"{d}/{x}/adapter_config.json")]), "adapters on local disk")
for log in sorted(glob.glob(f"{ROOT}/logs/fact_wave*.log") + glob.glob(f"{ROOT}/logs/fact_replicate*.log")):
    txt = open(log, errors="ignore").read()
    saved = [l for l in txt.splitlines() if l.startswith(("saved adapter", "HF upload", "[", "  !!", "hub:", "NOT ON", "all "))][-6:]
    print("--", os.path.basename(log), "(%d bytes)" % len(txt)); print("\n".join(saved))
    print("   last progress:", txt.replace("\r", "\n").strip().splitlines()[-1][:140])
print(subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip())
