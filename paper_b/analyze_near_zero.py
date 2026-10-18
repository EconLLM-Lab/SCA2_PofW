#!/usr/bin/env python3
"""Paper B — the C6 near-zero refits: refit vs size-matched control, and vs baseline.

Object (frozen by `planning/sprint_2026-10-11/paper-b-tier1/C6_DESIGN.md`; the
orchestrator's section 9 is the comparison in force). For the two predeclared countries
GBR (singleton profile) and COL (multi-member profile), a refit adapter was trained on the
bank-2 rows of that country's unit with the |z| < 0.10 dimensions removed, and a
size-matched CONTROL adapter on a uniform random subsample of the same unit's training
rows of the same size (every dimension eligible). Both are scored on the strict battery.

Per strict surface s, with the composite the frozen-recode item mean
(`analyze_factorial.unit_composites`) and SD_s the SD (ddof 1) over the 64 profile
composites of `adapter_strict_v1.csv`:

    primary C6 contrast   (refit - control) / SD_s          block R, imprint surfaces
    data-size reference   (refit - baseline) / SD_s
                          (control - baseline) / SD_s

Block R holds surfaces whose dimension is still in training after the removal (the C6
rule applies there); block D holds the dropped dimensions and is a loss-of-signal check
that can never drive the decision. Intended direction of a surface is the unit's own bit
(up for 1, down for 0). The reading (C6_DESIGN section 9, items 4-5) is applied to the
block-R imprint surfaces only: a move counts only when |delta| is larger than the
replicate's |delta| on the same surface (the noise floor); a block-R imprint surface that
moves against its intended direction beyond the floor is reported as such and the filter
is not promoted, otherwise the margin stays a footnote. If the noise floor is absent,
no direction is claimed. Two refits are a screen: no interval is claimed.

Inputs are local scorer CSVs, a refit manifest per country (profile unit + near-zero
dimensions) and the noise-floor table. No GPU, no network, no human data.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "heldout"))
import analyze_factorial as AF  # noqa: E402
import analyze_surface as AS  # noqa: E402
import factorial as F  # noqa: E402
from ceiling import surface_items  # noqa: E402

# -------------------------------------------------------------- frozen definitions
SURFACES = tuple(surface_items(AS.STRICT_ITEMS))
SURFACE_DIM = {"trust": "trust", "risktaking": "risktaking",
               "patience:Q43": "patience", "patience:Q50": "patience",
               "altruism": "altruism", "posrecip": "posrecip", "negrecip": "negrecip"}
IMPRINT_SURFACES = ("trust", "risktaking", "posrecip", "altruism")
ADAPTER_SUFFIX = "_adapter"

PRIMARY = "refit_minus_control_sd"
DO_NOT_PROMOTE = "do not promote the filter"
FOOTNOTE = "the margin stays a footnote"
NOISE_UNKNOWN = "noise floor unknown: no direction claimed"

DEFAULT_BASELINE = Path("/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/"
                        "adapter_strict_v1.csv")
DEFAULT_NOISE = (HERE.parent / "planning/sprint_2026-10-11/paper-b-tier1/results/replicate/"
                 "replicate_surface_diff.csv")


# --------------------------------------------------------------- frame selection
def with_country(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure an `eval_country` column; a single-unit score file names its unit in `model`."""
    out = df.copy()
    if "eval_country" not in out.columns:
        name = str(out.model.iloc[0])
        out["eval_country"] = name[: -len(ADAPTER_SUFFIX)] if name.endswith(ADAPTER_SUFFIX) else name
    return out


def _composites_frame(df: pd.DataFrame) -> pd.DataFrame:
    items = AF.unit_composites(with_country(df))
    if items.unit.nunique() != 1:
        raise ValueError(f"expected exactly one unit, got {items.unit.nunique()}")
    return items


def surface_composites(df: pd.DataFrame) -> pd.Series:
    """Frozen-recode composite per strict surface for one unit's score frame."""
    items = _composites_frame(df)
    s = items.set_index("surface").composite
    missing = sorted(set(SURFACES) - set(s.index))
    if missing:
        raise ValueError(f"frame is missing surface(s): {missing}")
    return s.reindex(list(SURFACES))


def sd_over_profiles(baseline64: pd.DataFrame) -> pd.Series:
    """SD (ddof 1) of each surface's composite over the 64 profile composites."""
    comp = AF.unit_composites(baseline64)
    wide = comp.pivot(index="unit", columns="surface", values="composite")
    if wide.shape[0] != 64:
        raise ValueError(f"expected the 64 profile composites, got {wide.shape[0]}")
    missing = sorted(set(SURFACES) - set(wide.columns))
    if missing:
        raise ValueError(f"baseline is missing surface(s): {missing}")
    return wide.std(ddof=1).reindex(list(SURFACES))


