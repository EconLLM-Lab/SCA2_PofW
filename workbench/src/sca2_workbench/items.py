"""Prompts for the 3D views, built with the SCA2 readout (Eq. 6).

Sources, copied verbatim and not reworded:
- ``survey_prompt_v1`` is ``paper_b/eval_lib.py:159-196``
  ``build_survey_user_prompt(spec, prompt_country=None)`` (variant "v1", no persona country).
- ``bank_user_prompt`` is ``paper_b/lib.py:119-129`` ``build_user_prompt``.
- WVS items come from ``DPO_eval_WVS/question_map_wvs_edited.csv``. That file is public and
  tracked in git. ``paper_b/eval_lib.py:9`` names it the source of the option codes. Nothing
  here reads the licensed ``data/`` tree.

Readout (Eq. 6): each completion is ``" " + code``. Its teacher-forced log-prob is summed,
and the result is softmaxed over the item's codes. When every completion is a shared token
prefix plus exactly one distinct token, the prefix log-prob cancels in that softmax. Eq. 6
is then exactly a softmax over the code-token logits at the last prefix position. That
position is the *readout position*. It is the only place where direct logit attribution
(DLA) is defined for the item.
"""

from __future__ import annotations

import bisect
import csv
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[2]
REPO = WORKBENCH.parent
QUESTION_MAP = REPO / "DPO_eval_WVS" / "question_map_wvs_edited.csv"
BANK_DIR = REPO / "synthetic_generation" / "outputs" / "gps_sign_relabel_all"


@dataclass(frozen=True)
class Item:
    item_id: str            # e.g. "wvs_Q57" or "bank_USA_00023ac74dac"
    kind: str               # "wvs" | "bank"
    user_prompt: str        # the user-turn text before the chat template
    codes: tuple            # option codes, e.g. ("1", "2")
    labels: tuple           # option labels, same order
    j_plus: str             # code whose logit is the + side of the DLA margin
    j_minus: str            # code on the - side
    meta: dict = field(default_factory=dict)
    #: The user prompt as ``(kind, label, text)`` parts whose texts concatenate to
    #: ``user_prompt`` exactly. The exporter turns them into token ``segments``.
    #: Empty for ad-hoc prompts that were not built from parts.
    parts: tuple = ()


def survey_prompt_parts(question_text: str, codes, labels, question_label: str = "question") -> tuple:
    """Verbatim ``build_survey_user_prompt`` v1 with ``prompt_country=None``, non-numeric branch,
    as ``(kind, label, text)`` parts. A blank-line separator belongs to the part before it.
    The kinds are the ones in the export contract: instruction, question, options, answer_cue."""
    persona = "Answer this questionnaire as an individual person."
    option_lines = "\n".join(f"{code}: {label}" for code, label in zip(codes, labels))
    return (
        ("instruction", "persona and tone",
         f"{persona} Respond naturally and sincerely, as someone would in real life. "
         "Do not mention being an AI or assistant.\n\n"),
        ("question", question_label, f"Question:\n{question_text}\n\n"),
        ("instruction", "response rule",
         "Select exactly one response code from the options below.\n"),
        ("options", f"options {codes[0]}\u2013{codes[-1]}", f"{option_lines}\n\n"),
        ("instruction", "output rule",
         "Return only the response code, with no words or explanation.\n\n"),
        ("answer_cue", "answer cue", "Answer:"),
    )


def survey_prompt_v1(question_text: str, codes, labels) -> str:
    """Verbatim ``build_survey_user_prompt`` v1 with ``prompt_country=None``, non-numeric branch."""
    return "".join(text for _, _, text in survey_prompt_parts(question_text, codes, labels))


def bank_user_prompt(prompt_text: str) -> str:
    """Verbatim ``paper_b/lib.py`` ``build_user_prompt`` (the DPO training prompt)."""
    return (
        "You are answering a questionnaire as an individual person. "
        "Respond naturally and thoughtfully, as someone would in real life. "
        "Do not mention being an AI or assistant. "
        "Keep the answer short, under 3 sentences. "
        "Give a sincere, human-like answer.\n\n"
        "Situation:\n"
        f"{prompt_text.strip()}\n\n"
        "Answer:"
    )


def _split(value: str) -> list:
    return [p.strip() for p in str(value).split(";") if p.strip()]


