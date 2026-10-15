"""Compute-ledger clocks stay scoped, and a republish does not duplicate rows."""
from __future__ import annotations

import json
from pathlib import Path

import compute_ledger as L


def test_print_tolerance_separates_rounding_from_a_retrain():
    assert L.same_printed_run(16.6, 16.64)
    assert L.same_printed_run(18.4, 18.38)
    assert not L.same_printed_run(18.4, 16.64)
    assert not L.same_printed_run(16.6, 17.2)


def test_incomplete_header_has_no_duration():
    text = """
===== GBR ===== VRAM free 14.46/14.56 GiB
saved adapter -> /content/drive/MyDrive/SCA2_paper_b/adapters/GBR in 16.6 min
===== IRN ===== VRAM free 8.87/14.56 GiB
  81%|████████▏ | 26/32 [13:28<03:07, 31.31s/it]
"""
    parsed = L.parse_training_log(text)
    assert parsed["incomplete_starts"] == ["IRN"]
    assert parsed["saved"] == [{"country": "GBR", "train_minutes_printed": 16.6}]
    assert parsed["vram_total_gib"] == 14.56


def test_superseded_lines_are_not_folded_into_the_surviving_sum():
    saves = [
        {"country": "GBR", "train_minutes_printed": 18.4},
        {"country": "GBR", "train_minutes_printed": 16.6},
    ]
    split = L.classify_saves(saves, {"GBR": 16.64})
    assert [r["train_minutes_printed"] for r in split["surviving"]] == [16.6]
    assert [r["train_minutes_printed"] for r in split["superseded"]] == [18.4]


def test_score_span_is_the_commit_gap_sum():
    commits = [
        {"created_at": "2026-10-12T04:19:56+00:00", "title": "paper-b-20261011: base"},
        {"created_at": "2026-10-12T04:20:56+00:00", "title": "paper-b-20261011: CHN_adapter"},
        {"created_at": "2026-10-12T04:21:51+00:00", "title": "other run: ignore"},
    ]
    span = L.score_upload_span(commits, "paper-b-20261011")
    assert span is not None
    assert span["n_commits"] == 2
    assert span["span_minutes"] == 1.0
    assert span["gaps"][0]["minutes"] == 1.0


def test_append_is_idempotent(tmp_path):
    path = tmp_path / "ledger.jsonl"
    event = L.train_event_from_record(
        {"country": "ARG", "train_minutes": 18.38, "bank_run_id": "bank",
         "model_name": "meta-llama/Llama-3.1-8B-Instruct", "n_train": 526, "epochs": 1},
        source="run_record.json", recorded_at="2026-10-12T00:00:00+00:00")
    assert L.append_events(path, [event]) == 1
    assert L.append_events(path, [event]) == 0
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["scope"] == "trainer.train"
    assert "model_load" in rows[0]["excludes"]
    assert "session_idle" in rows[0]["excludes"]


def test_estimate_does_not_invent_a_billed_total():
    sources = {
        "train_records": [
            {"country": "ARG", "train_minutes": 18.38, "bank_run_id": "bank",
             "model_name": "meta-llama/Llama-3.1-8B-Instruct"},
            {"country": "GBR", "train_minutes": 16.64, "bank_run_id": "bank",
             "model_name": "meta-llama/Llama-3.1-8B-Instruct"},
        ],
        "ref_manifest": {"elapsed_min": 7.86, "n_pairs_computed_this_run": 1052,
                         "n_pairs_total": 1052},
        "wave_logs": [{
            "source": "wave1.log",
            "parsed": L.parse_training_log(
                "===== GBR ===== VRAM free 3.15/14.56 GiB\n"
                "saved adapter -> /x/GBR in 18.4 min\n"
                "cohort done: 1 adapters | elapsed 20.0 min\n"
                "===== IRN ===== VRAM free 8.87/14.56 GiB\n"),
        }],
        "score_commits": [
            {"created_at": "2026-10-12T04:19:56+00:00",
             "title": "paper-b-20261011: base option probabilities"},
            {"created_at": "2026-10-12T04:22:53+00:00",
             "title": "paper-b-20261011: CHN_adapter option probabilities"},
        ],
        "score_title_prefix": "paper-b-20261011",
        "scoring_gpu_printed": "Tesla T4",
        "scoring_gpu_source": "stack freeze",
        "balance_snapshot": {"compute_units_remaining": 273.63, "not_consumption": True},
    }
    estimate = L.publication_estimate(sources, "2026-10-12T06:00:00+00:00")
    assert estimate["do_not_cite_as_invoice"] is True
    assert "total_gpu_hours" not in estimate
    assert "billed_compute_units" not in estimate
    assert estimate["measured"]["surviving_train"]["wall_minutes"] == 35.02
    assert estimate["discarded_or_incomplete"]["superseded_optimizer_minutes_observed"] == 18.4
    assert estimate["discarded_or_incomplete"]["incomplete_starts"] == [
        {"log": "wave1.log", "country": "IRN"}]
    assert estimate["discarded_or_incomplete"]["incomplete_duration"] == "not assigned"
    assert estimate["measured"]["score_upload_span"]["span_minutes"] == 2.95
    assert estimate["replication_demand"]["do_not_sum_clocks"] is True
    blob = json.dumps(estimate)
    assert "273.63" in blob
    assert "invoice" in blob
