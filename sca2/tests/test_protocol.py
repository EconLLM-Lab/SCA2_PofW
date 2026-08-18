from pathlib import Path

from sca2.protocol import load_protocol, protocol_hash, repo_root
from sca2.runs import format_receipt, new_run_id


def test_paper_protocol_loads_and_hashes() -> None:
    path = repo_root() / "protocols" / "gps_sign_dpo_wvs.toml"
    protocol = load_protocol(path)
    assert protocol["name"] == "gps_sign_dpo_wvs"
    assert protocol["generation"]["labeling"] == "deterministic_sign"
    assert protocol["profile"]["country_in_profile"] is False
    assert protocol["train"]["wired"] is False
    assert protocol["eval"]["wired"] is False
    assert protocol["_hash"] == protocol_hash(path)
    assert len(protocol["_hash"]) == 16


def test_missing_table_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.toml"
    path.write_text("name = \"x\"\n[anchor]\nsource = \"gps\"\n", encoding="utf-8")
    try:
        load_protocol(path)
    except ValueError as exc:
        assert "missing tables" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_receipt_is_scannable() -> None:
    text = format_receipt(
        {
            "run_id": "abc",
            "stage": "label",
            "status": "ok",
            "protocol_name": "gps_sign_dpo_wvs",
            "protocol_hash": "deadbeef",
            "rows": 12,
        }
    )
    assert "run_id    abc" in text
    assert "stage     label" in text
    assert "rows      12" in text


def test_run_id_uses_protocol_name() -> None:
    from datetime import datetime, timezone

    run_id = new_run_id("gps_sign_dpo_wvs", when=datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc))
    assert run_id == "20260818_120000Z_gps_sign_dpo_wvs"

    staged_run_id = new_run_id(
        "gps_sign_dpo_wvs",
        when=datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc),
        stage="label",
    )
    assert staged_run_id == "20260818_120000Z_gps_sign_dpo_wvs_label"