def wvs_item(qid: str) -> Item:
    """One fixed-option WVS item. The margin is the first code minus the last (scale endpoints)."""
    with QUESTION_MAP.open(encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle) if r["Question"].strip() == qid]
    if len(rows) != 1:
        raise ValueError(f"{qid}: expected one row in {QUESTION_MAP.name}, got {len(rows)}")
    row = rows[0]
    codes = [str(int(float(c))) for c in _split(row["ResponseCodes"])]
    labels = _split(row["ResponseLabels"])[: len(codes)]
    labels += codes[len(labels):]
    text = row["StandaloneQuestion"].strip()
    return Item(
        item_id=f"wvs_{qid}",
        kind="wvs",
        user_prompt=survey_prompt_v1(text, codes, labels),
        codes=tuple(codes),
        labels=tuple(labels),
        j_plus=codes[0],
        j_minus=codes[-1],
        meta={"question_id": qid, "response_type": row["ResponseType"],
              "source": "DPO_eval_WVS/question_map_wvs_edited.csv"},
        parts=survey_prompt_parts(text, codes, labels, "WVS question"),
    )


def bank_forced_choice(country: str, triplet_id: str) -> Item:
    """One synthetic anchor scenario posed as a two-option survey item.

    The question is the bank ``prompt``. The options are ``chosen`` and ``rejected``. The
    option order comes from a hash of ``triplet_id`` and does not depend on the label, so
    position cannot stand in for preference. ``j_plus`` is always the chosen (GPS-sign-aligned)
    code, so a positive margin means the model prefers the anchor-aligned answer.
    """
    path = BANK_DIR / f"D_syn_{country}.jsonl"
    with path.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    hits = [r for r in rows if r["triplet_id"] == triplet_id]
    if len(hits) != 1:
        raise ValueError(f"{triplet_id}: expected one row in {path.name}, got {len(hits)}")
    rec = hits[0]
    chosen_first = int(hashlib.sha256(triplet_id.encode()).hexdigest(), 16) % 2 == 0
    labels = (rec["chosen"], rec["rejected"]) if chosen_first else (rec["rejected"], rec["chosen"])
    j_plus = "1" if chosen_first else "2"
    return Item(
        item_id=f"bank_{country}_{triplet_id}",
        kind="bank",
        user_prompt=survey_prompt_v1(rec["prompt"].strip(), ("1", "2"), labels),
        codes=("1", "2"),
        labels=labels,
        j_plus=j_plus,
        j_minus="2" if j_plus == "1" else "1",
        meta={"country": country, "triplet_id": triplet_id, "gps_dimension": rec["gps_dimension"],
              "facet": rec["facet"], "chosen_code": j_plus, "source": str(path.relative_to(REPO))},
        parts=survey_prompt_parts(rec["prompt"].strip(), ("1", "2"), labels, "scenario"),
    )


def readout_ids(tokenizer, item: Item, chat_kwargs: dict | None = None) -> dict:
    """Token ids for the Eq. 6 readout of one item.

    Returns ``prompt_ids`` (chat-templated prompt plus the shared completion prefix),
    ``code_token`` (code -> the single distinct token id), and ``prefix_ids``.
    Raises when the codes do not split as shared prefix + one token (e.g. " 1" vs " 10").

    ``chat_kwargs`` go to ``apply_chat_template``. Llama-3.1's template writes a date into its
    system block unless one is passed, so Paper B's capture passes
    ``{"date_string": eval_config.ARCHIVE_CHAT_DATE}``; the SmolLM2 path passes nothing.
    """
    formatted = tokenizer.apply_chat_template(
        [{"role": "user", "content": item.user_prompt}], tokenize=False,
        add_generation_prompt=True, **(chat_kwargs or {}))
    base = tokenizer(formatted, add_special_tokens=False).input_ids
    comps = {c: tokenizer(" " + c, add_special_tokens=False).input_ids for c in item.codes}
    lengths = {len(v) for v in comps.values()}
    if len(lengths) != 1:
        raise ValueError(f"{item.item_id}: completions differ in length {comps}")
    n = lengths.pop()
    prefix = list(comps[item.codes[0]][:-1])
    if any(list(v[:-1]) != prefix for v in comps.values()):
        raise ValueError(f"{item.item_id}: completions do not share a prefix {comps}")
    last = {c: v[-1] for c, v in comps.items()}
    if len(set(last.values())) != len(last):
        raise ValueError(f"{item.item_id}: two codes map to the same token {comps}")
    return {"prompt_ids": list(base) + prefix, "prefix_ids": prefix, "code_token": last,
            "n_completion_tokens": n, "formatted_prompt": formatted}


