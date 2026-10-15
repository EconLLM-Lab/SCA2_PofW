#!/usr/bin/env python3
"""Extract in-repo wording, codes, and labels for the Paper A item table.

Reads only. Writes a JSON dump next to this script. Does not modify the repo.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent
REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
ITEMS = [
    "Q57", "Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73",
    "Q43", "Q50",
    "Q106", "Q107", "Q109", "Q178",
    "Q81",
    "Q176", "Q177", "Q179", "Q195",
    "Q99", "Q101", "Q103",
    "Q69", "Q70", "Q71",
]

qmap_path = REPO / "DPO_eval_WVS" / "question_map_wvs_edited.csv"
with qmap_path.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
qmap = {r["Question"]: r for r in rows}

preview_path = (
    REPO / "DPO_eval_WVS" / "eval_results_wvs_wave7" / "survey_complete_prompt_preview.jsonl"
)
preview = {}
with preview_path.open(encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        qid = obj.get("question_id")
        if qid in ITEMS or qid == "Q174":
            preview[qid] = {
                "question_text": obj.get("question_text"),
                "answer_codes": obj.get("answer_codes"),
                "answer_labels": obj.get("answer_labels"),
                "choices_as_shown": obj.get("choices_as_shown"),
                "response_type": obj.get("response_type"),
                "gps_dimension": obj.get("gps_dimension"),
            }

dta = REPO / "data" / "WVS" / "WVS_wave7.dta"
reader = pd.io.stata.StataReader(dta)
var_labels = reader.variable_labels()
value_labels = reader.value_labels()
# Map variable -> value-label name if the reader exposes it.
lbllist = {}
try:
    lbllist = dict(reader._lbllist) if hasattr(reader, "_lbllist") else {}
except Exception as exc:  # noqa: BLE001
    lbllist = {"error": str(exc)}

stata = {}
for q in ITEMS + ["Q174"]:
    entry = {
        "in_columns": q in var_labels or q in getattr(reader, "varlist", []),
        "variable_label": var_labels.get(q),
    }
    # value label dicts are keyed by label-set name, often the variable name
    vl = value_labels.get(q)
    if vl is None and isinstance(lbllist, dict):
        set_name = lbllist.get(q)
        if set_name:
            vl = value_labels.get(set_name)
            entry["value_label_set"] = set_name
    if vl is None:
        # search label sets whose keys include this variable name
        entry["value_labels"] = None
    else:
        # keys may be floats
        entry["value_labels"] = {str(k): v for k, v in vl.items()}
    stata[q] = entry

# If value labels were not keyed by variable, dump label-set names that mention Q
label_set_names = sorted(value_labels.keys())
q_sets = [n for n in label_set_names if any(q in n for q in ITEMS)]

dump = {
    "question_map": {
        q: {
            "QuestionText": qmap[q].get("QuestionText") if q in qmap else None,
            "IntroInstruction": qmap[q].get("IntroInstruction") if q in qmap else None,
            "ResponseType": qmap[q].get("ResponseType") if q in qmap else None,
            "ResponseLabels": qmap[q].get("ResponseLabels") if q in qmap else None,
            "ResponseCodes": qmap[q].get("ResponseCodes") if q in qmap else None,
            "StandaloneQuestion": qmap[q].get("StandaloneQuestion") if q in qmap else None,
            "gps_dimension": qmap[q].get("gps_dimension") if q in qmap else None,
            "Source": qmap[q].get("Source") if q in qmap else None,
            "Page": qmap[q].get("Page") if q in qmap else None,
            "in_question_map": q in qmap,
        }
        for q in ITEMS
    },
    "prompt_preview": preview,
    "stata": stata,
    "stata_value_label_set_count": len(label_set_names),
    "stata_value_label_sets_mentioning_items": q_sets[:80],
    "stata_lbllist_type": type(lbllist).__name__,
    "stata_lbllist_sample": (
        {q: lbllist.get(q) for q in ITEMS}
        if isinstance(lbllist, dict)
        else str(lbllist)[:500]
    ),
}
(OUT / "source_dump.json").write_text(json.dumps(dump, indent=2, ensure_ascii=False) + "\n")
print("wrote", OUT / "source_dump.json")
print("qmap missing", [q for q in ITEMS if q not in qmap])
print("preview missing", [q for q in ITEMS if q not in preview])
print("stata var labels present", sum(1 for q in ITEMS if stata[q]["variable_label"]))
print("stata value labels present", sum(1 for q in ITEMS if stata[q]["value_labels"]))
