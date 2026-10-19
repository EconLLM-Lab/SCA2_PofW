"""Tests for the anonymized copy of the preregistration."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import anonymize_prereg as AP  # noqa: E402

SOURCE = (AP.REPO / "paper_b/heldout/PREREGISTRATION.md").read_text()


def test_no_identifying_token_survives():
    out = AP.anonymize(SOURCE)
    low = out.lower()
    for tok in AP.FORBIDDEN:
        assert tok.lower() not in low, tok


def test_only_redacted_spans_change():
    out = AP.anonymize(SOURCE)
    body = out.split(AP.HEADER_END, 1)[1].lstrip("\n")
    src_lines, out_lines = SOURCE.splitlines(), body.splitlines()
    assert len(src_lines) == len(out_lines)
    changed = [(a, b) for a, b in zip(src_lines, out_lines) if a != b]
    assert changed and all(any(old in a for old, _ in AP.REDACTIONS) for a, _ in changed)


def test_header_records_source_hash_and_every_redaction():
    out = AP.anonymize(SOURCE)
    head = out.split(AP.HEADER_END, 1)[0]
    assert AP.sha256(SOURCE) in head and "prereg-heldout-2026-10-14" in head
    for _, new in AP.REDACTIONS:
        assert new in head


def test_unknown_identifier_in_source_fails():
    try:
        AP.anonymize(SOURCE + "\nContact: someone at EconLLM Lab\n")
    except AssertionError:
        return
    raise AssertionError("expected the residual-token check to fire")
