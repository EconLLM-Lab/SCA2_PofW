"""Forward pass on the local 658-scenario country banks.

The banks stay in synthetic_generation/. This test does not copy them.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sca2_workbench.bank import first_record, prompt_sha256
from sca2_workbench.forward import run_prompt

ROOT = Path(__file__).resolve().parents[2]
BANK = ROOT / "synthetic_generation" / "outputs" / "gps_sign_relabel_all"
COUNTRIES = (
    "ARG", "BRA", "CHN", "DEU", "EGY", "GBR", "GRC", "IDN",
    "IND", "JPN", "MEX", "NGA", "NLD", "RUS", "TUR", "USA",
)
REPORT = Path(__file__).resolve().parents[1] / "runs" / "slice2_forward.json"


def test_local_banks_exist_and_hold_658_rows():
    for iso in COUNTRIES:
        path = BANK / f"D_syn_{iso}.jsonl"
        assert path.is_file(), path
        count = sum(1 for _ in path.open(encoding="utf-8"))
        assert count == 658, (iso, count)


def test_forward_pass_conserves_on_local_prompts():
    rows = []
    for iso in COUNTRIES:
        path = BANK / f"D_syn_{iso}.jsonl"
        record = first_record(path)
        text = record["prompt"] + "\n" + record["chosen"]
        result = run_prompt(text)
        assert result["residual_inf_norm"] < 1e-3
        assert result["dla_abs_gap"] < 1e-2
        assert result["clamped_quadrant_iii_max_abs"] == pytest.approx(0.0)
        assert result["not_llama"] is True
        rows.append(
            {
                "country": iso,
                "source": str(path.relative_to(ROOT)),
                "triplet_id": record["triplet_id"],
                "prompt_sha256": prompt_sha256(record["prompt"]),
                "chosen_sha256": prompt_sha256(record["chosen"]),
                "prompt_chars": len(record["prompt"]),
                "chosen_chars": len(record["chosen"]),
                **result,
            }
        )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({"rows": rows}, indent=2) + "\n", encoding="utf-8")
    assert REPORT.is_file()
