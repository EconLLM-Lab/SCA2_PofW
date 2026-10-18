"""Card T8 — Tier-1 (bank 2) verification record and compute ledger.

Three jobs, one script, so that every number in
`planning/sprint_2026-10-11/paper-b-tier1/VERIFICATION.md` and every row appended to
`paper_b/compute/ledger.jsonl` comes from a file this script read:

  hashes      rebuild the scoring spec SHA-256 of every condition from the repo, and re-hash the frozen
              inputs (selection, pool, FREEZE.json) to check them against the freeze record
  provenance  per scoring run id, the code revision its own manifests record, and the commits that touched
              the readout path from that revision to HEAD
  ledger      harvest every GPU session of 2026-10-15..2026-10-18 from the Hub (per-run and per-session
              compute ledgers, adapter run records, the reference-cache manifest and the bank-2 generation
              manifest), append the events to `paper_b/compute/ledger.jsonl` with `compute_ledger.py`, and
              write the Tier-1 block of `paper_b/compute/publication_estimate.json`

No human data is read: only synthetic artifacts, model scores and Hub commit metadata. The HF token is
read from the `sca` profile's `.env` and never printed. Nothing is typed by hand except the Colab balance
readings quoted from the final comments of kanban cards T4 and T5, which are pinned in
`CARD_BALANCE_OBSERVATIONS` with their citation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent            # paper_b
REPO = HERE.parent
sys.path.insert(0, str(HERE))
import compute_ledger as CL  # noqa: E402

TIER1_SCHEMA = "sca2.compute_tier1.v1"
ARTIFACTS_REPO = "Bonorinoa/SCA2-paper-b-artifacts"
ADAPTERS_REPO = "Bonorinoa/SCA2-paper-b-adapters"
BANK_RUN_ID = "gps_sign_relabel_bank2_20261015_062543Z"
BANK_STATE = f"bank2/{BANK_RUN_ID}/state"
GEN_MANIFEST = f"banks/bank2_{BANK_RUN_ID}/gen_raw/generation_manifest.json"
TOKEN_FILE = Path("/Users/bonorinoa/.hermes/profiles/sca/.env")
DEFAULT_CACHE = Path(tempfile.gettempdir()) / "sca2_tier1_verification"

# A gap longer than this between two recorded unit clocks starts a new GPU session. 60 minutes is above every
# gap inside a session (the largest is 44.0 min, the pause between the near-zero training and its scoring on
# 2026-10-18) and below every gap between sessions (the smallest is 2.3 h, between the para-b and T4 sessions).
SESSION_GAP_MINUTES = 60.0
# The code a scoring run reads: the scorer, the plan that pins the spec, the CLI, the spec builder, and the
# frozen readout constants. A diff of these files from a run's revision to HEAD is the provenance claim.
READOUT_FILES = (
    "paper_b/score_runtime.py", "paper_b/score_plan.py", "paper_b/score_cohort.py",
    "paper_b/build_scoring_spec.py", "paper_b/eval_lib.py", "paper_b/eval_config.py",
)
# Readout constants that are frozen by a test in this repo (paper_b/test_score_runtime.py, test_prompt_pin.py).
FROZEN_READOUT_CONSTANTS = "T=1, completion ' '+code, 768-token prompt, no length normalisation"

# Colab reports a REMAINING BALANCE, not consumption. These are the observations quoted in the final comments
# of kanban cards T4 (t_b42d0d84) and T5 (t_719abccf); the compute ledger cannot measure them itself.
CARD_BALANCE_OBSERVATIONS = [
    {"card": "T4", "session": "2026-10-18T00:01Z..03:02Z", "before": 192.74, "after": 189.98,
     "stage": "scoring", "covers": ["replicate r1 strict + heldout", "64 sign-prompt cells, strict"],
     "source": "final comment of kanban card T4 (t_b42d0d84)"},
    {"card": "T5", "session": "2026-10-18T01:46Z..03:02Z", "before": 188.96, "after": 186.74,
     "stage": "training+scoring", "covers": ["4 near-zero adapters (1.6 T4 units, the card's own session hours)",
                                             "Augusto's separate TPU assignment in the same window"],
     "source": "final comment of kanban card T5 (t_719abccf) plus the orchestrator's 2026-10-17 addendum"},
]


def _harvest_at() -> str:
    """One timestamp for the whole harvest: re-running does not re-stamp a row that is already there."""
    return os.environ.get("SCA2_TIER1_RECORDED_AT") or datetime.now().astimezone().replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _hub_token() -> str:
    for line in TOKEN_FILE.read_text().splitlines():
        if line.startswith("HF_TOKEN="):
            return line.split("=", 1)[1].strip().strip("'\"")
    raise RuntimeError(f"HF_TOKEN is not in {TOKEN_FILE}")


# --------------------------------------------------------------------------- spec and input hashes

def spec_table() -> dict:
    """Every condition's spec SHA-256, rebuilt here, next to the pin the VM refuses to run without."""
    import score_plan as SPL
    pins = json.loads(SPL.PINS.read_text())
    table = {}
    for cond in SPL.CONDITIONS:
        c = SPL.CONDITIONS[cond]
        spec = SPL.build_spec(cond)
        table[cond] = {
            "sha256": SPL.spec_hash(spec), "pinned_sha256": pins["spec_sha256"].get(cond),
            "n_questions": spec["n_questions"], "battery": c["battery"], "variant": c["variant"],
            "kind": c["kind"], "run_id": c["run_id"],
        }
    return table


