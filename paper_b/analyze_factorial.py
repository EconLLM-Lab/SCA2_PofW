#!/usr/bin/env python3
"""Phase F2 driver: factorial effect matrices, bank robustness, readout-variant stability.

Inputs are the scorer's long option-probability files (columns model, eval_country,
question_id, option_code, model_prob), one per route/variant. Each unit's surface
composite is the frozen-recode expected value (analyze_surface.model_item_table),
averaged over the surface's items (patience kept as two surfaces). Units are the 64
sign profiles; a row's unit is its eval_country.

Outputs (to --out):
  mtmm_<route>.csv           6 x 7 main-effect matrix (rows = sign bit, cols = surface)
  mtmm_<route>_cells.csv     every cell with OLS t and Lenth t
  mtmm_summary.json          diagonal dominance per route (with chance and binomial p)
  bank_robustness.csv        per surface: bank-2 profile composite vs cohort-1 (cell means
                             of sign-mate countries) over the shared cells
  readout_variants.csv       per surface: max |composite - v1| across units, per variant,
                             and diagonal dominance per variant
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "heldout"))
import analyze_surface as AS  # noqa: E402
import factorial as F  # noqa: E402
import factorial_effects as FE  # noqa: E402
from ceiling import surface_items  # noqa: E402


def unit_composites(probs: pd.DataFrame, unit_col: str = "eval_country") -> pd.DataFrame:
    """Long (unit, surface, composite) from scorer probabilities."""
    items = AS.model_item_table(probs.rename(columns={unit_col: "eval_country"}))
    rows = []
    for unit, g in items.groupby("country"):
        for surface, qs in surface_items(AS.STRICT_ITEMS).items():
            s = g[g.item.isin(qs)]
            if s.item.nunique() != len(qs):
                continue
            rows.append({"unit": unit, "surface": surface, "composite": float(s.e_recode.mean())})
    return pd.DataFrame(rows)


def mtmm(comp: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    comp = comp[comp.unit.isin(F.all_units())]
    return FE.effect_matrix(comp), FE.fit(comp), FE.diagonal_dominance(FE.effect_matrix(comp))


def cohort1_cells(comp_countries: pd.DataFrame, gps_json: Path) -> pd.DataFrame:
    """Cohort-1 country composites -> mean over sign-mates in the same factorial cell."""
    raw = json.loads(Path(gps_json).read_text())
    c = comp_countries.assign(unit=[F.unit_of_z(raw[cc]) for cc in comp_countries.unit])
    return c.groupby(["unit", "surface"], as_index=False).composite.mean()


def bank_robustness(bank2: pd.DataFrame, cohort1: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for surface in sorted(set(bank2.surface) & set(cohort1.surface)):
        a = cohort1[cohort1.surface == surface].set_index("unit").composite
        b = bank2[bank2.surface == surface].set_index("unit").composite
        rows.append({"surface": surface, **FE.bank_contract(a, b)})
    return pd.DataFrame(rows)


def readout_variants(v1: pd.DataFrame, variants: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    base = v1.set_index(["unit", "surface"]).composite
    for name, comp in variants.items():
        d = (comp.set_index(["unit", "surface"]).composite - base).dropna()
        dd = FE.diagonal_dominance(FE.effect_matrix(comp[comp.unit.isin(F.all_units())]))
        for surface, s in d.groupby(level="surface"):
            rows.append({"variant": name, "surface": surface, "units": int(len(s)),
                         "max_abs_dev": float(s.abs().max()), "mean_abs_dev": float(s.abs().mean()),
                         "diag_hits": dd["hits"]})
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--adapter", required=True, help="bank-2 profile probabilities (v1)")
    ap.add_argument("--signprompt", default=None, help="64 sign-prompt profile probabilities (v1)")
    ap.add_argument("--cohort1", default=None, help="cohort-1 country adapter probabilities (v1)")
    ap.add_argument("--variant", action="append", default=[],
                    help="name=path for a readout variant of the adapter route")
    ap.add_argument("--gps-json", default=str(AS.DEFAULT_GPS_JSON))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    summary = {}
    routes = {"adapter": a.adapter, "signprompt": a.signprompt}
    comps = {}
    for route, path in routes.items():
        if not path:
            continue
        comps[route] = unit_composites(pd.read_csv(path))
        m, cells, dd = mtmm(comps[route])
        m.to_csv(out / f"mtmm_{route}.csv")
        cells.to_csv(out / f"mtmm_{route}_cells.csv", index=False)
        summary[route] = dd
    (out / "mtmm_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    if a.cohort1:
        c1 = cohort1_cells(unit_composites(pd.read_csv(a.cohort1)), Path(a.gps_json))
        bank_robustness(comps["adapter"], c1).to_csv(out / "bank_robustness.csv", index=False)
    if a.variant:
        vs = {kv.split("=", 1)[0]: unit_composites(pd.read_csv(kv.split("=", 1)[1]))
              for kv in a.variant}
        readout_variants(comps["adapter"], vs).to_csv(out / "readout_variants.csv", index=False)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
