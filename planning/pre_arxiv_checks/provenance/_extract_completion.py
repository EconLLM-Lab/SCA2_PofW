"""Pull completion-string construction and model-load kwargs from eval notebooks."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
OUT = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/provenance/_completion_extract.txt")

NEEDLES = (
    "completion_text",
    "f\" {code}",
    "f' {code}",
    '" " +',
    "leading",
    "revision",
    "PROMPT_COUNTRY_CONDITIONING",
    "BASE_MODEL_NAME",
    "MAX_PROMPT",
    "softmax",
    "temperature",
    "option_logprobs",
    "space",
)

nbs = [
    REPO / "DPO_eval_WVS/DPO_survey_distribution_evaluation.ipynb",
    REPO / "DPO_eval_WVS/DPO_WVS_evaluation_selective_skip_unavailable_questions (1).ipynb",
    REPO / "DPO_train_test/CO2_run/CO2_evaluation_cross_evaluation_selective_cached_ref.ipynb",
    REPO / "DPO_train_test/Base_run/DPO_evaluation_cross_evaluation_selective_cached_ref.ipynb",
    REPO / "DPO_train_test/DPO_evaluation_cross_evaluation.ipynb",
]

lines = []
for nb_path in nbs:
    nb = json.loads(nb_path.read_text())
    lines.append(f"\n######## {nb_path.relative_to(REPO)} ########")
    for i, cell in enumerate(nb.get("cells", [])):
        src = "".join(cell.get("source", []))
        if "completion_text" in src or "def score_question" in src or "def compute_option" in src:
            lines.append(f"\n--- cell {i} len={len(src)} ---")
            # extract functions containing completion
            lines.append(src)
        elif "PROMPT_COUNTRY_CONDITIONING" in src and "BASE_MODEL" in src and len(src) < 4000:
            lines.append(f"\n--- config cell {i} ---")
            lines.append(src)
        elif "from_pretrained" in src and "revision" in src:
            lines.append(f"\n--- revision cell {i} ---")
            lines.append(src[:2500])

OUT.write_text("\n".join(lines))
print("bytes", OUT.stat().st_size)
