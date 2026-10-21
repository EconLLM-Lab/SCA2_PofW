"""WB7-Q: synthetic light-run tier of the deploy bundle. No real exports, no inference."""
import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

WORKBENCH = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("deploy_bundle", WORKBENCH / "scripts/build_deploy_bundle.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
ISPEC = importlib.util.spec_from_file_location("bundle_identity", WORKBENCH / "scripts/check_bundle_identity.py")
identity = importlib.util.module_from_spec(ISPEC)
ISPEC.loader.exec_module(identity)
VERIFY = WORKBENCH / "viewer/screens/sca2/verify_bundle.py"
BASE = "BASE"
ADAPTERS = "phase1_nf4_t4"
PROMPTS = "phase1_promptroute_nf4_t4"
HEAVY = {"attn_topk_idx", "attn_topk_val", "attn_topk_mass", "g_last", "u_last", "c_last"}
RUN_ARRAYS = [("attn_topk_val", "float32", 64), ("g_last", "float32", 64), ("neuron_attr", "float32", 32),
              ("head_attr", "float32", 16), ("running_margin", "float32", 8), ("mlp_attr", "float32", 4)]
PAIR_ARRAYS = [("d_head_norm", "float32", 512), ("d_attn_attr", "float32", 8), ("d_mlp_attr", "float32", 8)]


def capture(path, arrays_spec):
    """Write a synthetic binary and return its array table; bytes depend on the offset."""
    path.parent.mkdir(parents=True, exist_ok=True)
    blob, table = bytearray(), {}
    for name, dtype, nbytes in arrays_spec:
        table[name] = {"dtype": dtype, "offset": len(blob), "nbytes": nbytes}
        blob += bytes((len(blob) * 7 + i * 37) % 256 for i in range(nbytes))
    path.with_suffix(".bin").write_bytes(bytes(blob))
    return table


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def folder_of(name):
    parts = name.split("__")
    model = parts[2] if parts[0] == "pair" else parts[1]
    return PROMPTS if model.startswith(("PROMPT", "sp")) else ADAPTERS


@pytest.fixture
def light(tmp_path, monkeypatch):
    w = tmp_path / "workbench"
    story = {"export": {"src": ADAPTERS, "prompt_src": PROMPTS, "base": BASE,
                        "default_units": [{"cc": "USA", "item": "wvs_Q57"}]},
             "featured": [{"bit": "trust", "surface": "trust", "x": "ARG", "y": "BRA", "item": "wvs_Q81",
                           "prompt_x": "PROMPT_arg", "prompt_y": "PROMPT_bra"}],
             "sources": [{"path": "relative/source.csv", "sha256": "a" * 64}]}
    put(w / "viewer/public/sca2/sca2_data.json", story)
    (w / "viewer/public/sca2/index.html").write_text("<h1>Story</h1>")
    (w / "viewer/src").mkdir(parents=True)
    (w / "viewer/src/main.ts").write_text('export const DEFAULT = { a: "BASE", b: "BASE_usa", item: "wvs_Q57" };')
    for name in ("ladder", "matrix", "object", "cohort"):
        p = w / f"viewer/screens/v4/{name}-1440.png"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"synthetic image")
    (w / "viewer/screens/v3").mkdir(parents=True)
    (w / "viewer/screens/v3/cohort-illustration.png").write_bytes(b"synthetic cohort")

    sets = ((ADAPTERS, [(BASE, BASE + "_usa", "wvs_Q57", 1.0), (BASE, BASE + "_chn", "wvs_Q57", -2.0),
                        (BASE, BASE + "_bgd", "wvs_Q57", 3.0), (BASE, BASE + "_arg", "wvs_Q81", 0.5),
                        (BASE, BASE + "_bra", "wvs_Q81", -0.5)]),
            (PROMPTS, [(BASE, "PROMPT_base_sp000000", "wvs_Q57", 0.25), (BASE, "PROMPT_arg", "wvs_Q81", 0.75),
                       (BASE, "PROMPT_bra", "wvs_Q81", 0.25)]))
    for folder, pairs in sets:
        root = w / "exports" / folder
        index = {"schema": "sca2-workbench/capture@1.1", "models": {}, "runs": [], "pairs": []}
        for a, b, item, margin in pairs:
            for key in (a, b):
                index["models"][key] = {"model_id": "synthetic", "adapter": None, "label": key}
                name = f"run__{key}__{item}.json"
                if any(r["file"] == name for r in index["runs"]):
                    continue
                index["runs"].append({"file": name, "model": key, "item_id": item})
                put(root / name, {"schema": index["schema"], "kind": "run",
                                  "model": {"key": key, "adapter": None}, "item": {"item_id": item},
                                  "bin": name.replace(".json", ".bin"), "arrays": capture(root / name, RUN_ARRAYS),
                                  "readout": {"prob": 0.25}, "provenance": {"source_digest": "b" * 64}})
            name = f"pair__{a}__{b}__{item}.json"
            index["pairs"].append({"file": name, "a": a, "b": b, "item_id": item, "d_margin": margin})
            put(root / name, {"schema": index["schema"], "kind": "pair", "a": a, "b": b, "item_id": item,
                              "bin": name.replace(".json", ".bin"), "arrays": capture(root / name, PAIR_ARRAYS),
                              "d_margin": margin, "probs": {"a": 0.5, "b": 0.5}})
        put(root / "index.json", index)
    # The builder always reads the top-level export folder's index (it holds the pinned captures).
    put(w / "exports/index.json", {"schema": "sca2-workbench/capture@1.1", "models": {}, "runs": [], "pairs": []})

    def npm(command, cwd, check, **kwargs):
        assert command == ["npm", "run", "build"] and check
        dist = w / "viewer/dist"
        dist.mkdir(exist_ok=True)
        (dist / "index.html").write_text('<script src="/assets/app.js"></script>')
        (dist / "assets").mkdir()
        (dist / "assets/app.js").write_text("/* synthetic static build */")
        shutil.copytree(w / "viewer/public/sca2", dist / "sca2")

    monkeypatch.setattr(subprocess, "run", npm)
    return w, argparse.Namespace(workbench=w, out=None, max_bytes=builder.MAX_BYTES)


