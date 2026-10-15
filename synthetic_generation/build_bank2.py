#!/usr/bin/env python3
"""Build a second shared scenario bank under the frozen sign rule.

One command, two stages, no country-specific model calls:
  1. generate the shared triplets with the documented generator endpoints
  2. relabel them for every GPS country with `deterministic_sign`

Refuses to run without a token that can call the endpoints named in
`sca2_datagen/config.py`. The 403 this lab's scoring token returns is a
permission wall, not a cold start.

Usage (from synthetic_generation/):
  python build_bank2.py --out-root outputs/bank2_20261011
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sca2_datagen.config import HF_ENDPOINTS  # noqa: E402
from sca2_datagen.relabel import DIMS, LABELING_RULE  # noqa: E402

TARGET_TRIPLETS = 658


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-root", required=True)
    ap.add_argument("--scenarios-per-dim", type=int, default=110,
                    help="110 reproduced the source bank's 658 triplets")
    ap.add_argument("--scenario-batch-size", type=int, default=6)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--use-anchors", action="store_true", default=True)
    ap.add_argument("--gps-json", default=None)
    args = ap.parse_args()

    raw_dir = Path(args.out_root) / "raw"
    bank_dir = Path(args.out_root) / "gps_sign_relabel_bank2"
    raw_dir.mkdir(parents=True, exist_ok=True)

    print("labeling rule:", LABELING_RULE, "| dimensions:", ",".join(DIMS))
    print("endpoints required:")
    for alias, spec in HF_ENDPOINTS.items():
        print(f"  {alias:10} {spec['role']:9} {spec['endpoint_name']} "
              f"(token env {spec['api_key_env']})")

    gen = [
        sys.executable, "run.py",
        "--scenarios-per-dim", str(args.scenarios_per_dim),
        "--scenario-batch-size", str(args.scenario_batch_size),
        "--concurrency", str(args.concurrency),
        "--labeling", "deterministic_sign",
        "--countries", "USA",
        "--output-dir", str(raw_dir),
    ]
    if args.use_anchors:
        gen += ["--use-anchors", "True"]
    print("\n>>>", " ".join(gen), "\n", flush=True)
    rc = subprocess.call(gen)
    if rc != 0:
        print(f"generation failed rc={rc}; the scorer endpoint may also be required "
              "because run.py always calls run_scoring_qc_export")
        return rc

    relabel = [
        sys.executable, "-m", "sca2_datagen.relabel",
        "--checkpoint", str(raw_dir / "checkpoint_raw_pairs.jsonl"),
        "--output-dir", str(bank_dir),
    ]
    if args.gps_json:
        relabel += ["--gps-json", args.gps_json]
    print("\n>>>", " ".join(relabel), "\n", flush=True)
    rc = subprocess.call(relabel)
    if rc != 0:
        print(f"relabel failed rc={rc}")
        return rc

    print(f"\nbank -> {bank_dir}")
    print("next: python ../paper_b/verify_gates.py "
          f"--bank-dir {bank_dir} --scan-text")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
