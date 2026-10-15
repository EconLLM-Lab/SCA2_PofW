"""Which completion prefix reproduces every saved option_token_count?"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
TOK = REPO / "data/phase2/adapters/co2_8/BRA/tokenizer.json"
OUT = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/provenance/_prefix_fit.json")


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


def build_bpe(path: Path):
    data = json.loads(path.read_text())
    vocab = data["model"]["vocab"]
    merges = data["model"]["merges"]
    merge_rank = {}
    for i, m in enumerate(merges):
        if isinstance(m, str):
            merge_rank[tuple(m.split(" ", 1))] = i
        else:
            merge_rank[tuple(m)] = i
    b2u = bytes_to_unicode()

    def bpe(s: str):
        enc = "".join(b2u[b] for b in s.encode("utf-8"))
        symbols = list(enc)
        while len(symbols) >= 2:
            pairs = [(symbols[i], symbols[i + 1]) for i in range(len(symbols) - 1)]
            ranked = [(merge_rank[p], i) for i, p in enumerate(pairs) if p in merge_rank]
            if not ranked:
                break
            ranked.sort()
            _, i = ranked[0]
            symbols = symbols[:i] + [symbols[i] + symbols[i + 1]] + symbols[i + 2:]
        return symbols

    return bpe, vocab


def code_str(v) -> str:
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    s = str(v)
    if s.endswith(".0"):
        return s[:-2]
    return s


def main():
    bpe, vocab = build_bpe(TOK)
    files = {
        "persona_USA": REPO / "data/phase2/raw/wvs/persona_baseline/model_option_probabilities_persona_base_on_USA.csv",
        "adapter_USA_canonical": REPO / "DPO_eval_WVS/eval_results_wvs_wave7/model_option_probabilities_USA_adapter_on_USA.csv",
        "adapter_BRA": REPO / "data/phase2/raw/wvs/co2_8/model_option_probabilities_BRA_adapter_on_BRA.csv",
        "adapter_ARG": REPO / "data/phase2/raw/wvs/ksenias_base8/model_option_probabilities_ARG_adapter_on_ARG.csv",
    }
    prefixes = ["", " ", "\n", "\n ", " \n", "\t"]
    report = {}
    observed_sets = {}
    for label, path in files.items():
        df = pd.read_csv(path, usecols=["question_id", "option_code", "option_token_count"])
        g = df.drop_duplicates(["option_code", "option_token_count"])
        # one count per code; flag conflicts
        conflicts = []
        observed = {}
        for code, sub in df.drop_duplicates(["question_id", "option_code"]).groupby(df["option_code"].map(code_str) if False else "option_code"):
            pass
        rows = df.drop_duplicates(["question_id", "option_code"]).copy()
        rows["code_s"] = rows["option_code"].map(code_str)
        for code, sub in rows.groupby("code_s"):
            counts = sorted(set(int(x) for x in sub.option_token_count))
            observed[code] = counts[0]
            if len(counts) != 1:
                conflicts.append({"code": code, "counts": counts})
        observed_sets[label] = observed
        fits = []
        for pref in prefixes:
            mismatches = []
            for code, n_obs in observed.items():
                got = len(bpe(f"{pref}{code}"))
                if got != n_obs:
                    mismatches.append({"code": code, "obs": n_obs, "got": got})
            fits.append({"prefix": repr(pref), "ok": len(mismatches) == 0, "n_mismatch": len(mismatches), "examples": mismatches[:8]})
        report[label] = {
            "n_codes": len(observed),
            "conflicts": conflicts,
            "token_count_hist": {str(k): int(v) for k, v in pd.Series(list(observed.values())).value_counts().items()},
            "fits": fits,
            "non_digit_codes": [c for c in observed if not c.lstrip("-").isdigit()][:20],
        }
    # cross-file observed equality on shared codes
    base = observed_sets["persona_USA"]
    cross = {}
    for label, obs in observed_sets.items():
        shared = set(base) & set(obs)
        bad = [c for c in shared if base[c] != obs[c]]
        cross[label] = {"shared": len(shared), "mismatch": bad[:10], "n_mismatch": len(bad)}
    report["cross_vs_persona_USA"] = cross
    OUT.write_text(json.dumps(report, indent=2))
    for label, rec in report.items():
        if label.startswith("cross"):
            continue
        print(label, [(f["prefix"], f["ok"], f["n_mismatch"]) for f in rec["fits"]])
    print("cross", cross)


if __name__ == "__main__":
    main()
