"""Proof that several first-30-minutes experiments already run today, from Python, with the shipped code.

Run from workbench/:
    env -u PYTHONPATH PYTHONPATH=src uv run python plans/scripts/experiments_poc.py
Nothing is written under exports/. Uses only SmolLM2-135M-Instruct (+ the usa_e3 adapter) and public items.
These are feasibility runs on single items. They are not findings about the models.
"""

import json
import sys
import time
from collections import defaultdict

from sca2_workbench import export as EX
from sca2_workbench import items as I
from sca2_workbench import llama_capture as LC


def question_text(item):
    p = item.user_prompt
    return p.split("Question:\n", 1)[1].split("\n\nSelect exactly", 1)[0]


def with_prompt(item, prompt, labels=None, j_plus=None):
    codes = item.codes
    labels = labels or item.labels
    j_plus = j_plus or item.j_plus
    j_minus = codes[0] if j_plus == codes[-1] else codes[-1]
    return I.Item(item.item_id + "*", item.kind, prompt, codes, labels, j_plus, j_minus, item.meta)


def show(tag, man):
    r = man["readout"]
    probs = {c: round(p, 3) for c, p in r["probs"].items()}
    print(f"  {tag:36s} T={len(man['tokens']):3d} margin={r['margin']:+.3f} probs={probs} "
          f"conservation_pass={man['conservation']['pass']}")


def main():
    sess = EX.Session()
    base = EX.item_from_id("wvs_Q57")
    q, codes, labels = question_text(base), base.codes, base.labels
    print("Q57:", q, "| codes", codes, "| labels", labels, "| j+ =", base.j_plus)

    print("(1) option-order reversal, (2) country persona, (3) paraphrase  [smol_inst, one item each]")
    man, _, _ = EX.capture_run(sess, "smol_inst", base)
    show("original", man)
    rev_labels = labels[::-1]
    rev = with_prompt(base, I.survey_prompt_v1(q, codes, rev_labels), rev_labels, j_plus=codes[-1])
    man, _, _ = EX.capture_run(sess, "smol_inst", rev)
    show("options reversed (j+ follows label)", man)
    persona = base.user_prompt.replace("Answer this questionnaire as an individual person.",
                                       "Answer this questionnaire as a typical adult living in Argentina.")
    assert persona != base.user_prompt
    man, _, _ = EX.capture_run(sess, "smol_inst", with_prompt(base, persona))
    show("persona: Argentina", man)
    para = "Would you say that having a job is among the most important things in life for a person like you?"
    man, _, _ = EX.capture_run(sess, "smol_inst", with_prompt(base, I.survey_prompt_v1(para, codes, labels)))
    show("paraphrase (hand-written)", man)

    print("(4) leave-one-word-out on Q57, margin shift vs original  [LC.run only]")
    hf, W, _ = sess.model("smol_inst")

    def margin(item):
        ro = I.readout_ids(sess.tok, item)
        o = LC.run(W, ro["prompt_ids"], j_plus=ro["code_token"][item.j_plus],
                   j_minus=ro["code_token"][item.j_minus])
        return o["margin"]

    m0 = margin(base)
    words = q.split()
    t0 = time.time()
    shifts = []
    for i, w in enumerate(words):
        q2 = " ".join(words[:i] + words[i + 1:])
        shifts.append((margin(with_prompt(base, I.survey_prompt_v1(q2, codes, labels))) - m0, w))
    print(f"  {len(words)} variants in {time.time() - t0:.1f} s; largest |shift|:",
          [(w, round(s, 3)) for s, w in sorted(shifts, key=lambda x: -abs(x[0]))[:3]])

    print("(5) per-GPS-dimension margin shift, e3 minus base, 4 held-out USA bank items per dimension [LC.run only]")
    log = json.loads((EX.WORKBENCH / "models/usa_e3/train_log.json").read_text())
    held = set(log["heldout_triplet_ids"])
    path = I.BANK_DIR / "D_syn_USA.jsonl"
    rows = [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]
    pick = defaultdict(list)
    for r in rows:
        if r["triplet_id"] in held and len(pick[r["gps_dimension"]]) < 4:
            pick[r["gps_dimension"]].append(r["triplet_id"])
    _, W3, _ = sess.model("smol_inst_usa_e3")
    t0 = time.time()
    n_runs = 0
    for dim in sorted(pick):
        d = []
        for tid in pick[dim]:
            it = EX.item_from_id(f"bank_USA_{tid}")
            ro = I.readout_ids(sess.tok, it)
            jp, jm = ro["code_token"][it.j_plus], ro["code_token"][it.j_minus]
            a = LC.run(W, ro["prompt_ids"], j_plus=jp, j_minus=jm)["margin"]
            b = LC.run(W3, ro["prompt_ids"], j_plus=jp, j_minus=jm)["margin"]
            d.append(b - a)
            n_runs += 2
        print(f"  {dim:11s} n={len(d)} mean d_margin={sum(d) / len(d):+.2f}  each={[round(x, 2) for x in d]}")
    print(f"  {n_runs} passes in {time.time() - t0:.1f} s")


if __name__ == "__main__":
    sys.exit(main())
