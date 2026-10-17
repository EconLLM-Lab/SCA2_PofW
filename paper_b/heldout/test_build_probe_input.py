"""The probe input table: every item scored by all 64 units on one option grid, or it raises."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import build_probe_input as B  # noqa: E402
import factorial as F  # noqa: E402


def _frame(item="Q150", codes=("1", "2", "3"), probs=(0.2, 0.3, 0.5)):
    return pd.DataFrame({"question_id": [item] * len(codes), "option_code": list(codes),
                         "model_prob": list(probs)})


def _scores(items=("Q150",), probs=(0.2, 0.3, 0.5)):
    return {u: pd.concat([_frame(i, probs=probs) for i in items], ignore_index=True) for u in F.all_units()}


def test_expected_code_is_the_probability_weighted_code():
    assert B.expected_code(_frame(), "Q150") == pytest.approx(0.2 * 1 + 0.3 * 2 + 0.5 * 3)


def test_values_cover_64_units_for_every_item():
    v = B.probe_values(_scores(items=("Q150", "Q151")), ["Q150", "Q151"])
    assert len(v) == 128 and set(v.unit) == set(F.all_units())
    assert v.groupby("item").size().tolist() == [64, 64]


def test_a_missing_unit_is_refused_not_filled():
    s = _scores()
    del s[F.all_units()[0]]
    with pytest.raises(ValueError, match="units have no scores"):
        B.probe_values(s, ["Q150"])


def test_an_unscored_item_is_refused():
    s = _scores(items=("Q150",))
    with pytest.raises(ValueError, match="not scored by"):
        B.probe_values(s, ["Q150", "Q999"])


def test_option_grids_must_agree_across_units():
    s = _scores()
    s[F.all_units()[7]] = _frame(codes=("1", "2", "3", "4"), probs=(0.1, 0.2, 0.3, 0.4))
    with pytest.raises(ValueError, match="option grids differ"):
        B.probe_values(s, ["Q150"])


def test_probabilities_must_sum_to_one_and_be_finite():
    with pytest.raises(ValueError, match="sums to"):
        B.expected_code(_frame(probs=(0.2, 0.3, 0.3)), "Q150")
    with pytest.raises(ValueError, match="finite"):
        B.expected_code(_frame(probs=(0.2, 0.3, np.nan)), "Q150")
    with pytest.raises(ValueError, match="non-negative"):
        B.expected_code(_frame(probs=(1.2, -0.1, -0.1)), "Q150")


def test_duplicate_option_codes_are_refused():
    with pytest.raises(ValueError, match="duplicate option codes"):
        B.expected_code(_frame(codes=("1", "1", "3"), probs=(0.2, 0.3, 0.5)), "Q150")


def test_loader_skips_units_that_have_not_landed_yet(tmp_path):
    (tmp_path / f"{F.all_units()[0]}_adapter_option_probabilities.csv").write_text(_frame().to_csv(index=False))
    got = B.load_run_dir(tmp_path)
    assert list(got) == [F.all_units()[0]]


def test_a_unit_whose_manifest_records_another_spec_is_excluded(tmp_path):
    """The amended pass reuses the superseded pass's paths, so a file count cannot tell them apart.
    Only the manifest's spec_sha256 can, and the probe must honour it."""
    units = F.all_units()[:3]
    present = {f"runs/R/synthetic/{u}_adapter_option_probabilities.csv" for u in units}
    manifests = {units[0]: {"spec_sha256": "new"}, units[1]: {"spec_sha256": "old"}, units[2]: {}}
    got = B.spec_verified_units(units, "R", present, "new", lambda rid, m: manifests.get(m.replace("_adapter", ""), {}))
    assert got == [units[0]], "units with a stale or missing manifest must not enter the probe"


def test_spec_check_without_a_reader_is_a_programming_error():
    with pytest.raises(ValueError, match="manifest reader"):
        B.spec_verified_units(F.all_units()[:1], "R", set(), "new", None)
