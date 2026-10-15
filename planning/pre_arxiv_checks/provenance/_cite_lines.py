"""Pull config lines and from_pretrained signatures for citations."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
OUT = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/provenance/_cite_lines.txt")
lines = []

nb_path = REPO / "DPO_eval_WVS/DPO_WVS_evaluation_selective_skip_unavailable_questions (1).ipynb"
nb = json.loads(nb_path.read_text())
src = "".join(nb["cells"][6]["source"])
lines.append("=== selective cell 6 ===")
lines.append(src)
src17 = "".join(nb["cells"][17]["source"])
lines.append("\n=== selective cell 17 head ===")
lines.append("\n".join(src17.splitlines()[:40]))

cfg = json.loads((REPO / "data/phase2/adapters/co2_8/BRA/adapter_config.json").read_text())
lines.append("\n=== adapter_config keys ===")
lines.append(json.dumps({k: cfg.get(k) for k in ("base_model_name_or_path", "revision", "peft_type")}, indent=2))

# line of revision in file
text = (REPO / "data/phase2/adapters/co2_8/BRA/adapter_config.json").read_text().splitlines()
for i, line in enumerate(text, 1):
    if "revision" in line or "base_model" in line:
        lines.append(f"adapter_config.json:{i}: {line}")

# summary.json already known
# protocols runner revision absence
runner = (REPO / "protocols/sca2_2x2_inference_runner.py").read_text().splitlines()
for i, line in enumerate(runner, 1):
    if "MODEL_ID" in line or "HF_REPO" in line or "revision" in line or "from_pretrained" in line:
        lines.append(f"runner:{i}: {line}")

OUT.write_text("\n".join(lines))
print("wrote", OUT.stat().st_size)
