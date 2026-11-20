"""Exact-match tests for the local tvd rebuild (paper_a/tvd_rebuild.py).

The public repo ships no tvd values. These tests pin the rebuilt column two ways:
  * against the committed frozen column (when present), to 1e-9;
  * against a sha256 of the frozen values, rounded to 10 decimals and serialised with repr() in sorted
    (arm, country, item) order, so the check works where the column has been removed.
The rebuild tests skip, with a reason, when the WVS parquet or GPS file is absent.
"""
from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "paper_a"))
import tvd_rebuild as T  # noqa: E402

_spec = importlib.util.spec_from_file_location("sca2_testing_helpers", ROOT / "paper_b" / "testing.py")
_testing = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_testing)

TVD_SHA256 = "56f784dcfb669e50a953297d5466d9885ab76170cea3a4e20645b76a5743764e"
MODEL_PROBS_SHA256 = "1b57a585c4e790689fceaadee651f2a5c2d79f1b4637b83ea39a18d903a3cd11"
KEY = ["arm", "country", "item"]


def pin_hash(df: pd.DataFrame) -> str:
    s = df.sort_values(KEY)["tvd"]
    return hashlib.sha256("\n".join(repr(round(float(x), 10)) for x in s).encode()).hexdigest()


def _frozen_with_tvd() -> pd.DataFrame:
    if not T.SCORES.exists():
        pytest.skip(f"frozen score file absent: {T.SCORES}")
    d = pd.read_csv(T.SCORES)
    if "tvd" not in d.columns:
        pytest.skip("frozen tvd column removed (public checkout); pinned-hash test covers the rebuild")
    return d[d.arm != "human"][KEY + ["tvd"]]


@pytest.fixture(scope="module")
def rebuilt() -> pd.DataFrame:
    _testing.requires_local_data(T.WVS_DIR, T.GPS_DTA)
    return T.rebuild_tvd()


def test_model_probs_file_is_model_only():
    assert hashlib.sha256(T.MODEL_PROBS.read_bytes()).hexdigest() == MODEL_PROBS_SHA256
    cols = list(pd.read_csv(T.MODEL_PROBS, nrows=0).columns)
    assert cols == ["arm", "country", "question_id", "option_value", "model_prob"]


def test_rebuild_shape(rebuilt):
    assert len(rebuilt) == 3424
    assert rebuilt.groupby("arm").size().eq(428).all() and rebuilt.arm.nunique() == 8


def test_rebuild_matches_pinned_sha(rebuilt):
    assert pin_hash(rebuilt) == TVD_SHA256


def test_rebuild_matches_frozen_column(rebuilt):
    frozen = _frozen_with_tvd()
    m = frozen.merge(rebuilt, on=KEY, how="outer", suffixes=("_frozen", "_rebuilt"), indicator=True)
    assert len(frozen) == 3424 and (m["_merge"] == "both").all()
    assert np.abs(m.tvd_frozen - m.tvd_rebuilt).max() < 1e-9


def test_frozen_column_matches_pinned_sha():
    assert pin_hash(_frozen_with_tvd()) == TVD_SHA256


def test_headline_means_use_strict_items(rebuilt):
    got = T.headline_means(rebuilt)
    assert len(T.strict_items()) == 23
    want = {"adapter": 0.4873, "base": 0.4622, "persona": 0.3695, "adapter_persona": 0.3963}
    assert {k: round(v, 4) for k, v in got.items()} == want


def test_load_tvd_fails_clearly_when_absent(tmp_path):
    scores = tmp_path / "scores.csv"
    pd.DataFrame({"arm": ["adapter"], "country": ["USA"], "item": ["Q43"]}).to_csv(scores, index=False)
    with pytest.raises(SystemExit, match="DATA.md"):
        T.load_tvd(scores, tmp_path / "missing.csv")


def test_load_tvd_prefers_committed_column(tmp_path):
    scores = tmp_path / "scores.csv"
    pd.DataFrame({"arm": ["adapter"], "country": ["USA"], "item": ["Q43"], "tvd": [0.25]}).to_csv(scores, index=False)
    rebuilt_file = tmp_path / "r.csv"
    pd.DataFrame({"arm": ["adapter"], "country": ["USA"], "item": ["Q43"], "tvd": [0.5]}).to_csv(rebuilt_file, index=False)
    assert T.load_tvd(scores, rebuilt_file).tvd.iloc[0] == 0.25
    pd.DataFrame({"arm": ["adapter"], "country": ["USA"], "item": ["Q43"]}).to_csv(scores, index=False)
    assert T.load_tvd(scores, rebuilt_file).tvd.iloc[0] == 0.5
