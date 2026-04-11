import asyncio

from sca2_datagen.config import CONFIG, CostTracker, GPS_DIMENSIONS
from sca2_datagen import generate


async def _run_generate_scenarios() -> tuple[list[dict[str, str]], list[str]]:
    prompts: list[str] = []

    async def fake_tracked_completion(block, tracker, **kwargs):
        prompts.append(kwargs["messages"][-1]["content"])
        if block == "C:facets":
            return __import__("tests.conftest", fromlist=["fake_response"]).fake_response(
                '{"facets": ["institutional trust", "stranger trust", "workplace trust", "market trust"]}'
            )
        return __import__("tests.conftest", fromlist=["fake_response"]).fake_response(
            '{"scenarios": ["Scenario one", "Scenario two"]}'
        )

    original = generate.utils.tracked_completion
    generate.utils.tracked_completion = fake_tracked_completion
    try:
        rows = await generate.generate_scenarios(
            "trust",
            GPS_DIMENSIONS["trust"],
            4,
            config=CONFIG,
            tracker=CostTracker(),
        )
    finally:
        generate.utils.tracked_completion = original
    return rows, prompts


def test_generate_scenarios_uses_facets_and_exclusions() -> None:
    rows, prompts = asyncio.run(_run_generate_scenarios())
    assert rows
    assert any("4 to 6 distinct sub-dimensions or facets" in prompt for prompt in prompts)
    assert any("Do NOT generate scenarios requiring numerical calculations" in prompt for prompt in prompts)


def test_generate_pair_prompt_forbids_nationality_self_references() -> None:
    prompts: list[str] = []

    async def fake_tracked_completion(block, tracker, **kwargs):
        prompts.append(kwargs["messages"][-1]["content"])
        return __import__("tests.conftest", fromlist=["fake_response"]).fake_response(
            '```json {"response_a": "A", "response_b": "B", "reasoning": "R"} ```'
        )

    async def run_test() -> None:
        original = generate.utils.tracked_completion
        generate.utils.tracked_completion = fake_tracked_completion
        try:
            sem = asyncio.Semaphore(1)
            payload = await generate.generate_pair(
                "A scenario",
                "stranger trust",
                "trust",
                GPS_DIMENSIONS["trust"],
                "MEX",
                "Profile text",
                {"trust": -0.35},
                sem,
                config=CONFIG,
                tracker=CostTracker(),
            )
        finally:
            generate.utils.tracked_completion = original
        assert payload["response_a"] == "A"

    asyncio.run(run_test())
    assert any("Do NOT use phrases like 'As a Mexican' or 'As an American'" in prompt for prompt in prompts)
    assert any("written in English" in prompt for prompt in prompts)
