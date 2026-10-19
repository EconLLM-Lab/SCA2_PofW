"""Recompute storage from actual capture array layouts and timing from local dry-run evidence."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from sca2_workbench.cohort import PACKAGE
from sca2_workbench.items import Item, readout_ids
from transformers import AutoTokenizer
from huggingface_hub import snapshot_download


def size_for(manifest, tokens):
    old_t = len(manifest["tokens"]) if manifest["kind"] == "run" else 132
    offset = 0
    for a in sorted(manifest["arrays"].values(), key=lambda v: v["offset"]):
        offset += (-offset) % 8
        count = 1
        for dim in a["shape"]:
            count *= tokens if dim == old_t else dim
        offset += count * (2 if a["dtype"] == "uint16" else 4)
    return offset


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verification", type=Path, required=True)
    ap.add_argument("--unquantized-verification", type=Path, required=True)
    ap.add_argument("--cu-per-hour", type=float, default=13.08, help="planning assumption only; replace with actual Colab rate")
    args = ap.parse_args()
    verification = json.loads(args.verification.read_text())
    unquant = json.loads(args.unquantized_verification.read_text())
    base_dir = Path(verification["baseline"])
    run = json.loads(next(base_dir.glob("run__*arg*.json")).read_text())
    pair = json.loads(next(base_dir.glob("pair__*.json")).read_text())
    pair["tokens"] = None
    items = json.loads((PACKAGE / "items.json").read_text())["items"]
    reg = json.loads((PACKAGE / "models.json").read_text())
    tok = AutoTokenizer.from_pretrained(snapshot_download(reg["base"]["model_id"], revision=reg["base"]["revision"],
                                                         local_files_only=True,
                                                         allow_patterns=["*.json", "tokenizer*"]))
    sizes = []
    for row in items:
        item = Item(**{k: v for k, v in row.items() if k != "archive"})
        tokens = len(readout_ids(tok, item, {"date_string": "26 Jul 2024"})["prompt_ids"])
        sizes.append({"item": item.item_id, "T": tokens, "run_bytes": size_for(run, tokens),
                      "pair_bytes": size_for(pair, tokens)})
    # A100 is intentionally NOT benchmarked here. Budget NO speed-up against the Mac.
    # Use the larger baseline/resume wall clock, scaled to the longest item for every unit.
    max_t = max(x["T"] for x in sizes)
    pilot_t = len(run["tokens"])
    nf4_seconds = max(verification["baseline_wall_seconds"], verification["resume_wall_seconds"]) * max_t / pilot_t
    uq_seconds = max(unquant["baseline_wall_seconds"], unquant["resume_wall_seconds"]) * max_t / pilot_t
    n = len(sizes)
    base_seconds = nf4_seconds  # conservative: same budget as the four-pass adapter unit
    pure_bytes = 43 * sum(x["run_bytes"] for x in sizes) + 42 * sum(x["pair_bytes"] for x in sizes)
    manifest_allowance = (43 + 42) * n * 100_000
    export_bytes = pure_bytes + manifest_allowance
    instrument_bytes = sum(p.stat().st_size for p in (PACKAGE / "local_nf4").glob("*.safetensors"))
    setup_hours = .5  # install, snapshot/adapter downloads, freeze, upload/readback
    sync_hours = export_bytes / 10_000_000 / 3600 * 2  # assumed 10 MB/s upload AND verification download
    phase1_hours = (n * base_seconds + 42 * n * nf4_seconds) / 3600 + setup_hours + sync_hours
    phase2_hours = 43 * n * uq_seconds / 3600 + setup_hours + sync_hours
    record = {"items": n, "models": 43, "adapters": 42, "adapter_item_units": 42*n,
              "base_item_units": n, "a100_unit_seconds": nf4_seconds, "a100_base_seconds": base_seconds,
              "unquantized_unit_seconds": uq_seconds, "max_T": max_t, "pilot_T": pilot_t,
              "a100_benchmark_performed": False, "assumed_cu_per_hour": args.cu_per_hour,
              "phase1_gpu_hours": phase1_hours, "phase1_compute_units": phase1_hours * args.cu_per_hour,
              "phase2_gpu_hours": phase2_hours, "phase2_compute_units": phase2_hours * args.cu_per_hour,
              "phase1_plus_unquantized_base_hours": phase1_hours + n*uq_seconds/3600 + sum(x["run_bytes"] for x in sizes)/10_000_000/3600*2,
              "binary_export_bytes": pure_bytes, "manifest_allowance_bytes": manifest_allowance,
              "export_bytes": export_bytes, "export_GB": export_bytes/1e9,
              "frozen_nf4_bytes_cpu_diagnostic": instrument_bytes, "setup_hours_assumption": setup_hours,
              "sync_hours_assumption": sync_hours, "timing_evidence": str(args.verification),
              "unquantized_timing_evidence": str(args.unquantized_verification), "sizes": sizes}
    (PACKAGE / "estimate.json").write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record, indent=1))


if __name__ == "__main__":
    main()
