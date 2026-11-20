from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest


def fake_response(content: str, prompt_tokens: int = 100, completion_tokens: int = 50) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )


@pytest.fixture
def gps_path(tmp_path: Path) -> Path:
    df = pd.DataFrame(
        [
            {
                "isocode": "MEX",
                "trust": -0.35,
                "risktaking": -0.14,
                "patience": -0.11,
                "altruism": -0.81,
                "posrecip": -1.03,
                "negrecip": -0.11,
            },
            {
                "isocode": "USA",
                "trust": 0.15,
                "risktaking": 0.12,
                "patience": 0.81,
                "altruism": 0.41,
                "posrecip": 0.20,
                "negrecip": 0.01,
            },
            {
                "isocode": "ARG",
                "trust": -0.05,
                "risktaking": 0.26,
                "patience": -0.22,
                "altruism": -0.18,
                "posrecip": -0.12,
                "negrecip": 0.31,
            },
            {
                "isocode": "SWE",
                "trust": 0.74,
                "risktaking": 0.33,
                "patience": 0.45,
                "altruism": 0.29,
                "posrecip": 0.18,
                "negrecip": -0.27,
            },
        ]
    )
    path = tmp_path / "country_gps.dta"
    df.to_stata(path, write_index=False)
    return path


@pytest.fixture
def wvs_path(tmp_path: Path) -> Path:
    df = pd.DataFrame(
        [
            {"B_COUNTRY_ALPHA": "MEX", "Q57": 1, "Q13": 1},
            {"B_COUNTRY_ALPHA": "MEX", "Q57": 0, "Q13": 1},
            {"B_COUNTRY_ALPHA": "USA", "Q57": 1, "Q13": 0},
        ]
    )
    path = tmp_path / "WVS_wave7.dta"
    df.to_stata(path, write_index=False)
    return path
