from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import run
from sca2_datagen import generate, score
from sca2_datagen.config import CONFIG, GPS_DIMENSIONS
from sca2_datagen.export import export_sample_runs


def test_estimate_only_runs(caplog, capsys, gps_path) -> None:
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
    out = capsys.readouterr().out
    assert "SCA 2.0 generator budget estimate" in out
    assert "LLM calls and token estimate" in out
    assert "rough cost per country" in out


def test_estimate_only_normalizes_non_default_countries(gps_path, caplog) -> None:
    with caplog.at_level("INFO", logger="sca2_datagen.run"):
        exit_code = run.main(
            [
                "--estimate-only",
                "--countries",
                "arg",
                "swe",
                "--scenarios-per-dim",
                "20",
                "--gps-path",
                str(gps_path),
            ]
        )
    assert exit_code == 0
    assert "countries=['ARG', 'SWE']" in caplog.text


def test_cli_model_override_flags_are_removed(gps_path) -> None:
    try:
        run.main(
            [
                "--estimate-only",
                "--countries",
                "MEX",
                "--gps-path",
                str(gps_path),
                "--teacher-model",
                "unsupported-model-alias",
            ]
        )
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("Expected argparse failure for removed model override flag")


def test_cli_use_anchors_accepts_bare_and_explicit_booleans() -> None:
    parser = run.build_parser()

    assert parser.parse_args(["--use-anchors"]).use_anchors is True
    assert parser.parse_args(["--use-anchors", "True"]).use_anchors is True
    assert parser.parse_args(["--use-anchors", "False"]).use_anchors is False


