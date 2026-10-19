"""Append-only unit exports and bounded-process cohort capture. No training or paper writes."""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

RSS_LIMIT = 16_000_000_000
PACKAGE = Path(__file__).resolve().parents[2] / "plans" / "gpu_cohort"


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=1, sort_keys=True, allow_nan=False) + "\n").encode()


def publish(path, raw):
    """Write-once atomic publication. Kill before/after link is safe; never overwrite data."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError(f"immutable artifact differs: {path}")
        return
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.partial")
    with temp.open("xb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    try:
        os.link(temp, path)
    except FileExistsError:
        if path.read_bytes() != raw:
            raise ValueError(f"immutable artifact differs: {path}")
    finally:
        temp.unlink(missing_ok=True)


def completed(root, marker, identity):
    if not marker.exists():
        return False
    rec = json.loads(marker.read_text())
    if rec["identity"] != identity:
        return False
    for name, sha in rec["files"].items():
        path = root / name
        if not path.exists() or digest(path) != sha:
            raise ValueError(f"completion digest mismatch: {name}")
    return rec["pass"]


def archive_parity(probs, archived, source, *, logprobs, archived_logprobs):
    import math
    import numpy as np
    if not (set(probs) == set(archived) == set(logprobs) == set(archived_logprobs)):
        raise ValueError("archive option codes differ")
    options = {}
    for code in probs:
        current, old = float(logprobs[code]), float(archived_logprobs[code])
        if not math.isfinite(current) or not math.isfinite(old) or float(np.float16(old)) != old:
            raise ValueError("archive logprobs must be finite and on the fp16 grid")
        # Conventional local binary16 ulp: positive spacing at |archived score|.
        # State this explicitly because toward/away spacing differs at powers of two.
        ulp = float(np.spacing(np.float16(abs(old))))
        gap = abs(current - old)
        options[code] = {"logprob": current, "archived_logprob": old,
                         "abs_logprob_gap_nats": gap, "archived_fp16_ulp_nats": ulp,
                         "fp16_ulp": gap / ulp, "pass": gap / ulp <= 4.,
                         "abs_prob_gap_descriptive": abs(probs[code] - archived[code])}
    maximum = max(x["fp16_ulp"] for x in options.values())
    return {"fatal": False, "tau": 4., "unit": "archived fp16 logprob ulp",
            "options": options, "max_fp16_ulp": maximum,
            "max_abs_logprob_gap_nats": max(x["abs_logprob_gap_nats"] for x in options.values()),
            "max_abs_prob_gap": max(x["abs_prob_gap_descriptive"] for x in options.values()),
            "probability_gap_is_descriptive": True, "pass": maximum <= 4., "source": source,
            "note": "parity unit per A2 F5; report-only, <=4 archived-logprob fp16 ulp. "
                    "ULP is positive binary16 spacing at abs(archived logprob). "
                    "High precision NF4 algebra is not historical fp16 CUDA execution."}


def completion_logprobs(out, ro):
    import torch
    if len(ro["prefix_ids"]) != 1:
        raise ValueError("archive full-logprob readout requires one shared prefix token")
    shared = torch.log_softmax(out["logits_before_readout"].double(), -1)[ro["prefix_ids"][0]]
    code_logp = torch.log_softmax(out["logits_last"].double(), -1)
    return {code: float(shared + code_logp[token]) for code, token in ro["code_token"].items()}


def canonical_manifest(man, provenance):
    man = copy.deepcopy(man)
    p = man["provenance"]
    for key in ("generated_at", "wall_seconds", "git_head"):
        p.pop(key, None)
    if "streaming" in p:
        for key in ("wall_seconds", "peak_rss_gb"):
            p["streaming"].pop(key, None)
    p.update(provenance)
    man["weights"] = provenance["weights"]
    return man


def update_index(root):
    from sca2_workbench import export as EX
    # Existing canonical registry layout, but publish index atomically (the only mutable view).
    old = EX.EXPORTS
    staging = root / ".index-staging"
    staging.mkdir(exist_ok=True)
    try:
        EX.EXPORTS = staging
        for p in sorted(root.glob("*.json")):
            if p.name.startswith(("run__", "pair__")):
                dest = staging / p.name
                if not dest.exists():
                    os.link(p, dest)
        EX.rebuild_index()
        os.replace(staging / "index.json", root / "index.json")
    finally:
        EX.EXPORTS = old


def check_prefix(prefix):
    if not prefix.startswith("workbench_cohort/") or ".." in prefix.split("/"):
        raise ValueError("outputs must use a new workbench_cohort/<run> prefix")
    return prefix.rstrip("/")


def source_digest():
    """Hash executed plumbing, not a misleading parent git revision."""
    root = Path(__file__).resolve().parents[2]
    files = sorted((root / "src" / "sca2_workbench").glob("*.py"))
    files += [PACKAGE / "runner" / "unit.py"]
    files += [PACKAGE / "models.json", PACKAGE / "items.json", root / "plans" / "stage1_8b_gaps.json"]
    h = hashlib.sha256()
    for p in files:
        h.update(str(p.relative_to(root)).encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


def fetch_inputs(registry, key):
    from huggingface_hub import snapshot_download
    token = os.environ.get("HF_TOKEN") or None
    base = registry["base"]
    snap = snapshot_download(base["model_id"], revision=base["revision"], token=token,
                             allow_patterns=["*.json", "*.safetensors", "tokenizer*"])
    if key == "base":
        return snap, None, None
    entry = next(x for x in registry["models"] if x["key"] == key)
    adapter = Path(snapshot_download(entry["repo_id"], repo_type="dataset", revision=entry["revision"],
                                    token=token, allow_patterns=[f"{entry['path']}/*"])) / entry["path"]
    if digest(adapter / "adapter_model.safetensors") != entry["sha256"]:
        raise ValueError("adapter weight digest mismatch")
    if digest(adapter / "adapter_config.json") != entry["config_sha256"]:
        raise ValueError("adapter config digest mismatch")
    return snap, adapter, entry


def to_cpu(x):
    import torch
    if isinstance(x, torch.Tensor):
        return x.detach().cpu()
    if isinstance(x, dict):
        return {k: to_cpu(v) for k, v in x.items()}
    return x


def capture(args):
    import importlib.metadata
    import torch
    from transformers import AutoTokenizer
    from sca2_workbench import export as EX, gates as G, items as I, llama_capture as LC
    from sca2_workbench import stream_capture as SC, stream_export as SE
    from sca2_workbench.nf4_source import FrozenNF4Source
    from sca2_workbench.offload_hf import build_offloaded_hf
    torch.set_grad_enabled(False)
    torch.set_num_threads(args.threads)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    registry = json.loads((PACKAGE / "models.json").read_text())
    item_record = next(x for x in json.loads((PACKAGE / "items.json").read_text())["items"] if x["item_id"] == args.item)
    identity_data = {"model": args.model, "item": args.item, "weights": args.weights, "dtype": args.dtype,
                     "device": args.device, "threads": args.threads, "source_digest": source_digest(),
                     "corrupt_mlp_layer": args.corrupt_mlp_layer,
                     "packages": {p: importlib.metadata.version(p) for p in
                                  ("torch", "transformers", "peft", "numpy", "bitsandbytes", "safetensors")}}
    identity = hashlib.sha256(json_bytes(identity_data)).hexdigest()
    root = Path(args.output)
    marker = root / "units" / f"{args.weights}_{args.dtype}_{args.model}_{args.item}.json"
    if completed(root, marker, identity):
        update_index(root)
        print("SKIP verified", marker, flush=True)
        return
    if marker.exists():
        raise ValueError("existing unit is failed or has a different identity; use a new output directory")
    snap, adapter_dir, entry = fetch_inputs(registry, args.model)
    tok = AutoTokenizer.from_pretrained(snap)
    item = I.Item(**{**{k: v for k, v in item_record.items() if k != "archive"},
                    "codes": tuple(item_record["codes"]), "labels": tuple(item_record["labels"]),
                    "parts": tuple(tuple(x) for x in item_record["parts"])})
    ro = I.readout_ids(tok, item, {"date_string": "26 Jul 2024"})
    dtype = getattr(torch, args.dtype)
    frozen = Path(args.frozen)

    def source(dt, device):
        if args.weights == "nf4_dequant":
            return FrozenNF4Source(snap, frozen, dt, device, prepare_cpu=args.device == "cpu")
        return SC.SafetensorsSource(snap, dt, device)

    src = source(dtype, args.device)
    instrument = src.instrument if args.weights == "nf4_dequant" else {"base_revision": registry["base"]["revision"]}
    lora = SC.LoraAdapter(adapter_dir, registry["base"]["model_id"]) if adapter_dir else None
    jp, jm = ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]
    t0 = time.monotonic()
    def log(msg):
        print(msg, flush=True)
        if args.pause_after_layer and int(msg.split()[1].split("/")[0]) == args.pause_after_layer:
            print("PAUSE_FOR_KILL", flush=True)
            time.sleep(120)
    corruption = (args.corrupt_mlp_layer, 1.001) if args.corrupt_mlp_layer is not None else None
    if lora:
        res = SC.run_streamed_pair(src, ro["prompt_ids"], lora, j_plus=jp, j_minus=jm,
                                   full_logits=True, log=log, scale_mlp_write=corruption)
    else:
        a, ac = SC.run_streamed(src, ro["prompt_ids"], j_plus=jp, j_minus=jm, clamps=(False, True),
                                full_logits=True, log=log, scale_mlp_write=corruption)
        res = {"a": a, "a_clamped": ac}
    res = to_cpu(res)
    capture_seconds = time.monotonic() - t0
    if args.weights == "nf4_dequant":
        # CPU diagnostic preparation is lazy; at this point all 224 files exist.
        instrument = {**instrument, "files": {p.name: digest(p) for p in sorted(frozen.glob("*.safetensors"))}}
    # Source versions, CPU/CUDA codes and distinct frozen instruments must coexist, not overwrite.
    instrument_id = hashlib.sha256(json_bytes(instrument)).hexdigest()[:8]
    base_key = f"llama31_8b_{args.weights}_{args.dtype}_{args.device}_{identity_data['source_digest'][:8]}_{instrument_id}"
    keys = {"a": base_key, "b": f"{base_key}_{args.model.lower()}"}
    if args.corrupt_mlp_layer is not None:
        keys = {k: f"{v}_corrupt_l{args.corrupt_mlp_layer}" for k, v in keys.items()}
    taus = G.GateTaus(**json.loads((PACKAGE.parent / "stage1_8b_gaps.json").read_text())["taus"]
                       ["f64" if args.dtype == "float64" else "f32"]["tau"])
    manifests, outputs = {}, {}
    # Same effective instrument, independent HF modelling code, in float32; not the archive.
    for arm in (["a", "b"] if lora else ["a"]):
        ref_src = source(torch.float32, args.device)
        ad = adapter_dir if arm == "b" else None
        model = build_offloaded_hf(snap, torch.float32, adapter_dir=ad,
                                  model_id=registry["base"]["model_id"], source=ref_src)
        logits = model(input_ids=torch.tensor([ro["prompt_ids"]], device=args.device)).logits[0, -1].float().cpu()
        del model
        ref_src.drop_handles()
        probs = LC.code_probs(logits, ro["code_token"])
        key = keys[arm]
        label = f"Llama-3.1-8B-Instruct{' + ' + args.model + ' LoRA' if arm == 'b' else ''} [{args.weights}, {args.dtype}]"
        meta = None if arm == "a" else {**lora.describe(), "dir": entry["path"], "country": args.model,
                                        "revision": entry["revision"], "item_split": None}
        man, bw = SE.run_manifest(key=key, label=label, model_id=registry["base"]["model_id"],
                                 src=src, tok=tok, item=item, ro=ro, plain=res[arm],
                                 clamped=res[f"{arm}_clamped"], taus=taus, hf_logits_last=logits,
                                 paper_b_probs=probs, parity_tau=1e-4, stats={},
                                 chat_kwargs={"date_string": "26 Jul 2024"}, adapter=meta)
        man["readout"]["probs_teacher_forced_hf_source"] = "HF float32 on the same effective weights; shared-prefix Eq.6 factorization"
        arm_archive = "base" if arm == "a" else args.model
        archived = item_record["archive"][arm_archive]
        scores = completion_logprobs(res[arm], ro)
        man["readout"]["option_logprobs"] = scores
        man["readout"]["option_logprob_source"] = "streamed high-precision full-vocabulary log-softmax: shared prefix token + final code token, summed nats"
        man["archive_parity"] = archive_parity(man["readout"]["probs"], archived["probs"], archived["source"],
                                                logprobs=scores, archived_logprobs=archived["logprobs"])
        man = canonical_manifest(man, {**identity_data, "model": key, "instrument": instrument,
                                       "base_revision": registry["base"]["revision"]})
        stem = f"run__{key}__{args.item}"
        man["bin"] = stem + ".bin"
        manifests[arm] = man
        outputs[stem + ".json"] = json_bytes(man)
        outputs[stem + ".bin"] = b"".join(bw.parts)
    if lora:
        dh, dm = SC.lora_weight_delta(lora, src)
        man, bw = SE.pair_manifest(key_a=keys["a"], key_b=keys["b"], item_id=args.item,
                                  man_a=manifests["a"], man_b=manifests["b"], res=res,
                                  d_weight_head=dh, d_weight_mlp=dm,
                                  run_files={k: f"run__{keys[k]}__{args.item}.json" for k in ("a", "b")},
                                  retain_failed=True)
        man = canonical_manifest(man, {"weights": args.weights, "compute_dtype": args.dtype,
                                       "source_digest": identity_data["source_digest"]})
        man["provenance"]["capture"] = f"streamed, unmerged B-A, {args.dtype}"
        stem = f"pair__{keys['a']}__{keys['b']}__{args.item}"
        man["bin"] = stem + ".bin"
        manifests["pair"] = man
        outputs[stem + ".json"] = json_bytes(man)
        outputs[stem + ".bin"] = b"".join(bw.parts)
    for name, raw in outputs.items():
        publish(root / name, raw)
    passed = all(m["conservation"]["pass"] for m in manifests.values())
    rec = {"identity": identity, "inputs": identity_data, "pass": passed,
           "files": {n: digest(root / n) for n in sorted(outputs)}}
    publish(marker, json_bytes(rec))
    update_index(root)
    timings = {"model": args.model, "item": args.item, "weights": args.weights, "dtype": args.dtype,
               "capture_seconds": capture_seconds, "total_seconds": time.monotonic() - t0,
               "peak_rss_gib": SC.peak_rss_gb(), "pass": passed,
               "sizes": {n: len(raw) for n, raw in outputs.items()}}
    attempt = root / "attempts" / f"{args.model}_{args.item}_{time.time_ns()}.json"
    publish(attempt, json_bytes(timings))
    print("UNIT_DONE", json.dumps(timings), flush=True)
    if not passed:
        raise SystemExit(2)


def supervise(command, *, timeout, log_path):
    """One child only; poll resident memory throughout downloads, capture, and reference."""
    import psutil
    log_path.parent.mkdir(parents=True, exist_ok=True)
    start, peak = time.monotonic(), 0
    with log_path.open("ab", buffering=0) as log:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                                                                CUBLAS_WORKSPACE_CONFIG=":4096:8"))
        try:
            while child.poll() is None:
                try:
                    peak = max(peak, psutil.Process(child.pid).memory_info().rss)
                except psutil.NoSuchProcess:
                    pass
                if peak > RSS_LIMIT or time.monotonic() - start > timeout:
                    raise RuntimeError(f"STOP RSS/time: peak={peak}, seconds={time.monotonic()-start:.1f}")
                time.sleep(.1)
        finally:
            if child.poll() is None:
                import signal
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            with log_path.with_suffix(".rc.json").open("w") as f:
                json.dump({"exit_code": child.returncode, "peak_rss_bytes": peak,
                           "seconds": time.monotonic() - start}, f, indent=1)
    return child.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--item", required=True)
    ap.add_argument("--weights", choices=["nf4_dequant", "unquantized"], default="nf4_dequant")
    ap.add_argument("--dtype", choices=["float64", "float32"], default="float64")
    ap.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    ap.add_argument("--output", required=True)
    ap.add_argument("--frozen", default=str(PACKAGE / "local_nf4"))
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--timeout", type=float, default=1800)
    ap.add_argument("--pause-after-layer", type=int)
    ap.add_argument("--corrupt-mlp-layer", type=int)
    ap.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()
    if args.worker:
        capture(args)
    else:
        stamp = time.time_ns()
        log = Path(args.output) / "attempts" / f"{args.model}_{args.item}_{stamp}.log"
        print("LOG", log, flush=True)
        # A file lock also prevents two separately launched cohort workers sharing the host.
        import fcntl
        lock = PACKAGE / ".cohort-8b.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        with lock.open("a") as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            rc = supervise([sys.executable, str(PACKAGE / "runner" / "unit.py"), *sys.argv[1:], "--worker"],
                           timeout=args.timeout, log_path=log)
        raise SystemExit(rc)


if __name__ == "__main__":
    main()