SEGMENT_KINDS = ("template", "system", "instruction", "question", "options", "answer_cue", "readout")


def check_segments(segments: list, n_tokens: int) -> None:
    """Raise unless the segments cover ``[0, n_tokens)`` once, in order, with no gap or overlap."""
    pos = 0
    for s in segments:
        if s["a"] != pos or s["b"] <= s["a"] or s["kind"] not in SEGMENT_KINDS:
            raise ValueError(f"segment {s} breaks the cover at token {pos}")
        pos = s["b"]
    if pos != n_tokens:
        raise ValueError(f"segments end at {pos}, prompt has {n_tokens} tokens")


def prompt_segments(tokenizer, item: Item, ro: dict) -> list:
    """Half-open token ranges ``[a, b)`` of the prompt, as ``{a, b, kind, label}``.

    Built from how the prompt is made, not from token text. The chat template puts the user
    prompt in verbatim, so its character span is an exact ``str.find``. Everything before it is
    the template's system turn, everything after it the closing markers. Inside the user prompt
    the spans come from ``item.parts``. Characters map to tokens through the tokenizer's offset
    mapping, and a token that straddles a span edge raises. The shared completion prefix
    (``ro["prefix_ids"]``) is not in the formatted text. It forms the ``readout`` segment, whose
    last token is t*. With an empty prefix there is no ``readout`` segment, and t* is the last
    token of the final ``template`` segment.
    """
    f = ro["formatted_prompt"]
    if "".join(text for _, _, text in item.parts) != item.user_prompt:
        raise ValueError(f"{item.item_id}: parts do not concatenate to the user prompt")
    u0 = f.find(item.user_prompt)
    if u0 < 0 or f.find(item.user_prompt, u0 + 1) >= 0:
        raise ValueError(f"{item.item_id}: user prompt is not found exactly once in the chat template")
    u1 = u0 + len(item.user_prompt)

    # character spans (c0, c1, kind, label), contiguous over the formatted prompt
    spans = []
    # ChatML (SmolLM2) writes the system turn as ``<|im_start|>system\n...<|im_end|>``; Llama-3 as
    # ``<|start_header_id|>system<|end_header_id|>\n\n...<|eot_id|>`` (its date block lives here).
    system = (re.search(r"<\|im_start\|>system\n(.*?)<\|im_end\|>", f[:u0], re.S)
              or re.search(r"<\|start_header_id\|>system<\|end_header_id\|>\n\n(.*?)<\|eot_id\|>",
                          f[:u0], re.S))
    if system:
        spans += [(0, system.start(1), "template", "system turn opens"),
                  (system.start(1), system.end(1), "system", "system prompt"),
                  (system.end(1), u0, "template", "system turn closes \u00b7 user turn opens")]
    else:
        spans += [(0, u0, "template", "user turn opens")]
    c = u0
    for kind, label, text in item.parts:
        spans.append((c, c + len(text), kind, label))
        c += len(text)
    spans.append((u1, len(f), "template", "user turn closes \u00b7 assistant turn opens"))
    spans = [s for s in spans if s[1] > s[0]]
    if spans[0][0] != 0 or any(x[1] != y[0] for x, y in zip(spans, spans[1:])) or spans[-1][1] != len(f):
        raise ValueError(f"{item.item_id}: character spans do not tile the prompt")

    enc = tokenizer(f, add_special_tokens=False, return_offsets_mapping=True)
    n_base = len(ro["prompt_ids"]) - len(ro["prefix_ids"])
    if len(enc.input_ids) != n_base or list(enc.input_ids) != list(ro["prompt_ids"][:n_base]):
        raise ValueError(f"{item.item_id}: re-tokenising the formatted prompt changed the ids")
    starts = [s[0] for s in spans]
    segments = []
    for tok_i, (s, e) in enumerate(enc.offset_mapping):
        j = bisect.bisect_right(starts, s) - 1
        if e > spans[j][1]:
            raise ValueError(f"{item.item_id}: token {tok_i} straddles the edge of span {spans[j][3]!r}")
        if segments and segments[-1]["_span"] == j:
            segments[-1]["b"] = tok_i + 1
        else:
            segments.append({"a": tok_i, "b": tok_i + 1, "kind": spans[j][2], "label": spans[j][3], "_span": j})
    for seg in segments:
        del seg["_span"]
    if ro["prefix_ids"]:
        segments.append({"a": n_base, "b": len(ro["prompt_ids"]), "kind": "readout", "label": "readout t*"})
    check_segments(segments, len(ro["prompt_ids"]))
    return segments
