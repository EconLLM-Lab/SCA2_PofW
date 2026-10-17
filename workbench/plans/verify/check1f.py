"""Check 1e/1f: margins unchanged vs the pre-@1.1 export, and shared arrays byte-identical.

Compares workbench/exports (new, @1.1) against $TMPDIR/exports_old (the engineer's kept copy, @1).
No model load: pure manifest + byte comparison.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reader import Export

NEW = "/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.worktrees/adapter-brain-vizualization/workbench/exports"
OLD = os.environ.get("TMPDIR", "/tmp") + "/exports_old"

new = Export(NEW)
old_files = sorted(f for f in os.listdir(OLD) if f.endswith(".json") and f != "index.json")
print("old files:", len(old_files))

margin_bad, scalar_bad, arr_bad, missing = [], [], [], []
n_arrays_cmp = 0
for f in old_files:
    npath = os.path.join(NEW, f)
    if not os.path.exists(npath):
        missing.append(f)
        continue
    om = json.load(open(os.path.join(OLD, f)))
    nm = json.load(open(npath))
    # --- readout scalars (margins, probs, embed_attr) must be identical ---
    for k, vo in om.get("readout", {}).items():
        vn = nm.get("readout", {}).get(k)
        if isinstance(vo, (int, float)) and not isinstance(vo, bool):
            if vn is None or vo != vn:
                scalar_bad.append((f, "readout." + k, vo, vn))
        elif isinstance(vo, dict):
            for kk, vv in vo.items():
                if vn is None or vn.get(kk) != vv:
                    scalar_bad.append((f, "readout.%s.%s" % (k, kk), vv, None if vn is None else vn.get(kk)))
    if om["kind"] == "pair":
        for k in ("d_margin", "d_probs"):
            if om.get(k) != nm.get(k):
                scalar_bad.append((f, k, om.get(k), nm.get(k)))
    # --- every @1 array that survives must be byte-identical ---
    for name, spec in om["arrays"].items():
        if name not in nm["arrays"]:
            missing.append((f, name))
            continue
        nspec = nm["arrays"][name]
        if nspec["dtype"] != spec["dtype"] or nspec["nbytes"] != spec["nbytes"] or nspec["shape"] != spec["shape"]:
            arr_bad.append((f, name, "meta", spec, nspec))
            continue
        n_arrays_cmp += 1
        with open(os.path.join(OLD, om["bin"]), "rb") as fh:
            fh.seek(spec["offset"]); a = fh.read(spec["nbytes"])
        with open(os.path.join(NEW, nm["bin"]), "rb") as fh:
            fh.seek(nspec["offset"]); b = fh.read(nspec["nbytes"])
        if a != b:
            diff = sum(1 for x, y in zip(a, b) if x != y)
            arr_bad.append((f, name, "bytes differ", diff, len(a)))

print("arrays compared byte-for-byte:", n_arrays_cmp)
print("missing files/arrays:", missing)
print("scalar mismatches:", len(scalar_bad))
for s in scalar_bad[:20]:
    print("   ", s)
print("array mismatches:", len(arr_bad))
for s in arr_bad[:20]:
    print("   ", s)

# --- explicit margin table ---
print("\nmargin + d_margin, old(@1) vs new(@1.1):")
worst = 0.0
for f in old_files:
    om = json.load(open(os.path.join(OLD, f)))
    nm = json.load(open(os.path.join(NEW, f)))
    if om["kind"] == "run":
        a = om["readout"]["margin"]; b = nm["readout"]["margin"]
        ac = om["readout"]["margin_clamped"]; bc = nm["readout"]["margin_clamped"]
        d = max(abs(a - b), abs(ac - bc)); worst = max(worst, d)
        if d:
            print("   DIFF %s %s %.17g vs %.17g" % (f, "margin", a, b))
    else:
        for k in ("d_margin", "d_margin_clamped"):
            if k in om:
                d = abs(om[k] - nm[k]); worst = max(worst, d)
                if d:
                    print("   DIFF %s %s %.17g vs %.17g" % (f, k, om[k], nm[k]))
print("worst margin difference over all old/new files: %.3e" % worst)
print("\nnew-only files (added after the re-export):",
      sorted(set(os.listdir(NEW)) - set(os.listdir(OLD)) - {"index.json"}))
