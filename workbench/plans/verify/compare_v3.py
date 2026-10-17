"""Independent comparator for the v3 port (verifier t_9799f1a1).

Reads $TMPDIR/pp/v3obs.json (raw strings the browser showed) and compares every
number against `reader.py`, my own manifest-offset reader over workbench/exports.
Nothing here imports the viewer or sca2_workbench.
"""
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reader import Export

ROOT = "/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.worktrees/adapter-brain-vizualization/workbench/exports"
OBS = json.load(open(os.environ.get("V3OBS", "/private/var/folders/x4/vhxvs_xj31z02hfv4nj85__h0000gn/T/pp/v3obs.json")))
ex = Export(ROOT)

fails = []
checks = 0
per = {}


def ok(tag, name, shown, mine, where=""):
    global checks
    checks += 1
    per.setdefault(tag, [0, 0])
    per[tag][0] += 1
    r = close(shown, mine)
    if r is None:
        per[tag][1] += 1
        fails.append({"tag": tag, "check": name, "where": where, "shown": shown, "mine": mine, "why": "unparsable"})
        return False
    good, d = r
    if not good:
        per[tag][1] += 1
        fails.append({"tag": tag, "check": name, "where": where, "shown": shown, "mine": mine,
                      "shown_v": d["shown"], "tol": d["tol"]})
        return False
    return True


def num(s):
    s = s.strip().replace("\u2212", "-")
    m = re.match(r"^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", s)
    return float(m.group(1)) if m else None


def oks(tag, name, shown, mine, where=""):
    """Exact string comparison (labels, flags)."""
    global checks
    checks += 1
    per.setdefault(tag, [0, 0])
    per[tag][0] += 1
    if str(shown) != str(mine):
        per[tag][1] += 1
        fails.append({"tag": tag, "check": name, "where": where, "shown": shown, "mine": mine, "why": "string mismatch"})
        return False
    return True


def sig(s):
    s = s.strip().replace("\u2212", "-").lstrip("+-")
    if "e" in s.lower():
        s = re.split("[eE]", s)[0]
    s = s.replace(".", "").lstrip("0")
    return max(1, len(s.rstrip("0")) if s.rstrip("0") else len(s))


def close(shown, mine):
    """True when `shown` (as displayed) equals `mine` at the precision it prints."""
    v = num(shown)
    if v is None or mine is None:
        return None
    p = sig(shown)
    mag = abs(mine)
    if mag == 0:
        return abs(v) < 5e-13, {"shown": v, "mine": mine, "tol": 0}
    tol = 0.5 * (10 ** (math.floor(math.log10(mag)) - (p - 1)))
    return abs(v - mine) <= tol * (1 + 1e-9) + 1e-15, {"shown": v, "mine": mine, "tol": tol, "p": p}


def js_fmt(v, p=4):
    if v == 0:
        return "0"
    a = abs(v)
    return ("%.*e" % (p - 1, v)) if (a >= 1e4 or a < 1e-3) else ("%.*g" % (p, v))


def manifest(model, item):
    return ex.manifest("run__%s__%s.json" % (model, item))


def pairman(a, b, item):
    return ex.manifest("pair__%s__%s__%s.json" % (a, b, item))


A, B, ITEM = "smol_inst", "smol_inst_usa_e3", "wvs_Q81"
ma, mb, mp = manifest(A, ITEM), manifest(B, ITEM), pairman(A, B, ITEM)
ha, hb = ex.nested(ma, "head_attr"), ex.nested(mb, "head_attr")
na, nb = ex.nested(ma, "head_norm"), ex.nested(mb, "head_norm")
mna, mnb = ex.nested(ma, "mlp_attr"), ex.nested(mb, "mlp_attr")
kdn = ex.nested(mp, "d_head_norm")
kd = ex.nested(mp, "d_head_attr")
kdm = ex.nested(mp, "d_mlp_attr")
L = ma["model"]["n_layers"]
H = ma["model"]["n_heads"]
T = len(ma["tokens"])
RO = ma["readout"]["position"]
ea = ma["readout"]["embed_attr"]
eb = mb["readout"]["embed_attr"]
dem = mp["d_embed_attr"]
dmargin = mp["d_margin"]
margin_a = ma["readout"]["margin"]
margin_b = mb["readout"]["margin"]
print("reader: L=%d H=%d T=%d ro=%d | A margin %.6f  B margin %.6f  d_margin %.6f" % (L, H, T, RO, margin_a, margin_b, dmargin))

