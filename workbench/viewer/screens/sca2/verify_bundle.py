#!/usr/bin/env python3
"""Independent read-back of a built archive; extracts only verified regular files."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile


def digest(stream):
    h = hashlib.sha256()
    for block in iter(lambda: stream.read(1 << 20), b""):
        h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archive", type=Path)
    ap.add_argument("destination", type=Path)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    manifest = json.loads(args.archive.with_suffix(".manifest.json").read_text())
    assert not args.destination.exists(), "Use a fresh extraction directory"
    assert args.archive.stat().st_size == manifest["archive_bytes"] <= 1_500_000_000
    with args.archive.open("rb") as f:
        assert digest(f) == manifest["archive_sha256"]
    entries = {e["file"]: e for e in manifest["files"]}
    assert len(entries) == len(manifest["files"])
    with tarfile.open(args.archive, "r:gz") as tar:
        members = tar.getmembers()
        assert {m.name for m in members} == set(entries)
        assert len(members) == len(entries)
        for m in members:
            p = Path(m.name)
            assert m.isfile() and not p.is_absolute() and ".." not in p.parts
            assert m.size == entries[m.name]["bytes"]
            extracted = tar.extractfile(m)
            assert extracted is not None
            with extracted as f:
                assert digest(f) == entries[m.name]["sha256"]
        # Paths/type checked above; no links, devices or directories in archive.
        tar.extractall(args.destination, members=members)
    payload = sum(e["bytes"] for e in entries.values())
    assert payload == manifest["payload_bytes"] <= 950_000_000   # the WB7 storage gate (Space cap is 1 GB)
    site = args.destination
    index = json.loads((site / "exports/index.json").read_text())
    assert set(index["models"]) == {r["model"] for r in index["runs"]}
    run_ids = {(r["model"], r["item_id"]) for r in index["runs"]}
    array_names = set()
    jsons = 0
    # Frozen capture-array contract. No embedding matrix/tokenizer/LoRA weights.
    allowed = set("resid_norm attn_norm mlp_norm head_norm attn_topk_idx attn_topk_val attn_topk_mass q3_count q3_write_norm g_last u_last c_last head_attr neuron_attr attn_attr mlp_attr running_margin running_margin_clamped head_attr_clamped mlp_attr_clamped d_resid_norm d_attn_norm d_mlp_norm d_head_norm d_weight_head d_weight_mlp d_head_attr d_mlp_attr d_attn_attr d_head_attr_clamped d_mlp_attr_clamped".split())
    # A light capture (the byte-budget tier of `build_deploy_bundle.py`) never carries a heavy array.
    heavy = set("attn_topk_idx attn_topk_val attn_topk_mass g_last u_last c_last".split())
    light_runs = 0
    numbers_only_runs = 0
    for row in index["runs"] + index["pairs"]:
        rel = "exports/" + row["file"]
        assert rel in entries
        m = json.loads((site / rel).read_text())
        if m.get("light"):
            assert m["arrays"], rel
            assert not (set(m["arrays"]) & heavy), (rel, set(m["arrays"]) & heavy)
            # The binary holds exactly the listed arrays, packed from offset 0.
            assert sum(a["nbytes"] for a in m["arrays"].values()) == entries["exports/" + m["bin"]]["bytes"], rel
            assert sorted((a["offset"], a["nbytes"]) for a in m["arrays"].values())[0][0] == 0, rel
        if m["arrays"]:
            assert m["bin"] and "exports/" + m["bin"] in entries
            binary = "exports/" + m["bin"]
        else:
            # Numbers only: every field but the arrays is the source export's.
            assert m["bin"] is None, rel
            binary = None
        assert m["kind"] in ("run", "pair")
        assert m["schema"] == "sca2-workbench/capture@1.1"
        array_names.update(m["arrays"])
        for a in m["arrays"].values():
            assert a["dtype"] in ("float32", "uint16")
            assert 0 <= a["offset"] <= a["offset"] + a["nbytes"] <= entries[binary]["bytes"]
        if m["kind"] == "pair":
            assert (m["a"], m["item_id"]) in run_ids
            assert (m["b"], m["item_id"]) in run_ids
            for ref in m.get("runs", {}).values():
                assert "exports/" + ref in entries
        elif m.get("light"):
            light_runs += 1
        elif m["kind"] == "run" and not m["arrays"]:
            numbers_only_runs += 1
        jsons += 1
    assert array_names <= allowed, array_names - allowed
    # index.json lists every Q57 comparator: kind, code, light flag, and files that exist.
    comparators = index.get("comparators", [])
    for c in comparators:
        assert ("exports/" + c["run"]) in entries and ("exports/" + c["pair"]) in entries, c
        assert (c["model"], c["item_id"]) in run_ids, c
        if c["kind"] == "adapter":
            assert len(c["cc"]) == 3 and c["cc"].isupper() and "bits" not in c, c
        else:
            assert c["kind"] == "sign_prompt" and set(c["bits"]) <= set("01") and len(c["bits"]) == 6 and "cc" not in c, c
        run = json.loads((site / "exports" / c["run"]).read_text())
        assert c["light"] is (c["tier"] == "light") and bool(run.get("light")) is c["light"], c
        has_heavy = bool(set(run["arrays"]) & heavy)
        assert c["tier"] in ("full", "light", "numbers"), c
        assert (c["tier"] == "full") == has_heavy, c
        assert (c["tier"] == "numbers") == (not run["arrays"]), c
    assert all(not p.endswith((".safetensors", ".pt", ".pth", ".gguf")) for p in entries)
    for rel, entry in entries.items():
        p = site / rel
        with p.open("rb") as f:
            assert digest(f) == entry["sha256"]
        if rel.endswith(".json"):
            # Provenance path strings are metadata, not human payloads. The
            # story payload's exact-field privacy schema is covered by pytest.
            text = p.read_text()
            for private in ("/Users/", "/home/", "file://", '"human_mean"', '"wvs_mean"', '"population_prob"'):
                assert private not in text, (rel, private)
    result = {"pass": True, "archive_bytes": manifest["archive_bytes"], "payload_bytes": payload,
              "files": len(entries), "runs": len(index["runs"]), "pairs": len(index["pairs"]),
              "capture_manifests": jsons, "comparators": len(comparators), "light_runs": light_runs,
              "numbers_only_runs": numbers_only_runs, "array_names": sorted(array_names),
              "archive_sha256": manifest["archive_sha256"]}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