def spec_pin_mismatches() -> list[dict]:
    return [{"condition": k, "built": v["sha256"], "pinned": v["pinned_sha256"]}
            for k, v in spec_table().items() if v["sha256"] != v["pinned_sha256"]]


def frozen_input_hashes() -> dict:
    held = HERE / "heldout"
    freeze_path = held / "FREEZE.json"
    freeze = json.loads(freeze_path.read_text())
    selection = held / "selection_amended_20261016.csv"
    pool = held / "pool_skeleton.csv"
    return {
        "selection_path": str(selection), "selection_sha256": sha256_file(selection),
        "selection_sha256_match": sha256_file(selection) == freeze["selection_sha256"],
        "pool_path": str(pool), "pool_sha256": sha256_file(pool),
        "pool_sha256_match": sha256_file(pool) == freeze["pool_sha256"],
        "freeze_sha256": sha256_file(freeze_path),
        "freeze_frozen_at": freeze["frozen_at"], "frozen_code_revision": freeze["code_revision"],
        "scoring_code_revision": freeze["scoring_code_revision"],
        "selected_items": freeze["selected_items"], "n_items": freeze["n_items"],
        "overrides_sha256": sha256_file(held / "overrides.json"),
        "face_valid_sha256": sha256_file(held / "face_valid.csv"),
        "comparator_review_sha256": sha256_file(held / "comparator_review.json"),
        "run_ids": freeze["run_ids"],
    }


def revision_pins() -> dict:
    import score_plan as SPL
    pins = json.loads(SPL.PINS.read_text())
    bank2 = json.loads((HERE / "bank2_pins.json").read_text())
    return {
        "adapter_revision": pins["adapter_revision"], "nearzero_adapter_revision": pins["nearzero_adapter_revision"],
        "score_plan_revision": SPL.ADAPTER_REVISION,
        "bank_run_id": bank2["relabel_run_id"], "generation_run_id": bank2["generation_run_id"],
        "bank_bundle_sha256": bank2["bundle"]["sha256"], "refcache_sha256": bank2["refcache"]["sha256"],
        "refcache_rows": bank2["refcache"]["rows"], "refcache_manifest_sha256": bank2["refcache_manifest"]["sha256"],
        "nearzero_bank_bundle": pins["nearzero_bank_bundle"],
    }


