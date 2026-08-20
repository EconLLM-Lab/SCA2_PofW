#!/usr/bin/env python3
"""_inspect_wvs_parquet.py — schema of data/wvs_eval_full/*.parquet (one file)."""
import pathlib
import sys

import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[2]
f = sys.argv[1] if len(sys.argv) > 1 else REPO / "data" / "wvs_eval_full" / "USA_WVS_wave7.parquet"
df = pd.read_parquet(f)
print(f"file: {f}")
print(f"shape: {df.shape}")
print("columns:", list(df.columns)[:40])
print("dtypes:", df.dtypes.astype(str).to_dict() if df.shape[1] < 60 else "many cols")
print(df.head(3).to_string())
