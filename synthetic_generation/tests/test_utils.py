from __future__ import annotations

import asyncio

import pytest

from sca2_datagen.config import CONFIG, CostTracker, HF_ENDPOINTS
from sca2_datagen import utils


def test_tracked_completion_routes_hf_alias_to_openai_compatible_endpoint(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        return __import__("tests.conftest", fromlist=["fake_response"]).fake_response("{}")

    monkeypatch.setenv("HF_TOKEN", "test-token")
    monkeypatch.setattr(utils, "acompletion", fake_acompletion)

    async def run_test() -> dict[str, object]:
        tracker = CostTracker()
        await utils.tracked_completion(
            "test:block",
            tracker,
            config=CONFIG,
            model="hf-teacher",
            messages=[{"role": "user", "content": "Return {}"}],
        )
        return tracker.summary()

    summary = asyncio.run(run_test())
    endpoint = HF_ENDPOINTS["hf-teacher"]
    assert captured["model"] == ""
    assert captured["base_url"] == endpoint["base_url"]
    assert captured["api_key"] == "test-token"
    assert captured["custom_llm_provider"] == "openai"
    assert "hf-teacher" in summary["models"]


def test_parse_json_response_accepts_first_json_object_with_trailing_text() -> None:
    response = __import__("tests.conftest", fromlist=["fake_response"]).fake_response(
        '{"scenarios": ["one"]}\nNote: done'
    )
    assert utils.parse_json_response(response) == {"scenarios": ["one"]}


def test_parse_json_response_repairs_trailing_commas() -> None:
    response = __import__("tests.conftest", fromlist=["fake_response"]).fake_response(
        '{"scenarios": ["one", "two",],}'
    )
    assert utils.parse_json_response(response) == {"scenarios": ["one", "two"]}


def test_tracked_json_completion_retries_malformed_json(monkeypatch) -> None:
    responses = [
        __import__("tests.conftest", fromlist=["fake_response"]).fake_response('{"scenarios": ["broken"'),
        __import__("tests.conftest", fromlist=["fake_response"]).fake_response('{"scenarios": ["ok"]}'),
    ]

    async def fake_acompletion(**kwargs):
        return responses.pop(0)

    monkeypatch.setenv("HF_TOKEN", "test-token")
    monkeypatch.setattr(utils, "acompletion", fake_acompletion)

    async def run_test() -> dict:
        return await utils.tracked_json_completion(
            "test:block",
            CostTracker(),
            config=CONFIG,
            model="hf-teacher",
            messages=[{"role": "user", "content": "Return JSON"}],
        )

    assert asyncio.run(run_test()) == {"scenarios": ["ok"]}


def test_tracked_completion_requires_hf_token(monkeypatch) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)

    async def run_test() -> None:
        await utils.tracked_completion(
            "test:block",
            CostTracker(),
            config=CONFIG,
            model="hf-teacher",
            messages=[{"role": "user", "content": "Return {}"}],
        )

    with pytest.raises(RuntimeError, match="HF_TOKEN"):
        asyncio.run(run_test())


def test_tracked_completion_rejects_non_hf_models(monkeypatch) -> None:
    monkeypatch.setenv("HF_TOKEN", "test-token")

    async def run_test() -> None:
        await utils.tracked_completion(
            "test:block",
            CostTracker(),
            config=CONFIG,
            model="unsupported-model-alias",
            messages=[{"role": "user", "content": "Return {}"}],
        )

    with pytest.raises(ValueError, match="Unsupported model"):
        asyncio.run(run_test())
