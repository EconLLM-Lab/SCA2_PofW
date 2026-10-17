#!/usr/bin/env python3
"""T2 — bank-2 transport on the strict battery (journey checkpoint C3).

Three steps, all reusing the banked analysis functions (no second recode):

  1. reproduction. Cohort-1 adapter-GPS Spearman per surface over the 42
     countries of `cohort1_strict.csv`, profile-block bootstrap. Must match the
     banked run `paper-b-20261011` (trust 0.74 [0.50, 0.86]).
  2. bank 2. Each of the 42 cohort countries takes the composite of its
     sign-profile unit (`factorial.unit_of_z` on the GPS z vector) from
     `adapter_strict_v1.csv`; Spearman against the surface's own GPS dimension
     over the 42 countries, with the profile-block bootstrap (clusters = profile
     cell id). Patience stays two surfaces (Q43, Q50).
  3. bank-to-bank agreement. For the 26 shared cells, Pearson and Spearman
     between bank-1 cell means (mean of sign-mate country composites) and bank-2
     profile composites, with a 2,000-draw bootstrap over cells.

C3 reading (journey C0): each imprint dimension (trust, risktaking, posrecip,
altruism) whose bank-2 interval still excludes 0 is transport; one that does not
is named and its transport sentence is dropped.

CPU only, no network, no human respondent rows. Reads only the two synthetic
score files named on the card; writes the JSON + note under OUT_DIR.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "heldout"))
import analyze_factorial as AF  # noqa: E402
import analyze_surface as AS  # noqa: E402
import factorial as F  # noqa: E402

# ------------------------------------------------------------------ constants
INPUT_DIR = Path("/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs")
COHORT1_STRICT = INPUT_DIR / "cohort1_strict.csv"
ADAPTER_STRICT_V1 = INPUT_DIR / "adapter_strict_v1.csv"
OUT_DIR = REPO / "planning/sprint_2026-10-11/paper-b-tier1/results"
JSON_NAME = "bank2_transport_strict.json"
MD_NAME = "BANK2_TRANSPORT_20261018.md"

# The seven surfaces, patience kept unpooled (frozen decision).
SURFACES = ["trust", "risktaking", "posrecip", "altruism",
            "negrecip", "patience:Q43", "patience:Q50"]
# Journey C0 imprint set: the four cohort-1 surfaces whose interval excluded 0.
IMPRINT = ["trust", "risktaking", "posrecip", "altruism"]
# Same six-dimension order analyze_surface/analyze_phase use for sign_profiles.
PROF_DIMS = ["altruism", "negrecip", "patience", "posrecip", "risktaking", "trust"]

DRAWS = AS.BOOT_DRAWS            # 2000
SEED = AS.BOOT_SEED              # 20261011
CI = (0.025, 0.975)


# ------------------------------------------------------------------- helpers
def load_scores(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["option_code"] = df["option_code"].astype(str)  # preserve string keys
    return df


def surface_composites(path: Path) -> pd.DataFrame:
    """(unit, surface, composite) for a score file, via the shared recode path."""
    return AF.unit_composites(load_scores(path))


def load_gps_raw(path: Path = AS.DEFAULT_GPS_JSON) -> dict:
    return json.loads(Path(path).read_text())


def country_units(gps_raw: dict, countries) -> pd.Series:
    """country -> factorial cell (unit code) from sign(z) over the six dims.

    Uses `factorial.unit_of_z`, the same sign rule as `sign_prompt`/`factorial`.
    Verified to induce the identical partition as `analyze_surface.sign_profiles`
    on the 42-country cohort (no GPS z is exactly 0).
    """
    return pd.Series({cc: F.unit_of_z(gps_raw[cc]) for cc in countries}, name="unit")


def unit_series(comp: pd.DataFrame, surface: str, units: pd.Series) -> pd.Series:
    """country -> composite of its unit on one surface (constant within a cell)."""
    by_unit = comp[comp.surface == surface].set_index("unit")["composite"]
    missing = sorted(set(units.values) - set(by_unit.index))
    if missing:
        raise ValueError(f"{surface}: units missing from composites: {missing}")
    return pd.Series({cc: float(by_unit[u]) for cc, u in units.items()}, name=surface)


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or np.all(a == a[0]) or np.all(b == b[0]):
        return float("nan")
    v = float(np.corrcoef(a, b)[0, 1])
    return v if math.isfinite(v) else float("nan")


def _ci(draws: np.ndarray) -> tuple[float, float]:
    valid = draws[np.isfinite(draws)]
    if valid.size == 0:
        return float("nan"), float("nan")
    lo, hi = (float(v) for v in np.quantile(valid, CI))
    return lo, hi


def _r(r: dict) -> dict:
    """Normalise a bootstrap_spearman result to plain floats."""
    return {"point": float(r["point"]), "ci_lo": float(r["ci_lo"]), "ci_hi": float(r["ci_hi"]),
            "n": int(r["n"]), "degenerate_draws": int(r["degenerate_draws"]),
            "draws": int(r["draws"])}


def bootstrap_cell_corr(x: pd.Series, y: pd.Series, *, draws: int = DRAWS,
                        seed: int = SEED) -> dict:
    """Cell bootstrap (rows = cells) of Pearson and Spearman; percentile intervals.

    One set of index resamples drives both statistics, so the intervals are
    paired. Degenerate draws are counted, never swallowed.
    """
    d = pd.concat([x.rename("x"), y.rename("y")], axis=1).dropna()
    n = len(d)
    xa, ya = d.x.to_numpy(float), d.y.to_numpy(float)
    point_p = _pearson(xa, ya)
    point_s = AS._spearman_arrays(xa, ya)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(draws, n)) if n else np.empty((draws, 0), dtype=int)
    ps = np.array([_pearson(xa[i], ya[i]) for i in idx])
    ss = np.array([AS._spearman_arrays(xa[i], ya[i]) for i in idx])
    plo, phi = _ci(ps)
    slo, shi = _ci(ss)
    return {"n_cells": int(n), "pearson": point_p, "pearson_lo": plo, "pearson_hi": phi,
            "spearman": point_s, "spearman_lo": slo, "spearman_hi": shi,
            "degenerate_draws": int(np.sum(~np.isfinite(ss))), "draws": int(draws)}


# ------------------------------------------------------------------ the steps
def cohort1_adapter_gps(comp_c1: pd.DataFrame, gps: pd.DataFrame, profiles: pd.DataFrame,
                        *, draws: int = DRAWS, seed: int = SEED) -> dict:
    """Step 1: cohort-1 adapter-GPS Spearman per surface, profile-block bootstrap."""
    prof_idx = profiles.set_index("country")["profile_id"]
    out = {}
    for surface in SURFACES:
        s = comp_c1[comp_c1.surface == surface].set_index("unit")["composite"]
        tgt = gps[surface.split(":")[0]].reindex(s.index)
        r = AS.bootstrap_spearman(s, tgt, clusters=prof_idx.reindex(s.index),
                                  draws=draws, seed=seed)
        out[surface] = _r(r)
    return out


def bank2_adapter_gps(comp_b2: pd.DataFrame, gps: pd.DataFrame, units: pd.Series,
                      *, draws: int = DRAWS, seed: int = SEED) -> dict:
    """Step 2: bank-2 unit composite per cohort country, profile-block bootstrap."""
    out = {}
    for surface in SURFACES:
        s = unit_series(comp_b2, surface, units)
        tgt = gps[surface.split(":")[0]].reindex(s.index)
        r = AS.bootstrap_spearman(s, tgt, clusters=units.reindex(s.index),
                                  draws=draws, seed=seed)
        out[surface] = _r(r)
    return out


def bank_to_bank(comp_c1: pd.DataFrame, comp_b2: pd.DataFrame, gps_json: Path,
                 *, draws: int = DRAWS, seed: int = SEED) -> dict:
    """Step 3: bank-1 cell means vs bank-2 profile composites over the shared cells."""
    cells = AF.cohort1_cells(comp_c1, gps_json)
    out = {}
    for surface in SURFACES:
        a = cells[cells.surface == surface].set_index("unit")["composite"]
        b = comp_b2[comp_b2.surface == surface].set_index("unit")["composite"]
        d = pd.concat([a.rename("bank1"), b.rename("bank2")], axis=1).dropna()
        out[surface] = bootstrap_cell_corr(d.bank1, d.bank2, draws=draws, seed=seed)
    return out


def c3_reading(surface: str, r: dict) -> str:
    """C3 pass rule for one surface, from its bank-2 interval."""
    if surface not in IMPRINT:
        return "reported (not an imprint dimension)"
    lo, hi = r["ci_lo"], r["ci_hi"]
    if math.isfinite(lo) and math.isfinite(hi) and (lo > 0 or hi < 0):
        return "transport holds"
    return "transport dropped: interval includes 0"


# ------------------------------------------------------------------- driver
def run(cohort1_path: Path | None = None, bank2_path: Path | None = None,
        gps_json: Path | None = None, *, draws: int = DRAWS, seed: int = SEED) -> dict:
    cohort1_path = Path(cohort1_path or COHORT1_STRICT)
    bank2_path = Path(bank2_path or ADAPTER_STRICT_V1)
    gps_json = Path(gps_json or AS.DEFAULT_GPS_JSON)

    comp_c1 = surface_composites(cohort1_path)
    comp_b2 = surface_composites(bank2_path)
    countries = sorted(comp_c1.unit.unique())
    gps_raw = load_gps_raw(gps_json)
    z = AS.load_gps_z(gps_json)
    gps = z.pivot(index="country", columns="dimension", values="z")
    profiles = AS.sign_profiles(z, countries, PROF_DIMS)
    units = country_units(gps_raw, countries)

    c1 = cohort1_adapter_gps(comp_c1, gps, profiles, draws=draws, seed=seed)
    b2 = bank2_adapter_gps(comp_b2, gps, units, draws=draws, seed=seed)
    bb = bank_to_bank(comp_c1, comp_b2, gps_json, draws=draws, seed=seed)

    surfaces_table = [{
        "surface": s, "imprint": s in IMPRINT,
        "cohort1_rho": c1[s]["point"], "cohort1_lo": c1[s]["ci_lo"], "cohort1_hi": c1[s]["ci_hi"],
        "bank2_rho": b2[s]["point"], "bank2_lo": b2[s]["ci_lo"], "bank2_hi": b2[s]["ci_hi"],
        "c3_reading": c3_reading(s, b2[s]),
    } for s in SURFACES]
    bank_to_bank_table = [{
        "surface": s, "n_cells": bb[s]["n_cells"],
        "pearson": bb[s]["pearson"], "pearson_lo": bb[s]["pearson_lo"], "pearson_hi": bb[s]["pearson_hi"],
        "spearman": bb[s]["spearman"], "spearman_lo": bb[s]["spearman_lo"], "spearman_hi": bb[s]["spearman_hi"],
    } for s in SURFACES]
    kept = [s for s in IMPRINT if c3_reading(s, b2[s]) == "transport holds"]
    c3_pass = {"imprint": list(IMPRINT), "kept": kept,
               "dropped": [s for s in IMPRINT if s not in kept],
               "all_imprint_keep": len(kept) == len(IMPRINT)}

    return {
        "generated_by": "paper_b/bank2_transport.py",
        "checkpoint": "C3",
        "run_date": "2026-10-18",
        "draws": int(draws), "seed": int(seed), "ci": list(CI),
        "n_countries": int(len(countries)), "n_cells": int(units.nunique()),
        "n_profiles_sign": int(profiles.profile_id.nunique()),
        "inputs": {
            "cohort1_strict": {"path": str(cohort1_path), "sha256": AS.sha256_file(cohort1_path)},
            "adapter_strict_v1": {"path": str(bank2_path), "sha256": AS.sha256_file(bank2_path)},
            "gps_z": {"path": str(gps_json), "sha256": AS.sha256_file(gps_json)},
        },
        "cohort1_adapter_gps": c1,
        "bank2_adapter_gps": b2,
        "bank_to_bank": bb,
        "surfaces_table": surfaces_table,
        "bank_to_bank_table": bank_to_bank_table,
        "c3_pass": c3_pass,
    }


def _f(x: float) -> str:
    return "nan" if x is None or not math.isfinite(float(x)) else f"{float(x):.3f}"


def render_note(res: dict) -> str:
    lines = [
        "# Bank-2 transport on the strict battery (checkpoint C3)",
        "",
        "Produced by `paper_b/bank2_transport.py`; every number below is read from",
        f"`{JSON_NAME}`. Seeds: bootstrap {res['seed']}, {res['draws']} draws, percentile interval.",
        f"Cohort: {res['n_countries']} countries in {res['n_cells']} factorial cells "
        f"({res['n_profiles_sign']} GPS-sign profiles).",
        "",
        "## Inputs",
        "",
    ]
    for name, meta in res["inputs"].items():
        lines.append(f"- {name}: `{meta['path']}` sha256 `{meta['sha256'][:12]}…`")
    lines += [
        "",
        "## Method",
        "",
        "Step 1 reproduces the banked cohort-1 adapter-GPS Spearman per surface",
        "(profile-block bootstrap, clusters = GPS-sign profile). Step 2 gives each of",
        "the 42 cohort countries the composite of its sign-profile unit on bank 2",
        "(`factorial.unit_of_z` on the GPS z vector) and correlates it with the",
        "surface's own GPS dimension, profile-block bootstrap. Step 3 correlates",
        "bank-1 cell means with bank-2 profile composites over the shared cells, with",
        "a 2,000-draw bootstrap over cells.",
        "",
        "## Table 1 — seven surfaces",
        "",
        "| Surface | Imprint | Cohort-1 rho [95% CI] | Bank-2 rho [95% CI] | C3 reading |",
        "|---|---|---|---|---|",
    ]
    for row in res["surfaces_table"]:
        lines.append(
            f"| {row['surface']} | {'yes' if row['imprint'] else 'no'} "
            f"| {_f(row['cohort1_rho'])} [{_f(row['cohort1_lo'])}, {_f(row['cohort1_hi'])}] "
            f"| {_f(row['bank2_rho'])} [{_f(row['bank2_lo'])}, {_f(row['bank2_hi'])}] "
            f"| {row['c3_reading']} |")
    lines += [
        "",
        "## Table 2 — bank-to-bank agreement (26 shared cells)",
        "",
        "| Bank-to-bank | Surface | Pearson [95% CI] | Spearman [95% CI] |",
        "|---|---|---|---|",
    ]
    for row in res["bank_to_bank_table"]:
        lines.append(
            f"| Bank-to-bank | {row['surface']} "
            f"| {_f(row['pearson'])} [{_f(row['pearson_lo'])}, {_f(row['pearson_hi'])}] "
            f"| {_f(row['spearman'])} [{_f(row['spearman_lo'])}, {_f(row['spearman_hi'])}] |")
    p = res["c3_pass"]
    lines += [
        "",
        "## C3 reading",
        "",
        f"Imprint dimensions whose bank-2 interval still excludes 0: "
        f"{', '.join(p['kept']) if p['kept'] else 'none'}. "
        f"Dropped (interval includes 0): {', '.join(p['dropped']) if p['dropped'] else 'none'}.",
        "",
        ("All four imprint intervals exclude 0 on bank 2: transport holds for the full imprint set."
         if p["all_imprint_keep"] else
         "Not every imprint interval excludes 0 on bank 2. The write-up names the dropped "
         "dimension(s) above and drops their transport sentence; the remaining imprint "
         "dimensions keep theirs. Patience and negative reciprocity are reported only."),
        "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="T2 bank-2 transport (C3)")
    ap.add_argument("--cohort1", default=str(COHORT1_STRICT))
    ap.add_argument("--bank2", default=str(ADAPTER_STRICT_V1))
    ap.add_argument("--gps-json", default=str(AS.DEFAULT_GPS_JSON))
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    ap.add_argument("--draws", type=int, default=DRAWS)
    ap.add_argument("--seed", type=int, default=SEED)
    a = ap.parse_args(argv)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    res = run(a.cohort1, a.bank2, a.gps_json, draws=a.draws, seed=a.seed)
    (out / JSON_NAME).write_text(json.dumps(res, indent=1) + "\n")
    (out / MD_NAME).write_text(render_note(res) + "\n")
    print(json.dumps(res["c3_pass"], indent=1))
    print("wrote", out / JSON_NAME)
    print("wrote", out / MD_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
