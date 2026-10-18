"""Gap table, taus and export from the streamed passes (``stream8b.py`` outputs).

    python analyze8b.py --dir SCRATCH --snapshot DIR --key llama31_8b --items wvs_Q81 bank_USA_...

Reads ``SCRATCH/<item>_<dtype>.pt`` (capture) and ``SCRATCH/parity.pt``. Writes
``plans/stage1_8b_gaps.json`` and, with ``--export``, the run files under ``exports/<key>/``.
Every relative error is |error| / scale with the scale ``gates.py`` divides by.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import torch

HERE = Path(__file__).resolve()
WORKBENCH = HERE.parents[2]
sys.path.insert(0, str(WORKBENCH / "src"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(WORKBENCH.parent / "paper_b"))

from sca2_workbench import export as EX  # noqa: E402
from sca2_workbench import gates as G  # noqa: E402
from sca2_workbench import llama_capture as LC  # noqa: E402
from sca2_workbench import stream_capture as SC  # noqa: E402
from sca2_workbench import stream_export as SE  # noqa: E402

ONE = G.GateTaus(1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
CHECKS = ("residual_closure", "step_closure", "head_closure", "readout")
MULT = G.TAU_MULTIPLE


def pow10(x: float) -> float:
    return 10.0 ** math.ceil(math.log10(x)) if x > 0 else 0.0


def rel(a, b) -> float:
    a, b = a.double(), b.double()
    return ((a - b).abs().max() / max(b.abs().max().item(), 1.0)).item()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--key", default="llama31_8b")
    ap.add_argument("--label", default="Llama-3.1-8B-Instruct (base, streamed)")
    ap.add_argument("--model-id", default="meta-llama/Llama-3.1-8B-Instruct")
    ap.add_argument("--items", nargs="+", required=True)
    ap.add_argument("--report", default=str(WORKBENCH / "plans" / "stage1_8b_gaps"))
    ap.add_argument("--export", action="store_true")
    args = ap.parse_args()
    d = Path(args.dir)
    par = torch.load(d / "parity.pt", weights_only=True)

    rec = {}
    for it in args.items:
        c64 = torch.load(d / f"{it}_float64.pt", weights_only=True)
        c32 = torch.load(d / f"{it}_float32.pt", weights_only=True)
        p = par["items"][it]
        hf = p["logits_last"]
        assert c64["ids"] == p["ids"] == c32["ids"], "ids differ between passes / Paper B"
        ct = c64["code_token"]
        pb = dict(zip(p["codes"], p["probs"]))
        r = {"T": c64["plain"]["T"], "stats": {"f64": c64["stats"], "f32": c32["stats"]}}
        for name, c in (("f64", c64), ("f32", c32)):
            g = G.check_capture(c["plain"], ONE)
            r[name] = {k: g[k].rel for k in CHECKS}
            r[name]["logits_reference"] = ((c["plain"]["logits_last"].double() - hf.double()).abs().max().item()
                                           / hf.abs().max().item())
            probs = LC.code_probs(c["plain"]["logits_last"], ct)
            r[name]["parity_prob_gap"] = max(abs(probs[k] - pb[k]) for k in pb)
            r[name]["probs"] = probs
            r[name]["margin"] = c["plain"]["margin"]
        a, b = c32["plain"], c64["plain"]
        r["pair"] = {
            "margin_rel": abs(a["margin"] - b["margin"]) / (abs(b["margin"]) + 1.0),
            "logits_last_rel": rel(a["logits_last"], b["logits_last"]),
            "head_attr_rel": rel(a["head_attr"], b["head_attr"]),
            "neuron_attr_rel": rel(a["neuron_attr"], b["neuron_attr"]),
            "prob_gap": max(abs(r["f32"]["probs"][k] - r["f64"]["probs"][k]) for k in pb),
            "resid_rel_by_layer": [((a["_resid"][l].double() - b["_resid"][l]).abs().max()
                                    / b["_resid"][l].abs().max().clamp(min=1.0)).item()
                                   for l in range(a["_resid"].shape[0])],
            "f32_closure_rel_by_layer": [e / max(b["_resid"][l + 1].abs().max().item(), 1.0)
                                         for l, e in enumerate(a["residual_closure_by_layer"])],
            "f32_step_rel_by_layer": (a["step_err_by_layer"].double()
                                      / b["_resid"][1:].abs().amax((1, 2)).clamp(min=1.0)).tolist(),
        }
        r["f64_gates_at_135M_taus"] = {k: v.ok for k, v in G.check_capture(b, G.TAUS_F64).items()}
        r["f64_clamped_rel"] = {k: v.rel for k, v in G.check_capture(c64["clamped"], ONE).items()}
        r["paper_b"] = {"probs": pb, "scores": p["scores"]}
        rec[it] = r

    # ---- taus: 10x the largest observed, next power of ten (gates.TAU_MULTIPLE) ----
    taus = {}
    for name, key in (("f64", "TAUS_F64"), ("f32", "TAUS_F32")):
        old = getattr(G, key).as_dict()
        new = dict(old)
        worsts = {}
        for k in (*CHECKS, "logits_reference"):
            worst = max(rec[it][name][k] for it in rec)
            worsts[k] = worst
            new[k] = pow10(MULT * worst) if worst > 0 else old[k]     # exactly 0 keeps the old tau
        taus[name] = {"tau": new, "worst": worsts}
    parity_worst = max(max(rec[it][n]["parity_prob_gap"] for it in rec) for n in ("f64", "f32"))
    parity_tau = pow10(MULT * parity_worst)

    out = {"rec": rec, "taus": taus, "parity_tau": parity_tau, "parity_worst": parity_worst}
    Path(args.report + ".json").write_text(json.dumps(out, indent=1, default=float))
    for n in taus:
        print(n, "tau", {k: f"{v:.0e}" for k, v in taus[n]["tau"].items()})
        print(n, "worst", {k: f"{v:.2e}" for k, v in taus[n]["worst"].items()})
    print("parity worst", f"{parity_worst:.2e}", "tau", f"{parity_tau:.0e}")
    for it, r in rec.items():
        print(it, "T", r["T"], r["stats"])
        for n in ("f64", "f32"):
            print("  ", n, {k: f"{v:.2e}" for k, v in r[n].items() if k not in ("probs", "margin")})
        print("   pair", {k: f"{v:.2e}" for k, v in r["pair"].items() if not isinstance(v, list)})

    if args.export:
        import eval_config as E  # noqa: PLC0415
        import stream8b as B  # noqa: PLC0415
        from transformers import AutoTokenizer  # noqa: PLC0415
        tok = AutoTokenizer.from_pretrained(args.snapshot)
        exp_dir = EX.EXPORTS / args.key
        exp_dir.mkdir(parents=True, exist_ok=True)
        for dt, nm, suffix in (("float64", "f64", ""), ("float32", "f32", "_f32")):
            tau_set = G.GateTaus(**taus[nm]["tau"])
            src = SC.SafetensorsSource(args.snapshot, torch.float64 if dt == "float64" else torch.float32)
            for it in args.items:
                c = torch.load(d / f"{it}_{dt}.pt", weights_only=True)
                p = B.paper_b_inputs(tok, it)
                man, binw = SE.run_manifest(
                    key=args.key + suffix, label=f"{args.label} [{dt}]", model_id=args.model_id,
                    src=src, tok=tok, item=p["item"], ro=p["ro"], plain=c["plain"], clamped=c["clamped"],
                    taus=tau_set, hf_logits_last=par["items"][it]["logits_last"],
                    paper_b_probs=rec[it]["paper_b"]["probs"], parity_tau=parity_tau, stats=c["stats"],
                    chat_kwargs={"date_string": E.ARCHIVE_CHAT_DATE})
                stem = f"run__{args.key}{suffix}__{it}"
                man["bin"] = f"{stem}.bin"
                binw.write(exp_dir / f"{stem}.bin")
                (exp_dir / f"{stem}.json").write_text(json.dumps(man, indent=1))
                print("EXPORT", stem, "pass", man["conservation"]["pass"],
                      (exp_dir / f"{stem}.bin").stat().st_size, "bytes bin")


if __name__ == "__main__":
    main()
