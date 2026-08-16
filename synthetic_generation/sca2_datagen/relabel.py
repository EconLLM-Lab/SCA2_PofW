"""Deterministic sign-relabel of a shared A/B triplet bank.

The June 2023 USA/MEX generator already wrote country-independent
Response A (positive loading) / Response B (negative loading) pairs.
This module assigns each pair to any GPS country by the sign of that
country's target-dimension z-score. No model calls.

    chosen = A if z_{c,k} >= 0 else B
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .config import GPS_DIMENSIONS

DIMS = tuple(GPS_DIMENSIONS)
LABELING_RULE = "deterministic_sign"
SOURCE_RUN_ID = "usa_mex_dpo_anchored_110_b6_c4_06232026_20260623_185531Z"
NEAR_ZERO = 0.10

DEFAULT_CHECKPOINT = (
    Path(__file__).resolve().parents[1]
    / "outputs"
    / "usa_mex_dpo_anchored_110_b6_c4_06232026"
    / "checkpoint_raw_pairs.jsonl"
)
DEFAULT_GPS_DTA = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "GPS"
    / "GPS_dataset_country_level"
    / "country_gps.dta"
)
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[1] / "outputs" / "gps_sign_relabel_all"
)


def sign_choice(z_value: float) -> str:
    """Return A for non-negative z, B for negative z."""

    if not math.isfinite(z_value):
        raise ValueError(f"z_value must be finite, got {z_value!r}")
    return "A" if z_value >= 0 else "B"


def triplet_id(prompt: str, gps_dimension: str) -> str:
    payload = f"{gps_dimension}\n{prompt}".encode("utf-8")
    return hashlib.sha1(payload).hexdigest()[:12]


def _finite_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def recover_ab_scores(row: dict[str, Any]) -> dict[str, float | None]:
    """Map chosen/rejected scorer columns back onto Response A / Response B."""

    chosen_option = str(row.get("chosen_option", "")).strip().upper()
    recovered: dict[str, float | None] = {}
    for dim in DIMS:
        chosen = _finite_or_none(row.get(f"m_chosen_{dim}"))
        rejected = _finite_or_none(row.get(f"m_rejected_{dim}"))
        if chosen_option == "A":
            recovered[f"m_a_{dim}"] = chosen
            recovered[f"m_b_{dim}"] = rejected
        elif chosen_option == "B":
            recovered[f"m_a_{dim}"] = rejected
            recovered[f"m_b_{dim}"] = chosen
        else:
            recovered[f"m_a_{dim}"] = None
            recovered[f"m_b_{dim}"] = None
    return recovered


def build_triplet_bank(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate checkpoint rows into a country-independent A/B bank."""

    bank: dict[str, dict[str, Any]] = {}
    for row in rows:
        prompt = row["prompt"]
        dim = row["gps_dimension"]
        key = triplet_id(prompt, dim)
        if key in bank:
            existing = bank[key]
            if existing["response_a"] != row["response_a"] or existing["response_b"] != row["response_b"]:
                raise ValueError(f"Conflicting A/B text for triplet {key} ({dim})")
            continue
        scores = recover_ab_scores(row)
        bank[key] = {
            "triplet_id": key,
            "prompt": prompt,
            "facet": row.get("facet", ""),
            "gps_dimension": dim,
            "response_a": row["response_a"],
            "response_b": row["response_b"],
            "source_qc_status": row.get("qc_status"),
            "source_contamination_ratio": _finite_or_none(row.get("contamination_ratio")),
            "source_contamination_category": row.get("contamination_category"),
            **scores,
        }
    return [bank[key] for key in sorted(bank)]


