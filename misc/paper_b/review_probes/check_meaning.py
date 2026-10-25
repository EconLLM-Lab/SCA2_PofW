#!/usr/bin/env python3
"""CP26-MV probe 2: for every claim id whose containing sentence was rewritten, print the old
(HEAD) and new (worktree) sentence side by side so the verifier can judge whether estimand,
direction and interval are unchanged.

Usage: python check_meaning.py [--files F ...]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
ID_RE = re.compile(r"\{(v|lo|hi|n|pct|abs)?\}")  # unused placeholder

# \cl{printed}{id[:field]} / \ci{lo}{hi}{id}
CL = re.compile(r"\\cl\{[^{}]*\}\{([^{}]*)\}")
CI = re.compile(r"\\ci\{[^{}]*\}\{[^{}]*\}\{([^{}]*)\}")
SENT = re.compile(r"(?<=[.!?])\s+")


def git_show(path: str) -> str:
    r = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=PAPER, capture_output=True, text=True)
    if r.returncode != 0:
        return ""
    return r.stdout


def sentences_with_ids(text: str):
    """Map claim id -> list of sentences containing it (macro args stripped for comparison)."""
    clean = re.sub(r"%.*", "", text)
    clean = re.sub(r"\s+", " ", clean)
    out = {}
    for sent in SENT.split(clean):
        ids = set(CL.findall(sent)) | set(CI.findall(sent))
        plain = CL.sub("<NUM>", sent)
        plain = CI.sub("<CI>", plain)
        for cid in ids:
            out.setdefault(cid, []).append(plain.strip())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="+", default=[
        "abstract.tex", "background.tex", "conclusion.tex", "design.tex", "discussion.tex",
        "instrument.tex", "introduction.tex", "results.tex",
        "tables/tab_checks.tex", "tables/tab_comparators.tex",
        "tables/tab_factorial.tex", "tables/tab_human.tex",
        "supplement.tmpl.tex",
    ])
    args = ap.parse_args()
    n_pairs = 0
    for f in args.files:
        old = sentences_with_ids(git_show(f"misc/paper_b/{f}"))
        new = sentences_with_ids((PAPER / f).read_text())
        for cid in sorted(set(old) | set(new)):
            o, n = old.get(cid, []), new.get(cid, [])
            # normalize the comparison: macro-stripped sentences
            if [s.strip() for s in o] == [s.strip() for s in n]:
                continue
            n_pairs += 1
            print(f"### {f} :: {cid}")
            for s in o:
                print(f"  OLD: {s}")
            for s in n:
                print(f"  NEW: {s}")
            print()
    print(f"--- {n_pairs} rewritten claim-id sentences across {len(args.files)} files")
    sys.exit(0)


if __name__ == "__main__":
    main()
