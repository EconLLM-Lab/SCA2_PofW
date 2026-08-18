import json
from pathlib import Path

from sca2.eval import inspect_item_map, run_eval


def _tiny_protocol(tmp_path: Path, item_map: Path) -> Path:
    protocol = tmp_path / "p.toml"
    protocol.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'name = "tiny_eval"',
                "[anchor]",
                'source = "gps"',
                "[profile]",
                'rule = "x"',
                "[generation]",
                'bank = "b.jsonl"',
                'labeling = "deterministic_sign"',
                "[qc]",
                'mode = "x"',
                "[prompts]",
                "country_conditioning = false",
                "[train]",
                "wired = false",
                "[eval]",
                'surface = "wvs_wave7"',
                f'item_map = "{item_map}"',
                "country_conditioning = false",
                'primary_metric = "tvd"',
                'matched_vs_cross_means = "fixed_policy_proximity"',
                'notebook_score = "DPO_eval_WVS/DPO_survey_distribution_evaluation.ipynb"',
                "wired = false",
            ]
        ),
        encoding="utf-8",
    )
    return protocol


def test_inspect_item_map_counts_mapped(tmp_path: Path) -> None:
    path = tmp_path / "map.csv"
    path.write_text(
        "Question,gps_dimension\nQ57,trust\nQ13,patience\nQ260,\n",
        encoding="utf-8",
    )
    report = inspect_item_map(path)
    assert report["n_rows"] == 3
    assert report["n_mapped"] == 2
    assert report["n_demographic"] == 1


def test_eval_plans_existing_item_map(tmp_path: Path) -> None:
    path = tmp_path / "map.csv"
    path.write_text("Question,gps_dimension\nQ57,trust\nQ13,patience\n", encoding="utf-8")
    protocol = _tiny_protocol(tmp_path, path)
    receipt = run_eval(protocol, runs_root=tmp_path / "runs")
    assert receipt["status"] == "planned"
    assert receipt["rows"] == 2
    plan = json.loads(Path(receipt["out"]).read_text())
    assert plan["matched_vs_cross_means"] == "fixed_policy_proximity"
    assert "not recovery" in plan["claim_boundary"]


def test_eval_missing_map_fails(tmp_path: Path) -> None:
    protocol = _tiny_protocol(tmp_path, tmp_path / "absent.csv")
    try:
        run_eval(protocol, runs_root=tmp_path / "runs")
    except FileNotFoundError:
        return
    raise AssertionError("expected FileNotFoundError")


def test_eval_execute_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "map.csv"
    path.write_text("Question,gps_dimension\nQ57,trust\n", encoding="utf-8")
    protocol = _tiny_protocol(tmp_path, path)
    try:
        run_eval(protocol, execute=True, runs_root=tmp_path / "runs")
    except RuntimeError as exc:
        assert "Refusing to execute" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
