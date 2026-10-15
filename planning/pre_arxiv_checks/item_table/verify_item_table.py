#!/usr/bin/env python3
"""Verify the written item table."""
from __future__ import annotations

import csv
from pathlib import Path

p = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/item_table/item_measurement_table.csv")
with p.open(encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
print("n", len(rows))
print("wording", sum(r["wording_in_repo"] == "yes" for r in rows), sum(r["wording_in_repo"] != "yes" for r in rows))
print("status", sorted({r["status"] for r in rows}))
print("token", sorted({r["candidate_response_codes_equal_token_length"] for r in rows}))
for r in rows:
    print(r["wvs_id"], r["rectangle"], r["range_min"], r["range_max"], r["status"])
md = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/item_table/ITEM_TABLE.md").read_text()
print("md_has_q174", "Q174" in md)
print("md_has_not_in_repo", md.count("not in repo"))
print("md_lines", md.count("\n"))
