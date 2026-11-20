#!/usr/bin/env python3
"""Paper B compute ledger.

Publication clocks and live run records. A number enters the ledger only from
a named source. Heterogeneous clocks are not summed into one GPU-hour total,
and a Colab balance is not treated as an invoice.

Live jobs append to ``DATA_ROOT/compute_ledger.jsonl``. A failed append must
not fail a completed training or scoring run: callers use ``try_record``.

Rebuild the publication snapshot from harvested sources::

    python paper_b/compute_ledger.py publish \\
        --sources paper_b/compute/sources --out paper_b/compute
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C

SCHEMA = "sca2.compute_event.v1"
ESTIMATE_SCHEMA = "sca2.compute_estimate.v1"
# Log lines print minutes to 1 decimal. A stored 2-decimal value from the
# same run differs by at most 0.05. Real retrains in the wave logs differ
# by at least 0.6, so 0.06 separates rounding from a different run.
PRINT_MATCH_TOLERANCE_MIN = 0.06

# A unit is either a cohort-1 three-letter country code or a bank-2 profile cell P_<six bits>.
# Kept as an explicit alternation: a looser token would match arbitrary text in the log.
_UNIT = r"(?:[A-Z]{3}|P_[01](?:_[01]){5})"
_HEADER = re.compile(rf"^===== ({_UNIT}) =====", re.M)
_SAVED = re.compile(rf"saved adapter -> .+/({_UNIT}) in ([0-9.]+) min")
_ELAPSED = re.compile(r"cohort done: (\d+) adapters \| elapsed ([0-9.]+) min")
_VRAM = re.compile(r"VRAM free ([0-9.]+)/([0-9.]+) GiB")


def ledger_path() -> Path:
    return C.DATA_ROOT / "compute_ledger.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def event_id(event: dict) -> str:
    """Stable id from the identifying fields, so a republish does not duplicate."""
    keys = (
        "schema", "stage", "unit", "role", "scope", "source",
        "wall_minutes", "status",
    )
    payload = {k: event.get(k) for k in keys}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def make_event(
    *,
    stage: str,
    unit: str,
    wall_minutes: float | None,
    scope: str,
    source: str,
    status: str = "measured",
    role: str = "observed",
    excludes: list[str] | None = None,
    includes: list[str] | None = None,
    provenance: dict | None = None,
    hardware: dict | None = None,
    recorded_at: str | None = None,
    notes: str = "",
) -> dict:
    event = {
        "schema": SCHEMA,
        "stage": stage,
        "unit": unit,
        "role": role,
        "status": status,
        "wall_minutes": None if wall_minutes is None else round(float(wall_minutes), 4),
        "scope": scope,
        "source": source,
        "excludes": list(excludes or []),
        "includes": list(includes or []),
        "provenance": provenance or {},
        "hardware": hardware or {},
        "recorded_at": recorded_at or _utc_now(),
        "notes": notes,
    }
    event["event_id"] = event_id(event)
    return event


def append_events(path: Path, events: list[dict]) -> int:
    """Append events whose ids are not already in ``path``. Returns the count added."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if path.exists():
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                seen.add(json.loads(line)["event_id"])
            except (json.JSONDecodeError, KeyError):
                continue
    added = 0
    with path.open("a", encoding="utf-8") as handle:
        for event in events:
            eid = event.get("event_id") or event_id(event)
            event["event_id"] = eid
            if eid in seen:
                continue
            handle.write(json.dumps(event, sort_keys=True) + "\n")
            seen.add(eid)
            added += 1
    return added


def try_record(event: dict, path: Path | None = None) -> bool:
    """Append one event. A write failure is printed and does not propagate."""
    try:
        append_events(path or ledger_path(), [event])
        return True
    except Exception as exc:  # noqa: BLE001 — ledger must not fail the job
        print(f"compute ledger append failed: {type(exc).__name__}: {exc}")
        return False