def baseline_composites(baseline64: pd.DataFrame) -> pd.DataFrame:
    """unit x surface composites of the 64 profile adapters."""
    wide = AF.unit_composites(baseline64).pivot(index="unit", columns="surface",
                                                values="composite")
    missing = sorted(set(SURFACES) - set(wide.columns))
    if missing:
        raise ValueError(f"baseline is missing surface(s): {missing}")
    return wide


def intended_direction(unit: str, surface: str) -> str:
    """The unit's own bit on the surface's dimension: 1 -> up, 0 -> down."""
    bit = F.bits_of_unit(unit)[F.DIMS.index(SURFACE_DIM[surface])]
    return "up" if int(bit) == 1 else "down"


# ---------------------------------------------------------------------- the table
def near_zero_table(*, countries, refit: dict, control: dict, baseline64: pd.DataFrame,
                    dropped_by_country: dict, profile_by_country: dict) -> pd.DataFrame:
    """One row per (country, surface): composites, the three SD-unit deltas, block, direction."""
    countries = list(countries)
    sd = sd_over_profiles(baseline64)
    base = baseline_composites(baseline64)
    rows = []
    for cc in countries:
        unit = profile_by_country[cc]
        if unit not in set(base.index):
            raise ValueError(f"{unit!r} is not among the baseline units")
        dropped = set(dropped_by_country[cc])
        r = surface_composites(refit[cc])
        c = surface_composites(control[cc])
        b = base.loc[unit]
        for s in SURFACES:
            direction = intended_direction(unit, s)
            delta = float(r[s] - c[s])
            rows.append({
                "country": cc, "profile_unit": unit, "surface": s, "dimension": SURFACE_DIM[s],
                "block": "D" if SURFACE_DIM[s] in dropped else "R",
                "imprint": bool(s in IMPRINT_SURFACES), "intended_direction": direction,
                "refit_composite": float(r[s]), "control_composite": float(c[s]),
                "baseline_composite": float(b[s]), "sd_over_64_profiles": float(sd[s]),
                "refit_minus_control": delta, "refit_minus_control_sd": delta / float(sd[s]),
                "refit_minus_baseline_sd": float(r[s] - b[s]) / float(sd[s]),
                "control_minus_baseline_sd": float(c[s] - b[s]) / float(sd[s]),
                "against_sign": bool(delta > 0) if direction == "down" else bool(delta < 0),
            })
    return pd.DataFrame(rows)


# -------------------------------------------------------------------- noise floor
def noise_floor(path) -> pd.Series:
    """Per surface, the replicate's |delta| in SD units (the floor a move must beat)."""
    d = pd.read_csv(path)
    need = {"surface", "diff_sd"}
    missing = need - set(d.columns)
    if missing:
        raise ValueError(f"noise-floor table missing columns: {sorted(missing)}")
    if d.surface.duplicated().any():
        raise ValueError("noise-floor table has duplicate surface rows")
    return d.set_index("surface").diff_sd.abs()


def apply_noise(table: pd.DataFrame, noise: pd.Series | None) -> pd.DataFrame:
    """Add noise_floor_sd, beyond_floor and against_intended on the primary contrast."""
    out = table.copy()
    if noise is None:
        out["noise_floor_sd"] = np.nan
        out["beyond_floor"] = [None] * len(out)
        out["against_intended"] = [None] * len(out)
        return out
    out["noise_floor_sd"] = [float(noise[s]) for s in out.surface]
    if any(pd.isna(v) for v in out.noise_floor_sd):
        bad = sorted(set(out.surface[pd.isna(out.noise_floor_sd)]))
        raise ValueError(f"no noise floor for surface(s): {bad}")
    beyond = out[PRIMARY].abs().to_numpy() > out.noise_floor_sd.to_numpy()
    out["beyond_floor"] = [bool(x) for x in beyond]
    out["against_intended"] = [bool(a and b) for a, b in zip(out.beyond_floor, out.against_sign)]
    return out


# ------------------------------------------------------------------------ reading
def c6_reading(table: pd.DataFrame, *, noise_known: bool) -> dict:
    """C6_DESIGN section 9, item 5, on the block-R imprint surfaces."""
    block_r = table[(table.block == "R") & (table.imprint)]
    rows = []
    for _, r in block_r.iterrows():
        rows.append({
            "country": r.country, "surface": r.surface,
            "intended_direction": r.intended_direction,
            "refit_minus_control_sd": float(r[PRIMARY]),
            "noise_floor_sd": (None if pd.isna(r.noise_floor_sd) else float(r.noise_floor_sd)),
            "beyond_floor": (None if r.beyond_floor is None else bool(r.beyond_floor)),
            "against_intended": (None if r.against_intended is None else bool(r.against_intended)),
        })
    if not noise_known:
        decision = NOISE_UNKNOWN
    elif any(r["against_intended"] for r in rows):
        decision = DO_NOT_PROMOTE
    else:
        decision = FOOTNOTE
    against = [f"{r['country']} {r['surface']}" for r in rows if r["against_intended"]]
    sentence = {
        DO_NOT_PROMOTE: ("a retained imprint surface moves against its intended direction "
                         "beyond the retraining noise floor; the near-zero filter is not "
                         "promoted (block D is not evidence either way)"),
        FOOTNOTE: ("no retained imprint surface moves against its intended direction beyond "
                   "the retraining noise floor; the near-zero margin stays a footnote"),
        NOISE_UNKNOWN: ("the replicate is not scored, so the retraining noise floor is unknown; "
                        "no direction is claimed"),
    }[decision]
    return {
        "rule": "C6_DESIGN.md section 9, items 4-5 (C6 journey checkpoint reworded for composites)",
        "primary_contrast": "(refit composite - size-matched control composite) / SD over the 64 profile composites",
        "noise_floor_known": bool(noise_known),
        "block_r_imprint": rows,
        "block_r_imprint_against": against,
        "decision": decision,
        "decision_sentence": sentence,
        "not_a_test": "two refits are a screen; block D is reported as a loss-of-signal check only",
    }


