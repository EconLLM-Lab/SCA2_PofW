import json
from pathlib import Path

from sca2.generate import inspect_bank, run_generate


def test_inspect_bank_counts_unique_triplets(tmp_path: Path) -> None:
    path = tmp_path / "bank.jsonl"
    rows = []
    for country in ("USA", "MEX"):
        rows.append(
            {
                "prompt": "Watch the bag?",
                "gps_dimension": "trust",
                "response_a": "yes",
                "response_b": "no",
                "country": country,
            }
        )
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    report = inspect_bank(path)
    assert report["n_rows"] == 2
    assert report["n_triplets"] == 1
    assert report["conflicting_ab"] == 0
    assert report["missing_ab"] == 0


def test_inspect_bank_flags_conflict(tmp_path: Path) -> None:
    path = tmp_path / "bank.jsonl"
    rows = [
        {"prompt": "p", "gps_dimension": "trust", "response_a": "A1", "response_b": "B1"},
        {"prompt": "p", "gps_dimension": "trust", "response_a": "A2", "response_b": "B1"},
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    report = inspect_bank(path)
    assert report["conflicting_ab"] == 1
    assert report["ok"] is False


def test_inspect_reports_inverted_polarity(tmp_path: Path) -> None:
    path = tmp_path / "bank.jsonl"
    row = {
        "prompt": "p",
        "gps_dimension": "trust",
        "response_a": "A",
        "response_b": "B",
        "chosen_option": "A",
        "m_chosen_trust": 0.2,
        "m_rejected_trust": 0.8,
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    report = inspect_bank(path)
    assert report["polarity_inverted"] == 1
    assert "polarity_inverted=1" in report["warnings"]


def test_generate_reuses_declared_bank(tmp_path: Path) -> None:
    bank = tmp_path / "bank.jsonl"
    rows = []
    for dim in ("trust", "risktaking", "patience", "altruism", "posrecip", "negrecip"):
        rows.append(
            {
                "prompt": f"scenario {dim}",
                "gps_dimension": dim,
                "response_a": "high",
                "response_b": "low",
            }
        )
    bank.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    protocol = tmp_path / "p.toml"
    protocol.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'name = "tiny_gen"',
                "[anchor]",
                'source = "gps"',
                'file = "x.dta"',
                'vectors_json = "z.json"',
                "[profile]",
                'rule = "deterministic_quantitative"',
                "[generation]",
                f'bank = "{bank}"',
                'labeling = "deterministic_sign"',
                "[qc]",
                'mode = "inherited_source_bank"',
                "[prompts]",
                "country_conditioning = false",
                "[train]",
                "wired = false",
                "[eval]",
                "wired = false",
            ]
        ),
        encoding="utf-8",
    )
    receipt = run_generate(protocol, runs_root=tmp_path / "runs")
    assert receipt["status"] == "bank_reused"
    assert receipt["triplets"] == 6
    assert receipt["stage"] == "generate"


def test_materialize_is_refused(tmp_path: Path) -> None:
    protocol = tmp_path / "p.toml"
    protocol.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'name = "tiny_gen"',
                "[anchor]",
                'source = "gps"',
                "[profile]",
                'rule = "x"',
                "[generation]",
                'bank = "missing.jsonl"',
                'labeling = "deterministic_sign"',
                "[qc]",
                'mode = "x"',
                "[prompts]",
                "country_conditioning = false",
                "[train]",
                "wired = false",
                "[eval]",
                "wired = false",
            ]
        ),
        encoding="utf-8",
    )
    try:
        run_generate(protocol, materialize=True, runs_root=tmp_path / "runs")
    except RuntimeError as exc:
        assert "Rematerialize" in str(exc) or "rematerialize" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
