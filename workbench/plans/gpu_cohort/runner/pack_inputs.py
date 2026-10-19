"""Package questionnaire text and model-only archive rows; never opens respondent data."""
import argparse
import csv
from dataclasses import asdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from sca2_workbench import items as I
from sca2_workbench.cohort import digest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    files = sorted(args.archive.glob("*_option_probabilities.csv"))
    rows_by_arm = {}
    sources = {}
    for p in files:
        arm = p.name.removesuffix("_option_probabilities.csv").removesuffix("_adapter")
        rows_by_arm[arm] = list(csv.DictReader(p.open()))
        sources[p.name] = digest(p)
    if len(rows_by_arm) != 43:
        raise ValueError(f"expected 43 model-only CSVs, found {len(rows_by_arm)}")
    qids = sorted({r["question_id"] for r in rows_by_arm["base"]}, key=lambda s: int(s[1:]))
    items = []
    for qid in qids:
        rec = asdict(I.wvs_item(qid))
        rec["archive"] = {}
        for arm, rows in rows_by_arm.items():
            group = [r for r in rows if r["question_id"] == qid]
            name = "base_option_probabilities.csv" if arm == "base" else f"{arm}_adapter_option_probabilities.csv"
            if set(r["option_code"] for r in group) != set(rec["codes"]):
                raise ValueError(f"{arm}/{qid}: archive option codes differ")
            rec["archive"][arm] = {"source": f"paper-b-20261011/scores_for_join/{name}",
                                    "probs": {r["option_code"]: float(r["model_prob"]) for r in group},
                                    "logprobs": {r["option_code"]: float(r["option_logprob"]) for r in group}}
        items.append(rec)
    args.out.write_text(json.dumps({"items": items, "question_map_sha256": digest(I.QUESTION_MAP),
                                   "archive_sha256": sources}, indent=1) + "\n")
    print(json.dumps({"items": len(items), "arms": len(rows_by_arm), "item_ids": [x["item_id"] for x in items]}))
