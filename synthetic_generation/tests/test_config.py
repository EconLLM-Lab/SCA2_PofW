from sca2_datagen.config import CONFIG, GPS_DIMENSIONS, WVS_ITEM_MAP


def test_gps_dimensions_has_six_entries() -> None:
    assert len(GPS_DIMENSIONS) == 6


def test_wvs_item_map_keys_preserved() -> None:
    assert "Q57" in WVS_ITEM_MAP
    assert "Q195" in WVS_ITEM_MAP
    assert WVS_ITEM_MAP["Q57"]["dim"] == "trust"


def test_config_has_three_model_fields() -> None:
    assert CONFIG.teacher_model
    assert CONFIG.generator_model
    assert CONFIG.scorer_model