# --------------------------------------------------------------------------- provenance

def readout_diff(code_revision: str) -> dict:
    """What HEAD changed in the readout path since `code_revision` (a git commit of this repo)."""
    def run(*args):
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=False)

    if run("cat-file", "-t", code_revision).stdout.strip() != "commit":
        return {"revision": code_revision, "present_locally": False}
    stat = run("diff", "--stat", f"{code_revision}..HEAD", "--", *READOUT_FILES).stdout.strip()
    diff = run("diff", f"{code_revision}..HEAD", "--", *READOUT_FILES).stdout
    removed = [ln for ln in diff.splitlines() if ln.startswith("-") and not ln.startswith("---")]
    touched = sorted({ln.split()[2][2:] for ln in diff.splitlines()
                      if ln.startswith("diff --git ") and len(ln.split()) >= 3})
    return {
        "revision": code_revision, "present_locally": True,
        "stat": stat.splitlines() or [],
        "files_touched": touched,
        "removed_line_count": len(removed),
        "removed_lines": removed,
        "identical": not stat,
    }


def provenance_table(manifests: dict[str, dict]) -> dict:
    """Per run id: the code revision its manifests record, and the readout diff from it to HEAD."""
    per_run: dict[str, Counter] = {}
    models: dict[str, dict[str, list[str]]] = {}
    for path, manifest in manifests.items():
        run_id = path.split("/")[1]
        revision = manifest.get("code_revision_sha256")
        per_run.setdefault(run_id, Counter())[revision] += 1
        models.setdefault(run_id, {}).setdefault(revision, []).append(manifest.get("model"))
    out = {}
    for run_id, counter in sorted(per_run.items()):
        revisions = {r: n for r, n in counter.items() if r}
        primary = counter.most_common(1)[0][0]
        out[run_id] = {
            "n_manifests": sum(counter.values()), "code_revisions": revisions,
            "agree": len(revisions) == 1, "code_revision": primary,
            "code_revision_missing": counter.get(None, 0),
            "models_by_revision": {r: sorted(m) for r, m in models[run_id].items() if r},
            "readout_diff_to_head": readout_diff(primary) if primary else None,
        }
    return out


# --------------------------------------------------------------------------- ledger arithmetic

def _copy_key(row: dict) -> tuple:
    """Identity of one recorded clock. The Hub keeps one accumulated ledger per session, so the same row is
    uploaded into several `runs/<run id>/compute/` directories; this key collapses those copies and keeps a
    deliberate repeat (the same unit retrained or rescored in another session) apart."""
    prov = row.get("provenance") or {}
    return (prov.get("run_id") or row.get("source") or "", row.get("stage"), row.get("unit"),
            row.get("wall_minutes"), row.get("recorded_at"))


def _unit_key(row: dict) -> tuple:
    prov = row.get("provenance") or {}
    return (prov.get("run_id") or row.get("source") or "", row.get("stage"), row.get("unit"))


def dedupe_copies(rows: list[dict]) -> tuple[list[dict], int]:
    """Collapse rows that are the same recorded clock, keep different clocks of the same unit."""
    seen, kept = set(), []
    for row in rows:
        key = _copy_key(row)
        if key in seen:
            continue
        seen.add(key)
        kept.append(row)
    return sorted(kept, key=lambda r: r["recorded_at"]), len(rows) - len(kept)


def repeat_unit_keys(rows: list[dict]) -> list[tuple]:
    """Units that were trained or scored more than once in the window (two clocks, both real)."""
    counts = Counter(_unit_key(r) for r in rows)
    return sorted(k for k, n in counts.items() if n > 1)


