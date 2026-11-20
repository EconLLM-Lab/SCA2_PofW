# VM-side: cohort status — which adapters exist, their measured minutes, ref cache.
import json, os, sys
sys.path.insert(0, "/content/SCA2_PofW/paper_b")
os.environ.setdefault("SCA2_PB_DATA_ROOT", "/content/drive/MyDrive/SCA2_paper_b")
import config as C

print("data root:", C.DATA_ROOT, "| exists:", C.DATA_ROOT.is_dir())
print("ref cache:", C.REF_CACHE_FILE.exists(),
      f"({sum(1 for _ in open(C.REF_CACHE_FILE)) if C.REF_CACHE_FILE.exists() else 0} rows)")

done, pending, mins = [], [], []
for cc in C.COHORT:
    d = C.ADAPTER_DIR / cc
    rec = d / "run_record.json"
    if (d / "adapter_config.json").exists():
        m = None
        if rec.exists():
            m = json.loads(rec.read_text()).get("train_minutes")
            mins.append(m)
        w = (d / "adapter_model.safetensors")
        sz = f"{w.stat().st_size/1e6:.1f}MB" if w.exists() else "no-weights"
        done.append((cc, m, sz))
    else:
        pending.append(cc)

print(f"\nDONE {len(done)} / PENDING {len(pending)}")
for cc, m, sz in done:
    print(f"  {cc}: train_minutes={m} weights={sz}")
if pending:
    print("pending:", " ".join(pending))

# prepared files
prep = sorted(p.name for p in C.PREPARED_DIR.glob("*_train_with_ref.jsonl")) if C.PREPARED_DIR.is_dir() else []
print("prepared train_with_ref files:", len(prep), prep[:5])

if mins:
    avg = sum(mins) / len(mins)
    print(f"\navg train_minutes/adapter: {avg:.1f}")
    print(f"projection for {len(pending)} remaining: {len(pending)*avg/60:.1f} h training "
          f"(+ ~3 min/adapter load) = ~{len(pending)*(avg+3)/60:.1f} h wall per single session")
    print(f"split 2 sessions: ~{len(pending)*(avg+3)/60/2:.1f} h each  |  ~{len(pending)*(avg+3)/60:.0f} T4-units")
    print("planning pad only: +3 min/adapter is not a measured load. "
          "Publication clocks are in paper_b/compute/publication_estimate.json.")
