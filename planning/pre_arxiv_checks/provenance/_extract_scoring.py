"""Extract scoring-related notebook cells and local provenance artifacts.

Does not modify the repo. Writes a text dump next to this script.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
OUT = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/provenance/_extract_dump.txt")

KEYS = re.compile(
    r"from_pretrained|apply_chat_template|build_survey_user_prompt|option_logprob|"
    r"PROMPT_COUNTRY|MODEL_NAME|MODEL_ID|revision|chat_template|leading|"
    r"add_generation_prompt|BitsAndBytes|log_softmax|f\" \{|\" \" \+|"
    r"typical adult|individual person|tokenizer",
    re.I,
)


def dump_notebooks(lines: list[str]) -> None:
    nbs = sorted(REPO.rglob("*.ipynb"))
    lines.append(f"NOTEBOOKS {len(nbs)}")
    for nb_path in nbs:
        try:
            nb = json.loads(nb_path.read_text(errors="replace"))
        except Exception as exc:
            lines.append(f"\nFAIL {nb_path}: {exc}")
            continue
        cells = nb.get("cells", [])
        hits = []
        for i, cell in enumerate(cells):
            src = "".join(cell.get("source", []))
            if KEYS.search(src):
                hits.append((i, cell.get("cell_type"), src))
        if not hits:
            continue
        rel = nb_path.relative_to(REPO)
        lines.append(f"\n===== {rel} cells={len(cells)} hits={len(hits)} =====")
        for i, ctype, src in hits:
            # keep scoring-relevant cells, truncate huge ones
            if len(src) > 8000:
                src = src[:4000] + "\n...[truncated]...\n" + src[-2000:]
            lines.append(f"\n--- cell {i} ({ctype}) ---")
            lines.append(src)


def dump_py(lines: list[str]) -> None:
    interesting = [
        REPO / "protocols/sca2_2x2_inference_runner.py",
        REPO / "analysis/phase2/colab/rung_mix_colab.py",
        REPO / "analysis/phase2/colab/smoke_test.py",
        REPO / "analysis/phase2/colab/rung_sft_vm.py",
    ]
    for p in interesting:
        if p.exists():
            lines.append(f"\n===== PY {p.relative_to(REPO)} =====")
            lines.append(p.read_text()[:12000])


def dump_previews(lines: list[str]) -> None:
    previews = list(REPO.rglob("survey_complete_prompt_preview.*"))
    lines.append(f"\nPREVIEWS {len(previews)}")
    for p in previews:
        lines.append(f"\n===== PREVIEW {p.relative_to(REPO)} size={p.stat().st_size} =====")
        text = p.read_text(errors="replace")
        lines.append(text[:6000])


def dump_adapter_configs(lines: list[str]) -> None:
    root = REPO / "data/phase2/adapters"
    lines.append("\n===== ADAPTER CONFIGS =====")
    if not root.exists():
        lines.append("missing adapters dir")
        return
    cfgs = sorted(root.rglob("adapter_config.json"))
    lines.append(f"n_configs={len(cfgs)}")
    # sample one from each bank
    shown = 0
    for cfg in cfgs:
        if shown >= 4:
            break
        data = json.loads(cfg.read_text())
        keep = {k: data.get(k) for k in [
            "base_model_name_or_path", "revision", "peft_type", "r", "lora_alpha",
            "target_modules", "task_type", "inference_mode",
        ]}
        lines.append(f"{cfg.relative_to(REPO)} :: {json.dumps(keep)}")
        shown += 1
    # unique base_model_name_or_path
    bases = set()
    revs = set()
    for cfg in cfgs:
        data = json.loads(cfg.read_text())
        bases.add(data.get("base_model_name_or_path"))
        revs.add(data.get("revision"))
    lines.append(f"unique base_model_name_or_path={sorted(map(str, bases))}")
    lines.append(f"unique revision field={sorted(map(str, revs))}")
    # tokenizer files present?
    tok_files = list(root.rglob("tokenizer_config.json"))
    lines.append(f"tokenizer_config.json count={len(tok_files)}")
    if tok_files:
        sample = tok_files[0]
        lines.append(f"sample tokenizer {sample.relative_to(REPO)}")
        raw = sample.read_text(errors="replace")
        lines.append(raw[:3000])


def dump_persona_headers(lines: list[str]) -> None:
    d = REPO / "data/phase2/raw/wvs/persona_baseline"
    lines.append("\n===== PERSONA BASELINE FILES =====")
    if not d.exists():
        lines.append("missing")
        return
    files = sorted(d.iterdir())
    lines.append(f"n={len(files)}")
    for f in files:
        lines.append(f"{f.name} size={f.stat().st_size}")
    # header + first 3 data rows of combined and one per-country
    for name in ["model_option_probabilities_persona.csv",
                 "model_option_probabilities_persona_base_on_ARG.csv"]:
        p = d / name
        if not p.exists():
            continue
        text = p.read_text(errors="replace").splitlines()
        lines.append(f"\n--- {name} nlines={len(text)} ---")
        lines.append("\n".join(text[:4]))
        # unique models
    # also look for any sidecar json/md in persona dirs
    for extra in [d, REPO / "data/phase2/raw/wvs/persona_adapter"]:
        for f in sorted(extra.iterdir()):
            if f.suffix.lower() in {".json", ".md", ".txt", ".jsonl"} or "prompt" in f.name.lower() or "manifest" in f.name.lower():
                lines.append(f"sidecar {f}")


def main() -> None:
    lines: list[str] = []
    dump_adapter_configs(lines)
    dump_persona_headers(lines)
    dump_previews(lines)
    dump_py(lines)
    dump_notebooks(lines)
    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT} bytes={OUT.stat().st_size} lines={len(lines)}")


if __name__ == "__main__":
    main()
