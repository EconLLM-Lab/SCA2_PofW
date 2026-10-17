import json, os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reader import Export

ROOT = "/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.worktrees/adapter-brain-vizualization/workbench/exports"
ex = Export(ROOT)

def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]

print("=== 1d pair attributions ===")
worst = {}
fails = []
for p in ex.index["pairs"]:
    m = ex.manifest(p["file"])
    ma = ex.manifest(m["runs"]["a"])
    mb = ex.manifest(m["runs"]["b"])
    L = 30; H = 9

    d_head = ex.nested(m, "d_head_attr")          # (L,H)
    d_mlp = ex.nested(m, "d_mlp_attr")            # (L,)
    d_attn = ex.nested(m, "d_attn_attr")          # (L,)
    d_head_c = ex.nested(m, "d_head_attr_clamped")
    d_mlp_c = ex.nested(m, "d_mlp_attr_clamped")

    # --- stored float32 sums (in float64) + float64 d_embed ---
    s32 = sum(sum(row) for row in d_head) + sum(d_mlp) + m["d_embed_attr"]
    g32 = abs(s32 - m["d_margin"])
    # --- float64 sums ---
    # float64 sums are not stored; approximate via float32 arrays is the same as above.
    s32c = sum(sum(row) for row in d_head_c) + sum(d_mlp_c) + m["d_embed_attr_clamped"]
    g32c = abs(s32c - m["d_margin_clamped"])
    # --- d_attn_attr == sum_h d_head_attr ---
    attn_from_heads = [sum(row) for row in d_head]
    g_attn = max(abs(a - b) for a, b in zip(attn_from_heads, d_attn))

    # --- d_head_attr == head_attr(B) - head_attr(A) to float32 ---
    ha = ex.nested(ma, "head_attr"); hb = ex.nested(mb, "head_attr")
    maxdh = 0.0; maxdh_rel = 0.0; maxdh_mag = 0.0
    for l in range(L):
        for h in range(H):
            # float32 difference of the two stored float32 run values
            ref = f32(f32(hb[l][h]) - f32(ha[l][h]))
            v = d_head[l][h]
            dd = abs(v - ref)
            maxdh = max(maxdh, dd)
            maxdh_mag = max(maxdh_mag, abs(ref))
            denom = max(abs(ref), 1e-30)
            maxdh_rel = max(maxdh_rel, dd / denom)
    # also d_mlp_attr vs mlp_attr
    mlpa = ex.nested(ma, "mlp_attr"); mlpb = ex.nested(mb, "mlp_attr")
    maxdm = max(abs(f32(f32(mlpb[l]) - f32(mlpa[l])) - d_mlp[l]) for l in range(L))

    k = p["file"]
    worst.setdefault("g32", (0, None)); worst.setdefault("g32c", (0, None))
    worst.setdefault("attn", (0, None)); worst.setdefault("dh", (0, None)); worst.setdefault("dm", (0, None))
    for key, val in (("g32", g32), ("g32c", g32c), ("attn", g_attn), ("dh", maxdh), ("dm", maxdm)):
        if val > worst[key][0]:
            worst[key] = (val, k)
    if g32 > 1e-6 or g32c > 1e-6:
        fails.append((k, "sum gap", g32, g32c))
    if maxdh > 1e-6 and maxdh_rel > 1e-5:
        fails.append((k, "d_head_attr mismatch", maxdh, maxdh_rel))

print("pairs:", len(ex.index["pairs"]))
for key in ["g32", "g32c", "attn", "dh", "dm"]:
    print("  worst %-6s = %.6e  %s" % (key, worst[key][0], worst[key][1]))
print("fails:", fails)

print()
print("=== per-pair stored-vs-float64-run values ===")
for p in ex.index["pairs"]:
    m = ex.manifest(p["file"])
    ma = ex.manifest(m["runs"]["a"]); mb = ex.manifest(m["runs"]["b"])
    # d_margin from runs
    rma = ma["readout"]["margin"]; rmb = mb["readout"]["margin"]
    dm_from_runs = rmb - rma
    # d_embed_attr from runs
    dea = mb["readout"]["embed_attr"] - ma["readout"]["embed_attr"]
    d_head = ex.nested(m, "d_head_attr"); d_mlp = ex.nested(m, "d_mlp_attr")
    s32 = sum(sum(row) for row in d_head) + sum(d_mlp) + m["d_embed_attr"]
    print("  %-58s d_margin=%.9f  runs=%.9f  diff=%.2e | sum32-margin=%.2e | d_embed stored-runs=%.2e" % (
        p["file"][:58], m["d_margin"], dm_from_runs, abs(m["d_margin"] - dm_from_runs),
        abs(s32 - m["d_margin"]), abs(m["d_embed_attr"] - dea)))
