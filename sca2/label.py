"""sca2 label — deterministic sign-relabel of a shared A/B bank."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .protocol import load_protocol, repo_root, resolve_repo_path
from .runs import format_receipt, new_run_id, prepare_run_dir, write_receipt


def _ensure_datagen_on_path() -> None:
    datagen_root = repo_root() / "synthetic_generation"
    if str(datagen_root) not in sys.path:
        sys.path.insert(0, str(datagen_root))


def run_label(
    protocol_path: str | Path,
    *,
    output_dir: Path | None = None,
    runs_root: Path | None = None,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    generation = protocol["generation"]
    if generation.get("labeling") != "deterministic_sign":
        raise ValueError(
            f"sca2 label only implements deterministic_sign; got {generation.get('labeling')!r}"
        )

    _ensure_datagen_on_path()
    from sca2_datagen.relabel import export_sign_relabel

    run_id = new_run_id(str(protocol["name"]), stage="label")
    root = repo_root()
    dest = Path(output_dir) if output_dir else prepare_run_dir(
        Path(runs_root) if runs_root else root / "runs",
        run_id,
        protocol,
    ) / "data"
    dest.mkdir(parents=True, exist_ok=True)

    bank = resolve_repo_path(generation["bank"], root)
    gps_json = resolve_repo_path(protocol["anchor"]["vectors_json"], root)
    gps_dta = resolve_repo_path(protocol["anchor"]["file"], root)

    manifest = export_sign_relabel(
        checkpoint_path=bank,
        output_dir=dest,
        gps_json=gps_json if gps_json.exists() else None,
        gps_dta=None if gps_json.exists() else gps_dta,
    )
    receipt = {
        "run_id": run_id,
        "stage": "label",
        "status": "ok",
        "protocol_name": protocol["name"],
        "protocol_hash": protocol["_hash"],
        "protocol_path": protocol["_path"],
        "rows": manifest["n_rows"],
        "countries": manifest["n_countries"],
        "triplets": manifest["n_triplets"],
        "rule": manifest["labeling_rule"],
        "out": str(dest),
    }
    run_dir = dest.parent if dest.name == "data" else dest
    write_receipt(run_dir, receipt)
    print(format_receipt(receipt))
    return receipt