def test_cli_sample_sizes_exports_without_real_api_calls(tmp_path: Path, gps_path, monkeypatch) -> None:
    seen_anchor_settings: list[tuple[bool, bool]] = []

    async def fake_run_teacher_pipeline(
        cultural_profiles, countries, config=CONFIG, tracker=None, use_anchors=False
    ):
        import pandas as pd

        seen_anchor_settings.append((use_anchors, config.use_anchors))
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
            "--use-anchors",
            "True",
            "--gps-path",
            str(gps_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    assert seen_anchor_settings == [(True, True)]
    assert (output_dir / "D_syn_MEX_2.jsonl").exists()
    assert (output_dir / "D_syn_USA_3.jsonl").exists()
    first_export_row = json.loads((output_dir / "D_syn_MEX_2.jsonl").read_text().splitlines()[0])
    assert list(first_export_row)[:11] == [
        "prompt",
        "chosen",
        "rejected",
        "country",
        "gps_dimension",
        "z_value",
        "contamination_category",
        "contamination_ratio",
        "run_id",
        "export_timestamp",
        "gps_profile_vector",
    ]
    assert first_export_row["run_id"].startswith("outputs_")
    assert first_export_row["export_timestamp"]
    assert first_export_row["gps_profile_vector"]
    assert first_export_row["contamination_category"] == "high"
    manifest = json.loads((output_dir / "manifest_3.json").read_text())
    assert manifest["run_id"] == first_export_row["run_id"]
    assert manifest["sample_size"] == 3
    assert manifest["config"]["teacher_model"]
    assert manifest["config"]["use_anchors"] is True
    assert manifest["config"]["qc_mono_epsilon"] == 0.03
    assert manifest["qc_pass_rate"] == 1.0
    assert manifest["mono_fail_rate"] == 0.0
    assert manifest["dist_fail_rate"] == 0.0
    assert manifest["contamination_distribution"]["high"]["count"] == 6
    assert manifest["mean_m_diff_abs"] == 0.7
    assert "trust" in manifest["per_dimension_qc"]
    assert manifest["per_country_dimension_counts"]["MEX"]["trust"] == 3
    assert manifest["per_country_dimension_counts"]["USA"]["trust"] == 3
    assert manifest["per_country_contamination_counts"]["MEX"]["high"] == 3
    assert manifest["per_country_contamination_counts"]["USA"]["high"] == 3
    assert manifest["qc_health_summary"]
    assert (output_dir / "D_syn_combined_hf_2").exists()


def test_cli_persists_scoring_fields_to_checkpoint(tmp_path: Path, gps_path, monkeypatch) -> None:
    async def fake_run_teacher_pipeline(
        cultural_profiles, countries, config=CONFIG, tracker=None, use_anchors=False
    ):
        rows = [
            {
                "prompt": "prompt-MEX-0",
                "facet": "facet",
                "gps_dimension": "trust",
                "country": "MEX",
                "response_a": "high trust",
                "response_b": "low trust",
                "chosen_option": "B",
                "chosen": "low trust",
                "rejected": "high trust",
                "reasoning": "selection",
                "generation_reasoning": "generation",
            },
            {
                "prompt": "prompt-MEX-1",
                "facet": "facet",
                "gps_dimension": "trust",
                "country": "MEX",
                "response_a": "high trust 2",
                "response_b": "low trust 2",
                "chosen_option": "A",
                "chosen": "high trust 2",
                "rejected": "low trust 2",
                "reasoning": "selection fail",
                "generation_reasoning": "generation fail",
            },
        ]
        return pd.DataFrame(rows), {"trust": [{"facet": "facet", "prompt": "prompt"}]}

    async def fake_run_scoring_qc_export(df_raw, cultural_profiles, config=CONFIG, tracker=None):
        return pd.DataFrame(
            [
                {
                    "prompt": "prompt-MEX-0",
                    "facet": "facet",
                    "chosen": "low trust",
                    "rejected": "high trust",
                    "gps_dimension": "trust",
                    "country": "MEX",
                    "generation_reasoning": "generation",
                    "selection_reasoning": "selection",
                    "reasoning": "score pass",
                    "qc_status": "pass",
                    "failure_reason": "",
                    "mono_pass": True,
                    "dist_pass": True,
                    "m_chosen": 0.2,
                    "m_rejected": 0.9,
                    "m_diff_signed": -0.7,
                    "m_diff_abs": 0.7,
                    "z_value": -0.35,
                    "contamination_ratio": 0.25,
                    "contamination_category": "low",
                    "m_chosen_trust": 0.2,
                    "m_rejected_trust": 0.9,
                },
                {
                    "prompt": "prompt-MEX-1",
                    "facet": "facet",
                    "chosen": "high trust 2",
                    "rejected": "low trust 2",
                    "gps_dimension": "trust",
                    "country": "MEX",
                    "generation_reasoning": "generation fail",
                    "selection_reasoning": "selection fail",
                    "reasoning": "score fail",
                    "qc_status": "mono_fail",
                    "failure_reason": "mono_fail: signed_diff=0.7000 wrong sign for z=-0.35",
                    "mono_pass": False,
                    "dist_pass": True,
                    "m_chosen": 0.9,
                    "m_rejected": 0.2,
                    "m_diff_signed": 0.7,
                    "m_diff_abs": 0.7,
                    "z_value": -0.35,
                    "contamination_ratio": 0.8,
                    "contamination_category": "high",
                    "m_chosen_trust": 0.9,
                    "m_rejected_trust": 0.2,
                },
            ]
        ), {
            "total": 2,
            "score_fail": 0,
            "mono_fail": 1,
            "dist_fail": 0,
            "pass": 1,
            "per_dimension": {
                dim: {
                    "total": 2 if dim == "trust" else 0,
                    "score_fail": 0,
                    "mono_fail": 1 if dim == "trust" else 0,
                    "dist_fail": 0,
                    "pass": 1 if dim == "trust" else 0,
                }
                for dim in GPS_DIMENSIONS
            },
        }

    monkeypatch.setattr(generate, "run_teacher_pipeline", fake_run_teacher_pipeline)
    monkeypatch.setattr(score, "run_scoring_qc_export", fake_run_scoring_qc_export)

    output_dir = tmp_path / "outputs"
    exit_code = run.main(
        [
            "--countries",
            "MEX",
            "--sample-sizes",
            "1",
            "--gps-path",
            str(gps_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    checkpoint_rows = [
        json.loads(line)
        for line in (output_dir / "checkpoint_raw_pairs.jsonl").read_text().splitlines()
    ]
    assert checkpoint_rows[0]["response_a"] == "high trust"
    assert checkpoint_rows[0]["qc_status"] == "pass"
    assert checkpoint_rows[0]["score_reasoning"] == "score pass"
    assert checkpoint_rows[0]["selection_reasoning"] == "selection"
    assert checkpoint_rows[0]["mono_pass"] is True
    assert checkpoint_rows[0]["dist_pass"] is True
    assert checkpoint_rows[0]["contamination_ratio"] == 0.25
    assert checkpoint_rows[0]["m_chosen_trust"] == 0.2
    assert checkpoint_rows[1]["qc_status"] == "mono_fail"
    assert checkpoint_rows[1]["failure_reason"].startswith("mono_fail")


def test_export_sample_runs_filters_nonpassing_qc_rows(tmp_path: Path) -> None:
    rows = []
    for country in ["MEX", "USA"]:
        for index, qc_status in enumerate(["pass", "pass", "mono_fail"]):
            rows.append(
                {
                    "prompt": f"prompt-{country}-{index}",
                    "chosen": "chosen",
                    "rejected": "rejected",
                    "country": country,
                    "gps_dimension": "trust",
                    "z_value": -0.35 if country == "MEX" else 0.15,
                    "qc_status": qc_status,
                    "failure_reason": "" if qc_status == "pass" else "wrong sign",
                    "mono_pass": qc_status == "pass",
                    "dist_pass": True,
                    "m_diff_abs": 0.7,
                    "contamination_ratio": 0.2,
                }
            )
    df_final = pd.DataFrame(rows)
    cultural_profiles = {
        "MEX": {"z_c": {dim: -0.1 for dim in GPS_DIMENSIONS}},
        "USA": {"z_c": {dim: 0.1 for dim in GPS_DIMENSIONS}},
    }
    qc_stats = {
        "total": 6,
        "score_fail": 0,
        "mono_fail": 2,
        "dist_fail": 0,
        "pass": 4,
        "per_dimension": {
            dim: {
                "total": 6 if dim == "trust" else 0,
                "score_fail": 0,
                "mono_fail": 2 if dim == "trust" else 0,
                "dist_fail": 0,
                "pass": 4 if dim == "trust" else 0,
            }
            for dim in GPS_DIMENSIONS
        },
    }

    export_sample_runs(
        df_final=df_final,
        sample_sizes=[2],
        cultural_profiles=cultural_profiles,
        config=CONFIG,
        output_dir=tmp_path,
        cost_summary={},
        scenario_bank={},
        qc_stats=qc_stats,
        raw_pair_count=len(df_final),
    )

    for country in ["MEX", "USA"]:
        exported = pd.read_json(tmp_path / f"D_syn_{country}_2.jsonl", lines=True)
        assert len(exported) == 2
        assert set(exported["qc_status"]) == {"pass"}


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

    async def fake_run_teacher_pipeline(
        cultural_profiles, countries, config=CONFIG, tracker=None, use_anchors=False
    ):
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


def test_cli_resume_defaults_to_checkpoint_countries(tmp_path: Path, gps_path, monkeypatch) -> None:
    checkpoint_path = tmp_path / "checkpoint_raw_pairs.jsonl"
    checkpoint_df = pd.DataFrame(
        [
            {
                "prompt": "prompt-ARG-0",
                "facet": "facet",
                "gps_dimension": "trust",
                "country": "arg",
                "chosen": "chosen",
                "rejected": "rejected",
                "reasoning": "generation",
            },
            {
                "prompt": "prompt-SWE-0",
                "facet": "facet",
                "gps_dimension": "trust",
                "country": "SWE",
                "chosen": "chosen",
                "rejected": "rejected",
                "reasoning": "generation",
            },
        ]
    )
    checkpoint_df.to_json(checkpoint_path, orient="records", lines=True)

    seen_profile_countries: list[list[str]] = []

    async def should_not_generate(cultural_profiles, countries, config=CONFIG, tracker=None):
        raise AssertionError("Generation should be skipped when --resume is used")

    async def fake_run_scoring_qc_export(df_raw, cultural_profiles, config=CONFIG, tracker=None):
        seen_profile_countries.append(sorted(cultural_profiles))
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
                    "m_chosen": 0.9,
                    "m_rejected": 0.2,
                    "m_diff_signed": 0.7,
                    "m_diff_abs": 0.7,
                    "z_value": 0.1,
                    "contamination_ratio": 1.0,
                    "m_chosen_trust": 0.9,
                    "m_rejected_trust": 0.2,
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
    monkeypatch.setattr(score, "run_scoring_qc_export", fake_run_scoring_qc_export)

    output_dir = tmp_path / "outputs"
    exit_code = run.main(
        [
            "--resume",
            str(checkpoint_path),
            "--sample-sizes",
            "1",
            "--gps-path",
            str(gps_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    assert seen_profile_countries == [["ARG", "SWE"]]
    manifest = json.loads((output_dir / "manifest_1.json").read_text())
    assert sorted(manifest["countries"]) == ["ARG", "SWE"]


def test_cli_resume_country_mismatch_has_clear_argparse_error(tmp_path: Path, gps_path) -> None:
    checkpoint_path = tmp_path / "checkpoint_raw_pairs.jsonl"
    pd.DataFrame(
        [
            {
                "prompt": "prompt-ARG-0",
                "facet": "facet",
                "gps_dimension": "trust",
                "country": "ARG",
                "chosen": "chosen",
                "rejected": "rejected",
                "reasoning": "generation",
            }
        ]
    ).to_json(checkpoint_path, orient="records", lines=True)

    with pytest.raises(SystemExit) as exc_info:
        run.main(
            [
                "--resume",
                str(checkpoint_path),
                "--countries",
                "MEX",
                "--gps-path",
                str(gps_path),
            ]
        )

    assert exc_info.value.code == 2


def test_cli_checkpoint_fallback_after_scoring_failure(tmp_path: Path, gps_path, monkeypatch) -> None:
    async def fake_run_teacher_pipeline(
        cultural_profiles, countries, config=CONFIG, tracker=None, use_anchors=False
    ):
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
    except SystemExit as exc:
        assert "Simulated internet error" in str(exc)
        assert "Resume with --resume" in str(exc)
    else:
        raise AssertionError("Expected simulated scoring failure to exit with resume guidance")

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


def test_cli_skip_unavailable_sample_sizes_exports_feasible_only(
    tmp_path: Path, gps_path, monkeypatch
) -> None:
    async def fake_run_teacher_pipeline(
        cultural_profiles, countries, config=CONFIG, tracker=None, use_anchors=False
    ):
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
            "--countries",
            "MEX",
            "USA",
            "--sample-sizes",
            "2,5",
            "--sample-size-policy",
            "skip_unavailable",
            "--scenarios-per-dim",
            "1",
            "--gps-path",
            str(gps_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    assert (output_dir / "manifest_2.json").exists()
    assert not (output_dir / "manifest_5.json").exists()
    manifest = json.loads((output_dir / "manifest_2.json").read_text())
    assert manifest["sample_size_policy"] == "skip_unavailable"
    assert any(item["requested"] == 5 for item in manifest["skipped_sample_sizes"])


def test_cli_auto_sample_size_uses_qc_passed_rows(tmp_path: Path, gps_path, monkeypatch) -> None:
    async def fake_run_teacher_pipeline(
        cultural_profiles, countries, config=CONFIG, tracker=None, use_anchors=False
    ):
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
        rows = []
        for _, row in df_raw.iterrows():
            qc_status = "score_fail" if row["country"] == "USA" and row["prompt"].endswith("-2") else "pass"
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
                    "qc_status": qc_status,
                    "failure_reason": "mock" if qc_status != "pass" else "",
                    "mono_pass": qc_status == "pass",
                    "dist_pass": qc_status == "pass",
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
        return pd.DataFrame(rows), {
            "total": len(rows),
            "score_fail": 1,
            "mono_fail": 0,
            "dist_fail": 0,
            "pass": len(rows) - 1,
            "per_dimension": {
                dim: {
                    "total": len(rows) if dim == "trust" else 0,
                    "score_fail": 1 if dim == "trust" else 0,
                    "mono_fail": 0,
                    "dist_fail": 0,
                    "pass": len(rows) - 1 if dim == "trust" else 0,
                }
                for dim in GPS_DIMENSIONS
            },
        }

    monkeypatch.setattr(generate, "run_teacher_pipeline", fake_run_teacher_pipeline)
    monkeypatch.setattr(score, "run_scoring_qc_export", fake_run_scoring_qc_export)

    output_dir = tmp_path / "outputs"
    exit_code = run.main(
        [
            "--countries",
            "MEX",
            "USA",
            "--scenarios-per-dim",
            "1",
            "--gps-path",
            str(gps_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    assert (output_dir / "manifest_2.json").exists()
    assert not (output_dir / "manifest_3.json").exists()
    assert len(pd.read_json(output_dir / "D_syn_MEX_2.jsonl", lines=True)) == 2
    assert len(pd.read_json(output_dir / "D_syn_USA_2.jsonl", lines=True)) == 2


def test_cli_generation_failure_has_actionable_message(tmp_path: Path, gps_path, monkeypatch) -> None:
    async def failing_run_teacher_pipeline(
        cultural_profiles, countries, config=CONFIG, tracker=None, use_anchors=False
    ):
        raise ConnectionError("503 Service Unavailable")

    monkeypatch.setattr(generate, "run_teacher_pipeline", failing_run_teacher_pipeline)

    output_dir = tmp_path / "outputs"
    with pytest.raises(SystemExit) as exc_info:
        run.main(
            [
                "--countries",
                "ARG",
                "SWE",
                "--scenarios-per-dim",
                "1",
                "--sample-sizes",
                "1",
                "--gps-path",
                str(gps_path),
                "--output-dir",
                str(output_dir),
            ]
        )

    assert "Generation failed before a raw-pair checkpoint" in str(exc_info.value)
    assert "larger retry budget" in str(exc_info.value)
    assert not (output_dir / "checkpoint_raw_pairs.jsonl").exists()


def test_run_teacher_pipeline_stops_early_on_sustained_failures(monkeypatch) -> None:
    async def fake_generate_scenarios(
        dim_key, dim_info, n, config=CONFIG, tracker=None, use_anchors=False, sem=None
    ):
        return [{"facet": "f", "prompt": f"scenario-{dim_key}"}]

    async def fake_safe_generate_triplet(*args, **kwargs):
        return {"error": "RateLimitError: 429"}

    monkeypatch.setattr(generate, "generate_scenarios", fake_generate_scenarios)
    monkeypatch.setattr(generate, "safe_generate_triplet", fake_safe_generate_triplet)

    profiles = {
        "SWE": {
            "profile_text": "p",
            "z_c": {
                "trust": 0.1,
                "risktaking": 0.1,
                "patience": 0.1,
                "altruism": 0.1,
                "posrecip": 0.1,
                "negrecip": 0.1,
            },
        }
    }
    test_config = CONFIG.with_overrides(
        scenarios_per_dim=2,
        error_rate_window=3,
        max_error_rate_for_continue=0.5,
    )

    try:
        import asyncio

        asyncio.run(
            generate.run_teacher_pipeline(
                profiles,
                ["SWE"],
                config=test_config,
            )
        )
    except RuntimeError as exc:
        assert "Early stop triggered" in str(exc)
    else:
        raise AssertionError("Expected early stop runtime error")
