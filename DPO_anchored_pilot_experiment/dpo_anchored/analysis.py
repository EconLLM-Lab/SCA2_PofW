"""Result aggregation and report writing for anchored DPO runs.

The primary evidence for the anchored pilot is still the country-level 3x3
adapter/evaluation matrix. The additional summaries below expose the same
reward-recovery signal by GPS dimension, GPS profile magnitude, and generator
contamination bucket. They are intentionally CSV-first so Colab runs can be
audited without importing plotting or notebook-only dependencies.
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import COUNTRIES, ExperimentConfig


def summarize_results(config: ExperimentConfig) -> dict[str, Path]:
    combined_file = config.results_dir / "reward_recovery_adapters_combined.csv"
    if not combined_file.exists():
        raise FileNotFoundError(f"Missing combined evaluation file: {combined_file}")

    rows = _enrich_rows_with_eval_metadata(config, _read_csv_dicts(combined_file))
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
    dimension_specialization = _dimension_specialization_rows(dimension_summary)
    z_correlation = _z_recovery_correlation_rows(rows)
    contamination_summary = _contamination_summary_rows(rows)

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
        "dimension_specialization": config.results_dir
        / "per_dimension_specialization_summary.csv",
        "z_correlation": config.results_dir / "z_value_recovery_correlation.csv",
        "contamination_summary": config.results_dir
        / "contamination_recovery_summary.csv",
    }

    _write_dicts(outputs["adapter_summary"], adapter_summary)
    _write_dicts(outputs["dimension_summary"], dimension_summary)
    _write_dicts(outputs["mean_matrix"], mean_matrix)
    _write_dicts(outputs["accuracy_matrix"], acc_matrix)
    _write_dicts(outputs["own_vs_other"], own_vs_other_rows)
    _write_dicts(outputs["dimension_specialization"], dimension_specialization)
    _write_dicts(outputs["z_correlation"], z_correlation)
    _write_dicts(outputs["contamination_summary"], contamination_summary)
    return outputs


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _mean(values: Any) -> float:
    materialized = [value for value in values if not _is_nan(value)]
    if not materialized:
        return float("nan")
    return sum(materialized) / len(materialized)


def _is_nan(value: Any) -> bool:
    return isinstance(value, float) and math.isnan(value)


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


def _dimension_specialization_rows(
    dimension_summary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute own-minus-other specialization separately for each GPS dimension."""

    out: list[dict[str, Any]] = []
    by_adapter_dim: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in dimension_summary:
        by_adapter_dim[(row["adapter_country"], row["gps_dimension"])].append(row)

    for adapter_country in COUNTRIES:
        for gps_dimension in sorted({row["gps_dimension"] for row in dimension_summary}):
            group_rows = by_adapter_dim.get((adapter_country, gps_dimension), [])
            own = [
                row for row in group_rows if row["eval_country"] == adapter_country
            ]
            other = [
                row for row in group_rows if row["eval_country"] != adapter_country
            ]
            own_reward = _float(own[0]["mean_reward_delta"]) if own else float("nan")
            other_reward = _mean(_float(row["mean_reward_delta"]) for row in other)
            own_acc = _float(own[0]["preference_accuracy"]) if own else float("nan")
            other_acc = _mean(_float(row["preference_accuracy"]) for row in other)
            out.append(
                {
                    "adapter_country": adapter_country,
                    "gps_dimension": gps_dimension,
                    "own_n": int(float(own[0]["n"])) if own else 0,
                    "other_n": int(sum(float(row["n"]) for row in other)),
                    "own_mean_reward_delta": own_reward,
                    "other_mean_reward_delta": other_reward,
                    "own_minus_other_mean_reward_delta": own_reward - other_reward,
                    "own_preference_accuracy": own_acc,
                    "other_preference_accuracy": other_acc,
                    "own_minus_other_preference_accuracy": own_acc - other_acc,
                }
            )
    return out


