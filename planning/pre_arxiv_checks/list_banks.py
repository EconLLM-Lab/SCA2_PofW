#!/usr/bin/env python3
"""Which saved scoring banks contain which adapter countries."""
from pathlib import Path
import pandas as pd

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
banks = {
    "usamex_canonical": REPO / "DPO_eval_WVS/eval_results_wvs_wave7",
    "ksenias_base8": REPO / "data/phase2/raw/wvs/ksenias_base8",
    "co2_8": REPO / "data/phase2/raw/wvs/co2_8",
}
for name, d in banks.items():
    files = sorted(d.glob("model_option_probabilities_*adapter*.csv"))
    countries = []
    for f in files:
        stem = f.name.replace("model_option_probabilities_", "").replace(".csv", "")
        countries.append(stem)
    print(f"\n{name} adapter-like files: {len(files)}")
    for c in countries:
        print(" ", c)
