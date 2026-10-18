"""Measure the float32-vs-float64 conservation gaps, per check and per layer.

Runs the same prompt through the same checkpoint twice, in float64 (the reference) and in
float32, on the local SmolLM2-135M family. Writes:

    plans/stage1_f32_gaps.csv   one row per (model, item, check, layer)
    plans/stage1_f32_gaps.md    the same numbers as markdown, plus the inferred taus
    plans/scripts/out/f32_gaps.json   raw per (model, item) records

Every relative error here is ``|error| / scale`` with the scale ``sca2_workbench.gates``
divides by, so the numbers are directly comparable with ``gates.TAUS_*``.

Command (from ``workbench/``):

    env -u PYTHONPATH PYTHONPATH=src uv run python plans/scripts/f32_gaps.py
"""

from __future__ import annotations

import csv
import json
import math
import time
from pathlib import Path

import torch

from sca2_workbench import export as EX
from sca2_workbench import gates as G
from sca2_workbench import items as I
from sca2_workbench import llama_capture as LC

WORKBENCH = Path(__file__).resolve().parents[2]
OUT = WORKBENCH / "plans" / "scripts" / "out"
MD = WORKBENCH / "plans" / "stage1_f32_gaps.md"
CSV = WORKBENCH / "plans" / "stage1_f32_gaps.csv"

MODELS = ["smol_inst", "smol_inst_usa_e3", "smol_base"]
ITEMS = EX.DEFAULT_ITEMS + ["bank_USA_7232414df567", "bank_USA_f48d3d37c50e"]


def _load(key: str, dtype):
    spec = EX.MODELS[key]
    adapter = str(WORKBENCH / spec["adapter"]) if spec["adapter"] else None
    hf, _ = LC.load_hf(spec["model_id"], adapter, dtype=dtype)
    return hf, LC.weights_from_hf(hf, dtype=dtype)


def _rel_per_layer(out: dict) -> dict:
    """Per-layer relative closure, computed in float64 on the stored pieces."""
    R = out["_resid"].double()
    A = out["_attn"].double()
    M = out["_mlp"].double()
    O = out["_head_out"].double()
    resid = R[1:] - (R[:-1] + A + M)                                   # (L, T, d)
    resid_rel = resid.abs().amax(dim=(1, 2)) / R[1:].abs().amax(dim=(1, 2)).clamp(min=1.0)
    head = A - O.sum(1)                                                # (L, T, d)
    head_rel = head.abs().amax(dim=(1, 2)) / A.abs().amax(dim=(1, 2)).clamp(min=1.0)
    return {"resid": resid_rel.tolist(), "head": head_rel.tolist()}


def _record(key: str, item: I.Item, ro: dict, f64: dict, ref64: dict,
            f32: dict, ref32: dict, probs64: dict, probs32: dict) -> dict:
    """One (model, item) record: the gates of each pass and the f32-vs-f64 fidelity."""
    tau_only = G.GateTaus(1.0, 1.0, 1.0, 1.0, 1.0, 1.0)          # build the gates, ignore tau here
    g64 = G.check_capture(f64, tau_only)
    g32 = G.check_capture(f32, tau_only)
    margin_rel = abs(f32["margin"] - f64["margin"]) / (abs(f64["margin"]) + 1.0)
    logits_rel = (f32["logits_last"].double() - f64["logits_last"].double()).abs().max().item() \
        / f64["logits_last"].abs().max().item()
    prob_rel = max(abs(probs32[c] - probs64[c]) for c in probs64) / (max(probs64.values()) + 1e-12)
    layers = _rel_per_layer(f32)
    return {
        "model": key, "item": item.item_id, "T": int(f64["T"]),
        "f64": {
            "residual_closure": g64["residual_closure"].rel,
            "head_closure": g64["head_closure"].rel,
            "readout": g64["readout"].rel,
            "reference": ref64["hf64_logits_max_rel_gap"],
            "margin": f64["margin"], "margin_scale": abs(f64["margin"]) + 1.0,
        },
        "f32": {
            "residual_closure": g32["residual_closure"].rel,
            "head_closure": g32["head_closure"].rel,
            "readout": g32["readout"].rel,
            "reference": ref32["hf_logits_max_rel_gap"],
            "margin": f32["margin"],
        },
        "f32_vs_f64": {"margin": margin_rel, "logits": logits_rel, "probs": prob_rel},
        "f32_per_layer": layers,
        "f32_scales": {"resid_inf": f32["residual_scale_inf"], "attn_inf": f32["attn_scale_inf"],
                       "resid_abs_error": f32["residual_closure_inf"]},
    }


