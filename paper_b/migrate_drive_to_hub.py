#!/usr/bin/env python3
"""Stage and upload the SCA2 Drive archive to the Hugging Face Hub (copy only; Drive is never modified).

Phases:  stage  -> build the three repo layouts under STAGE_ROOT and write MIGRATION_MANIFEST.json
         upload -> push each staged repo (retrying), never touching existing adapters/<CC> paths
         verify -> compare every staged file with the Hub (LFS sha256 or git blob id)

Repos (all private):
  Bonorinoa/SCA2-paper-b-adapters   weights only (adds replicates/ and a README; adapters/ untouched)
  Bonorinoa/SCA2-paper-b-artifacts  banks, reference caches, run state, logs, notebooks, manifest
  Bonorinoa/SCA2-phase2-artifacts   Paper A Phase-2 analysis/eval/docs + DPO_CO2 (human-derived aggregates)

The token is read from the profile .env and is never printed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

HOME = Path("/Users/bonorinoa")
STAGE_ROOT = Path(os.environ.get("MIGR_STAGE", HOME / ".hermes/profiles/sca/cache/scratch/migr/stage"))
DRIVE = STAGE_ROOT / "drive"
HFROOT = STAGE_ROOT / "hf"
SG = HOME / "Desktop/Github_Repositories/SCA2_PofW/synthetic_generation/outputs"
BUNDLE = HOME / ".hermes/profiles/sca/cache/scratch/pb_bank2_profiles.tgz"
INV = HOME / ".hermes/profiles/sca/cache/scratch/migr"

ADAPTERS = "Bonorinoa/SCA2-paper-b-adapters"
ARTIFACTS = "Bonorinoa/SCA2-paper-b-artifacts"
PHASE2 = "Bonorinoa/SCA2-phase2-artifacts"
RELABEL_RUN = "gps_sign_relabel_bank2_20261015_062543Z"
GEN_RUN = "bank2_20261014_20261015T062513Z"
HUMAN_DERIVED = re.compile(r"(population_response|wvs_|/wvs/|eval_results_wvs|survey_)", re.I)

README = {
    ADAPTERS: """# SCA2 Paper B adapters (weights only)

Private dataset repo. `adapters/<CC>/` are the 42 cohort-1 country adapters (never overwritten).
`bank2/<run>/profiles/<unit>/` are the 64 sign-profile adapters trained on bank 2.
`replicates/` holds extra training runs kept for the training-noise audit; they are not used by any score.
Everything else lives in `Bonorinoa/SCA2-paper-b-artifacts`. Hashes: see its `MIGRATION_MANIFEST.json`.
""",
    ARTIFACTS: f"""# SCA2 Paper B artifacts

Private dataset repo (no human respondent data; synthetic text, caches, logs, manifests).

- `cohort1/`    run state of the 42-country run (reference cache, manifests, logs).
- `banks/bank2_{RELABEL_RUN}/`  bank 2 generation outputs, relabel sources, and `bank2_bundle.tgz`
  (the exact bundle the Colab VMs unpack; SHA-256 in `SHA256SUMS`).
- `bank2/{RELABEL_RUN}/state/`  reference cache with SHA-256, per-wave logs, manifests, ledgers.
- `runs/`, `manifests/`  earlier Paper B result runs.
- `drive_archive/`  files copied from Google Drive on 2026-10-15. Drive is now a read-only archive.
- `MIGRATION_MANIFEST.json`  every copied file: Hub path, size, SHA-256, Drive source and Drive MD5.
""",
    PHASE2: """# SCA2 Phase 2 artifacts (Paper A)

