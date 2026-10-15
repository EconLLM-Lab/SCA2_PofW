#!/usr/bin/env python3
"""Where do same-wave item scores disagree with the frozen adapter arm?"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

# reuse the loader by importing the previous script's functions
import importlib.util
spec = importlib.util.spec_from_file_location(
    "sw", "/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/same_wave_full.py"
)
sw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sw)

scores = pd.concat([sw.load_country(c) for c in sw.PANEL], ignore_index=True)
frozen = pd.read_csv(sw.FROZEN)
fr = frozen[(frozen.arm == "adapter") & (frozen.country.isin(sw.PANEL))]
m = scores.merge(fr[["country", "item", "dimension", "raw"]], on=["country", "item"], suffixes=("_wave", "_frozen"))
m["delta"] = m.raw_wave - m.raw_frozen
bad = m[m.delta.abs() > 1e-6]
print("n_compared", len(m), "n_disagree", len(bad))
print("disagree_countries", sorted(bad.country.unique()))
print("disagree_items", sorted(bad.item.unique()))
print(bad.groupby("item").delta.agg(["count", "max", "min"]).to_string())
print("--- ARG trust ---")
print(m[(m.country == "ARG") & (m.item.isin(sw.ITEMS["trust"]))][["item", "raw_wave", "raw_frozen", "delta"]].to_string(index=False))
print("--- ARG any bad ---")
print(bad[bad.country == "ARG"][["item", "raw_wave", "raw_frozen", "delta"]].head(20).to_string(index=False))
