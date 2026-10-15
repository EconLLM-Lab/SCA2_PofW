#!/usr/bin/env python3
"""Paper B — data gates (T2). Re-runnable checkpoint before any compute.

Checks, against config.COHORT and the shared bank:
  1. every cohort country has a bank file with N_ROWS rows
  2. the bank is shared (identical prompt/response texts across countries)
  3. labels match the deterministic sign rule chosen=A iff z_dim >= 0
  4. row order is identical across the cohort (=> one common seed-42 split)
  5. prints twin groups and near-zero exposure for the record

Exit code 0 = all gates pass. Prints nothing to disk.
Usage: python paper_b/verify_gates.py
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import config as C
from lib import load_country, response_pair
import sign_prompt as SP

_parser = argparse.ArgumentParser(description="Paper B bank gates")
_parser.add_argument("--bank-dir", default="", help="override config.BANK_DIR for this process")
_parser.add_argument("--scan-text", action="store_true",
                     help="fail if scenario text contains a country name, ISO code, or Q-id")
_args = _parser.parse_args()
if _args.bank_dir:
    C.BANK_DIR = Path(_args.bank_dir)

DIMS = ["trust", "risktaking", "patience", "altruism", "posrecip", "negrecip"]
fails: list[str] = []


def bank_path(cc: str):
    return C.BANK_DIR / C.BANK_FILE.format(cc=cc)


print(f"cohort: {len(C.COHORT)} countries")
data = {}
for cc in C.COHORT:
    p = bank_path(cc)
    if not p.exists():
        fails.append(f"{cc}: bank file missing ({p})")
        continue
    rows, by_prompt = load_country(p)
    data[cc] = (p, rows, by_prompt)
    if len(rows) != C.N_ROWS:
        fails.append(f"{cc}: {len(rows)} rows, expected {C.N_ROWS}")

# gate 2: shared bank
bank_sig = None
for cc, (p, rows, _) in data.items():
    sig = tuple(sorted(hashlib.md5(
        (r["prompt"] + r["response_a"] + r["response_b"]).encode()).hexdigest() for r in rows))
    if bank_sig is None:
        bank_sig = sig
    elif sig != bank_sig:
        fails.append(f"{cc}: bank content differs from cohort reference")
print("gate 2 (shared bank):", "PASS" if not any("bank content" in f for f in fails) else "FAIL")

# gate 3: labels
from lib import DIMENSION_RENAMES
BACK = {v: k for k, v in DIMENSION_RENAMES.items()}
label_bad = 0
for cc, (_, rows, _) in data.items():
    for r in rows:
        dim = BACK.get(r["gps_dimension"], r["gps_dimension"])
        z = r["gps_profile_vector"][dim]
        if r["chosen_option"] != ("A" if z >= 0 else "B"):
            label_bad += 1
if label_bad:
    fails.append(f"{label_bad} label mismatches vs the sign rule")
print("gate 3 (labels match sign rule):", "PASS" if label_bad == 0 else f"FAIL ({label_bad})")

# gate 4: row order identical
orders = {cc: tuple(r["triplet_id"] for r in rows) for cc, (_, rows, _) in data.items()}
ref_order = next(iter(orders.values()))
order_bad = [cc for cc, o in orders.items() if o != ref_order]
if order_bad:
    fails.append(f"row order differs in {order_bad}")
print("gate 4 (common split eligible):", "PASS" if not order_bad else f"FAIL {order_bad}")

# record: twins + near-zero exposure
prof = {}
for cc, (_, rows, _) in data.items():
    v = rows[0]["gps_profile_vector"]
    prof[cc] = tuple(1 if v[d] >= 0 else 0 for d in DIMS)
groups = defaultdict(list)
for cc, p in prof.items():
    groups[p].append(cc)
twins = sorted(sorted(g) for g in groups.values() if len(g) > 1)
print(f"\nrecord: {len(groups)} distinct sign profiles; {len(twins)} twin groups")
for g in twins:
    print("   ", " ".join(g))

nz = {cc: sum(1 for r in rows if r.get("near_zero_z"))
      for cc, (_, rows, _) in data.items()}
hot = {cc: n for cc, n in nz.items() if n and n > C.N_ROWS * 0.2}
print(f"\nrecord: near-zero(|z|<{C.NEAR_ZERO}) heavy countries (>20% of rows): {hot}")

print()
if _args.scan_text and data:
    text_hits = []
    qid = re.compile(r"\bQ\d{2,3}\b")
    for cc, (_, rows, _) in data.items():
        for r in rows:
            blob = " ".join(str(r.get(k, "")) for k in ("prompt", "response_a", "response_b", "chosen", "rejected"))
            hits = SP.leak_hits(blob)
            qhits = qid.findall(blob)
            if hits or qhits:
                text_hits.append(f"{cc}: {hits + qhits}")
                if len(text_hits) >= 8:
                    break
        if len(text_hits) >= 8:
            break
    if text_hits:
        fails.append(f"text scan failed ({len(text_hits)} shown): {text_hits}")
        print("gate 5 (no country / WVS id in text): FAIL")
    else:
        print("gate 5 (no country / WVS id in text): PASS")

if fails:
    print("GATES FAILED:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("ALL GATES PASS")
