#!/usr/bin/env python3
"""
SCA2 WVS evaluation surfaces — all GPS ∩ WVS Wave 7 countries.

Produces one parquet per country under data/wvs_eval_full/ ({ISO3}_WVS_wave7.parquet)
plus _manifest.json, for the 42-country GPS ∩ WVS7 intersection.

Pipeline mirrors data/merged/_build_merge.py exactly (same WVS_ITEM_MAP, same
provenance columns, same ordering, no recodes) so the files are drop-in compatible
with DPO_eval_WVS notebooks. No cross-survey row-stacking; GPS not merged.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent          # .../SCA2_PofW/data
OUT = DATA / "wvs_eval_full"
REPO = DATA.parent

WVS_META = ["B_COUNTRY_ALPHA", "A_YEAR", "W_WEIGHT", "D_INTERVIEW"]
WVS_DEMOG = ["Q260", "Q261", "Q262", "Q275", "Q288"]


def _load_wvs_item_map() -> dict:
    """Parse WVS_ITEM_MAP as a pure literal from config.py (no package import)."""
    cfg_path = REPO / "synthetic_generation" / "sca2_datagen" / "config.py"
    src = cfg_path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "WVS_ITEM_MAP" for t in node.targets
        ):
            return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == "WVS_ITEM_MAP" and node.value is not None:
                return ast.literal_eval(node.value)
    raise RuntimeError(f"WVS_ITEM_MAP not found as a literal in {cfg_path}")


def main() -> None:
    WVS_ITEM_MAP = _load_wvs_item_map()
    item_cols = list(WVS_ITEM_MAP.keys())
    want = list(dict.fromkeys(WVS_META + item_cols + WVS_DEMOG))

    # --- country sets ------------------------------------------------------
    gps = pd.read_stata(DATA / "GPS/GPS_dataset_country_level/country_gps.dta",
                        convert_categoricals=False)
    gps_codes = set(gps["isocode"].dropna().unique())
    name_of = dict(zip(gps["isocode"], gps["country"]))

    probe = pd.read_stata(DATA / "WVS" / "WVS_wave7.dta", iterator=True,
                          convert_categoricals=False)
    first = probe.read(1)
    available = set(first.columns)
    missing = [c for c in want if c not in available]
    if missing:
        raise RuntimeError(f"requested columns missing from WVS file: {missing}")

    wvs_codes = set(pd.read_stata(DATA / "WVS" / "WVS_wave7.dta",
                                  convert_categoricals=False,
                                  columns=["B_COUNTRY_ALPHA"])["B_COUNTRY_ALPHA"].dropna().unique())
    countries = sorted(gps_codes & wvs_codes)
    print(f"GPS countries: {len(gps_codes)} | WVS7 countries: {len(wvs_codes)} "
          f"| INTERSECTION: {len(countries)}")

    # --- read full item frame once -----------------------------------------
    df = pd.read_stata(DATA / "WVS" / "WVS_wave7.dta", columns=want,
                       convert_categoricals=False)
    print(f"loaded {len(df)} rows, {df.shape[1]} cols")

    OUT.mkdir(parents=True, exist_ok=True)
    manifest: dict = {
        "description": "SCA2 WVS7 evaluation surfaces, GPS ∩ WVS Wave 7 intersection",
        "built_by": "data/wvs_eval_full/_build_wvs_eval_full.py",
        "n_countries": len(countries),
        "countries": countries,
        "country_names": {c: name_of.get(c, "?") for c in countries},
        "wvs_item_map": {
            k: {"dim": v["dim"], "tier": v["tier"], "label": v["label"]}
            for k, v in WVS_ITEM_MAP.items()
        },
        "files": {},
    }

    for c in countries:
        sub = df[df["B_COUNTRY_ALPHA"] == c].copy()
        if len(sub) == 0:
            raise RuntimeError(f"empty country: {c}")
        sub.insert(0, "survey", "WVS_wave7")
        sub.insert(1, "country", c)
        sub.insert(2, "year", sub["A_YEAR"].astype(int))
        sub.insert(3, "source_file", "WVS_wave7.dta")
        sub["weight"] = sub["W_WEIGHT"]
        # same int dtypes as merged/ files: ensure Q260..Q288 stay compact
        out_path = OUT / f"{c}_WVS_wave7.parquet"
        sub.to_parquet(out_path, index=False)

        item_nn = {i: float(sub[i].notna().mean()) for i in item_cols}
        manifest["files"][f"{c}_WVS_wave7.parquet"] = {
            "country": c,
            "name": name_of.get(c, "?"),
            "n": int(len(sub)),
            "ncols": int(sub.shape[1]),
            "fieldwork_year": int(sub["year"].iloc[0]),
            "years": sorted(sub["year"].dropna().unique().astype(int).tolist()),
            "item_nonnull_min": min(item_nn.values()),
            "item_nonnull_mean": round(sum(item_nn.values()) / len(item_nn), 4),
            "mapped_items_present": len([i for i in item_cols if i in sub.columns]),
        }
        print(f"  {c:5s} {name_of.get(c,'?'):22s} n={len(sub):5d} year={sub['year'].iloc[0]}")

    man_path = OUT / "_manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2, default=str))
    print(f"\nWrote {man_path}")

    # --- verification: schema parity with existing merged/ USA/MEX files -----
    print("\n=== VERIFICATION vs data/merged/ USA/MEX ===")
    ref = pd.read_parquet(DATA / "merged" / "USA_WVS_wave7.parquet")
    for c in ("USA", "MEX"):
        new = pd.read_parquet(OUT / f"{c}_WVS_wave7.parquet")
        old = pd.read_parquet(DATA / "merged" / f"{c}_WVS_wave7.parquet")
        same_cols = list(new.columns) == list(old.columns)
        same_dtypes = all(new[col].dtype == old[col].dtype for col in old.columns)
        same_n = len(new) == len(old)
        print(f"  {c}: n_new={len(new)} n_old={len(old)} match={same_n} | "
              f"cols_match={same_cols} dtypes_match={same_dtypes}")
        assert same_cols and same_dtypes and same_n, f"schema mismatch for {c}"
        assert list(new.columns) == list(ref.columns), "column order drift vs USA reference"

    # hard asserts on known anchors
    assert len(countries) == 42, f"expected 42 countries, got {len(countries)}"
    assert manifest["files"]["USA_WVS_wave7.parquet"]["n"] > 2000
    assert manifest["files"]["MEX_WVS_wave7.parquet"]["n"] > 1500
    assert all(
        f["mapped_items_present"] == 30 for f in manifest["files"].values()
    ), "a country is missing mapped items"
    print("\nASSERTS OK — 42 countries, all 30 items present everywhere")


if __name__ == "__main__":
    main()
