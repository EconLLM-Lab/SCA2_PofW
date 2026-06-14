"""CLI entrypoint for the anchored pilot DPO replication.

Examples:
    python run_experiment.py prepare
    python run_experiment.py smoke
    python run_experiment.py train --country ARG
    python run_experiment.py evaluate --adapter-country ARG --max-examples 2 --no-generate-answers
    python run_experiment.py summarize
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dpo_anchored.analysis import summarize_results, write_run_report
from dpo_anchored.config import COUNTRIES, ExperimentConfig
from dpo_anchored.data import prepare_splits, print_reports, validate_sources, write_validation_report


def make_config(
    output_root: Path | None,
    source_dir: Path | None,
    source_suffix: str | None,
) -> ExperimentConfig:
    kwargs: dict[str, object] = {}
    if output_root is not None:
        kwargs["output_root"] = output_root
    if source_dir is not None:
        kwargs["source_dir"] = source_dir
    if source_suffix is not None:
        kwargs["source_suffix"] = source_suffix
    return ExperimentConfig(**kwargs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run anchored pilot DPO replication phases.")
    parser.add_argument(
        "phase",
        choices=("check", "prepare", "smoke", "precompute", "train", "evaluate", "summarize"),
    )
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--source-dir", type=Path, default=None)
    parser.add_argument("--source-suffix", type=str, default=None)
    parser.add_argument("--country", choices=COUNTRIES, default=None)
    parser.add_argument("--adapter-country", choices=COUNTRIES, default=None)
    parser.add_argument("--max-examples", type=int, default=None)
    parser.add_argument("--no-generate-answers", action="store_true")
    args = parser.parse_args()

    config = make_config(args.output_root, args.source_dir, args.source_suffix)

    if args.phase == "check":
        reports = validate_sources(config)
        print_reports(reports)
        write_validation_report(config, reports)
        return

    if args.phase == "prepare":
        split_summary = prepare_splits(config)
        reports = validate_sources(config)
        print_reports(reports)
        report_path = write_validation_report(config, reports, split_summary=split_summary)
        print(f"Wrote {report_path}")
        return

    if args.phase == "smoke":
        from dpo_anchored.modeling import runtime_smoke_check

        runtime_smoke_check(config)
        return

    if args.phase == "precompute":
        from dpo_anchored.modeling import precompute_reference_logps, write_training_metadata

        countries = [args.country] if args.country else list(COUNTRIES)
        write_training_metadata(config)
        for country in countries:
            out = precompute_reference_logps(config, country, max_examples=args.max_examples)
            print(f"Wrote {out}")
        return

    if args.phase == "train":
        from dpo_anchored.modeling import train_adapter, write_training_metadata

        countries = [args.country] if args.country else list(COUNTRIES)
        write_training_metadata(config)
        for country in countries:
            adapter_dir = train_adapter(config, country)
            print(f"Trained {country}: {adapter_dir}")
        return

    if args.phase == "evaluate":
        from dpo_anchored.modeling import evaluate_adapter_on_all_countries, run_full_evaluation

        generate_answers = not args.no_generate_answers
        if args.adapter_country:
            df = evaluate_adapter_on_all_countries(
                config,
                adapter_country=args.adapter_country,
                max_examples=args.max_examples,
                generate_answers=generate_answers,
            )
            print(df.groupby(["adapter_country", "eval_country"]).size())
        else:
            combined_file = run_full_evaluation(
                config,
                max_examples=args.max_examples,
                generate_answers=generate_answers,
            )
            print(f"Wrote {combined_file}")
        return

    if args.phase == "summarize":
        outputs = summarize_results(config)
        report = write_run_report(config)
        for path in outputs.values():
            print(f"Wrote {path}")
        print(f"Wrote {report}")
        return


if __name__ == "__main__":
    main()
