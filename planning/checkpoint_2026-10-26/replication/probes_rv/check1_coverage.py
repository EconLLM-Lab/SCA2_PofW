#!/usr/bin/env python3
"""RV check 1: coverage of every NUMBERS_TABLE.csv claim_id by the two replication cards.

Independent classifier: no import from paper_b, no reuse of RP1/RP2 code.
RP1 families come from MANIFEST_model_only.md (table "Commands per result file" +
"Families left to RP2"); RP2 families from MANIFEST_human.md (its scope paragraph).
The RO_* family is shared (counted by both cards) -- allowed, but every other claim_id
must fall in exactly one card, and no claim_id may be left out or double-assigned.
Also cross-checks RP2's own scope rule (output_file endswith one of its 8 result files)
against the prefix families, and each card's per-family count against its report table.
Prints PASS or the failing claim ids.
"""
import csv, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TABLE = ROOT / "planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv"
EXPECTED_SHA = "71ee7c8c"

RP1 = ["B2_", "FX_", "FX26_", "RP_", "NZ_", "RO_", "HASH_", "PX_", "C9_W1_", "C9_label_recovery_"]
# RP2's own FAMILIES tuple (compare_results_human.py line 71) -- RO_ is shared with RP1
RP2 = ["SCR_", "PD_", "CMP_", "SP_", "RO_", "C9_a_", "C9_b_", "C9_c_", "C9_d_", "C9_e_", "C9_f_", "C9_TVD_"]
# counts printed in each card's report table (REPLICATION_model_only.md / REPLICATION_human.md)
RP1_COUNTS = {"B2_": 30, "FX_": 58, "FX26_": 4, "RP_": 17, "NZ_": 32, "RO_": 9,
              "HASH_": 6, "PX_": 46, "C9_W1_": 66, "C9_label_recovery_": 8}
RP2_COUNTS = {"SCR_": 25, "PD_": 27, "CMP_": 10, "SP_": 7, "RO_": 9, "C9_a_": 21,
              "C9_b_": 14, "C9_c_": 60, "C9_d_": 21, "C9_e_": 42, "C9_f_": 9, "C9_TVD_": 50}
RP2_SCOPE_SUFFIXES = ("screen_result.json", "heldout_analysis.json", "heldout_per_dimension.json",
                      "selection_heldout_reverse.csv", "selection_heldout_para_a.csv",
                      "selection_heldout_para_b.csv", "c9_human_agreement.json", "c9_tvd.json")
RP1_ONLY_FILES = {"bank2_transport_strict.json", "factorial_report.json", "replicate_analysis.json",
                  "near_zero_analysis.json", "persona_strict.json", "w1_why_trust.json",
                  "c9_label_recovery.json"}

def main():
    import hashlib
    sha = hashlib.sha256(TABLE.read_bytes()).hexdigest()
    problems = []
    if not sha.startswith(EXPECTED_SHA):
        problems.append(f"table sha {sha[:16]} != locked {EXPECTED_SHA}")
    rows = list(csv.DictReader(TABLE.open()))
    if len(rows) != 562:
        problems.append(f"table has {len(rows)} rows, expected 562")
    ids = [r["claim_id"] for r in rows]
    if len(set(ids)) != len(ids):
        dup = [k for k, n in Counter(ids).items() if n > 1]
        problems.append(f"duplicate claim_id: {dup}")

    counts, owners, unassigned = Counter(), {}, []
    rp1_counts, rp2_counts = Counter(), Counter()
    for cid in ids:
        fams = [f for f in RP1 + RP2 if cid.startswith(f)]
        cards = {("RP1" if f in RP1 else "RP2") for f in fams}
        if not fams:
            unassigned.append(cid); continue
        if len(cards) != 1 and not (fams == ["RO_"]):
            # RO_ is the only family both cards count; anything else double-owned is a problem
            problems.append(f"{cid} assigned to {sorted(cards)}")
        owners[cid] = cards
        for f in fams:
            counts[f] += 1
        f1 = next((f for f in RP1 if cid.startswith(f)), None)
        f2 = next((f for f in RP2 if cid.startswith(f)), None)
        if f1: rp1_counts[f1] += 1
        if f2: rp2_counts[f2] += 1
    if unassigned:
        problems.append(f"unassigned claim ids (no family, no out-of-scope reason): {unassigned}")

    for fam, n in RP1_COUNTS.items():
        if rp1_counts[fam] != n:
            problems.append(f"RP1 family {fam}: table has {rp1_counts[fam]}, report says {n}")
    for fam, n in RP2_COUNTS.items():
        if rp2_counts[fam] != n:
            problems.append(f"RP2 family {fam}: table has {rp2_counts[fam]}, report says {n}")
    rp1_rows = sum(RP1_COUNTS.values()); rp2_rows = sum(RP2_COUNTS.values())
    if rp1_rows != 276: problems.append(f"RP1 in-scope total {rp1_rows} != 276")
    if rp2_rows != 295: problems.append(f"RP2 in-scope total {rp2_rows} != 295")
    if rp1_rows + rp2_rows - RP1_COUNTS["RO_"] != 562:
        problems.append("276 + 295 - 9 shared != 562")

    # cross-check: RP2's file-based scope vs its prefix families (their coverage rule, both ways)
    file_scope = {cid for cid, r in zip(ids, rows) if r["output_file"].endswith(RP2_SCOPE_SUFFIXES)}
    prefix_scope = {cid for cid in ids if any(cid.startswith(f) for f in RP2)}
    if file_scope != prefix_scope:
        problems.append(f"RP2 file-scope vs prefix-scope differ: {sorted(file_scope ^ prefix_scope)[:8]}")
    # and the RP1-only result files: rows reading them must all be RP1 prefixes
    for cid, r in zip(ids, rows):
        base = r["output_file"].rsplit("/", 1)[-1]
        if base in RP1_ONLY_FILES and not any(cid.startswith(f) for f in RP1):
            problems.append(f"{cid} reads RP1 file {base} but is not an RP1 family")

    print(f"rows 562? {len(rows) == 562}; RP1 families: " +
          ", ".join(f"{f}{rp1_counts[f]}" for f in RP1) +
          f" (total {sum(rp1_counts.values())}); RP2 families: " +
          ", ".join(f"{f}{rp2_counts[f]}" for f in RP2) +
          f" (total {sum(rp2_counts.values())}, RO_ shared with RP1)")
    if problems:
        print("PROBLEMS:")
        for p in problems: print("  " + p)
        return 1
    print("COVERAGE PASS: every claim_id in exactly one card (RO_ shared), "
          "all report counts match, RP2 file-scope == prefix-scope")
    return 0

if __name__ == "__main__":
    sys.exit(main())