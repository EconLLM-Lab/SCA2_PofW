#!/usr/bin/env python3
"""Render the online supplement from supplement.tmpl.tex and NUMBERS_TABLE.csv.

The template writes the LaTeX backslash as the section sign and every statistic as a placeholder:

    «v|<claim_id>|<decimals>»    value rounded half-up            -> cl{<printed>}{<claim_id>}
    «pct|<claim_id>|<decimals>»  100 x value                      -> cl{<printed>}{<claim_id>:pct}
    «n|<claim_id>»               the row's n                      -> cl{<n>}{<claim_id>:n}
    «ci|<claim_id>|<decimals>»   interval                         -> ci{<lo>}{<hi>}{<claim_id>}
    «h|<claim_id>|<chars>»       hash prefix                      -> clh{<prefix>}{<claim_id>}
    «items»                      rows of the frozen primary selection, by dimension and sign

The output keeps the manuscript's number macros, so tools/audit_numbers.py re-checks every printed number
against the table. An unknown claim id, an unknown placeholder or a count that disagrees with the table stops
the render.

Usage:  python render_supplement.py [--table PATH] [--selection PATH] [--template PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
REPO = PAPER.parent.parent
TABLE_DEFAULT = REPO / "planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv"
SELECTION_DEFAULT = REPO / "paper_b/heldout/selection_amended_20261016.csv"

BS = chr(92)  # the LaTeX backslash; kept out of string literals on purpose
SECTION = "§"
PLACEHOLDER = re.compile("«([a-z]+)[|]([^|»]+)(?:[|]([0-9]+))?»")
DIMENSIONS = [("trust", "Trust"), ("risktaking", "Risk taking"), ("posrecip", "Positive reciprocity"),
              ("altruism", "Altruism")]


def _fmt(raw: str, decimals: int, scale: int = 1) -> str:
    q = Decimal(1).scaleb(-decimals)
    x = (Decimal(raw) * scale).quantize(q, rounding=ROUND_HALF_UP)
    if x == 0:
        x = abs(x)
    return str(x)


def _n(raw: str) -> str:
    n = int(Decimal(raw))
    return f"{n:,}".replace(",", "{,}")


def _row(table: dict, cid: str) -> dict:
    if cid not in table:
        raise KeyError(f"claim_id {cid!r} not in NUMBERS_TABLE")
    return table[cid]


def _sub(m: re.Match, table: dict) -> str:
    kind, cid, arg = m.group(1), m.group(2), m.group(3)
    r = _row(table, cid)
    if kind == "v":
        return f"{BS}cl{{{_fmt(r['value'], int(arg))}}}{{{cid}}}"
    if kind == "pct":
        return f"{BS}cl{{{_fmt(r['value'], int(arg), 100)}}}{{{cid}:pct}}"
    if kind == "n":
        return f"{BS}cl{{{_n(r['n'])}}}{{{cid}:n}}"
    if kind == "ci":
        d = int(arg)
        return f"{BS}ci{{{_fmt(r['ci_low'], d)}}}{{{_fmt(r['ci_high'], d)}}}{{{cid}}}"
    if kind == "h":
        return f"{BS}clh{{{r['value'][:int(arg)]}}}{{{cid}}}"
    raise ValueError(f"unknown placeholder kind {kind!r}")


def item_rows(selection: pd.DataFrame, table: dict) -> str:
    """One row per imprint dimension: item count (a table macro) and the items by sign of t."""
    sel = selection[selection["primary_selected"].astype(bool)]
    lines = []
    for dim, name in DIMENSIONS:
        cid = f"PD_adapter_primary_{dim}_A"
        part = sel[sel["top_dimension"] == dim]
        assert len(part) == int(Decimal(_row(table, cid)["n"])), f"{dim}: selection and table disagree"
        if part.empty:
            continue
        key = lambda q: int(q[1:])  # noqa: E731
        pos = sorted(part.loc[part["t_top"] > 0, "question_id"], key=key)
        neg = sorted(part.loc[part["t_top"] < 0, "question_id"], key=key)
        lines.append(f"{name} & {BS}cl{{{len(part)}}}{{{cid}:n}} & {', '.join(pos) or 'none'} & "
                     f"{', '.join(neg) or 'none'} {BS}{BS}")
    return "\n".join(lines)


def render(template: str, table: dict, selection: pd.DataFrame | None = None) -> str:
    out = template
    if "«items»" in out:
        if selection is None:
            raise ValueError("«items» needs the frozen selection")
        out = out.replace("«items»", item_rows(selection, table).replace(BS, SECTION))
    out = PLACEHOLDER.sub(lambda m: _sub(m, table).replace(BS, SECTION), out)
    if "«" in out or "»" in out:
        raise ValueError("unresolved placeholder: " + out[out.find("«"):out.find("«") + 60])
    return out.replace(SECTION, BS)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", type=Path, default=TABLE_DEFAULT)
    ap.add_argument("--selection", type=Path, default=SELECTION_DEFAULT)
    ap.add_argument("--template", type=Path, default=PAPER / "supplement.tmpl.tex")
    ap.add_argument("--out", type=Path, default=PAPER / "supplement.tex")
    a = ap.parse_args(argv)
    with open(a.table, newline="") as fh:
        table = {r["claim_id"]: r for r in csv.DictReader(fh)}
    tex = render(a.template.read_text(), table, pd.read_csv(a.selection))
    a.out.write_text(tex)
    print(f"wrote {a.out.relative_to(REPO)} ({len(tex)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
