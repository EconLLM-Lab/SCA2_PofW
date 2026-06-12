from sca2_datagen.config import CONFIG, CostTracker, GPS_DIMENSIONS, HF_ENDPOINTS, MODEL_PRICING, WVS_ITEM_MAP


def test_gps_dimensions_has_six_entries() -> None:
    assert len(GPS_DIMENSIONS) == 6


def test_wvs_item_map_keys_preserved() -> None:
    assert "Q57" in WVS_ITEM_MAP
    assert "Q195" in WVS_ITEM_MAP
    assert WVS_ITEM_MAP["Q57"]["dim"] == "trust"


def test_config_has_three_model_fields() -> None:
    assert CONFIG.teacher_model == "hf-teacher"
    assert CONFIG.generator_model == "hf-generator"
    assert CONFIG.scorer_model == "hf-scorer"


def test_hf_endpoint_metadata_is_configured() -> None:
    assert set(HF_ENDPOINTS) == {"hf-teacher", "hf-generator", "hf-scorer"}
    assert {endpoint["role"] for endpoint in HF_ENDPOINTS.values()} == {
        "teacher",
        "generator",
        "scorer",
    }
    for endpoint in HF_ENDPOINTS.values():
        assert endpoint["base_url"].startswith("https://")
        assert endpoint["base_url"].endswith("/v1/")
        assert endpoint["base_url_env"].startswith("HF_")
        assert endpoint["base_url_env"].endswith("_ENDPOINT_URL")
        assert endpoint["api_key_env"] == "HF_TOKEN"
        assert endpoint["hourly_rate_env"].startswith("HF_")
        assert endpoint["hourly_rate_env"].endswith("_HOURLY_USD")
        assert endpoint["litellm_model"] == ""
        assert endpoint["custom_llm_provider"] == "openai"


def test_runtime_pricing_contains_only_hf_aliases() -> None:
    assert set(MODEL_PRICING) == set(HF_ENDPOINTS)


def test_config_has_reliability_defaults() -> None:
    assert CONFIG.max_retries >= 0
    assert CONFIG.json_parse_retries >= 0
    assert CONFIG.cold_start_min_wait_s > 0
    assert CONFIG.server_error_min_wait_s > 0
    assert CONFIG.retry_backoff_min_s > 0
    assert CONFIG.retry_backoff_max_s >= CONFIG.retry_backoff_min_s
    assert CONFIG.request_timeout_s > 0
    assert 0.0 <= CONFIG.max_error_rate_for_continue <= 1.0


def test_config_has_supported_sample_size_policy() -> None:
    assert CONFIG.sample_size_policy in {"fail_fast", "skip_unavailable", "degrade_to_feasible"}


def test_endpoint_runtime_cost_uses_hourly_rate_env(monkeypatch) -> None:
    monkeypatch.setenv("HF_TEACHER_HOURLY_USD", "1.50")
    monkeypatch.setenv("HF_GENERATOR_HOURLY_USD", "2.00")
    monkeypatch.setenv("HF_SCORER_HOURLY_USD", "0.50")

    summary = CostTracker().summary(elapsed_seconds=1800)

    assert summary["endpoint_runtime_cost"]["total_cost_usd"] == 2.0
    assert summary["total_cost_usd"] == 2.0


def test_endpoint_runtime_cost_missing_rates_are_nonfatal(monkeypatch) -> None:
    monkeypatch.delenv("HF_TEACHER_HOURLY_USD", raising=False)
    monkeypatch.delenv("HF_GENERATOR_HOURLY_USD", raising=False)
    monkeypatch.delenv("HF_SCORER_HOURLY_USD", raising=False)

    summary = CostTracker().summary(elapsed_seconds=1800)

    runtime_cost = summary["endpoint_runtime_cost"]
    assert runtime_cost["total_cost_usd"] == 0.0
    assert runtime_cost["rates_configured"] is False
    assert set(runtime_cost["missing_rate_envs"]) == {
        "HF_TEACHER_HOURLY_USD",
        "HF_GENERATOR_HOURLY_USD",
        "HF_SCORER_HOURLY_USD",
    }