def read_archive(out):
    with tarfile.open(out) as tar:
        return {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}


def test_light_run_output_numbers_and_closure(light):
    w, args = light
    assert builder.build_bundle(args) == 0
    out = w / "dist/deploy_bundle.tar.gz"
    manifest = json.loads(out.with_suffix(".manifest.json").read_text())
    files = read_archive(out)
    q57 = manifest["q57"]
    assert q57["comparators"] == 4
    assert q57["shipped_full"] == ["BASE_usa"]
    # Allocation order: adapters first (largest |d_margin| first), then sign prompts.
    assert q57["shipped_light"] == ["BASE_bgd", "BASE_chn", "PROMPT_base_sp000000"]
    assert q57["allocation_order"][-1] == "PROMPT_base_sp000000"
    assert q57["pairs_only"] == []
    assert q57["heavy_arrays"] == sorted(HEAVY) or set(q57["heavy_arrays"]) == HEAVY
    assert "every Q57 comparator" in manifest["selection_rule"] and "light flag" in manifest["selection_rule"]

    index = json.loads(files["exports/index.json"])
    run_names = {r["file"] for r in index["runs"]}
    pair_names = {r["file"] for r in index["pairs"]}
    assert len(index["pairs"]) == 8 and len(index["runs"]) == 10
    for name in sorted(run_names | pair_names):
        source_path = w / "exports" / folder_of(name) / name
        source = json.loads(source_path.read_text())
        shipped = json.loads(files["exports/" + name])
        if name in pair_names:
            if "BASE_usa" in name or not name.endswith("__wvs_Q57.json"):
                # A pair already in the v1.4 selection ships whole: the exact source bytes.
                assert files["exports/" + name] == source_path.read_bytes()
                assert files["exports/" + shipped["bin"]] == (source_path.parent / source["bin"]).read_bytes()
                continue
            # A new Q57 pair drops only d_head_norm (PM decision, WB7-Q comment 157); every kept number is the source's.
            assert set(shipped["arrays"]) == set(source["arrays"]) - {"d_head_norm"} and "light" not in shipped
            assert {k: v for k, v in shipped.items() if k not in ("arrays", "bin")} == \
                   {k: v for k, v in source.items() if k not in ("arrays", "bin")}
            pbin, sbin = files["exports/" + shipped["bin"]], (source_path.parent / source["bin"]).read_bytes()
            for array, meta in shipped["arrays"].items():
                st = source["arrays"][array]["offset"]
                assert pbin[meta["offset"]:meta["offset"] + meta["nbytes"]] == sbin[st:st + meta["nbytes"]], (name, array)
            continue
        # Every non-array field of a run is the source export's, unchanged.
        assert {k: v for k, v in shipped.items() if k not in ("arrays", "bin", "light")} == \
               {k: v for k, v in source.items() if k not in ("arrays", "bin")}
        shipped_bin = files["exports/" + shipped["bin"]]
        source_bin = (source_path.parent / source["bin"]).read_bytes()
        for array, meta in shipped["arrays"].items():
            assert meta["dtype"] == source["arrays"][array]["dtype"]
            start = source["arrays"][array]["offset"]
            # Every number is the source export's, byte for byte.
            assert shipped_bin[meta["offset"]:meta["offset"] + meta["nbytes"]] == \
                   source_bin[start:start + meta["nbytes"]], (name, array)
        if name.split("__")[1] == "BASE_usa":
            # A capture already in the v1.4 selection keeps its exact bytes.
            assert files["exports/" + name] == source_path.read_bytes()
            assert shipped_bin == source_bin
        if shipped.get("light"):
            assert not set(shipped["arrays"]) & HEAVY
            assert set(shipped["arrays"]) == set(source["arrays"]) - HEAVY - {"neuron_attr", "q3_write_norm"}
            assert sum(m["nbytes"] for m in shipped["arrays"].values()) == len(shipped_bin)
        for meta in shipped["arrays"].values():
            assert 0 <= meta["offset"] <= meta["offset"] + meta["nbytes"] <= len(shipped_bin)

    by_model = {c["model"]: c for c in index["comparators"]}
    assert len(index["comparators"]) == 4
    assert by_model["BASE_usa"] | {} == dict(model="BASE_usa", item_id="wvs_Q57", kind="adapter", cc="USA",
                                             tier="full", light=False, run="run__BASE_usa__wvs_Q57.json",
                                             pair="pair__BASE__BASE_usa__wvs_Q57.json")
    assert by_model["BASE_chn"]["light"] is True and by_model["BASE_chn"]["cc"] == "CHN"
    assert by_model["PROMPT_base_sp000000"]["kind"] == "sign_prompt"
    assert by_model["PROMPT_base_sp000000"]["bits"] == "000000" and by_model["PROMPT_base_sp000000"]["light"] is True


