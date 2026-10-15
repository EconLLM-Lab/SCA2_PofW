"""Cite-ready checks: wrapper equality, notebook cell numbers, revision strings in outputs."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
OUT = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/provenance/_cite_checks.json")


def norm_user(text: str) -> str:
    m = re.search(r"<\|start_header_id\|>user<\|end_header_id\|>(.*?)<\|eot_id\|>", str(text), re.S)
    ub = m.group(1) if m else ""
    return re.sub(
        r"Answer this questionnaire as (?:an individual person|a typical adult living in [^.]+)\.",
        "PERSONA_SENTENCE",
        ub,
        count=1,
    )


def sysblock(text: str):
    m = re.search(r"<\|start_header_id\|>system<\|end_header_id\|>(.*?)<\|eot_id\|>", str(text), re.S)
    return m.group(1) if m else None


def assistant_tail(text: str) -> str:
    i = str(text).rfind("<|start_header_id|>assistant")
    return str(text)[i:]


def main():
    report = {}
    pairs = [
        ("USA", REPO / "DPO_eval_WVS/eval_results_wvs_wave7/model_option_probabilities_USA_adapter_on_USA.csv",
         REPO / "data/phase2/raw/wvs/persona_baseline/model_option_probabilities_persona_base_on_USA.csv"),
        ("MEX", REPO / "DPO_eval_WVS/eval_results_wvs_wave7/model_option_probabilities_MEX_adapter_on_MEX.csv",
         REPO / "data/phase2/raw/wvs/persona_baseline/model_option_probabilities_persona_base_on_MEX.csv"),
        ("ARG", REPO / "data/phase2/raw/wvs/ksenias_base8/model_option_probabilities_ARG_adapter_on_ARG.csv",
         REPO / "data/phase2/raw/wvs/persona_baseline/model_option_probabilities_persona_base_on_ARG.csv"),
        ("BRA", REPO / "data/phase2/raw/wvs/co2_8/model_option_probabilities_BRA_adapter_on_BRA.csv",
         REPO / "data/phase2/raw/wvs/persona_baseline/model_option_probabilities_persona_base_on_BRA.csv"),
    ]
    comps = []
    for cc, ap, pp in pairs:
        a = pd.read_csv(ap)
        p = pd.read_csv(pp)
        # compare Q57 and all shared questions' prompt_text after first sentence
        aq = a[a.question_id == "Q57"].iloc[0]
        pq = p[p.question_id == "Q57"].iloc[0]
        a_prompts = a.drop_duplicates("question_id")[["question_id", "prompt_text", "complete_prompt_model_received"]]
        p_prompts = p.drop_duplicates("question_id")[["question_id", "prompt_text", "complete_prompt_model_received"]]
        m = a_prompts.merge(p_prompts, on="question_id", suffixes=("_a", "_p"))
        rest_bad = 0
        user_bad = 0
        sys_bad = 0
        tail_bad = 0
        for r in m.itertuples():
            ra = str(r.prompt_text_a).split(". ", 1)[-1]
            rp = str(r.prompt_text_p).split(". ", 1)[-1]
            if ra != rp:
                rest_bad += 1
            if norm_user(r.complete_prompt_model_received_a) != norm_user(r.complete_prompt_model_received_p):
                user_bad += 1
            if sysblock(r.complete_prompt_model_received_a) != sysblock(r.complete_prompt_model_received_p):
                sys_bad += 1
            if assistant_tail(r.complete_prompt_model_received_a) != assistant_tail(r.complete_prompt_model_received_p):
                tail_bad += 1
        comps.append({
            "country": cc,
            "n_shared_questions": int(len(m)),
            "rest_mismatch": rest_bad,
            "norm_user_mismatch": user_bad,
            "system_mismatch": sys_bad,
            "assistant_tail_mismatch": tail_bad,
            "adapter_first": str(aq.prompt_text).split(". ", 1)[0],
            "persona_first": str(pq.prompt_text).split(". ", 1)[0],
            "adapter_prompt_country_isna": bool(pd.isna(aq.prompt_country)),
            "persona_model": str(pq.model),
            "adapter_model": str(aq.model),
        })
    report["wrapper_comps"] = comps

    # notebook cells
    nbs = [
        REPO / "DPO_eval_WVS/DPO_survey_distribution_evaluation.ipynb",
        REPO / "DPO_eval_WVS/DPO_WVS_evaluation_selective_skip_unavailable_questions (1).ipynb",
    ]
    cell_index = {}
    rev_hits = []
    for nb_path in nbs:
        nb = json.loads(nb_path.read_text())
        marks = []
        for i, cell in enumerate(nb["cells"]):
            src = "".join(cell.get("source", []))
            flags = []
            for key in ("COMPLETION_PREFIX", "BASE_MODEL_NAME =", "PROMPT_COUNTRY_CONDITIONING",
                        "from_pretrained", "OPTION_SCORE_TEMPERATURE", "LENGTH_NORMALIZE"):
                if key in src:
                    flags.append(key)
            if flags:
                marks.append({"cell": i, "flags": flags, "head": src.strip().splitlines()[0][:120]})
            # outputs mentioning revision/commit
            for out in cell.get("outputs", [])[:8]:
                blob = json.dumps(out)[:5000]
                if re.search(r"commit|revision|sha", blob, re.I):
                    rev_hits.append({"nb": nb_path.name, "cell": i, "snippet": blob[:300]})
        cell_index[nb_path.name] = marks
    report["cell_index"] = cell_index
    report["rev_hits_n"] = len(rev_hits)
    report["rev_hits"] = rev_hits[:8]

    # tokenizer_config chat template date
    cfg = (REPO / "data/phase2/adapters/co2_8/BRA/tokenizer_config.json").read_text()
    report["tokenizer_config_has_26_jul"] = "26 Jul 2024" in cfg
    report["tokenizer_config_has_dec_2023"] = "December 2023" in cfg
    # line number
    for i, line in enumerate(cfg.splitlines(), 1):
        if "26 Jul 2024" in line or "chat_template" in line and i < 5:
            report.setdefault("tokenizer_config_lines", []).append({"line": i, "text": line[:180]})
    # find chat_template line
    for i, line in enumerate(cfg.splitlines(), 1):
        if "chat_template" in line or "26 Jul 2024" in line:
            report.setdefault("tok_lines", []).append(i)

    OUT.write_text(json.dumps(report, indent=2))
    print(json.dumps(comps, indent=2))
    print("cells", {k: [(m["cell"], m["flags"]) for m in v] for k, v in cell_index.items()})
    print("rev hits", len(rev_hits))
    print("tok lines", report.get("tok_lines"))


if __name__ == "__main__":
    main()
