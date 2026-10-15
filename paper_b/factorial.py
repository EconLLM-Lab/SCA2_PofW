"""Paper B — the 2^6 sign-profile factorial design.

A *unit* is one of the 64 possible sign vectors over the six GPS dimensions.
Unit codes are `P_<trust>_<risktaking>_<patience>_<altruism>_<posrecip>_<negrecip>`
(1 = non-negative z, 0 = negative), the same bit order as `sign_prompt.profile_id`.
A unit code is a filesystem-safe token and the design cell itself.

Labeling mirrors `synthetic_generation/sca2_datagen/relabel.py` (chosen = A iff
z >= 0). It is reimplemented here, as `verify_gates.py` does, so paper_b never
imports the generation package and its endpoint dependencies. verify_gates.py
re-checks every label against the sign rule before any training.

This module builds data only. It never trains and never calls a model.
"""
from __future__ import annotations

import itertools
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

DIMS = ["trust", "risktaking", "patience", "altruism", "posrecip", "negrecip"]
LABELING_RULE = "deterministic_sign"
NEAR_ZERO = 0.10


def unit_of_bits(bits: Sequence[int]) -> str:
    if len(bits) != 6 or any(int(b) not in (0, 1) for b in bits):
        raise ValueError(f"bits must be six 0/1 values, got {bits!r}")
    return "P_" + "_".join(str(int(b)) for b in bits)


def bits_of_unit(unit: str) -> tuple[int, ...]:
    parts = str(unit).split("_")
    if len(parts) != 7 or parts[0] != "P" or any(p not in ("0", "1") for p in parts[1:]):
        raise ValueError(f"not a unit code: {unit!r}")
    return tuple(int(p) for p in parts[1:])


def all_units() -> list[str]:
    return [unit_of_bits(b) for b in itertools.product((0, 1), repeat=6)]


def z_vector(unit: str) -> dict[str, float]:
    return {d: (1.0 if b else -1.0) for d, b in zip(DIMS, bits_of_unit(unit))}


def unit_of_z(z: dict[str, float]) -> str:
    return unit_of_bits([1 if float(z[d]) >= 0 else 0 for d in DIMS])


def flip(unit: str, dim: str) -> str:
    if dim not in DIMS:
        raise ValueError(f"unknown dimension {dim!r}")
    bits = list(bits_of_unit(unit))
    i = DIMS.index(dim)
    bits[i] = 1 - bits[i]
    return unit_of_bits(bits)


def unit_members(gps_json: Path, cohort: Sequence[str]) -> dict[str, list[str]]:
    """Factorial cell -> the real cohort countries whose GPS signs fall in it."""
    raw = json.loads(Path(gps_json).read_text())
    out: dict[str, list[str]] = {}
    for cc in cohort:
        out.setdefault(unit_of_z(raw[cc]), []).append(cc)
    return {u: sorted(v) for u, v in sorted(out.items())}


def label_row(triplet: dict, unit: str, *, run_id: str, source_run_id: str,
              export_timestamp: str) -> dict:
    """One labeled DPO row; same fields as relabel.label_triplet_for_country."""
    z = z_vector(unit)
    dim = triplet["gps_dimension"]
    z_value = z[dim]
    chosen_option = "A" if z_value >= 0 else "B"
    chosen = triplet["response_a"] if chosen_option == "A" else triplet["response_b"]
    rejected = triplet["response_b"] if chosen_option == "A" else triplet["response_a"]
    return {
        "prompt": triplet["prompt"], "chosen": chosen, "rejected": rejected,
        "country": unit, "gps_dimension": dim, "z_value": z_value,
        "facet": triplet.get("facet", ""),
        "response_a": triplet["response_a"], "response_b": triplet["response_b"],
        "chosen_option": chosen_option, "gps_profile_vector": dict(z),
        "labeling_rule": LABELING_RULE, "near_zero_z": abs(z_value) < NEAR_ZERO,
        "triplet_id": triplet["triplet_id"], "source_run_id": source_run_id,
        "run_id": run_id, "export_timestamp": export_timestamp,
        "source_qc_status": triplet.get("source_qc_status"),
    }


def build_profile_bank(triplets_bank: Path, out_dir: Path, *, bank_run_id: str,
                       source_run_id: str, units: Iterable[str] | None = None) -> dict:
    """Write D_syn_<unit>.jsonl for every unit from relabel's triplets_bank.jsonl."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    triplets = [json.loads(l) for l in Path(triplets_bank).read_text().splitlines() if l.strip()]
    if not triplets:
        raise ValueError(f"empty triplet bank: {triplets_bank}")
    bad = [t.get("gps_dimension") for t in triplets if t.get("gps_dimension") not in DIMS]
    if bad:
        raise ValueError(f"unknown dimensions in bank: {sorted(set(map(str, bad)))}")
    triplets.sort(key=lambda r: r["triplet_id"])
    units = sorted(units) if units else all_units()
    for u in units:
        bits_of_unit(u)
    ts = datetime.now(timezone.utc).isoformat()
    counts = {}
    for u in units:
        rows = [label_row(t, u, run_id=bank_run_id, source_run_id=source_run_id,
                          export_timestamp=ts) for t in triplets]
        with (out_dir / f"D_syn_{u}.jsonl").open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        counts[u] = len(rows)
    per_dim = {d: sum(1 for t in triplets if t["gps_dimension"] == d) for d in DIMS}
    manifest = {
        "run_id": bank_run_id, "source_run_id": source_run_id,
        "source_triplets_bank": str(triplets_bank), "labeling_rule": LABELING_RULE,
        "n_triplets": len(triplets), "n_units": len(units), "units": units,
        "per_unit_counts": counts, "per_dimension_triplet_counts": per_dim,
        "timestamp": ts,
        "notes": [
            "Units are sign vectors (P_<bits> in sign_prompt.DIMS order), not countries.",
            "Shared A/B bank is reused for every unit; only chosen/rejected are flipped.",
            "No model calls were made for this export.",
        ],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="write the 64 sign-profile banks")
    ap.add_argument("--triplets-bank", required=True, help="relabel output triplets_bank.jsonl")
    ap.add_argument("--bank-manifest", required=True, help="relabel output manifest.json")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    bm = json.loads(Path(a.bank_manifest).read_text())
    m = build_profile_bank(Path(a.triplets_bank), Path(a.out_dir), bank_run_id=bm["run_id"],
                           source_run_id=bm["source_run_id"])
    print(f"wrote {m['n_units']} units x {m['n_triplets']} triplets -> {a.out_dir}")
    print("per dimension:", m["per_dimension_triplet_counts"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