def test_cap_fills_adapters_first_and_leaves_the_rest_pairs_only(light, monkeypatch):
    w, args = light
    with monkeypatch.context() as m:
        m.setattr(builder, "LIGHT_DROP", tuple(n for n, _, _ in RUN_ARRAYS))   # nothing is light: numbers only
        assert builder.build_bundle(args) == 0
    floor = json.loads((w / "dist/deploy_bundle.tar.manifest.json").read_text())["payload_bytes"]
    assert builder.build_bundle(args) == 0   # unconstrained: the size of one upgrade
    sizes = json.loads((w / "dist/deploy_bundle.tar.manifest.json").read_text())["q57"]
    one = sizes["upgrade_bytes"] // len(sizes["shipped_light"])
    args.max_bytes = floor + one + one // 2   # room for one light run, not two
    assert builder.build_bundle(args) == 0
    manifest = json.loads((w / "dist/deploy_bundle.tar.manifest.json").read_text())
    files = read_archive(w / "dist/deploy_bundle.tar.gz")
    q57 = manifest["q57"]
    assert manifest["payload_bytes"] <= args.max_bytes
    assert q57["shipped_light"] == ["BASE_bgd"]
    assert q57["pairs_only"] == ["BASE_chn", "PROMPT_base_sp000000"]
    index = json.loads(files["exports/index.json"])
    assert {c["model"]: (c["tier"], c["light"]) for c in index["comparators"]} == {
        "BASE_usa": ("full", False), "BASE_bgd": ("light", True), "BASE_chn": ("numbers", False),
        "PROMPT_base_sp000000": ("numbers", False)}
    for model in q57["pairs_only"]:
        shipped = json.loads(files[f"exports/run__{model}__wvs_Q57.json"])
        assert shipped["arrays"] == {} and shipped["bin"] is None and "light" not in shipped
        assert f"exports/pair__BASE__{model}__wvs_Q57.json" in files   # its pair is still whole


