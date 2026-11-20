import pytest

from sca2_datagen.profiles import build_cultural_profile, extract_gps_vector, load_cultural_profiles


def test_extract_gps_vector_for_mex(gps_path) -> None:
    profiles, df_gps = load_cultural_profiles(["MEX", "USA"], gps_path=gps_path)
    vector = extract_gps_vector(df_gps, "MEX")
    assert vector["trust"] == pytest.approx(-0.35)
    assert "profile_text" in profiles["MEX"]


def test_missing_country_raises(gps_path) -> None:
    _, df_gps = load_cultural_profiles(["MEX"], gps_path=gps_path)
    with pytest.raises(ValueError, match="Country BRA not found"):
        extract_gps_vector(df_gps, "BRA")


def test_profile_is_anonymized_gps_vector_only() -> None:
    profile = build_cultural_profile(
        {"trust": 0.1, "risktaking": 0.1, "patience": 0.1, "altruism": 0.1, "posrecip": 0.1, "negrecip": 0.1}
    )
    assert profile.startswith("GPS CULTURAL STATE VECTOR")
    assert "USA" not in profile
    assert "English only" not in profile
    assert "Do not use nationality labels" not in profile
