"""Bank-similarity audit tests (text only)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bank_similarity as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BANK1 = ROOT / "synthetic_generation/outputs/gps_sign_relabel_all/triplets_bank.jsonl"


def _row(dim, p, a="yes I will do it now", b="no I will not do it"):
    return {"gps_dimension": dim, "prompt": p, "response_a": a, "response_b": b}


def test_a_bank_is_similar_to_itself():
    b1 = S.load(BANK1)
    res = S.audit(b1[:300], b1[300:])
    assert res["verdict"] == "similar", res["flags"]


def test_ks_detects_a_shift_and_not_an_identity():
    assert S.ks([1, 2, 3, 4, 5] * 20, [1, 2, 3, 4, 5] * 20)[1] > 0.99
    assert S.ks(list(range(100)), list(range(60, 160)))[1] < 1e-6


def test_flags_fire_on_skewed_counts_and_long_prompts():
    base = [_row(d, f"scenario {d} number {i} about a choice with a friend and a cost")
            for d in S.DIMS for i in range(20)]
    skew = [_row("trust", " ".join(["word"] * 60 + [str(i)])) for i in range(120)]
    flags = S.audit(base, skew)["flags"]
    assert "counts:trust" in flags and "lengths:prompt" in flags


def test_exact_copy_is_flagged_as_overlap():
    b1 = S.load(BANK1)[:100]
    assert "overlap" in S.audit(b1, b1)["flags"]