def hardware_snapshot() -> dict:
    """GPU name and VRAM if CUDA is importable. Empty fields if it is not."""
    out = {"gpu": None, "vram_total_gib": None, "vram_free_gib": None,
           "precision": "nf4-fp16"}
    try:
        import torch  # type: ignore[import-not-found]
        if torch.cuda.is_available():
            free, total = torch.cuda.mem_get_info()
            out["gpu"] = torch.cuda.get_device_name(0)
            out["vram_total_gib"] = round(total / 1024**3, 2)
            out["vram_free_gib"] = round(free / 1024**3, 2)
    except Exception:  # noqa: BLE001 — snapshot is optional provenance
        pass
    return out


def train_event_from_record(record: dict, source: str, recorded_at: str | None = None) -> dict:
    return make_event(
        stage="train",
        unit=str(record["country"]),
        wall_minutes=record.get("train_minutes"),
        scope="trainer.train",
        source=source,
        role="surviving_artifact",
        excludes=["model_load", "model_download", "adapter_save", "hub_upload", "session_idle"],
        provenance={
            "bank_run_id": record.get("bank_run_id"),
            "model_name": record.get("model_name"),
            "n_train": record.get("n_train"),
            "epochs": record.get("epochs"),
        },
        hardware={
            "gpu": record.get("gpu_name"),
            "vram_total_gib": record.get("vram_total_gib"),
            "precision": "nf4-fp16",
        },
        recorded_at=recorded_at,
        notes="Optimizer wall clock stored on the adapter. Load and upload are outside it.",
    )


def ref_event_from_manifest(manifest: dict, source: str, recorded_at: str | None = None) -> dict:
    return make_event(
        stage="ref_cache",
        unit="shared",
        wall_minutes=manifest.get("elapsed_min"),
        scope="forward_passes_after_model_load",
        source=source,
        role="surviving_artifact",
        excludes=["model_download", "model_load"],
        includes=[f"{manifest.get('n_pairs_computed_this_run')} pairs this run",
                  f"{manifest.get('n_pairs_total')} pairs in the completed cache"],
        provenance={
            "bank_run_id": manifest.get("bank_run_id"),
            "model_name": manifest.get("model_name"),
            "n_pairs_computed_this_run": manifest.get("n_pairs_computed_this_run"),
            "n_pairs_total": manifest.get("n_pairs_total"),
        },
        recorded_at=recorded_at,
    )


def same_printed_run(printed_minutes: float, stored_minutes: float) -> bool:
    return abs(float(printed_minutes) - float(stored_minutes)) <= PRINT_MATCH_TOLERANCE_MIN


def parse_training_log(text: str) -> dict:
    """Saved-adapter lines, cohort elapsed lines, and headers with no save."""
    headers = [(m.start(), m.group(1)) for m in _HEADER.finditer(text)]
    saves = [(m.start(), m.group(1), float(m.group(2))) for m in _SAVED.finditer(text)]
    incomplete = []
    for i, (pos, country) in enumerate(headers):
        end = headers[i + 1][0] if i + 1 < len(headers) else len(text)
        if not any(pos < sp < end and sc == country for sp, sc, _ in saves):
            incomplete.append(country)
    vram = _VRAM.search(text)
    return {
        "saved": [{"country": c, "train_minutes_printed": m} for _, c, m in saves],
        "cohort_elapsed": [
            {"n_reported_done": int(n), "elapsed_minutes": float(m)}
            for n, m in _ELAPSED.findall(text)
        ],
        "incomplete_starts": incomplete,
        "vram_total_gib": float(vram.group(2)) if vram else None,
    }


def classify_saves(saves: list[dict], final_minutes: dict[str, float]) -> dict:
    """Split log lines into the surviving run versus earlier runs of the same country."""
    surviving, superseded = [], []
    for row in saves:
        stored = final_minutes.get(row["country"])
        item = dict(row)
        item["hub_train_minutes"] = stored
        if stored is not None and same_printed_run(row["train_minutes_printed"], stored):
            surviving.append(item)
        else:
            superseded.append(item)
    return {"surviving": surviving, "superseded": superseded}


