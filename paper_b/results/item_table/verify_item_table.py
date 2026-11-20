#!/usr/bin/env python3
"""Verify the written item table."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit("usage: verify_item_table.py ITEM_CSV ITEM_MD")
p = Path(sys.argv[1])
with p.open(encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
print("n", len(rows))
print("wording", sum(r["wording_in_repo"] == "yes" for r in rows), sum(r["wording_in_repo"] != "yes" for r in rows))
print("status", sorted({r["status"] for r in rows}))
print("token", sorted({r["candidate_response_codes_equal_token_length"] for r in rows}))
for r in rows:
    print(r["wvs_id"], r["rectangle"], r["range_min"], r["range_max"], r["status"])
md = Path(sys.argv[2]).read_text()
print("md_has_q174", "Q174" in md)
print("md_has_not_in_repo", md.count("not in repo"))
print("md_lines", md.count("\n"))
