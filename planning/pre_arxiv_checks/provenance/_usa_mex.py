"""Resolve USA/MEX adapter source and compare canonical vs persona scoring artifacts."""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
OUT = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/provenance/_usa_mex_report.json")
RAW = REPO / "data/phase2/raw/wvs"
CANON = REPO / "DPO_eval_WVS/eval_results_wvs_wave7"
SCORES = REPO / "analysis/phase2/outputs/paper_a/country_item_scores.csv"
GPS = REPO / "synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json"
PANEL = ["ARG","BRA","CHN","DEU","EGY","GBR","GRC","IDN","IND","JPN","MEX","NGA","NLD","RUS","TUR","USA"]
TRUST9 = ["Q57","Q58","Q59","Q60","Q61","Q62","Q63","Q64","Q73"]
INVERT = {"Q59","Q61","Q62","Q63","Q64","Q58","Q60","Q73"}
BASE8 = {"ARG","CHN","DEU","GBR","JPN","MEX","RUS","USA"}


def recode(raw, item):
    s = float(raw)
    if item in INVERT:
        return 5.0 - s
    if item == "Q57":
        return 1.0 if s == 1.0 else 0.0
    return s


def item_score(df, q):
    d = df[df.question_id == q]
    if d.empty:
        return np.nan
    pm = d.model_prob.to_numpy(float)
    raw = d.option_value.to_numpy(float)
    pm = pm / pm.sum()
    rec = np.array([recode(v, q) for v in raw])
    return float((rec * pm).sum())


def sysblock(text):
    m = re.search(r"<\|start_header_id\|>system<\|end_header_id\|>(.*?)<\|eot_id\|>", str(text), re.S)
    return m.group(1) if m else None


def rest(text):
    parts = str(text).split(". ", 1)
    return parts[1] if len(parts) == 2 else str(text)


def load(path):
    return pd.read_csv(path)


def main():
    scores = pd.read_csv(SCORES)
    z = json.loads(GPS.read_text())
    report = {}

    sources = {
        "usamex_repo": CANON / "model_option_probabilities_USA_adapter_on_USA.csv",
        "usamex_raw": RAW / "usamex_canonical" / "model_option_probabilities_USA_adapter_on_USA.csv",
        "ksenias_USA": RAW / "ksenias_base8" / "model_option_probabilities_USA_adapter_on_USA.csv",
        "usamex_MEX_repo": CANON / "model_option_probabilities_MEX_adapter_on_MEX.csv",
        "ksenias_MEX": RAW / "ksenias_base8" / "model_option_probabilities_MEX_adapter_on_MEX.csv",
    }
    # also search raw usamex
    raw_usamex = list((RAW / "usamex_canonical").glob("model_option_probabilities_*adapter_on_*.csv")) if (RAW / "usamex_canonical").exists() else []
    report["raw_usamex_files"] = [p.name for p in raw_usamex]

    comparisons = []
    for label, path in sources.items():
        rec = {"label": label, "exists": path.exists(), "path": str(path.relative_to(REPO)) if path.exists() else str(path)}
        if not path.exists():
            comparisons.append(rec)
            continue
        df = load(path)
        rec["n"] = len(df)
        rec["cols_have_prompt"] = "prompt_text" in df.columns
        rec["model"] = str(df.model.iloc[0]) if "model" in df.columns else None
        if "prompt_text" in df.columns:
            q = df[df.question_id == "Q57"].iloc[0]
            rec["first"] = str(q.prompt_text).split(". ", 1)[0]
            rec["system"] = sysblock(q.complete_prompt_model_received) if "complete_prompt_model_received" in df.columns else None
            rec["today"] = "26 Jul 2024" in str(q.get("complete_prompt_model_received", ""))
            rec["prompt_country"] = None if pd.isna(q.prompt_country) else str(q.prompt_country)
            rec["q57_tokens"] = {
                str(int(r.option_code)): int(r.option_token_count)
                for r in df[df.question_id == "Q57"].itertuples()
            }
        cc = "USA" if "USA_adapter" in path.name else "MEX"
        item_abs = []
        for qid in TRUST9:
            recon = item_score(df, qid)
            fr = scores[(scores.arm == "adapter") & (scores.country == cc) & (scores.item == qid)]
            if fr.empty:
                continue
            item_abs.append(abs(recon - float(fr.iloc[0].raw)))
        rec["max_abs_vs_frozen_adapter_trust9"] = max(item_abs) if item_abs else None
        rec["mean_abs"] = float(np.mean(item_abs)) if item_abs else None
        comparisons.append(rec)
    report["comparisons"] = comparisons

    # rebuild 16 composites with precedence usamex > ksenias > co2 for USA/MEX
    def adapter_path(c):
        if c in {"USA", "MEX"}:
            for p in [
                CANON / f"model_option_probabilities_{c}_adapter_on_{c}.csv",
                RAW / "usamex_canonical" / f"model_option_probabilities_{c}_adapter_on_{c}.csv",
                RAW / "ksenias_base8" / f"model_option_probabilities_{c}_adapter_on_{c}.csv",
            ]:
                if p.exists():
                    return p
        bank = "ksenias_base8" if c in BASE8 else "co2_8"
        return RAW / bank / f"model_option_probabilities_{c}_adapter_on_{c}.csv"

    comps = {}
    used = {}
    for c in PANEL:
        p = adapter_path(c)
        df = pd.read_csv(p, usecols=["question_id", "option_value", "model_prob"])
        comps[c] = float(np.mean([item_score(df, q) for q in TRUST9]))
        used[c] = str(p.relative_to(REPO))
    z16 = pd.Series({c: float(z[c]["trust"]) for c in PANEL})
    a = pd.Series(comps)
    report["precedence_rho"] = float(spearmanr(a.reindex(PANEL), z16).statistic)
    report["files_used"] = used
    frozen = scores[(scores.arm == "adapter") & (scores.item.isin(TRUST9))].groupby("country").raw.mean()
    delta = (frozen.reindex(PANEL) - a.reindex(PANEL)).abs()
    report["precedence_vs_frozen_max_abs"] = float(delta.max())
    report["precedence_vs_frozen"] = delta.round(8).to_dict()

    # if still mismatch, try canonical combined file models
    # compare logprobs USA adapter Q57 between canon and ksenias
    def q57_logprobs(path):
        df = pd.read_csv(path)
        d = df[df.question_id == "Q57"][["option_code", "option_logprob", "model_prob", "option_token_count"]]
        return d.to_dict(orient="records")
    report["q57_logprobs"] = {}
    for label, path in sources.items():
        if path.exists():
            report["q57_logprobs"][label] = q57_logprobs(path)

    OUT.write_text(json.dumps(report, indent=2, default=str))
    print("precedence rho", report["precedence_rho"], "max abs", report["precedence_vs_frozen_max_abs"])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
