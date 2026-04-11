from __future__ import annotations

import json
from pathlib import Path

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
