"""First real 8B pair: Llama-3.1-8B-Instruct (A) vs A + Paper B's USA LoRA (B), streamed, unmerged.

    layercheck: python pair8b.py layercheck --snapshot DIR --adapter DIR --out OUT.json
    capture:    python pair8b.py capture    --snapshot DIR --adapter DIR --item wvs_Q81 --out OUT.pt
    parity:     python pair8b.py parity     --snapshot DIR --adapter DIR --items ... --out OUT.pt
    export:     python pair8b.py export     --snapshot DIR --adapter DIR --items ... --dir SCRATCH

``layercheck`` = one layer, float64, unmerged ``W x + (a/r) B (A x)`` vs merged ``(W + (a/r) B A) x``
on the real weights and the real item. ``capture`` = A, A clamped, B, B clamped off one read of
each layer (``run_streamed_pair``), float64. ``parity`` = Paper B's own
``score_cohort.sequence_logprob`` on HF + peft (float32, LoRA unmerged by peft, one block resident).
``export`` = run files for A and B and the pair file at the top of ``exports/``, ``index.json``
rebuilt, report in ``plans/stage1_8b_pair.json``. Each pass in its own process (peak RSS per pass).

Run with: env -u PYTHONPATH uv run --project workbench --with pandas python plans/scripts/pair8b.py ...
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve()
WORKBENCH = HERE.parents[2]
REPO = WORKBENCH.parent
sys.path.insert(0, str(WORKBENCH / "src"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(REPO / "paper_b"))          # read-only import of Paper B

from sca2_workbench import export as EX  # noqa: E402
from sca2_workbench import gates as G  # noqa: E402
from sca2_workbench import llama_capture as LC  # noqa: E402
from sca2_workbench import stream_capture as SC  # noqa: E402
from sca2_workbench import stream_export as SE  # noqa: E402

MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"
KEY_A, KEY_B = "llama31_8b", "llama31_8b_usa"
LABEL_A = "Llama-3.1-8B-Instruct (streamed, float64)"
LABEL_B = "Llama-3.1-8B-Instruct + Paper B USA LoRA (streamed, unmerged, float64)"
RSS_STOP_GB = 16.0
ARCHIVE = REPO / "planning" / "sprint_2026-10-11" / "paper-b-20261011" / "scores_for_join"


def _guard_rss():
    if SC.peak_rss_gb() > RSS_STOP_GB:
        raise SystemExit(f"STOP: peak RSS {SC.peak_rss_gb():.1f} GB > {RSS_STOP_GB} GB")


def layercheck(args) -> None:
    import stream8b as B  # noqa: PLC0415
    from transformers import AutoTokenizer  # noqa: PLC0415

    tok = AutoTokenizer.from_pretrained(args.snapshot)
    p = B.paper_b_inputs(tok, "wvs_Q81")
    ro, item = p["ro"], p["item"]
    jp, jm = ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]
    src = SC.SafetensorsSource(args.snapshot, torch.float64)
    lora = SC.LoraAdapter(args.adapter, MODEL_ID)
    out = {"adapter": lora.describe(), "item": "wvs_Q81", "gate": 1e-12, "layers": {}}
    for layer in args.layers:
        t0 = time.time()
        lw, lo = src.layer(layer), lora.layer(layer, torch.float64)
        merged = dict(lw)
        for name, (A, Bm) in lo.items():
            merged[name] = lw[name] + lora.scale * (Bm @ A)
        gaps = SC.unmerged_vs_merged(src, ro["prompt_ids"], layer, lw, lo, merged, lora.scale,
                                     j_plus=jp, j_minus=jm)
        changed = gaps.pop("h_out (unmerged vs base)")
        worst = max(gaps, key=gaps.get)
        out["layers"][layer] = {"gaps": gaps, "worst": worst, "worst_gap": gaps[worst],
                                "pass": gaps[worst] <= 1e-12, "h_out_rel_change_vs_base": changed,
                                "wall_s": round(time.time() - t0, 1)}
        print(f"layer {layer}: worst {worst} {gaps[worst]:.2e}  (adapter moves h_out by {changed:.2e})"
              f"  peak RSS {SC.peak_rss_gb():.2f} GB", flush=True)
        _guard_rss()
    out["peak_rss_gb"] = round(SC.peak_rss_gb(), 2)
    Path(args.out).write_text(json.dumps(out, indent=1))
    if not all(v["pass"] for v in out["layers"].values()):
        raise SystemExit("FAIL: unmerged != merged")


def capture(args) -> None:
    import stream8b as B  # noqa: PLC0415
    from transformers import AutoTokenizer  # noqa: PLC0415

    tok = AutoTokenizer.from_pretrained(args.snapshot)
    p = B.paper_b_inputs(tok, args.item)
    item, ro = p["item"], p["ro"]
    jp, jm = ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]

    def log(msg: str) -> None:
        l = int(msg.split()[1].split("/")[0])
        if l % 4 == 0 or l == 1:
            print(f"[{args.item} pair f64] {msg}", flush=True)
        _guard_rss()

    t0 = time.time()
    src = SC.SafetensorsSource(args.snapshot, torch.float64)
    lora = SC.LoraAdapter(args.adapter, MODEL_ID)
    res = SC.run_streamed_pair(src, ro["prompt_ids"], lora, j_plus=jp, j_minus=jm,
                               full_logits=True, log=log)
    stats = {"item": args.item, "dtype": "float64", "T": res["a"]["T"], "passes": 4,
             "wall_seconds": round(time.time() - t0, 1), "peak_rss_gb": round(SC.peak_rss_gb(), 2),
             "torch": str(torch.__version__), "threads": torch.get_num_threads()}
    print("PASS", json.dumps(stats), flush=True)
    torch.save({**res, "ids": ro["prompt_ids"], "code_token": ro["code_token"], "stats": stats},
               args.out)


def parity(args) -> None:
    import eval_config as E  # noqa: PLC0415
    import eval_lib as L  # noqa: PLC0415
    import score_cohort as S  # noqa: PLC0415
    import stream8b as B  # noqa: PLC0415
    from transformers import AutoTokenizer  # noqa: PLC0415

    from sca2_workbench.offload_hf import build_offloaded_hf  # noqa: PLC0415

    tok = AutoTokenizer.from_pretrained(args.snapshot)
    model = build_offloaded_hf(args.snapshot, torch.float32, adapter_dir=args.adapter, model_id=MODEL_ID)
    result, t0 = {}, time.time()
    for item_id in args.items:
        p = B.paper_b_inputs(tok, item_id)
        scores = []
        for code in p["codes"]:
            logp, ntok = S.sequence_logprob(model, tok, p["prompt_text"], f"{E.COMPLETION_PREFIX}{code}")
            scores.append(logp)
            print(f"[parity+USA {item_id}] code {code}: {logp:.6f} ({ntok} tok)  {time.time() - t0:.0f}s"
                  f"  peak RSS {SC.peak_rss_gb():.2f} GB", flush=True)
            _guard_rss()
        probs = L.stable_softmax(scores, E.OPTION_SCORE_TEMPERATURE)
        with torch.no_grad():
            logits_last = model(input_ids=torch.tensor([p["ro"]["prompt_ids"]])).logits[0, -1].clone()
        result[item_id] = {"codes": p["codes"], "scores": scores, "probs": [float(x) for x in probs],
                           "ids": p["ro"]["prompt_ids"], "logits_last": logits_last}
    stats = {"wall_seconds": round(time.time() - t0, 1), "peak_rss_gb": round(SC.peak_rss_gb(), 2),
             "reference": "HF LlamaForCausalLM + peft get_peft_model (LoRA unmerged), float32, "
                          "one block resident"}
    print("PARITY_DONE", json.dumps(stats), flush=True)
    torch.save({"items": result, "stats": stats}, args.out)


def _archived(country: str, qid: str) -> dict | None:
    """Paper B's archived scored row for (country adapter, WVS question), if the repo holds one."""
    path = ARCHIVE / f"{country}_adapter_option_probabilities.csv"
    if not path.exists():
        return None
    rows = [r for r in csv.DictReader(path.open()) if r["question_id"] == qid]
    if not rows:
        return None
    return {"file": str(path.relative_to(REPO)), "adapter_revision": rows[0]["adapter_revision"],
            "run_id": rows[0]["run_id"],
            "probs": {r["option_code"]: float(r["model_prob"]) for r in rows},
            "logprobs": {r["option_code"]: float(r["option_logprob"]) for r in rows}}


