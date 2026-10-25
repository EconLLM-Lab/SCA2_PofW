#!/usr/bin/env python3
"""RP1 comparison: re-run model-only results vs the tracked ones, then the rebuilt numbers table vs the tracked one.

Card CP26-RP1 (t_bfaf8f2a). Run after `.replication_2026-10-25/model_only/run_all.sh` has finished:

    env -u PYTHONPATH .venv/bin/python planning/checkpoint_2026-10-26/replication/compare_results.py [--show-size]

Part 1  every re-run JSON/CSV in the copied tree (`rtree/`) against the tracked file of the same name: every field,
        ints/bools/strings exact; floats exact for the seeded-bootstrap files (same seed, same draws), else abs <= 1e-9.
        Path fields (`path`, `source`) are skipped, the sha256 beside them is compared.
Part 2  `build_numbers_table.py` of the copied tree (reading the re-run files) against the tracked 562-row table,
        row by row in the RP1 scope (families below); the other rows belong to RP2 (human data) and are only counted.

Output: counts per file and family, then `0 mismatches` or the mismatching keys (claim_id or file:field), never rows.
`--show-size` adds the absolute difference next to each mismatching key. Nothing under paper_b/, results/ or the
table is written; the rebuilt table goes to `<rep>/NUMBERS_TABLE_rebuilt.csv`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
REP = ROOT / ".replication_2026-10-25/model_only"
RES = "planning/sprint_2026-10-11/paper-b-tier1/results"
TABLE = "planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv"
TABLE_SHA = "71ee7c8c"                       # first 8 hex of the tracked table (card header)
TOL = 1e-9

# Files re-run by RP1 (relative to results/); True = seeded bootstrap or replayed bootstrap, so floats must match exactly.
FILES = {
    "bank2_transport_strict.json": True,
    "factorial/factorial_report.json": False,
    "factorial/mtmm_adapter.csv": False,
    "factorial/mtmm_signprompt.csv": False,
    "factorial/mtmm_adapter_cells.csv": False,
    "factorial/mtmm_signprompt_cells.csv": False,
    "factorial/mtmm_adapter_standardized.csv": False,
    "factorial/mtmm_summary.json": False,
    "factorial/route26_adapter_standardized.csv": False,
    "factorial/route26_signprompt_standardized.csv": False,
    "factorial/route64_adapter_standardized.csv": False,
    "factorial/route64_signprompt_standardized.csv": False,
    "replicate/replicate_analysis.json": False,
    "replicate/replicate_surface_diff.csv": False,
    "replicate/replicate_item_codes.csv": False,
    "near_zero/near_zero_analysis.json": False,
    "near_zero/near_zero_table.csv": False,
    "persona/persona_strict.json": True,
    "c9/w1_why_trust.json": False,
    "c9/c9_label_recovery.json": True,
    "c9/c9_label_recovery.csv": True,
    "robustness/selection_heldout_reverse.csv": False,
    "robustness/selection_heldout_para_a.csv": False,
    "robustness/selection_heldout_para_b.csv": False,
}
# Tracked files in the same directories that no recorded command regenerates (informational, not a mismatch).
NOT_REGENERATED = ["factorial/bank_robustness.csv"]
# Row families in RP1 scope: prefix -> exact floats?
FAMILIES = {
    "B2_": True, "FX_": False, "FX26_": False, "RP_": False, "NZ_": False, "RO_": False, "HASH_": False,
    "PX_": True, "C9_W1_": False, "C9_label_recovery_": True,
}
# Families RP2 owns (read human data): only counted here.
RP2_PREFIXES = ("SCR_", "PD_", "CMP_", "SP_", "C9_a_", "C9_b_", "C9_c_", "C9_d_", "C9_e_", "C9_f_", "C9_TVD_")
SKIP_KEYS = {"path", "source"}              # absolute paths differ by design; sha256 next to them is compared


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


class Diff:
    def __init__(self, tol: float):
        self.tol, self.n, self.bad, self.maxd = tol, 0, [], 0.0

    def cmp(self, a, b, key: str):
        if isinstance(a, dict) and isinstance(b, dict):
            if set(a) != set(b):
                self.n += 1
                self.bad.append((f"{key} (keys differ)", math.nan))
            for k in sorted(set(a) & set(b)):
                if k in SKIP_KEYS:
                    continue
                self.cmp(a[k], b[k], f"{key}/{k}")
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                self.n += 1
                self.bad.append((f"{key} (length {len(a)} vs {len(b)})", math.nan))
            for i, (x, y) in enumerate(zip(a, b)):
                self.cmp(x, y, f"{key}[{i}]")
        else:
            self.n += 1
            self._leaf(a, b, key)

    def _leaf(self, a, b, key):
        if _num(a) and _num(b) and not (isinstance(a, int) and isinstance(b, int)):
            if math.isnan(a) and math.isnan(b):
                return
            d = abs(a - b)
            self.maxd = max(self.maxd, d if math.isfinite(d) else 0.0)
            if not (d <= self.tol):
                self.bad.append((key, d))
        elif a != b or type(a) is not type(b) and not (_num(a) and _num(b)):
            self.bad.append((key, math.nan))


def read_any(path: Path):
    if path.suffix == ".json":
        return json.loads(path.read_text())
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    out = []
    for rec in df.to_dict("records"):
        row = {}
        for k, v in rec.items():
            try:
                row[k] = int(v) if v.lstrip("-").isdigit() else float(v)
            except ValueError:
                row[k] = v
        out.append(row)
    return out


def part1(rtree: Path, show: bool) -> list[tuple[str, int, int, float]]:
    rows, bad_all = [], []
    for rel, exact in FILES.items():
        new, old = rtree / RES / rel, ROOT / RES / rel
        if not new.is_file():
            rows.append((rel, 0, 1, math.nan)); bad_all.append((f"{rel} (not regenerated)", math.nan)); continue
        d = Diff(0.0 if exact else TOL)
        d.cmp(read_any(new), read_any(old), rel)
        rows.append((rel, d.n, len(d.bad), d.maxd)); bad_all += d.bad
    print("Part 1: re-run files vs tracked files")
    for rel, n, m, mx in rows:
        print(f"  {rel:45s} fields {n:6d}  mismatches {m:3d}  max|diff| {mx:.3g}")
    for rel in NOT_REGENERATED:
        print(f"  {rel:45s} not regenerated: no recorded command (not read by the numbers table)")
    return bad_all


def part2(rtree: Path, show: bool):
    out = REP / "NUMBERS_TABLE_rebuilt.csv"
    cmd = [sys.executable, str(rtree / "paper_b/build_numbers_table.py"), "--out", str(out),
           "--readout-dir", str(rtree / RES / "robustness")]
    r = subprocess.run(cmd, cwd=rtree, capture_output=True, text=True)
    print(f"Part 2: build_numbers_table.py in the copied tree exit {r.returncode}")
    if r.returncode:
        print(r.stderr[-400:]); return [("build_numbers_table.py failed", math.nan)]
    tr = pd.read_csv(ROOT / TABLE, dtype=str, keep_default_na=False)
    sha = hashlib.sha256((ROOT / TABLE).read_bytes()).hexdigest()
    print(f"  tracked table: {len(tr)} rows, sha256 {sha[:8]} (card says {TABLE_SHA}): {'ok' if sha.startswith(TABLE_SHA) and len(tr) == 562 else 'MISMATCH'}")
    new = pd.read_csv(out, dtype=str, keep_default_na=False)
    bad = []
    if tr.claim_id.is_unique is False or new.claim_id.is_unique is False:
        bad.append(("claim_id not unique", math.nan))
    ti, ni = tr.set_index("claim_id"), new.set_index("claim_id")
    print(f"  rebuilt table: {len(new)} rows; keys only in tracked: {len(set(ti.index) - set(ni.index))}, only in rebuilt: {len(set(ni.index) - set(ti.index))}")
    for k in sorted(set(ti.index) ^ set(ni.index)):
        bad.append((f"{k} (row on one side only)", math.nan))
    scope = lambda k: next((p for p in FAMILIES if k.startswith(p)), None)
    rp2 = [k for k in ti.index if k.startswith(RP2_PREFIXES)]
    unassigned = [k for k in ti.index if scope(k) is None and not k.startswith(RP2_PREFIXES)]
    print(f"  rows in RP1 scope: {sum(scope(k) is not None for k in ti.index)}; left to RP2: {len(rp2)}; unassigned: {len(unassigned)}")
    bad += [(f"{k} (family unassigned)", math.nan) for k in unassigned]
    fam_stats = {p: [0, 0, 0.0] for p in FAMILIES}
    for k in sorted(set(ti.index) & set(ni.index)):
        p = scope(k)
        if p is None:
            continue
        fam_stats[p][0] += 1
        a, b = ti.loc[k], ni.loc[k]
        tol = 0.0 if FAMILIES[p] else TOL
        for col in ("sentence_use", "statistic", "n", "surface_label", "run_id", "producing_script", "output_file"):
            if a[col] != b[col]:
                bad.append((f"{k}:{col}", math.nan)); fam_stats[p][1] += 1
        for col in ("value", "ci_low", "ci_high"):
            x, y = a[col], b[col]
            if x == y:
                continue
            try:
                fx, fy = float(x), float(y)
            except ValueError:
                bad.append((f"{k}:{col}", math.nan)); fam_stats[p][1] += 1; continue
            if "e" not in x.lower() and "." not in x and "." not in y:      # integer-valued column: exact
                tol_here = 0.0
            else:
                tol_here = tol
            d = abs(fx - fy)
            fam_stats[p][2] = max(fam_stats[p][2], d)
            if not d <= tol_here:
                bad.append((f"{k}:{col}", d)); fam_stats[p][1] += 1
    print("  family               rows  mismatches  max|diff|  float rule")
    for p, (n, m, mx) in fam_stats.items():
        print(f"  {p:20s} {n:4d}  {m:10d}  {mx:9.3g}  {'exact' if FAMILIES[p] else '<=1e-9'}")
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rep", default=str(REP))
    ap.add_argument("--show-size", action="store_true")
    a = ap.parse_args(argv)
    rtree = Path(a.rep) / "rtree"
    bad = part1(rtree, a.show_size) + part2(rtree, a.show_size)
    if not bad:
        print("0 mismatches")
        return 0
    print(f"{len(bad)} mismatches:")
    for k, d in bad:
        print(f"  {k}" + (f"  |diff| {d:.6g}" if a.show_size and d == d else ""))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