Private dataset repo. Copied from Google Drive `SCA2_phase2/` and `DPO_CO2/` on 2026-10-15.
Contains human-derived country-level aggregates (WVS population response distributions and metric tables).
No respondent-level files (.dta/.sav) are included. Keep this repo private.
`SCA2_phase2/public_eval/` was not copied; it stays on Drive for the public eval pack.
Hashes: see `Bonorinoa/SCA2-paper-b-artifacts` `MIGRATION_MANIFEST.json`.
""",
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def git_blob(p: Path) -> str:
    data = p.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def token() -> str:
    for line in (HOME / ".hermes/profiles/sca/.env").read_text().splitlines():
        if line.startswith("HF_TOKEN="):
            return line.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit("HF_TOKEN missing in profile .env")


def put(src: Path, repo: str, dest: str, meta: list, source: str, drive_md5: str | None = None):
    out = HFROOT / repo.split("/")[1] / dest
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, out)
    meta.append({"hf_repo": repo, "hf_path": dest, "size": out.stat().st_size, "sha256": sha256(out),
                 "source": source, "drive_md5": drive_md5,
                 "human_derived_aggregate": bool(HUMAN_DERIVED.search(dest)) and repo == PHASE2})


def drive_md5_index() -> dict:
    idx = {}
    for name, prefix in (("SCA2_paper_b", "SCA2_paper_b/"), ("SCA2_paper_b_bank2_profiles", "SCA2_paper_b_bank2_profiles/"),
                         ("SCA2_phase2", "SCA2_phase2/"), ("DPO_CO2", "DPO_CO2/")):
        f = INV / f"inv_{name}.json"
        if f.exists():
            for i in json.loads(f.read_text()):
                idx[prefix + i["Path"]] = i.get("Hashes", {}).get("md5")
    return idx


def stage() -> None:
    if HFROOT.exists():
        shutil.rmtree(HFROOT)
    meta: list[dict] = []
    md5 = drive_md5_index()
    # --- adapters repo: GRC replicate (the Drive training run that is NOT the Hub copy)
    grc = INV / "drive_w/GRC/adapter_model.safetensors"
    rep = "replicates/cohort1_GRC_drive_20261010T155517Z"
    put(grc, ADAPTERS, f"{rep}/adapter_model.safetensors", meta, "Drive SCA2_paper_b/adapters/GRC",
        md5.get("SCA2_paper_b/adapters/GRC/adapter_model.safetensors"))
    for n in ("adapter_config.json", "run_record.json"):
        tmp = STAGE_ROOT / "tmp_grc" / n
        tmp.parent.mkdir(parents=True, exist_ok=True)
        os.system(f"env -u PYTHONPATH rclone copyto 'sca2drive:SCA2_paper_b/adapters/GRC/{n}' '{tmp}' 2>/dev/null")
        put(tmp, ADAPTERS, f"{rep}/{n}", meta, f"Drive SCA2_paper_b/adapters/GRC/{n}",
            md5.get(f"SCA2_paper_b/adapters/GRC/{n}"))
    # --- artifacts repo
    d = DRIVE / "paper_b"
    for f in sorted(d.rglob("*")):
        if f.is_file():
            rel = f.relative_to(d).as_posix()
            put(f, ARTIFACTS, f"cohort1/{rel}", meta, f"Drive SCA2_paper_b/{rel}", md5.get(f"SCA2_paper_b/{rel}"))
    b2 = DRIVE / "bank2_profiles"
    st = f"bank2/{RELABEL_RUN}/state"
    for n in ("shared_reference_logps.jsonl", "shared_reference_logps_manifest.json"):
        put(b2 / n, ARTIFACTS, f"{st}/refcache/{n}", meta, f"Drive SCA2_paper_b_bank2_profiles/{n}",
            md5.get(f"SCA2_paper_b_bank2_profiles/{n}"))
    for f in sorted(b2.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(b2).as_posix()
        if rel.startswith("shared_reference") or rel.startswith("adapters/"):
            continue
        put(f, ARTIFACTS, f"{st}/session1_drive_snapshot/{rel}", meta, f"Drive SCA2_paper_b_bank2_profiles/{rel}",
            md5.get(f"SCA2_paper_b_bank2_profiles/{rel}"))
    bk = f"banks/bank2_{RELABEL_RUN}"
    for rel, src in (("gen_raw/checkpoint_raw_pairs.jsonl", SG / "bank2_20261014/raw/checkpoint_raw_pairs.jsonl"),
                     ("gen_raw/checkpoint_scenario_bank.json", SG / "bank2_20261014/raw/checkpoint_scenario_bank.json"),
                     ("gen_raw/generation_manifest.json", SG / "bank2_20261014/raw/generation_manifest.json"),
                     ("gen_raw/stage_cache_full.jsonl", SG / "bank2_20261014/stage_cache_full.jsonl"),
                     ("relabel/triplets_bank.jsonl", SG / "gps_sign_relabel_bank2/triplets_bank.jsonl"),
                     ("relabel/gps_z_vectors.json", SG / "gps_sign_relabel_bank2/gps_z_vectors.json"),
                     ("relabel/manifest.json", SG / "gps_sign_relabel_bank2/manifest.json"),
                     ("bank2_bundle.tgz", BUNDLE)):
        put(src, ARTIFACTS, f"{bk}/{rel}", meta, f"local {src.relative_to(HOME)}")
    for f in sorted((DRIVE / "notebooks").glob("*.ipynb")):
        put(f, ARTIFACTS, f"drive_archive/colab_notebooks/{f.name}", meta, f"Drive Colab Notebooks/{f.name}")
    # --- phase2 repo
    for f in sorted((DRIVE / "phase2").rglob("*")):
        if f.is_file():
            rel = f.relative_to(DRIVE / "phase2").as_posix()
            put(f, PHASE2, rel, meta, f"Drive SCA2_phase2/{rel}", md5.get(f"SCA2_phase2/{rel}"))
    for f in sorted((DRIVE / "dpo_co2").rglob("*")):
        if f.is_file():
            rel = f.relative_to(DRIVE / "dpo_co2").as_posix()
            put(f, PHASE2, f"dpo_co2/{rel}", meta, f"Drive DPO_CO2/{rel}", md5.get(f"DPO_CO2/{rel}"))
    # --- SHA256SUMS for the bundle + readmes + manifest
    bundle = next(m for m in meta if m["hf_path"].endswith("bank2_bundle.tgz"))
    sums = HFROOT / "SCA2-paper-b-artifacts" / bk / "SHA256SUMS"
    sums.write_text("".join(f"{m['sha256']}  {Path(m['hf_path']).name}\n" for m in meta
                            if m["hf_path"].startswith(bk) or "refcache/" in m["hf_path"]))
    for repo, text in README.items():
        p = HFROOT / repo.split("/")[1] / "README.md"
        p.write_text(text)
    manifest = {
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "purpose": "Drive -> Hub migration of SCA2 (Paper A and B) artifacts. Copy only; Drive unchanged.",
        "not_migrated": {
            "SCA2_paper_b/adapters": "Hub canonical for 42 countries; 33 of 34 Drive weight files byte-identical; "
                                     "GRC differs (separate training run, archived under replicates/); VNM has no top-level weights on Drive.",
            "SCA2_paper_b/prepared, SCA2_paper_b_bank2_profiles/prepared": "rebuildable from banks plus reference cache",
            "SCA2_paper_b/qtest.txt": "write probe",
            "SCA2_paper_b_bank2_profiles/adapters": "5 profile adapters verified byte-identical to the Hub",
            "SCA2_phase2/public_eval": "stays on Drive (public eval pack)",
            "Research/Projects/WVS Cultural Fine-Tuning": "contains raw WVS respondent data and an earlier project; not SCA2",
            "Colab Notebooks (one duplicate-named sca2_synthetic_generation_colab.ipynb)": "Drive duplicate name; one copy archived",
        },
        "bundle_sha256": bundle["sha256"],
        "files": meta,
    }
    (HFROOT / "SCA2-paper-b-artifacts" / "MIGRATION_MANIFEST.json").write_text(json.dumps(manifest, indent=1))
    per = {}
    for m in meta:
        per.setdefault(m["hf_repo"], [0, 0])
        per[m["hf_repo"]][0] += 1
        per[m["hf_repo"]][1] += m["size"]
    for r, (n, s) in per.items():
        print(f"staged {r}: {n} files, {s/1e6:.1f} MB")
    print("human-derived aggregate files flagged:", sum(m["human_derived_aggregate"] for m in meta))


def _retry(fn, what, tries=3):
    for k in range(1, tries + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            print(f"  {what}: attempt {k} failed: {type(e).__name__}: {str(e)[:160]}")
            if k == tries:
                raise
            time.sleep(10 * k)


def upload() -> None:
    from huggingface_hub import HfApi
    api = HfApi(token=token())
    for repo in (PHASE2,):
        api.create_repo(repo, repo_type="dataset", private=True, exist_ok=True)
    for repo in (ADAPTERS, ARTIFACTS, PHASE2):
        info = api.repo_info(repo, repo_type="dataset")
        assert info.private, f"{repo} must be private"
        folder = HFROOT / repo.split("/")[1]
        existing = {f for f in api.list_repo_files(repo, repo_type="dataset")}
        if repo == ADAPTERS:                       # never touch or replace anything already there
            clash = [p.relative_to(folder).as_posix() for p in folder.rglob("*")
                     if p.is_file() and p.relative_to(folder).as_posix() in existing]
            if clash:
                keep = [c for c in clash if c != "README.md"]
                assert not keep, f"refusing to overwrite existing adapter-repo paths: {keep[:3]}"
                (folder / "README.md").unlink(missing_ok=True)
        t0 = time.time()
        _retry(lambda: api.upload_folder(repo_id=repo, repo_type="dataset", folder_path=str(folder),
                                         commit_message="Drive archive migration 2026-10-15 (copy only)"),
               f"upload {repo}")
        print(f"uploaded {repo} in {time.time()-t0:.0f}s")


def verify() -> int:
    from huggingface_hub import HfApi
    api = HfApi(token=token())
    bad = 0
    for repo in (ADAPTERS, ARTIFACTS, PHASE2):
        folder = HFROOT / repo.split("/")[1]
        info = api.dataset_info(repo, files_metadata=True)
        hub = {s.rfilename: s for s in (info.siblings or [])}
        n = 0
        for p in sorted(folder.rglob("*")):
            if not p.is_file() or ".cache" in p.parts:
                continue
            rel = p.relative_to(folder).as_posix()
            s = hub.get(rel)
            if s is None:
                if repo == ADAPTERS and rel == "README.md":
                    continue
                print("MISSING", repo, rel); bad += 1; continue
            ok = (s.lfs.sha256 == sha256(p)) if s.lfs else (s.blob_id == git_blob(p))
            if not ok or s.size != p.stat().st_size:
                print("MISMATCH", repo, rel); bad += 1
            n += 1
        print(f"verified {repo}: {n} staged files match the Hub")
    print("VERIFY OK" if bad == 0 else f"VERIFY FAILED: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["stage", "upload", "verify"])
    a = ap.parse_args()
    if a.phase == "stage":
        stage()
    elif a.phase == "upload":
        upload()
    else:
        sys.exit(verify())
