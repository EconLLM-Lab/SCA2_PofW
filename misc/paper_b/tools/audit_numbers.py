#!/usr/bin/env python3
"""Rounding-aware number audit for the Paper B manuscript (card T10).

Every statistic in the manuscript is written as ``\\cl{<printed>}{<claim_id>[:field]}``; the macro prints
``<printed>`` and carries the claim id of ``NUMBERS_TABLE.csv``. Design constants (pool size, draws, seeds,
training settings) are written as ``\\dc{<printed>}{<key>}`` and must match the allowlist below, whose
entries name the file that fixes them. A printed statistic passes only if it equals the table value rounded to
the printed precision (SMR rounding). Any other digit left in the prose is listed; it passes only when one of
the named exclusion rules explains it (item codes, dates, identifiers, cross-references, formula constants).

Fields: v (value, default), lo (ci_low), hi (ci_high), n, pct (100 x value), abs (|value|).
Printed forms: decimals (rounded to the printed precision), integers, ``<0.001`` (value below 0.001),
hash prefixes (non-numeric table values; printed string must be a prefix of at least 8 characters).

Usage:  python audit_numbers.py [--table PATH] [--root DIR] [--out FILE]
Exit status 0 when every printed number passes and no residual numeral is unexplained, 1 otherwise.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
REPO = PAPER.parent.parent
TABLE_DEFAULT = REPO / "planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv"

# Design constants: key -> (allowed printed strings, source that fixes the value).
DESIGN: dict[str, tuple[set[str], str]] = {
    "pool_items": ({"223"}, "PREREGISTRATION.md s2 (pool of 223 items)"),
    "countries": ({"42"}, "PREREGISTRATION.md s1 (42 GPS x WVS-7 countries)"),
    "cells": ({"64"}, "PREREGISTRATION.md s1 (2^6 sign-profile factorial, 64 units)"),
    "error_df": ({"42"}, "PREREGISTRATION.md s3 (error df 42)"),
    "interactions": ({"15"}, "PREREGISTRATION.md s3 (15 two-way interactions)"),
    "x_code": ({"0.5"}, "PREREGISTRATION.md s3 (x_d = +/-0.5)"),
    "t_threshold": ({"2", "2.0"}, "PREREGISTRATION.md s3 (|t| >= 2.0)"),
    "top_share": ({"25"}, "PREREGISTRATION.md s3 (top 25 percent of 223 items)"),
    "max_selected": ({"56"}, "PREREGISTRATION.md s3 (at most 56 items)"),
    "alpha": ({"0.05"}, "PREREGISTRATION.md s3 D5 (one-sided alpha 0.05)"),
    "ci_level": ({"95"}, "PREREGISTRATION.md s4 (95 percent interval)"),
    "boot_draws": ({"2,000", "2{,}000"}, "PREREGISTRATION.md s4; bank2_transport.py DRAWS"),
    "perm_draws": ({"10,000", "10{,}000"}, "PREREGISTRATION.md s4 (10,000 draws)"),
    "seed_screen": ({"20261015"}, "paper_b/heldout/screen_test.py PERM_SEED"),
    "seed_c3": ({"20261011"}, "paper_b/analyze_surface.py BOOT_SEED"),
    "ceiling_countries": ({"28"}, "PREREGISTRATION.md s7 (28 countries with both waves)"),
    "repaired_items": ({"12"}, "PREREGISTRATION.md s11 (12 repaired items)"),
    "strict_items": ({"23"}, "TWO_PAPER_CLAIM_LOCK.md (23-item strict battery)"),
    "bank_pairs": ({"658"}, "paper_b/config.py N_ROWS; VERIFICATION.md V1 (658 triplets)"),
    "train_rows": ({"526"}, "paper_b/config.py TRAIN_ROWS (526 training pairs)"),
    "lora_r": ({"16"}, "paper_b/config.py LORA_R"),
    "dpo_beta": ({"0.1"}, "paper_b/config.py DPO_BETA"),
    "profiles_realized": ({"26"}, "results/BANK2_TRANSPORT_20261018.md (42 countries in 26 sign profiles)"),
    "near_zero_cut": ({"0.10"}, "paper_b/factorial.py NEAR_ZERO"),
    "imprint_dims": ({"4"}, "PREREGISTRATION.md s3 (four imprint dimensions); lock Amendment C7"),
    "v5_required": ({"4"}, "VERIFICATION.md V5 (at least 4 of 6 dominant)"),
    "jev_runs": ({"5"}, "PREREGISTRATION.md s6 (five runs)"),
    "jev_majority": ({"3"}, "PREREGISTRATION.md s6 (at least three of five runs)"),
    "sign_bits": ({"6"}, "PREREGISTRATION.md s1 (six GPS dimensions)"),
    "bonf_level": ({"98.75"}, "paper_b/heldout/per_dimension.py CI_BONF (0.625 and 99.375 percentiles)"),
    "surfaces": ({"7"}, "factorial_report.py (seven surfaces; patience kept as two)"),
}

CL_RE = re.compile(r"\\clh?\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}\{([^{}]*)\}")
CI_RE = re.compile(r"\\ci\{([^{}]*)\}\{([^{}]*)\}\{([^{}]*)\}")
DC_RE = re.compile(r"\\dc\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}\{([^{}]*)\}")
NUM_RE = re.compile(r"(?<![A-Za-z_\\])\d+(?:[.,]\d+)*")

# (name, pattern) applied to the de-macroed, comment-free text; a digit inside a match is explained.
EXCLUDE: list[tuple[str, re.Pattern]] = [
    ("cross-reference or citation command", re.compile(
        r"\\(?:cite[tp]?|citealp|citeauthor|citeyear|ref|eqref|label|input|include|bibliography"
        r"|bibliographystyle|usepackage|documentclass|setcounter|hyperref|url|href)\*?(?:\[[^\]]*\])*\{[^}]*\}")),
    ("LaTeX length or layout argument", re.compile(
        r"-?\d*\.?\d+\s*(?:pt|mm|cm|em|ex|in|bp)\b|\d*\.?\d+\\(?:textwidth|linewidth|columnwidth|baselineskip)"
        r"|\\\\\[[^\]]*\]|\\(?:hspace|vspace|setlength|addtolength|arraystretch|renewcommand\\arraystretch)\*?\{[^}]*\}"
        r"|\\(?:renewcommand|setstretch|linespread)\{[^}]*\}(?:\{[^}]*\})?|\\multicolumn\{\d+\}|\\cmidrule(?:\([^)]*\))?\{[^}]*\}")),
    ("WVS item code", re.compile(r"\bQ\d+\b")),
    ("named instrument or model version", re.compile(
        r"SHA-256|WVS-?\s?7|WVS-?\s?6|[Ww]ave[- ~]?[67](?:/7)?|[Ww]aves? [67] (?:and|or|to) [67]|Llama~?\s?3\.1~?\s?8B"
        r"|jev-\d+\.\d+\.\d+|2\^\{?6\}?|2\$?\^\{?6\}?\$?|\\texttt\{[^}]*\}|QLoRA|S[12]\b|C[0-7]\b|V[1-5]\b")),
    ("date or registration tag", re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b(?:19|20)\d{2}\b")),
    ("section or amendment number of a cited document", re.compile(
        r"(?:Amendment|[Ss]ection|[Ss]ections|Table|Figure|item|step|Step|[Cc]ard)s?~?\s?\d+(?:\s?(?:and|to|--)\s?\d+)?")),
    ("formula constant in display math", re.compile(
        r"\\begin\{(equation|align)\*?\}.*?\\end\{\1\*?\}", re.S)),
    ("TikZ figure geometry", re.compile(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", re.S)),
    ("formula constant in math mode", re.compile(r"\$[^$]*\$")),
]

TEX_FILES_ORDER = ["title_page.tex", "abstract.tex", "introduction.tex", "background.tex", "instrument.tex",
                   "design.tex", "results.tex", "discussion.tex", "conclusion.tex", "backmatter.tex"]


def load_table(path: Path) -> dict[str, dict[str, str]]:
    with open(path, newline="") as fh:
        return {r["claim_id"]: r for r in csv.DictReader(fh)}


def _clean(printed: str) -> str:
    s = printed.replace("$", "").replace("{,}", ",").replace("\\,", "").replace("~", "").strip()
    return s.replace("\u2212", "-").replace("--", "-")


def _decimals(s: str) -> int:
    return len(s.split(".")[1]) if "." in s else 0


FIELDS = {"v", "lo", "hi", "n", "pct", "abs"}


def split_ref(ref: str, table: dict[str, dict[str, str]]) -> tuple[str, str]:
    """Split ``<claim_id>[:field]``. Some claim ids contain a colon, so the whole ref wins if it is a row."""
    if ref in table:
        return ref, "v"
    cid, sep, field = ref.rpartition(":")
    if sep and field in FIELDS:
        return cid, field
    return ref, "v"


def check(printed: str, ref: str, table: dict[str, dict[str, str]]) -> tuple[str, str]:
    cid, field = split_ref(ref, table)
    row = table.get(cid)
    if row is None:
        return "FAIL", f"claim_id {cid!r} not in NUMBERS_TABLE"
    raw = {"v": row.get("value", ""), "lo": row.get("ci_low", ""), "hi": row.get("ci_high", ""),
           "n": row.get("n", ""), "pct": row.get("value", ""), "abs": row.get("value", "")}.get(field)
    if raw is None or raw == "":
        return "FAIL", f"field {field!r} empty for {cid}"
    s = _clean(printed)
    try:
        full = Decimal(raw)
    except InvalidOperation:  # hash or other string value
        p = s.rstrip(".").replace("\\ldots", "").replace("…", "")
        ok = len(p) >= 8 and raw.startswith(p)
        return ("PASS" if ok else "FAIL"), f"string value {raw}"
    if field == "pct":
        full = full * 100
    if field == "abs":
        full = abs(full)
    if s.startswith("<"):
        bound = Decimal(s[1:])
        return ("PASS" if full < bound else "FAIL"), f"full {raw}"
    s_num = s.replace(",", "")
    try:
        shown = Decimal(s_num)
    except InvalidOperation:
        return "FAIL", f"cannot parse printed {printed!r}"
    q = Decimal(1).scaleb(-_decimals(s_num))
    rounded = full.quantize(q, rounding=ROUND_HALF_UP)
    ok = rounded == shown
    return ("PASS" if ok else "FAIL"), f"full {raw}{' x100' if field == 'pct' else ''} -> {rounded}"


def strip_comments(tex: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", tex)


def extract(tex: str):
    body = strip_comments(tex)
    cls = []
    for lo, hi, cid in CI_RE.findall(body):
        cls += [(lo, f"{cid}:lo"), (hi, f"{cid}:hi")]
    body = CI_RE.sub(" ", body)
    cls += CL_RE.findall(body)
    dcs = DC_RE.findall(body)
    rest = DC_RE.sub(" ", CL_RE.sub(" ", body))
    explained = []
    for name, pat in EXCLUDE:
        for m in pat.finditer(rest):
            for n in NUM_RE.finditer(m.group(0)):
                explained.append((n.group(0), name, m.group(0)[:60]))
        rest = pat.sub(" ", rest)
    residual = [(m.group(0), rest[max(0, m.start() - 40): m.end() + 40].replace("\n", " "))
                for m in NUM_RE.finditer(rest)]
    return cls, dcs, residual


def extract_explained(tex: str):
    body = DC_RE.sub(" ", CL_RE.sub(" ", CI_RE.sub(" ", strip_comments(tex))))
    out = []
    for name, pat in EXCLUDE:
        for m in pat.finditer(body):
            if NUM_RE.search(m.group(0)):
                out.append((name, m.group(0).replace("\n", " ")[:70]))
        body = pat.sub(" ", body)
    return out


def tex_files(root: Path) -> list[Path]:
    files = [root / f for f in TEX_FILES_ORDER if (root / f).exists()]
    files += sorted((root / "tables").glob("*.tex")) if (root / "tables").exists() else []
    return files


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", type=Path, default=TABLE_DEFAULT)
    ap.add_argument("--root", type=Path, default=PAPER)
    ap.add_argument("--out", type=Path, default=PAPER / "NUMBER_AUDIT.txt")
    a = ap.parse_args(argv)
    table = load_table(a.table)
    sha = hashlib.sha256(a.table.read_bytes()).hexdigest()
    lines = [f"Paper B number audit (card T10). Table: {a.table.relative_to(REPO)}",
             f"Table sha256 {sha}, {len(table)} rows. Rule: a printed number passes only if it equals the",
             "table value rounded to the printed precision (p to 3 decimals, t to 2, percentages to 1).", ""]
    n_pass = n_fail = n_dc_fail = n_resid = 0
    used: set[str] = set()
    for f in tex_files(a.root):
        tex = f.read_text()
        cls, dcs, residual = extract(tex)
        lines.append(f"== {f.relative_to(a.root)}: {len(cls)} statistics, {len(dcs)} design constants")
        for printed, ref in cls:
            status, detail = check(printed, ref, table)
            used.add(split_ref(ref, table)[0])
            n_pass += status == "PASS"
            n_fail += status == "FAIL"
            lines.append(f"  {status}  {_clean(printed):>12}  {ref:<55} {detail}")
        for printed, key in dcs:
            allowed, src = DESIGN.get(key, (set(), "UNKNOWN KEY"))
            ok = _clean(printed) in {_clean(x) for x in allowed}
            n_dc_fail += not ok
            lines.append(f"  {'PASS' if ok else 'FAIL'}  {_clean(printed):>12}  design:{key:<48} {src}")
        for num, ctx in residual:
            n_resid += 1
            lines.append(f"  FAIL  {num:>12}  unexplained numeral in prose: ...{ctx}...")
        for name, frag in extract_explained(tex):
            lines.append(f"  note  explained ({name}): {frag}")
        lines.append("")
    total = n_pass + n_fail
    lines += [f"Statistics: {total} printed, {n_pass} PASS, {n_fail} FAIL.",
              f"Design constants: {n_dc_fail} FAIL.", f"Unexplained numerals: {n_resid}.",
              f"Distinct claim_ids used: {len(used)}.",
              "RESULT: " + ("PASS" if (n_fail == 0 and n_dc_fail == 0 and n_resid == 0) else "FAIL")]
    a.out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-5:]))
    return 0 if (n_fail == 0 and n_dc_fail == 0 and n_resid == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
