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
            (PROMPTS, [(BASE, "PROMPT_000000", "wvs_Q57", 0.25), (BASE, "PROMPT_arg", "wvs_Q81", 0.75),
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
    assert q57["shipped_light"] == ["BASE_bgd", "BASE_chn", "PROMPT_000000"]
    assert q57["numbers_only"] == []
    assert q57["pairs_without"] == ["d_head_norm"]
    assert "every Q57 comparator" in manifest["selection_rule"]

    index = json.loads(files["exports/index.json"])
    run_names = {r["file"] for r in index["runs"]}
    pair_names = {r["file"] for r in index["pairs"]}
    assert len(index["pairs"]) == 8 and len(index["runs"]) == 10
    for name in sorted(run_names | pair_names):
        source_path = w / "exports" / folder_of(name) / name
        source = json.loads(source_path.read_text())
        shipped = json.loads(files["exports/" + name])
        # Every non-array field is the source export's, unchanged.
        assert {k: v for k, v in shipped.items() if k not in ("arrays", "bin", "light")} == \
               {k: v for k, v in source.items() if k not in ("arrays", "bin")}
        if shipped["bin"] is None:
            assert shipped["arrays"] == {}
            continue
        shipped_bin = files["exports/" + shipped["bin"]]
        source_bin = (source_path.parent / source["bin"]).read_bytes()
        for array, meta in shipped["arrays"].items():
            assert meta["dtype"] == source["arrays"][array]["dtype"]
            start = source["arrays"][array]["offset"]
            # Every number is the source export's, byte for byte.
            assert shipped_bin[meta["offset"]:meta["offset"] + meta["nbytes"]] == \
                   source_bin[start:start + meta["nbytes"]], (name, array)
        if name in pair_names and name.endswith("__wvs_Q57.json") and name.split("__")[2] != "BASE_usa":
            # A new Q57 pair: everything but the per-head array.
            assert set(shipped["arrays"]) == set(source["arrays"]) - {"d_head_norm"}, name
        if name in pair_names and ("__wvs_Q81" in name or name.split("__")[2] == "BASE_usa"):
            # A pair already in the v1.4 selection keeps its exact bytes.
            assert files["exports/" + name] == source_path.read_bytes()
            assert shipped_bin == source_bin
        if name in run_names and name.split("__")[1] == "BASE_usa":
            # A capture already in the v1.4 selection keeps its exact bytes.
            assert files["exports/" + name] == source_path.read_bytes()
            assert shipped_bin == source_bin
        if shipped.get("light"):
            assert not set(shipped["arrays"]) & HEAVY
            assert set(shipped["arrays"]) == set(builder.LIGHT_ARRAYS) & set(source["arrays"])
        for meta in shipped["arrays"].values():
            assert 0 <= meta["offset"] <= meta["offset"] + meta["nbytes"] <= len(shipped_bin)


def test_numbers_only_fallback_when_nothing_fits(light, monkeypatch):
    w, args = light
    monkeypatch.setattr(builder, "LIGHT_ARRAYS", ())
    assert builder.build_bundle(args) == 0
    manifest = json.loads((w / "dist/deploy_bundle.tar.gz").with_suffix(".manifest.json").read_text())
    files = read_archive(w / "dist/deploy_bundle.tar.gz")
    q57 = manifest["q57"]
    assert q57["shipped_light"] == [] and q57["shipped_full"] == ["BASE_usa"]
    assert q57["numbers_only"] == ["BASE_bgd", "BASE_chn", "PROMPT_000000"]
    for model in q57["numbers_only"]:
        name = f"exports/run__{model}__wvs_Q57.json"
        shipped = json.loads(files[name])
        assert shipped["arrays"] == {} and shipped["bin"] is None and "light" not in shipped
        source = json.loads((w / "exports" / folder_of(name.split("/")[-1]) / name.split("/")[-1]).read_text())
        assert {k: v for k, v in shipped.items() if k not in ("arrays", "bin")} == \
               {k: v for k, v in source.items() if k not in ("arrays", "bin")}


def test_verify_bundle_accepts_light_and_reduced_pairs(light, monkeypatch):
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
    # The head array is gone from the new Q57 pair but kept by the v1.4 pairs.
    assert "d_head_norm" in data["array_names"]
