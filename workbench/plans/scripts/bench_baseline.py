"""Re-measure the PM baseline: per-stage times of one (model, prompt) on CPU float64, warm.

Run from workbench/:
    env -u PYTHONPATH PYTHONPATH=src uv run python plans/scripts/bench_baseline.py [--cold]

The stages are the same calls, in the same order, as ``export.capture_run``.
Writes nothing under exports/ (EXPORTS is redirected to $TMPDIR in --cold mode).
"""

import argparse
import json
import os
import resource
import statistics as st
import sys
import tempfile
import time
from pathlib import Path

import torch

from sca2_workbench import export as EX
from sca2_workbench import items as I
from sca2_workbench import llama_capture as LC


def rss_gb():
    # macOS ru_maxrss is bytes
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9


def stages(sess, key, item, reps=5):
    hf, W, _ = sess.model(key)
    ro = I.readout_ids(sess.tok, item)
    ids = ro["prompt_ids"]
    jp, jm = ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]
    comps = {c: sess.tok(" " + c, add_special_tokens=False).input_ids for c in item.codes}
    base_ids = ids[: len(ids) - len(ro["prefix_ids"])]
    rows = {k: [] for k in ("capture", "clamped", "hf_ref_x2", "eq6_tf", "export_total")}
    for r in range(reps + 1):                      # rep 0 is a discarded warm-up
        t = time.perf_counter(); out = LC.run(W, ids, j_plus=jp, j_minus=jm, keep_head_out=False)
        a = time.perf_counter() - t
        t = time.perf_counter(); LC.run(W, ids, j_plus=jp, j_minus=jm, clamp_q3=True)
        b = time.perf_counter() - t
        t = time.perf_counter(); LC.reference_check(hf, ids, out)
        c = time.perf_counter() - t
        t = time.perf_counter(); LC.teacher_forced_probs(hf, base_ids, comps)
        d = time.perf_counter() - t
        t = time.perf_counter(); EX.capture_run(sess, key, item, keep_head_out=True)
        e = time.perf_counter() - t
        if r:
            for k, v in zip(rows, (a, b, c, d, e)):
                rows[k].append(v)
    return len(ids), {k: round(st.median(v), 3) for k, v in rows.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cold", action="store_true")
    args = ap.parse_args()
    print("threads", torch.get_num_threads(), "torch", torch.__version__)
    if args.cold:
        EX.EXPORTS = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        t0 = time.perf_counter()
        sess = EX.Session()
        t1 = time.perf_counter()
        for k in ("smol_base", "smol_inst"):
            tt = time.perf_counter(); sess.model(k)
            print(f"load {k}: {time.perf_counter() - tt:.2f} s")
        print(f"tokenizer: {t1 - t0:.2f} s; both models: {time.perf_counter() - t1:.2f} s")
        EX.EXPORTS.joinpath("x").mkdir()
        t = time.perf_counter()
        EX.export_pair("smol_base", "smol_inst", ["wvs_Q57"])      # models already warm here
        print(f"warm pair export wvs_Q57: {time.perf_counter() - t:.2f} s; peak RSS {rss_gb():.2f} GB")
        print("exports dir", EX.EXPORTS)
        return
    sess = EX.Session()
    for item_id in EX.DEFAULT_ITEMS:
        T, row = stages(sess, "smol_inst", EX.item_from_id(item_id))
        print(json.dumps({"item": item_id, "T": T, **row}))
    print(f"peak RSS {rss_gb():.2f} GB")


if __name__ == "__main__":
    sys.exit(main())