def export(args) -> None:
    import eval_config as E  # noqa: PLC0415
    import stream8b as B  # noqa: PLC0415
    from transformers import AutoTokenizer  # noqa: PLC0415

    d = Path(args.dir)
    gaps8b = json.loads((WORKBENCH / "plans" / "stage1_8b_gaps.json").read_text())
    taus = G.GateTaus(**gaps8b["taus"]["f64"]["tau"])
    parity_tau = gaps8b["parity_tau"]
    par_a = torch.load(d / "parity.pt", weights_only=True)            # base, from t_7d7ad93e
    par_b = torch.load(d / "parity_usa.pt", weights_only=True)
    tok = AutoTokenizer.from_pretrained(args.snapshot)
    src = SC.SafetensorsSource(args.snapshot, torch.float64)
    lora = SC.LoraAdapter(args.adapter, MODEL_ID)
    t0 = time.time()
    dW_head, dW_mlp = SC.lora_weight_delta(lora, src)
    dw_s = round(time.time() - t0, 1)
    adapter_meta = {**lora.describe(), "repo": "Bonorinoa/SCA2-paper-b-adapters (dataset)",
                    "path_in_repo": "adapters/USA", "country": "USA",
                    "item_split": None,
                    "item_split_note": "unknown: the adapter's train/held-out split lives under data/, out of fence"}
    report = {"adapter": adapter_meta, "taus_f64_8b": taus.as_dict(), "parity_tau": parity_tau,
              "items": {}, "weight_delta_wall_s": dw_s}
    for it in args.items:
        c = torch.load(d / f"pair_{it}.pt", weights_only=True)
        p = B.paper_b_inputs(tok, it)
        assert c["ids"] == p["ro"]["prompt_ids"] == par_a["items"][it]["ids"] == par_b["items"][it]["ids"]
        ct = c["code_token"]
        rec = {"T": c["a"]["T"], "stats": c["stats"]}
        mans = {}
        for key, label, run, runc, par, ad in ((KEY_A, LABEL_A, c["a"], c["a_clamped"], par_a, None),
                                               (KEY_B, LABEL_B, c["b"], c["b_clamped"], par_b, adapter_meta)):
            pb = dict(zip(par["items"][it]["codes"], par["items"][it]["probs"]))
            man, binw = SE.run_manifest(
                key=key, label=label, model_id=MODEL_ID, src=src, tok=tok, item=p["item"], ro=p["ro"],
                plain=run, clamped=runc, taus=taus, hf_logits_last=par["items"][it]["logits_last"],
                paper_b_probs=pb, parity_tau=parity_tau, stats=c["stats"],
                chat_kwargs={"date_string": E.ARCHIVE_CHAT_DATE}, adapter=ad)
            if ad is not None:
                man["provenance"]["paper_b_reference"] = par_b["stats"]["reference"]
            stem = f"run__{key}__{it}"
            man["bin"] = f"{stem}.bin"
            binw.write(EX.EXPORTS / f"{stem}.bin")
            (EX.EXPORTS / f"{stem}.json").write_text(json.dumps(man, indent=1))
            mans[key] = man
            probs = man["readout"]["probs"]
            rec[key] = {"pass": man["conservation"]["pass"], "margin": run["margin"], "probs": probs,
                        "paper_b_probs": pb, "paper_b_scores": par["items"][it]["scores"],
                        "parity_gap": man["conservation"]["eq6_teacher_forced_max_abs_gap"],
                        "hf_logits_rel_gap": man["conservation"]["hf_logits_max_rel_gap"],
                        "relative": {k: v for k, v in man["conservation"]["relative"].items()
                                     if isinstance(v, dict) and "rel" in v},
                        "bin_bytes": (EX.EXPORTS / f"{stem}.bin").stat().st_size,
                        "json_bytes": (EX.EXPORTS / f"{stem}.json").stat().st_size}
            print("RUN", stem, "pass", man["conservation"]["pass"], "probs",
                  {k: round(v, 6) for k, v in probs.items()}, flush=True)
        # A here must be the base capture of t_7d7ad93e, bit for bit (same code path, same weights)
        old = d / f"{it}_float64.pt"
        if old.exists():
            o = torch.load(old, weights_only=True)["plain"]
            rec["a_vs_stage1b_base"] = {k: (c["a"][k].double() - o[k].double()).abs().max().item()
                                        for k in ("head_attr", "neuron_attr", "logits_last", "running_margin")}
        pair, pbin = SE.pair_manifest(key_a=KEY_A, key_b=KEY_B, item_id=it, man_a=mans[KEY_A],
                                      man_b=mans[KEY_B], res=c, d_weight_head=dW_head,
                                      d_weight_mlp=dW_mlp,
                                      run_files={"a": f"run__{KEY_A}__{it}.json", "b": f"run__{KEY_B}__{it}.json"})
        stem = f"pair__{KEY_A}__{KEY_B}__{it}"
        pair["bin"] = f"{stem}.bin"
        pbin.write(EX.EXPORTS / f"{stem}.bin")
        (EX.EXPORTS / f"{stem}.json").write_text(json.dumps(pair, indent=1))
        rec["pair"] = {"d_margin": pair["d_margin"], "d_probs": pair["d_probs"],
                       "conservation": {k: v for k, v in pair["conservation"].items() if k != "thresholds"},
                       "bin_bytes": (EX.EXPORTS / f"{stem}.bin").stat().st_size,
                       "json_bytes": (EX.EXPORTS / f"{stem}.json").stat().st_size,
                       "shapes": {k: v["shape"] for k, v in pair["arrays"].items()}}
        rec["run_shapes"] = {k: v["shape"] for k, v in mans[KEY_B]["arrays"].items()}
        if it.startswith("wvs_"):
            arch = _archived("USA", it[4:])
            if arch:
                ours = mans[KEY_B]["readout"]["probs"]
                arch["max_abs_prob_gap_vs_ours"] = max(abs(ours[k] - arch["probs"][k]) for k in ours)
                arch["max_abs_prob_gap_vs_paper_b_now"] = max(
                    abs(rec[KEY_B]["paper_b_probs"][k] - arch["probs"][k]) for k in ours)
                base_arch = _archived_base(it[4:])
                arch["archived_base"] = base_arch
            rec["archived_paper_b_usa"] = arch
        else:
            rec["archived_paper_b_usa"] = None
        report["items"][it] = rec
        print("PAIR", stem, "d_margin", f"{pair['d_margin']:+.4f}", "gate pass",
              pair["conservation"]["pass"], flush=True)
    EX.rebuild_index()
    report["index_pairs"] = [p_["file"] for p_ in json.loads((EX.EXPORTS / "index.json").read_text())["pairs"]
                             if p_["a"] == KEY_A]
    (WORKBENCH / "plans" / "stage1_8b_pair.json").write_text(json.dumps(report, indent=1, default=float))
    print("EXPORT_DONE", flush=True)


def _archived_base(qid: str) -> dict | None:
    path = ARCHIVE / "base_option_probabilities.csv"
    rows = [r for r in csv.DictReader(path.open()) if r["question_id"] == qid] if path.exists() else []
    return {"probs": {r["option_code"]: float(r["model_prob"]) for r in rows},
            "logprobs": {r["option_code"]: float(r["option_logprob"]) for r in rows}} if rows else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["layercheck", "capture", "parity", "export"])
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--item")
    ap.add_argument("--items", nargs="*")
    ap.add_argument("--layers", nargs="*", type=int, default=[0, 15])
    ap.add_argument("--dir")
    ap.add_argument("--out")
    args = ap.parse_args()
    {"layercheck": layercheck, "capture": capture, "parity": parity, "export": export}[args.mode](args)


if __name__ == "__main__":
    main()
