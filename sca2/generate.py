"""sca2 generate — inspect or refuse to rematerialize the shared A/B bank.

The paper protocol reuses a frozen bank. Creating a new bank is a new
scientific object: it requires the teacher + generator endpoints and a
new protocol name. This verb never calls those endpoints.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .protocol import load_protocol, repo_root, resolve_repo_path
from .runs import format_receipt, new_run_id, prepare_run_dir, write_receipt

REQUIRED_FIELDS = ("prompt", "gps_dimension", "response_a", "response_b")
DIMS = ("trust", "risktaking", "patience", "altruism", "posrecip", "negrecip")


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None  # NaN check


def _polarity(row: dict[str, Any]) -> str:
    """Return 'ok', 'inverted', or 'unscored' for the target dimension."""

    dim = str(row.get("gps_dimension", ""))
    chosen_opt = str(row.get("chosen_option", "")).strip().upper()
    m_ch = _finite(row.get(f"m_chosen_{dim}"))
    m_rj = _finite(row.get(f"m_rejected_{dim}"))
    if m_ch is None or m_rj is None or chosen_opt not in {"A", "B"}:
        return "unscored"
    m_a, m_b = (m_ch, m_rj) if chosen_opt == "A" else (m_rj, m_ch)
    if m_a > m_b:
        return "ok"
    return "inverted"


def inspect_bank(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"generation bank not found: {path}")
    n_rows = 0
    unique: dict[tuple[str, str], dict[str, str]] = {}
    dims: Counter[str] = Counter()
    missing_ab = 0
    conflicts = 0
    polarity = Counter()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            n_rows += 1
            if any(not row.get(field) for field in REQUIRED_FIELDS):
                missing_ab += 1
                continue
            key = (str(row["prompt"]), str(row["gps_dimension"]))
            pair = {"response_a": row["response_a"], "response_b": row["response_b"]}
            if key in unique:
                if unique[key] != pair:
                    conflicts += 1
                continue
            unique[key] = pair
            dims[str(row["gps_dimension"])] += 1
            polarity[_polarity(row)] += 1
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    inverted = int(polarity.get("inverted", 0))
    unscored = int(polarity.get("unscored", 0))
    return {
        "path": str(path),
        "sha256_16": digest,
        "n_rows": n_rows,
        "n_triplets": len(unique),
        "n_dimensions": len(dims),
        "per_dimension": dict(dims),
        "missing_ab": missing_ab,
        "conflicting_ab": conflicts,
        "polarity_ok": int(polarity.get("ok", 0)),
        "polarity_inverted": inverted,
        "polarity_unscored": unscored,
        "ok": missing_ab == 0 and conflicts == 0 and set(dims) == set(DIMS),
        "warnings": (
            ([f"polarity_inverted={inverted}"] if inverted else [])
            + ([f"polarity_unscored={unscored}"] if unscored else [])
        ),
    }


def run_generate(
    protocol_path: str | Path,
    *,
    materialize: bool = False,
    runs_root: Path | None = None,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    if materialize:
        raise RuntimeError(
            "Refusing to rematerialize. A new teacher/generator bank is a new "
            "protocol — copy gps_sign_dpo_wvs.toml, rename it, and wire HF there. "
            "The paper application reuses the frozen June 23 bank."
        )

    bank = resolve_repo_path(protocol["generation"]["bank"], repo_root())
    inspection = inspect_bank(bank)
    run_id = new_run_id(str(protocol["name"]), stage="generate")
    run_dir = prepare_run_dir(
        Path(runs_root) if runs_root else repo_root() / "runs",
        run_id,
        protocol,
    )
    (run_dir / "data" / "bank_inspect.json").write_text(
        json.dumps(inspection, indent=2) + "\n",
        encoding="utf-8",
    )
    status = "bank_reused" if inspection["ok"] else "bank_unhealthy"
    receipt = {
        "run_id": run_id,
        "stage": "generate",
        "status": status,
        "protocol_name": protocol["name"],
        "protocol_hash": protocol["_hash"],
        "protocol_path": protocol["_path"],
        "triplets": inspection["n_triplets"],
        "rows": inspection["n_rows"],
        "rule": protocol["generation"].get("labeling"),
        "out": inspection["path"],
        "bank_sha256_16": inspection["sha256_16"],
        "missing_ab": inspection["missing_ab"],
        "conflicting_ab": inspection["conflicting_ab"],
        "polarity_inverted": inspection.get("polarity_inverted", 0),
        "polarity_unscored": inspection.get("polarity_unscored", 0),
        "warnings": inspection.get("warnings", []),
    }
    write_receipt(run_dir, receipt)
    print(format_receipt(receipt))
    print(
        f"bank      {inspection['n_triplets']} unique A/B  "
        f"dims={inspection['n_dimensions']}  "
        f"sha={inspection['sha256_16']}"
    )
    if inspection.get("warnings"):
        print("warn     " + "; ".join(inspection["warnings"]))
    if status != "bank_reused":
        print("ok=false  bank failed inspection; not labeling from it")
    return receipt
