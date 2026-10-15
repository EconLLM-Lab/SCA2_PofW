"""Durable stage cache: a killed run resumes without paying for finished requests."""
import asyncio
import json

from sca2_datagen import generate
from sca2_datagen.config import CONFIG, CostTracker, GPS_DIMENSIONS
from sca2_datagen.stage_cache import StageCache
from tests.conftest import fake_response

FACETS = '{"facets": ["f1", "f2", "f3", "f4", "f5"]}'


def _fake(calls, fail_after=None):
    async def fake(block, tracker, **kwargs):
        calls.append(block)
        if fail_after is not None and len(calls) > fail_after:
            raise RuntimeError("process killed")
        if block == "C:facets":
            return fake_response(FACETS)
        n = len(calls)
        return fake_response(json.dumps({"scenarios": [f"s{n}a", f"s{n}b"]}))
    return fake


def _run(config, calls, fail_after=None):
    original = generate.utils.tracked_completion
    generate.utils.tracked_completion = _fake(calls, fail_after)
    try:
        return asyncio.run(generate.generate_scenarios(
            "trust", GPS_DIMENSIONS["trust"], 10,
            config=config.with_overrides(scenario_batch_size=2), tracker=CostTracker()))
    finally:
        generate.utils.tracked_completion = original


def test_cache_roundtrip_survives_reopen(tmp_path):
    p = tmp_path / "c.jsonl"
    c = StageCache(p)
    c.put(("scenarios", "trust", "f1", 1), ["a", "b"])
    assert StageCache(p).get(("scenarios", "trust", "f1", 1)) == ["a", "b"]
    assert StageCache(p).get(("scenarios", "trust", "f1", 2)) is None


def test_cache_ignores_a_torn_last_line(tmp_path):
    p = tmp_path / "c.jsonl"
    StageCache(p).put(("facets", "trust"), ["x"])
    with p.open("a") as fh:
        fh.write('{"key": ["facets", "risk')          # killed mid-write
    assert StageCache(p).get(("facets", "trust")) == ["x"]


def test_killed_scenario_run_resumes_without_repeating_calls(tmp_path):
    cfg = CONFIG.with_overrides(stage_cache_path=str(tmp_path / "cache.jsonl"))
    first: list[str] = []
    try:
        _run(cfg, first, fail_after=3)                    # facets + 2 batches, then dies
    except RuntimeError:
        pass
    second: list[str] = []
    rows = _run(cfg, second)
    assert len(rows) == 10
    assert "C:facets" not in second                      # facets reused, not redrawn
    assert len(second) == 5 - 2                          # 5 batches, 2 already cached
    third: list[str] = []
    assert _run(cfg, third) == rows and third == []      # fully cached: no calls


def test_no_cache_path_means_no_cache_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls: list[str] = []
    _run(CONFIG, calls)
    assert list(tmp_path.iterdir()) == []


def test_killed_triplet_stage_resumes_from_cache(tmp_path, monkeypatch):
    calls: list[str] = []
    budget = {"left": 3}

    async def fake_scen(dim_key, dim_info, n, config=CONFIG, tracker=None, use_anchors=False, sem=None):
        return [{"facet": "f", "prompt": f"scenario-{dim_key}"}]

    async def fake_triplet(prompt, facet, dim_key, dim_info, sem, config=CONFIG, tracker=None,
                           use_anchors=False):
        if budget["left"] <= 0:
            raise RuntimeError("process killed")
        budget["left"] -= 1
        calls.append(dim_key)
        return {"response_a": f"{prompt} hi", "response_b": f"{prompt} lo", "reasoning": "r"}

    monkeypatch.setattr(generate, "generate_scenarios", fake_scen)
    monkeypatch.setattr(generate, "safe_generate_triplet", fake_triplet)
    cfg = CONFIG.with_overrides(stage_cache_path=str(tmp_path / "cache.jsonl"), concurrency=1)
    profiles = {"USA": {"profile_text": "", "z_c": {k: 0.1 for k in GPS_DIMENSIONS}}}
    try:
        asyncio.run(generate.run_teacher_pipeline(profiles, ["USA"], config=cfg, tracker=CostTracker()))
    except RuntimeError:
        pass
    done_first = len(calls)
    assert 0 < done_first < len(GPS_DIMENSIONS)
    budget["left"] = 100
    df, _ = asyncio.run(generate.run_teacher_pipeline(profiles, ["USA"], config=cfg,
                                                     tracker=CostTracker()))
    assert len(df) == len(GPS_DIMENSIONS)
    assert len(calls) == len(GPS_DIMENSIONS)          # each triplet generated exactly once
