import asyncio

import pandas as pd

from sca2_datagen import score
from sca2_datagen.config import CONFIG, CostTracker, GPS_DIMENSIONS


def test_unwrap_handles_dict() -> None:
    assert score.unwrap({"response": "hello"}) == "hello"


def test_score_pair_clips_scores() -> None:
    async def fake_tracked_completion(block, tracker, **kwargs):
        return __import__("tests.conftest", fromlist=["fake_response"]).fake_response(
            '{"scores_a": {"trust": 1.5, "risktaking": 0.4, "patience": 0.4, "altruism": 0.4, "posrecip": 0.4, "negrecip": 0.4}, '
            '"scores_b": {"trust": -1.0, "risktaking": 0.3, "patience": 0.3, "altruism": 0.3, "posrecip": 0.3, "negrecip": 0.3}, '
            '"reasoning": "ok"}'
        )

    async def run_test():
        original = score.utils.tracked_completion
        score.utils.tracked_completion = fake_tracked_completion
        try:
            return await score.score_pair(
                "scenario",
                "chosen",
                "rejected",
                "trust",
                GPS_DIMENSIONS["trust"],
                asyncio.Semaphore(1),
                config=CONFIG,
                tracker=CostTracker(),
            )
        finally:
            score.utils.tracked_completion = original

    scores_a, scores_b, reasoning = asyncio.run(run_test())
    assert scores_a["trust"] == 1.0
    assert scores_b["trust"] == 0.0
    assert reasoning == "ok"


def test_run_scoring_qc_export_filters_and_keeps_contamination() -> None:
    async def fake_score_pair(*args, **kwargs):
        return (
            {"trust": 0.2, "risktaking": 0.5, "patience": 0.5, "altruism": 0.5, "posrecip": 0.5, "negrecip": 0.5},
            {"trust": 0.9, "risktaking": 0.2, "patience": 0.2, "altruism": 0.2, "posrecip": 0.2, "negrecip": 0.2},
            "reasoning",
        )

    async def run_test():
        original = score.score_pair
        score.score_pair = fake_score_pair
        try:
            df_raw = pd.DataFrame(
                [
                    {
                        "prompt": "scenario",
                        "facet": "facet",
                        "chosen": "chosen",
                        "rejected": "rejected",
                        "gps_dimension": "trust",
                        "country": "MEX",
                        "reasoning": "generation",
                    }
                ]
            )
            profiles = {"MEX": {"z_c": {"trust": -0.35}}}
            return await score.run_scoring_qc_export(
                df_raw,
                profiles,
                config=CONFIG,
                tracker=CostTracker(),
            )
        finally:
            score.score_pair = original

    df_final, stats = asyncio.run(run_test())
    assert len(df_final) == 1
    assert stats["pass"] == 1
    assert stats["per_dimension"]["trust"]["pass"] == 1
    assert df_final.iloc[0]["contamination_ratio"] is not None
    assert df_final.iloc[0]["contamination_category"] == "high"


def test_run_scoring_qc_export_allows_mono_epsilon_near_tie() -> None:
    async def fake_score_pair(*args, **kwargs):
        return (
            {"trust": 0.49, "risktaking": 0.5, "patience": 0.5, "altruism": 0.5, "posrecip": 0.5, "negrecip": 0.5},
            {"trust": 0.50, "risktaking": 0.5, "patience": 0.5, "altruism": 0.5, "posrecip": 0.5, "negrecip": 0.5},
            "reasoning",
        )

    async def run_test():
        original = score.score_pair
        score.score_pair = fake_score_pair
        try:
            df_raw = pd.DataFrame(
                [
                    {
                        "prompt": "scenario",
                        "facet": "facet",
                        "chosen": "chosen",
                        "rejected": "rejected",
                        "gps_dimension": "trust",
                        "country": "USA",
                        "reasoning": "generation",
                    }
                ]
            )
            profiles = {"USA": {"z_c": {"trust": 0.35}}}
            config = CONFIG.with_overrides(qc_distance_thresh=0.0, qc_mono_epsilon=0.03)
            return await score.run_scoring_qc_export(
                df_raw,
                profiles,
                config=config,
                tracker=CostTracker(),
            )
        finally:
            score.score_pair = original

    df_final, stats = asyncio.run(run_test())
    assert len(df_final) == 1
    assert stats["pass"] == 1


def test_run_scoring_qc_export_counts_failed_scores() -> None:
    calls = 0

    async def fake_score_pair(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ConnectionError("simulated scorer outage")
        return (
            {"trust": 0.2, "risktaking": 0.5, "patience": 0.5, "altruism": 0.5, "posrecip": 0.5, "negrecip": 0.5},
            {"trust": 0.9, "risktaking": 0.2, "patience": 0.2, "altruism": 0.2, "posrecip": 0.2, "negrecip": 0.2},
            "reasoning",
        )

    async def run_test():
        original = score.score_pair
        score.score_pair = fake_score_pair
        try:
            df_raw = pd.DataFrame(
                [
                    {
                        "prompt": "scenario-1",
                        "facet": "facet",
                        "chosen": "chosen",
                        "rejected": "rejected",
                        "gps_dimension": "trust",
                        "country": "MEX",
                        "reasoning": "generation",
                    },
                    {
                        "prompt": "scenario-2",
                        "facet": "facet",
                        "chosen": "chosen",
                        "rejected": "rejected",
                        "gps_dimension": "trust",
                        "country": "MEX",
                        "reasoning": "generation",
                    },
                ]
            )
            profiles = {"MEX": {"z_c": {"trust": -0.35}}}
            return await score.run_scoring_qc_export(
                df_raw,
                profiles,
                config=CONFIG,
                tracker=CostTracker(),
            )
        finally:
            score.score_pair = original

    df_final, stats = asyncio.run(run_test())
    assert len(df_final) == 2
    assert stats["score_fail"] == 1
    assert stats["pass"] == 1
    assert set(df_final["qc_status"]) == {"pass", "score_fail"}
