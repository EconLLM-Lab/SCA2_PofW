"""sca2 train — freeze a DPO/QLoRA plan. Does not launch GPU training."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .protocol import load_protocol, repo_root, resolve_repo_path
from .runs import format_receipt, new_run_id, prepare_run_dir, write_receipt


def _count_jsonl(path: Path) -> int:
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def resolve_country_files(data_dir: Path, countries: list[str]) -> dict[str, Path]:
    found: dict[str, Path] = {}
    missing: list[str] = []
    for iso in countries:
        path = data_dir / f"D_syn_{iso}.jsonl"
        if path.is_file():
            found[iso] = path
        else:
            missing.append(iso)
    if missing:
        raise FileNotFoundError(
            "missing labeled files for: " + ", ".join(missing) + f" (looked in {data_dir})"
        )
    return found


def default_countries(data_dir: Path) -> list[str]:
    names = sorted(p.stem.removeprefix("D_syn_") for p in data_dir.glob("D_syn_*.jsonl"))
    return names


def build_train_plan(
    protocol: dict[str, Any],
    *,
    countries: list[str],
    files: dict[str, Path],
) -> dict[str, Any]:
    train = protocol["train"]
    return {
        "estimator": train.get("estimator"),
        "base_model": train.get("base_model"),
        "notebook": train.get("notebook"),
        "countries": countries,
        "n_pairs": {iso: _count_jsonl(path) for iso, path in files.items()},
        "files": {iso: str(path) for iso, path in files.items()},
        "split": {"train_frac": train.get("train_frac"), "seed": train.get("seed")},
        "dpo": {
            "beta": train.get("beta"),
            "learning_rate": train.get("learning_rate"),
            "num_train_epochs": train.get("num_train_epochs"),
            "per_device_train_batch_size": train.get("per_device_train_batch_size"),
            "gradient_accumulation_steps": train.get("gradient_accumulation_steps"),
            "max_length": train.get("max_length"),
        },
        "lora": {
            "r": train.get("lora_r"),
            "alpha": train.get("lora_alpha"),
            "dropout": train.get("lora_dropout"),
            "targets": train.get("lora_targets"),
        },
        "quantization": train.get("quantization"),
        "execute": False,
        "note": (
            "This is a frozen plan. GPU training still lives in the notebook. "
            "Passing --execute is refused until a local trainer is wired."
        ),
    }


def run_train(
    protocol_path: str | Path,
    *,
    countries: list[str] | None = None,
    data_dir: Path | None = None,
    execute: bool = False,
    runs_root: Path | None = None,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    if execute:
        raise RuntimeError(
            "Refusing to execute training. The notebook "
            f"{protocol['train'].get('notebook')} is still the GPU path. "
            "sca2 train writes a plan so the knobs are frozen first."
        )

    root = repo_root()
    labeled = Path(data_dir) if data_dir else resolve_repo_path(
        protocol["train"].get("data_dir", "synthetic_generation/outputs/gps_sign_relabel_all"),
        root,
    )
    chosen = countries or default_countries(labeled)
    if not chosen:
        raise FileNotFoundError(f"no D_syn_*.jsonl files in {labeled}")
    files = resolve_country_files(labeled, chosen)
    plan = build_train_plan(protocol, countries=chosen, files=files)

    run_id = new_run_id(str(protocol["name"]), stage="train")
    run_dir = prepare_run_dir(
        Path(runs_root) if runs_root else root / "runs",
        run_id,
        protocol,
    )
    (run_dir / "train_plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "run_id": run_id,
        "stage": "train",
        "status": "planned",
        "protocol_name": protocol["name"],
        "protocol_hash": protocol["_hash"],
        "protocol_path": protocol["_path"],
        "countries": len(chosen),
        "rows": sum(plan["n_pairs"].values()),
        "rule": protocol["train"].get("estimator"),
        "out": str(run_dir / "train_plan.json"),
        "base_model": protocol["train"].get("base_model"),
        "notebook": protocol["train"].get("notebook"),
    }
    write_receipt(run_dir, receipt)
    print(format_receipt(receipt))
    print(f"plan      {receipt['out']}")
    print(f"countries {', '.join(chosen)}")
    return receipt
