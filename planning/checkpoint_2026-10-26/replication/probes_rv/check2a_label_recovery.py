#!/usr/bin/env python3
"""RV check 2a: recompute the 8 C9_label_recovery_* rows of NUMBERS_TABLE.csv, my own code.

Input: the RP1 re-run result file `.replication_2026-10-25/model_only/rtree/.../results/c9/c9_label_recovery.json`
(per-country recovery / accuracy / base_accuracy / mean_margin_shift over 42 countries, each over its 132
held-out pairs, plus each country's sign profile_id). Nothing else is needed: the cohort row is the
country-equal mean, and the intervals are the percentile bootstrap described in the producer
(pairs -> per-country rates; profile-block bootstrap = 26 profiles redrawn with replacement, all member
countries moving together; country bootstrap = 42 countries redrawn with replacement; 2000 draws;
recorded seeds). My own bootstrap implementation mirrors that documented procedure and the recorded seeds
-- no paper_b import, no RP1 code.

Prints only `0 mismatches` or the mismatching keys.
"""
import csv, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
RTREE = ROOT / ".replication_2026-10-25/model_only/rtree"
JSON = RTREE / "planning/sprint_2026-10-11/paper-b-tier1/results/c9/c9_label_recovery.json"
TABLE = ROOT / "planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv"
TOL = 1e-12          # seeded bootstrap, mirrored RNG stream -> expect bit-exact

def bootstrap_mean(x, clusters, draws, seed):
    rng = np.random.default_rng(seed)
    if clusters is None:
        idx = rng.integers(0, len(x), size=(draws, len(x)))
        means = x[idx].mean(axis=1)
    else:
        uniq = list(dict.fromkeys(clusters))            # first-appearance order (== sorted country order here)
        pos = {c: np.where(np.asarray(clusters) == c)[0] for c in uniq}
        pick = rng.integers(0, len(uniq), size=(draws, len(uniq)))
        means = np.array([x[np.concatenate([pos[uniq[j]] for j in pick[i]])].mean() for i in range(draws)])
    lo, hi = np.quantile(means, [0.025, 0.975])
    return float(lo), float(hi)

def main():
    d = json.loads(JSON.read_text())
    cs = sorted(d["countries"])
    assert len(cs) == d["n_countries"] == 42
    prof = [d["countries"][c]["profile_id"] for c in cs]
    assert d["n_profiles"] == len(set(prof)) == 26, (d["n_profiles"], len(set(prof)))
    draws, seed_pb, seed_ct = d["draws"], d["seed_profile_block"], d["seed_country"]
    mine = {}
    for m in ("recovery", "accuracy", "base_accuracy", "mean_margin_shift"):
        x = np.array([d["countries"][c][m] for c in cs], float)
        point = float(x.mean())
        for unit, cl, seed in (("profile_block", prof, seed_pb), ("country", None, seed_ct)):
            lo, hi = bootstrap_mean(x, cl, draws, seed)
            mine[f"C9_label_recovery_{m}_{unit}"] = (point, float(lo), float(hi))
    # tracked rows
    bad = []
    for r in csv.DictReader(TABLE.open()):
        cid = r["claim_id"]
        if cid in mine:
            p, lo, hi = mine[cid]
            got = (float(r["value"]), float(r["ci_low"]), float(r["ci_high"]), int(r["n"]))
            want = (p, lo, hi, 42)
            if any(abs(a - b) > TOL for a, b in zip(got[:3], want[:3])) or got[3] != want[3]:
                bad.append(f"{cid} (mine {want}, tracked {got})")
    print("0 mismatches" if not bad else "mismatches:\n  " + "\n  ".join(bad))
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())