"""Projection of the 989-unit cohort per device x dtype from the measured benchmark units.

central = mean of measured items per arm; upper = longest item (Q107) for every unit (A3's convention).
CU = rate * (wall_h + setup_h + reclaims * reclaim_h), reclaims = wall_h / 4 (one per ~4 h, expected value),
reclaim_h = (12.5 min re-provision/re-gate + half an in-flight unit)/60. Hub upload/readback (A3: 1.371874296 h at an
assumed 10 MB/s) was NOT measured here (no Hub writes allowed) and is shown as an explicit add-on.
"""
import json, re, statistics, sys
from pathlib import Path

N_BASE, N_ADAPTER = 23, 966
SYNC_H = 1.371874296
RECLAIM_MIN = 12.5
BALANCE_START, SPENT = 186.66, float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
AVAILABLE = BALANCE_START - SPENT
B = Path(__file__).parent
devs = {"mac": ("mac/out", None), "a100": ("a100/bench/out", "a100"), "l4": ("l4/bench/out", "l4"), "t4": ("t4/bench/out", "t4"), "g4": ("g4/bench/out", "g4")}

def rate(d):
    p = B / d / "cu_watch.log"
    vals = [float(m.group(1)) for m in re.finditer(r"rate=([\d.]+)", p.read_text())] if p.exists() else []
    vals = [v for v in vals if v > 0]
    return statistics.median(vals) if vals else None

out = []
for name, (path, d) in devs.items():
    f = B / path / "summary.json"
    if not f.exists(): continue
    rows = [r for r in json.loads(f.read_text()) if r["status"] in ("ok", "failed")]
    setup = None
    if d:
        t = json.loads((B / d / "bench/setup_timing.json").read_text()); setup = t["nf4_prepared"] / 60
    for dt in ("float64", "float32"):
        arg = [r for r in rows if r["dtype"] == dt and r["model"] == "ARG"]
        base = [r for r in rows if r["dtype"] == dt and r["model"] == "base"]
        if not arg: continue
        a_c = statistics.mean(r["wall_seconds"] for r in arg); a_u = max(r["wall_seconds"] for r in arg)
        if base: b_c = statistics.mean(r["wall_seconds"] for r in base); b_u = max(r["wall_seconds"] for r in base); bnote = ""
        else: b_c, b_u, bnote = a_c, a_u, "base units charged at the ARG time (not measured)"
        row = {"device": name, "dtype": dt, "n_measured_adapter": len(arg), "n_measured_base": len(base), "note": bnote,
               "setup_min": setup, "cu_per_h": rate(d) if d else 0.0}
        for tag, (a, b) in (("central", (a_c, b_c)), ("upper", (a_u, b_u))):
            wall_h = (N_BASE * b + N_ADAPTER * a) / 3600
            row[f"{tag}_unit_s"] = {"adapter": a, "base": b}
            row[f"{tag}_wall_h"] = wall_h
            if d:
                r_ = row["cu_per_h"]; unit_h = (a / 2) / 3600
                reclaim_h = RECLAIM_MIN / 60 + unit_h
                for lab, extra in (("", 0.0), ("_with_sync", SYNC_H)):
                    wh = wall_h + extra
                    cu = r_ * (wh + setup / 60 + (wh / 4) * reclaim_h)
                    row[f"{tag}_cu{lab}"] = cu; row[f"{tag}_fits{lab}"] = cu <= AVAILABLE
                    row[f"{tag}_arith{lab}"] = (f"{r_:.2f} CU/h x ({wh:.2f} h + {setup/60:.3f} h setup + {wh/4:.2f} reclaims x {reclaim_h:.3f} h)")
            else:
                row[f"{tag}_cu"] = 0.0; row[f"{tag}_fits"] = True
        out.append(row)
(B / "projection.json").write_text(json.dumps({"available_cu": AVAILABLE, "rows": out}, indent=1))
print(f"available = {BALANCE_START} - {SPENT} = {AVAILABLE:.2f} CU")
for r in out:
    print(f"{r['device']:5s} {r['dtype'][-2:]} unit s (central) adapter {r['central_unit_s']['adapter']:.1f} base {r['central_unit_s']['base']:.1f} | wall h {r['central_wall_h']:.2f} (upper {r['upper_wall_h']:.2f}) | "
          f"CU {r['central_cu']:.1f} / {r['upper_cu']:.1f}" + (f" ; +sync CU {r['central_cu_with_sync']:.1f} / {r['upper_cu_with_sync']:.1f} fits={r['upper_fits_with_sync']}" if r['device'] != 'mac' else "") + f" {r['note']}")
