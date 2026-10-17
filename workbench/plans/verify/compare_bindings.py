"""Compare the browser observations against the independent reader (verifier t_ebb2173c)."""
import json, os, re, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reader import Export

ROOT = "/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.worktrees/adapter-brain-vizualization/workbench/exports"
ex = Export(ROOT)
OBS = json.load(open(sys.argv[1]))

NUM = re.compile(r"^[−+-]?\d+(\.\d+)?([eE][−+-]?\d+)?$")


def num(s):
    s = s.strip().replace("−", "-")
    m = re.match(r"^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", s)
    return float(m.group(1)) if m else None


def sigdigits(s):
    s = s.strip().replace("−", "-").lstrip("+-")
    if "e" in s or "E" in s:
        s = re.split("[eE]", s)[0]
    s = s.replace(".", "")
    s = s.lstrip("0")
    return max(1, len(s.rstrip("0")) if s.rstrip("0") else len(s))


def close(shown_str, mine, slack=1):
    """True when the shown number equals `mine` to the precision it displays."""
    v = num(shown_str)
    if v is None or mine is None:
        return None
    p = sigdigits(shown_str)
    mag = abs(mine)
    tol = 0.5 * (10 ** (math.floor(math.log10(mag)) - (p - 1))) if mag > 0 else 1e-12
    if shown_str.strip().replace("−", "-").startswith("-") and "e" not in shown_str.lower():
        pass
    return abs(v - mine) <= tol * (1 + 1e-9) + 1e-12, {"shown": v, "mine": mine, "tol": tol, "p": p}


fails, checks = [], 0


def cmp(name, shown, mine, where):
    global checks
    r = close(shown, mine)
    checks += 1
    if r is None:
        fails.append({"check": name, "where": where, "shown": shown, "mine": mine, "why": "unparsable"})
        return
    ok, d = r
    if not ok:
        fails.append({"check": name, "where": where, "shown": shown, "mine": mine,
                      "why": "mismatch", "shown_v": d["shown"], "tol": d["tol"], "p": d["p"]})


def manifest(model, item):
    return ex.manifest("run__%s__%s.json" % (model, item))


def pairman(a, b, item):
    return ex.manifest("pair__%s__%s__%s.json" % (a, b, item))


