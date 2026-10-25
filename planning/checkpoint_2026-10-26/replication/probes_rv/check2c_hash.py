#!/usr/bin/env python3
"""RV check 2c: recompute the 6 HASH_* rows of NUMBERS_TABLE.csv, my own code.

The HASH rows pin (a) the working-tree sha256 of the held-out pool skeleton, (b) its git blob at HEAD (LF),
(c/d) its git blob at tag `prereg-heldout-2026-10-14` (LF and the CRLF form the preregistration records),
(e) overrides.json and (f) the frozen selection. My own hashlib + `git show`; no paper_b import.
Working-tree files are read from the *live* repo (the card allows everything outside data/ and the human
replication dir; these are design/provenance files, not respondent data).
Prints only `0 mismatches` or the mismatching keys.
"""
import csv, hashlib, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TABLE = ROOT / "planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv"
TAG = "prereg-heldout-2026-10-14"
POOL = "paper_b/heldout/pool_skeleton.csv"

def sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def git_show(ref: str) -> bytes:
    r = subprocess.run(["git", "show", ref], capture_output=True, cwd=ROOT, check=True)
    return r.stdout

def main():
    work = (ROOT / POOL).read_bytes()
    blob = git_show(f"HEAD:{POOL}")
    tag_blob = git_show(f"{TAG}:{POOL}")
    crlf = tag_blob.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    mine = {
        "HASH_pool_worktree": sha(work),
        "HASH_pool_git_blob_lf": sha(blob),
        "HASH_pool_pre_amendment_crlf": sha(crlf),
        "HASH_pool_pre_amendment_lf": sha(tag_blob),
        "HASH_overrides": sha((ROOT / "paper_b/heldout/overrides.json").read_bytes()),
        "HASH_selection_amended_20261016": sha((ROOT / "paper_b/heldout/selection_amended_20261016.csv").read_bytes()),
    }
    ns = {"HASH_pool_worktree": len(work), "HASH_pool_git_blob_lf": len(blob),
          "HASH_pool_pre_amendment_crlf": len(crlf), "HASH_pool_pre_amendment_lf": len(tag_blob),
          "HASH_overrides": -1, "HASH_selection_amended_20261016": -1}
    bad = []
    for r in csv.DictReader(TABLE.open()):
        cid = r["claim_id"]
        if cid in mine:
            if r["value"] != mine[cid] or (ns[cid] >= 0 and int(r["n"]) != ns[cid]):
                bad.append(f"{cid} (mine {mine[cid][:12]} n={ns[cid]}, tracked {r['value'][:12]} n={r['n']})")
    print("0 mismatches" if not bad else "mismatches:\n  " + "\n  ".join(bad))
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())