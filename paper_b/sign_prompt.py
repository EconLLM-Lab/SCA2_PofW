"""Sign-profile prompts: same six signs, no country, no magnitude.

Dimension order matches synthetic_generation GPS_DIMENSIONS / verify_gates.DIMS.
A sign is positive when z >= 0, the training rule, not numpy.sign.
"""
from __future__ import annotations

import json
from pathlib import Path

DIMS = ["trust", "risktaking", "patience", "altruism", "posrecip", "negrecip"]

# Names that must not appear in a primary sign-profile prompt.
# ISO codes are checked as whole tokens. Country names are checked as substrings.
ISO_CODES = [
    "ARG", "AUS", "BGD", "BOL", "BRA", "CAN", "CHL", "CHN", "COL", "CZE",
    "DEU", "EGY", "GBR", "GRC", "GTM", "IDN", "IND", "IRN", "IRQ", "JOR",
    "JPN", "KAZ", "KEN", "KOR", "MAR", "MEX", "NGA", "NIC", "NLD", "PAK",
    "PER", "PHL", "ROU", "RUS", "SRB", "THA", "TUR", "UKR", "USA", "VEN",
    "VNM", "ZWE",
]
COUNTRY_NAMES = [
    "Argentina", "Australia", "Bangladesh", "Bolivia", "Brazil", "Canada",
    "Chile", "China", "Colombia", "Czechia", "Germany", "Egypt",
    "Great Britain", "Greece", "Guatemala", "Indonesia", "India", "Iran",
    "Iraq", "Jordan", "Japan", "Kazakhstan", "Kenya", "South Korea",
    "Morocco", "Mexico", "Nigeria", "Nicaragua", "the Netherlands",
    "Pakistan", "Peru", "the Philippines", "Romania", "Russia", "Serbia",
    "Thailand", "Turkey", "Ukraine", "the United States", "Venezuela",
    "Vietnam", "Zimbabwe", "America", "American", "Mexican", "Chinese",
]


def sign_word(z_value: float) -> str:
    if z_value != z_value:  # NaN
        raise ValueError(f"non-finite z: {z_value}")
    return "positive" if z_value >= 0 else "negative"


def profile_id(signs: dict[str, str]) -> str:
    missing = [d for d in DIMS if d not in signs]
    if missing:
        raise ValueError(f"profile missing dimensions: {missing}")
    return "_".join("1" if signs[d] == "positive" else "0" for d in DIMS)


def sign_prompt(signs: dict[str, str]) -> str:
    lines = [f"{dim}: {signs[dim]}" for dim in DIMS]
    return (
        "Your preference signs are fixed. They are not a country and not a number.\n"
        + "\n".join(lines)
        + "\nAnswer this questionnaire as an individual person with those signs."
    )


def leak_hits(text: str) -> list[str]:
    """Return forbidden tokens found in a primary prompt."""
    hits = []
    folded = text.casefold()
    for name in COUNTRY_NAMES:
        if name.casefold() in folded:
            hits.append(name)
    tokens = set(text.replace(":", " ").replace("\n", " ").split())
    for code in ISO_CODES:
        if code in tokens:
            hits.append(code)
    return hits


def profiles_from_gps(z_by_country: dict[str, dict[str, float]],
                      countries: list[str]) -> list[dict]:
    """One row per distinct sign profile. Member countries are metadata only."""
    grouped: dict[str, dict] = {}
    for cc in countries:
        vector = z_by_country[cc]
        signs = {dim: sign_word(float(vector[dim])) for dim in DIMS}
        pid = profile_id(signs)
        prompt = sign_prompt(signs)
        hits = leak_hits(prompt)
        if hits:
            raise ValueError(f"sign prompt leaked {hits}")
        row = grouped.get(pid)
        if row is None:
            grouped[pid] = {
                "profile_id": pid,
                "signs": signs,
                "prompt": prompt,
                "members": [cc],
            }
        else:
            row["members"].append(cc)
    return [grouped[k] for k in sorted(grouped)]


def load_gps_json(path: Path) -> dict[str, dict[str, float]]:
    raw = json.loads(path.read_text())
    return {cc: {dim: float(vals[dim]) for dim in DIMS} for cc, vals in raw.items()}
