#!/usr/bin/env python3
"""Build the held-out WVS-7 item pool from metadata and questionnaire text only.

Reads NO responses: `pyreadstat.read_dta(..., metadataonly=True)` returns variable
labels and value labels, never a respondent row.

Pool rule (frozen before any held-out item is scored or any human value is read):
  * a `Qnnn` variable of data/WVS/WVS_wave7.dta;
  * not one of the 35 items in DPO_eval_WVS/question_map_wvs_edited.csv;
  * not the demographic block (Q260 and above);
  * 2..11 non-negative response codes that are contiguous integers;
  * an ordinal reading of its codes (TRUE, or REVIEW resolved in overrides.json).

Output is in question-map format, so build_scoring_spec.py --battery heldout
--question-map <pool csv> consumes it directly.

Usage:
  python paper_b/heldout/build_pool.py [--out paper_b/heldout/pool_skeleton.csv]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import questionnaire_text as QT  # noqa: E402

WVS7 = REPO / "data" / "WVS" / "WVS_wave7.dta"
QMAP = REPO / "DPO_eval_WVS" / "question_map_wvs_edited.csv"
OVERRIDES = HERE / "overrides.json"
DEMOGRAPHIC_FROM = 260
Q_RE = re.compile(r"^Q(\d{1,3})$")

_ORDINAL_WORDS = (
    "important", "agree", "disagree", "confidence", "trust", "often", "never", "always",
    "likely", "satisfied", "much", "very", "justif", "member", "good", "bad", "interested",
    "worried", "frequently", "rarely", "sometimes", "satisf", "better", "worse", "more",
    "less", "fair", "unfair", "democratic", "free", "secure", "happy", "healthy", "proud",
    "close", "done", "might", "would never", "a lot", "none", "not at all", "completely",
    "all of the time", "probably", "definitely", "essential", "high", "low",
)


def mapped_items(path: Path = QMAP) -> set[str]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        return {row["Question"].strip() for row in csv.DictReader(fh)}


def _qnum(qid: str) -> int:
    return int(Q_RE.match(qid).group(1))


def select_pool(items: dict[str, dict], already_mapped: set[str] | None = None) -> list[str]:
    """items: qid -> {"codes": [...], "labels": [...]}; returns pool ids in Q order."""
    already_mapped = already_mapped if already_mapped is not None else {"Q57"}
    keep = []
    for qid in sorted(items, key=_qnum):
        if qid in already_mapped or _qnum(qid) >= DEMOGRAPHIC_FROM:
            continue
        codes = [int(c) for c in items[qid]["codes"]]
        if not 2 <= len(codes) <= 11:
            continue
        if codes != list(range(codes[0], codes[0] + len(codes))):
            continue
        keep.append(qid)
    return keep


def ordinal_guess(labels: list[str]) -> str:
    """TRUE when the codes plausibly form an ordered scale; REVIEW otherwise."""
    if len(labels) == 2:
        return "TRUE"                       # binary: E[code] is a share
    if any(re.fullmatch(r"\d{1,2}", str(l).strip()) for l in labels):
        return "TRUE"                       # numbered scale with labeled endpoints
    words = " ".join(str(l).lower() for l in labels)
    hits = sum(w in words for w in _ORDINAL_WORDS)
    return "TRUE" if hits >= 2 else "REVIEW"


def read_metadata(path: Path = WVS7) -> dict[str, dict]:
    import pyreadstat
    _, meta = pyreadstat.read_dta(str(path), metadataonly=True, encoding="latin1")
    out = {}
    for name, label in zip(meta.column_names, meta.column_labels):
        if not Q_RE.match(name):
            continue
        vl = meta.variable_value_labels.get(name) or {}
        pairs = sorted((int(float(k)), str(v)) for k, v in vl.items() if float(k) >= 0)
        out[name] = {"varlabel": (label or "").strip(),
                     "codes": [str(k) for k, _ in pairs],
                     "labels": [v.replace(";", ",").strip() for _, v in pairs]}
    return out


def build(out_path: Path) -> dict:
    meta = read_metadata()
    mapped = mapped_items()
    text = QT.extract()
    overrides = json.loads(OVERRIDES.read_text()) if OVERRIDES.is_file() else {}
    pool = select_pool(meta, mapped)
    rows, sources = [], {"questionnaire": 0, "varlabel": 0, "override": 0}
    for qid in pool:
        ov = overrides.get(qid, {})
        if ov.get("exclude"):
            continue
        if ov.get("StandaloneQuestion"):
            q, src = ov["StandaloneQuestion"], "override"
        elif len(text.get(qid, "")) >= 20:
            q, src = text[qid], "questionnaire"
        else:
            q, src = meta[qid]["varlabel"], "varlabel"
        sources[src] += 1
        ordinal = ov.get("ordinal") or ordinal_guess(meta[qid]["labels"])
        rows.append({
            "Question": qid, "ParentQuestion": qid,
            "ResponseType": f"heldout_{len(meta[qid]['codes'])}",
            "ResponseCodes": "; ".join(meta[qid]["codes"]),
            "ResponseLabels": "; ".join(meta[qid]["labels"]),
            "StandaloneQuestion": q, "gps_dimension": "",
            "VariableLabel": meta[qid]["varlabel"], "ordinal": ordinal, "text_source": src,
        })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summary = {
        "n_pool": len(rows), "text_sources": sources,
        "ordinal": {k: sum(r["ordinal"] == k for r in rows) for k in ("TRUE", "FALSE", "REVIEW")},
        "overlap_with_mapped": sorted({r["Question"] for r in rows} & mapped),
        "excluded_by_override": sorted(q for q, v in overrides.items() if v.get("exclude")),
    }
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(HERE / "pool_skeleton.csv"))
    a = ap.parse_args()
    s = build(Path(a.out))
    print(json.dumps(s, indent=1))
    print(f"-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
