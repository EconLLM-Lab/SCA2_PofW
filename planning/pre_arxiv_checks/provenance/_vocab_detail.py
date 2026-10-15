"""Inspect how the saved tokenizer.json encodes a leading space."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
TOK = REPO / "data/phase2/adapters/co2_8/BRA/tokenizer.json"
OUT = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/provenance/_vocab_detail.json")

data = json.loads(TOK.read_text())
vocab = data["model"]["vocab"]
# short keys containing digit 1
short = []
for k, i in vocab.items():
    if "1" in k and len(k) <= 3:
        short.append({"key": k, "repr": repr(k), "id": i, "codepoints": [hex(ord(ch)) for ch in k]})
short.sort(key=lambda r: r["id"])
# pretokenizer
pre = data.get("pre_tokenizer")
dec = data.get("decoder")
normalizer = data.get("normalizer")
# added tokens
added = data.get("added_tokens")
report = {
    "top_keys": list(data.keys()),
    "model_keys": list(data["model"].keys()),
    "pre_tokenizer": pre,
    "decoder_type": dec.get("type") if isinstance(dec, dict) else None,
    "normalizer": normalizer,
    "n_short_with_1": len(short),
    "short_with_1": short[:80],
    "added_token_contents": [a.get("content") for a in (added or [])][:15],
}
OUT.write_text(json.dumps(report, indent=2)[:80000])
print("short", len(short), "wrote", OUT.stat().st_size)
print("pre type", pre.get("type") if isinstance(pre, dict) else type(pre))
print("sample", short[:12])
