"""Vocab lookup in the saved Llama tokenizer.json. No model, no transformers."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
OUT = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/provenance/_vocab_probe.json")
TOK = REPO / "data/phase2/adapters/co2_8/BRA/tokenizer.json"
TOK2 = REPO / "data/phase2/adapters/base8/ARG/tokenizer.json"

def load_vocab(path: Path) -> dict:
    data = json.loads(path.read_text())
    model = data.get("model", {})
    vocab = model.get("vocab")
    if vocab is None and "vocab" in data:
        vocab = data["vocab"]
    return vocab or {}, data.get("pre_tokenizer"), list(data.keys())


def main():
    report = {}
    for label, path in [("co2_BRA", TOK), ("base8_ARG", TOK2)]:
        vocab, pre, keys = load_vocab(path)
        probes = ["1", " 1", "Ġ1", "2", " 2", "10", " 10", " ", "1", "\n", "Yes", " Yes"]
        found = {}
        for s in probes:
            found[repr(s)] = vocab.get(s)
        # also search keys that equal space+digit via unicode
        space_digit = [k for k in vocab if k in {f" {d}" for d in "0123456789"} or k in {f"Ġ{d}" for d in "0123456789"}]
        report[label] = {
            "n_vocab": len(vocab),
            "top_keys": keys,
            "pre_tokenizer_type": (pre or {}).get("type") if isinstance(pre, dict) else type(pre).__name__,
            "probe_ids": found,
            "space_digit_keys_sample": space_digit[:20],
        }
        # hash vocab
        import hashlib
        h = hashlib.sha256(json.dumps(sorted(vocab.items())).encode()).hexdigest()[:16]
        report[label]["vocab_sha16"] = h
    report["vocabs_equal"] = report["co2_BRA"]["vocab_sha16"] == report["base8_ARG"]["vocab_sha16"]
    OUT.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: {"sha": v["vocab_sha16"], "probes": v["probe_ids"], "space": v["space_digit_keys_sample"][:8]} for k, v in report.items() if isinstance(v, dict)}, indent=2))


if __name__ == "__main__":
    main()