def _z_recovery_correlation_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Correlate profile magnitude with recovered reward/accuracy by adapter/eval cell.

    The row-level DPO reward delta is expected to be positive when the adapter
    favors the chosen response. Since the chosen response was already aligned to
    the country profile, profile *magnitude* is represented by abs(z_value).
    Signed correlations are included as diagnostics, but the abs-z columns are
    the main magnitude-recovery test.
    """

    if not any(row.get("z_value") not in {"", None} for row in rows):
        return []

    dim_rows = _summarize_groups(
        [row for row in rows if row.get("gps_dimension") and row.get("z_value")],
        keys=("model", "adapter_country", "eval_country", "gps_dimension"),
        include_median=False,
        include_margins=False,
    )
    z_by_cell = _mean_by_keys(
        rows,
        keys=("model", "adapter_country", "eval_country", "gps_dimension"),
        value_key="z_value",
    )
    for row in dim_rows:
        key = (
            row["model"],
            row["adapter_country"],
            row["eval_country"],
            row["gps_dimension"],
        )
        row["z_value"] = z_by_cell.get(key, float("nan"))
        row["abs_z_value"] = abs(row["z_value"])

    out: list[dict[str, Any]] = []
    for key, group in _group_by(dim_rows, ("model", "adapter_country", "eval_country")).items():
        z_values = [_float(row["z_value"]) for row in group]
        abs_z_values = [_float(row["abs_z_value"]) for row in group]
        reward_values = [_float(row["mean_reward_delta"]) for row in group]
        acc_values = [_float(row["preference_accuracy"]) for row in group]
        out.append(
            {
                "model": key[0],
                "adapter_country": key[1],
                "eval_country": key[2],
                "n_dimension_cells": len(group),
                "pearson_abs_z_vs_mean_reward_delta": _pearson(abs_z_values, reward_values),
                "pearson_abs_z_vs_preference_accuracy": _pearson(abs_z_values, acc_values),
                "pearson_z_vs_mean_reward_delta": _pearson(z_values, reward_values),
                "pearson_z_vs_preference_accuracy": _pearson(z_values, acc_values),
            }
        )

    if dim_rows:
        abs_z_values = [_float(row["abs_z_value"]) for row in dim_rows]
        z_values = [_float(row["z_value"]) for row in dim_rows]
        reward_values = [_float(row["mean_reward_delta"]) for row in dim_rows]
        acc_values = [_float(row["preference_accuracy"]) for row in dim_rows]
        out.append(
            {
                "model": "ALL",
                "adapter_country": "ALL",
                "eval_country": "ALL",
                "n_dimension_cells": len(dim_rows),
                "pearson_abs_z_vs_mean_reward_delta": _pearson(abs_z_values, reward_values),
                "pearson_abs_z_vs_preference_accuracy": _pearson(abs_z_values, acc_values),
                "pearson_z_vs_mean_reward_delta": _pearson(z_values, reward_values),
                "pearson_z_vs_preference_accuracy": _pearson(z_values, acc_values),
            }
        )
    return out


def _contamination_summary_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Summarize recovery by generator contamination category."""

    if not any(row.get("contamination_category") for row in rows):
        return []

    summary = _summarize_groups(
        [row for row in rows if row.get("contamination_category")],
        keys=("model", "adapter_country", "eval_country", "contamination_category"),
        include_median=False,
        include_margins=False,
    )
    own_flags = {
        (row["model"], row["adapter_country"], row["eval_country"]): (
            row["adapter_country"] == row["eval_country"]
        )
        for row in summary
    }
    for row in summary:
        row["is_own_country_eval"] = own_flags[
            (row["model"], row["adapter_country"], row["eval_country"])
        ]

    compact = _summarize_groups(
        [row for row in rows if row.get("contamination_category")],
        keys=("contamination_category",),
        include_median=True,
        include_margins=False,
    )
    for row in compact:
        row["model"] = "ALL"
        row["adapter_country"] = "ALL"
        row["eval_country"] = "ALL"
        row["is_own_country_eval"] = ""

    return compact + summary


def _mean_by_keys(
    rows: list[dict[str, str]],
    keys: tuple[str, ...],
    value_key: str,
) -> dict[tuple[str, ...], float]:
    grouped: dict[tuple[str, ...], list[float]] = defaultdict(list)
    for row in rows:
        value = _float(row.get(value_key, ""))
        if _is_nan(value):
            continue
        grouped[tuple(row.get(key, "") for key in keys)].append(value)
    return {key: _mean(values) for key, values in grouped.items()}


def _group_by(
    rows: list[dict[str, Any]],
    keys: tuple[str, ...],
) -> dict[tuple[str, ...], list[dict[str, Any]]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)
    return grouped


