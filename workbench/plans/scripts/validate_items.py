"""Which items does the readout rule accept, and how long (T) are the prompts? Tokenizer only, no model.

Run from workbench/:
    env -u PYTHONPATH PYTHONPATH=src uv run python plans/scripts/validate_items.py
Reads DPO_eval_WVS/question_map_wvs_edited.csv (public, tracked) and the bank file
synthetic_generation/outputs/gps_sign_relabel_all/D_syn_USA.jsonl. Does not touch data/.
"""

import csv
import json
import statistics as st
import sys

from transformers import AutoTokenizer

from sca2_workbench import export as EX
from sca2_workbench import items as I


def main():
    tok = AutoTokenizer.from_pretrained(EX.TOKENIZER_ID)
    qids = [r["Question"].strip() for r in csv.DictReader(I.QUESTION_MAP.open(encoding="utf-8"))]
    print("rows in question_map:", len(qids), "unique:", len(set(qids)))
    ok, bad = [], []
    for q in qids:
        try:
            item = I.wvs_item(q)
        except Exception as e:  # noqa: BLE001
            bad.append((q, "wvs_item: " + str(e)[:90])); continue
        try:
            ro = I.readout_ids(tok, item)
            ok.append((q, len(ro["prompt_ids"]), item.codes, item.meta["response_type"]))
        except Exception as e:  # noqa: BLE001
            bad.append((q, f"{item.meta['response_type']} codes={item.codes[:4]}.. -> {str(e)[:70]}"))
    print(f"accepted {len(ok)} / {len(qids)}; refused {len(bad)}")
    for q, why in bad:
        print("  refused", q, why)
    Ts = [t for _, t, _, _ in ok]
    print("WVS accepted T: min", min(Ts), "median", st.median(Ts), "max", max(Ts))
    by_type = {}
    for q, t, codes, rt in ok:
        by_type.setdefault(rt, []).append(len(codes))
    print("accepted by ResponseType -> (count, max #codes):", {k: (len(v), max(v)) for k, v in by_type.items()})
    # bank (USA): prompt length distribution
    path = I.BANK_DIR / "D_syn_USA.jsonl"
    rows = [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]
    Tb = []
    for r in rows:
        labels = (r["chosen"], r["rejected"])
        p = I.survey_prompt_v1(r["prompt"].strip(), ("1", "2"), labels)
        it = I.Item("x", "bank", p, ("1", "2"), labels, "1", "2")
        Tb.append(len(I.readout_ids(tok, it)["prompt_ids"]))
    Tb.sort()
    pct = lambda p: Tb[min(len(Tb) - 1, int(p * len(Tb)))]  # noqa: E731
    print(f"bank USA: {len(Tb)} rows, T min {Tb[0]} p50 {pct(.5)} p90 {pct(.9)} p99 {pct(.99)} max {Tb[-1]}")
    print("gps_dimension values in the CSV:", sorted({r["gps_dimension"] for r in csv.DictReader(I.QUESTION_MAP.open(encoding="utf-8"))}))
    print("bank gps_dimension values:", sorted({r["gps_dimension"] for r in rows}))


if __name__ == "__main__":
    sys.exit(main())
