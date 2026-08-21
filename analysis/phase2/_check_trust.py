#!/usr/bin/env python3
"""quick check: reconcile trust movement vs composite correlation."""
import pandas as pd
from scipy.stats import spearmanr

wvs = pd.read_parquet("analysis/phase2/outputs/wvs_question_metrics_long.parquet")
gps = pd.read_stata("data/GPS/GPS_dataset_country_level/country_gps.dta").set_index("isocode")
TRUST_ITEMS = [f"Q{i}" for i in [57, 59, 61, 62, 63, 64, 69, 70, 71, 58, 60, 73]]

m = wvs[(wvs["relationship"] == "matched") & (wvs["is_adapter"]) &
        (wvs["gps_dimension"] == "trust") & (wvs["question_id"].isin(TRUST_ITEMS))]
comp = m.groupby("eval_country")["model_mean"].mean()
z = gps.loc[comp.index, "trust"]
print("Spearman(composite_raw, trust z):", round(spearmanr(comp, z).statistic, 3))
print("Pearson(composite_raw, z):", round(comp.corr(z), 3))

b = wvs[(wvs["model"] == "base") & (wvs["gps_dimension"] == "trust") &
        (wvs["question_id"].isin(TRUST_ITEMS))]
bcomp = b.groupby(["bank", "eval_country"])["model_mean"].mean()
print("\nbase trust composite by (bank,country):")
print(bcomp.round(4).to_string())

# movement recomputed: comp_raw - base_const (population cancels)
base_const = bcomp.mean()  # constant across countries IF identical
print("\nbase composite range:", round(bcomp.min(), 4), "to", round(bcomp.max(), 4))
print("base composite nunique:", bcomp.nunique())

mov = comp - bcomp.mean()
print("\nSpearman(movement, z):", round(spearmanr(mov, z).statistic, 3))
print("\ncomposite per country (raw trust means):")
print(pd.concat([comp.round(3), z.round(3)], axis=1).to_string())
