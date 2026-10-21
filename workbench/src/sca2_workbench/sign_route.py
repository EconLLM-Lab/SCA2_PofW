"""Prompt route (W2): the base model prompted with one of the 26 sign-profile prompts, paired with its
phase-1 base run. Pure helpers; no model code. The prompt texts are vendored in
`plans/gpu_cohort/sign_profiles.json` (build-time copy of `paper_b/sign_prompt.py`, sha256-checked there)."""
from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import numpy as np

from sca2_workbench.items import Item

PROFILES_PATH = Path(__file__).resolve().parents[2] / "plans" / "gpu_cohort" / "sign_profiles.json"
TAG_PREFIX = "base_sp"


def _sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_profiles(path=PROFILES_PATH):
    """{profile_id: profile}. Refuses any prompt whose text no longer matches its recorded sha256."""
    doc = json.loads(Path(path).read_text())
    out = {}
    for p in doc["profiles"]:
        if hashlib.sha256(p["prompt"].encode()).hexdigest() != p["prompt_sha256"]:
            raise ValueError(f"{p['profile_id']}: prompt text differs from its recorded sha256")
        out[p["profile_id"]] = p
    return out


def unit_tag(profile_id):
    """Marker/key stem of a prompt-route unit: 'base_sp' + the six sign bits, e.g. base_sp010110."""
    return TAG_PREFIX + profile_id.replace("_", "")


def profile_of_tag(tag):
    """Profile id of a prompt-route tag, or None for an ordinary model key ('base', 'ARG', ...)."""
    if not tag.startswith(TAG_PREFIX):
        return None
    bits = tag[len(TAG_PREFIX):]
    if len(bits) != 6 or set(bits) - {"0", "1"}:
        raise ValueError(f"malformed prompt-route tag: {tag}")
    return "_".join(bits)


def archive_for(profile_id, item_id):
    """Paper B's archived sign-prompt scores ({source, probs, logprobs}) for one profile and item."""
    return load_profiles()[profile_id]["archive"][item_id]


def sign_item(item: Item, profile) -> Item:
    """The strict battery item with the sign text in front, exactly as `score_sign_profiles.combined_prompt`:
    sign_prompt.rstrip() + blank line + survey prompt. Item id, codes and margin sides are unchanged."""
    sign = profile["prompt"].rstrip() + "\n\n"
    parts = (("instruction", "sign profile", sign),) + tuple(item.parts)
    return dataclasses.replace(item, user_prompt=sign + item.user_prompt, parts=parts,
                               meta={**item.meta, "prompt_profile": profile["profile_id"], "route": "prompt"})


def insertion_alignment(ids_a, ids_b):
    """Is B = A with one block of tokens inserted? Descriptive, never a gate: tokenisation could merge
    across the insertion edge. Returns insert_at, n_inserted and whether the two ends match exactly."""
    n_ins = len(ids_b) - len(ids_a)
    p = 0
    while p < min(len(ids_a), len(ids_b)) and ids_a[p] == ids_b[p]:
        p += 1
    exact = n_ins > 0 and list(ids_b[:p]) == list(ids_a[:p]) and list(ids_b[p + n_ins:]) == list(ids_a[p:])
    return {"insert_at": p, "n_inserted": n_ins, "exact": bool(exact)}


def read_array(manifest, raw, name):
    meta = manifest["arrays"][name]
    a = np.frombuffer(raw, dtype=np.dtype(meta["dtype"]).newbyteorder("<"), count=int(np.prod(meta["shape"])),
                      offset=meta["offset"])
    return a.reshape(meta["shape"])


def load_baseline(root, item_id):
    """The phase-1 base run A for one item: its manifest, the float32 attribution arrays widened to float64,
    and the digests of its files. Fails closed on a missing or failed unit or any digest mismatch."""
    import torch
    root = Path(root)
    marker = root / "units" / f"nf4_dequant_float64_base_{item_id}.json"
    if not marker.exists():
        raise ValueError(f"baseline unit missing: {marker}")
    rec = json.loads(marker.read_text())
    if not rec["pass"]:
        raise ValueError(f"baseline unit failed its gates: {marker.name}")
    for name, sha in rec["files"].items():
        if not (root / name).exists() or _sha256_file(root / name) != sha:
            raise ValueError(f"baseline digest mismatch: {name}")
    run_json = next(n for n in rec["files"] if n.startswith("run__") and n.endswith(".json"))
    manifest = json.loads((root / run_json).read_text())
    raw = (root / manifest["bin"]).read_bytes()

    def arr(name):
        return torch.from_numpy(read_array(manifest, raw, name).astype(np.float64))
    ro = manifest["readout"]
    out = {"head_attr": arr("head_attr"), "mlp_attr": arr("mlp_attr"), "attn_attr": arr("attn_attr"),
           "embed_attr": float(ro["embed_attr"]),
           "_clamped_attr": {"head_attr": arr("head_attr_clamped"), "mlp_attr": arr("mlp_attr_clamped"),
                             "embed_attr": float(ro["embed_attr_clamped"])}}
    return {"key": manifest["model"]["key"], "manifest": manifest, "out": out, "files": dict(rec["files"]),
            "run_file": run_json}
