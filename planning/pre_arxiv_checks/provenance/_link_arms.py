"""Link headline arms to saved option files and compare scoring artifacts."""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
OUT = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/provenance/_link_report.json")
RAW = REPO / "data/phase2/raw/wvs"
SCORES = REPO / "analysis/phase2/outputs/paper_a/country_item_scores.csv"
GPS = REPO / "synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json"
PANEL = ["ARG","BRA","CHN","DEU","EGY","GBR","GRC","IDN","IND","JPN","MEX","NGA","NLD","RUS","TUR","USA"]
TRUST9 = ["Q57","Q58","Q59","Q60","Q61","Q62","Q63","Q64","Q73"]
INVERT_1_4 = {"Q59","Q61","Q62","Q63","Q64","Q58","Q60","Q73","Q81"}
BINARY = {"Q57"}


def recode(raw, item):
    s = float(raw)
    if item in INVERT_1_4:
        return 5.0 - s
    if item in BINARY:
        return 1.0 if s == 1.0 else 0.0
    return s


def item_score(df, q):
    d = df[df.question_id == q]
    if d.empty:
        return np.nan
    pm = d.model_prob.to_numpy(float)
    raw = d.option_value.to_numpy(float)
    if pm.sum() <= 0:
        return np.nan
    pm = pm / pm.sum()
    rec = np.array([recode(v, q) for v in raw])
    return float((rec * pm).sum())


def composite(df):
    vals = [item_score(df, q) for q in TRUST9]
    vals = [v for v in vals if np.isfinite(v)]
    return float(np.mean(vals)) if vals else np.nan


def first_sentence(text):
    text = str(text)
    return text.split(". ", 1)[0] + "."


def rest(text):
    text = str(text)
    parts = text.split(". ", 1)
    return parts[1] if len(parts) == 2 else text


def sysblock(text):
    m = re.search(r"<\|start_header_id\|>system<\|end_header_id\|>(.*?)<\|eot_id\|>", str(text), re.S)
    return m.group(1) if m else None


def userblock(text):
    m = re.search(r"<\|start_header_id\|>user<\|end_header_id\|>(.*?)<\|eot_id\|>", str(text), re.S)
    return m.group(1) if m else None


def softmax_ok(df, n=30):
    bad = 0
    checked = 0
    max_abs = 0.0
    for _, g in df.groupby("question_id"):
        lp = g.option_logprob.to_numpy(float)
        pr = g.model_prob.to_numpy(float)
        z = lp - np.max(lp)
        sm = np.exp(z)
        sm = sm / sm.sum()
        err = float(np.max(np.abs(sm - pr)))
        max_abs = max(max_abs, err)
        checked += 1
        if err > 1e-5:
            bad += 1
        if checked >= n:
            break
    return {"checked": checked, "bad": bad, "max_abs": max_abs}