def _pearson(xs: list[float], ys: list[float]) -> float:
    pairs = [
        (x, y)
        for x, y in zip(xs, ys)
        if not _is_nan(x) and not _is_nan(y)
    ]
    if len(pairs) < 2:
        return float("nan")
    mean_x = _mean(x for x, _ in pairs)
    mean_y = _mean(y for _, y in pairs)
    centered_x = [x - mean_x for x, _ in pairs]
    centered_y = [y - mean_y for _, y in pairs]
    denom_x = math.sqrt(sum(x * x for x in centered_x))
    denom_y = math.sqrt(sum(y * y for y in centered_y))
    if denom_x == 0.0 or denom_y == 0.0:
        return float("nan")
    return sum(x * y for x, y in zip(centered_x, centered_y)) / (denom_x * denom_y)


def _matrix_rows(
    summary_by_adapter_eval: dict[tuple[str, str], dict[str, Any]],
    metric: str,
) -> list[dict[str, Any]]:
    """Return the 3x3 adapter/eval matrix for a scalar recovery metric."""

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
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
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
    except (TypeError, ValueError):
        return float("nan")


def _enrich_rows_with_eval_metadata(
    config: ExperimentConfig,
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Join eval-split metadata back into combined result rows when available."""

    metadata_fields = (
        "z_value",
        "contamination_ratio",
        "contamination_category",
        "m_diff_signed",
        "m_diff_abs",
        "facet",
        "chosen_option",
    )
    if all(any(row.get(field) for row in rows) for field in ("z_value", "contamination_category")):
        return rows

    by_item: dict[tuple[str, str], dict[str, Any]] = {}
    by_text: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for country in COUNTRIES:
        eval_file = config.eval_file(country)
        if not eval_file.exists():
            continue
        for eval_row in _read_jsonl_dicts(eval_file):
            item_id = str(eval_row.get("item_id", ""))
            if item_id:
                by_item[(country, item_id)] = eval_row
            by_text[
                (
                    country,
                    str(eval_row.get("prompt", "")),
                    str(eval_row.get("chosen", "")),
                    str(eval_row.get("rejected", "")),
                )
            ] = eval_row

    if not by_item and not by_text:
        return rows

    enriched: list[dict[str, str]] = []
    for row in rows:
        copied = dict(row)
        country = str(row.get("eval_country") or row.get("country") or "")
        item_id = str(row.get("item_id") or "")
        metadata = by_item.get((country, item_id)) if item_id else None
        if metadata is None:
            metadata = by_text.get(
                (
                    country,
                    str(row.get("prompt", "")),
                    str(row.get("chosen", "")),
                    str(row.get("rejected", "")),
                )
            )
        if metadata:
            for field in metadata_fields:
                if not copied.get(field) and field in metadata:
                    copied[field] = str(metadata[field])
        enriched.append(copied)
    return enriched


def _read_jsonl_dicts(path: Path) -> list[dict[str, Any]]:
    import json

    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def generate_run_report(config: ExperimentConfig) -> Path:
    adapter_summary_file = config.results_dir / "reward_recovery_adapter_summary.csv"
    dimension_summary_file = config.results_dir / "reward_recovery_dimension_summary.csv"
    own_vs_other_file = config.results_dir / "own_vs_other_summary.csv"
    dimension_specialization_file = (
        config.results_dir / "per_dimension_specialization_summary.csv"
    )
    z_correlation_file = config.results_dir / "z_value_recovery_correlation.csv"
    contamination_summary_file = config.results_dir / "contamination_recovery_summary.csv"

    adapter_rows = _read_csv_dicts(adapter_summary_file)
    dim_rows = _read_csv_dicts(dimension_summary_file)
    own_rows = _read_csv_dicts(own_vs_other_file)
    dim_spec_rows = _read_csv_dicts(dimension_specialization_file)
    z_rows = _read_csv_dicts(z_correlation_file)
    contamination_rows = _read_csv_dicts(contamination_summary_file)

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
    interpretable_dim_specs = [
        row
        for row in dim_spec_rows
        if not _is_nan(_float(row["own_minus_other_mean_reward_delta"]))
    ]
    weakest_dim_specs = sorted(
        interpretable_dim_specs,
        key=lambda row: _float(row["own_minus_other_mean_reward_delta"]),
    )[:6]
    overall_z = next((row for row in z_rows if row.get("model") == "ALL"), None)
    contamination_compact = [
        row for row in contamination_rows if row.get("model") == "ALL"
    ]
    high_contamination = next(
        (
            row
            for row in contamination_compact
            if row.get("contamination_category") == "high"
        ),
        None,
    )
    non_high_contamination = [
        row
        for row in contamination_compact
        if row.get("contamination_category") in {"low", "medium"}
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
        "## Per-Dimension Specialization",
        "",
        "Own-minus-other values are computed within each adapter country and GPS dimension.",
    ]
    if weakest_dim_specs:
        lines.append("")
        lines.append("| Adapter | Dimension | Own n | Other n | Reward gap | Accuracy gap |")
        lines.append("| --- | --- | ---: | ---: | ---: | ---: |")
        for row in weakest_dim_specs:
            lines.append(
                "| "
                f"{row['adapter_country']} | {row['gps_dimension']} | "
                f"{row['own_n']} | {row['other_n']} | "
                f"{_float(row['own_minus_other_mean_reward_delta']):.4f} | "
                f"{_float(row['own_minus_other_preference_accuracy']):.4f} |"
            )
    else:
        lines.append("")
        lines.append("- No per-dimension specialization rows were available.")

    lines.extend(
        [
            "",
            "## GPS Magnitude Recovery",
            "",
        ]
    )
    if overall_z:
        lines.extend(
            [
                "- Correlations use dimension-level means and `abs(z_value)` for the magnitude test.",
                f"- Overall abs(z) vs mean reward delta: {_float(overall_z['pearson_abs_z_vs_mean_reward_delta']):.4f}",
                f"- Overall abs(z) vs preference accuracy: {_float(overall_z['pearson_abs_z_vs_preference_accuracy']):.4f}",
            ]
        )
    else:
        lines.append("- `z_value` was unavailable in the combined results or eval splits.")

    lines.extend(
        [
            "",
            "## Contamination Slice",
            "",
        ]
    )
    if contamination_compact:
        lines.append("| Category | n | Mean reward delta | Preference accuracy |")
        lines.append("| --- | ---: | ---: | ---: |")
        for row in sorted(contamination_compact, key=lambda r: r["contamination_category"]):
            lines.append(
                "| "
                f"{row['contamination_category']} | {row['n']} | "
                f"{_float(row['mean_reward_delta']):.4f} | "
                f"{_float(row['preference_accuracy']):.4f} |"
            )
        if high_contamination and non_high_contamination:
            high_reward = _float(high_contamination["mean_reward_delta"])
            high_acc = _float(high_contamination["preference_accuracy"])
            non_high_reward = _mean(
                _float(row["mean_reward_delta"]) for row in non_high_contamination
            )
            non_high_acc = _mean(
                _float(row["preference_accuracy"]) for row in non_high_contamination
            )
            lines.extend(
                [
                    "",
                    f"- High minus low/medium mean reward delta: {high_reward - non_high_reward:.4f}",
                    f"- High minus low/medium preference accuracy: {high_acc - non_high_acc:.4f}",
                ]
            )
    else:
        lines.append("- `contamination_category` was unavailable in the combined results or eval splits.")

    lines.extend(
        [
            "",
        "## Data Caveats",
        "",
        "- Results are exploratory because each eval split has 35 examples.",
        "- USA `negrecip` is underpowered in the source sample: the 172-row USA file has only 1 example.",
        "- Dimension-level and contamination-level cells are noisy; inspect `n` before interpreting a sign.",
        "- Contamination slices are diagnostic, not causal. In the 172-row anchored source files most items are high-contamination, so low/medium buckets are very small.",
        ]
    )

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
            f"- `{dimension_specialization_file}`",
            f"- `{z_correlation_file}`",
            f"- `{contamination_summary_file}`",
            f"- `{config.results_dir / 'specialization_matrix_mean_reward_delta.csv'}`",
            f"- `{config.results_dir / 'specialization_matrix_preference_accuracy.csv'}`",
            f"- `{own_vs_other_file}`",
        ]
    )

    out = config.reports_dir / "run_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_run_report(config: ExperimentConfig) -> Path:
    """Backward-compatible wrapper for older notebooks."""

    return generate_run_report(config)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize anchored DPO reward recovery results.")
    parser.add_argument("--output-root", type=Path, default=None)
    args = parser.parse_args()
    config = ExperimentConfig(output_root=args.output_root) if args.output_root else ExperimentConfig()
    outputs = summarize_results(config)
    report = generate_run_report(config)
    print("Wrote summaries:")
    for path in outputs.values():
        print(f"  {path}")
    print(f"Wrote report: {report}")


if __name__ == "__main__":
    main()
