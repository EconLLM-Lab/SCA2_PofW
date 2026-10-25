#!/usr/bin/env python3
"""RP2 comparison: re-run human-criterion results vs the tracked ones, then the rebuilt table rows vs the tracked table.

Card CP26-RP2 (t_536cff76). Same rules as RP1's `compare_results.py` (whose `Diff` and `read_any` are reused):
ints/bools/strings exact; floats exact for seeded bootstraps and permutations re-run with the recorded seed,
`abs <= 1e-9` for the deterministic files (wave-6/7 ceiling, probe selections, item tables).

    env -u PYTHONPATH .venv/bin/python planning/checkpoint_2026-10-26/replication/compare_results_human.py [--show-size] [--self-test]

Inputs: the mirror tree `.replication_2026-10-25/human/tree/` written by the commands in MANIFEST_human.md.
Part 1  every re-run file against the tracked file of the same name (all fields), plus byte identity.
Part 2  the tree's `paper_b/build_numbers_table.py` functions (`screen_rows`, `per_dimension_rows`, `comparator_rows`,
        `readout_rows`, `c9_human_agreement_rows`, `c9_tvd_rows`) run on the re-run files; every row they emit against
        the tracked 562-row table, row by row and in the same order. The scope is defined from the tracked table:
        the rows whose `output_file` is one of the human-criterion result files (coverage is checked both ways).

Output: counts per file and family, then `0 mismatches` or the mismatching keys (claim_id or file:field), never rows.
`--show-size` adds the absolute difference. `--self-test` changes one value of a copy and requires the comparator to
report it (a comparator that swallows a mismatch is the failure this guards against). Nothing tracked is written.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import compare_results as C  # noqa: E402  (RP1: Diff, read_any, TOL)

REP = ROOT / ".replication_2026-10-25/human"
RES = C.RES
TABLE = C.TABLE
TOL = C.TOL

# result file (relative to results/, or to the repo root when it starts with paper_b/) -> exact floats?
FILES = {
    "paper_b/heldout/screen_result.json": True,
    "heldout_analysis.json": True,
    "heldout_items.csv": False,
    "heldout_per_dimension.json": True,
    "signprompt_selection_20261017.csv": False,
    "ceiling_heldout/ceiling_items.csv": False,
    "ceiling_heldout/ceiling_surfaces.csv": False,
    "ceiling_heldout/ceiling_sanity.json": False,
    "ceiling_heldout/ts_crosswalk.json": False,
    "ceiling_items.csv": False,
    "ceiling_surfaces.csv": False,
    "ceiling_sanity.json": False,
    "ts_crosswalk.json": False,
    "robustness/selection_heldout_reverse.csv": False,
    "robustness/selection_heldout_para_a.csv": False,
    "robustness/selection_heldout_para_b.csv": False,
    "c9/c9_human_agreement.json": True,
    "c9/c9_human_agreement.csv": True,
    "c9/c9_tvd.json": True,
    "c9/c9_tvd.csv": True,
}
# Tracked table rows are in scope when their output_file ends with one of these.
SCOPE_FILES = ("screen_result.json", "heldout_analysis.json", "heldout_per_dimension.json",
               "selection_heldout_reverse.csv", "selection_heldout_para_a.csv", "selection_heldout_para_b.csv",
               "c9_human_agreement.json", "c9_tvd.json")
FAMILIES = ("SCR_", "PD_", "CMP_", "SP_", "RO_", "C9_a_", "C9_b_", "C9_c_", "C9_d_", "C9_e_", "C9_f_", "C9_TVD_")
# Rows built from the deterministic ceiling or a deterministic Pearson (no seed): abs <= 1e-9; all others exact.
TOL_ROWS = ("SCR_ceiling_", "SCR_A_over_ceiling", "SCR_one_third_ceiling", "RO_")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def part1(rtree: Path) -> list:
    bad_all, rows = [], []
    for rel, exact in FILES.items():
        base = ROOT if rel.startswith("paper_b/") else None
        new = rtree / rel if base else rtree / RES / rel
        old = ROOT / rel if base else ROOT / RES / rel
        if not new.is_file():
            rows.append((rel, 0, 1, math.nan, False)); bad_all.append((f"{rel} (not regenerated)", math.nan)); continue
        d = C.Diff(0.0 if exact else TOL)
        d.cmp(C.read_any(new), C.read_any(old), rel)
        rows.append((rel, d.n, len(d.bad), d.maxd, sha(new) == sha(old))); bad_all += d.bad
    print("Part 1: re-run files vs tracked files")
    for rel, n, m, mx, same in rows:
        print(f"  {rel:45s} fields {n:6d}  mismatches {m:3d}  max|diff| {mx:.3g}  byte-identical {same}")
    return bad_all


def load_tree_builder(rtree: Path):
    path = rtree / "paper_b/build_numbers_table.py"
    spec = importlib.util.spec_from_file_location("rp2_tree_builder", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert Path(mod.ROOT).resolve() == rtree.resolve(), "builder is not reading the mirror tree"
    return mod


def rebuild(rtree: Path) -> pd.DataFrame:
    B = load_tree_builder(rtree)
    freeze = json.loads((rtree / "paper_b/heldout/FREEZE.json").read_text())
    t = B.Table()
    B.screen_rows(t, freeze)
    B.per_dimension_rows(t, freeze)
    B.comparator_rows(t, freeze)
    B.readout_rows(t, freeze, rtree / RES / "robustness")
    B.c9_human_agreement_rows(t)
    B.c9_tvd_rows(t)
    return pd.DataFrame(t.rows, columns=B.COLUMNS).astype(str)


def compare_rows(tr: pd.DataFrame, new: pd.DataFrame, label: str = "") -> tuple[list, dict]:
    """tr: tracked rows in scope (table order); new: rebuilt rows. Keys, order, every column."""
    bad = []
    if list(tr.claim_id) != list(new.claim_id):
        for k in sorted(set(tr.claim_id) ^ set(new.claim_id)):
            bad.append((f"{k} (row on one side only)", math.nan))
        if set(tr.claim_id) == set(new.claim_id):
            bad.append(("row order differs", math.nan))
    ti, ni = tr.set_index("claim_id"), new.set_index("claim_id")
    fam = {p: [0, 0, 0.0] for p in FAMILIES}
    for k in [k for k in ti.index if k in ni.index]:
        p = next(p for p in FAMILIES if k.startswith(p))
        fam[p][0] += 1
        a, b = ti.loc[k], ni.loc[k]
        for col in ("sentence_use", "statistic", "n", "surface_label", "run_id", "producing_script", "output_file"):
            if a[col] != b[col]:
                bad.append((f"{k}:{col}", math.nan)); fam[p][1] += 1
        tol = TOL if k.startswith(TOL_ROWS) else 0.0
        for col in ("value", "ci_low", "ci_high"):
            x, y = a[col], b[col]
            if x == y:
                continue
            try:
                d = abs(float(x) - float(y))
            except ValueError:
                bad.append((f"{k}:{col}", math.nan)); fam[p][1] += 1; continue
            fam[p][2] = max(fam[p][2], d)
            integer_valued = "." not in x and "e" not in x.lower() and "." not in y
            if not d <= (0.0 if integer_valued else tol):
                bad.append((f"{k}:{col}", d)); fam[p][1] += 1
    return bad, fam


def part2(rtree: Path) -> tuple[list, pd.DataFrame, pd.DataFrame]:
    full = pd.read_csv(ROOT / TABLE, dtype=str, keep_default_na=False)
    s = hashlib.sha256((ROOT / TABLE).read_bytes()).hexdigest()
    print(f"Part 2: tracked table {len(full)} rows, sha256 {s[:8]} ({'ok' if s.startswith(C.TABLE_SHA) and len(full) == 562 else 'MISMATCH'})")
    tr = full[full.output_file.str.endswith(SCOPE_FILES)].reset_index(drop=True)
    bad = []
    stray = [k for k in tr.claim_id if not k.startswith(FAMILIES)]
    bad += [(f"{k} (in scope by file, family unassigned)", math.nan) for k in stray]
    new = rebuild(rtree)
    print(f"  rows in scope (tracked): {len(tr)}; rows rebuilt from the re-run files: {len(new)}")
    b, fam = compare_rows(tr, new)
    bad += b
    print("  family     rows  mismatches  max|diff|")
    for p, (n, m, mx) in fam.items():
        print(f"  {p:10s} {n:4d}  {m:10d}  {mx:9.3g}")
    return bad, tr, new


def self_test(tr: pd.DataFrame, new: pd.DataFrame) -> bool:
    """Perturb one float, drop one row and change one string in copies; each must be reported."""
    ok = True
    m = new.copy()
    i = m.index[m.claim_id.str.startswith("SCR_A_primary")][0]
    m.loc[i, "value"] = repr(float(m.loc[i, "value"]) + 1e-6)
    ok &= any(k.startswith("SCR_A_primary") for k, _ in compare_rows(tr, m)[0])
    m = new.drop(index=new.index[new.claim_id.str.startswith("C9_TVD_")][0]).reset_index(drop=True)
    ok &= bool(compare_rows(tr, m)[0])
    m = new.copy()
    j = m.index[m.claim_id.str.startswith("RO_")][0]
    m.loc[j, "n"] = str(int(float(m.loc[j, "n"])) + 1)
    ok &= any(k.startswith("RO_") for k, _ in compare_rows(tr, m)[0])
    d = C.Diff(0.0)
    d.cmp({"a": [1.0, 2.0]}, {"a": [1.0, 2.0 + 1e-12]}, "x")
    ok &= len(d.bad) == 1
    print(f"Self-test (perturbed float, dropped row, changed count, exact-rule float): {'detected' if ok else 'NOT DETECTED'}")
    return bool(ok)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rep", default=str(REP))
    ap.add_argument("--show-size", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    rtree = Path(a.rep) / "tree"
    bad = part1(rtree)
    b2, tr, new = part2(rtree)
    bad += b2
    if a.self_test and not self_test(tr, new):
        bad.append(("comparator self-test failed", math.nan))
    if not bad:
        print("0 mismatches")
        return 0
    print(f"{len(bad)} mismatches:")
    for k, d in bad:
        print(f"  {k}" + (f"  |diff| {d:.6g}" if a.show_size and d == d else ""))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
