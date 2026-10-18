"""Card T8 — the Tier-1 verification helper's logic: session clustering, pass dedupe, stage totals.

The helper (`paper_b/tier1_verification.py`) is what produces the numbers in
`planning/sprint_2026-10-11/paper-b-tier1/VERIFICATION.md` and the Tier-1 block of
`paper_b/compute/publication_estimate.json`, so the two things that can silently corrupt a
publication clock — a duplicated ledger copy and a duplicated session — are tested here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tier1_verification as TV  # noqa: E402


def _row(ts, stage, unit, minutes, run_id="r1", source="score_cohort.py", **extra):
    row = {
        "schema": "sca2.compute_event.v1", "stage": stage, "unit": unit, "role": "live",
        "status": "measured", "wall_minutes": minutes, "scope": "score_and_persist",
        "source": source, "provenance": {}, "recorded_at": ts,
    }
    if run_id:
        row["provenance"]["run_id"] = run_id
    row.update(extra)
    return row


# ------------------------------------------------------------------ sessions

def test_cluster_sessions_splits_on_the_gap_and_keeps_the_span():
    events = [
        _row("2026-10-17T05:18:07+00:00", "score", "a", 6.0),
        _row("2026-10-17T05:24:44+00:00", "score", "b", 6.0),
        _row("2026-10-17T20:29:07+00:00", "score", "c", 6.0),
    ]
    got = TV.cluster_sessions(events, gap_minutes=60)
    assert len(got) == 2
    assert got[0]["n_events"] == 2
    assert got[0]["units"] == ["a", "b"]
    assert got[0]["stages"] == ["score"]
    assert got[0]["span_minutes"] == pytest.approx(6.6166, abs=1e-3)
    assert got[1]["units"] == ["c"]
    assert got[1]["span_minutes"] == 0.0


def test_cluster_sessions_keeps_a_gap_exactly_at_the_threshold():
    events = [
        _row("2026-10-17T05:00:00+00:00", "score", "a", 1.0),
        _row("2026-10-17T06:00:00+00:00", "score", "b", 1.0),
        _row("2026-10-17T07:00:01+00:00", "score", "c", 1.0),
    ]
    got = TV.cluster_sessions(events, gap_minutes=60)
    assert [s["n_events"] for s in got] == [2, 1]


# ------------------------------------------------------------------ dedupe

def test_dedupe_copies_collapses_the_accumulated_ledger_copies():
    """A run's Hub ledger holds the whole session's events, so the same row lands in several run dirs."""
    a = _row("2026-10-17T05:18:07+00:00", "score", "a", 6.496, run_id="v1")
    dup = dict(a, provenance=dict(a["provenance"]))
    other = _row("2026-10-17T10:29:44+00:00", "score", "a", 6.351, run_id="reverse")
    kept, dropped = TV.dedupe_copies([a, dup, other])
    assert len(kept) == 2
    assert dropped == 1
    assert {r["provenance"]["run_id"] for r in kept} == {"v1", "reverse"}


def test_dedupe_copies_keeps_a_real_retrain_that_shares_a_unit_name():
    """P_1_0_1_1_0_1 was trained in the drive session and refit as replicate r1: two clocks, not one."""
    first = _row("2026-10-15T07:37:30+00:00", "train", "P_1_0_1_1_0_1", 15.0, run_id="",
                 source="train_country.py")
    again = _row("2026-10-16T12:16:13+00:00", "train", "P_1_0_1_1_0_1", 17.24, run_id="",
                 source="train_country.py")
    kept, dropped = TV.dedupe_copies([first, again])
    assert dropped == 0
    assert len(kept) == 2
    assert TV.repeat_unit_keys(kept) == [("train_country.py", "train", "P_1_0_1_1_0_1")]


# ------------------------------------------------------------------ run records

def test_tier1_adapter_path_keeps_only_bank2_records():
    assert TV.is_tier1_adapter_path(f"bank2/{TV.BANK_RUN_ID}/profiles/P_0_0_0_0_0_0/run_record.json")
    assert TV.is_tier1_adapter_path(f"bank2/{TV.BANK_RUN_ID}/near_zero/GBR/run_record.json")
    assert TV.is_tier1_adapter_path(f"bank2/{TV.BANK_RUN_ID}/replicates/r1/profiles/P_1_0_1_1_0_1/run_record.json")
    assert not TV.is_tier1_adapter_path("adapters/ARG/run_record.json")
    assert not TV.is_tier1_adapter_path(f"bank2/{TV.BANK_RUN_ID}/../marker.json")


# ------------------------------------------------------------------ totals

def test_tier1_block_reports_totals_by_stage():
    train = [TV._train_event({"country": "P_0_0_0_0_0_0", "train_minutes": 10.0,
                              "bank_run_id": TV.BANK_RUN_ID, "n_train": 526, "epochs": 1},
                             "hub:profiles/P_0_0_0_0_0_0"),
             TV._train_event({"country": "GBR", "train_minutes": 20.0,
                              "bank_run_id": TV.BANK_RUN_ID, "n_train": 164, "epochs": 1},
                             "hub:near_zero/GBR")]
    score = [TV._score_event(_row("2026-10-17T05:18:07+00:00", "score", "a_adapter", 6.0, run_id="v1")),
             TV._score_event(_row("2026-10-17T05:24:44+00:00", "score", "b_adapter", 4.0, run_id="v1"))]
    sessions = TV.session_events(TV.cluster_sessions(train + score, 60))
    block = TV.tier1_block(train_events=train, score_events=score, session_events=sessions,
                           ref_event=None, endpoints={"total_cost_usd": 13.99},
                           recorded_at="2026-10-18T00:00:00+00:00")
    assert block["stage_totals"]["training"]["n"] == 2
    assert block["stage_totals"]["training"]["wall_minutes"] == 30.0
    assert block["stage_totals"]["scoring"]["n"] == 2
    assert block["stage_totals"]["scoring"]["wall_minutes"] == 10.0
    assert block["measured"]["gpu_sessions"][0]["n_events"] == 4
    assert [s["stage"] for s in block["measured"]["gpu_sessions"]] == ["gpu_session"]
    assert block["bank_run_id"] == TV.BANK_RUN_ID


# ------------------------------------------------------------------ writing

def test_append_ledger_is_idempotent_and_keeps_existing_rows(tmp_path):
    path = tmp_path / "ledger.jsonl"
    old = {"schema": "sca2.compute_event.v1", "stage": "train", "unit": "ARG", "role": "surviving_artifact",
           "status": "measured", "wall_minutes": 18.38, "scope": "trainer.train",
           "source": "run_record.json", "provenance": {}, "recorded_at": "2026-10-12T06:53:19+00:00",
           "event_id": "cohort1"}
    path.write_text(json.dumps(old, sort_keys=True) + "\n")
    event = TV._score_event(_row("2026-10-17T05:18:07+00:00", "score", "a_adapter", 6.0, run_id="v1"))
    assert TV.append_ledger(path, [event]) == 1
    assert TV.append_ledger(path, [event]) == 0
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert [r["event_id"] for r in rows] == ["cohort1", event["event_id"]]


def test_update_estimate_keeps_the_cohort1_estimate(tmp_path):
    path = tmp_path / "publication_estimate.json"
    path.write_text(json.dumps({"schema": "sca2.compute_estimate.v1", "do_not_cite_as_invoice": True,
                                "measured": {"surviving_train": {"wall_minutes": 767.68}}}))
    TV.update_estimate(path, {"schema": "sca2.compute_tier1.v1", "stage_totals": {}})
    got = json.loads(path.read_text())
    assert got["measured"]["surviving_train"]["wall_minutes"] == 767.68
    assert got["tier1_bank2"]["schema"] == "sca2.compute_tier1.v1"
    assert got["do_not_cite_as_invoice"] is True


# ------------------------------------------------------------------ pinned facts

def test_repo_rebuilds_every_pinned_spec_hash():
    """The VM refuses to load a model unless build_spec reproduces the pin; this is that check at HEAD."""
    assert TV.spec_pin_mismatches() == []


def test_frozen_input_hashes_match_the_freeze_record():
    got = TV.frozen_input_hashes()
    assert got["selection_sha256_match"] is True
    assert got["pool_sha256_match"] is True
    assert len(got["freeze_sha256"]) == 64
    assert got["selected_items"] == 56
