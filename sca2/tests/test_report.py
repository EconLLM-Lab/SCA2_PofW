import json
from pathlib import Path

from sca2.report import build_report, collect_stage_receipts, run_report


def _write_receipt(root: Path, run_id: str, stage: str, protocol_hash: str) -> None:
    folder = root / run_id
    folder.mkdir(parents=True)
    (folder / "receipt.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "stage": stage,
                "status": "ok",
                "protocol_hash": protocol_hash,
                "out": str(folder / f"{stage}.json"),
                "rows": 1,
                "rule": stage,
            }
        )
        + "\n"
    )


def _tiny_protocol(tmp_path: Path) -> Path:
    path = tmp_path / "p.toml"
    path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'name = "tiny_report"',
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
                "wired = false",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_collect_keeps_latest_matching_hash(tmp_path: Path) -> None:
    _write_receipt(tmp_path, "old_label", "label", "aaa")
    newer = tmp_path / "new_label" / "receipt.json"
    _write_receipt(tmp_path, "new_label", "label", "aaa")
    import os
    import time

    later = time.time() + 2
    os.utime(newer, (later, later))
    _write_receipt(tmp_path, "other", "label", "bbb")
    found = collect_stage_receipts(tmp_path, "aaa")
    assert found["label"]["run_id"] == "new_label"
    assert "other" not in str(found)


def test_report_incomplete_without_all_stages(tmp_path: Path) -> None:
    protocol = _tiny_protocol(tmp_path)
    from sca2.protocol import load_protocol

    loaded = load_protocol(protocol)
    _write_receipt(tmp_path / "runs", "only_gen", "generate", loaded["_hash"])
    receipt = run_report(protocol, runs_root=tmp_path / "runs")
    assert receipt["status"] == "incomplete"
    report = json.loads(Path(receipt["out"]).read_text())
    assert report["chain_ok"] is False
    assert "missing:label,train,eval" in report["notes"]


def test_report_chains_four_stages(tmp_path: Path) -> None:
    protocol = _tiny_protocol(tmp_path)
    from sca2.protocol import load_protocol

    loaded = load_protocol(protocol)
    runs = tmp_path / "runs"
    for stage in ("generate", "label", "train", "eval"):
        _write_receipt(runs, f"r_{stage}", stage, loaded["_hash"])
    receipt = run_report(protocol, runs_root=runs)
    assert receipt["status"] == "chained"
    report = json.loads(Path(receipt["out"]).read_text())
    assert report["chain_ok"] is True
    assert set(report["stages"]) == {"generate", "label", "train", "eval"}
    assert "not a trained adapter" in report["claim_boundary"]
