#!/usr/bin/env python3
"""Statistical-similarity audit of a second A/B bank against bank 1 (text only, no model).

Bank 2 is a fresh stochastic draw from the same generator, so it is judged by
distribution, not bytes. Each check is descriptive; the FLAGS are pre-declared
here (2026-10-14, before bank 2 finished) so the verdict is not tuned to the result.

  counts       per-dimension share; flag if any dimension differs by > 3 points
  lengths      prompt / response_a / response_b word counts; two-sample KS per field,
               flag if the median differs by > 15%
  ab_length    median (len A - len B): A is the chosen side for z >= 0, so a length
               asymmetry is a label-correlated nuisance; flag if banks differ by > 5 words
  near_dups    share of prompts whose word-5-gram Jaccard with another prompt in the
               same bank is >= 0.5; flag if bank 2 exceeds bank 1 by > 5 points
  overlap      share of bank-2 prompts with Jaccard >= 0.5 against any bank-1 prompt
               (should be small; flag if > 5%)
  vocabulary   Jaccard of the two banks' word types (descriptive only)

Usage:
  python paper_b/bank_similarity.py --bank1 <triplets_bank.jsonl> --bank2 <jsonl> [--out audit.json]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter
from pathlib import Path

DIMS = ["trust", "risktaking", "patience", "altruism", "posrecip", "negrecip"]
WORD = re.compile(r"[a-z']+")
FLAG = {"share_pts": 3.0, "median_rel": 0.15, "ab_words": 5.0, "dup_pts": 5.0, "overlap": 0.05}


def load(path: Path) -> list[dict]:
    rows = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    for r in rows:
        if r.get("gps_dimension") not in DIMS:
            raise ValueError(f"{path}: unknown dimension {r.get('gps_dimension')!r}")
    return rows


def words(s: str) -> list[str]:
    return WORD.findall(str(s).lower())


def shingles(s: str, k: int = 5) -> set:
    w = words(s)
    return {tuple(w[i:i + k]) for i in range(max(1, len(w) - k + 1))}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def ks(x: list[float], y: list[float]) -> tuple[float, float]:
    """Two-sample KS statistic and asymptotic p-value (no scipy dependency)."""
    import math
    xs, ys = sorted(x), sorted(y)
    n, m = len(xs), len(ys)
    i = j = 0
    d = 0.0
    while i < n and j < m:
        v = min(xs[i], ys[j])
        while i < n and xs[i] <= v:
            i += 1
        while j < m and ys[j] <= v:
            j += 1
        d = max(d, abs(i / n - j / m))
    en = math.sqrt(n * m / (n + m))
    lam = (en + 0.12 + 0.11 / en) * d
    if lam < 0.3:            # series is unstable near 0; Q_KS(0.3) > 0.9999
        return d, 1.0
    p = 2 * sum((-1) ** (k - 1) * math.exp(-2 * k * k * lam * lam) for k in range(1, 101))
    return d, float(min(1.0, max(0.0, p)))


def near_dup_share(rows: list[dict], thr: float = 0.5) -> float:
    sh = [shingles(r["prompt"]) for r in rows]
    hit = [False] * len(sh)
    for i in range(len(sh)):
        for j in range(i + 1, len(sh)):
            if jaccard(sh[i], sh[j]) >= thr:
                hit[i] = hit[j] = True
    return sum(hit) / len(hit) if hit else 0.0


def audit(b1: list[dict], b2: list[dict]) -> dict:
    out: dict = {"n": {"bank1": len(b1), "bank2": len(b2)}, "flags": []}
    c1, c2 = Counter(r["gps_dimension"] for r in b1), Counter(r["gps_dimension"] for r in b2)
    out["counts"] = {d: {"bank1": c1[d], "bank2": c2[d],
                         "share_diff_pts": round(100 * (c2[d] / len(b2) - c1[d] / len(b1)), 2)}
                     for d in DIMS}
    for d, v in out["counts"].items():
        if abs(v["share_diff_pts"]) > FLAG["share_pts"]:
            out["flags"].append(f"counts:{d}")
    out["lengths"] = {}
    for f in ("prompt", "response_a", "response_b"):
        x = [len(words(r[f])) for r in b1]
        y = [len(words(r[f])) for r in b2]
        d, p = ks(x, y)
        m1, m2 = statistics.median(x), statistics.median(y)
        out["lengths"][f] = {"median1": m1, "median2": m2, "ks_d": round(d, 3), "ks_p": round(p, 4)}
        if abs(m2 - m1) / m1 > FLAG["median_rel"]:
            out["flags"].append(f"lengths:{f}")
    ab1 = statistics.median(len(words(r["response_a"])) - len(words(r["response_b"])) for r in b1)
    ab2 = statistics.median(len(words(r["response_a"])) - len(words(r["response_b"])) for r in b2)
    out["ab_length"] = {"bank1": ab1, "bank2": ab2}
    if abs(ab2 - ab1) > FLAG["ab_words"]:
        out["flags"].append("ab_length")
    nd1, nd2 = near_dup_share(b1), near_dup_share(b2)
    out["near_dups"] = {"bank1": round(nd1, 4), "bank2": round(nd2, 4)}
    if 100 * (nd2 - nd1) > FLAG["dup_pts"]:
        out["flags"].append("near_dups")
    sh1 = [shingles(r["prompt"]) for r in b1]
    cross = sum(any(jaccard(shingles(r["prompt"]), s) >= 0.5 for s in sh1) for r in b2) / len(b2)
    out["overlap_bank2_with_bank1"] = round(cross, 4)
    if cross > FLAG["overlap"]:
        out["flags"].append("overlap")
    v1 = {w for r in b1 for f in ("prompt", "response_a", "response_b") for w in words(r[f])}
    v2 = {w for r in b2 for f in ("prompt", "response_a", "response_b") for w in words(r[f])}
    out["vocabulary_jaccard"] = round(jaccard(v1, v2), 4)
    out["thresholds"] = FLAG
    out["verdict"] = "similar" if not out["flags"] else "review"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="bank-2 vs bank-1 similarity audit")
    ap.add_argument("--bank1", required=True)
    ap.add_argument("--bank2", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = audit(load(Path(a.bank1)), load(Path(a.bank2)))
    text = json.dumps(res, indent=1)
    if a.out:
        Path(a.out).write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
