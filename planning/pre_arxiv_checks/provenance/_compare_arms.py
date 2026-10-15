"""Compare saved scoring artifacts for Arm A (adapter, unconditioned) vs Arm B (base persona).

Writes a JSON report. Does not modify the repo.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
OUT = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/provenance/_compare_report.json")

RAW = REPO / "data/phase2/raw/wvs"
CANON = REPO / "DPO_eval_WVS/eval_results_wvs_wave7"
PERSONA = RAW / "persona_baseline"
ADAPTERS = ["ARG", "BRA", "CHN", "DEU", "EGY", "GBR", "GRC", "IDN",
            "IND", "JPN", "MEX", "NGA", "NLD", "RUS", "TUR", "USA"]
BASE8 = {"ARG", "CHN", "DEU", "GBR", "JPN", "MEX", "RUS", "USA"}


def header(path: Path) -> list[str]:
    with path.open() as f:
        return f.readline().rstrip("\n").split(",")


def find_adapter_files() -> dict:
    found = {}
    candidates = []
    for root in [RAW, CANON.parent, REPO / "DPO_eval_WVS"]:
        if not root.exists():
            continue
        for p in root.rglob("model_option_probabilities*.csv"):
            name = p.name
            if "persona" in name:
                continue
            candidates.append(str(p.relative_to(REPO)))
    # pick one matched adapter file per country if present
    picked = {}
    patterns = []
    for c in ADAPTERS:
        hits = [p for p in candidates if f"{c}_adapter" in Path(p).name or f"{c}_adapter" in p]
        # prefer on_{c}
        own = [p for p in hits if f"_on_{c}" in Path(p).name or f"on_{c}" in Path(p).name]
        picked[c] = (own or hits)[:3]
    return {"n_non_persona_option_csvs": len(candidates), "sample_paths": candidates[:30], "picked": picked}


def load_persona_slice() -> pd.DataFrame:
    # combined file is huge; use per-country ARG and USA and one co2 country
    frames = []
    for c in ["ARG", "USA", "BRA"]:
        p = PERSONA / f"model_option_probabilities_persona_base_on_{c}.csv"
        df = pd.read_csv(p)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def chat_bits(text: str) -> dict:
    if not isinstance(text, str):
        return {"missing": True}
    return {
        "has_begin": "<|begin_of_text|>" in text,
        "has_system": "<|start_header_id|>system<|end_header_id|>" in text,
        "has_user": "<|start_header_id|>user<|end_header_id|>" in text,
        "has_assistant_gen": "<|start_header_id|>assistant<|end_header_id|>" in text,
        "cutting_date": (re.search(r"Cutting Knowledge Date: ([^\n]+)", text) or [None, None])[1]
        if False else (m.group(1) if (m := re.search(r"Cutting Knowledge Date: ([^\n]+)", text)) else None),
        "today_date": (m.group(1) if (m := re.search(r"Today Date: ([^\n]+)", text)) else None),
        "first_user_sentence": None,
        "len": len(text),
    }


def first_sentence(prompt_text: str) -> str:
    if not isinstance(prompt_text, str):
        return ""
    return prompt_text.split(". ", 1)[0] + "."


def strip_country_sentence(prompt_text: str) -> str:
    if not isinstance(prompt_text, str):
        return ""
    # drop first sentence
    parts = prompt_text.split(". ", 1)
    if len(parts) == 1:
        return prompt_text
    return parts[1]


def softmax_check(df: pd.DataFrame, keys: list[str]) -> dict:
    import numpy as np
    bad = 0
    checked = 0
    max_abs = 0.0
    for _, g in df.groupby(keys):
        if len(g) < 2:
            continue
        lp = g["option_logprob"].to_numpy(float)
        pr = g["model_prob"].to_numpy(float)
        z = lp - lp.max()
        sm = np.exp(z)
        sm = sm / sm.sum()
        err = float(np.max(np.abs(sm - pr)))
        max_abs = max(max_abs, err)
        checked += 1
        if err > 1e-6:
            bad += 1
        if checked >= 200:
            break
    return {"groups_checked": checked, "groups_not_unit_softmax": bad, "max_abs_err": max_abs}


def token_count_summary(df: pd.DataFrame) -> dict:
    sub = df[df["question_id"].isin(["Q57", "Q58", "Q12"])][
        ["question_id", "option_code", "option_token_count"]
    ].drop_duplicates()
    rows = sub.to_dict(orient="records")
    # overall distribution
    vc = df["option_token_count"].value_counts().head(8).to_dict()
    vc = {str(k): int(v) for k, v in vc.items()}
    return {"examples": rows[:40], "value_counts": vc}


def prompt_compare(persona: pd.DataFrame, adapter_df: pd.DataFrame | None, label: str) -> dict:
    out = {"label": label}
    # persona Q57 ARG
    p = persona[(persona.prompt_country == "ARG") & (persona.question_id == "Q57")].iloc[0]
    out["persona_first_sentence"] = first_sentence(p["prompt_text"])
    out["persona_rest"] = strip_country_sentence(p["prompt_text"])[:500]
    out["persona_chat"] = chat_bits(p.get("complete_prompt_model_received", ""))
    out["persona_formatted_chat"] = chat_bits(p.get("formatted_prompt", ""))
    out["persona_truncated"] = bool(p.get("prompt_was_truncated"))
    out["persona_prompt_tokens"] = int(p.get("prompt_token_count_model"))
    if adapter_df is not None and len(adapter_df):
        # pick Q57 if present
        a = adapter_df[adapter_df.question_id == "Q57"]
        if a.empty:
            a = adapter_df.head(1)
        else:
            a = a.head(1)
        row = a.iloc[0]
        out["adapter_cols_have_prompt"] = "prompt_text" in adapter_df.columns
        if "prompt_text" in adapter_df.columns:
            out["adapter_first_sentence"] = first_sentence(row["prompt_text"])
            out["adapter_rest"] = strip_country_sentence(row["prompt_text"])[:500]
            out["rest_equal_after_first_sentence"] = (
                strip_country_sentence(row["prompt_text"]) == strip_country_sentence(p["prompt_text"])
            )
            # also compare after normalizing country sentence only
            out["adapter_prompt_text_head"] = str(row["prompt_text"])[:400]
        if "complete_prompt_model_received" in adapter_df.columns:
            out["adapter_chat"] = chat_bits(row["complete_prompt_model_received"])
            # compare system header block
            def sysblock(t):
                if not isinstance(t, str):
                    return None
                m = re.search(r"<\|start_header_id\|>system<\|end_header_id\|>(.*?)<\|eot_id\|>", t, re.S)
                return m.group(1) if m else None
            ps = sysblock(p.get("complete_prompt_model_received", ""))
            as_ = sysblock(row["complete_prompt_model_received"])
            out["system_blocks_equal"] = ps == as_
            out["persona_system"] = ps
            out["adapter_system"] = as_
        out["adapter_model"] = str(row.get("model"))
        out["adapter_prompt_country"] = None if pd.isna(row.get("prompt_country")) else row.get("prompt_country")
    return out


def main() -> None:
    report = {}
    report["persona_summary"] = json.loads((PERSONA / "summary.json").read_text())
    report["persona_files"] = sorted(p.name for p in PERSONA.iterdir())

    # headers
    p_arg = PERSONA / "model_option_probabilities_persona_base_on_ARG.csv"
    report["persona_header"] = header(p_arg)

    files = find_adapter_files()
    report["adapter_file_index"] = {
        "n": files["n_non_persona_option_csvs"],
        "sample": files["sample_paths"][:20],
        "picked_counts": {c: len(v) for c, v in files["picked"].items()},
        "picked_first": {c: (v[0] if v else None) for c, v in files["picked"].items()},
    }

    persona = load_persona_slice()
    report["persona_models"] = sorted(persona["model"].unique().tolist())
    report["persona_token_summary"] = token_count_summary(persona)
    report["persona_softmax"] = softmax_check(persona, ["prompt_country", "question_id"])
    report["persona_truncated_any"] = bool(persona["prompt_was_truncated"].any())
    report["persona_today_dates"] = sorted({
        chat_bits(t)["today_date"] for t in persona["complete_prompt_model_received"].dropna().unique()
    })
    report["persona_cutting_dates"] = sorted({
        chat_bits(t)["cutting_date"] for t in persona["complete_prompt_model_received"].dropna().unique()
    })
    # first sentences
    fs = persona.drop_duplicates("prompt_country")[["prompt_country", "prompt_text"]]
    report["persona_first_sentences"] = {
        r.prompt_country: first_sentence(r.prompt_text) for r in fs.itertuples()
    }
    # rest of prompt identical across countries?
    rests = {c: strip_country_sentence(t) for c, t in zip(fs.prompt_country, fs.prompt_text)}
    report["persona_rest_identical_across_sampled_countries"] = len(set(rests.values())) == 1

    # load one adapter file that has prompt columns if any
    adapter_compares = []
    promptful = []
    for c, paths in files["picked"].items():
        if not paths:
            continue
        path = REPO / paths[0]
        cols = header(path)
        if "prompt_text" in cols or "formatted_prompt" in cols or "complete_prompt_model_received" in cols:
            promptful.append(paths[0])
    report["adapter_files_with_prompt_cols"] = promptful[:40]

    # also scan canon and bank combined files
    combined_candidates = [
        CANON / "model_option_probabilities.csv",
        RAW / "ksenias_base8" / "model_option_probabilities.csv",
        RAW / "co2_8" / "model_option_probabilities.csv",
        RAW / "usamex_canonical" / "model_option_probabilities.csv",
    ]
    report["combined_headers"] = {}
    for p in combined_candidates:
        if p.exists():
            report["combined_headers"][str(p.relative_to(REPO))] = header(p)

    # per-file headers for one base8 and one co2 adapter on-own file
    sample_files = []
    for c in ["ARG", "BRA", "USA"]:
        first = files["picked"].get(c, [None])[0]
        if first:
            sample_files.append(first)
    # also look for preview files next to adapter evals
    previews = list(REPO.rglob("survey_complete_prompt_preview.csv"))
    report["preview_files"] = [str(p.relative_to(REPO)) for p in previews]

    # compare persona prompt rest to each preview's unconditioned prompt rest
    preview_compares = []
    p_arg_row = persona[(persona.prompt_country == "ARG") & (persona.question_id == "Q57")]
    if p_arg_row.empty:
        p_arg_row = persona[(persona.prompt_country == "ARG")].head(1)
    persona_rest = strip_country_sentence(p_arg_row.iloc[0]["prompt_text"])
    persona_sys = None
    m = re.search(
        r"<\|start_header_id\|>system<\|end_header_id\|>(.*?)<\|eot_id\|>",
        str(p_arg_row.iloc[0].get("complete_prompt_model_received", "")),
        re.S,
    )
    persona_sys = m.group(1) if m else None

    for prev in previews:
        try:
            pdf = pd.read_csv(prev)
        except Exception as exc:
            preview_compares.append({"file": str(prev.relative_to(REPO)), "error": str(exc)})
            continue
        rec = {
            "file": str(prev.relative_to(REPO)),
            "n": len(pdf),
            "cols": list(pdf.columns),
            "prompt_countries": sorted({str(x) for x in pdf["prompt_country"].unique()}) if "prompt_country" in pdf.columns else None,
        }
        if "question_id" in pdf.columns and "prompt_text" in pdf.columns:
            q = pdf[pdf.question_id == "Q57"]
            if q.empty:
                q = pdf.head(1)
            row = q.iloc[0]
            rec["first_sentence"] = first_sentence(str(row["prompt_text"]))
            rec["rest_equal_to_persona_Q57_ARG"] = strip_country_sentence(str(row["prompt_text"])) == persona_rest
            rec["preview_rest_head"] = strip_country_sentence(str(row["prompt_text"]))[:240]
            if "complete_prompt_model_received" in pdf.columns:
                mm = re.search(
                    r"<\|start_header_id\|>system<\|end_header_id\|>(.*?)<\|eot_id\|>",
                    str(row["complete_prompt_model_received"]),
                    re.S,
                )
                rec["system"] = mm.group(1) if mm else None
                rec["system_equal_to_persona"] = rec["system"] == persona_sys
                rec["chat"] = chat_bits(str(row["complete_prompt_model_received"]))
        preview_compares.append(rec)
    report["preview_compares"] = preview_compares
    report["persona_system"] = persona_sys
    report["persona_rest_head"] = persona_rest[:800]
    report["persona_Q57_prompt_text"] = str(p_arg_row.iloc[0]["prompt_text"])
    report["persona_Q57_complete_head"] = str(p_arg_row.iloc[0].get("complete_prompt_model_received", ""))[:1200]

    # tokenizer configs: chat_template hash across adapters
    import hashlib
    tok_root = REPO / "data/phase2/adapters"
    hashes = {}
    dates = set()
    for cfg in tok_root.rglob("tokenizer_config.json"):
        raw = cfg.read_text(errors="replace")
        h = hashlib.sha256(raw.encode()).hexdigest()[:12]
        rel = str(cfg.relative_to(tok_root))
        bank = rel.split("/")[0]
        hashes.setdefault(h, {"n": 0, "example": rel, "banks": set()})
        hashes[h]["n"] += 1
        hashes[h]["banks"].add(bank)
        mm = re.search(r"Today Date: ([^\\n\"]+)", raw)
        if mm:
            dates.add(mm.group(1))
    report["tokenizer_config_hashes"] = [
        {"hash": k, "n": v["n"], "example": v["example"], "banks": sorted(v["banks"])}
        for k, v in hashes.items()
    ]
    report["tokenizer_config_today_dates"] = sorted(dates)

    # adapter_config revision already known; also README frontmatter and any .gitattributes / config.json revision
    revs = []
    for p in tok_root.rglob("*"):
        if p.is_file() and p.name in {"config.json", "adapter_config.json", "README.md", "trainer_state.json"}:
            if p.stat().st_size > 2_000_000:
                continue
            text = p.read_text(errors="replace")
            if "revision" in text or "commit" in text[:2000]:
                if p.name == "adapter_config.json" and '"revision": null' in text:
                    continue
                revs.append(str(p.relative_to(REPO)))
    report["files_mentioning_revision_or_commit"] = revs[:40]

    # option code strings: persona codes for Q57
    q57 = persona[(persona.prompt_country == "ARG") & (persona.question_id == "Q57")][
        ["option_code", "option_label", "option_token_count", "option_logprob", "model_prob"]
    ]
    report["persona_Q57_ARG_options"] = q57.to_dict(orient="records")

    OUT.write_text(json.dumps(report, indent=2, default=str))
    print("wrote", OUT, "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()
