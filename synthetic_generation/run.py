"""CLI entrypoint for the SCA 2.0 synthetic data generation pipeline."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Sequence

import pandas as pd
from dotenv import load_dotenv

from sca2_datagen.config import CONFIG, CostTracker
from sca2_datagen.export import export_sample_runs, summarize_qc
from sca2_datagen.profiles import load_cultural_profiles
from sca2_datagen.utils import setup_logging
from sca2_datagen import generate, score


LOGGER = logging.getLogger("sca2_datagen.run")


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(description="SCA 2.0 synthetic data generation pipeline")
    parser.add_argument("--scenarios-per-dim", type=int, default=CONFIG.scenarios_per_dim)
    parser.add_argument("--countries", nargs="+", default=CONFIG.default_countries)
    parser.add_argument("--sample-sizes", type=str, default="")
    parser.add_argument("--estimate-only", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--gps-path", type=Path, default=None)
    parser.add_argument("--wvs-path", type=Path, default=None)
    parser.add_argument(
        "--resume",
        type=Path,
        default=None,
        help="Path to checkpoint_raw_pairs.jsonl to skip generation and resume from scoring",
    )
    parser.add_argument(
        "--teacher-model",
        type=str,
        default=None,
        help="Model for scenario/facet generation (default: from config)",
    )
    parser.add_argument(
        "--generator-model",
        type=str,
        default=None,
        help="Model for paired response generation (default: from config)",
    )
    parser.add_argument(
        "--scorer-model",
        type=str,
        default=None,
        help="Model for scoring (default: from config)",
    )
    return parser


def parse_sample_sizes(raw: str) -> list[int]:
    """Parse comma-separated sample sizes."""

    if not raw.strip():
        return []
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


async def async_main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI."""

    load_dotenv(override=False)
    setup_logging()
    args = build_parser().parse_args(argv)

    overrides = {"scenarios_per_dim": args.scenarios_per_dim}
    if args.teacher_model:
        overrides["teacher_model"] = args.teacher_model
    if args.generator_model:
        overrides["generator_model"] = args.generator_model
    if args.scorer_model:
        overrides["scorer_model"] = args.scorer_model
    config = CONFIG.with_overrides(**overrides)
    countries = list(dict.fromkeys(args.countries))
    sample_sizes = sorted(parse_sample_sizes(args.sample_sizes))
    tracker = CostTracker()

    if args.estimate_only:
        estimate = tracker.estimate_run(config, countries, sample_sizes=sample_sizes or None)
        LOGGER.info("Estimate summary: %s", json.dumps(estimate, indent=2))
        if sample_sizes and estimate["expected_qc_passed_per_country"] < max(sample_sizes):
            LOGGER.warning(
                "Estimated QC-passed rows per country (%s) may be below the largest requested sample size (%s).",
                estimate["expected_qc_passed_per_country"],
                max(sample_sizes),
            )
        return 0

    cultural_profiles, _ = load_cultural_profiles(
        countries,
        gps_path=args.gps_path,
        wvs_path=args.wvs_path,
    )

    checkpoint_path = args.output_dir / "checkpoint_raw_pairs.jsonl"
    scenario_bank_path = args.output_dir / "checkpoint_scenario_bank.json"
    scenario_bank: dict[str, list[dict[str, str]]]

    if args.resume:
        df_raw = pd.read_json(args.resume, orient="records", lines=True)
        if scenario_bank_path.exists():
            scenario_bank = json.loads(scenario_bank_path.read_text())
        else:
            sibling_scenario_bank = args.resume.with_name("checkpoint_scenario_bank.json")
            scenario_bank = (
                json.loads(sibling_scenario_bank.read_text()) if sibling_scenario_bank.exists() else {}
            )
        LOGGER.info("Resumed from checkpoint: %s (%d pairs)", args.resume, len(df_raw))
    else:
        df_raw, scenario_bank = await generate.run_teacher_pipeline(
            cultural_profiles,
            countries,
            config=config,
            tracker=tracker,
        )
        LOGGER.info("Generated %s raw pairs", len(df_raw))
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        df_raw.to_json(checkpoint_path, orient="records", lines=True)
        LOGGER.info("Checkpoint saved: %s (%d pairs)", checkpoint_path, len(df_raw))
        scenario_bank_path.write_text(json.dumps(scenario_bank, indent=2))
        LOGGER.info("Scenario bank saved: %s", scenario_bank_path)

    df_final, qc_stats = await score.run_scoring_qc_export(
        df_raw,
        cultural_profiles,
        config=config,
        tracker=tracker,
    )
    summarize_qc(df_final, qc_stats)

    if df_final.empty:
        raise SystemExit("No QC-passed rows were generated.")

    export_sizes = sample_sizes or [min(df_final["country"].value_counts())]
    export_sample_runs(
        df_final=df_final,
        sample_sizes=export_sizes,
        cultural_profiles=cultural_profiles,
        config=config,
        output_dir=args.output_dir,
        cost_summary=tracker.summary(),
        scenario_bank=scenario_bank,
        qc_stats=qc_stats,
        raw_pair_count=len(df_raw),
        git_cwd=Path.cwd(),
    )
    LOGGER.info("Exported sample sizes: %s", export_sizes)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the async CLI from synchronous entrypoints."""

    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