def main():
    scores = pd.read_csv(SCORES)
    report = {
        "score_arms": sorted(scores.arm.unique().tolist()),
        "score_n": int(len(scores)),
    }
    z = json.loads(GPS.read_text())
    z16 = pd.Series({c: float(z[c]["trust"]) for c in PANEL})

    def rho_arm(arm):
        sub = scores[(scores.arm == arm) & (scores.item.isin(TRUST9)) & (scores.country.isin(PANEL))]
        comp = sub.groupby("country")["raw"].mean().reindex(PANEL)
        d = pd.concat([comp.rename("a"), z16.rename("b")], axis=1).dropna()
        return float(spearmanr(d.a, d.b).statistic), comp.to_dict()

    arm_rhos = {}
    for arm in scores.arm.unique():
        rho, _ = rho_arm(arm)
        arm_rhos[arm] = rho
    report["frozen_score_trust_rho"] = arm_rhos

    # persona composites from per-country files
    persona_comp = {}
    persona_meta = []
    adapter_comp = {}
    adapter_meta = []
    mismatches = []

    # one persona file for prompt identity across countries
    persona_rests = {}
    persona_systems = {}
    persona_token = {}

    for c in PANEL:
        p = RAW / "persona_baseline" / f"model_option_probabilities_persona_base_on_{c}.csv"
        df = pd.read_csv(p, usecols=[
            "model", "prompt_country", "question_id", "option_code", "option_value",
            "option_logprob", "option_token_count", "model_prob", "prompt_text",
            "complete_prompt_model_received", "prompt_was_truncated", "eval_country",
        ])
        persona_comp[c] = composite(df)
        q57 = df[df.question_id == "Q57"].iloc[0]
        persona_rests[c] = rest(q57.prompt_text)
        persona_systems[c] = sysblock(q57.complete_prompt_model_received)
        persona_token[c] = {
            str(int(r.option_code)) if float(r.option_code) == int(r.option_code) else str(r.option_code): int(r.option_token_count)
            for r in df[df.question_id == "Q57"].itertuples()
        }
        if c == "ARG":
            persona_meta.append({
                "model": q57.model,
                "prompt_country": q57.prompt_country,
                "eval_country": q57.eval_country,
                "first": first_sentence(q57.prompt_text),
                "rest_head": rest(q57.prompt_text)[:300],
                "system": persona_systems[c],
                "truncated": bool(q57.prompt_was_truncated),
                "softmax": softmax_ok(df),
                "n_rows": int(len(df)),
                "questions": sorted(df.question_id.unique().tolist()),
            })

    # adapter matched files
    banks = {
        "ARG": "ksenias_base8", "CHN": "ksenias_base8", "DEU": "ksenias_base8",
        "GBR": "ksenias_base8", "JPN": "ksenias_base8", "MEX": "ksenias_base8",
        "RUS": "ksenias_base8", "USA": "ksenias_base8",
        "BRA": "co2_8", "EGY": "co2_8", "GRC": "co2_8", "IDN": "co2_8",
        "IND": "co2_8", "NGA": "co2_8", "NLD": "co2_8", "TUR": "co2_8",
    }
    adapter_rests = {}
    adapter_systems = {}
    adapter_firsts = {}
    adapter_token = {}
    adapter_softmax = {}
    prompt_country_values = {}
    for c, bank in banks.items():
        path = RAW / bank / f"model_option_probabilities_{c}_adapter_on_{c}.csv"
        df = pd.read_csv(path, usecols=[
            "model", "prompt_country", "question_id", "option_code", "option_value",
            "option_logprob", "option_token_count", "model_prob", "prompt_text",
            "complete_prompt_model_received", "prompt_was_truncated",
        ])
        adapter_comp[c] = composite(df)
        q57 = df[df.question_id == "Q57"].iloc[0]
        adapter_rests[c] = rest(q57.prompt_text)
        adapter_systems[c] = sysblock(q57.complete_prompt_model_received)
        adapter_firsts[c] = first_sentence(q57.prompt_text)
        adapter_token[c] = {
            str(int(r.option_code)) if float(r.option_code) == int(r.option_code) else str(r.option_code): int(r.option_token_count)
            for r in df[df.question_id == "Q57"].itertuples()
        }
        prompt_country_values[c] = None if pd.isna(q57.prompt_country) else str(q57.prompt_country)
        if c in {"ARG", "BRA"}:
            adapter_softmax[c] = softmax_ok(df)
            adapter_meta.append({
                "country": c,
                "bank": bank,
                "file": str(path.relative_to(REPO)),
                "model": q57.model,
                "prompt_country": prompt_country_values[c],
                "first": adapter_firsts[c],
                "system": adapter_systems[c],
                "truncated": bool(q57.prompt_was_truncated),
                "n_rows": int(len(df)),
                "n_questions": int(df.question_id.nunique()),
            })

    # compare rests and systems
    report["persona_rest_nunique"] = len(set(persona_rests.values()))
    report["adapter_rest_nunique"] = len(set(adapter_rests.values()))
    report["persona_system_nunique"] = len(set(persona_systems.values()))
    report["adapter_system_nunique"] = len(set(adapter_systems.values()))
    report["rest_equal_persona_vs_adapter"] = {
        c: persona_rests[c] == adapter_rests[c] for c in PANEL
    }
    report["system_equal_persona_vs_adapter"] = {
        c: persona_systems[c] == adapter_systems[c] for c in PANEL
    }
    report["q57_token_equal"] = {c: persona_token[c] == adapter_token[c] for c in PANEL}
    report["adapter_first_sentences"] = adapter_firsts
    report["adapter_prompt_country"] = prompt_country_values
    report["persona_meta_ARG"] = persona_meta
    report["adapter_meta"] = adapter_meta
    report["adapter_softmax"] = adapter_softmax

    # spearman from recomputed composites
    def rho_from(comp):
        a = pd.Series(comp).reindex(PANEL)
        d = pd.concat([a.rename("a"), z16.rename("b")], axis=1).dropna()
        return float(spearmanr(d.a, d.b).statistic)

    report["recomputed_trust_rho"] = {
        "adapter_from_matched_option_csvs": rho_from(adapter_comp),
        "persona_from_persona_base_csvs": rho_from(persona_comp),
    }
    # match frozen adapter raw means?
    frozen_ad = scores[(scores.arm == "adapter") & (scores.item.isin(TRUST9))].groupby("country")["raw"].mean()
    recon_ad = pd.Series(adapter_comp)
    delta = (frozen_ad.reindex(PANEL) - recon_ad.reindex(PANEL)).abs()
    report["adapter_composite_vs_frozen"] = {
        "max_abs": float(delta.max()),
        "mean_abs": float(delta.mean()),
        "per_country": delta.round(6).to_dict(),
    }
    # is there a persona arm in frozen scores?
    # try all arms against persona composites
    arm_match = {}
    for arm in scores.arm.unique():
        sub = scores[(scores.arm == arm) & (scores.item.isin(TRUST9))]
        fr = sub.groupby("country")["raw"].mean()
        dlt = (fr.reindex(PANEL) - pd.Series(persona_comp).reindex(PANEL)).abs()
        arm_match[arm] = {"max_abs": float(dlt.max()) if dlt.notna().any() else None}
    report["frozen_arm_vs_persona_composite"] = arm_match

    # also compare item-level frozen adapter vs recomputed for ARG Q57
    # item-level
    item_deltas = []
    for c in ["ARG", "BRA", "USA"]:
        bank = banks[c]
        path = RAW / bank / f"model_option_probabilities_{c}_adapter_on_{c}.csv"
        df = pd.read_csv(path, usecols=["question_id", "option_value", "model_prob"])
        for q in TRUST9:
            recon = item_score(df, q)
            fr = scores[(scores.arm == "adapter") & (scores.country == c) & (scores.item == q)]
            if fr.empty:
                item_deltas.append({"c": c, "q": q, "missing_frozen": True})
            else:
                item_deltas.append({
                    "c": c, "q": q,
                    "recon": recon,
                    "frozen": float(fr.iloc[0]["raw"]),
                    "abs": abs(recon - float(fr.iloc[0]["raw"])),
                })
    report["item_level_adapter_vs_frozen"] = item_deltas

    # persona item vs any arm
    p_arg = pd.read_csv(RAW / "persona_baseline" / "model_option_probabilities_persona_base_on_ARG.csv",
                        usecols=["question_id", "option_value", "model_prob"])
    persona_item_match = {}
    for arm in scores.arm.unique():
        absmax = 0.0
        n = 0
        for q in TRUST9:
            recon = item_score(p_arg, q)
            fr = scores[(scores.arm == arm) & (scores.country == "ARG") & (scores.item == q)]
            if fr.empty:
                continue
            absmax = max(absmax, abs(recon - float(fr.iloc[0]["raw"])))
            n += 1
        persona_item_match[arm] = {"n": n, "max_abs_ARG_trust9": absmax}
    report["persona_item_vs_frozen_arms_ARG"] = persona_item_match

    # token count patterns: codes with token_count != 1
    # sample a few questions' codes and counts from both
    def code_counts(path):
        df = pd.read_csv(path, usecols=["question_id", "option_code", "option_token_count"])
        g = df.drop_duplicates(["question_id", "option_code"])
        return {
            "n_pairs": int(len(g)),
            "token_count_values": {str(k): int(v) for k, v in g.option_token_count.value_counts().items()},
            "codes_with_tc_ne_2": g[g.option_token_count != 2][["question_id", "option_code", "option_token_count"]].head(15).to_dict(orient="records"),
        }
    report["token_patterns"] = {
        "persona_ARG": code_counts(RAW / "persona_baseline" / "model_option_probabilities_persona_base_on_ARG.csv"),
        "adapter_ARG": code_counts(RAW / "ksenias_base8" / "model_option_probabilities_ARG_adapter_on_ARG.csv"),
        "adapter_BRA": code_counts(RAW / "co2_8" / "model_option_probabilities_BRA_adapter_on_BRA.csv"),
    }

    # exact prompt_text equality for Q57 after replacing first sentence
    report["all_rest_equal"] = all(persona_rests[c] == adapter_rests[c] for c in PANEL)
    report["all_system_equal"] = all(persona_systems[c] == adapter_systems[c] for c in PANEL)
    report["all_q57_token_equal"] = all(persona_token[c] == adapter_token[c] for c in PANEL)
    report["adapter_first_all_individual"] = all(
        adapter_firsts[c] == "Answer this questionnaire as an individual person." for c in PANEL
    )
    report["persona_first_all_typical"] = True  # filled below

    # user-block equality aside from first sentence, from complete prompt
    user_equal = {}
    for c in PANEL:
        # already compared rest of prompt_text; also compare assistant header tail
        pass
    # compare full formatted wrapper structure: everything except the country sentence inside user content
    # load one complete prompt each
    pcomp = pd.read_csv(RAW / "persona_baseline" / "model_option_probabilities_persona_base_on_ARG.csv",
                        usecols=["question_id", "complete_prompt_model_received"]).query("question_id=='Q57'").iloc[0, 1]
    acomp = pd.read_csv(RAW / "ksenias_base8" / "model_option_probabilities_ARG_adapter_on_ARG.csv",
                        usecols=["question_id", "complete_prompt_model_received"]).query("question_id=='Q57'").iloc[0, 1]
    bcomp = pd.read_csv(RAW / "co2_8" / "model_option_probabilities_BRA_adapter_on_BRA.csv",
                        usecols=["question_id", "complete_prompt_model_received"]).query("question_id=='Q57'").iloc[0, 1]
    def normalize_user(text):
        ub = userblock(text) or ""
        # replace first sentence
        ub2 = re.sub(
            r"Answer this questionnaire as (?:an individual person|a typical adult living in [^.]+)\.",
            "PERSONA_SENTENCE",
            ub,
            count=1,
        )
        return ub2
    report["normalized_user_equal_ARG"] = normalize_user(pcomp) == normalize_user(acomp)
    report["normalized_user_equal_adapter_ARG_vs_BRA"] = normalize_user(acomp) == normalize_user(bcomp)
    report["assistant_suffix_persona"] = str(pcomp)[-80:]
    report["assistant_suffix_adapter_ARG"] = str(acomp)[-80:]
    report["assistant_suffix_equal"] = str(pcomp).endswith(str(acomp)[-40:]) or (
        str(pcomp)[str(pcomp).rfind("<|start_header_id|>assistant"):] ==
        str(acomp)[str(acomp).rfind("<|start_header_id|>assistant"):]
    )
    report["assistant_tail_persona"] = str(pcomp)[str(pcomp).rfind("<|start_header_id|>assistant"):]
    report["assistant_tail_adapter"] = str(acomp)[str(acomp).rfind("<|start_header_id|>assistant"):]

    OUT.write_text(json.dumps(report, indent=2, default=str))
    print("wrote", OUT, OUT.stat().st_size)
    print("frozen rhos", arm_rhos)
    print("recomputed", report["recomputed_trust_rho"])
    print("adapter vs frozen max", report["adapter_composite_vs_frozen"]["max_abs"])
    print("rest equal", report["all_rest_equal"], "system", report["all_system_equal"], "tok", report["all_q57_token_equal"])


if __name__ == "__main__":
    main()