def cluster_sessions(events: list[dict], gap_minutes: float = SESSION_GAP_MINUTES) -> list[dict]:
    """Group recorded clocks into GPU sessions: a gap longer than `gap_minutes` starts a new one."""
    clusters: list[dict] = []
    for row in sorted(events, key=lambda r: r["recorded_at"]):
        at = datetime.fromisoformat(row["recorded_at"])
        if clusters:
            current = clusters[-1]
            own = (at - current["current"]).total_seconds() / 60
            if own <= gap_minutes:
                current["last"] = at
                current["n_events"] += 1
                current["units"].append(row["unit"])
                if row["stage"] not in current["stages"]:
                    current["stages"].append(row["stage"])
                continue
        clusters.append({"first": at, "last": at, "current": at, "n_events": 1,
                         "units": [row["unit"]], "stages": [row["stage"]]})
    return [{"first_utc": c["first"].isoformat(), "last_utc": c["last"].isoformat(),
             "span_minutes": round((c["last"] - c["first"]).total_seconds() / 60, 4),
             "n_events": c["n_events"], "units": c["units"], "stages": c["stages"]}
            for c in clusters]


def _train_event(record: dict, source: str, recorded_at: str | None = None) -> dict:
    return CL.train_event_from_record(record, source=source, recorded_at=recorded_at or _harvest_at())


def _score_event(row: dict) -> dict:
    prov = row.get("provenance") or {}
    run_id = prov.get("run_id") or ""
    return CL.make_event(
        stage="score", unit=row["unit"], wall_minutes=row["wall_minutes"],
        scope=row.get("scope", "score_and_persist"), source=f"{row.get('source', 'score_cohort.py')}:{run_id}",
        role="live", includes=row.get("includes", []), excludes=row.get("excludes", ["session_idle"]),
        provenance={"run_id": run_id, "adapter_revision": prov.get("adapter_revision"),
                    "observed_at_utc": row["recorded_at"]},
        hardware=row.get("hardware") or {}, recorded_at=_harvest_at(),
        notes="Measured on the VM; observed_at_utc is when the VM recorded it.")


def session_events(clusters: list[dict]) -> list[dict]:
    out = []
    for i, c in enumerate(clusters, 1):
        event = CL.make_event(
            stage="gpu_session", unit=f"tier1-session-{i}", wall_minutes=c["span_minutes"],
            scope="gpu session wall clock: first to last recorded unit clock",
            source="harvested from Hub compute ledgers", role="session_loop",
            includes=[f"{c['n_events']} recorded unit clocks", *c["stages"]],
            excludes=["vm provision", "session idle outside the recorded clocks",
                      "units whose session ledger was never uploaded"],
            provenance={"first_utc": c["first_utc"], "last_utc": c["last_utc"], "n_events": c["n_events"]},
            recorded_at=_harvest_at())
        event.update(n_events=c["n_events"], units=c["units"])
        out.append(event)
    return out


def _totals(events: list[dict]) -> dict:
    minutes = [float(e["wall_minutes"]) for e in events if e.get("wall_minutes") is not None]
    return {"n": len(minutes), "wall_minutes": round(sum(minutes), 4),
            "gpu_hours": round(sum(minutes) / 60, 4)}