# ----------------------------------------------------------------------- assembly
def analyse(*, countries, refit: dict, control: dict, manifests: dict, baseline64: pd.DataFrame,
            noise: pd.Series | None, results_dir, inputs: dict | None = None) -> dict:
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    profile_by_country = {cc: str(manifests[cc]["profile_unit"]) for cc in countries}
    dropped_by_country = {cc: list(manifests[cc]["near_zero_dimensions"]) for cc in countries}
    table = near_zero_table(countries=countries, refit=refit, control=control,
                            baseline64=baseline64, dropped_by_country=dropped_by_country,
                            profile_by_country=profile_by_country)
    annotated = apply_noise(table, noise)
    annotated.to_csv(results_dir / "near_zero_table.csv", index=False)
    reading = c6_reading(annotated, noise_known=noise is not None)
    out = {
        "what_this_is": ("the C6 near-zero refit vs its size-matched control and vs the "
                         "baseline profile adapter, per strict surface, in SD units of the 64 "
                         "profile composites"),
        "countries": list(countries),
        "profile_by_country": profile_by_country,
        "dropped_dimensions_by_country": dropped_by_country,
        "imprint_surfaces": list(IMPRINT_SURFACES),
        "noise_floor_sd": (None if noise is None else {str(k): float(v) for k, v in noise.items()}),
        "reading": reading,
        "table": annotated.to_dict(orient="records"),
    }
    if inputs:
        out["inputs"] = inputs
    (results_dir / "near_zero_analysis.json").write_text(json.dumps(out, indent=1) + "\n")
    return {"table": annotated, "reading": reading, "out": out}


def _pairs(items, what: str) -> dict:
    out = {}
    for kv in items or []:
        if "=" not in kv:
            raise SystemExit(f"--{what} expects CC=PATH, got {kv!r}")
        cc, path = kv.split("=", 1)
        out[cc] = Path(path)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--refit", action="append", required=True, metavar="CC=PATH")
    ap.add_argument("--control", action="append", required=True, metavar="CC=PATH")
    ap.add_argument("--manifest", action="append", required=True, metavar="CC=PATH",
                    help="refit manifest (profile_unit + near_zero_dimensions)")
    ap.add_argument("--baseline", default=str(DEFAULT_BASELINE),
                    help="the 64 profile adapters on the strict battery")
    ap.add_argument("--noise", default=None,
                    help="replicate_surface_diff.csv (noise floor); omit -> unknown")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    refit_paths, control_paths, man_paths = _pairs(a.refit, "refit"), _pairs(a.control, "control"), _pairs(a.manifest, "manifest")
    countries = sorted(refit_paths)
    if set(countries) != set(control_paths) or set(countries) != set(man_paths):
        raise SystemExit("the refit/control/manifest country sets differ")
    read = lambda p: pd.read_csv(p, dtype={"option_code": str, "question_id": str})  # noqa: E731
    refit = {cc: read(p) for cc, p in refit_paths.items()}
    control = {cc: read(p) for cc, p in control_paths.items()}
    manifests = {cc: json.loads(p.read_text()) for cc, p in man_paths.items()}
    baseline64 = read(Path(a.baseline))
    noise = noise_floor(a.noise) if a.noise else None

    paths = {f"refit_{cc}": p for cc, p in refit_paths.items()}
    paths |= {f"control_{cc}": p for cc, p in control_paths.items()}
    paths |= {f"manifest_{cc}": p for cc, p in man_paths.items()}
    paths["baseline"] = Path(a.baseline)
    if a.noise:
        paths["noise_floor"] = Path(a.noise)
    res = analyse(countries=countries, refit=refit, control=control, manifests=manifests,
                  baseline64=baseline64, noise=noise, results_dir=Path(a.out),
                  inputs={k: {"path": str(v), "sha256": AS.sha256_file(v)} for k, v in paths.items()})
    print(json.dumps(res["reading"], indent=1, default=str))
    print(f"wrote {a.out}/near_zero_table.csv, near_zero_analysis.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
