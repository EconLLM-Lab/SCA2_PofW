"""Result aggregation and report writing for anchored DPO runs."""

from __future__ import annotations

import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import COUNTRIES, ExperimentConfig


def summarize_results(config: ExperimentConfig) -> dict[str, Path]:
    combined_file = config.results_dir / "reward_recovery_adapters_combined.csv"
    if not combined_file.exists():
        raise FileNotFoundError(f"Missing combined evaluation file: {combined_file}")

    rows = _read_csv_dicts(combined_file)
    adapter_summary = _summarize_groups(
        rows,
        keys=("model", "adapter_country", "eval_country"),
        include_median=True,
        include_margins=True,
    )
    dimension_summary = _summarize_groups(
        [row for row in rows if row.get("gps_dimension")],
        keys=("model", "adapter_country", "eval_country", "gps_dimension"),
        include_median=False,
        include_margins=False,
    )

    summary_by_adapter_eval = {
        (row["adapter_country"], row["eval_country"]): row for row in adapter_summary
    }

    mean_matrix = _matrix_rows(summary_by_adapter_eval, "mean_reward_delta")
    acc_matrix = _matrix_rows(summary_by_adapter_eval, "preference_accuracy")

    own_vs_other_rows: list[dict[str, Any]] = []
    for adapter_country in COUNTRIES:
        adapter_rows = [
            row for row in adapter_summary if row["adapter_country"] == adapter_country
        ]
        own = [
            row for row in adapter_rows if row["eval_country"] == adapter_country
        ]
        other = [
            row for row in adapter_rows if row["eval_country"] != adapter_country
        ]
        own_mean = _float(own[0]["mean_reward_delta"]) if own else float("nan")
        other_mean = _mean(_float(row["mean_reward_delta"]) for row in other)
        own_acc = _float(own[0]["preference_accuracy"]) if own else float("nan")
        other_acc = _mean(_float(row["preference_accuracy"]) for row in other)
        max_reward = max(_float(row["mean_reward_delta"]) for row in adapter_rows)
        max_acc = max(_float(row["preference_accuracy"]) for row in adapter_rows)
        own_vs_other_rows.append(
            {
                "adapter_country": adapter_country,
                "own_mean_reward_delta": own_mean,
                "other_mean_reward_delta": other_mean,
                "own_minus_other_reward_delta": own_mean - other_mean,
                "own_preference_accuracy": own_acc,
                "other_preference_accuracy": other_acc,
                "own_minus_other_preference_accuracy": own_acc - other_acc,
                "own_is_best_by_reward_delta": own_mean == max_reward,
                "own_is_best_by_preference_accuracy": own_acc == max_acc,
            }
        )

    outputs = {
        "adapter_summary": config.results_dir / "reward_recovery_adapter_summary.csv",
        "dimension_summary": config.results_dir / "reward_recovery_dimension_summary.csv",
        "mean_matrix": config.results_dir / "specialization_matrix_mean_reward_delta.csv",
        "accuracy_matrix": config.results_dir / "specialization_matrix_preference_accuracy.csv",
        "own_vs_other": config.results_dir / "own_vs_other_summary.csv",
    }

    _write_dicts(outputs["adapter_summary"], adapter_summary)
    _write_dicts(outputs["dimension_summary"], dimension_summary)
    _write_dicts(outputs["mean_matrix"], mean_matrix)
    _write_dicts(outputs["accuracy_matrix"], acc_matrix)
    _write_dicts(outputs["own_vs_other"], own_vs_other_rows)
    return outputs


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _mean(values: Any) -> float:
    materialized = list(values)
    if not materialized:
        return float("nan")
    return sum(materialized) / len(materialized)


def _summarize_groups(
    rows: list[dict[str, str]],
    keys: tuple[str, ...],
    include_median: bool,
    include_margins: bool,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)

    summary: list[dict[str, Any]] = []
    for group_key in sorted(grouped):
        group_rows = grouped[group_key]
        reward = [_float(row["dpo_reward_delta"]) for row in group_rows]
        pref_acc = [1.0 if _truthy(row["dpo_prefers_chosen"]) else 0.0 for row in group_rows]
        pref_prob = [_float(row["dpo_pref_prob"]) for row in group_rows]
        out: dict[str, Any] = dict(zip(keys, group_key))
        out.update(
            {
                "n": len(group_rows),
                "mean_reward_delta": _mean(reward),
                "preference_accuracy": _mean(pref_acc),
                "mean_dpo_pref_prob": _mean(pref_prob),
            }
        )
        if include_median:
            out["median_reward_delta"] = statistics.median(reward)
        if include_margins:
            out["mean_ref_margin"] = _mean(_float(row["ref_margin"]) for row in group_rows)
            out["mean_adapter_margin"] = _mean(
                _float(row["adapter_margin"]) for row in group_rows
            )
        summary.append(out)
    return summary


