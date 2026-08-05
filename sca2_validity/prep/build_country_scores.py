#!/usr/bin/env python3
"""Build the frozen country x measure score matrix for SCA2 validity profiles.

Inputs (local, not committed):
  - GPS country-level:  data/GPS/GPS_dataset_country_level/country_gps.dta  (76 countries)
  - WVS wave 7:         data/WVS/WVS_wave7.dta                             (66 countries)
  - protocol:           prep/protocol.yaml  (frozen scoring recipe)

Outputs (data/validity/, reproducible):
  - scores_full.csv     unit=iso3 x {m_<dim>_<facet>, gps_<dim>} + n_respondents audit cols
  - roles_full.json     column roles for the full table
  - scores_<dim>.csv    per-dimension subset (one construct per run)
  - roles_<dim>.json
  - protocol_hash.txt   sha256 of the frozen protocol (pin into run ids)

Notes:
  - WVS_wave7.dta is read with pandas.read_stata (pyreadstat chokes on its
    metadata); GPS dta reads fine with pyreadstat.
  - Negative WVS codes are missing (DK/NA); masked before scoring.
  - Country means are unweighted (matches SCA2 merge convention).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
import pyreadstat
import yaml

REPO = Path(__file__).resolve().parents[2]
DEFAULT_GPS = REPO / "data" / "GPS" / "GPS_dataset_country_level" / "country_gps.dta"
DEFAULT_WVS = REPO / "data" / "WVS" / "WVS_wave7.dta"
DEFAULT_PROTOCOL = Path(__file__).resolve().parent / "protocol.yaml"
DEFAULT_OUT = REPO / "data" / "validity"

# WVS item columns used by the protocol (superset; prep selects by protocol)
WVS_COUNTRY_COL = "B_COUNTRY_ALPHA"

SCALES = {
    "binary_1_2": {"min": 1, "max": 2},
    "likert_1_4": {"min": 1, "max": 4},
    "scale_1_3": {"min": 1, "max": 3},
    "scale_1_10": {"min": 1, "max": 10},
    "member_0_2": {"min": 0, "max": 2},
}


def load_protocol(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("protocol must be a YAML mapping")
    return data


def protocol_hash(protocol: dict) -> str:
    return hashlib.sha256(
        yaml.safe_dump(protocol, sort_keys=True).encode("utf-8")
    ).hexdigest()


def read_wvs(path: Path) -> pd.DataFrame:
    """Read WVS wave 7 (pandas path; pyreadstat fails on this file's metadata)."""
    # item columns referenced by the protocol
    items: list[str] = []
    for dim, dim_spec in _PROTOCOL["dimensions"].items():
        for facet_spec in dim_spec["facets"].values():
            items.extend(facet_spec["items"].keys())
    cols = list(dict.fromkeys([WVS_COUNTRY_COL] + items))
    return pd.read_stata(path, columns=cols, convert_categoricals=False)


def read_gps(path: Path) -> pd.DataFrame:
    df, _ = pyreadstat.read_dta(str(path))
    return df


def normalize(value: pd.Series, scale: str) -> pd.Series:
    lo, hi = SCALES[scale]["min"], SCALES[scale]["max"]
    return (value - lo) / (hi - lo)


def build_country_scores(wvs: pd.DataFrame, gps: pd.DataFrame, protocol: dict) -> pd.DataFrame:
    dims = protocol["dimensions"]
    item_to_spec: dict[str, dict] = {}
    for dim, dim_spec in dims.items():
        for facet_name, facet_spec in dim_spec["facets"].items():
            for item, item_spec in facet_spec["items"].items():
                item_to_spec[item] = {"dim": dim, "facet": facet_name, **item_spec}

    gps_iso = gps.rename(columns={"isocode": "iso3"})
    gps_cols = {f"gps_{d}": d for d in dims}  # GPS dim columns -> aux names

    # respondent-level scored items
    scored = wvs[[WVS_COUNTRY_COL]].copy()
    for item, spec in item_to_spec.items():
        direction = float(spec["direction"])
        raw = pd.to_numeric(wvs[item], errors="coerce")
        valid = raw >= 0  # negative codes are missing
        norm = normalize(raw, spec["scale"])
        s = norm if direction > 0 else (1.0 - norm)
        scored[f"item_{item}"] = s.where(valid)

    # facet score per respondent = row mean over non-missing items
    for dim, dim_spec in dims.items():
        for facet_name, facet_spec in dim_spec["facets"].items():
            cols = [f"item_{it}" for it in facet_spec["items"]]
            scored[f"m_{dim}_{facet_name}"] = scored[cols].mean(axis=1, skipna=True)
            # require at least one non-missing item (else NaN)
            scored.loc[scored[cols].isna().all(axis=1), f"m_{dim}_{facet_name}"] = pd.NA

    min_n = int(protocol["min_respondents_per_country"])
    country_rows: list[dict] = []
    for iso, grp in scored.groupby(WVS_COUNTRY_COL):
        row: dict = {"iso3": iso}
        ok = True
        for dim, dim_spec in dims.items():
            for facet_name in dim_spec["facets"]:
                col = f"m_{dim}_{facet_name}"
                vals = grp[col].dropna()
                row[f"n_{dim}_{facet_name}"] = int(len(vals))
                row[col] = float(vals.mean()) if len(vals) >= min_n else pd.NA
        country_rows.append(row)

    out = pd.DataFrame(country_rows)
    # attach GPS criterion columns (aux)
    gps_map = gps_iso.set_index("iso3")
    for aux, dim in gps_cols.items():
        out[aux] = out["iso3"].map(gps_map[dim])
    return out


def write_roles(dims: dict, out_dir: Path, suffix: str = "full") -> None:
    measures = [f"m_{d}_{f}" for d, ds in dims.items() for f in ds["facets"]]
    aux = [f"gps_{d}" for d in dims]
    roles = {"unit_id": "iso3", "measures": measures, "aux": aux, "outcome": None}
    (out_dir / f"roles_{suffix}.json").write_text(json.dumps(roles, indent=2) + "\n")
    for d, ds in dims.items():
        sub = {
            "unit_id": "iso3",
            "measures": [f"m_{d}_{f}" for f in ds["facets"]],
            "aux": [f"gps_{d}"],
            "outcome": None,
        }
        (out_dir / f"roles_{d}.json").write_text(json.dumps(sub, indent=2) + "\n")


def main() -> None:
    global _PROTOCOL  # module-level cache used by read_wvs
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gps", type=Path, default=DEFAULT_GPS)
    parser.add_argument("--wvs", type=Path, default=DEFAULT_WVS)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    _PROTOCOL = load_protocol(args.protocol)
    protocol = _PROTOCOL

    print(f"reading WVS from {args.wvs} ...")
    wvs = read_wvs(args.wvs)
    print(f"  {wvs.shape[0]} respondents, {wvs[WVS_COUNTRY_COL].nunique()} countries")
    print(f"reading GPS from {args.gps} ...")
    gps = read_gps(args.gps)
    print(f"  {gps.shape[0]} countries")

    scores = build_country_scores(wvs, gps, protocol)
    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    scores.to_csv(out_dir / "scores_full.csv", index=False)
    write_roles(protocol["dimensions"], out_dir)

    # per-dimension subsets
    for d, ds in protocol["dimensions"].items():
        facet_cols = [f"m_{d}_{f}" for f in ds["facets"]]
        n_cols = [f"n_{d}_{f}" for f in ds["facets"]]
        sub = scores[["iso3", *facet_cols, f"gps_{d}", *n_cols]].copy()
        sub.to_csv(out_dir / f"scores_{d}.csv", index=False)

    phash = protocol_hash(protocol)
    (out_dir / "protocol_hash.txt").write_text(phash + "\n")

    n_with_gps = int(scores[f"gps_{list(protocol['dimensions'])[0]}"].notna().sum())
    print(f"wrote {out_dir}:")
    print(f"  scores_full.csv rows={len(scores)}  (countries with GPS: {n_with_gps})")
    print(f"  roles_*.json, scores_<dim>.csv per dimension")
    print(f"  protocol_hash.txt = {phash}")
    print("  next: sca2-validity run --scores data/validity/scores_trust.csv "
          "--roles data/validity/roles_trust.json --network prep/networks/trust.yaml ...")


if __name__ == "__main__":
    _PROTOCOL: dict = {}
    main()
