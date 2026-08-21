#!/usr/bin/env python3
"""_dump_items.py — dump the trust-dimension item roster (question_id, text, type, section)
and the full dimension roster, to ground the trust-target classification."""
import pathlib
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[2]
df = pd.read_parquet(REPO / "analysis" / "phase2" / "outputs" / "wvs_question_metrics_long.parquet")

print("=== TRUST items ===")
t = (df[df["gps_dimension"] == "trust"]
       .groupby(["question_id", "question_text", "response_type", "Section"])
       .size().reset_index().sort_values("question_id"))
print(t.to_string(index=False))

print("\n=== all mapped items by dimension ===")
allq = (df[df["gps_dimension"].notna()]
          .groupby(["gps_dimension", "question_id"]).size()
          .reset_index().pivot(index="question_id", columns="gps_dimension", values=0))
print(allq.fillna("").to_string())
