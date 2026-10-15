"""Paper B — build the model-only scoring specification.

Exports a JSON spec (option grids per question, STRICT battery filter, optional
numeric-open grids) that the GPU scorer consumes directly. NO human frames, NO
population joins, NO Drive: the spec is built from the question map alone and
exported to a local file with a full SHA-256 for provenance.

Batteries:
  --battery strict   the primary 23-item battery (STRICT_ITEMS; parent decision)
  --battery archive  23 + Q69/Q70/Q71 + numeric-open grids (the archived 35-gate
                     question surface, for the adapter-path gate only)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_lib as L

# The primary battery: existing STRICT_ITEMS definition, 23 unique items.
# Source of truth: analysis/phase2/22_paper_a_surface.py (parent decision,
# PARENT_DECISIONS.md 2026-10-11: "23 unique items; Q69-71 secondary; patience
# Q43 and Q50 separate").
STRICT_ITEMS = {
    "trust": ["Q57", "Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73"],
    "patience": ["Q43", "Q50"],
    "risktaking": ["Q106", "Q107", "Q109", "Q178"],
    "posrecip": ["Q81"],
    "negrecip": ["Q176", "Q177", "Q179", "Q195"],
    "altruism": ["Q99", "Q101", "Q103"],
}
SECONDARY_IDS = ("Q69", "Q70", "Q71")


def strict_item_ids() -> set[str]:
    return {q for qs in STRICT_ITEMS.values() for q in qs}


def build_scoring_spec(question_map, numeric_support: dict[str, list[str]],
                       battery: str = "strict", sanitized: bool = False,
                       expect_missing: bool = True, prompt_variant: str = "v1",
                       heldout_items: list[str] | None = None) -> dict:
    """Model-only spec from the question map. No survey frames are touched.

    numeric_support is REQUIRED whenever the (filtered) battery contains a
    numeric_open question: the GPU scorer must never derive grids from human
    data it cannot see.
    """
    if battery == "strict":
        keep = strict_item_ids()
        unknown = {q for q in question_map["Question"] if q.startswith("Q")}
        # cross-check the map against the frozen battery: an item in the map
        # that collides with a strict id is fine; a strict id missing from the
        # map is a hard error unless explicitly allowed.
        mapped = set(question_map["Question"])
        missing = keep - mapped
        if missing and expect_missing:
            raise ValueError(f"strict battery items missing from question map: "
                             f"{sorted(missing)}")
    elif battery == "archive":
        keep = strict_item_ids() | set(SECONDARY_IDS)
        # archived gate surface also includes the numeric-open questions
        keep |= {str(q) for q, rt in zip(question_map["Question"],
                                         question_map["ResponseType"])
                 if str(rt) == "numeric_open"}
    elif battery == "heldout":
        if not heldout_items:
            raise ValueError("battery='heldout' requires heldout_items")
        keep = {str(q) for q in heldout_items}
        if keep & strict_item_ids():
            raise ValueError(f"held-out battery may not overlap the 23 strict items: "
                             f"{sorted(keep & strict_item_ids())}")
        missing = keep - set(question_map["Question"].astype(str))
        if missing:
            raise ValueError(f"held-out items missing from the question map: {sorted(missing)}")
    else:
        raise ValueError(f"unknown battery {battery!r} (use strict|archive|heldout)")
    if prompt_variant not in L.PROMPT_VARIANTS:
        raise ValueError(f"unknown prompt variant {prompt_variant!r}")

    questions = []
    for _, row in question_map.iterrows():
        qid = row["Question"]
        if qid not in keep:
            continue
        response_type = str(row["ResponseType"])
        is_numeric = response_type == "numeric_open"
        if is_numeric:
            if qid not in numeric_support:
                raise ValueError(
                    f"{qid} is numeric_open but no option grid was supplied — "
                    "the model-only scorer never derives grids from human data")
            codes = [str(c) for c in numeric_support[qid]]
            labels = list(codes)
        else:
            codes, labels = L.parse_fixed_options(row)
        if len(codes) < 2:
            raise ValueError(f"{qid}: fewer than two response codes")
        entry = {
            "question_id": qid, "response_type": response_type,
            "codes": codes, "labels": labels,
            "is_numeric_open": is_numeric,
            "is_ordered": qid not in L.E.NOMINAL_QUESTION_IDS,
            "gps_dimension": row.get("gps_dimension"),
        }
        if not sanitized:
            entry["question_text"] = str(row["StandaloneQuestion"])
        if prompt_variant != "v1":  # v1 specs stay byte-identical to the frozen surface
            entry["prompt_variant"] = prompt_variant
        questions.append(entry)

    if battery == "strict" and len(questions) != len(keep):
        raise AssertionError(
            f"strict battery must yield exactly {len(keep)} questions, got {len(questions)}")
    if battery == "heldout" and len(questions) != len(keep):
        raise AssertionError(f"held-out battery yielded {len(questions)} of {len(keep)} items")
    spec = {"battery": battery, "sanitized": bool(sanitized),
            "n_questions": len(questions), "questions": questions}
    if prompt_variant != "v1":
        spec["prompt_variant"] = prompt_variant
    return spec


def spec_sha256(spec: dict) -> str:
    blob = json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def write_spec(spec: dict, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"spec_sha256": spec_sha256(spec), **spec}
    path.write_text(json.dumps(payload, indent=2))
    print(f"spec -> {path}  ({spec['n_questions']} questions, "
          f"sha256 {payload['spec_sha256'][:16]}…)")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--battery", choices=["strict", "archive", "heldout"], default="strict")
    ap.add_argument("--prompt-variant", default="v1", choices=list(L.PROMPT_VARIANTS))
    ap.add_argument("--question-map", default=None,
                    help="alternate question map CSV (the held-out pool); default: frozen map")
    ap.add_argument("--heldout-items-file", default=None, help="JSON list of held-out item ids")
    ap.add_argument("--out", required=True, help="output spec JSON path (local)")
    ap.add_argument("--sanitized", action="store_true",
                    help="omit question_text (for the durable/uploadable copy)")
    ap.add_argument("--numeric-grid-json", default=None,
                    help="JSON file {question_id: [codes]} pinning numeric grids")
    a = ap.parse_args()

    qmap = L.load_question_map(a.question_map) if a.question_map else L.load_question_map()
    heldout = json.loads(Path(a.heldout_items_file).read_text()) if a.heldout_items_file else None
    grids: dict[str, list[str]] = {}
    if a.numeric_grid_json:
        grids = {k: [str(c) for c in v]
                 for k, v in json.loads(Path(a.numeric_grid_json).read_text()).items()}
    spec = build_scoring_spec(qmap, numeric_support=grids, battery=a.battery,
                              sanitized=a.sanitized, prompt_variant=a.prompt_variant,
                              heldout_items=heldout)
    write_spec(spec, Path(a.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
