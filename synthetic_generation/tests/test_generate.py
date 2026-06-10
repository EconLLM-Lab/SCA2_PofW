import asyncio
import inspect

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


def test_generate_triplet_has_no_country_or_z_arguments() -> None:
    signature = inspect.signature(generate.generate_triplet)
    assert "country" not in signature.parameters
    assert "z_c" not in signature.parameters
    assert "profile_text" not in signature.parameters


def test_generate_triplet_prompt_is_country_independent() -> None:
    prompts: list[str] = []
    message_roles: list[list[str]] = []

    async def fake_tracked_completion(block, tracker, **kwargs):
        prompts.append(kwargs["messages"][-1]["content"])
        message_roles.append([message["role"] for message in kwargs["messages"]])
        return __import__("tests.conftest", fromlist=["fake_response"]).fake_response(
            '{"response_a": "High trust option", "response_b": "Low trust option", "reasoning": "R"}'
        )

    async def run_test() -> None:
        original = generate.utils.tracked_completion
        generate.utils.tracked_completion = fake_tracked_completion
        try:
            payload = await generate.generate_triplet(
                "A scenario",
                "stranger trust",
                "trust",
                GPS_DIMENSIONS["trust"],
                asyncio.Semaphore(1),
                config=CONFIG,
                tracker=CostTracker(),
            )
        finally:
            generate.utils.tracked_completion = original
        assert payload["response_a"] == "High trust option"

    asyncio.run(run_test())
    assert message_roles == [["user"]]
    assert not any("MEX" in prompt or "USA" in prompt or "z-score" in prompt for prompt in prompts)
    assert any("Do NOT use phrases like 'As a Mexican' or 'As an American'" in prompt for prompt in prompts)


def test_run_teacher_pipeline_reuses_fixed_options_and_only_selects_per_country(monkeypatch) -> None:
    async def fake_generate_scenarios(dim_key, dim_info, n, config=CONFIG, tracker=None):
        return [{"facet": "f", "prompt": f"scenario-{dim_key}"}]

    triplet_calls: list[tuple[str, str]] = []
    selection_calls: list[tuple[str, str, str, str, str]] = []

    async def fake_safe_generate_triplet(prompt, facet, dim_key, dim_info, sem, config=CONFIG, tracker=None):
        triplet_calls.append((dim_key, prompt))
        return {
            "response_a": f"{prompt} :: high {dim_key}",
            "response_b": f"{prompt} :: low {dim_key}",
            "reasoning": "fixed options",
        }

    async def fake_safe_select_triplet_for_profile(
        scenario,
        facet,
        dim_key,
        dim_info,
        response_a,
        response_b,
        country,
        profile_text,
        z_c,
        sem,
        config=CONFIG,
        tracker=None,
    ):
        selection_calls.append((country, dim_key, response_a, response_b, profile_text))
        chosen_option = "A" if z_c[dim_key] >= 0 else "B"
        return {
            "chosen_option": chosen_option,
            "chosen": response_a if chosen_option == "A" else response_b,
            "rejected": response_b if chosen_option == "A" else response_a,
            "reasoning": "selected from fixed options",
        }

    monkeypatch.setattr(generate, "generate_scenarios", fake_generate_scenarios)
    monkeypatch.setattr(generate, "safe_generate_triplet", fake_safe_generate_triplet)
    monkeypatch.setattr(generate, "safe_select_triplet_for_profile", fake_safe_select_triplet_for_profile)

    profiles = {
        "MEX": {
            "profile_text": "Mexico profile",
            "z_c": {key: -0.1 for key in GPS_DIMENSIONS},
        },
        "USA": {
            "profile_text": "USA profile",
            "z_c": {key: 0.1 for key in GPS_DIMENSIONS},
        },
    }
    df_raw, _ = asyncio.run(
        generate.run_teacher_pipeline(
            profiles,
            ["MEX", "USA"],
            config=CONFIG.with_overrides(scenarios_per_dim=1),
            tracker=CostTracker(),
        )
    )

    assert len(triplet_calls) == len(GPS_DIMENSIONS)
    assert len(selection_calls) == len(GPS_DIMENSIONS) * 2
    for _, group in df_raw.groupby(["gps_dimension", "prompt"], sort=True):
        assert group["response_a"].nunique() == 1
        assert group["response_b"].nunique() == 1
        assert set(group["country"]) == {"MEX", "USA"}
        assert set(group["chosen_option"]) == {"A", "B"}
    assert all(call[4] in {"Mexico profile", "USA profile"} for call in selection_calls)
