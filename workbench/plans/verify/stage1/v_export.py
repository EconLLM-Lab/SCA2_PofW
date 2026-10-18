"""Verifier: capture@1.1 conformance of the exports, read from the files only."""
import json, math
from pathlib import Path
import numpy as np

WB = Path(__file__).resolve().parents[3]
EX = WB / "exports"

# contract: name -> shape builder (L,H,F,T; k topk; L+1 where noted)
RUN_SHAPES = {
    "resid_norm": lambda L, H, F, T, k: (L + 1, T),
    "attn_norm": lambda L, H, F, T, k: (L, T),
    "mlp_norm": lambda L, H, F, T, k: (L, T),
    "head_norm": lambda L, H, F, T, k: (L, H, T),
    "attn_topk_idx": lambda L, H, F, T, k: (L, H, T, k),
    "attn_topk_val": lambda L, H, F, T, k: (L, H, T, k),
    "attn_topk_mass": lambda L, H, F, T, k: (L, H, T),
    "q3_count": lambda L, H, F, T, k: (L, T),
    "q3_write_norm": lambda L, H, F, T, k: (L, T),
    "g_last": lambda L, H, F, T, k: (L, F),
    "u_last": lambda L, H, F, T, k: (L, F),
    "c_last": lambda L, H, F, T, k: (L, F),
    "head_attr": lambda L, H, F, T, k: (L, H),
    "neuron_attr": lambda L, H, F, T, k: (L, F),
    "attn_attr": lambda L, H, F, T, k: (L,),
    "mlp_attr": lambda L, H, F, T, k: (L,),
    "running_margin": lambda L, H, F, T, k: (L + 1,),
}
PAIR_SHAPES = {
    "d_resid_norm": lambda L, H, F, T, k: (L + 1, T),
    "d_attn_norm": lambda L, H, F, T, k: (L, T),
    "d_mlp_norm": lambda L, H, F, T, k: (L, T),
    "d_head_norm": lambda L, H, F, T, k: (L, H, T),
    "d_weight_head": lambda L, H, F, T, k: (L, H, 4),
    "d_weight_mlp": lambda L, H, F, T, k: (L, 3),
    "d_head_attr": lambda L, H, F, T, k: (L, H),
    "d_mlp_attr": lambda L, H, F, T, k: (L,),
    "d_attn_attr": lambda L, H, F, T, k: (L,),
    "d_head_attr_clamped": lambda L, H, F, T, k: (L, H),
    "d_mlp_attr_clamped": lambda L, H, F, T, k: (L,),
}
CLAMPED = lambda names: {n + "_clamped" for n in names}
problems = []


