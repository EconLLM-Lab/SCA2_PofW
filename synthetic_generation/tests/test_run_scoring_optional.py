"""Default path skips the Phi-4 scorer; --diagnostic-scorer opts in."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

import run
from sca2_datagen import generate, score
from sca2_datagen.config import CONFIG
from sca2_datagen.export import _qc_health_summary


def _raw_pairs(countries: list[str]) -> pd.DataFrame:
    rows = []
    for country in countries:
        rows.append(
            {
                "prompt": f"prompt-{country}",
                "facet": "facet",
                "gps_dimension": "trust",
                "country": country,
                "chosen": "chosen",
                "rejected": "rejected",
                "reasoning": "generation",
            }
        )
    return pd.DataFrame(rows)


def test_default_cli_does_not_call_scorer(tmp_path: Path, gps_path, monkeypatch) -> None:
    called = {"score": 0}

    async def fake_generate(cultural_profiles, countries, config=CONFIG, tracker=None, use_anchors=False):
        return _raw_pairs(list(countries)), {"trust": [{"facet": "facet", "prompt": "p"}]}

    async def fake_score(df_raw, cultural_profiles, config=CONFIG, tracker=None):
        called["score"] += 1
        raise AssertionError("scorer must not run on the default path")

    monkeypatch.setattr(generate, "run_teacher_pipeline", fake_generate)
    monkeypatch.setattr(score, "run_scoring_qc_export", fake_score)

    exit_code = run.main(
        [
            "--countries",
            "MEX",
            "USA",
            "--scenarios-per-dim",
            "1",
            "--sample-sizes",
            "1",
            "--gps-path",
            str(gps_path),
            "--output-dir",
            str(tmp_path / "outputs"),
        ]
    )
    assert exit_code == 0
    assert called["score"] == 0


def test_diagnostic_scorer_flag_calls_scorer(tmp_path: Path, gps_path, monkeypatch) -> None:
    called = {"score": 0}

    async def fake_generate(cultural_profiles, countries, config=CONFIG, tracker=None, use_anchors=False):
        return _raw_pairs(list(countries)), {"trust": [{"facet": "facet", "prompt": "p"}]}

    async def fake_score(df_raw, cultural_profiles, config=CONFIG, tracker=None):
        called["score"] += 1
        out = df_raw.copy()
        out["qc_status"] = "pass"
        return out, {"total": len(out), "score_fail": 0, "mono_fail": 0, "dist_fail": 0, "pass": len(out)}

    monkeypatch.setattr(generate, "run_teacher_pipeline", fake_generate)
    monkeypatch.setattr(score, "run_scoring_qc_export", fake_score)

    exit_code = run.main(
        [
            "--diagnostic-scorer",
            "--countries",
            "MEX",
            "--scenarios-per-dim",
            "1",
            "--sample-sizes",
            "1",
            "--gps-path",
            str(gps_path),
            "--output-dir",
            str(tmp_path / "outputs"),
        ]
    )
    assert exit_code == 0
    assert called["score"] == 1


def test_qc_health_summary_does_not_grade_contamination_bins() -> None:
    text = _qc_health_summary(
        qc_pass_rate=0.9,
        mono_fail_rate=0.0,
        dist_fail_rate=0.0,
        contamination_distribution={"high": {"share": 0.0}, "low": {"share": 1.0}},
    )
    assert "contamination" not in text.lower()
