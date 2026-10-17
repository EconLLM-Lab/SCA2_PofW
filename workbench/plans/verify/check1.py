import json, os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reader import Export

ROOT = "/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.worktrees/adapter-brain-vizualization/workbench/exports"
ex = Export(ROOT)

# ---- 1b: segments cover [0, T) exactly once, in order ----
bad = []
for r in ex.index["runs"]:
    m = ex.manifest(r["file"])
    segs = m["segments"]
    T = r["T"]
    if segs is None:
        bad.append((r["file"], "segments is null"))
        continue
    pos = 0
    order_ok = True
    for s in segs:
        if s["a"] != pos:
            order_ok = False
            bad.append((r["file"], "gap/overlap at a=%d expected %d" % (s["a"], pos)))
            break
        if s["b"] <= s["a"]:
            bad.append((r["file"], "empty or inverted segment %r" % (s,)))
        pos = s["b"]
    if order_ok and pos != T:
        bad.append((r["file"], "does not reach T: ends %d vs T=%d" % (pos, T)))
    # tokens length must equal T
    if len(m["tokens"]) != T:
        bad.append((r["file"], "token count %d vs T=%d" % (len(m["tokens"]), T)))
print("1b segments coverage failures:", len(bad))
for b in bad:
    print("   ", b)

# ---- segment inventory ----
from collections import Counter
kindsets = Counter()
for r in ex.index["runs"]:
    m = ex.manifest(r["file"])
    kindsets[tuple(s["kind"] for s in m["segments"])] += 1
print("\n1b distinct kind sequences (count):")
for k, c in kindsets.items():
    print("  %2d  %s" % (c, k))

# ---- 1c: decode 3 items' segment tokens ----
print("\n1c segment token decode:")
checked = []
seen_items = set()
for r in ex.index["runs"]:
    if r["item_id"] in seen_items:
        continue
    if len(checked) < 3:
        pass
    seen_items.add(r["item_id"])

def show(item_id):
    for r in ex.index["runs"]:
        if r["item_id"] == item_id:
            m = ex.manifest(r["file"])
            print("  === %s (%s, T=%d) ===" % (item_id, r["model"], r["T"]))
            for s in m["segments"]:
                toks = "".join(t["text"] for t in m["tokens"][s["a"]:s["b"]])
                print("    [%3d,%3d) %-11s %-38s |%s|" % (s["a"], s["b"], s["kind"], s["label"], toks.replace("\n", "\\n")[:150]))
            return

for it in ["bank_USA_00023ac74dac", "wvs_Q57", "bank_USA_7232414df567"]:
    show(it)