def tier1_block(*, train_events, score_events, session_events, ref_event, endpoints, recorded_at,
                repeats=None, observations=None) -> dict:
    """The citable Tier-1 block. Totals are per stage; the clocks are never summed into one number."""
    train, score = _totals(train_events), _totals(score_events)
    return {
        "schema": TIER1_SCHEMA,
        "recorded_at": recorded_at,
        "bank_run_id": BANK_RUN_ID,
        "do_not_cite_as_invoice": True,
        "measured": {
            "train_surviving": {
                **train, "scope": "trainer.train",
                "source": f"adapter run_record.json under bank2/{BANK_RUN_ID}/ on {ADAPTERS_REPO} "
                          "(one clock per trained adapter)",
                "excludes": ["model_load", "model_download", "adapter_save", "hub_upload", "session_idle"],
            },
            "score_live": {
                **score, "scope": "score_and_persist",
                "source": f"runs/*/compute/ledger.jsonl on {ARTIFACTS_REPO}, deduped per run id and unit",
                "excludes": ["session_idle", "the 64 sign-prompt cells of each sign-prompt run, which "
                             "record no per-unit ledger row"],
            },
            "ref_cache": ref_event,
            "gpu_sessions": session_events,
        },
        "stage_totals": {"training": train, "scoring": score},
        "endpoints": endpoints,
        "colab_units": {"observations": observations or CARD_BALANCE_OBSERVATIONS, "note": (
            "Colab reports a remaining balance, not consumption. The before/after pairs are quoted from the "
            "kanban cards named in each observation; the training and scoring sessions of 2026-10-15/16 have "
            "no balance reading, so their unit cost is unknown.")},
        "repeated_units": repeats or [],
        "unknown": [
            "Billed Colab units per stage. Only two before/after balance pairs exist, both from card comments.",
            "Sessions of 2026-10-15/16 (bank-2 training waves) have no balance reading.",
            "VM provision, model download, adapter upload and session idle.",
            "The 10 profile units whose 2026-10-15 session ledger was never uploaded: their training clock "
            "survives in the adapter run record, their session wall time does not.",
        ],
    }


# --------------------------------------------------------------------------- writing

def append_ledger(path: Path, events: list[dict]) -> int:
    return CL.append_events(Path(path), events)


def update_estimate(path: Path, block: dict) -> dict:
    path = Path(path)
    estimate = json.loads(path.read_text()) if path.exists() else {}
    estimate["tier1_bank2"] = block
    path.write_text(json.dumps(estimate, indent=2) + "\n")
    return estimate


# --------------------------------------------------------------------------- harvest

def _download(cache: Path, repo: str, path: str, token: str) -> Path:
    from huggingface_hub import hf_hub_download
    return Path(hf_hub_download(repo, path, repo_type="dataset", token=token, local_dir=str(cache / repo)))


def harvest(cache: Path = DEFAULT_CACHE) -> dict:
    """Download every source and return the raw material. Nothing is written outside `cache`."""
    from huggingface_hub import HfApi
    token = _hub_token()
    api = HfApi(token=token)
    artifacts = api.list_repo_files(ARTIFACTS_REPO, repo_type="dataset", token=token)
    state_ledgers = sorted(f for f in artifacts
                           if f.startswith(f"{BANK_STATE}/") and f.endswith("compute_ledger.jsonl"))
    run_ledgers = sorted(f for f in artifacts if f.startswith("runs/") and f.endswith("compute/ledger.jsonl"))
    manifests = sorted(f for f in artifacts
                       if f.startswith("runs/") and f.endswith("_manifest.json")
                       and not f.startswith("runs/paper-b-20261011/") and not f.startswith("runs/sign-prompt-20261011/"))
    adapters = api.list_repo_files(ADAPTERS_REPO, repo_type="dataset", token=token)
    records = sorted(f for f in adapters if is_tier1_adapter_path(f))

    rows: list[dict] = []
    for hub_path in state_ledgers + run_ledgers:
        text = _download(cache, ARTIFACTS_REPO, hub_path, token).read_text()
        for line in text.splitlines():
            if line.strip():
                row = json.loads(line)
                row["_hub_path"] = hub_path
                rows.append(row)
    manifest_data = {f: json.loads(_download(cache, ARTIFACTS_REPO, f, token).read_text()) for f in manifests}
    ref_manifest = json.loads(_download(
        cache, ARTIFACTS_REPO, f"{BANK_STATE}/refcache/shared_reference_logps_manifest.json", token).read_text())
    generation = json.loads(_download(cache, ARTIFACTS_REPO, GEN_MANIFEST, token).read_text())
    train_records = [{"path": f, "record": json.loads(_download(cache, ADAPTERS_REPO, f, token).read_text())}
                     for f in records]
    return {"rows": rows, "state_ledgers": state_ledgers, "run_ledgers": run_ledgers,
            "manifests": manifest_data, "ref_manifest": ref_manifest,
            "generation": generation, "train_records": train_records}


