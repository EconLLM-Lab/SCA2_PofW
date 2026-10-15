#!/usr/bin/env python3
"""Spot-check the USA Q57 logprob stitch claim."""
from pathlib import Path
import pandas as pd

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
canon = REPO / "DPO_eval_WVS/eval_results_wvs_wave7/model_option_probabilities_USA_adapter_on_USA.csv"
later = REPO / "data/phase2/raw/wvs/ksenias_base8/model_option_probabilities_USA_adapter_on_USA.csv"

def q57_code1(path: Path) -> float:
    df = pd.read_csv(path)
    hit = df[df["question_id"].astype(str).str.contains("Q57")]
    one = hit[hit["option_code"].astype(str).str.strip().isin(["1", "1.0"])]
    return float(one["option_logprob"].iloc[0]), int(len(hit)), list(df.columns)

print("canon", q57_code1(canon)[0], "rows", q57_code1(canon)[1])
print("later", q57_code1(later)[0], "rows", q57_code1(later)[1])
print("later_has_generated", any(c.startswith("generated_answer") for c in pd.read_csv(later, nrows=0).columns))
persona = REPO / "data/phase2/raw/wvs/persona_baseline/model_option_probabilities_persona_base_on_USA.csv"
pcols = list(pd.read_csv(persona, nrows=0).columns)
print("persona_cols_head", pcols[:15])
print("persona_has_generated", any(c.startswith("generated_answer") for c in pcols))
print("canon_has_generated", any(c.startswith("generated_answer") for c in pd.read_csv(canon, nrows=0).columns))
