"""Data validation and split preparation for anchored DPO inputs."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import COUNTRIES, ExperimentConfig


REQUIRED_FIELDS = ("prompt", "chosen", "rejected", "country", "gps_dimension")


@dataclass(frozen=True)
class ValidationReport:
    country: str
    source_file: str
    n_rows: int
    country_counts: dict[str, int]
    dimension_counts: dict[str, int]
    missing_required: int
    empty_required: int
    identical_chosen_rejected: int
    expected_rows: int | None

    @property
    def ok(self) -> bool:
        return (
            self.missing_required == 0
            and self.empty_required == 0
            and self.identical_chosen_rejected == 0
            and (
                self.expected_rows is None
                or self.expected_rows <= 0
                or self.n_rows == self.expected_rows
            )
        )


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def validate_rows(
    rows: list[dict[str, Any]],
    country: str,
    source_file: Path,
    expected_rows: int | None = None,
) -> ValidationReport:
    missing_required = 0
    empty_required = 0
    identical = 0

    for row in rows:
        if any(field not in row for field in REQUIRED_FIELDS):
            missing_required += 1
            continue
        if any(not str(row.get(field, "")).strip() for field in REQUIRED_FIELDS):
            empty_required += 1
        if row.get("chosen") == row.get("rejected"):
            identical += 1

    return ValidationReport(
        country=country,
        source_file=str(source_file),
        n_rows=len(rows),
        country_counts=dict(Counter(str(row.get("country")) for row in rows)),
        dimension_counts=dict(Counter(str(row.get("gps_dimension")) for row in rows)),
        missing_required=missing_required,
        empty_required=empty_required,
        identical_chosen_rejected=identical,
        expected_rows=expected_rows,
    )


def validate_sources(config: ExperimentConfig, expected_rows: int | None = None) -> list[ValidationReport]:
    reports: list[ValidationReport] = []
    for country in COUNTRIES:
        source_file = config.source_file(country)
        rows = load_jsonl(source_file)
        reports.append(validate_rows(rows, country, source_file, expected_rows=expected_rows))
    return reports


def assert_reports_ok(reports: list[ValidationReport]) -> None:
    bad = [report for report in reports if not report.ok]
    if bad:
        details = "\n".join(json.dumps(asdict(report), indent=2) for report in bad)
        raise ValueError(f"Anchored DPO input validation failed:\n{details}")


def split_country_rows(
    rows: list[dict[str, Any]],
    country: str,
    train_frac: float,
    seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    prepared: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        copied = dict(row)
        copied.setdefault("country", country)
        copied.setdefault("item_id", f"{country}_{index:04d}")
        prepared.append(copied)

    rng = random.Random(seed)
    rng.shuffle(prepared)
    n_train = int(len(prepared) * train_frac)
    return prepared[:n_train], prepared[n_train:]


def prepare_splits(config: ExperimentConfig) -> dict[str, dict[str, int]]:
    config.ensure_output_dirs()
    reports = validate_sources(config)
    assert_reports_ok(reports)

    split_summary: dict[str, dict[str, int]] = {}
    for country in COUNTRIES:
        rows = load_jsonl(config.source_file(country))
        train_rows, eval_rows = split_country_rows(
            rows=rows,
            country=country,
            train_frac=config.train_frac,
            seed=config.seed,
        )
        write_jsonl(train_rows, config.train_file(country))
        write_jsonl(eval_rows, config.eval_file(country))
        split_summary[country] = {
            "source": len(rows),
            "train": len(train_rows),
            "eval": len(eval_rows),
        }
    return split_summary


def write_validation_report(
    config: ExperimentConfig,
    reports: list[ValidationReport],
    split_summary: dict[str, dict[str, int]] | None = None,
) -> Path:
    config.ensure_output_dirs()
    out = config.reports_dir / "data_validation_report.json"
    payload = {
        "reports": [asdict(report) for report in reports],
        "split_summary": split_summary,
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def print_reports(reports: list[ValidationReport]) -> None:
    for report in reports:
        status = "OK" if report.ok else "FAIL"
        print(f"{status} {report.country}: {report.n_rows} rows")
        print(f"  countries: {report.country_counts}")
        print(f"  dimensions: {report.dimension_counts}")
        print(
            "  invalid: "
            f"missing={report.missing_required}, "
            f"empty={report.empty_required}, "
            f"identical={report.identical_chosen_rejected}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and split anchored DPO inputs.")
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    config = ExperimentConfig(output_root=args.output_root) if args.output_root else ExperimentConfig()
    reports = validate_sources(config)
    print_reports(reports)
    assert_reports_ok(reports)

    split_summary = None
    if not args.check_only:
        split_summary = prepare_splits(config)
        print("Split summary:", split_summary)

    report_path = write_validation_report(config, reports, split_summary=split_summary)
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
