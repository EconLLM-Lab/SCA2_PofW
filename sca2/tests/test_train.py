import json
from pathlib import Path

from sca2.train import run_train


def _tiny_protocol(tmp_path: Path, data_dir: Path) -> Path:
    protocol = tmp_path / "p.toml"
    protocol.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'name = "tiny_train"',
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
                'estimator = "dpo_qlora"',
                'base_model = "meta-llama/Llama-3.1-8B-Instruct"',
                "wired = false",
                f'data_dir = "{data_dir}"',
                'notebook = "DPO_train_test/DPO_train.ipynb"',
                "beta = 0.1",
                "lora_r = 16",
                "[eval]",
                "wired = false",
            ]
        ),
        encoding="utf-8",
    )
    return protocol


def test_train_plans_existing_country_files(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "D_syn_USA.jsonl").write_text(json.dumps({"prompt": "p", "chosen": "a", "rejected": "b"}) + "\n")
    protocol = _tiny_protocol(tmp_path, data)
    receipt = run_train(protocol, countries=["USA"], runs_root=tmp_path / "runs")
    assert receipt["status"] == "planned"
    assert receipt["countries"] == 1
    assert receipt["rows"] == 1
    plan = json.loads(Path(receipt["out"]).read_text())
    assert plan["dpo"]["beta"] == 0.1
    assert plan["execute"] is False


def test_train_missing_country_fails(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    protocol = _tiny_protocol(tmp_path, data)
    try:
        run_train(protocol, countries=["JPN"], runs_root=tmp_path / "runs")
    except FileNotFoundError as exc:
        assert "JPN" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")


def test_train_execute_is_refused(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "D_syn_USA.jsonl").write_text("{}\n")
    protocol = _tiny_protocol(tmp_path, data)
    try:
        run_train(protocol, countries=["USA"], execute=True, runs_root=tmp_path / "runs")
    except RuntimeError as exc:
        assert "Refusing to execute" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