def _matrix_rows(
    summary_by_adapter_eval: dict[tuple[str, str], dict[str, Any]],
    metric: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for adapter_country in COUNTRIES:
        row: dict[str, Any] = {"adapter_country": adapter_country}
        for eval_country in COUNTRIES:
            summary_row = summary_by_adapter_eval.get((adapter_country, eval_country))
            row[eval_country] = summary_row.get(metric, "") if summary_row else ""
        rows.append(row)
    return rows


def _write_dicts(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _float(value: str) -> float:
    try:
        return float(value)
    except ValueError:
        return float("nan")


def write_run_report(config: ExperimentConfig) -> Path:
    adapter_summary_file = config.results_dir / "reward_recovery_adapter_summary.csv"
    dimension_summary_file = config.results_dir / "reward_recovery_dimension_summary.csv"
    own_vs_other_file = config.results_dir / "own_vs_other_summary.csv"

    adapter_rows = _read_csv_dicts(adapter_summary_file)
    dim_rows = _read_csv_dicts(dimension_summary_file)
    own_rows = _read_csv_dicts(own_vs_other_file)

    diagonal = [
        _float(row["mean_reward_delta"])
        for row in adapter_rows
        if row["adapter_country"] == row["eval_country"]
    ]
    off_diagonal = [
        _float(row["mean_reward_delta"])
        for row in adapter_rows
        if row["adapter_country"] != row["eval_country"]
    ]
    diag_avg = sum(diagonal) / len(diagonal)
    off_avg = sum(off_diagonal) / len(off_diagonal)

    own_best_reward = [
        row["adapter_country"]
        for row in own_rows
        if row["own_is_best_by_reward_delta"] == "True"
    ]
    own_best_accuracy = [
        row["adapter_country"]
        for row in own_rows
        if row["own_is_best_by_preference_accuracy"] == "True"
    ]

    low_n_dims = [
        row
        for row in dim_rows
        if int(float(row["n"])) < 5
    ]

    lines = [
        "# Anchored Pilot DPO Run Report",
        "",
        "## Specialization Summary",
        "",
        f"- Diagonal mean reward delta average: {diag_avg:.4f}",
        f"- Off-diagonal mean reward delta average: {off_avg:.4f}",
        f"- Diagonal minus off-diagonal: {diag_avg - off_avg:.4f}",
        f"- Own-country best by reward delta: {', '.join(own_best_reward) or 'none'}",
        f"- Own-country best by preference accuracy: {', '.join(own_best_accuracy) or 'none'}",
        "",
        "## Data Caveats",
        "",
        "- Results are exploratory because each eval split has 35 examples.",
        "- USA `negrecip` is underpowered in the source sample: the 172-row USA file has only 1 example.",
    ]

    if low_n_dims:
        lines.extend(["- Dimension cells with n < 5 should not be interpreted strongly:"])
        for row in low_n_dims:
            lines.append(
                "  - "
                f"{row['adapter_country']} adapter on {row['eval_country']} "
                f"/ {row['gps_dimension']}: n={row['n']}"
            )

    lines.extend(
        [
            "",
            "## Output Files",
            "",
            f"- `{config.results_dir / 'reward_recovery_adapters_combined.csv'}`",
            f"- `{adapter_summary_file}`",
            f"- `{dimension_summary_file}`",
            f"- `{config.results_dir / 'specialization_matrix_mean_reward_delta.csv'}`",
            f"- `{config.results_dir / 'specialization_matrix_preference_accuracy.csv'}`",
            f"- `{own_vs_other_file}`",
        ]
    )

    out = config.reports_dir / "run_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize anchored DPO reward recovery results.")
    parser.add_argument("--output-root", type=Path, default=None)
    args = parser.parse_args()
    config = ExperimentConfig(output_root=args.output_root) if args.output_root else ExperimentConfig()
    outputs = summarize_results(config)
    report = write_run_report(config)
    print("Wrote summaries:")
    for path in outputs.values():
        print(f"  {path}")
    print(f"Wrote report: {report}")


if __name__ == "__main__":
    main()