def is_tier1_adapter_path(path: str) -> bool:
    return str(path).startswith(f"bank2/{BANK_RUN_ID}/") and str(path).endswith("run_record.json")


def build(harvested: dict) -> dict:
    """Turn the harvest into (train events, score events, session events, ref event, block)."""
    rows, dropped = dedupe_copies(harvested["rows"])
    train_rows = [r for r in rows if r["stage"] == "train"]
    score_rows = [r for r in rows if r["stage"] == "score"]
    clusters = cluster_sessions(rows)
    train_events = [_train_event(item["record"], source=f"{ADAPTERS_REPO}:{item['path']}")
                    for item in harvested["train_records"]]
    score_events = [_score_event(r) for r in score_rows]
    sessions = session_events(clusters)
    ref = harvested["ref_manifest"]
    ref_event = CL.ref_event_from_manifest(ref, source=f"{ARTIFACTS_REPO}:{BANK_STATE}/refcache/"
                                                        "shared_reference_logps_manifest.json",
                                           recorded_at=_harvest_at())
    endpoints = harvested["generation"]["cost_summary"]["endpoint_runtime_cost"]
    block = tier1_block(
        train_events=train_events, score_events=score_events, session_events=sessions, ref_event=ref_event,
        endpoints={"total_cost_usd": endpoints["total_cost_usd"],
                   "per_endpoint_usd": {k: v["cost_usd"] for k, v in endpoints["endpoints"].items()},
                   "elapsed_seconds": endpoints["elapsed_seconds"],
                   "historical_observed_total_usd": endpoints["historical_endpoint_spend"]["total_observed_cost_usd"],
                   "source": f"{ARTIFACTS_REPO}:{GEN_MANIFEST}",
                   "note": "Endpoint spend for the bank-2 generation. The historical figure is the provider "
                           "console's observed total since endpoint creation, calibration only."},
        recorded_at=_harvest_at(), repeats=repeat_unit_keys(rows))
    return {"rows": rows, "dropped": dropped, "train_rows": train_rows, "score_rows": score_rows,
            "clusters": clusters, "train_events": train_events, "score_events": score_events,
            "session_events": sessions, "ref_event": ref_event, "block": block}


# --------------------------------------------------------------------------- CLI

def _emit(payload: dict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=False, default=str))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    h = sub.add_parser("hashes", help="spec SHA-256 per condition and the frozen-input digests")
    h.add_argument("--bank-digests", action="store_true", help="also re-hash the bank inputs")
    p = sub.add_parser("provenance", help="per scoring run id: code revision and readout diff to HEAD")
    p.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    led = sub.add_parser("ledger", help="append the Tier-1 sessions and write the Tier-1 estimate block")
    led.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    led.add_argument("--ledger", type=Path, default=HERE / "compute" / "ledger.jsonl")
    led.add_argument("--estimate", type=Path, default=HERE / "compute" / "publication_estimate.json")
    led.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "hashes":
        _emit({"spec": spec_table(), "spec_pin_mismatches": spec_pin_mismatches(),
               "frozen": frozen_input_hashes(), "revisions": revision_pins()})
        return 0
    if a.cmd == "provenance":
        harvested = harvest(a.cache)
        _emit({"provenance": provenance_table(harvested["manifests"])})
        return 0
    if a.cmd == "ledger":
        harvested = harvest(a.cache)
        built = build(harvested)
        added = 0 if a.dry_run else append_ledger(a.ledger, built["train_events"] + built["score_events"]
                                                  + built["session_events"] + [built["ref_event"]])
        if not a.dry_run:
            update_estimate(a.estimate, built["block"])
        _emit({"sessions": built["clusters"], "dropped_duplicate_rows": built["dropped"],
               "appended_events": added, "repeated_units": repeat_unit_keys(built["rows"]),
               "stage_totals": built["block"]["stage_totals"],
               "dry_run": bool(a.dry_run)})
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
