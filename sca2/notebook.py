"""Optional notebook client for a frozen SCA2 train/eval plan.

Existing Colab notebooks keep their Drive paths. Import this module in a
new cell if you want protocol knobs instead of hard-coded constants.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ISO3_ALIASES = {
    "US": "USA",
    "USA": "USA",
    "MX": "MEX",
    "MEX": "MEX",
}


def to_iso3(code: str) -> str:
    key = code.strip().upper()
    if key in ISO3_ALIASES:
        return ISO3_ALIASES[key]
    if len(key) == 3:
        return key
    raise ValueError(f"unrecognized country code: {code}")


def load_plan(path: str | Path) -> dict[str, Any]:
    plan_path = Path(path)
    if not plan_path.is_file():
        raise FileNotFoundError(f"plan not found: {plan_path}")
    return json.loads(plan_path.read_text(encoding="utf-8"))


def labeled_file(plan: dict[str, Any], country: str) -> Path:
    iso = to_iso3(country)
    files = plan.get("files") or {}
    if iso not in files:
        raise KeyError(f"{iso} not in plan files ({sorted(files)})")
    return Path(files[iso])


def train_knobs(plan: dict[str, Any]) -> dict[str, Any]:
    """Map a train_plan.json onto the names the notebooks already use."""

    dpo = plan.get("dpo") or {}
    lora = plan.get("lora") or {}
    split = plan.get("split") or {}
    return {
        "MODEL_NAME": plan.get("base_model"),
        "TRAIN_FRAC": split.get("train_frac"),
        "SEED": split.get("seed"),
        "beta": dpo.get("beta"),
        "learning_rate": dpo.get("learning_rate"),
        "num_train_epochs": dpo.get("num_train_epochs"),
        "per_device_train_batch_size": dpo.get("per_device_train_batch_size"),
        "gradient_accumulation_steps": dpo.get("gradient_accumulation_steps"),
        "max_length": dpo.get("max_length"),
        "lora_r": lora.get("r"),
        "lora_alpha": lora.get("alpha"),
        "lora_dropout": lora.get("dropout"),
        "lora_targets": lora.get("targets"),
        "quantization": plan.get("quantization"),
        "notebook": plan.get("notebook"),
        "execute": plan.get("execute", False),
    }


def eval_claim(plan: dict[str, Any]) -> str:
    return str(plan.get("claim_boundary") or plan.get("matched_vs_cross_means") or "")
