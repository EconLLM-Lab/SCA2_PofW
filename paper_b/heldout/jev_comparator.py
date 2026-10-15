#!/usr/bin/env python3
"""Jev comparator: a System One model reads only an item's wording and assigns a GPS dimension.

Fixed rule (decided 2026-10-14, before any pool item was sent):
  model       jev-1.13.0 (pinned; `jev-latest` resolved to it on 2026-10-14)
  state       "Survey question: <wording>\\nResponse options: <code> = <label>; ..."
              (item text and labels only; no country, no model output, no human data)
  call 1      Choice over the six GPS dimensions + "none", each described by the same
              construct definitions used to generate the training data (DEFS, from
              synthetic_generation/sca2_datagen/config.GPS_DIMENSIONS, measurement-method
              clauses removed)
  assign      top choice != "none" and its probability >= TAU (0.5, not tuned: Jev's
              probabilities are calibrated by design, so 0.5 = "more likely than not")
  call 2      for an assigned item only, a Noul naming that dimension: does choosing the
              first listed response reveal more of it than choosing the last?
  sign        -1 if P(first = more) >= 0.5 (higher codes = less of the trait), else +1
  validation  the 23 battery items (already analysed) are scored against the frozen
              mapping and frozen recodes; reported, never used to tune anything.
Every request and answer is cached to a JSONL file and frozen with the selection.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "paper_b"))

MODEL = "jev-1.13.0"
TAU = 0.5
DIMS = ["trust", "risktaking", "patience", "altruism", "posrecip", "negrecip"]
NAMES = {"trust": "trust", "risktaking": "willingness to take risks",
         "patience": "patience", "altruism": "altruism",
         "posrecip": "positive reciprocity", "negrecip": "negative reciprocity"}
DEFS = {
    "trust": "Trust: belief that others have good intentions; baseline faith in strangers "
             "without enforcement; assuming good faith from unfamiliar others and confidence "
             "in institutional reliability.",
    "risktaking": "Risk-taking: willingness to take risks; embracing uncertainty and "
                  "preferring bold or entrepreneurial action over cautious avoidance.",
    "patience": "Patience: willingness to defer gratification; favouring later payoffs, "
                "future planning and long-horizon reasoning over immediate gratification.",
    "altruism": "Altruism: willingness to give to good causes without expecting a return; "
                "sharing resources and putting others' or the community's welfare first.",
    "posrecip": "Positive reciprocity: willingness to return a favour to someone who helped, "
                "at personal cost; expressing and acting on gratitude.",
    "negrecip": "Negative reciprocity: willingness to punish unfair behaviour even when it is "
                "costly; endorsing sanctions or retaliation against norm violators.",
    "none": "None of these: the answer does not directly reveal any of the preferences above.",
}
DIM_INSTRUCTIONS = ("Which one of these economic preferences does a person's answer to this "
                    "survey question most directly reveal? Choose 'none' if it does not "
                    "directly reveal any of them.")


def state_text(question: str, codes: list[str], labels: list[str]) -> str:
    opts = "; ".join(f"{c} = {l}" for c, l in zip(codes, labels))
    return f"Survey question: {question}\nResponse options: {opts}"


def direction_instructions(dim: str, codes: list[str], labels: list[str]) -> str:
    return (f"Does choosing response {codes[0]} ({labels[0]}) reveal more {NAMES[dim]} "
            f"than choosing response {codes[-1]} ({labels[-1]})?")


def _key() -> str:
    if "TYPESAFE_API_KEY" not in os.environ:
        env = Path.home() / ".hermes/profiles/sca/.env"
        for line in env.read_text().splitlines():
            if line.startswith("TYPESAFE_API_KEY="):
                os.environ["TYPESAFE_API_KEY"] = line.split("=", 1)[1].strip().strip("'\"")
    return os.environ["TYPESAFE_API_KEY"]


def make_caller() -> Callable[[str, dict], dict]:
    import typesafe_sdk as T
    client = T.TypeSafeClient(api_key=_key(), model=MODEL)

    def call(state: str, questions: dict) -> dict:
        qs = {}
        for name, q in questions.items():
            if q["type"] == "choice":
                qs[name] = T.Choice(instructions=q["instructions"], criteria=q["criteria"])
            else:
                qs[name] = T.Noul(instructions=q["instructions"])
        r = client.system_one(state=state, questions=qs, model=MODEL)
        return {"model": r.model, "answers": {k: a.model_dump() for k, a in r.answers.items()}}
    return call


class Cache:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.data: dict[str, dict] = {}
        if self.path.is_file():
            for line in self.path.read_text().splitlines():
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self.data[rec["key"]] = rec

    def get_or_call(self, key: str, state: str, questions: dict, call) -> dict:
        import hashlib
        key = key + "|" + hashlib.sha256(
            (state + json.dumps(questions, sort_keys=True)).encode()).hexdigest()[:16]
        if key in self.data:
            return self.data[key]["response"]
        resp = call(state, questions)
        rec = {"key": key, "state": state, "questions": questions, "response": resp}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self.data[key] = rec
        return resp


def _ascending(codes: list[str], labels: list[str]) -> tuple[list[str], list[str]]:
    pairs = sorted(zip(codes, labels), key=lambda cl: float(cl[0]))
    return [c for c, _ in pairs], [l for _, l in pairs]


def classify(item: str, question: str, codes: list[str], labels: list[str],
             call, cache: Cache) -> dict:
    # 'first' in the direction question must be the LOWEST code: some maps list 2;1;0.
    codes, labels = _ascending([str(c).strip() for c in codes], [str(l).strip() for l in labels])
    state = state_text(question, codes, labels)
    q1 = {"dimension": {"type": "choice", "instructions": DIM_INSTRUCTIONS, "criteria": DEFS}}
    a1 = cache.get_or_call(f"{item}|dimension", state, q1, call)["answers"]["dimension"]
    probs = a1["probabilities"]
    top = max(probs, key=probs.get)
    out = {"question_id": item, "top_choice": top, "top_prob": float(probs[top]),
           **{f"p_{d}": float(probs.get(d, 0.0)) for d in DIMS + ["none"]}}
    assigned = top != "none" and probs[top] >= TAU
    out["dimension"] = top if assigned else "none"
    out["p_first_more"] = float("nan")
    out["sign"] = 0
    if assigned:
        q2 = {"direction": {"type": "noul",
                            "instructions": direction_instructions(top, codes, labels)}}
        a2 = cache.get_or_call(f"{item}|direction|{top}", state, q2, call)["answers"]["direction"]
        p = float(a2["noul"])
        out["p_first_more"] = p
        out["sign"] = -1 if p >= 0.5 else 1
    return out


def frozen_battery() -> pd.DataFrame:
    """The 23 battery items with their frozen dimension and frozen direction."""
    import analyze_surface as AS
    import eval_lib as L
    qmap = L.load_question_map().drop_duplicates("Question").set_index("Question")
    rows = []
    for dim, qs in AS.STRICT_ITEMS.items():
        for q in qs:
            r = qmap.loc[q]
            codes = [c.strip() for c in str(r.ResponseCodes).split(";")]
            labels = [l.strip() for l in str(r.ResponseLabels).split(";")]
            inverted = q in AS.INVERT_1_4 or q in AS.INVERT_10 or q in AS.BINARY
            rows.append({"question_id": q, "question": str(r.StandaloneQuestion), "codes": codes,
                         "labels": labels, "frozen_dimension": dim,
                         "frozen_sign": -1 if inverted else 1})
    return pd.DataFrame(rows)


def run(items: pd.DataFrame, call, cache: Cache) -> pd.DataFrame:
    return pd.DataFrame([classify(r.question_id, r.question, list(r.codes), list(r.labels),
                                  call, cache) for r in items.itertuples()])


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Jev face-reading comparator")
    ap.add_argument("--set", choices=["battery", "pool"], required=True)
    ap.add_argument("--out-dir", default=str(HERE / "jev"))
    a = ap.parse_args()
    out = Path(a.out_dir)
    cache = Cache(out / f"jev_raw_{a.set}.jsonl")
    call = make_caller()
    if a.set == "battery":
        items = frozen_battery()
        res = run(items, call, cache).merge(
            items[["question_id", "frozen_dimension", "frozen_sign"]], on="question_id")
        res.to_csv(out / "jev_battery.csv", index=False)
        hit = res.dimension == res.frozen_dimension
        summary = {"model": MODEL, "tau": TAU, "items": len(res),
                   "dimension_agreement": float(hit.mean()),
                   "abstained": int((res.dimension == "none").sum()),
                   "sign_agreement_when_dimension_agrees":
                       float((res[hit].sign == res[hit].frozen_sign).mean()) if hit.any() else None}
        (out / "jev_battery_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
        print(json.dumps(summary, indent=1))
    else:
        pool = pd.read_csv(HERE / "pool_skeleton.csv")
        items = pd.DataFrame({"question_id": pool.Question, "question": pool.StandaloneQuestion,
                              "codes": pool.ResponseCodes.str.split("; "),
                              "labels": pool.ResponseLabels.str.split("; ")})
        res = run(items, call, cache)
        res.to_csv(out / "face_valid_jev.csv", index=False)
        a_ = res[res.dimension != "none"]
        print(f"pool {len(res)} | assigned {len(a_)} | {a_.dimension.value_counts().to_dict()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
