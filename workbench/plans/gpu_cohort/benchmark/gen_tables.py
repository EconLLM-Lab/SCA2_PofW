"""Emit markdown tables for BENCHMARK.md from summary.json / projection.json / watcher logs (no hand-typed numbers)."""
import json, re, statistics
from pathlib import Path
B = Path(__file__).parent
DEV = [("mac", "Mac (12 CPU, 24 GB, CPU codes)", "mac/out", None), ("a100", "A100-SXM4-80GB high-mem", "a100/bench/out", "a100"),
       ("l4", "L4", "l4/bench/out", "l4"), ("t4", "T4", "t4/bench/out", "t4"), ("g4", "G4 RTX PRO 6000 Blackwell", "g4/bench/out", "g4"),
       ("g4r2", "G4 replicate (2nd session)", "g4r2/bench/out", "g4r2")]
def rate(d):
    p = B / d / "cu_watch.log"; v = [float(x) for x in re.findall(r"rate=([\d.]+)", p.read_text())]; v = [x for x in v if x > 0]
    return (statistics.median(v), min(v), max(v), len(v)) if v else None
print("### Per-unit table (seconds; load = process start + imports + input fetch; cap = 4 streamed passes; ref+exp+write = 2 float32 HF reference forwards + manifests + file writes)\n")
print("| device | dtype | unit | wall s | load s | capture s | ref+exp+write s | peak RSS GB | peak VRAM MiB | gates | max parity ulp (arms) |")
print("|---|---|---|---:|---:|---:|---:|---:|---:|---|---|")
for k, label, path, d in DEV:
    f = B / path / "summary.json"
    if not f.exists(): continue
    for r in json.loads(f.read_text()):
        unit = f"{r['model']} x {r['item'][4:]}"
        if r["status"].startswith("skipped"):
            print(f"| {label} | {r['dtype'][-2:]} | {unit} | skipped (f64 > 3x Mac on first unit) | | | | | | | |"); continue
        g = "PASS" if r["gates_pass"] else "FAIL: " + ", ".join(sorted({x[1].split('/')[-1] for x in r["failing_checks"] if "checks/" in x[1]}))
        u = ", ".join(f"{x:.2f}" for x in r["parity_per_arm"])
        print(f"| {label} | {r['dtype'][-2:]} | {unit} | {r['wall_seconds']:.1f} | {r['startup_fetch_seconds']:.1f} | {r['capture_seconds']:.1f} | {r['reference_export_write_seconds']:.1f} | {r['supervisor_peak_rss_gb']:.2f} | {r['peak_vram_mib_nvidia_smi'] or ''} | {g} | {max(r['parity_per_arm']):.2f} ({u}) |")
print("\n### Per-device table\n")
print("| device | setup min (provision to NF4 frozen) | measured CU/h (median; min-max; polls) | ARG f64 mean s/unit | base f64 mean s/unit | ARG f32 mean s/unit | f64 gates | f32 gates | max VRAM MiB |")
print("|---|---:|---|---:|---:|---:|---|---|---:|")
for k, label, path, d in DEV:
    f = B / path / "summary.json"
    if not f.exists(): continue
    rows = [r for r in json.loads(f.read_text()) if r["status"] in ("ok", "failed")]
    def m(dt, mod):
        x = [r["wall_seconds"] for r in rows if r["dtype"] == dt and r["model"] == mod]; return f"{statistics.mean(x):.1f} (n={len(x)})" if x else "n/a"
    def gp(dt):
        x = [r for r in rows if r["dtype"] == dt]; return f"{sum(r['gates_pass'] for r in x)}/{len(x)} pass" if x else "n/a"
    setup = f"{json.loads((B/d/'bench/setup_timing.json').read_text())['nf4_prepared']/60:.2f}" if d else "0 (local codes pre-built)"
    rt = rate(d) if d else None
    rts = f"{rt[0]:.2f}; {rt[1]:.2f}-{rt[2]:.2f}; {rt[3]}" if rt else "0 (Mac)"
    vr = max([r["peak_vram_mib_nvidia_smi"] or 0 for r in rows]) or ""
    print(f"| {label} | {setup} | {rts} | {m('float64','ARG')} | {m('float64','base')} | {m('float32','ARG')} | {gp('float64')} | {gp('float32')} | {vr} |")
P = json.loads((B / "projection.json").read_text())
print(f"\n### Projection (989 units = 23 base + 966 adapter); CU available = 186.66 - benchmark spend = {P['available_cu']:.2f}\n")
print("| device | dtype | adapter s / base s (central) | wall h central (upper) | CU central (upper) | CU with +1.37 h Hub sync, central (upper) | fits (upper, with sync) |")
print("|---|---|---|---:|---:|---:|---|")
for r in P["rows"]:
    cu = "0" if r["device"] == "mac" else f"{r['central_cu']:.1f} ({r['upper_cu']:.1f})"
    cs = "0" if r["device"] == "mac" else f"{r['central_cu_with_sync']:.1f} ({r['upper_cu_with_sync']:.1f})"
    fit = "n/a (0 CU)" if r["device"] == "mac" else ("yes" if r["upper_fits_with_sync"] else "NO")
    print(f"| {r['device']} | {r['dtype'][-2:]} | {r['central_unit_s']['adapter']:.1f} / {r['central_unit_s']['base']:.1f}{' *' if r['note'] else ''} | {r['central_wall_h']:.2f} ({r['upper_wall_h']:.2f}) | {cu} | {cs} | {fit} |")
