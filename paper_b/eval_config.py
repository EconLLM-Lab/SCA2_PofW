"""Paper B — evaluation / scoring constants.

These are the WVS readout constants. They mirror
`DPO_eval_WVS/DPO_survey_distribution_evaluation.ipynb` exactly so the cohort
scorer reproduces the Paper A readout.

They are deliberately NOT part of `paper_b/config.py`, which holds the frozen
*training* protocol and must not drift. Training freezes live there; readout
freezes live here.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# ------------------------------------------------------------------ inputs
QUESTION_MAP_FILE = REPO / "DPO_eval_WVS" / "question_map_wvs_edited.csv"
WVS_DIR = REPO / "data" / "wvs_eval_full"  # {CC}_WVS_wave7.parquet, the 42
BASE_MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"

# The parquet carries both `weight` and `W_WEIGHT`; in the shipped files the two
# columns are identical (verified on CHN, 2026-10-10). The Paper A notebook used
# `weight`, so we do too.
WEIGHT_COLUMN = "weight"
USE_SURVEY_WEIGHTS = True

# ------------------------------------------------------------------ readout
EVAL_MAX_PROMPT_TOKENS = 768
EVAL_MAX_COMPLETION_TOKENS = 16
COMPLETION_PREFIX = " "          # teacher-forced completion is " " + code
OPTION_SCORE_TEMPERATURE = 1.0
LENGTH_NORMALIZE_OPTION_LOGPROBS = False
# Llama-3.1's chat template inserts this date unless the caller pins it.
# The archived Paper A prompts contain this exact string. Leaving it unset
# lets a newer transformers build substitute today's date and change logprobs.
ARCHIVE_CHAT_DATE = "26 Jul 2024"

# Deterministic single answer per question, saved alongside the option scores
# (not used in any metric). Kept for parity with the Paper A artifacts.
SAVE_GENERATED_ANSWERS = True
GENERATION_MAX_NEW_TOKENS = 32
GENERATION_DO_SAMPLE = False

# ------------------------------------------------------------------ item grid
INCLUDE_NUMERIC_OPEN = True
NUMERIC_VALID_RANGES = {"Q261": (1900, 2010), "Q262": (15, 110)}
MAX_NUMERIC_SUPPORT = 150
NOMINAL_QUESTION_IDS = {"Q174", "Q260"}
EPS = 1e-12

# ------------------------------------------------------------------ paths
# On Colab set SCA2_PB_DATA_ROOT=/content/drive/MyDrive/SCA2_paper_b
DATA_ROOT = Path(os.environ.get("SCA2_PB_DATA_ROOT", REPO / "data" / "paper_b"))
ADAPTER_DIR = DATA_ROOT / "adapters"
SCORE_DIR = DATA_ROOT / "scores"
SCORE_MANIFEST_FILE = SCORE_DIR / "score_manifest.json"

# Archived Paper A artifacts, used only by the reproduction gates.
ARCHIVE_DIR = REPO / "data" / "phase2" / "raw" / "wvs" / "ksenias_base8"

# ------------------------------------------------------------------ adapter source
# Adapters land on the HF hub dataset repo (`config.HF_ADAPTER_REPO`, path
# `adapters/<CC>/`) straight from the training VM. The Drive copy under
# `SCA2_paper_b/adapters/` is a fallback: it is stale for any country retrained
# after the hub change, and it has lost data twice. Neither source is complete
# while a run is live, so resolution is a UNION with the hub tried first.
HF_ADAPTER_REPO_TYPE = "dataset"


def _default_adapter_cache() -> Path:
    # a local scratch dir; never the Drive FUSE, which is what fails
    if Path("/content").is_dir():
        return Path("/content/adapter_cache")
    return DATA_ROOT / "adapter_cache"


ADAPTER_CACHE_DIR = Path(os.environ.get("SCA2_PB_ADAPTER_CACHE", str(_default_adapter_cache())))

# ------------------------------------------------------------------ persona arm
# Country names used only by the country-named persona prompt.
COUNTRY_NAMES = {
    "ARG": "Argentina", "AUS": "Australia", "BGD": "Bangladesh", "BOL": "Bolivia",
    "BRA": "Brazil", "CAN": "Canada", "CHL": "Chile", "CHN": "China",
    "COL": "Colombia", "CZE": "Czechia", "DEU": "Germany", "EGY": "Egypt",
    "GBR": "Great Britain", "GRC": "Greece", "GTM": "Guatemala", "IDN": "Indonesia",
    "IND": "India", "IRN": "Iran", "IRQ": "Iraq", "JOR": "Jordan",
    "JPN": "Japan", "KAZ": "Kazakhstan", "KEN": "Kenya", "KOR": "South Korea",
    "MAR": "Morocco", "MEX": "Mexico", "NGA": "Nigeria", "NIC": "Nicaragua",
    "NLD": "the Netherlands", "PAK": "Pakistan", "PER": "Peru", "PHL": "the Philippines",
    "ROU": "Romania", "RUS": "Russia", "SRB": "Serbia", "THA": "Thailand",
    "TUR": "Turkey", "UKR": "Ukraine", "USA": "the United States", "VEN": "Venezuela",
    "VNM": "Vietnam", "ZWE": "Zimbabwe",
}
