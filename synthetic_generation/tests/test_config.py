from sca2_datagen.config import CONFIG, GPS_DIMENSIONS, HF_ENDPOINTS, MODEL_PRICING, WVS_ITEM_MAP


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
    for endpoint in HF_ENDPOINTS.values():
        assert endpoint["base_url"].startswith("https://")
        assert endpoint["base_url"].endswith("/v1/")
        assert endpoint["api_key_env"] == "HF_TOKEN"
        assert endpoint["litellm_model"] == ""
        assert endpoint["custom_llm_provider"] == "openai"


def test_runtime_pricing_contains_only_hf_aliases() -> None:
    assert set(MODEL_PRICING) == set(HF_ENDPOINTS)


def test_config_has_reliability_defaults() -> None:
    assert CONFIG.max_retries >= 0
    assert CONFIG.retry_backoff_min_s > 0
    assert CONFIG.retry_backoff_max_s >= CONFIG.retry_backoff_min_s
    assert CONFIG.request_timeout_s > 0
    assert 0.0 <= CONFIG.max_error_rate_for_continue <= 1.0


def test_config_has_supported_sample_size_policy() -> None:
    assert CONFIG.sample_size_policy in {"fail_fast", "skip_unavailable", "degrade_to_feasible"}
