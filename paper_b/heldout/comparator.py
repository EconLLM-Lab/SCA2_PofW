#!/usr/bin/env python3
"""Face-valid comparator for the held-out screen (PREREGISTRATION.md section 6).

What a careful reader would do with the questionnaire alone: assign an item to a
GPS dimension only when its wording names that construct, and read the direction
off its response labels. No model output and no human response enter this file.

Fixed procedure (written 2026-10-14, before the rule was run on the pool):
  1. Text = StandaloneQuestion + VariableLabel, lower-cased.
  2. Dimension: the item matches a dimension when any stem in LEXICON[dimension]
     occurs as a word prefix. Exactly one matching dimension -> assigned; zero or
     two or more -> "none" (a reader would not commit).
  3. Direction: sign = +1 when a higher response code means more of the trait,
     -1 when it means less. Proposed by `propose_sign` from the code-1 label (an
     intensity word at code 1, e.g. "a great deal", "very", "agree strongly",
     "completely", "mentioned", means codes run from more to less -> -1); every
     assigned item is then read by a person, who may only confirm or flip the sign,
     or set the item to "none" when the wording's direction is not readable. Each
     change carries a written reason in comparator_review.json.
  4. The final table (face_valid.csv) is frozen with the selection (FREEZE.json).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
POOL = HERE / "pool_skeleton.csv"
REVIEW = HERE / "comparator_review.json"

LEXICON: dict[str, tuple[str, ...]] = {
    "trust": ("trust", "confidence", "honest", "reliab", "depend on"),
    "risktaking": ("risk", "adventur", "danger", "gambl", "uncertain", "secur"),
    "patience": ("patien", "future", "saving", "thrift", "long-term", "long term", "wait"),
    "altruism": ("help", "charit", "donat", "volunteer", "unselfish", "sacrific",
                 "care for", "humanitarian", "well-being of others", "welfare of others"),
    "posrecip": ("reciproc", "repay", "return a favo", "grateful", "gratitude"),
    "negrecip": ("revenge", "retaliat", "punish", "violen", "death penalty", "beat"),
}
_HIGH_FIRST = re.compile(
    r"^(a great deal|very|agree strongly|strongly agree|completely|always|mentioned|"
    r"a lot|trust completely|definitely|absolutely|highly|great|all of them|often)", re.I)


def match_dimensions(text: str) -> list[str]:
    t = text.lower()
    hits = []
    for dim, stems in LEXICON.items():
        if any(re.search(r"(?<![a-z])" + re.escape(s), t) for s in stems):
            hits.append(dim)
    return hits


def propose_sign(labels: list[str]) -> int:
    first = str(labels[0]).strip()
    return -1 if _HIGH_FIRST.match(first) else 1


def build(pool: pd.DataFrame, review: dict | None = None) -> pd.DataFrame:
    review = review or {}
    rows = []
    for _, r in pool.iterrows():
        text = f"{r.StandaloneQuestion} {r.VariableLabel}"
        hits = match_dimensions(text)
        dim = hits[0] if len(hits) == 1 else "none"
        labels = str(r.ResponseLabels).split("; ")
        sign = propose_sign(labels) if dim != "none" else 0
        rv = review.get(str(r.Question), {})
        if rv.get("action") == "flip" and dim != "none":
            sign = -sign
        elif rv.get("action") == "none":
            dim, sign = "none", 0
        rows.append({"question_id": str(r.Question), "dimension": dim, "sign": sign,
                     "lexicon_hits": ";".join(hits), "code1_label": labels[0],
                     "codeN_label": labels[-1], "review": rv.get("action", ""),
                     "review_reason": rv.get("reason", ""),
                     "variable_label": r.VariableLabel})
    return pd.DataFrame(rows)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="face-valid comparator table")
    ap.add_argument("--out", default=str(HERE / "face_valid.csv"))
    a = ap.parse_args()
    review = json.loads(REVIEW.read_text()) if REVIEW.is_file() else {}
    df = build(pd.read_csv(POOL), review)
    df.to_csv(a.out, index=False)
    a_ = df[df.dimension != "none"]
    print(f"pool {len(df)} | assigned {len(a_)} | by dimension {a_.dimension.value_counts().to_dict()} "
          f"| ambiguous {(df.lexicon_hits.str.count(';') >= 1).sum()} -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