def score_upload_span(commits: list[dict], title_prefix: str) -> dict | None:
    """Wall span of Hub commits whose titles start with ``title_prefix``.

    Commit time is when the file landed, so the span includes scoring and
    upload after the first matching commit. It excludes work before that commit.
    """
    rows = [c for c in commits if str(c.get("title", "")).startswith(title_prefix)]
    if len(rows) < 2:
        return None
    rows = sorted(rows, key=lambda r: r["created_at"])

    def parse(value: str) -> datetime:
        return datetime.fromisoformat(value)

    gaps = []
    for left, right in zip(rows, rows[1:]):
        gaps.append({
            "from": left["title"],
            "to": right["title"],
            "minutes": round(
                (parse(right["created_at"]) - parse(left["created_at"])).total_seconds() / 60,
                4,
            ),
        })
    span = round(sum(g["minutes"] for g in gaps), 4)
    ordered = sorted(g["minutes"] for g in gaps)
    mid = ordered[len(ordered) // 2]
    return {
        "n_commits": len(rows),
        "first": {"created_at": rows[0]["created_at"], "title": rows[0]["title"]},
        "last": {"created_at": rows[-1]["created_at"], "title": rows[-1]["title"]},
        "span_minutes": span,
        "median_gap_minutes": mid,
        "max_gap_minutes": max(ordered),
        "gaps": gaps,
    }


def _sum_minutes(rows: list[dict], key: str) -> float:
    return round(sum(float(r[key]) for r in rows), 4)


def publication_estimate(sources: dict, recorded_at: str) -> dict:
    """Build the citable estimate. Does not invent a billed total."""
    records = sources["train_records"]
    minutes = [float(r["train_minutes"]) for r in records]
    final = {r["country"]: float(r["train_minutes"]) for r in records}
    ref = sources["ref_manifest"]
    waves = []
    superseded_rows = []
    incomplete = []
    vram_totals = set()
    for wave in sources["wave_logs"]:
        parsed = wave["parsed"]
        if parsed.get("vram_total_gib") is not None:
            vram_totals.add(parsed["vram_total_gib"])
        split = classify_saves(parsed["saved"], final)
        for row in split["superseded"]:
            superseded_rows.append({**row, "log": wave["source"]})
        for country in parsed["incomplete_starts"]:
            incomplete.append({"log": wave["source"], "country": country})
        printed = _sum_minutes(parsed["saved"], "train_minutes_printed")
        for elapsed in parsed["cohort_elapsed"]:
            waves.append({
                "source": wave["source"],
                "elapsed_minutes": elapsed["elapsed_minutes"],
                "printed_train_minutes": printed,
                "n_saved": len(parsed["saved"]),
                "n_reported_done": elapsed["n_reported_done"],
                "loop_overhead_minutes": round(elapsed["elapsed_minutes"] - printed, 4),
                "scope": "run_cohort training-loop wall clock",
                "includes": ["model_load", "trainer.train", "adapter_save", "skipped countries in the same process"],
                "excludes": ["vm_provision", "session_idle_after_the_loop", "hub_upload"],
            })
    span = score_upload_span(sources["score_commits"], sources["score_title_prefix"])
    train_sum = round(sum(minutes), 4)
    return {
        "schema": ESTIMATE_SCHEMA,
        "recorded_at": recorded_at,
        "do_not_cite_as_invoice": True,
        "hardware": {
            "training_vram_total_gib_printed": sorted(vram_totals),
            "training_gpu_name_printed_in_wave_logs": None,
            "scoring_gpu_printed": sources.get("scoring_gpu_printed"),
            "scoring_gpu_source": sources.get("scoring_gpu_source"),
            "precision": "4-bit NF4, fp16 compute, double quantization",
            "provider": "Google Colab Pro",
            "plan_rate_note": (
                "T4 is about 1 compute unit per hour on the Colab Pro plan. "
                "That rate is a planning convention. It is not an invoice."
            ),
        },
        "measured": {
            "surviving_train": {
                "n": len(minutes),
                "wall_minutes": train_sum,
                "gpu_hours": round(train_sum / 60, 4),
                "mean_minutes": round(train_sum / len(minutes), 4) if minutes else None,
                "min_minutes": min(minutes) if minutes else None,
                "max_minutes": max(minutes) if minutes else None,
                "scope": "trainer.train",
                "source": "adapter run_record.json train_minutes",
                "bank_run_id": sorted({r.get("bank_run_id") for r in records}),
                "model_name": sorted({r.get("model_name") for r in records}),
                "excludes": ["model_load", "model_download", "adapter_save", "hub_upload", "session_idle"],
            },
            "ref_cache": {
                "wall_minutes": ref.get("elapsed_min"),
                "n_pairs_computed_this_run": ref.get("n_pairs_computed_this_run"),
                "n_pairs_total": ref.get("n_pairs_total"),
                "scope": "forward_passes_after_model_load",
                "source": "shared_reference_logps_manifest.json",
                "excludes": ["model_download", "model_load"],
            },
            "training_loop_wall": waves,
            "score_upload_span": None if span is None else {
                "run_id": sources["score_title_prefix"].split(":")[0],
                "n_commits": span["n_commits"],
                "first": span["first"],
                "last": span["last"],
                "span_minutes": span["span_minutes"],
                "median_gap_minutes": span["median_gap_minutes"],
                "max_gap_minutes": span["max_gap_minutes"],
                "scope": "hub commit times from the first score upload to the last",
                "includes": [
                    "China same-weights gate in the gap between the base upload and the CHN upload",
                    "per-country score and upload after CHN",
                ],
                "excludes": [
                    "model load before the base upload",
                    "base scoring before the base upload",
                    "session idle after the last upload",
                ],
            },
        },
        "discarded_or_incomplete": {
            "superseded_optimizer_minutes_observed": _sum_minutes(
                superseded_rows, "train_minutes_printed"),
            "n_superseded_saves": len(superseded_rows),
            "superseded_saves": superseded_rows,
            "incomplete_starts": incomplete,
            "incomplete_duration": "not assigned",
            "note": (
                "Superseded lines are saved-adapter prints that do not match the "
                "surviving run_record within the 1-decimal print tolerance. "
                "This is a lower bound from the harvested logs. A later retrain "
                "whose only surviving clock is the run_record is already in the "
                "surviving total."
            ),
        },
        "unknown": [
            "Billed Colab units. colab usage reports a remaining balance, not consumption.",
            "Session idle, model downloads, and VM reclamations.",
            "Base scoring and model load before the first score upload.",
            "Duration of any training header that has no saved-adapter line.",
            "Pilot load and upload overhead beyond trainer.train.",
        ],
        "balance_snapshot": sources.get("balance_snapshot"),
        "replication_demand": {
            "clean_rerun_keeps": [
                "ref_cache forward-pass clock",
                "surviving trainer.train clock, once per adapter",
                "one score pass on a warm T4 after the base file, plus the China gate",
            ],
            "clean_rerun_drops": ["superseded retrains", "truncated attempts"],
            "do_not_sum_clocks": True,
            "why": (
                "The optimizer clock, the reference-cache clock, the training-loop "
                "wall clock, and the score-upload span cover different work. "
                "Adding them would mix those scopes and still omit idle time."
            ),
        },
    }


def events_from_sources(sources: dict, recorded_at: str) -> list[dict]:
    events = [
        train_event_from_record(r, source="run_record.json", recorded_at=recorded_at)
        for r in sources["train_records"]
    ]
    events.append(ref_event_from_manifest(
        sources["ref_manifest"], source="shared_reference_logps_manifest.json",
        recorded_at=recorded_at))
    final = {r["country"]: float(r["train_minutes"]) for r in sources["train_records"]}
    for wave in sources["wave_logs"]:
        parsed = wave["parsed"]
        split = classify_saves(parsed["saved"], final)
        for row in split["superseded"]:
            events.append(make_event(
                stage="train",
                unit=row["country"],
                wall_minutes=row["train_minutes_printed"],
                scope="trainer.train",
                source=wave["source"],
                role="superseded",
                excludes=["model_load", "hub_upload", "session_idle"],
                recorded_at=recorded_at,
                notes="Printed save line does not match the surviving run_record.",
            ))
        for elapsed in parsed["cohort_elapsed"]:
            events.append(make_event(
                stage="train_loop",
                unit=wave["source"],
                wall_minutes=elapsed["elapsed_minutes"],
                scope="run_cohort training-loop wall clock",
                source=wave["source"],
                role="session_loop",
                includes=["model_load", "trainer.train", "adapter_save"],
                excludes=["vm_provision", "session_idle_after_the_loop", "hub_upload"],
                recorded_at=recorded_at,
            ))
        for country in parsed["incomplete_starts"]:
            events.append(make_event(
                stage="train",
                unit=country,
                wall_minutes=None,
                scope="trainer.train",
                source=wave["source"],
                status="unknown",
                role="incomplete",
                recorded_at=recorded_at,
                notes="Header with no saved-adapter line. Duration not assigned.",
            ))
    span = score_upload_span(sources["score_commits"], sources["score_title_prefix"])
    if span is not None:
        events.append(make_event(
            stage="score",
            unit=sources["score_title_prefix"].split(":")[0],
            wall_minutes=span["span_minutes"],
            scope="hub commit span from first score upload to last",
            source="huggingface hub commit times",
            role="upload_span",
            includes=["score_and_upload after the first score commit", "china gate between base and CHN"],
            excludes=["model_load", "base scoring before the base upload", "session idle after the last upload"],
            recorded_at=recorded_at,
        ))
    return events


def load_sources(directory: Path) -> dict:
    directory = Path(directory)
    wave_dir = directory / "wave_logs"
    waves = []
    for path in sorted(wave_dir.glob("*.log")):
        waves.append({"source": path.name, "parsed": parse_training_log(path.read_text(errors="replace"))})
    meta = json.loads((directory / "harvest_meta.json").read_text())
    return {
        "train_records": json.loads((directory / "train_records.json").read_text()),
        "ref_manifest": json.loads((directory / "ref_manifest.json").read_text()),
        "score_commits": json.loads((directory / "score_commits.json").read_text()),
        "score_title_prefix": meta["score_title_prefix"],
        "scoring_gpu_printed": meta.get("scoring_gpu_printed"),
        "scoring_gpu_source": meta.get("scoring_gpu_source"),
        "balance_snapshot": json.loads((directory / "balance_snapshot.json").read_text()),
        "wave_logs": waves,
        "recorded_at": meta["recorded_at"],
    }


def publish(sources_dir: Path, out_dir: Path) -> dict:
    sources = load_sources(sources_dir)
    recorded_at = sources["recorded_at"]
    estimate = publication_estimate(sources, recorded_at)
    events = events_from_sources(sources, recorded_at)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger = out_dir / "ledger.jsonl"
    if ledger.exists():
        ledger.unlink()
    append_events(ledger, events)
    (out_dir / "publication_estimate.json").write_text(
        json.dumps(estimate, indent=2) + "\n")
    return estimate


def try_upload_ledger(repo: str, run_id: str, path: Path | None = None) -> bool:
    """Best-effort Hub upload of the live ledger. Never raises."""
    try:
        from huggingface_hub import HfApi
        ledger = path or ledger_path()
        if not ledger.exists():
            return False
        HfApi().upload_file(
            path_or_fileobj=str(ledger),
            path_in_repo=f"runs/{run_id}/compute/ledger.jsonl",
            repo_id=repo,
            repo_type="dataset",
            commit_message=f"{run_id}: compute ledger",
        )
        print(f"compute ledger uploaded -> {repo}/runs/{run_id}/compute/ledger.jsonl")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"compute ledger upload failed: {type(exc).__name__}: {exc}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Rebuild the Paper B compute snapshot")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pub = sub.add_parser("publish", help="write ledger.jsonl and publication_estimate.json")
    pub.add_argument("--sources", type=Path, required=True)
    pub.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.cmd == "publish":
        estimate = publish(args.sources, args.out)
        train = estimate["measured"]["surviving_train"]
        print(
            f"surviving train {train['wall_minutes']} min "
            f"({train['n']} adapters) | "
            f"ref cache {estimate['measured']['ref_cache']['wall_minutes']} min | "
            f"superseded saves {estimate['discarded_or_incomplete']['n_superseded_saves']}"
        )
        print(f"wrote {args.out}/ledger.jsonl and publication_estimate.json")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
