"""One streamed pass, or the Paper B parity pass, in its own process (so peak RSS is per pass).

    capture:  python stream8b.py capture --snapshot DIR --item wvs_Q81 --dtype float64 --out OUT
    parity:   python stream8b.py parity   --snapshot DIR --items wvs_Q81 bank_USA_00023ac74dac --out OUT

``capture`` streams the prompt through the model one layer at a time (plain + Quadrant-III-clamped
pass off one read of each layer) and saves the result with wall time and peak RSS.
``parity`` builds a Hugging Face model that holds one block at a time, in float32, and runs
Paper B's own ``score_cohort.sequence_logprob`` on it (unmodified, imported read-only). It also
saves the HF full-vocabulary logits at t*, the reference the ``logits_reference`` gate divides.

The input ids come from Paper B's ``prepare_prompt_for_model`` (pinned chat date included), and
are asserted equal to the workbench's own (``items.readout_ids`` with the same ``chat_kwargs``).

Run with:  env -u PYTHONPATH uv run --project workbench --with pandas python plans/scripts/stream8b.py ...
(pandas is Paper B's import; it is not a workbench dependency).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve()
WORKBENCH = HERE.parents[2]
REPO = WORKBENCH.parent
sys.path.insert(0, str(WORKBENCH / "src"))
sys.path.insert(0, str(REPO / "paper_b"))          # read-only import of Paper B

from sca2_workbench import export as EX  # noqa: E402
from sca2_workbench import items as I  # noqa: E402
from sca2_workbench import stream_capture as SC  # noqa: E402

RSS_STOP_GB = 16.0


def paper_b_inputs(tok, item_id: str) -> dict:
    """Item -> Paper B's prompt text, Paper B's prepared ids, and our ids; asserts they agree."""
    import eval_config as E  # noqa: PLC0415
    import eval_lib as L  # noqa: PLC0415
    import score_cohort as S  # noqa: PLC0415

    item = EX.item_from_id(item_id)
    if item.kind == "wvs":                                  # Paper B's own loaders
        qm = L.load_question_map()
        row = qm[qm["Question"].astype(str).str.strip() == item.meta["question_id"]].iloc[0]
        codes, labels = L.parse_fixed_options(row)
        spec = {"question_text": row["StandaloneQuestion"], "codes": codes, "labels": labels,
                "is_numeric_open": False}
    else:                                                   # bank scenario posed as a survey item
        text = item.parts[1][2]
        spec = {"question_text": text[len("Question:\n"):-2], "codes": list(item.codes),
                "labels": list(item.labels), "is_numeric_open": False}
    prompt_text = L.build_survey_user_prompt(spec)
    if prompt_text != item.user_prompt:
        raise AssertionError(f"{item_id}: Paper B prompt != workbench prompt")
    prepared = S.prepare_prompt_for_model(tok, prompt_text)
    if prepared["prompt_was_truncated"]:
        raise AssertionError(f"{item_id}: Paper B truncated the prompt")
    ro = I.readout_ids(tok, item, {"date_string": E.ARCHIVE_CHAT_DATE})
    ours = ro["prompt_ids"]
    if ours[:-len(ro["prefix_ids"])] != prepared["model_prompt_ids"] or \
            ro["formatted_prompt"] != prepared["formatted_prompt"]:
        raise AssertionError(f"{item_id}: workbench ids != Paper B prepare_prompt_for_model ids")
    return {"item": item, "ro": ro, "prompt_text": prompt_text, "prepared": prepared,
            "codes": list(item.codes)}


def capture(args) -> None:
    from transformers import AutoTokenizer  # noqa: PLC0415

    tok = AutoTokenizer.from_pretrained(args.snapshot)
    p = paper_b_inputs(tok, args.item)
    item, ro = p["item"], p["ro"]
    dtype = {"float64": torch.float64, "float32": torch.float32}[args.dtype]
    jp, jm = ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]

    def log(msg: str) -> None:
        l = int(msg.split()[1].split("/")[0])
        if l % 4 == 0 or l == 1:
            print(f"[{args.item} {args.dtype}] {msg}", flush=True)
        if SC.peak_rss_gb() > RSS_STOP_GB:
            raise SystemExit(f"STOP: peak RSS {SC.peak_rss_gb():.1f} GB > {RSS_STOP_GB} GB")

    t0 = time.time()
    src = SC.SafetensorsSource(args.snapshot, dtype)
    plain, clamped = SC.run_streamed(src, ro["prompt_ids"], j_plus=jp, j_minus=jm,
                                     clamps=(False, True), full_logits=True, keep_resid=True,
                                     log=log)
    stats = {"item": args.item, "dtype": args.dtype, "T": plain["T"],
             "wall_seconds": round(time.time() - t0, 1), "peak_rss_gb": round(SC.peak_rss_gb(), 2),
             "torch": str(torch.__version__), "threads": torch.get_num_threads()}
    print("PASS", json.dumps(stats), flush=True)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"plain": plain, "clamped": clamped, "ids": ro["prompt_ids"],
                "code_token": ro["code_token"], "stats": stats}, out)


def parity(args) -> None:
    import eval_config as E  # noqa: PLC0415
    import eval_lib as L  # noqa: PLC0415
    import score_cohort as S  # noqa: PLC0415
    from transformers import AutoTokenizer  # noqa: PLC0415

    from sca2_workbench.offload_hf import build_offloaded_hf  # noqa: PLC0415

    tok = AutoTokenizer.from_pretrained(args.snapshot)
    model = build_offloaded_hf(args.snapshot, torch.float32)
    result = {}
    t0 = time.time()
    for item_id in args.items:
        p = paper_b_inputs(tok, item_id)
        scores = []
        for code in p["codes"]:
            logp, ntok = S.sequence_logprob(model, tok, p["prompt_text"], f"{E.COMPLETION_PREFIX}{code}")
            scores.append(logp)
            print(f"[parity {item_id}] code {code}: sequence_logprob {logp:.6f} ({ntok} tokens)  "
                  f"{time.time() - t0:.0f}s  peak RSS {SC.peak_rss_gb():.2f} GB", flush=True)
            if SC.peak_rss_gb() > RSS_STOP_GB:
                raise SystemExit(f"STOP: peak RSS {SC.peak_rss_gb():.1f} GB")
        probs = L.stable_softmax(scores, E.OPTION_SCORE_TEMPERATURE)
        ids = torch.tensor([p["ro"]["prompt_ids"]])
        with torch.no_grad():
            logits_last = model(input_ids=ids).logits[0, -1].clone()
        result[item_id] = {"codes": p["codes"], "scores": scores, "probs": [float(x) for x in probs],
                           "ids": p["ro"]["prompt_ids"], "code_token": p["ro"]["code_token"],
                           "ids_equal_paper_b": True, "logits_last": logits_last}
    stats = {"wall_seconds": round(time.time() - t0, 1), "peak_rss_gb": round(SC.peak_rss_gb(), 2)}
    print("PARITY_DONE", json.dumps(stats), flush=True)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"items": result, "stats": stats}, out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["capture", "parity"])
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--item")
    ap.add_argument("--items", nargs="*")
    ap.add_argument("--dtype", choices=["float64", "float32"], default="float64")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    torch.set_num_threads(max(1, torch.get_num_threads()))
    {"capture": capture, "parity": parity}[args.mode](args)


if __name__ == "__main__":
    main()