def arr(binp, a):
    dt = np.uint16 if a["dtype"] == "uint16" else np.float32
    return np.fromfile(binp, dtype=dt, count=a["nbytes"] // np.dtype(dt).itemsize, offset=a["offset"])


def check_arrays(tag, man, binp, templates, L, H, F, T, k=16):
    a_block = man["arrays"]
    names = set(a_block)
    expected = set(templates)
    missing = expected - names
    extra = {n for n in names - expected if not n.endswith("_clamped")}
    if missing:
        problems.append(f"{tag}: missing contract arrays {sorted(missing)}")
    if extra:
        problems.append(f"{tag}: arrays not in the contract {sorted(extra)}")
    if binp.stat().st_size != max((x["offset"] + x["nbytes"] for x in a_block.values()), default=0):
        problems.append(f"{tag}: bin size {binp.stat().st_size} != end of last array")
    covered = 0
    for name, a in sorted(a_block.items(), key=lambda kv: kv[1]["offset"]):
        want = templates.get(name.rstrip("_clamped") if name.endswith("_clamped") else name)
        if want is None:
            continue
        if tuple(a["shape"]) != tuple(want(L, H, F, T, k)):
            problems.append(f"{tag}/{name}: shape {a['shape']} != {want(L,H,F,T,k)}")
        exp_dtype = "uint16" if name == "attn_topk_idx" else "float32"
        if a["dtype"] != exp_dtype:
            problems.append(f"{tag}/{name}: dtype {a['dtype']} != {exp_dtype}")
        pad = a["offset"] - covered
        if pad < 0 or pad > 7 or a["offset"] % 8:
            problems.append(f"{tag}/{name}: offset {a['offset']} vs previous end {covered} (pad {pad})")
        covered = a["offset"] + a["nbytes"]
        v = arr(binp, a)
        if not np.isfinite(v).all() and exp_dtype == "float32":
            problems.append(f"{tag}/{name}: non-finite values")
    return a_block


print("### run manifests")
run_files = sorted(p for p in EX.glob("run__*.json")) + sorted((EX / "llama31_8b").glob("run__*.json"))
for p in run_files:
    man = json.loads(p.read_text())
    mm = man["model"]
    L, H, F = mm["n_layers"], mm["n_heads"], mm["d_ffn"]
    toks = man["tokens"]
    T = toks["T"] if isinstance(toks, dict) and "T" in toks else len(man["readout"]["position"] and [0]) * 0
    if not T:
        T = man["readout"]["position"] + 1
    tag = p.name
    if man.get("schema") != "sca2-workbench/capture@1.1":
        problems.append(f"{tag}: schema {man.get('schema')}")
    if man.get("kind") != "run":
        problems.append(f"{tag}: kind {man.get('kind')}")
    segs = man.get("segments")
    if not segs:
        problems.append(f"{tag}: no segments")
    else:
        pos = 0
        for s in segs:
            if s["a"] != pos:
                problems.append(f"{tag}: segment gap/overlap at {s}")
            if s["b"] <= s["a"]:
                problems.append(f"{tag}: empty segment {s}")
            pos = s["b"]
        if pos != T:
            problems.append(f"{tag}: segments end {pos} != T {T}")
        ro = [s for s in segs if s["kind"] == "readout"]
        if len(ro) != 1 or (ro[0]["a"], ro[0]["b"]) != (T - 1, T):
            problems.append(f"{tag}: readout segment {ro}")
        if [s["kind"] for s in segs] != ["template", "system", "template", "instruction", "question",
                                         "instruction", "options", "instruction", "answer_cue",
                                         "template", "readout"]:
            problems.append(f"{tag}: segment kinds {[s['kind'] for s in segs]}")
        if man["readout"]["position"] != T - 1:
            problems.append(f"{tag}: readout.position {man['readout']['position']} != T-1")
    tmp = dict(RUN_SHAPES)
    if "attn_topk_idx" in man["arrays"]:
        pass
    else:
        problems.append(f"{tag}: no attn_topk_idx (contract requires the top-k storage)")
    k = man["arrays"].get("attn_topk_idx", {}).get("shape", [0, 0, 0, 16])[3]
    check_arrays(tag, man, p.with_name(man["bin"]), tmp, L, H, F, T, k)
    prov = man.get("provenance", {})
    print(f"  {tag:52s} L={L:2d} H={H:2d} F={F:5d} T={T:3d} "
          f"compute={prov.get('compute_dtype')} stored={prov.get('stored_dtype')} "
          f"arrays={len(man['arrays'])} rel_taus={'yes' if 'relative' in man.get('conservation', {}) else 'NO'} "
          f"legacy_applicable={man.get('conservation', {}).get('legacy_absolute_applicable')}")

print("\n### pair manifests")
for p in sorted(EX.glob("pair__*.json")):
    man = json.loads(p.read_text())
    ra = json.loads((EX / man["runs"]["a"]).read_text()) if (EX / man["runs"]["a"]).exists() else None
    if ra is None:
        problems.append(f"{p.name}: runs.a {man['runs']['a']} not found")
        continue
    mm = ra["model"]
    L, H, F = mm["n_layers"], mm["n_heads"], mm["d_ffn"]
    T = man["arrays"]["d_resid_norm"]["shape"][1]
    check_arrays(p.name, man, p.with_name(man["bin"]), PAIR_SHAPES, L, H, F, T)
    ab = man["arrays"]
    binp = p.with_name(man["bin"])
    dh = arr(binp, ab["d_head_attr"]).astype(np.float64)
    dm = arr(binp, ab["d_mlp_attr"]).astype(np.float64)
    dhc = arr(binp, ab["d_head_attr_clamped"]).astype(np.float64)
    dmc = arr(binp, ab["d_mlp_attr_clamped"]).astype(np.float64)
    # the gate a viewer can recompute: sum of stored float32 arrays + float64 d_embed_attr
    g32 = abs(dh.sum() + dm.sum() + man["d_embed_attr"] - man["d_margin"])
    g32c = abs(dhc.sum() + dmc.sum() + man["d_embed_attr_clamped"] - man["d_margin_clamped"])
    rec = man["conservation"]
    ok = (g32 <= 1e-6 and g32c <= 1e-6)
    rel = rec.get("relative", {})
    print(f"  {p.name[:62]:62s} L={L} T={T:3d} d_attr_gap_float32 mine={g32:.2e} "
          f"(manifest {rec['d_attr_gap_float32']:.2e}) clamped mine={g32c:.2e} "
          f"(manifest {rec['d_attr_gap_float32_clamped']:.2e}) pass={ok} "
          f"tau={rel.get('checks', {}).get('d_attr_gap_float32', {}).get('tau')} "
          f"f32_rel={rel.get('checks', {}).get('d_attr_gap_float32', {}).get('rel', float('nan')):.2e}")
    if not ok:
        problems.append(f"{p.name}: d_attr_gap_float32 recomputed {g32:.2e} > 1e-6")
    if abs(g32 - rec["d_attr_gap_float32"]) > 0.2 * max(rec["d_attr_gap_float32"], 1e-12):
        problems.append(f"{p.name}: manifest d_attr_gap_float32 {rec['d_attr_gap_float32']:.3e} "
                        f"!= recomputed {g32:.3e}")

print("\n### index.json")
idx = json.loads((EX / "index.json").read_text())
runs_on_disk = {p.name for p in EX.glob("run__*.json")} | {p.name for p in (EX / "llama31_8b").glob("run__*.json")}
pairs_on_disk = {p.name for p in EX.glob("pair__*.json")}
listed_runs = {r["file"] for r in idx["runs"]}
listed_pairs = {r["file"] for r in idx["pairs"]}
print(f"  models={len(idx['models'])} runs listed={len(listed_runs)} on disk={len(runs_on_disk)} "
      f"pairs listed={len(listed_pairs)} on disk={len(pairs_on_disk)}")
print(f"  runs on disk not in index: {sorted(runs_on_disk - listed_runs)}")
print(f"  index runs with no file:  {sorted(listed_runs - runs_on_disk)}")
print(f"  pairs on disk not in index: {sorted(pairs_on_disk - listed_pairs)}")
for r in idx["runs"]:
    f = EX / r["file"]
    if f.exists():
        m = json.loads(f.read_text())
        first_code = next(iter(r["probs"]))
        if abs(m["readout"]["probs"][first_code] - r["probs"][first_code]) > 1e-12:
            problems.append(f"index {r['file']}: probs differ from manifest")
print("\n### PROBLEMS" if problems else "\n### no conformance problems found")
for x in problems:
    print("  -", x)