# ---------------------------------------------------------------- check 1a: tab C ladder
c = OBS["tabs"]["c"]
oks("C-face", "default face is B - A", c["face_default"], "d")
for hv in c["hovers"]:
    l, h = hv["l"], hv["h"]
    tip = hv["tip"]
    head = re.match(r"^(head (\d+) · layer (\d+)|MLP · layer (\d+))", tip)
    if not head:
        fails.append({"tag": "C-hover", "check": "tooltip shape", "where": tip, "why": "unparsable"})
        continue
    body = tip.split("\n")[1]
    dline = tip.split("\n")[2]
    m = re.match(r"A\s+(\S+)\s+B\s+(\S+)", body)
    m2 = re.match(r"B \u2212 A\s+(\S+)", dline)
    tag = "head" if head.group(2) else "MLP"
    va = ha[l][h] if tag == "head" else mna[l]
    vb = hb[l][h] if tag == "head" else mnb[l]
    vd = kd[l][h] if tag == "head" else kdm[l]
    ok("C-hover", "ladder %s A l=%d h=%d" % (tag, l, h), m.group(1), va, tip)
    ok("C-hover", "ladder %s B l=%d h=%d" % (tag, l, h), m.group(2), vb, tip)
    ok("C-hover", "ladder %s B-A l=%d h=%d" % (tag, l, h), m2.group(1), vd, tip)
    if "(pair export)" not in dline:
        fails.append({"tag": "C-hover", "check": "B-A face does not cite the pair export", "where": tip})


def sums_of(face):
    if face == "a":
        s = ea + sum(ha[l][h] for l in range(L) for h in range(H)) + sum(mna[l] for l in range(L))
        return s, margin_a
    if face == "b":
        s = eb + sum(hb[l][h] for l in range(L) for h in range(H)) + sum(mnb[l] for l in range(L))
        return s, margin_b
    s = dem + sum(kd[l][h] for l in range(L) for h in range(H)) + sum(kdm[l] for l in range(L))
    return s, dmargin


for face, key in [("d", None), ("a", "face_a"), ("b", "face_b")]:
    src = c["lfoot"] if key is None else c[key]["lfoot"]
    m = re.findall(r'class="num">([^<]+)</span>', src)
    s, t = sums_of(face)
    ok("C-resum", "face %s re-sum line" % face, m[0], s, src[:200])
    ok("C-resum", "face %s target" % face, m[1], t, src[:200])
    # the re-sum line is a pass mark on the untainted page
    if "sumline ok" not in src or "\u2713 cells + embedding" not in src:
        fails.append({"tag": "C-resum", "check": "re-sum line missing/red on a clean page", "where": src[:200]})

# sign convention + rings legend visible at rest
if "orange: toward" not in c["lfoot"] or "blue: toward" not in c["lfoot"]:
    fails.append({"tag": "C-sign", "check": "sign convention not in the ladder footer", "where": c["lfoot"][:200]})
else:
    checks += 1
if "gold ring: 5 largest B \u2212 A" not in c["lfoot"]:
    fails.append({"tag": "C-rings", "check": "ring legend missing", "where": c["lfoot"][:200]})
else:
    checks += 1