report = []
for tag, tabs in OBS["tabs"].items():
    a, b, item = tag.split("|")
    ma, mb = manifest(a, item), manifest(b, item)
    mp = pairman(a, b, item)
    ha = ex.nested(ma, "head_attr"); hb = ex.nested(mb, "head_attr")
    na = ex.nested(ma, "head_norm"); nb = ex.nested(mb, "head_norm")
    kd = ex.nested(mp, "d_head_attr"); kdn = ex.nested(mp, "d_head_norm")
    counts = {"C": 0, "B": 0, "A": 0}

    # ---------------- tab C
    C = tabs["C"]
    for key, titles in C["titles"].items():
        l, h = map(int, key.split(","))
        # three groups: A, B, B-A
        for idx, t in enumerate(titles):
            m = re.search(r"push on the margin ([−+-]?[0-9.]+)", t)
            if not m:
                continue
            if idx == 0:
                cmp("C ladder A cell", m.group(1), ha[l][h], "cell %s group A: %s" % (key, t))
            elif idx == 1:
                cmp("C ladder B cell", m.group(1), hb[l][h], "cell %s group B: %s" % (key, t))
            else:
                cmp("C ladder B-A cell", m.group(1), kd[l][h], "cell %s group B-A: %s" % (key, t))
            counts["C"] += 1
    for hv in C["hovers"]:
        l, h = hv["l"], hv["h"]
        for row in (hv["rows"] or []):
            if len(row) < 4:
                continue
            lab, A, B, ch = row[0], row[1], row[2], row[3]
            if lab.startswith("Write size"):
                cmp("C hover write A", A, na[l][h], "hover %d,%d" % (l, h))
                cmp("C hover write B", B, nb[l][h], "hover %d,%d" % (l, h))
                cmp("C hover write change", ch, kdn[l][h], str(hv["title"])[:80])
                counts["C"] += 3
            elif lab.startswith("Push on the margin"):
                cmp("C hover DLA A", A, ha[l][h], "hover %d,%d" % (l, h))
                cmp("C hover DLA B", B, hb[l][h], "hover %d,%d" % (l, h))
                cmp("C hover DLA change", ch, kd[l][h], "hover %d,%d change" % (l, h))
                counts["C"] += 3
    for row in (C["pinned"]["rows"] or []):
        if len(row) >= 4 and row[0].startswith("Push on the margin"):
            l, h = 12, 3
            cm2 = re.search(r"sel=(-?\d+),(-?\d+)", C["pinned"]["url"])
            if cm2:
                l, h = int(cm2.group(1)), int(cm2.group(2))
            if h >= 0:
                cmp("C pinned DLA A", row[1], ha[l][h], "pinned url %s" % C["pinned"]["url"])
                cmp("C pinned DLA B", row[2], hb[l][h], "pinned")
                cmp("C pinned DLA change", row[3], kd[l][h], "pinned")
                counts["C"] += 3
    for row in (C["clamped"]["rows"] or []):
        if len(row) >= 4 and row[0].startswith("Push on the margin"):
            ka = ex.nested(ma, "head_attr_clamped"); kb = ex.nested(mb, "head_attr_clamped")
            kc = ex.nested(mp, "d_head_attr_clamped")
            l, h = 12, 3
            cmp("C clamped DLA A", row[1], ka[l][h], "clamped url %s" % C["clamped"]["url"])
            cmp("C clamped DLA B", row[2], kb[l][h], "clamped")
            cmp("C clamped DLA d", row[3], kc[l][h], "clamped")
            counts["C"] += 3
    report.append((tag, "C", counts["C"], (C["hovers"][0]["rows"] if C["hovers"] else None)))

    # ---------------- tab B
    for qty in ["resid", "mlp", "attn"]:
        key = "B_" + qty
        seen = 0
        arrays = {"resid": ("resid_norm", "d_resid_norm"), "mlp": ("mlp_norm", "d_mlp_norm"), "attn": ("attn_norm", "d_attn_norm")}[qty]
        Aarr = [ex.nested(ma, arrays[0]), ex.nested(mb, arrays[0])]
        Parr = ex.nested(mp, arrays[1])
        for ob in tabs[key]:
            text = ob["text"]
            mt = re.search(r"token (\d+):", text)
            if not mt:
                continue
            t = int(mt.group(1))
            if qty == "resid":
                ml = re.search(r"entering layer (\d+)", text)
                if ml:
                    l = int(ml.group(1))
                elif "after the last layer" in text:
                    l = ma["model"]["n_layers"]
                else:
                    continue
            else:
                ml = re.search(r"layer (\d+)", text)
                if not ml:
                    continue
                l = int(ml.group(1))
            rows = ob["rows"] or []
            for row in rows:
                if len(row) < 4:
                    continue
                lab = row[0]
                if lab.startswith("Running-state size") or lab.startswith("Write size"):
                    cmp("B %s A" % qty, row[1], Aarr[0][l][t], "l=%d t=%d" % (l, t))
                    cmp("B %s B" % qty, row[2], Aarr[1][l][t], "l=%d t=%d" % (l, t))
                    cmp("B %s delta" % qty, row[3], Parr[l][t], "l=%d t=%d (delta map)" % (l, t))
                    seen += 3
            # the change map: its own canvas cell must use the same pair array
        counts["B"] = seen
        report.append((tag, "B_" + qty, seen, (tabs[key][0]["text"] if tabs[key] else None)))

    # ---------------- tab A
    for view in ["side", "delta"]:
        key = "A_" + view
        seen = 0
        for ob in tabs[key]["obs"]:
            tip = ob["tip"]
            mh = re.search(r"Head · layer (\d+) · head (\d+) · token (\d+)", tip)
            if not mh:
                continue
            l, h, t = int(mh.group(1)), int(mh.group(2)), int(mh.group(3))
            for mm in re.finditer(r"— ([^\n]+)\n(?:  ([^:\n]+): ([^\n]+))?", tip):
                pass
            # panel rows: "— label" then "  key: value"
            parts = re.split(r"\n— ", tip)
            for part in parts[1:]:
                label = part.split("\n")[0]
                rows = re.findall(r"^  ([^:\n]+): (.+)$", part, re.M)
                for k, v in rows:
                    if k.strip() == "||o^l_{h,t}||":
                        cmp("A %s head_norm" % view, v.split()[0], na[l][h][t] if False else ex.nested(ma, "head_norm")[l][h][t], "hover l=%d h=%d t=%d" % (l, h, t))
                        seen += 1
                    elif k.strip() == "DLA to margin":
                        cmp("A %s DLA" % view, v.split()[0], ha[l][h], "hover l=%d h=%d t=%d (t=ro?)" % (l, h, t))
                        seen += 1
                    elif k.strip() == "||o_B - o_A||":
                        cmp("A %s d_head_norm" % view, v.split()[0], kdn[l][h][t], "hover l=%d h=%d t=%d" % (l, h, t))
                        seen += 1
                    elif k.strip() == "||o_A||":
                        cmp("A %s head_norm(A)" % view, v.split()[0], ex.nested(ma, "head_norm")[l][h][t], "delta panel")
                        seen += 1
                    elif k.strip() == "||o_B||":
                        cmp("A %s head_norm(B)" % view, v.split()[0], ex.nested(mb, "head_norm")[l][h][t], "delta panel")
                        seen += 1
        counts["A"] += seen
        # the "largest changes" list binds d_head_norm at the readout position
        big = tabs[key]["big"]
        if big:
            ro = ma["readout"]["position"]
            for label, val in zip(big["rows"], big["nums"]):
                mm = re.match(r"layer (\d+) · head (\d+)", label)
                if mm:
                    cmp("A %s bigList d_head_norm" % view, val, kdn[int(mm.group(1))][int(mm.group(2))][ro], label)
                    counts["A"] += 1
        report.append((tag, key, seen, tabs[key]["big"] and tabs[key]["big"]["rows"][:2]))

print("=== checks run ===")
for r in report:
    print("  %-42s %-9s %4d  %s" % (r[0], r[1], r[2], ""))
print("\nTOTAL number comparisons:", checks)
print("FAILURES:", len(fails))
for f in fails:
    print("  ", json.dumps(f))
print("\nconsole errors seen by the browser during the scan:", len(OBS.get("console_errors", [])))
for e in OBS.get("console_errors", [])[:10]:
    print("  ", e)
