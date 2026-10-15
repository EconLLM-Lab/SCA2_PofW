"""Search notebooks and nearby text for the persona scoring run and revision pins."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
OUT = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/provenance/_search_notes.txt")

needles = (
    "persona_base",
    "prompt_conditioning",
    "summary.json",
    "COMPLETION_PREFIX",
    "revision=",
    "commit",
    "0f2c0e",
    "model_option_probabilities_persona",
)

lines = []
for nb in sorted(REPO.rglob("*.ipynb")):
    try:
        text = nb.read_text(errors="replace")
    except Exception as exc:
        lines.append(f"FAIL {nb}: {exc}")
        continue
    hits = [n for n in needles if n in text]
    if hits:
        lines.append(f"{nb.relative_to(REPO)} :: {hits}")

# also py/md
for p in REPO.rglob("*"):
    if p.suffix.lower() not in {".py", ".md", ".json", ".txt"}:
        continue
    if "provenance" in str(p):
        continue
    if p.stat().st_size > 5_000_000:
        continue
    try:
        text = p.read_text(errors="replace")
    except Exception:
        continue
    if "persona_base" in text or "model_option_probabilities_persona" in text:
        # line hits
        for i, line in enumerate(text.splitlines(), 1):
            if "persona_base" in line or "probabilities_persona" in line or "COMPLETION_PREFIX" in line:
                lines.append(f"{p.relative_to(REPO)}:{i}: {line[:200]}")

OUT.write_text("\n".join(lines))
print("lines", len(lines), "bytes", OUT.stat().st_size)