def test_a_cap_below_the_numbers_floor_fails(light):
    w, args = light
    args.max_bytes = 1000
    with pytest.raises(ValueError):
        builder.build_bundle(args)


def test_check_light_rejects_heavy_array_and_size_mismatch():
    table = {"head_attr": {"dtype": "float32", "offset": 0, "nbytes": 8}}
    builder.check_light({"arrays": table}, bytes(8))
    with pytest.raises(ValueError, match="heavy"):
        builder.check_light({"arrays": table | {"g_last": {"dtype": "float32", "offset": 8, "nbytes": 8}}}, bytes(16))
    with pytest.raises(ValueError, match="size"):
        builder.check_light({"arrays": table}, bytes(9))
    with pytest.raises(ValueError, match="bounds"):
        builder.check_light({"arrays": {"head_attr": {"dtype": "float32", "offset": 4, "nbytes": 8}}}, bytes(8))


def test_comparator_identity():
    assert builder.comparator_identity("B_1_arg", "B_1") == {"kind": "adapter", "cc": "ARG"}
    assert builder.comparator_identity("X_9_base_sp010101", "B_1") == {"kind": "sign_prompt", "bits": "010101"}
    with pytest.raises(ValueError):
        builder.comparator_identity("B_1_arg_corrupt_l15", "B_1")


def test_v14_identity_check():
    baseline = {"files": {"exports/a.bin": {"sha256": "1", "bytes": 3}, "exports/index.json": {"sha256": "2", "bytes": 4},
                          "assets/app.js": {"sha256": "3", "bytes": 5}, "sca2/index.html": {"sha256": "4", "bytes": 6},
                          "sca2/sca2_data.json": {"sha256": "5", "bytes": 7}}}
    same = [{"file": n, "sha256": v["sha256"], "bytes": v["bytes"]} for n, v in baseline["files"].items()]
    assert identity.compare(baseline, {"files": same})["violations"] == []
    moved = [dict(f, sha256="9") if f["file"] in ("exports/index.json", "assets/app.js", "sca2/index.html") else f
             for f in same]
    result = identity.compare(baseline, {"files": moved})
    assert result["violations"] == [] and len(result["allowed_changed"]) == 3
    bad = [dict(f, sha256="9") if f["file"] == "exports/a.bin" else f for f in same if f["file"] != "sca2/sca2_data.json"]
    assert identity.compare(baseline, {"files": bad})["violations"] == [
        "exports/a.bin (changed)", "sca2/sca2_data.json (missing)"]


def test_real_v14_baseline_has_143_files():
    baseline = json.loads((WORKBENCH / "deploy/v1.4_file_hashes.json").read_text())
    assert len(baseline["files"]) == 143


def test_verify_bundle_accepts_light_runs_and_comparator_index(light, monkeypatch):
    w, args = light
    assert builder.build_bundle(args) == 0
    monkeypatch.undo()   # the verifier runs in its own process; restore the real subprocess.run
    out = w / "dist/deploy_bundle.tar.gz"
    report = w / "dist/verify-report.json"
    result = subprocess.run([sys.executable, str(VERIFY), str(out), str(w / "dist/extracted"),
                             "--report", str(report)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    data = json.loads(report.read_text())
    assert data["pass"] is True and data["light_runs"] == 3 and data["numbers_only_runs"] == 0
    assert data["comparators"] == 4
    assert "d_head_norm" in data["array_names"]   # the v1.4 pair stays whole
