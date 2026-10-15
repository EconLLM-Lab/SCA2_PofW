"""Use a local adapter tokenizer (no model load, no download) to interpret option_token_count.

Also diff realized prompts between usamex canonical Arm A and persona Arm B.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
OUT = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/provenance/_token_report.json")
TOK_DIR = REPO / "data/phase2/adapters/co2_8/BRA"
PERSONA = REPO / "data/phase2/raw/wvs/persona_baseline/model_option_probabilities_persona_base_on_USA.csv"
ARM_A = REPO / "DPO_eval_WVS/eval_results_wvs_wave7/model_option_probabilities_USA_adapter_on_USA.csv"
ARM_A_BRA = REPO / "data/phase2/raw/wvs/co2_8/model_option_probabilities_BRA_adapter_on_BRA.csv"


def userblock(text):
    m = re.search(r"<\|start_header_id\|>user<\|end_header_id\|>(.*?)<\|eot_id\|>", str(text), re.S)
    return m.group(1) if m else None


def normalize(text):
    ub = userblock(text) or ""
    return re.sub(
        r"Answer this questionnaire as (?:an individual person|a typical adult living in [^.]+)\.",
        "PERSONA_SENTENCE",
        ub,
        count=1,
    )


def main():
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(TOK_DIR), local_files_only=True)
    report = {
        "tokenizer_dir": str(TOK_DIR.relative_to(REPO)),
        "name_or_path": getattr(tok, "name_or_path", None),
        "vocab_size": tok.vocab_size,
        "chat_template_present": bool(getattr(tok, "chat_template", None)),
    }
    # probe completions
    probes = ["1", " 1", "\n1", "1\n", " 1\n", "2", " 2", "10", " 10", "Yes", " Yes"]
    report["probes"] = {}
    for s in probes:
        ids = tok(s, add_special_tokens=False).input_ids
        report["probes"][repr(s)] = {"n": len(ids), "ids": ids}

    # what strings of the form prefix+code have n==2 for code 1 and n==3 for longer codes?
    persona = pd.read_csv(PERSONA)
    g = persona.drop_duplicates(["question_id", "option_code"])
    # map code -> token count (should be stable)
    pairs = []
    for code, tc in g.groupby("option_code")["option_token_count"].unique().items():
        pairs.append({"code": str(code), "token_counts": [int(x) for x in tc]})
    report["persona_code_token_counts"] = pairs

    # find prefix such that tok(prefix+code) length matches observed for all codes
    codes = sorted({str(int(c)) if float(c) == int(float(c)) else str(c) for c in g.option_code.unique()})
    observed = {}
    for _, row in g.iterrows():
        code = str(int(row.option_code)) if float(row.option_code) == int(row.option_code) else str(row.option_code)
        observed[code] = int(row.option_token_count)
    prefixes = ["", " ", "\n", " \n", "\n ", "Answer: ", " "]
    # also try the notebook prefix exactly
    prefix_fits = []
    for pref in ["", " ", "\n", "\t", "  ", "\n\n"]:
        ok = True
        detail = {}
        for code, n_obs in observed.items():
            n = len(tok(f"{pref}{code}", add_special_tokens=False).input_ids)
            detail[code] = {"obs": n_obs, "got": n}
            if n != n_obs:
                ok = False
        prefix_fits.append({"prefix": repr(pref), "ok": ok, "n_codes": len(detail), "mismatches": {k: v for k, v in detail.items() if v["obs"] != v["got"]}})
    report["prefix_fits_local_tokenizer"] = prefix_fits

    # compare prompts USA adapter canonical vs persona USA Q57
    a = pd.read_csv(ARM_A)
    p = persona
    aq = a[a.question_id == "Q57"].iloc[0]
    pq = p[p.question_id == "Q57"].iloc[0]
    report["usa_q57"] = {
        "adapter_first": str(aq.prompt_text).split("\n", 1)[0],
        "persona_first": str(pq.prompt_text).split("\n", 1)[0],
        "normalized_user_equal": normalize(aq.complete_prompt_model_received) == normalize(pq.complete_prompt_model_received),
        "adapter_norm_len": len(normalize(aq.complete_prompt_model_received)),
        "persona_norm_len": len(normalize(pq.complete_prompt_model_received)),
        "adapter_has_generated_cols": "generated_answer_raw" in a.columns,
        "persona_has_generated_cols": "generated_answer_raw" in p.columns,
        "adapter_prompt_was_truncated": bool(aq.prompt_was_truncated),
        "persona_prompt_was_truncated": bool(pq.prompt_was_truncated),
        "adapter_prompt_tokens": int(aq.prompt_token_count_model),
        "persona_prompt_tokens": int(pq.prompt_token_count_model),
    }
    # token count equality all questions USA
    a_tc = a.drop_duplicates(["question_id", "option_code"])[["question_id", "option_code", "option_token_count"]]
    p_tc = p.drop_duplicates(["question_id", "option_code"])[["question_id", "option_code", "option_token_count"]]
    m = a_tc.merge(p_tc, on=["question_id", "option_code"], suffixes=("_a", "_p"), how="outer")
    report["usa_token_count_compare"] = {
        "n_adapter": int(len(a_tc)),
        "n_persona": int(len(p_tc)),
        "n_inner": int(m.dropna().shape[0]),
        "n_mismatch": int((m.dropna().option_token_count_a != m.dropna().option_token_count_p).sum()),
        "only_adapter": int(m.option_token_count_p.isna().sum()),
        "only_persona": int(m.option_token_count_a.isna().sum()),
    }

    # BRA adapter vs persona BRA
    b = pd.read_csv(ARM_A_BRA)
    pb = pd.read_csv(REPO / "data/phase2/raw/wvs/persona_baseline/model_option_probabilities_persona_base_on_BRA.csv")
    bq = b[b.question_id == "Q57"].iloc[0]
    pq = pb[pb.question_id == "Q57"].iloc[0]
    report["bra_q57_normalized_user_equal"] = normalize(bq.complete_prompt_model_received) == normalize(pq.complete_prompt_model_received)
    b_tc = b.drop_duplicates(["question_id", "option_code"])[["question_id", "option_code", "option_token_count"]]
    p_tc = pb.drop_duplicates(["question_id", "option_code"])[["question_id", "option_code", "option_token_count"]]
    m = b_tc.merge(p_tc, on=["question_id", "option_code"], suffixes=("_a", "_p"))
    report["bra_token_mismatch"] = int((m.option_token_count_a != m.option_token_count_p).sum())

    # chat template render check: does local tokenizer reproduce the saved system date?
    rendered = tok.apply_chat_template(
        [{"role": "user", "content": "Answer this questionnaire as an individual person. TEST"}],
        tokenize=False,
        add_generation_prompt=True,
    )
    report["local_tokenizer_render_has_26_jul_2024"] = "26 Jul 2024" in rendered
    report["local_tokenizer_render_has_dec_2023"] = "December 2023" in rendered
    report["local_render_head"] = rendered[:400]

    # revision fields in tokenizer_config
    cfg = json.loads((TOK_DIR / "tokenizer_config.json").read_text())
    report["tokenizer_config_keys_sample"] = sorted(cfg.keys())[:40]
    report["tokenizer_config_revision"] = cfg.get("revision")
    report["tokenizer_config_name_or_path"] = cfg.get("name_or_path") or cfg.get("tokenizer_class")

    OUT.write_text(json.dumps(report, indent=2))
    print("wrote", OUT, OUT.stat().st_size)
    print("prefix fits", [(x["prefix"], x["ok"], len(x["mismatches"])) for x in prefix_fits])
    print("usa normalized equal", report["usa_q57"]["normalized_user_equal"])
    print("local date", report["local_tokenizer_render_has_26_jul_2024"])


if __name__ == "__main__":
    main()
