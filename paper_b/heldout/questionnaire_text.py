"""WVS-7 questionnaire wording for the held-out pool (text layer of the official PDF).

`planning/pre_arxiv_checks/item_table/MasterQuestionnaire.txt` is the text layer of
`data/WVS/MasterQuestionnaire.pdf`. Two layouts occur:

  standalone  "Q57. Generally speaking, would you say ... (Code one answer):"
  grid row    " Q65       The armed forces        1    2    3    4"
              under a prose intro ("... how much confidence you have in them ...")

A grid row's question is "<battery intro> — <row label>".
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_TEXT = REPO / "planning" / "pre_arxiv_checks" / "item_table" / "MasterQuestionnaire.txt"

_STANDALONE = re.compile(r"^\s*(Q\d{1,3})\.\s*(.*)$")
_GRID_ROW = re.compile(r"^\s*(Q\d{1,3})\s{2,}(.*?)(?:\s{2,}|\s)(?:-?\d+\s*)+$")
_OPTION = re.compile(r"^\s*-?\d{1,3}\s{1,}\S")
_NOISE = re.compile(
    r"\((?:Code|Read out|Show|SHOW|Interviewer|code)[^)]*\)?|SHOW CARD\s*\d*|"
    r"Interviewer[^.]*\.|\[[^\]]*\]\d*", re.IGNORECASE)


_COLUMNS = re.compile(r"\S\s{3,}\S.*\S\s{3,}\S")   # two+ wide gaps = a table header


def _is_columns(line: str) -> bool:
    return bool(_COLUMNS.search(line.strip()))


def clean(text: str) -> str:
    text = re.sub(r"\s1\.\s.*$", "", text)       # inline options "1. Freedom 2. Security"
    text = _NOISE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s:\s.*$", "", text)   # " : <scale anchors / column header>" left by noise removal
    return text.rstrip(":;").strip()


def _is_prose(line: str) -> bool:
    s = line.strip()
    if not s or s.startswith("\f") or "WVS 2017" in s or re.match(r"^Q\d", s):
        return False
    if _is_columns(line) or (s.upper() == s and any(c.isalpha() for c in s)):
        return False
    if _OPTION.match(line):
        return False
    words = re.findall(r"[A-Za-z’']+", s)
    return len(words) >= 4


def extract(path: Path | None = None) -> dict[str, str]:
    """Map Q-id -> standalone question wording."""
    path = Path(path or DEFAULT_TEXT)
    if not path.is_file():
        raise FileNotFoundError(f"questionnaire text not found: {path}")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out: dict[str, str] = {}
    intro: list[str] = []          # most recent prose block (battery intro)
    block: list[str] = []          # prose block being read
    i = 0
    while i < len(lines):
        line = lines[i].replace("\f", "")
        m = _STANDALONE.match(line)
        if m and re.search(r"\S\s{3,}(?:-?\d{1,3}\s+)*-?\d{1,3}\s*$", line):
            # numbered grid row: "Q209. Signing a petition      1      2      3"
            label = clean(re.sub(r"(\s+-?\d{1,3})+\s*$", "", m.group(2)))
            stem = clean(" ".join(intro))
            if label:
                out.setdefault(m.group(1), f"{stem} — {label}" if stem else label)
            block = []
            i += 1
            continue
        if m:
            qid, parts = m.group(1), [m.group(2)]
            j = i + 1
            while j < len(lines):
                nxt = lines[j].replace("\f", "")
                if not nxt.strip() or _OPTION.match(nxt) or re.match(r"^\s*Q\d{1,3}\b", nxt):
                    break
                if "WVS 2017" in nxt or _is_columns(nxt):
                    break
                parts.append(nxt.strip())
                j += 1
            text = clean(" ".join(parts))
            if text:
                out.setdefault(qid, text)
                intro = [text]     # a standalone stem can head a grid that follows
            block = []
            i = j
            continue
        g = re.match(r"^\s*(Q\d{1,3})\s{2,}(.+)$", line)
        if g and not line.strip().startswith(tuple(f"{g.group(1)}." for _ in [0])):
            qid = g.group(1)
            label = re.sub(r"(\s+-?\d{1,3})+\s*$", "", g.group(2)).strip()
            j = i + 1        # wrapped row label: indented words, no codes, no new Q
            while j < len(lines):
                nxt = lines[j].replace("\f", "")
                if (not nxt.strip() or re.match(r"^\s*Q\d{1,3}\b", nxt) or _OPTION.match(nxt)
                        or _is_columns(nxt) or "WVS 2017" in nxt or not nxt.startswith(" ")):
                    break
                label += " " + re.sub(r"(\s+-?\d{1,3})+\s*$", "", nxt).strip()
                j += 1
            label = clean(label)
            stem = clean(" ".join(intro))
            if label:
                out.setdefault(qid, f"{stem} — {label}" if stem else label)
            block = []
            i = j
            continue
        if _is_prose(line):
            block.append(line.strip())
            intro = list(block)
        elif not line.strip():
            block = []
        i += 1
    return {k: v for k, v in out.items() if v}
