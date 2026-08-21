#!/usr/bin/env python3
"""Sign-vector analysis of the GPS labeling z-scores.

Why do countries get identical DPO labels? The production labeling rule is
G = sign(z) on the frozen A/B bank: each item's label uses only the SIGN of the
country's GPS z-score on that item's dimension. With 6 dimensions there are at
most 2^6 = 64 sign vectors, so countries with identical sign patterns are
label-equivalent (identical training data -> replicate adapters), even when the
z MAGNITUDES differ enormously (e.g. NLD patience +0.95 vs SAU +0.20).

Run from the repo root.
"""
import json, glob, os

def load(p):
    with open(p) as f:
        return [json.loads(l) for l in f if l.strip()]

DIMS = ["altruism", "negrecip", "patience", "posrecip", "risktaking", "trust"]

def z_by_dim(c):
    rows = load(f"synthetic_generation/outputs/gps_sign_relabel_all/D_syn_{c}.jsonl")
    zd = {}
    for r in rows:
        d = r.get("gps_dimension")
        z = r.get("z_value")
        if d and z is not None:
            zd.setdefault(d, set()).add(round(float(z), 6))
    return {d: (sorted(v) if len(v) > 1 else v.pop()) for d, v in zd.items()}

def signvec(zd):
    return "".join("+" if zd[d] > 0 else ("-" if zd[d] < 0 else "0") for d in DIMS)

files = sorted(glob.glob("synthetic_generation/outputs/gps_sign_relabel_all/D_syn_*.jsonl"))
clusters = {}
for f in files:
    c = os.path.basename(f).removeprefix("D_syn_").removesuffix(".jsonl")
    zd = z_by_dim(c)
    if len(zd) < 6:
        continue
    clusters.setdefault(signvec(zd), []).append(c)

print("=== clusters by sign vector (dims: altruism, negrecip, patience, posrecip, risktaking, trust) ===")
for vec, cs in sorted(clusters.items(), key=lambda kv: (-len(kv[1]), kv[0])):
    print(f"{vec}  ({len(cs):2d})  {', '.join(sorted(cs))}")
