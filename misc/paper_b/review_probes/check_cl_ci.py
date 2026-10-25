#!/usr/bin/env python3
"""CP26-MV probe 1b: independent check of every \\cl{value}{id} and \\ci{lo}{hi}{id} in all .tex
files against NUMBERS_TABLE.csv at the printed precision.

Own implementation: no imports from tools/audit_numbers.py. Rounded with ROUND_HALF_UP on the
table's decimal string. Printed forms handled: plain decimals, negatives, integers, `{,}`
thousands separators, `<0.001`, and the fields :v (default), :lo, :hi, :n, :pct, :abs.
Full-line comments (leading %) are skipped (macros.tex documents the macro in a comment).
Prints only `0 mismatches` or the mismatching ids.
Usage: python check_cl_ci.py [--table PATH] [--root DIR]
Exit 0 iff no mismatches and no unknown ids.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
REPO = PAPER.parent.parent
TABLE_DEFAULT = REPO / "planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv"

CL = re.compile(r"\\cl\{([^{}]*)\}\{([^{}]*)\}")
CI = re.compile(r"\\ci\{([^{}]*)\}\{([^{}]*)\}\{([^{}]*)\}")
COMMENT = re.compile(r"^\s*%")
# the macro definitions in macros.tex (e.g. \newcommand{\cl}[2]{...}) are not uses
DEFN = re.compile(r"\\(newcommand|renewcommand|providecommand|def)\b")
FIELDS = ("lo", "hi", "n", "pct", "abs", "v")


def parse_ref(ref: str):
    """Claim ids may themselves contain colons (e.g. B2_cohort1_patience:Q43_rho), so only a
    trailing :<known field> is a field suffix."""
    head, sep, tail = ref.rpartition(":")
    if sep and tail in FIELDS and head:
        return head, tail
    return ref, "v"


def load_table(path: Path):
    rows = {}
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            cid = row["claim_id"]
            rows[cid] = {
                "v": row["value"],
                "lo": row["ci_low"],
                "hi": row["ci_high"],
                "n": row["n"],
            }
    return rows


def cell_for(rows, cid, field):
    if cid not in rows:
        return None, None, f"unknown claim id {cid}"
    base = "v" if field in ("v", "pct", "abs") else field
    raw = rows[cid][base]
    if raw is None or raw == "":
        return None, None, f"{cid}:{field} has empty table cell"
    d = Decimal(raw)
    if field == "pct":
        d = d * 100
    elif field == "abs":
        d = abs(d)
    return d, raw, None


def decimals_of(printed: str) -> int:
    p = printed.replace("{,}", "")
    if "." in p:
        return len(p.split(".", 1)[1])
    return 0


def round_half_up(value: Decimal, places: int) -> Decimal:
    q = Decimal(1).scaleb(-places)
    return value.quantize(q, rounding=ROUND_HALF_UP)


def check_printed(printed: str, table_value: Decimal, where: str, problems: list):
    p = printed.replace("{,}", "").strip()
    if p.startswith("<"):
        # comparison form, only `<0.001` expected
        try:
            bound = Decimal(p[1:])
        except Exception:
            problems.append(f"{where}: unparseable comparison print {printed!r}")
            return
        if not table_value < bound:
            problems.append(f"{where}: prints {printed!r} but table value {table_value} >= {bound}")
        return
    places = decimals_of(printed)
    expected = round_half_up(table_value, places)
    norm_p = p.replace(",", "")  # 1,087 form
    try:
        got = Decimal(norm_p)
    except Exception:
        problems.append(f"{where}: unparseable print {printed!r}")
        return
    if got != expected:
        problems.append(
            f"{where}: prints {printed!r} (field {places} dp) but table rounds to {expected}"
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", type=Path, default=TABLE_DEFAULT)
    ap.add_argument("--root", type=Path, default=PAPER)
    args = ap.parse_args()

    rows = load_table(args.table)
    tex_files = sorted(
        list((args.root).glob("*.tex"))
        + list((args.root / "tables").glob("*.tex"))
    )
    problems: list[str] = []
    counts = {}
    for f in tex_files:
        n_cl = n_ci = 0
        for lineno, line in enumerate(f.read_text().splitlines(), 1):
            if COMMENT.match(line) or DEFN.search(line):
                continue
            # \ci first so its embedded \cl-equivalents are not double-counted
            for m in CI.finditer(line):
                lo, hi, cid = m.groups()
                n_ci += 1
                for printed, field in ((lo, "lo"), (hi, "hi")):
                    val, _, err = cell_for(rows, cid, field)
                    if err:
                        problems.append(f"{f.name}:{lineno}: {err}")
                        continue
                    check_printed(printed, val, f"{f.name}:{lineno} (\\ci {cid}:{field})", problems)
                # also make sure the :lo/:hi fields exist is covered above
            for m in CL.finditer(line):
                printed, ref = m.groups()
                cid, field = parse_ref(ref)
                n_cl += 1
                val, _, err = cell_for(rows, cid, field)
                if err:
                    problems.append(f"{f.name}:{lineno}: {err}")
                    continue
                check_printed(printed, val, f"{f.name}:{lineno} (\\cl {ref})", problems)
        counts[f.name] = (n_cl, n_ci)

    total = sum(a + b for a, b in counts.values())
    if problems:
        print(f"{len(problems)} mismatches")
        for p in problems:
            print(" ", p)
        sys.exit(1)
    print(f"0 mismatches ({total} checks: {sum(b for _, b in counts.values())} \\ci, "
          f"{sum(a for a, _ in counts.values())} \\cl, over {len(counts)} files)")
    per_file = ", ".join(f"{k}:{v[0]}+{v[1]}" for k, v in counts.items() if v[0] + v[1])
    print("  per-file: " + per_file)
    sys.exit(0)


if __name__ == "__main__":
    main()
