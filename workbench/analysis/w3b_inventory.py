#!/usr/bin/env python3
"""W3b step 1-2: inventory bank-2 LoRA profile weights on disk, pin by sha256, enumerate pairs.

Read-only on the weights. Writes only out/W3b_inventory.json and out/W3b_pairs.json.
No principal-angle (or any subspace) number is computed here.

Run:  env -u PYTHONPATH .venv/bin/python analysis/w3b_inventory.py   (cwd = workbench/)

Everything reported (counts, distances, degrees) is derived in code from the files on disk.
Bit vector: parsed from the profile id P_<b_trust>_<b_risktaking>_<b_patience>_<b_altruism>_
<b_posrecip>_<b_negrecip>, identical to paper_b/factorial.py::bits_of_unit (the bank-2 design cell).
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import itertools
import os
import json
import re
import sys
from pathlib import Path

from safetensors import safe_open
import numpy as np

HF = Path.home() / ".cache/huggingface/hub/datasets--Bonorinoa--SCA2-paper-b-adapters"
OUT = Path(__file__).resolve().parent / "out"
EXPECTED_PROFILES, EXPECTED_ONE_BIT = 17, 30  # W3-V's counts; only used to flag a discrepancy
KEY_RE = re.compile(r"^(?P<mod>.+)\.lora_(?P<ab>[AB])\.weight$")


def bits_of_unit(unit: str) -> tuple[int, ...]:  # same rule as paper_b/factorial.py
    parts = str(unit).split("_")
    if len(parts) != 7 or parts[0] != "P" or any(p not in ("0", "1") for p in parts[1:]):
        raise ValueError(f"not a unit code: {unit!r}")
    return tuple(int(p) for p in parts[1:])


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_candidates() -> list[Path]:
    """Every adapter_model.safetensors under a bank-2 .../profiles/<id>/ dir, any snapshot, any replicate."""
    out = []
    for p in sorted(HF.glob("snapshots/*/bank2/*/**/adapter_model.safetensors")):
        rel = p.relative_to(HF / "snapshots").parts  # <rev>/bank2/<run>/.../profiles/<id>/file
        if "profiles" in rel and rel[-2].startswith("P_"):
            out.append(p)
    return out


def inspect(p: Path) -> dict:
    prof = p.parent.name
    rel = p.relative_to(HF / "snapshots").parts
    rec = {
        "profile_id": prof,
        "path": str(p),
        "snapshot_revision": rel[0],
        "bank_run_id": rel[2],
        "is_replicate": "replicates" in rel,
        "status": "included",
        "exclusion_reason": None,
    }
    try:
        rec["bits"] = list(bits_of_unit(prof))
        real = p.resolve()
        rec["resolved_blob"] = str(real)
        rec["size_bytes"] = real.stat().st_size
        rec["sha256"] = sha256_file(p)
        # HF cache: snapshot file -> blobs/<sha256> (-> a content-store path). Walk the chain; the
        # first-hop blob name is the file's sha256 for LFS files, so it is a free cross-check.
        chain, q = [], p
        while q.is_symlink():
            q = (q.parent / os.readlink(q))
            chain.append(Path(os.path.normpath(q)).name)
        rec["symlink_chain_names"] = chain
        rec["blob_name_matches_sha256"] = rec["sha256"] in chain
        # alpha / r: adapter_config.json is absent from the bank-2 snapshots; the only per-profile
        # record of the LoRA config is run_record.json["lora"]. r is also cross-checked against A's shape.
        cfg = p.parent / "adapter_config.json"
        rr = p.parent / "run_record.json"
        if cfg.exists():
            c = json.loads(cfg.read_text())
            rec["lora_config_source"] = "adapter_config.json"
            rec["r_declared"], rec["alpha"] = c["r"], c["lora_alpha"]
            rec["target_modules_declared"] = c.get("target_modules")
        elif rr.exists():
            c = json.loads(rr.read_text())["lora"]
            rec["lora_config_source"] = "run_record.json[lora] (adapter_config.json absent)"
            rec["r_declared"], rec["alpha"] = c["r"], c["alpha"]
        else:
            raise ValueError("no adapter_config.json and no run_record.json: alpha unknown")
        mods: dict[str, dict] = collections.defaultdict(dict)
        with safe_open(str(p), "pt") as f:
            rec["safetensors_metadata"] = f.metadata()
            for k in sorted(f.keys()):
                m = KEY_RE.match(k)
                if not m:
                    raise ValueError(f"unexpected tensor key {k!r}")
                t = f.get_tensor(k)  # actually load: a truncated file fails here
                a = t.double().numpy()
                if not np.isfinite(a).all():
                    raise ValueError(f"non-finite values in {k}")
                mods[m["mod"]][m["ab"]] = {"shape": list(t.shape), "dtype": str(t.dtype)}
        for mod, d in mods.items():
            if set(d) != {"A", "B"}:
                raise ValueError(f"module {mod} lacks A or B")
            if d["A"]["shape"][0] != d["B"]["shape"][1]:
                raise ValueError(f"module {mod}: A rows {d['A']['shape'][0]} != B cols {d['B']['shape'][1]}")
        ranks = {d["A"]["shape"][0] for d in mods.values()}
        if len(ranks) != 1:
            raise ValueError(f"modules disagree on rank: {sorted(ranks)}")
        rec["r_from_shapes"] = ranks.pop()
        if rec["r_from_shapes"] != rec["r_declared"]:
            raise ValueError(f"declared r {rec['r_declared']} != A rows {rec['r_from_shapes']}")
        rec["r"] = rec["r_from_shapes"]
        rec["scale_alpha_over_r"] = rec["alpha"] / rec["r"]
        rec["target_modules"] = sorted({m.rsplit(".", 1)[-1] for m in mods})
        rec["n_modules"] = len(mods)
        rec["modules"] = {m: {"A_shape": d["A"]["shape"], "B_shape": d["B"]["shape"],
                              "dtype": d["A"]["dtype"]} for m, d in sorted(mods.items())}
    except Exception as e:  # a profile that cannot be read is excluded, with the reason
        rec["status"], rec["exclusion_reason"] = "excluded", f"{type(e).__name__}: {e}"
    return rec


def sig(rec: dict):
    return tuple((m, tuple(d["A_shape"]), tuple(d["B_shape"])) for m, d in rec["modules"].items())


def exact_degree_matched_feasible(nodes, edges_pool, degrees):
    """Exact backtracking: is there an edge subset of `edges_pool` with exactly `degrees`?"""
    need = dict(degrees)
    pool = sorted(edges_pool)
    adj = collections.defaultdict(list)
    for a, b in pool:
        adj[a].append(b), adj[b].append(a)
    sys.setrecursionlimit(10000)

    def go(remaining_edges):
        if all(v == 0 for v in need.values()):
            return True
        # branch on the node with the largest unmet need
        n = max(need, key=lambda x: need[x])
        if need[n] > sum(1 for b in adj[n] if (min(n, b), max(n, b)) in remaining_edges and need[b] > 0):
            return False
        for b in sorted(adj[n]):
            e = (min(n, b), max(n, b))
            if e in remaining_edges and need[b] > 0:
                need[n] -= 1; need[b] -= 1
                if go(remaining_edges - {e}):
                    need[n] += 1; need[b] += 1
                    return True
                need[n] += 1; need[b] += 1
        return False

    return go(frozenset(pool))


def main() -> int:
    OUT.mkdir(exist_ok=True)
    cands = find_candidates()
    recs = [inspect(p) for p in cands]
    # duplicates by content: the same blob exposed under two snapshots
    seen: dict[str, dict] = {}
    for r in recs:
        if r["status"] == "included" and r["sha256"] in seen:
            r["status"], r["exclusion_reason"] = "excluded", f"duplicate content of {seen[r['sha256']]['path']}"
        elif r["status"] == "included":
            seen[r["sha256"]] = r
    # replicates are not part of the profile pool (the pairs test is across distinct profiles)
    for r in recs:
        if r["status"] == "included" and r["is_replicate"]:
            r["status"], r["exclusion_reason"] = "excluded", "replicate adapter (same profile, different seed); not in profile pool"
    # same profile id twice (non-identical content) would make pairs ambiguous
    by_id = collections.defaultdict(list)
    for r in recs:
        if r["status"] == "included":
            by_id[r["profile_id"]].append(r)
    for pid, rs in by_id.items():
        for r in rs[1:]:
            r["status"], r["exclusion_reason"] = "excluded", f"second weights file for profile {pid}"
    # module-set / shape consistency against the modal signature
    inc = [r for r in recs if r["status"] == "included"]
    modal = collections.Counter(sig(r) for r in inc).most_common(1)[0][0] if inc else None
    for r in inc:
        if sig(r) != modal:
            r["status"], r["exclusion_reason"] = "excluded", "module set or A/B shapes differ from the modal signature"
    inc = sorted((r for r in recs if r["status"] == "included"), key=lambda r: r["profile_id"])
    common = sorted(set.intersection(*(set(r["modules"]) for r in inc))) if inc else []
    ref_mods = inc[0]["modules"] if inc else {}
    inventory = {
        "task": "t_53621092 (W3b)",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source_root": str(HF),
        "n_candidate_files": len(recs),
        "n_included": len(inc),
        "n_excluded": len(recs) - len(inc),
        "expected_from_W3V": {"profiles": EXPECTED_PROFILES, "one_bit_pairs": EXPECTED_ONE_BIT},
        "discrepancies": [],
        "bit_order": ["trust", "risktaking", "patience", "altruism", "posrecip", "negrecip"],
        "bit_source": "parsed from profile id P_<b1>_..._<b6>; same rule as paper_b/factorial.py::bits_of_unit",
        "intersected_modules": common,
        "n_intersected_modules": len(common),
        "intersected_module_dims": {m: {"d_out": ref_mods[m]["B_shape"][0], "d_in": ref_mods[m]["A_shape"][1]} for m in common},
        "alpha_values": sorted({r["alpha"] for r in inc}),
        "r_values": sorted({r["r"] for r in inc}),
        "profiles": sorted(recs, key=lambda r: (r["status"] != "included", r["profile_id"], r["path"])),
    }
    # ---- pairs ----
    ids = [r["profile_id"] for r in inc]
    bits = {r["profile_id"]: tuple(r["bits"]) for r in inc}
    pairs = []
    for a, b in itertools.combinations(ids, 2):
        d = sum(x != y for x, y in zip(bits[a], bits[b]))
        pairs.append({"a": a, "b": b, "hamming": d, "label": "one_bit" if d == 1 else "non_one_bit",
                      "differing_bit": next(i for i, (x, y) in enumerate(zip(bits[a], bits[b])) if x != y) if d == 1 else None})
    one = [p for p in pairs if p["label"] == "one_bit"]
    non = [p for p in pairs if p["label"] == "non_one_bit"]
    reuse = {i: sum(1 for p in one if i in (p["a"], p["b"])) for i in ids}
    reuse_non = {i: sum(1 for p in non if i in (p["a"], p["b"])) for i in ids}
    deg = {i: d for i, d in reuse.items() if d > 0}
    feasible = None
    if len(non) >= len(one):
        idx = {i: k for k, i in enumerate(ids)}
        pool = {(min(idx[p["a"]], idx[p["b"]]), max(idx[p["a"]], idx[p["b"]])) for p in non}
        feasible = bool(exact_degree_matched_feasible(list(idx.values()), pool, {idx[i]: d for i, d in deg.items()}))
    if len(inc) != EXPECTED_PROFILES:
        inventory["discrepancies"].append(f"PROFILE COUNT {len(inc)} != W3-V's {EXPECTED_PROFILES}")
    if len(one) != EXPECTED_ONE_BIT:
        inventory["discrepancies"].append(f"ONE-BIT PAIR COUNT {len(one)} != W3-V's {EXPECTED_ONE_BIT}")
    out_pairs = {
        "task": "t_53621092 (W3b)",
        "generated_utc": inventory["generated_utc"],
        "inventory_sha256_not_self_referential_note": "inventory file is hashed in W3b_PREREG.md",
        "discrepancies": inventory["discrepancies"],
        "n_profiles": len(ids),
        "profiles": ids,
        "n_pairs_total": len(pairs),
        "n_one_bit": len(one),
        "n_non_one_bit": len(non),
        "hamming_histogram": dict(sorted(collections.Counter(p["hamming"] for p in pairs).items())),
        "one_bit_by_differing_bit": dict(sorted(collections.Counter(p["differing_bit"] for p in one).items())),
        "one_bit_reuse_per_profile": reuse,
        "non_one_bit_reuse_per_profile": reuse_non,
        "one_bit_degree_sequence_sorted": sorted(reuse.values(), reverse=True),
        "degree_matched_null_feasible_exact_search": feasible,
        "degree_matched_null_note": ("exact backtracking over the non-one-bit pair pool for an edge subset with exactly the one-bit "
                                     "degree sequence" if feasible is not None else "pool smaller than one-bit set"),
        "pairs": pairs,
    }
    (OUT / "W3b_inventory.json").write_text(json.dumps(inventory, indent=1))
    (OUT / "W3b_pairs.json").write_text(json.dumps(out_pairs, indent=1))
    print(f"candidates {len(recs)} included {len(inc)} excluded {len(recs)-len(inc)}")
    print(f"modules intersected {len(common)}; alpha {inventory['alpha_values']} r {inventory['r_values']}")
    print(f"pairs total {len(pairs)} one_bit {len(one)} non_one_bit {len(non)} hist {out_pairs['hamming_histogram']}")
    print(f"degree-matched null feasible: {feasible}")
    for d in inventory["discrepancies"]:
        print("DISCREPANCY:", d)
    for r in recs:
        if r["status"] != "included":
            print("EXCLUDED", r["profile_id"], r["path"], "->", r["exclusion_reason"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