def label_triplet_for_country(
    triplet: dict[str, Any],
    country: str,
    z_c: dict[str, float],
    *,
    run_id: str,
    export_timestamp: str,
) -> dict[str, Any]:
    dim = triplet["gps_dimension"]
    z_value = float(z_c[dim])
    chosen_option = sign_choice(z_value)
    chosen = triplet["response_a"] if chosen_option == "A" else triplet["response_b"]
    rejected = triplet["response_b"] if chosen_option == "A" else triplet["response_a"]
    m_chosen = triplet.get(f"m_a_{dim}" if chosen_option == "A" else f"m_b_{dim}")
    m_rejected = triplet.get(f"m_b_{dim}" if chosen_option == "A" else f"m_a_{dim}")
    signed_diff = None
    if m_chosen is not None and m_rejected is not None:
        signed_diff = m_chosen - m_rejected
    return {
        "prompt": triplet["prompt"],
        "chosen": chosen,
        "rejected": rejected,
        "country": country,
        "gps_dimension": dim,
        "z_value": round(z_value, 10),
        "facet": triplet["facet"],
        "response_a": triplet["response_a"],
        "response_b": triplet["response_b"],
        "chosen_option": chosen_option,
        "gps_profile_vector": {key: z_c[key] for key in DIMS},
        "labeling_rule": LABELING_RULE,
        "near_zero_z": abs(z_value) < NEAR_ZERO,
        "triplet_id": triplet["triplet_id"],
        "source_run_id": SOURCE_RUN_ID,
        "run_id": run_id,
        "export_timestamp": export_timestamp,
        "source_qc_status": triplet.get("source_qc_status"),
        "source_contamination_ratio": triplet.get("source_contamination_ratio"),
        "source_contamination_category": triplet.get("source_contamination_category"),
        "m_chosen": m_chosen,
        "m_rejected": m_rejected,
        "m_diff_signed": None if signed_diff is None else round(signed_diff, 4),
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
    return count


def load_gps_vectors(gps_json: Path | None = None, gps_dta: Path | None = None) -> dict[str, dict[str, float]]:
    if gps_json and gps_json.exists():
        payload = json.loads(gps_json.read_text(encoding="utf-8"))
        return {iso: {dim: float(values[dim]) for dim in DIMS} for iso, values in payload.items()}

    path = gps_dta or DEFAULT_GPS_DTA
    if not path.exists():
        raise FileNotFoundError(
            f"GPS vectors not found. Provide --gps-json or place country_gps.dta at {path}"
        )
    import pandas as pd

    frame = pd.read_stata(path, convert_categoricals=False)
    missing = [dim for dim in DIMS if dim not in frame.columns]
    if missing or "isocode" not in frame.columns:
        raise ValueError(f"GPS file missing required columns: {missing or 'isocode'}")
    vectors: dict[str, dict[str, float]] = {}
    for _, row in frame.iterrows():
        iso = str(row["isocode"]).strip().upper()
        values = {dim: float(row[dim]) for dim in DIMS}
        if any(not math.isfinite(values[dim]) for dim in DIMS):
            continue
        vectors[iso] = values
    return vectors


def export_sign_relabel(
    *,
    checkpoint_path: Path,
    output_dir: Path,
    gps_json: Path | None = None,
    gps_dta: Path | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    export_time = datetime.now(timezone.utc)
    export_timestamp = export_time.isoformat()
    run_id = f"gps_sign_relabel_all_{export_time.strftime('%Y%m%d_%H%M%SZ')}"

    checkpoint_rows = load_jsonl(checkpoint_path)
    bank = build_triplet_bank(checkpoint_rows)
    vectors = load_gps_vectors(gps_json=gps_json, gps_dta=gps_dta)
    countries = sorted(vectors)

    write_jsonl(output_dir / "triplets_bank.jsonl", bank)
    (output_dir / "gps_z_vectors.json").write_text(
        json.dumps(vectors, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    per_country_counts: dict[str, int] = {}
    per_country_sign: dict[str, dict[str, str]] = {}
    near_zero_cells = 0
    for country in countries:
        z_c = vectors[country]
        labeled = [
            label_triplet_for_country(
                triplet,
                country,
                z_c,
                run_id=run_id,
                export_timestamp=export_timestamp,
            )
            for triplet in bank
        ]
        near_zero_cells += sum(1 for row in labeled if row["near_zero_z"])
        write_jsonl(output_dir / f"D_syn_{country}.jsonl", labeled)
        per_country_counts[country] = len(labeled)
        per_country_sign[country] = {dim: sign_choice(z_c[dim]) for dim in DIMS}

    dim_counts = {dim: 0 for dim in DIMS}
    for triplet in bank:
        dim_counts[triplet["gps_dimension"]] += 1

    manifest = {
        "run_id": run_id,
        "timestamp": export_timestamp,
        "labeling_rule": LABELING_RULE,
        "source_run_id": SOURCE_RUN_ID,
        "source_checkpoint": str(checkpoint_path),
        "n_triplets": len(bank),
        "n_countries": len(countries),
        "n_rows": len(bank) * len(countries),
        "countries": countries,
        "gps_vectors": vectors,
        "per_country_sign": per_country_sign,
        "per_country_counts": per_country_counts,
        "per_dimension_triplet_counts": dim_counts,
        "near_zero_threshold": NEAR_ZERO,
        "near_zero_labeled_rows": near_zero_cells,
        "notes": [
            "Shared A/B bank is reused for every country; only chosen/rejected are flipped.",
            "z == 0 is labeled A (non-negative). Magnitude is discarded.",
            "source_qc_status is the original USA/MEX scorer label for that pair, not a new score.",
            "No Hugging Face / LLM calls were made for this export.",
        ],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sign-relabel a shared triplet bank for all GPS countries")
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--gps-json", type=Path, default=None)
    parser.add_argument("--gps-dta", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = export_sign_relabel(
        checkpoint_path=args.checkpoint,
        output_dir=args.output_dir,
        gps_json=args.gps_json,
        gps_dta=args.gps_dta,
    )
    print(
        f"Wrote {manifest['n_rows']} rows "
        f"({manifest['n_countries']} countries × {manifest['n_triplets']} triplets) "
        f"to {args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
