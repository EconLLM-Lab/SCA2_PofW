"""Collect per-unit results for a device dir: timings, gates (failing checks named), parity ulp."""
import json, sys
from pathlib import Path

def fails(node, path=""):
    out = []
    if isinstance(node, dict):
        if node.get("pass") is False and path:
            out.append((path, {k: node.get(k) for k in ("error", "rel", "tau", "scale") if k in node}))
        for k, v in node.items():
            out += fails(v, f"{path}/{k}")
    return out

def unit_rows(outdir):
    outdir = Path(outdir)
    rows = []
    for line in (outdir / "bench_results.jsonl").read_text().splitlines():
        r = json.loads(line)
        row = {k: r.get(k) for k in ("label", "dtype", "model", "item", "status", "wall_seconds", "peak_vram_mib_nvidia_smi")}
        t, s = r.get("timings", {}), r.get("supervisor", {})
        if t:
            worker = s.get("seconds")
            row.update(worker_seconds=worker, startup_fetch_seconds=(worker - t["total_seconds"]) if worker else None,
                       capture_seconds=t["capture_seconds"], reference_export_write_seconds=t["total_seconds"] - t["capture_seconds"],
                       total_after_load_seconds=t["total_seconds"], peak_rss_gib=t["peak_rss_gib"], gates_pass=t["pass"],
                       supervisor_peak_rss_gb=(s.get("peak_rss_bytes") or 0) / 1e9)
            marker = outdir / "units" / f"nf4_dequant_{r['dtype']}_{r['model']}_{r['item']}.json"
            if marker.exists():
                files = json.loads(marker.read_text())["files"]
                ulps, failing = [], []
                for name in files:
                    if name.endswith(".json"):
                        m = json.loads((outdir / name).read_text())
                        failing += [(name.split("__")[0] + ":" + name.split("__")[-2][-12:], *x) for x in fails(m.get("conservation", {}), "conservation")]
                        if "archive_parity" in m:
                            ulps.append(m["archive_parity"]["max_fp16_ulp"])
                row.update(parity_max_fp16_ulp=max(ulps) if ulps else None, parity_per_arm=ulps, failing_checks=failing)
        rows.append(row)
    return rows

if __name__ == "__main__":
    for d in sys.argv[1:]:
        rows = unit_rows(d)
        Path(d, "summary.json").write_text(json.dumps(rows, indent=1))
        for r in rows:
            print(r["dtype"][-2:], r["model"], r["item"][-3:], r["status"], round(r["wall_seconds"] or 0, 1),
                  "load", round(r.get("startup_fetch_seconds") or 0, 1), "cap", round(r.get("capture_seconds") or 0, 1),
                  "ref+exp", round(r.get("reference_export_write_seconds") or 0, 1), "ulp", r.get("parity_max_fp16_ulp") and round(r["parity_max_fp16_ulp"], 2),
                  "rss", r.get("supervisor_peak_rss_gb") and round(r["supervisor_peak_rss_gb"], 2), "vram", r["peak_vram_mib_nvidia_smi"], "FAIL" if r.get("failing_checks") else "")
            for f in r.get("failing_checks", []): print("    ", f)
