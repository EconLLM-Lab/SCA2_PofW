"""Drift guards for the repo spine (AGENTS.md, STATUS.md, planning/DECISIONS.md).

Every profile and every agent reads these files first, so a number or a link in them that has gone
stale is worse than none. These tests fail when:
- STATUS.md quotes a NUMBERS_TABLE value that the table no longer holds (at the printed precision),
- STATUS.md pins a table hash or row count the table no longer has,
- a relative link in a spine document points at nothing,
- a planning document exists that the STATUS.md document map does not classify,
- a document the map calls a record does not open with the record banner.
"""
from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "STATUS.md"
TABLE = ROOT / "planning" / "sprint_2026-10-11" / "paper-b-tier1" / "NUMBERS_TABLE.csv"
SPINE = [p for p in (ROOT / "AGENTS.md", STATUS, ROOT / "planning" / "DECISIONS.md",
                     ROOT / "planning" / "KANBAN_LEDGER.md", ROOT / "README.md")
         if p.name != "AGENTS.md" or p.exists()]
BANNER = "> **Record, not status.**"
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
NUM = re.compile(r"[−-]?\d+\.\d+")


def _table() -> dict[str, dict[str, str]]:
    with TABLE.open(newline="") as fh:
        return {r["claim_id"]: r for r in csv.DictReader(fh)}


def _section(text: str, title: str) -> str:
    m = re.search(rf"^## {re.escape(title)}\b.*?$(.*?)(?=^## |\Z)", text, flags=re.M | re.S)
    assert m, f"STATUS.md has no '## {title}' section"
    return m.group(1)


def _links(path: Path) -> list[Path]:
    out = []
    for target in LINK.findall(path.read_text()):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        out.append((path.parent / target.split("#", 1)[0]).resolve())
    return out


def test_agents_md_points_every_tool_at_the_same_spine():
    agents_path = ROOT / "AGENTS.md"
    if not agents_path.exists():
        pytest.skip("AGENTS.md is pending Augusto's approval (protected instruction file)")
    agents = agents_path.read_text()
    for name in ("STATUS.md", "planning/DECISIONS.md", "planning/TWO_PAPER_CLAIM_LOCK.md", "NUMBERS_TABLE.csv"):
        assert name in agents, name
    claude = ROOT / "CLAUDE.md"
    if claude.exists():
        assert claude.read_text().strip().startswith("@AGENTS.md")


def test_status_pins_the_current_numbers_table():
    text = STATUS.read_text()
    digest = hashlib.sha256(TABLE.read_bytes()).hexdigest()
    assert digest in text, "STATUS.md does not carry the current NUMBERS_TABLE sha256"
    m = re.search(r"NUMBERS_TABLE\.csv[^\n]*?(\d+) rows", text)
    assert m and int(m.group(1)) == len(_table())


def test_status_quotes_numbers_exactly_as_the_table_holds_them():
    table = _table()
    rows = [ln for ln in _section(STATUS.read_text(), "Headline numbers").splitlines() if ln.startswith("|")]
    checked = 0
    for ln in rows:
        ids = [c for c in re.findall(r"`([A-Za-z0-9_]+)`", ln) if c in table]
        if not ids:
            continue
        assert len(ids) == 1, ln
        r = table[ids[0]]
        cells = [c.strip() for c in ln.strip("|").split("|")]
        quoted = [q.replace("−", "-") for q in NUM.findall(cells[1])]
        wanted = [r["value"]] + ([r["ci_low"], r["ci_high"]] if len(quoted) == 3 else [])
        assert len(quoted) in (1, 3), ln
        for q, w in zip(quoted, wanted):
            dec = len(q.split(".")[1])
            assert f"{float(w):.{dec}f}" == f"{float(q):.{dec}f}", f"{ids[0]}: quoted {q}, table {w}"
        checked += 1
    assert checked >= 8, "the headline table lost its claim-id rows"


def test_spine_links_resolve():
    broken = [f"{p.relative_to(ROOT)} -> {t}" for p in SPINE for t in _links(p) if not t.exists()]
    assert not broken, broken


def test_every_planning_document_is_classified_in_the_document_map():
    mapped = _links(STATUS)
    unmapped = []
    for md in sorted((ROOT / "planning").rglob("*.md")):
        md = md.resolve()
        if md in mapped or any(d.is_dir() and d in md.parents for d in mapped):
            continue
        unmapped.append(str(md.relative_to(ROOT)))
    assert not unmapped, f"add these to the STATUS.md document map: {unmapped}"


def test_documents_mapped_as_records_open_with_the_banner():
    record = _section(STATUS.read_text(), "Document map")
    record = record.split("### Record", 1)[1]
    files = [(STATUS.parent / t).resolve() for t in LINK.findall(record)
             if not t.startswith("http") and t.endswith(".md")]
    assert files
    missing = [str(f.relative_to(ROOT)) for f in files
               if BANNER not in "\n".join(f.read_text().splitlines()[:8])]
    assert not missing, missing
