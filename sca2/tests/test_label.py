import json
from pathlib import Path

from sca2.label import run_label


def test_label_on_tiny_bank(tmp_path: Path) -> None:
    bank = tmp_path / "bank.jsonl"
    tmp_path.mkdir(parents=True, exist_ok=True)
    row = {
        "prompt": "A stranger asks me to watch their bag.",
        "facet": "stranger trust",
        "gps_dimension": "trust",
        "country": "USA",
        "response_a": "I watch the bag.",
        "response_b": "I decline.",
        "chosen_option": "A",
        "qc_status": "pass",
        "contamination_ratio": 0.1,
        "contamination_category": "low",
    }
    for dim in ("trust", "risktaking", "patience", "altruism", "posrecip", "negrecip"):
        row[f"m_chosen_{dim}"] = 0.8 if dim == "trust" else 0.4
        row[f"m_rejected_{dim}"] = 0.2 if dim == "trust" else 0.4
    bank.write_text(json.dumps(row) + "\n", encoding="utf-8")

    vectors = tmp_path / "z.json"
    vectors.write_text(
        json.dumps(
            {
                "AAA": {"trust": 0.4, "risktaking": 0.0, "patience": 0.0, "altruism": 0.0, "posrecip": 0.0, "negrecip": 0.0},
                "BBB": {"trust": -0.4, "risktaking": 0.0, "patience": 0.0, "altruism": 0.0, "posrecip": 0.0, "negrecip": 0.0},
            }
        ),
        encoding="utf-8",
    )

    protocol = tmp_path / "p.toml"
    protocol.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'name = "tiny"',
                "[anchor]",
                'source = "gps_falk_2018"',
                'file = "missing.dta"',
                f'vectors_json = "{vectors}"',
                "[profile]",
                'rule = "deterministic_quantitative"',
                "country_in_profile = false",
                "[generation]",
                f'bank = "{bank}"',
                'labeling = "deterministic_sign"',
                'selector = "none"',
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

    dest = tmp_path / "out"
    receipt = run_label(protocol, output_dir=dest)
    assert receipt["status"] == "ok"
    assert receipt["countries"] == 2
    assert receipt["triplets"] == 1
    assert receipt["rows"] == 2

    aaa = json.loads((dest / "D_syn_AAA.jsonl").read_text().splitlines()[0])
    bbb = json.loads((dest / "D_syn_BBB.jsonl").read_text().splitlines()[0])
    assert aaa["chosen_option"] == "A"
    assert aaa["chosen"] == "I watch the bag."
    assert bbb["chosen_option"] == "B"
    assert bbb["chosen"] == "I decline."
    assert aaa["prompt"] == bbb["prompt"]
