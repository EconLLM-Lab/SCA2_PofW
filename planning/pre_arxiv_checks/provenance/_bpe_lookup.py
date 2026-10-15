"""Map a leading space through the GPT-2/Llama byte encoder and look it up."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
TOK = REPO / "data/phase2/adapters/co2_8/BRA/tokenizer.json"
OUT = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/provenance/_bpe_lookup.json")


def bytes_to_unicode():
    bs = (
        list(range(ord("!"), ord("~") + 1))
        + list(range(ord("¡"), ord("¬") + 1))
        + list(range(ord("®"), ord("ÿ") + 1))
    )
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return dict(zip(bs, [chr(c) for c in cs]))


def encode_token_str(s: str, b2u: dict) -> str:
    return "".join(b2u[b] for b in s.encode("utf-8"))


def main():
    data = json.loads(TOK.read_text())
    vocab = data["model"]["vocab"]
    merges = data["model"]["merges"]
    b2u = bytes_to_unicode()
    space_char = b2u[32]
    report = {
        "space_mapped_repr": repr(space_char),
        "space_codepoint": hex(ord(space_char)),
        "space_in_vocab": space_char in vocab,
        "space_id": vocab.get(space_char),
    }
    probes = ["1", " 1", "2", " 2", "10", " 10", "4", " 4", "Yes", " Yes", "\n1", "1\n"]
    rows = []
    for s in probes:
        enc = encode_token_str(s, b2u)
        rows.append({
            "s": repr(s),
            "encoded_repr": repr(enc),
            "in_vocab": enc in vocab,
            "id": vocab.get(enc),
        })
    report["probes"] = rows

    # greedy BPE for " 1" using merges if not a single token
    # merges may be list of "a b" strings or list of pairs
    merge_rank = {}
    if merges and isinstance(merges[0], str):
        for i, m in enumerate(merges):
            merge_rank[tuple(m.split(" "))] = i
    elif merges and isinstance(merges[0], list):
        for i, m in enumerate(merges):
            merge_rank[tuple(m)] = i
    report["merge0_type"] = type(merges[0]).__name__
    report["n_merges"] = len(merges)

    def bpe(s: str):
        enc = encode_token_str(s, b2u)
        # start from bytes as individual encoded chars? ByteLevel splits into the encoded unicode chars
        symbols = list(enc)
        # actually each byte becomes one unicode char, so symbols = list(enc) is correct
        while len(symbols) >= 2:
            pairs = [(symbols[i], symbols[i + 1]) for i in range(len(symbols) - 1)]
            ranked = [(merge_rank[p], i, p) for i, p in enumerate(pairs) if p in merge_rank]
            if not ranked:
                break
            ranked.sort()
            _, i, p = ranked[0]
            symbols = symbols[:i] + [p[0] + p[1]] + symbols[i + 2:]
        return symbols

    report["bpe"] = {repr(s): [{"tok": repr(t), "id": vocab.get(t)} for t in bpe(s)] for s in probes}

    OUT.write_text(json.dumps(report, indent=2))
    print(json.dumps(report["bpe"], indent=2))
    print("space id", report["space_id"], "mapped", report["space_mapped_repr"])


if __name__ == "__main__":
    main()
