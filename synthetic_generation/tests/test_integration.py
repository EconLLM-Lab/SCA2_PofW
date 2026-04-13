from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import run
from sca2_datagen import generate, score
from sca2_datagen.config import CONFIG


def test_estimate_only_runs(caplog, gps_path) -> None:
    exit_code = run.main(
        [
            "--estimate-only",
            "--countries",
            "MEX",
            "USA",
            "--scenarios-per-dim",
            "20",
            "--sample-sizes",
            "10,20",
            "--gps-path",
            str(gps_path),
        ]
    )
    assert exit_code == 0


def test_cli_sample_sizes_exports_without_real_api_calls(tmp_path: Path, gps_path, monkeypatch) -> None:
    async def fake_run_teacher_pipeline(cultural_profiles, countries, config=CONFIG, tracker=None):
        import pandas as pd

        rows = []
        for country in countries:
            for index in range(3):
                rows.append(
                    {
                        "prompt": f"prompt-{country}-{index}",
                        "facet": "facet",
                        "gps_dimension": "trust",
                        "country": country,
                        "chosen": "chosen",
                        "rejected": "rejected",
                        "reasoning": "generation",
                    }
                )
        return pd.DataFrame(rows), {"trust": [{"facet": "facet", "prompt": "p"}]}

    async def fake_run_scoring_qc_export(df_raw, cultural_profiles, config=CONFIG, tracker=None):
        import pandas as pd

        rows = []
        for _, row in df_raw.iterrows():
            rows.append(
                {
                    "prompt": row["prompt"],
                    "facet": row["facet"],
                    "chosen": row["chosen"],
                    "rejected": row["rejected"],
                    "gps_dimension": row["gps_dimension"],
                    "country": row["country"],
                    "generation_reasoning": row["reasoning"],
                    "reasoning": "score",
                    "m_chosen": 0.2,
                    "m_rejected": 0.9,
                    "m_diff_signed": -0.7,
                    "m_diff_abs": 0.7,
                    "z_value": -0.35 if row["country"] == "MEX" else 0.15,
                    "contamination_ratio": 1.0,
                    "m_chosen_trust": 0.2,
                    "m_rejected_trust": 0.9,
                    "m_chosen_risktaking": 0.1,
                    "m_rejected_risktaking": 0.2,
                    "m_chosen_patience": 0.1,
                    "m_rejected_patience": 0.2,
                    "m_chosen_altruism": 0.1,
                    "m_rejected_altruism": 0.2,
                    "m_chosen_posrecip": 0.1,
                    "m_rejected_posrecip": 0.2,
                    "m_chosen_negrecip": 0.1,
                    "m_rejected_negrecip": 0.2,
                }
            )
        return pd.DataFrame(rows), {"total": len(rows), "score_fail": 0, "mono_fail": 0, "dist_fail": 0, "pass": len(rows)}

    monkeypatch.setattr(generate, "run_teacher_pipeline", fake_run_teacher_pipeline)
    monkeypatch.setattr(score, "run_scoring_qc_export", fake_run_scoring_qc_export)

    output_dir = tmp_path / "outputs"
    exit_code = run.main(
        [
            "--countries",
            "MEX",
            "USA",
            "--sample-sizes",
            "2,3",
            "--scenarios-per-dim",
            "1",
            "--gps-path",
            str(gps_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    assert (output_dir / "D_syn_MEX_2.jsonl").exists()
    assert (output_dir / "D_syn_USA_3.jsonl").exists()
    manifest = json.loads((output_dir / "manifest_3.json").read_text())
    assert manifest["sample_size"] == 3
    assert manifest["config"]["teacher_model"]
    assert (output_dir / "D_syn_combined_hf_2").exists()


def test_cli_resume_uses_checkpoint_without_generation(tmp_path: Path, gps_path, monkeypatch) -> None:
    checkpoint_path = tmp_path / "checkpoint_raw_pairs.jsonl"
    checkpoint_df = pd.DataFrame(
        [
            {
                "prompt": "prompt-MEX-0",
                "facet": "facet",
                "gps_dimension": "trust",
                "country": "MEX",
                "chosen": "chosen",
                "rejected": "rejected",
                "reasoning": "generation",
            },
            {
                "prompt": "prompt-USA-0",
                "facet": "facet",
                "gps_dimension": "trust",
                "country": "USA",
                "chosen": "chosen",
                "rejected": "rejected",
                "reasoning": "generation",
            },
        ]
    )
    checkpoint_df.to_json(checkpoint_path, orient="records", lines=True)
    checkpoint_path.with_name("checkpoint_scenario_bank.json").write_text(
        json.dumps({"trust": [{"facet": "facet", "prompt": "prompt"}]})
    )

    generation_called = False
    scoring_input_rows: list[int] = []

    async def fake_run_teacher_pipeline(cultural_profiles, countries, config=CONFIG, tracker=None):
        nonlocal generation_called
        generation_called = True
        raise AssertionError("Generation should be skipped when --resume is used")

    async def fake_run_scoring_qc_export(df_raw, cultural_profiles, config=CONFIG, tracker=None):
        scoring_input_rows.append(len(df_raw))
        rows = []
        for _, row in df_raw.iterrows():
            rows.append(
                {
                    "prompt": row["prompt"],
                    "facet": row["facet"],
                    "chosen": row["chosen"],
                    "rejected": row["rejected"],
                    "gps_dimension": row["gps_dimension"],
                    "country": row["country"],
                    "generation_reasoning": row["reasoning"],
                    "reasoning": "score",
                    "m_chosen": 0.2,
                    "m_rejected": 0.9 if row["country"] == "MEX" else 0.1,
                    "m_diff_signed": -0.7 if row["country"] == "MEX" else 0.7,
                    "m_diff_abs": 0.7,
                    "z_value": -0.35 if row["country"] == "MEX" else 0.15,
                    "contamination_ratio": 1.0,
                    "m_chosen_trust": 0.2,
                    "m_rejected_trust": 0.9 if row["country"] == "MEX" else 0.1,
                    "m_chosen_risktaking": 0.1,
                    "m_rejected_risktaking": 0.2,
                    "m_chosen_patience": 0.1,
                    "m_rejected_patience": 0.2,
                    "m_chosen_altruism": 0.1,
                    "m_rejected_altruism": 0.2,
                    "m_chosen_posrecip": 0.1,
                    "m_rejected_posrecip": 0.2,
                    "m_chosen_negrecip": 0.1,
                    "m_rejected_negrecip": 0.2,
                }
            )
        return pd.DataFrame(rows), {
            "total": len(rows),
            "score_fail": 0,
            "mono_fail": 0,
            "dist_fail": 0,
            "pass": len(rows),
        }

    monkeypatch.setattr(generate, "run_teacher_pipeline", fake_run_teacher_pipeline)
    monkeypatch.setattr(score, "run_scoring_qc_export", fake_run_scoring_qc_export)

    output_dir = tmp_path / "outputs"
    exit_code = run.main(
        [
            "--resume",
            str(checkpoint_path),
            "--countries",
            "MEX",
            "USA",
            "--sample-sizes",
            "1",
            "--gps-path",
            str(gps_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    assert generation_called is False
    assert scoring_input_rows == [2]
    assert (output_dir / "manifest_1.json").exists()


def test_cli_checkpoint_fallback_after_scoring_failure(tmp_path: Path, gps_path, monkeypatch) -> None:
    async def fake_run_teacher_pipeline(cultural_profiles, countries, config=CONFIG, tracker=None):
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
        return pd.DataFrame(rows), {"trust": [{"facet": "facet", "prompt": "prompt"}]}

    async def failing_run_scoring_qc_export(df_raw, cultural_profiles, config=CONFIG, tracker=None):
        raise ConnectionError("Simulated internet error during scoring")

    monkeypatch.setattr(generate, "run_teacher_pipeline", fake_run_teacher_pipeline)
    monkeypatch.setattr(score, "run_scoring_qc_export", failing_run_scoring_qc_export)

    output_dir = tmp_path / "outputs"
    try:
        run.main(
            [
                "--countries",
                "MEX",
                "USA",
                "--sample-sizes",
                "1",
                "--gps-path",
                str(gps_path),
                "--output-dir",
                str(output_dir),
            ]
        )
    except ConnectionError as exc:
        assert "Simulated internet error" in str(exc)
    else:
        raise AssertionError("Expected simulated scoring failure to propagate")

    checkpoint_path = output_dir / "checkpoint_raw_pairs.jsonl"
    assert checkpoint_path.exists()
    assert (output_dir / "checkpoint_scenario_bank.json").exists()

    generation_called = False

    async def should_not_generate(cultural_profiles, countries, config=CONFIG, tracker=None):
        nonlocal generation_called
        generation_called = True
        raise AssertionError("Generation should be skipped on resume")

    async def recovered_run_scoring_qc_export(df_raw, cultural_profiles, config=CONFIG, tracker=None):
        rows = []
        for _, row in df_raw.iterrows():
            rows.append(
                {
                    "prompt": row["prompt"],
                    "facet": row["facet"],
                    "chosen": row["chosen"],
                    "rejected": row["rejected"],
                    "gps_dimension": row["gps_dimension"],
                    "country": row["country"],
                    "generation_reasoning": row["reasoning"],
                    "reasoning": "recovered",
                    "m_chosen": 0.2,
                    "m_rejected": 0.9 if row["country"] == "MEX" else 0.1,
                    "m_diff_signed": -0.7 if row["country"] == "MEX" else 0.7,
                    "m_diff_abs": 0.7,
                    "z_value": -0.35 if row["country"] == "MEX" else 0.15,
                    "contamination_ratio": 1.0,
                    "m_chosen_trust": 0.2,
                    "m_rejected_trust": 0.9 if row["country"] == "MEX" else 0.1,
                    "m_chosen_risktaking": 0.1,
                    "m_rejected_risktaking": 0.2,
                    "m_chosen_patience": 0.1,
                    "m_rejected_patience": 0.2,
                    "m_chosen_altruism": 0.1,
                    "m_rejected_altruism": 0.2,
                    "m_chosen_posrecip": 0.1,
                    "m_rejected_posrecip": 0.2,
                    "m_chosen_negrecip": 0.1,
                    "m_rejected_negrecip": 0.2,
                }
            )
        return pd.DataFrame(rows), {
            "total": len(rows),
            "score_fail": 0,
            "mono_fail": 0,
            "dist_fail": 0,
            "pass": len(rows),
        }

    monkeypatch.setattr(generate, "run_teacher_pipeline", should_not_generate)
    monkeypatch.setattr(score, "run_scoring_qc_export", recovered_run_scoring_qc_export)

    exit_code = run.main(
        [
            "--resume",
            str(checkpoint_path),
            "--countries",
            "MEX",
            "USA",
            "--sample-sizes",
            "1",
            "--gps-path",
            str(gps_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    assert generation_called is False
    assert (output_dir / "manifest_1.json").exists()