def tbl(html):
    """Rows of cells from an A|B|Change table in the drawer HTML."""
    out = []
    for tr in re.findall(r"<tr>(.*?)</tr>", html or "", re.S):
        cells = [re.sub(r"<[^>]+>", "", td).strip() for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if cells:
            out.append(cells)
    return out


def chg(cell):
    """The number in a Change cell (strips the ‖Δ‖ prefix)."""
    n = re.findall(r"[\u2212+\-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?", cell.replace("e-", "e-"))
    return n[-1] if n else cell


# the pinned drawer
dr = c["pinned"]
oks("C-drawer", "pin writes sel= into the URL", "yes" if "sel=17,3" in dr["url"] else "no", "yes", dr["url"])
dtxt = dr["drawerText"]
rows = {r[0]: r for r in tbl(dr["drawerHTML"]) if len(r) >= 4}
tma = ex.nested(ma, "attn_topk_mass")[17][3][RO]
tmb = ex.nested(mb, "attn_topk_mass")[17][3][RO]
expect = [("Write size \u2016o\u2016", na[17][3][RO], nb[17][3][RO], kdn[17][3][RO]),
          ("Push (DLA)", ha[17][3], hb[17][3], kd[17][3]),
          ("Top-16 coverage", tma, tmb, tmb - tma)]
for label, va, vb, vd in expect:
    row = rows.get(label)
    if not row:
        fails.append({"tag": "C-drawer", "check": "drawer row missing: " + label, "where": dtxt[:300]})
        continue
    ok("C-drawer", "drawer %s A" % label, row[1], va, dtxt[:200])
    ok("C-drawer", "drawer %s B" % label, row[2], vb, dtxt[:200])
    ok("C-drawer", "drawer %s change" % label, chg(row[3]), vd, dtxt[:200])
if len(rows) != 3:
    fails.append({"tag": "C-drawer", "check": "ladder drawer row count", "where": "got %d" % len(rows)})
if "sel=17,3" not in dr["url"] or dr["drawerHidden"]:
    fails.append({"tag": "C-drawer", "check": "drawer not open after a click", "where": dr["url"]})

# ---------------------------------------------------------------- check 1a-bis: the drawn cell colours
# The ladder's marks are the cells. Re-derive each fill from my own reader: diverging(v, vmax) =
# mix("#3a3a3e", blue/orange, sqrt(min(1, |v|/vmax))), vmax over the drawn grid (embedding included).
NEUTRAL = (0x3a, 0x3a, 0x3e)
BLUE = (0x6b, 0x9b, 0xff)
ORANGE = (0xff, 0x9a, 0x3c)


def val_face(face, l, h):
    if face == "a":
        return ea if l < 0 else (mna[l] if h < 0 else ha[l][h])
    if face == "b":
        return eb if l < 0 else (mnb[l] if h < 0 else hb[l][h])
    return dem if l < 0 else (kdm[l] if h < 0 else kd[l][h])


def expect_fill(face, l, h, vmax):
    v = val_face(face, l, h)
    f = math.sqrt(min(1.0, abs(v) / (vmax or 1)))
    tgt = BLUE if v >= 0 else ORANGE
    return tuple(int(math.floor(a + (b - a) * f + 0.5)) for a, b in zip(NEUTRAL, tgt))


for face, key in [("d", "cells_d"), ("a", None), ("b", None)]:
    cells = c["cells_d"] if key else c["face_" + face]["cells"]
    vmax = 0.0
    for l in range(-1, L):
        for h in (-1,) if l < 0 else range(-1, H):
            vmax = max(vmax, abs(val_face(face, l, h)))
    bad = 0
    for cell in cells:
        l, h = cell["l"], cell["h"]
        hh = -1 if h == -2 else h
        m = re.match(r"rgb\((\d+),(\d+),(\d+)\)", cell["fill"] or "")
        if not m:
            fails.append({"tag": "C-fill", "check": "cell fill unparsable", "where": json.dumps(cell)})
            continue
        got = tuple(int(x) for x in m.groups())
        exp = expect_fill(face, l, hh, vmax)
        checks += 1
        per.setdefault("C-fill", [0, 0])
        per["C-fill"][0] += 1
        if any(abs(a - b) > 1 for a, b in zip(got, exp)):
            bad += 1
            per["C-fill"][1] += 1
            if bad <= 5:
                fails.append({"tag": "C-fill", "check": "cell colour (face %s) l=%d h=%d" % (face, l, h), "shown": got, "mine": exp})
    print("  ladder fills face %s: %d cells, %d mismatched (vmax %.4f)" % (face, len(cells), bad, vmax))

# clamped run: the frame says so
oks("C-clamp", "frame chip visible when clamp=1", "clamped run" if not c["clamp"]["chipHidden"] else "hidden", "clamped run")
oks("C-clamp", "clamp chip off at rest", c["clamp_off"]["chipHidden"], True)
mc = re.findall(r'class="num">([^<]+)</span>', c["clamp"]["lfoot"])
ka = ex.nested(ma, "head_attr_clamped")
kb = ex.nested(mb, "head_attr_clamped")
km = ex.nested(mp, "d_head_attr_clamped")
kmn = ex.nested(mp, "d_mlp_attr_clamped")
s_c = mp["d_embed_attr_clamped"] + sum(km[l][h] for l in range(L) for h in range(H)) + sum(kmn[l] for l in range(L))
ok("C-clamp", "clamped re-sum", mc[0], s_c, c["clamp"]["lfoot"][:200])
ok("C-clamp", "clamped target (d_margin_clamped)", mc[1], mp["d_margin_clamped"], c["clamp"]["lfoot"][:200])

# ---------------------------------------------------------------- check 1b: tab B matrix
bb = OBS["tabs"]["b"]
oks("B-qty", "matrix default quantity is attention writes", bb["qty_on"], "attn")
oks("B-face", "matrix default face is B - A", bb["face_on"], "d")


def mat_rows(qty):
    src = {"attn": ("attn_norm", "d_attn_norm"), "resid": ("resid_norm", "d_resid_norm"), "mlp": ("mlp_norm", "d_mlp_norm")}[qty]
    return ex.nested(ma, src[0]), ex.nested(mb, src[0]), ex.nested(mp, src[1])


seen = {}
for qty, key in [("attn", "hovers"), ("resid", "qty_resid"), ("mlp", "qty_mlp")]:
    ArrA, ArrB, PArr = mat_rows(qty)
    hvs = bb[key] if key == "hovers" else bb[key]["hovers"]
    n = 0
    for hv in hvs:
        tip = hv["tip"]
        head = re.match(r"^(?:layer (\d+)|state after layer (\d+)) · token (\d+)", tip)
        if not head:
            continue
        if head.group(1) is not None:
            l = int(head.group(1))
        else:
            l = int(head.group(2)) + 1
        t = int(head.group(3))
        if l >= len(ArrA) or t >= T:
            fails.append({"tag": "B-hover", "check": "matrix tooltip names an out-of-range cell", "where": tip})
            continue
        mm = re.search(r"A\s+(\S+)\s+B\s+(\S+)", tip)
        md = re.search(r"\u2016B \u2212 A\u2016\s+(\S+)", tip)
        if not (mm and md):
            fails.append({"tag": "B-hover", "check": "matrix tooltip unparsable", "where": tip})
            continue
        ok("B-hover", "%s A l=%d t=%d" % (qty, l, t), mm.group(1), ArrA[l][t], tip)
        ok("B-hover", "%s B l=%d t=%d" % (qty, l, t), mm.group(2), ArrB[l][t], tip)
        ok("B-hover", "%s d l=%d t=%d" % (qty, l, t), md.group(1), PArr[l][t], tip)
        seen.setdefault(qty, set()).add((l, t))
        n += 1
    per.setdefault("B-hover-" + qty, [n, 0])
    print("  matrix %-5s tooltips parsed: %d  distinct cells: %d" % (qty, n, len(seen.get(qty, ()))))

# matrix footer: clip value (p99) and max, from the drawn tensor
for qty, fkey in [("attn", "bfoot"), ("resid", "qty_resid"), ("mlp", "qty_mlp")]:
    src = {"attn": ("attn_norm", "d_attn_norm"), "resid": ("resid_norm", "d_resid_norm"), "mlp": ("mlp_norm", "d_mlp_norm")}[qty]
    foot = bb["bfoot"] if fkey == "bfoot" else bb[fkey]["bfoot"]
    flat = ex.nested(mp, src[1]) if qty != "x" else None
    vals = sorted(ex.read(mp, src[1])[0]) if qty != "x" else None
    p99 = vals[int(len(vals) * 0.99)]
    mx = vals[-1]
    nums = re.findall(r'class="num">([^<]+)</span>', foot)
    ok("B-foot", "%s footer clip p99" % qty, nums[0], p99, foot[:200])
    ok("B-foot", "%s footer max" % qty, nums[1], mx, foot[:200])
    if "99th percentile" not in foot or "clipped" not in foot:
        fails.append({"tag": "B-foot", "check": "%s footer does not state the clip" % qty, "where": foot[:200]})

# matrix drawer
bdr = bb["pinned"]
print("  matrix pin url:", bdr["url"], "drawer open:", not bdr["drawerHidden"])
brows = {r[0]: r for r in tbl(bdr["drawerHTML"]) if len(r) >= 4}
ml = re.search(r"pin=(\d+),(\d+)", bdr["url"])
l, t = (int(ml.group(1)), int(ml.group(2))) if ml else (0, 0)
an = ex.nested(ma, "attn_norm")
bn = ex.nested(mb, "attn_norm")
dn = ex.nested(mp, "d_attn_norm")
if "Attention write \u2016a\u2016" in brows:
    row = brows["Attention write \u2016a\u2016"]
    ok("B-drawer", "drawer attn write A l=%d t=%d" % (l, t), row[1], an[l][t], bdr["drawerText"][:200])
    ok("B-drawer", "drawer attn write B", row[2], bn[l][t], bdr["drawerText"][:200])
    ok("B-drawer", "drawer attn write d", chg(row[3]), dn[l][t], bdr["drawerText"][:200])
    # the nine per-head d_head_norm rows
    rows = re.findall(r"<div class=\"hrow\"><span>h(\d)</span>.*?<span class=\"num\">([\d.e+-]+)</span>", bdr["drawerHTML"], re.S)
    dhn = ex.nested(mp, "d_head_norm")
    for h, v in rows:
        ok("B-drawer", "drawer head h%s d_head_norm" % h, v, dhn[l][int(h)][t], bdr["drawerText"][:200])
    if len(rows) != 9:
        fails.append({"tag": "B-drawer", "check": "expected 9 head rows in the matrix drawer", "where": "got %d" % len(rows)})
else:
    fails.append({"tag": "B-drawer", "check": "matrix drawer attention row unparsable", "where": bdr["drawerText"][:300]})

# ---------------------------------------------------------------- check 1c: tab A object
for tag in ["a_delta", "a_side"]:
    o = OBS["tabs"][tag]
    dhn = ex.nested(mp, "d_head_norm")
    dmn = ex.nested(mp, "d_mlp_norm")
    drn = ex.nested(mp, "d_resid_norm")
    hna = ex.nested(ma, "head_norm")
    hnb = ex.nested(mb, "head_norm")
    nparsed = 0
    for hv in o["hovers"]:
        tip = hv["tip"]
        head = re.match(r"^(Head|MLP|State) · layer (\d+)(?: · head (\d+))? · token (\d+)", tip)
        if not head:
            fails.append({"tag": "A-hover-" + tag, "check": "3D tooltip unparsable", "where": tip[:200]})
            continue
        kind, l, h, t = head.group(1), int(head.group(2)), head.group(3), int(head.group(4))
        h = int(h) if h is not None else None
        panels = re.split(r"\n— ", tip)[1:]
        for pan in panels:
            label = pan.split("\n")[0]
            delta = label.startswith("\u2016B \u2212 A\u2016")
            for k, v in re.findall(r"^  ([^:\n]+): ([^\n]*)", pan, re.M):
                v0 = v.split()[0] if v.split() else v
                if k == "||o^l_{h,t}||":
                    which = "A" if label.startswith("A ") else ("B" if label.startswith("B ") else "?")
                    mine = hna[l][h][t] if which == "A" else hnb[l][h][t]
                    ok("A-hover-" + tag, "%s head_norm l=%d h=%d t=%d" % (which, l, h, t), v0, mine, tip[:160]); nparsed += 1
                elif k == "DLA to margin":
                    ok("A-hover-" + tag, "A head_attr l=%d h=%d" % (l, h), v0, ha[l][h], tip[:160]); nparsed += 1
                elif k == "||o_B - o_A||":
                    ok("A-hover-" + tag, "d_head_norm l=%d h=%d t=%d" % (l, h, t), v0, dhn[l][h][t], tip[:160]); nparsed += 1
                elif k == "||o_A||":
                    ok("A-hover-" + tag, "head_norm A l=%d h=%d t=%d" % (l, h, t), v0, hna[l][h][t], tip[:160]); nparsed += 1
                elif k == "||o_B||":
                    ok("A-hover-" + tag, "head_norm B l=%d h=%d t=%d" % (l, h, t), v0, hnb[l][h][t], tip[:160]); nparsed += 1
                elif k == "||m_B - m_A||":
                    ok("A-hover-" + tag, "d_mlp_norm l=%d t=%d" % (l, t), v0, dmn[l][t], tip[:160]); nparsed += 1
                elif k == "||h_B - h_A||":
                    ok("A-hover-" + tag, "d_resid_norm l=%d t=%d" % (l, t), v0, drn[l][t], tip[:160]); nparsed += 1
                elif k == "top keys A[q,k]" and h is not None and kind == "Head":
                    run = ma if label.startswith("A ") else (mb if label.startswith("B ") else None)
                    if run is not None:
                        w = re.match(r"(\S+)\s*->\s*t=(\d+)", v)
                        idx = ex.nested(run, "attn_topk_idx")[l][h][t]
                        val = ex.nested(run, "attn_topk_val")[l][h][t]
                        ok("A-hover-" + tag, "top-16 weight l=%d h=%d t=%d" % (l, h, t), w.group(1), val[0], tip[:160]); nparsed += 1
                        oks("A-hover-" + tag, "top-16 key index l=%d h=%d t=%d" % (l, h, t), w.group(2), idx[0], tip[:160]); nparsed += 1
    per.setdefault("A-hover-" + tag, [nparsed, 0])
    print("  object %-7s numbers parsed from tooltips: %d  (hovers: %d)" % (tag, nparsed, len(o["hovers"])))
    # view labels
    if tag == "a_delta":
        if not o["labels"][0].startswith("A ·") or not o["labels"][1].startswith("\u2016B \u2212 A\u2016"):
            fails.append({"tag": "A-view", "check": "default view is not A | ||B-A||", "where": str(o["labels"])})
        else:
            checks += 1
        if o["view_on"] != "delta":
            fails.append({"tag": "A-view", "check": "default view button", "where": str(o["view_on"])})
        else:
            checks += 1
        if "dashed: 0 = even odds" not in o["inset"] or 'class="zero"' not in o["inset"]:
            fails.append({"tag": "A-inset", "check": "inset has no zero line", "where": o["inset"][:200]})
        else:
            checks += 1
    # pinned drawer
    if "pinned" in o:
        pdr = o["pinned"]
        m = re.search(r"Head (\d+) · layer (\d+)", pdr["drawerText"])
        if m:
            h, l = int(m.group(1)), int(m.group(2))
            mt = re.search(r"token (\d+)", pdr["drawerText"])
            t = int(mt.group(1)) if mt else RO
            arows = {r[0]: r for r in tbl(pdr["drawerHTML"]) if len(r) >= 4}
            row = arows.get("Write size \u2016o\u2016")
            if row:
                ok("A-drawer", "object drawer Write A l=%d h=%d t=%d" % (l, h, t), row[1], hna[l][h][t], pdr["drawerText"][:200])
                ok("A-drawer", "object drawer Write B", row[2], hnb[l][h][t], pdr["drawerText"][:200])
                ok("A-drawer", "object drawer d_head_norm", chg(row[3]), dhn[l][h][t], pdr["drawerText"][:200])
            else:
                fails.append({"tag": "A-drawer", "check": "object drawer unparsable", "where": pdr["drawerText"][:300]})

# ---------------------------------------------------------------- check 2: never-hide
for tab, f in OBS["fail"].items():
    oks("fail-" + tab, "banner present and visible", "yes" if (f["banner"] and f["bannerVisible"] and f["bannerVisible"]["w"] > 100) else "no", "yes")
    oks("fail-" + tab, "banner says simulated", "yes" if f["banner"] and "simulated" in f["banner"] else "no", "yes")
    oks("fail-" + tab, "banner names the check and its value/threshold",
        "yes" if (f["banner"] and re.search(r"dla_gap = [\d.]+ \u2265 [\d.]+", f["banner"])) else "no", "yes")
    gre = [h for h in f["checks"] if "\u2713" in h["text"]]
    per.setdefault("fail-green-" + tab, [0, 0])
    if gre:
        per["fail-green-" + tab][1] += 1
        fails.append({"tag": "fail-" + tab, "check": "a green check mark is still visible", "where": json.dumps(gre)[:400]})
    else:
        per["fail-green-" + tab][0] += 1
        checks += 1
    if not any("\u2717" in h["text"] for h in f["checks"]):
        fails.append({"tag": "fail-" + tab, "check": "no red mark visible at all", "where": json.dumps(f["checks"])[:300]})
    else:
        checks += 1
    print("  fail[%s]: banner=%r glyph=%r visible-marks=%d" % (tab, (f["banner"] or "")[:90], f["glyph"], len(f["checks"])))

# ---------------------------------------------------------------- check 4: drawer overlap
# Authoritative measurement: $TMPDIR/pp/overlap.json (probe_overlap.mjs, 2.5 s settle after the
# pin). The snapshot inside v3obs.json is taken 300 ms after the click and catches the object tab
# mid-reflow (stale #sceneB box), so it is not used here.
OVER = json.load(open(os.environ.get("V3OVERLAP", "/private/var/folders/x4/vhxvs_xj31z02hfv4nj85__h0000gn/T/pp/overlap.json")))
for rec in OVER:
    tag = rec["label"].split()[0]
    bad = rec["after"]["overlaps"]
    names = [o["name"] for o in rec["after"]["objs"]]
    oks("overlap-" + tag, "drawer overlaps nothing (%s)" % rec["label"], "yes" if not bad else "no", "yes")
    oks("overlap-" + tag, "every at-rest object still visible (%s)" % rec["label"], "yes" if "drawer" in names and len(names) >= 7 else "no", "yes")
    if rec["before"]["chartW"] is not None:
        oks("overlap-" + tag, "margin chart width unchanged (%s)" % rec["label"], rec["after"]["chartW"], rec["before"]["chartW"])
    print("  overlap [%s]: %s chartW %s -> %s" % (rec["label"], json.dumps(bad), rec["before"]["chartW"], rec["after"]["chartW"]))
for tag, o in [("c", OBS["tabs"]["c"]), ("b", OBS["tabs"]["b"]), ("a", OBS["tabs"]["a_delta"])]:
    ov = o.get("pin_overlap") or []
    bad = [x for x in ov if x.get("area", 0) > 0]
    print("  overlap snapshot [%s] (300 ms after the click, informational): %s" % (tag, json.dumps([x["sel"] for x in bad])))
    if bad:
        print("    (transient only; the settled measurement above is the one that counts)")

# ---------------------------------------------------------------- summary
print("\n=== checks: %d   failures: %d ===" % (checks, len(fails)))
for t, (n, bad) in sorted(per.items()):
    print("  %-24s %4d checks  %d failed" % (t, n, bad))
for f in fails:
    print("  FAIL", json.dumps(f))
json.dump({"checks": checks, "fails": fails, "per": per}, open(os.environ.get("V3OUT", "/private/var/folders/x4/vhxvs_xj31z02hfv4nj85__h0000gn/T/pp/v3cmp.json"), "w"), indent=1)