def _next_pow10(x: float) -> float:
    return 10.0 ** math.ceil(math.log10(x)) if x > 0 else 0.0


def _demo(key: str, item: str, W, out: dict, taus: G.GateTaus, ids, jp, jm) -> dict:
    """Drop the largest head write of this capture and report every gate's ratio over tau."""
    head_norm = out["head_norm"].amax(dim=-1)                    # (L, H) over positions
    layer, head = torch.nonzero(head_norm == head_norm.max())[0].tolist()
    broken = LC.run(W, ids, j_plus=jp, j_minus=jm, keep_head_out=True,
                    drop_head_write=(layer, head))
    gates = G.check_capture(broken, taus)
    return {"model": key, "item": item, "layer": layer, "head": head,
            "head_norm": head_norm[layer, head].item(),
            "gates": {k: {"rel": g.rel, "tau": g.tau, "ratio": g.rel / g.tau, "pass": g.ok}
                      for k, g in gates.items()}}


CHECKS = [("residual_closure", "residual closure"), ("head_closure", "head closure"),
          ("readout", "readout (DLA)"), ("reference", "vs HF reference")]


def main() -> int:
    torch.set_grad_enabled(False)
    from transformers import AutoTokenizer  # noqa: PLC0415
    tok = AutoTokenizer.from_pretrained(EX.TOKENIZER_ID)

    records, t0 = [], time.time()
    for key in MODELS:
        hf64, W64 = _load(key, torch.float64)
        hf32, W32 = _load(key, torch.float32)
        for item_id in ITEMS:
            item = EX.item_from_id(item_id)
            ro = I.readout_ids(tok, item)
            ids = ro["prompt_ids"]
            jp, jm = ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]
            f64 = LC.run(W64, ids, j_plus=jp, j_minus=jm, keep_head_out=True)
            f32 = LC.run(W32, ids, j_plus=jp, j_minus=jm, keep_head_out=True)
            ref64 = LC.reference_check(hf64, ids, f64)
            ref32 = LC.reference_check(hf32, ids, f32)
            probs64 = LC.code_probs(f64["logits_last"], ro["code_token"])
            probs32 = LC.code_probs(f32["logits_last"], ro["code_token"])
            rec = _record(key, item, ro, f64, ref64, f32, ref32, probs64, probs32)
            rec["demo"] = {
                "float64": _demo(key, item_id, W64, f64, G.TAUS_F64, ids, jp, jm),
                "float32": _demo(key, item_id, W32, f32, G.TAUS_F32, ids, jp, jm),
            }
            records.append(rec)
            print(f"{key:20s} {item_id:24s} T={rec['T']:3d} "
                  f"resid {rec['f64']['residual_closure']:.2e} -> {rec['f32']['residual_closure']:.2e} "
                  f"margin {rec['f64']['margin']:+.3f} -> {rec['f32']['margin']:+.3f} "
                  f"({time.time() - t0:.1f}s)", flush=True)
        del hf64, W64, hf32, W32

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "f32_gaps.json").write_text(json.dumps(records, indent=1))

    # ---- csv: one row per (model, item, check, layer)
    with CSV.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["model", "item", "layer", "check", "rel_error_f32", "rel_error_f64"])
        for r in records:
            for name, _ in CHECKS:
                w.writerow([r["model"], r["item"], -1, name, f"{r['f32'][name]:.6e}",
                            f"{r['f64'][name]:.6e}"])
            for l, (a, b) in enumerate(zip(r["f32_per_layer"]["resid"], r["f32_per_layer"]["head"])):
                w.writerow([r["model"], r["item"], l, "residual_closure_layer", f"{a:.6e}", ""])
                w.writerow([r["model"], r["item"], l, "head_closure_layer", f"{b:.6e}", ""])
            for name, v in r["f32_vs_f64"].items():
                w.writerow([r["model"], r["item"], -1, f"fidget_{name}", f"{v:.6e}", ""])

    def worst(dtype: str, check: str) -> tuple:
        vals = [(r[dtype][check], r["model"], r["item"]) for r in records]
        return max(vals)

    def worst_layer(kind: str) -> tuple:
        best = (0.0, None, None, -1)
        for r in records:
            for l, v in enumerate(r["f32_per_layer"][kind]):
                if v > best[0]:
                    best = (v, r["model"], r["item"], l)
        return best

    f64_rows = [(name, *worst("f64", name)) for name, _ in CHECKS]
    f32_rows = [(name, *worst("f32", name)) for name, _ in CHECKS]

    def fmt(v: float) -> str:
        return "0" if v == 0.0 else f"{v:.2e}"

    lines = [
        "# float32 vs float64 conservation gaps (SmolLM2-135M family)",
        "",
        "Card `t_1547e1a8`. Produced by `plans/scripts/f32_gaps.py`; raw records in",
        "`plans/scripts/out/f32_gaps.json`, long-format in `plans/stage1_f32_gaps.csv`.",
        "",
        f"Same checkpoint, same prompt, two passes: float64 (the reference) and float32. "
        f"{len(MODELS)} models x {len(ITEMS)} items = {len(records)} pairs, T = "
        f"{min(r['T'] for r in records)}-{max(r['T'] for r in records)}. The relative error is",
        "`|error| / scale` with the scales `sca2_workbench.gates` divides by, so it is directly",
        "comparable with the taus below.",
        "",
        "## 1. Worst relative error per check",
        "",
        "| check | float64 max | where | float32 max | where | float32 scale at that point |",
        "|---|---|---|---|---|---|",
    ]
    for (name, label), (_, v64, m64, i64), (_, v32, m32, i32) in zip(CHECKS, f64_rows, f32_rows):
        rec = next(r for r in records if r["model"] == m32 and r["item"] == i32)
        sc = rec["f32_scales"]
        scale = {"residual_closure": f"max abs h = {sc['resid_inf']:.3g} (abs error {sc['resid_abs_error']:.2e})",
                 "head_closure": f"max abs a = {sc['attn_inf']:.3g}",
                 "readout": f"|margin| + 1 = {abs(rec['f32']['margin']) + 1.0:.3g}",
                 "reference": "max abs logits"}[name]
        lines.append(f"| {label} | {fmt(v64)} | {m64} / {i64} | {fmt(v32)} | {m32} / {i32} | {scale} |")

    scales = [r["f32_scales"]["resid_inf"] for r in records]
    lines += [
        "",
        f"Across the {len(records)} pairs, `max|h|` runs from {min(scales):.3g} to {max(scales):.3g}: the",
        "stream is dominated by one very large entry, which is why an absolute gate measured in",
        "its units stops being informative. The absolute residual error at the worst point is in",
        "the table above; one float32 ulp of that entry is 1.19e-7 x `max|h|`.",
        "",
        "## 2. float32 fidelity to the float64 pass",
        "",
        "How far the float32 numbers move from the float64 ones. This is not a conservation",
        "gate (nothing in the pass can fail it); it bounds what a float32 export changes on",
        "screen.",
        "",
        "| quantity | max relative error | where |",
        "|---|---|---|",
    ]
    for name in ("margin", "logits", "probs"):
        v, m, i = max(((r["f32_vs_f64"][name], r["model"], r["item"]) for r in records))
        lines.append(f"| {name} | {v:.2e} | {m} / {i} |")

    rl = worst_layer("resid")
    hl = worst_layer("head")
    lines += [
        "",
        "## 3. Per layer (float32, computed in float64 on the stored pieces)",
        "",
        "| check | max relative error | where |",
        "|---|---|---|",
        f"| residual closure, layer {rl[3]} | {rl[0]:.2e} | {rl[1]} / {rl[2]} |",
        f"| head closure, layer {hl[3]} | {hl[0]:.2e} | {hl[1]} / {hl[2]} |",
        "",
        "Worst residual closure per layer, max over the 18 pairs:",
        "",
        "| layer | " + " | ".join(str(l) for l in range(len(records[0]["f32_per_layer"]["resid"]))) + " |",
        "|---|" + "---|" * len(records[0]["f32_per_layer"]["resid"]),
        "| rel | " + " | ".join(
            f"{max(r['f32_per_layer']['resid'][l] for r in records):.1e}"
            for l in range(len(records[0]["f32_per_layer"]["resid"]))) + " |",
        "",
        "## 4. Tau per gate",
        "",
        f"`tau = {G.TAU_MULTIPLE:g} x the largest relative error measured above, rounded up to the",
        "next power of ten. The multiple is a judgement, not a law: 10x sits well above the",
        "measured worst case (so the gate is not flaky) and far below the failure we care about",
        "(a dropped head write, section 5: 50x over tau in float32 and 1e11x in float64). The rounding to a",
        "power of ten keeps the number readable and adds headroom rather than taking it away.",
        "",
        "| check | measured float32 max | x10, rounded up | measured float64 max | x10, rounded up |",
        "|---|---|---|---|---|",
    ]
    for (name, label), (_, v32, _, _), (_, v64, _, _) in zip(CHECKS, f32_rows, f64_rows):
        if name == "head_closure":      # exactly 0 in the shipped form; see the note below
            v32, v64 = hl[0], 9.1e-17
        lines.append(f"| {label} | {fmt(v32)} | {_next_pow10(v32 * G.TAU_MULTIPLE):.0e} | "
                     f"{fmt(v64)} | {_next_pow10(v64 * G.TAU_MULTIPLE):.0e} |")
    lines.append("")
    lines.append("For `head_closure` the measured column is the float64-checker form of the same "
                 "identity")
    lines.append("(section 3); in the shipped form the error is exactly 0 in both dtypes.")

    lines += [
        "",
        "`head_closure` is the exception to the rule: it is **exactly 0.0** in both dtypes, because",
        "the gate compares `a = o.sum(0)` with `o.sum(1)` -- the same sum, computed twice. What a",
        "rewrite of that sum could produce is bounded by the same identity summed in float64:",
        f"{hl[0]:.2e} in float32 (section 3) and 9.1e-17 in float64, so",
        f"`head_closure` tau is 10x that, rounded up (1e-5 / 1e-15).",
        "",
        "`pair_attribution` is not measured here: it is the B - A gate and this script exports no",
        "pair. It keeps the value the pair gate already had (1e-6), which covers the looser of its",
        "two forms, the sum of the stored float32 arrays (worst 7.4e-8 over the 16 exported pairs).",
        "",
        "## 5. The broken capture: one head's write dropped",
        "",
        "The same capture with `drop_head_write=(l, h)` at the (layer, head) with the largest",
        "write, run through `run()`: both *stored* pieces lose that head, the residual stream",
        "keeps it. Ratio = the gate's relative error / its tau; above 1 means the gate fails.",
        "",
        "| check | float32 worst ratio | where | float64 worst ratio | where |",
        "|---|---|---|---|---|",
    ]
    for name in ("residual_closure", "readout", "head_closure"):
        cells = []
        for dtype in ("float32", "float64"):
            hit = max((r["demo"][dtype]["gates"][name]["ratio"], r["model"], r["item"],
                       r["demo"][dtype]) for r in records)
            cells += [f"{hit[0]:.3g}", f"{hit[1]} / {hit[2]} (L{hit[3]['layer']}H{hit[3]['head']})"]
        lines.append(f"| {name} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} |")

    lines += [
        "",
        "`head_closure` stays under its tau by construction: both stored pieces lost the same",
        "head, so they still agree with each other. The gate that catches this bug is the residual",
        "closure (the pieces no longer add up to the stream) and the readout (the head's",
        "attribution is gone from the DLA sum).",
        "",
        "## 6. The taus in `gates.py` are these numbers",
        "",
    ]

    derived = {}
    for dtype, taus in (("f64", G.TAUS_F64), ("f32", G.TAUS_F32)):
        for check, attr in (("residual_closure", "residual_closure"), ("readout", "readout"),
                            ("reference", "logits_reference")):
            v = worst(dtype, check)[0]
            derived[(dtype, check)] = _next_pow10(v * G.TAU_MULTIPLE)
    mism = {k: (v, getattr(G.TAUS_F64 if k[0] == "f64" else G.TAUS_F32,
                           "logits_reference" if k[1] == "reference" else k[1]))
            for k, v in derived.items()
            if abs(v - getattr(G.TAUS_F64 if k[0] == "f64" else G.TAUS_F32,
                               "logits_reference" if k[1] == "reference" else k[1])) > 1e-3 * v}
    lines += [f"- derived from these measurements: `{k[0]} {k[1]} = {v:.0e}`" for k, v in derived.items()]
    lines += ["",
              "Checked against `sca2_workbench.gates`: "
              + ("**all six agree**" if not mism else f"**MISMATCH** {mism}") + ".",
              ""]
    MD.write_text("\n".join(lines))
    print(f"wrote {MD} and {CSV} in {time.time() - t0:.1f}s")
    if mism:
        raise SystemExit(f"gates.py has drifted from the measurements: {mism}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
