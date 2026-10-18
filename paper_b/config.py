"""Paper B — frozen protocol constants.

Source of truth: Hermes/Projects/SCA2/PAPER_B_PROTOCOL_DRAFT.md (frozen 2026-10-09).
Do not change a value here without a dated amendment to that file.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------- cohort (42)
# GPS ∩ WVS7 intersection; enumerated by data/wvs_eval_full/*_WVS_wave7.parquet.
COHORT = [
    "ARG", "AUS", "BGD", "BOL", "BRA", "CAN", "CHL", "CHN", "COL", "CZE",
    "DEU", "EGY", "GBR", "GRC", "GTM", "IDN", "IND", "IRN", "IRQ", "JOR",
    "JPN", "KAZ", "KEN", "KOR", "MAR", "MEX", "NGA", "NIC", "NLD", "PAK",
    "PER", "PHL", "ROU", "RUS", "SRB", "THA", "TUR", "UKR", "USA", "VEN",
    "VNM", "ZWE",
]
assert len(COHORT) == 42, len(COHORT)

# ---------------------------------------------------------------- shared bank
BANK_DIR = REPO / "synthetic_generation" / "outputs" / "gps_sign_relabel_all"
BANK_RUN_ID = "gps_sign_relabel_all_20260816_004545Z"
N_ROWS = 658
LABELING_RULE = "deterministic_sign"
BANK_FILE = "D_syn_{cc}.jsonl"

# ---------------------------------------------------------------- split
TRAIN_FRAC = 0.80
SEED = 42
TRAIN_ROWS = int(N_ROWS * TRAIN_FRAC)   # 526 for cohort 1; protocol_bank2 recomputes it
UNITS = "countries"                      # protocol_bank2 may switch to "profiles"
# Near-zero refits (card T5): protocol_bank2.apply fills these under SCA2_PB_NEARZERO. The defaults exist so that
# a module reload always resets them: a leaked per-unit n_train would change the cohort-1 run-record check.
EXPECTED_N_TRAIN: dict = {}              # unit -> training rows; empty means TRAIN_ROWS for every unit
NEARZERO_DIR = None                      # directory of the reduced banks, or None


# ---------------------------------------------------------------- reference pass
MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"
MAX_PROMPT_TOKENS = 256
MAX_COMPLETION_TOKENS = 256
PROMPT_FORMAT_VERSION = "questionnaire_situation_v1"

# ---------------------------------------------------------------- training (frozen)
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LORA_TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj"]
DPO_BETA = 0.1
LEARNING_RATE = 1e-4
NUM_TRAIN_EPOCHS = 1
MAX_LENGTH = 768
PER_DEVICE_BATCH_SIZE = 1
GRADIENT_ACCUMULATION_STEPS = 16

# ---------------------------------------------------------------- frozen decision (B)
NEAR_ZERO = 0.10

# ---------------------------------------------------------------- paths
# On Colab set SCA2_PB_DATA_ROOT=/content/drive/MyDrive/SCA2_paper_b
DATA_ROOT = Path(os.environ.get("SCA2_PB_DATA_ROOT", REPO / "data" / "paper_b"))
PREPARED_DIR = DATA_ROOT / "prepared"        # {cc}_train.jsonl, {cc}_eval.jsonl, {cc}_train_with_ref.jsonl
ADAPTER_DIR = DATA_ROOT / "adapters"         # one subdir per country
REF_CACHE_FILE = DATA_ROOT / "shared_reference_logps.jsonl"
REF_MANIFEST_FILE = DATA_ROOT / "shared_reference_logps_manifest.json"
RUN_MANIFEST_FILE = DATA_ROOT / "run_manifest.json"
LOG_DIR = DATA_ROOT / "logs"

# Durable artifact bus: adapters are uploaded here straight from the VM via HTTPS,
# independent of the Colab Drive FUSE (which uploads lazily and has lost data twice).
HF_ADAPTER_REPO = "Bonorinoa/SCA2-paper-b-adapters"
# Cohort 1 upload prefix. protocol_bank2.apply overrides this in memory only.
HF_ADAPTER_PREFIX = "adapters"


def hub_adapter_path(country_code: str) -> str:
    import protocol_bank2
    return protocol_bank2.hub_adapter_path_from_prefix(HF_ADAPTER_PREFIX, country_code)


def _maybe_apply_bank2() -> None:
    if os.environ.get("SCA2_PB_PROTOCOL") != "bank2":
        return
    import sys
    import protocol_bank2
    protocol_bank2.apply(sys.modules[__name__])


_maybe_apply_bank2()
