#!/usr/bin/env python3
"""Screen preference-profile identity across the D_syn bank.

Countries whose GPS z-SIGN patterns are identical on every item receive identical
DPO labels (labeling rule G = sign(z)) -> their adapters are replicates, not
independent country models. This script clusters countries by full label pattern
(prompt -> chosen/rejected order) so future country sets can be deduplicated
(or deliberately include replicates).

Usage: run from the repo root.
"""
import json, glob, os

def load(p):
    with open(p) as f:
        return [json.loads(l) for l in f if l.strip()]

files = sorted(glob.glob("synthetic_generation/outputs/gps_sign_relabel_all/D_syn_*.jsonl"))
profiles = {}
for f in files:
    c = os.path.basename(f).removeprefix("D_syn_").removesuffix(".jsonl")
    rows = load(f)
    pat = tuple((r["prompt"], r["chosen"], r["rejected"]) for r in rows)
    profiles.setdefault(pat, []).append(c)

print(f"countries: {len(files)}, distinct profiles: {len(profiles)}")
print("\n=== clusters of size > 1 (label-identical countries) ===")
for pat, cs in sorted(profiles.items(), key=lambda kv: -len(kv[1])):
    if len(cs) > 1:
        print(f"  {len(cs)} countries: {', '.join(cs)}")
print("\n=== singleton profiles ===")
print("  " + ", ".join(sorted(cs[0] for pat, cs in profiles.items() if len(cs) == 1)))
