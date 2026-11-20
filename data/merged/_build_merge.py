#!/usr/bin/env python3
"""
SCA2 tier-2 evaluation surfaces: merge WVS7 and AmericasBarometer (2012–2019).

Produces four separate country×survey parquet files under data/merged/.
Does NOT row-stack WVS with AB. Does NOT touch GPS. Does NOT recode item values.

Founder decisions (2026-07-12):
  - OOS adapter evaluation surfaces, not panel econometrics
  - AB waves 2012–2019 only (ignore 2020–2023; exclude USA pretest)
  - WVS uses lab pre-registered WVS_ITEM_MAP from sca2_datagen.config
  - AB trust-core + demog + design/weights; broader common cols kept for audit
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd
import pyreadstat

DATA = Path(__file__).resolve().parent
MERGED = DATA / "merged"
REPO = DATA.parent


def _load_wvs_item_map() -> dict:
    """Parse WVS_ITEM_MAP as a pure literal from config.py (no package import, no exec).

    Avoids sca2_datagen.__init__ → litellm and avoids dataclass import side-effects.
    """
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


WVS_ITEM_MAP = _load_wvs_item_map()

# ---------------------------------------------------------------------------
# File maps (explicit — no filename-year guessing for AB)
# ---------------------------------------------------------------------------
USA_AB_FILES = {
    2012: DATA / "Barometer/USA_Barometer/241473079UnitedStates LAPOP AmericasBarometer 2012 Rev1_W.dta",
    2014: DATA / "Barometer/USA_Barometer/98099043UnitedStates LAPOP AmericasBarometer 2014 v3.0_W.dta",
    2017: DATA / "Barometer/USA_Barometer/2133069031United States LAPOP AmericasBarometer 2017 V1.0_W.dta",
    2019: DATA / "Barometer/USA_Barometer/UnitedStates LAPOP AmericasBarometer 2019 v1.0_W.dta",
}
MEX_AB_FILES = {
    2012: DATA / "Barometer/MEX_Barometer/641926122Mexico LAPOP AmericasBarometer 2012 Rev1_W.dta",
    2014: DATA / "Barometer/MEX_Barometer/534049480Mexico LAPOP AmericasBarometer 2014 v3.0_W.dta",
    2017: DATA / "Barometer/MEX_Barometer/275973272Mexico LAPOP AmericasBarometer 2017 V1.0_W.dta",
    2019: DATA / "Barometer/MEX_Barometer/Mexico LAPOP AmericasBarometer 2019 v1.0_W.dta",
}

# Trust-core + political-culture cluster + demog + design (lowercase canonical names)
AB_TRUST_CORE = [
    "it1",
    "b1", "b2", "b3", "b4", "b6",
    "b10a", "b12", "b13", "b18", "b21", "b31", "b32", "b37", "b47a",
    "exc6", "exc7",
    "ing4", "pn4", "dem2",
]
AB_DEMOG = ["q1", "q2", "ed", "q10"]
AB_DESIGN = ["wt", "weight1500", "upm", "strata", "estratopri", "estratosec", "estrato"]
AB_KEEP_ALWAYS = AB_TRUST_CORE + AB_DEMOG + AB_DESIGN

WVS_DEMOG = ["Q260", "Q261", "Q262", "Q275", "Q288"]
WVS_META = ["B_COUNTRY_ALPHA", "A_YEAR", "W_WEIGHT", "D_INTERVIEW"]


def _lower_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = pd.Index([str(c).lower() for c in out.columns])
    # if collisions after lowercasing, keep first
    if out.columns.duplicated().any():
        out = out.loc[:, ~out.columns.duplicated()]
    return out


def _read_dta(path: Path, usecols: list[str] | None = None) -> tuple[pd.DataFrame, dict]:
    """Read Stata; return df + variable labels (original case keys when possible)."""
    labels: dict = {}
    try:
        if usecols is None:
            df, meta = pyreadstat.read_dta(str(path))
        else:
            # pyreadstat needs exact case; read all then subset if selective fails
            try:
                df, meta = pyreadstat.read_dta(str(path), usecols=usecols)
            except Exception:
                df, meta = pyreadstat.read_dta(str(path))
        labels = meta.column_names_to_labels or {}
        return df, labels
    except Exception as e:
        print(f"  pyreadstat failed on {path.name}: {e}; trying pandas")
        if usecols:
            try:
                df = pd.read_stata(path, columns=usecols, convert_categoricals=False)
            except Exception:
                df = pd.read_stata(path, convert_categoricals=False)
        else:
            df = pd.read_stata(path, convert_categoricals=False)
        return df, labels


def merge_wvs() -> dict:
    path = DATA / "WVS" / "WVS_wave7.dta"
    print(f"\n=== WVS Wave 7: {path} ===")
    item_cols = list(WVS_ITEM_MAP.keys())
    want = list(dict.fromkeys(WVS_META + item_cols + WVS_DEMOG))

    # Column probe via pandas (handles encoding better for this file)
    probe = pd.read_stata(path, iterator=True, convert_categoricals=False)
    first = probe.read(1)
    available = set(first.columns)
    present = [c for c in want if c in available]
    missing = [c for c in want if c not in available]
    print(f"  requested={len(want)} present={len(present)} missing={missing}")

    df = pd.read_stata(path, columns=present, convert_categoricals=False)
    print(f"  total rows={len(df)}")

    # tier tags as long-form metadata (not per-row); stored in manifest
    tier_of = {k: v["tier"] for k, v in WVS_ITEM_MAP.items()}
    dim_of = {k: v["dim"] for k, v in WVS_ITEM_MAP.items()}
    label_of = {k: v["label"] for k, v in WVS_ITEM_MAP.items()}

    out_info = {}
    for country, year, fname in [
        ("USA", 2017, "USA_WVS_wave7.parquet"),
        ("MEX", 2018, "MEX_WVS_wave7.parquet"),
    ]:
        sub = df[(df["B_COUNTRY_ALPHA"] == country) & (df["A_YEAR"] == year)].copy()
        # fallback if year filter too strict
        if len(sub) == 0:
            sub = df[df["B_COUNTRY_ALPHA"] == country].copy()
            print(f"  WARN {country}: year filter empty; using all years for country")
        sub.insert(0, "survey", "WVS_wave7")
        sub.insert(1, "country", country)
        sub.insert(2, "year", sub["A_YEAR"].astype(int) if "A_YEAR" in sub.columns else year)
        sub.insert(3, "source_file", path.name)
        # rename weight for clarity (keep original too)
        if "W_WEIGHT" in sub.columns:
            sub["weight"] = sub["W_WEIGHT"]
        out_path = MERGED / fname
        sub.to_parquet(out_path, index=False)
        # item non-null rates
        item_nn = {
            c: float(sub[c].notna().mean())
            for c in item_cols
            if c in sub.columns
        }
        out_info[fname] = {
            "path": str(out_path),
            "n": int(len(sub)),
            "ncols": int(sub.shape[1]),
            "years": sorted(sub["year"].dropna().unique().tolist()),
            "country": country,
            "survey": "WVS_wave7",
            "weight_col": "W_WEIGHT" if "W_WEIGHT" in sub.columns else None,
            "weight_nonnull": float(sub["W_WEIGHT"].notna().mean()) if "W_WEIGHT" in sub.columns else None,
            "mapped_items_present": [c for c in item_cols if c in sub.columns],
            "mapped_items_missing": [c for c in item_cols if c not in sub.columns],
            "item_nonnull_rate": item_nn,
            "demog_present": [c for c in WVS_DEMOG if c in sub.columns],
        }
        print(f"  wrote {fname}: n={len(sub)} cols={sub.shape[1]} years={out_info[fname]['years']}")

    out_info["_wvs_item_map"] = {
        k: {"dim": dim_of[k], "tier": tier_of[k], "label": label_of[k]}
        for k in item_cols
    }
    out_info["_wvs_missing_from_file"] = missing
    return out_info


def _select_ab_columns(df_lower: pd.DataFrame, min_wave_support: int, col_counts: dict[str, int]) -> list[str]:
    """Keep trust-core/demog/design if present + any col in ≥ min_wave_support waves."""
    keep = set()
    for c in AB_KEEP_ALWAYS:
        if c in df_lower.columns:
            keep.add(c)
    # also keep common exploratory columns that appear often
    for c, n in col_counts.items():
        if n >= min_wave_support and not c.startswith("_"):
            # skip pure admin noise if huge — still keep if common
            keep.add(c)
    # never keep raw fecha as primary year (we add year)
    return sorted(keep)


def merge_ab_country(country: str, filemap: dict[int, Path]) -> dict:
    print(f"\n=== AmericasBarometer {country} 2012–2019 ===")
    waves: list[pd.DataFrame] = []
    wave_meta: list[dict] = []
    col_counts: dict[str, int] = {}
    labels_by_wave: dict[int, dict] = {}

    for year, path in sorted(filemap.items()):
        if not path.exists():
            raise FileNotFoundError(path)
        print(f"  reading {year}: {path.name}")
        raw, labels = _read_dta(path)
        labels_by_wave[year] = {str(k).lower(): v for k, v in (labels or {}).items()}
        df = _lower_cols(raw)
        for c in df.columns:
            col_counts[c] = col_counts.get(c, 0) + 1

        # year provenance: always use explicit map year (2019 files have wave=2018).
        # Many waves already contain lowercase `year` / `wave` after lowercasing —
        # rename those first so insert does not collide.
        df = df.copy()
        if "year" in df.columns:
            df = df.rename(columns={"year": "year_lapop_raw"})
        if "wave" in df.columns and "wave_raw" not in df.columns:
            df = df.rename(columns={"wave": "wave_raw"})
        df.insert(0, "survey", "AmericasBarometer")
        df.insert(1, "country", country)
        df.insert(2, "year", year)
        df.insert(3, "source_file", path.name)

        # weight usability
        wt_notes = []
        if "wt" in df.columns:
            wt_notes.append(f"wt nonnull={df['wt'].notna().mean():.3f}")
        if "weight1500" in df.columns:
            wt_notes.append(f"weight1500 nonnull={df['weight1500'].notna().mean():.3f}")
        if not wt_notes:
            wt_notes.append("NO standard wt/weight1500")

        core_present = [c for c in AB_TRUST_CORE if c in df.columns]
        core_missing = [c for c in AB_TRUST_CORE if c not in df.columns]
        wave_meta.append(
            {
                "year": year,
                "source_file": path.name,
                "n": int(len(df)),
                "ncols_raw": int(df.shape[1]),
                "trust_core_present": core_present,
                "trust_core_missing": core_missing,
                "weight_notes": wt_notes,
                "has_wt": "wt" in df.columns,
                "has_weight1500": "weight1500" in df.columns,
            }
        )
        print(
            f"    n={len(df)} cols={df.shape[1]} core={len(core_present)}/{len(AB_TRUST_CORE)} "
            f"missing_core={core_missing} weights={wt_notes}"
        )
        waves.append(df)

    # EVAL-ONLY columns: trust-core + demog + design + provenance.
    # Do NOT outer-union all LAPOP admin columns — mixed dtypes (e.g. idnum
    # as int in one wave and scientific-notation string in another) break parquet.
    provenance = ["survey", "country", "year", "source_file"]
    audit_cols = ["wave_raw", "year_lapop_raw"]
    retain = list(dict.fromkeys(provenance + audit_cols + AB_TRUST_CORE + AB_DEMOG + AB_DESIGN))

    aligned = []
    for w in waves:
        cols = [c for c in retain if c in w.columns]
        aligned.append(w[cols].copy())

    panel = pd.concat(aligned, axis=0, ignore_index=True, sort=False)

    # unified weight: prefer wt, else weight1500 (assign after copy to avoid fragmentation)
    panel = panel.copy()
    if "wt" in panel.columns:
        panel["weight"] = panel["wt"]
    elif "weight1500" in panel.columns:
        panel["weight"] = panel["weight1500"]
    else:
        panel["weight"] = pd.NA

    # Coerce object columns to string so mixed wave dtypes never break parquet
    for c in panel.columns:
        if panel[c].dtype == object:
            panel[c] = panel[c].astype("string")

    fname = f"{country}_Barometer_2012_2019.parquet"
    out_path = MERGED / fname
    panel.to_parquet(out_path, index=False)

    # per-year core nonnull
    core_coverage = {}
    for year in sorted(panel["year"].unique()):
        sub = panel[panel["year"] == year]
        core_coverage[int(year)] = {
            c: float(sub[c].notna().mean()) if c in sub.columns else None
            for c in AB_TRUST_CORE
        }

    info = {
        "path": str(out_path),
        "n": int(len(panel)),
        "ncols": int(panel.shape[1]),
        "years": sorted(int(y) for y in panel["year"].unique()),
        "n_by_year": {int(y): int((panel["year"] == y).sum()) for y in panel["year"].unique()},
        "country": country,
        "survey": "AmericasBarometer",
        "waves": wave_meta,
        "trust_core": AB_TRUST_CORE,
        "demog": AB_DEMOG,
        "design": AB_DESIGN,
        "columns_retained": list(panel.columns),
        "core_nonnull_by_year": core_coverage,
        "col_wave_support": {c: col_counts.get(c, 0) for c in AB_TRUST_CORE},
    }
    print(f"  wrote {fname}: n={len(panel)} cols={panel.shape[1]} years={info['years']} by_year={info['n_by_year']}")
    return {fname: info}


def write_construct_map(manifest: dict) -> None:
    path = MERGED / "CONSTRUCT_MAP.md"
    lines = [
        "# Tier-2 Construct Map (GPS → WVS / AmericasBarometer)",
        "",
        "**Status:** evaluation surfaces only. Frozen DPO adapters; no retraining.",
        "**GPS:** identification / in-sample instrument — **not** merged here.",
        "**Years:** WVS USA 2017 / MEX 2018; AB 2012–2019 pooled within country.",
        "",
        "Strength tags: `clean` | `bridge` | `stretch` | `no-coverage`.",
        "",
        "## Summary table",
        "",
        "| GPS dim | WVS (pre-registered) | Strength | AB (trust-core focus) | Strength |",
        "|---------|----------------------|----------|-----------------------|----------|",
        "| trust | Q57, Q59, Q61–63, Q64, Q69–71 (t2); Q58, Q60, Q73 (t3) | clean | IT1; B1–B6; B10A/B12/B13/B21…; EXC6/7 | clean |",
        "| patience | Q13 thrift, Q14 perseverance, Q43 (t2); Q50 (t3) | bridge | — | no-coverage |",
        "| risktaking | Q106, Q107, Q109 (t2); Q178 (t3) | bridge | — | no-coverage |",
        "| posrecip | Q12, Q174 (t2); Q81 (t3) | bridge | CP* not in core extract | stretch / omitted |",
        "| negrecip | Q176, Q177, Q179 (t2); Q195 (t3) | bridge | EXC/JC partial only in core EXC | stretch |",
        "| altruism | Q101, Q99 (t2); Q103 (t3) | bridge | CP community help not in core | thin / omitted |",
        "",
        "## WVS item map (from `sca2_datagen.config.WVS_ITEM_MAP`)",
        "",
        "| Item | Dim | Tier | Label |",
        "|------|-----|------|-------|",
    ]
    for k, v in WVS_ITEM_MAP.items():
        lines.append(f"| {k} | {v['dim']} | {v['tier']} | {v['label']} |")

    lines += [
        "",
        "## AB trust-core items retained",
        "",
        "Canonical lowercase names in merged files:",
        "",
        "- Interpersonal: `it1`",
        "- System support: `b1` `b2` `b3` `b4` `b6`",
        "- Institutional trust (subset): `b10a` `b12` `b13` `b18` `b21` `b31` `b32` `b37` `b47a`",
        "- Corruption: `exc6` `exc7`",
        "- Democracy / system eval: `ing4` `pn4` `dem2`",
        "- Demographics: `q1` `q2` `ed` `q10`",
        "- Design/weights: `wt` `weight1500` `upm` `strata`/`estratopri`… + derived `weight`",
        "",
        "Per-wave presence is recorded in `_manifest.json` → `*.waves[].trust_core_missing`.",
        "",
        "## Files",
        "",
        "| File | Role |",
        "|------|------|",
        "| `USA_WVS_wave7.parquet` | USA WVS7 evaluation surface |",
        "| `MEX_WVS_wave7.parquet` | MEX WVS7 evaluation surface |",
        "| `USA_Barometer_2012_2019.parquet` | USA AB 2012–2019 evaluation surface |",
        "| `MEX_Barometer_2012_2019.parquet` | MEX AB 2012–2019 evaluation surface |",
        "| `_manifest.json` | row counts, weight notes, coverage |",
        "",
        "## Non-claims",
        "",
        "- Item wording is **not** identical across GPS training scenarios and these surveys.",
        "- AB does **not** cover all six GPS dimensions; score trust-core only for primary AB claims.",
        "- Values are **raw** (no reverse-coding in merge). Recodes belong in the scoring step.",
        "- Do **not** row-merge these four files across surveys.",
        "",
    ]
    path.write_text("\n".join(lines))
    print(f"\nWrote {path}")


def write_readme() -> None:
    path = MERGED / "README.md"
    path.write_text(
        """# Tier-2 evaluation surfaces (merged)

Four country×survey parquet files for **frozen** USA/MEX DPO adapter OOS evaluation.

See `CONSTRUCT_MAP.md` for GPS→WVS/AB construct mapping and `_manifest.json` for coverage.

- WVS: Wave 7, lab `WVS_ITEM_MAP` items + demog + `W_WEIGHT`
- AmericasBarometer: 2012–2019 only (post-2012 sampling window; 2020–2023 excluded)
- GPS: not included (in-sample identification instrument)
"""
    )


def main() -> None:
    MERGED.mkdir(parents=True, exist_ok=True)
    manifest: dict = {
        "description": "SCA2 tier-2 OOS evaluation surfaces",
        "created_by": "data/_merge_tier2.py",
        "decisions": {
            "ab_years": [2012, 2014, 2017, 2019],
            "ab_exclude": "pre-2012, 2020–2023, USA pretest",
            "wvs": "Wave 7 USA 2017 / MEX 2018; WVS_ITEM_MAP from sca2_datagen.config",
            "gps": "excluded from merge",
            "no_cross_survey_row_stack": True,
            "no_value_recodes_in_merge": True,
        },
        "files": {},
    }

    wvs_info = merge_wvs()
    for k, v in wvs_info.items():
        if k.startswith("_"):
            manifest[k] = v
        else:
            manifest["files"][k] = v

    for country, fmap in [("USA", USA_AB_FILES), ("MEX", MEX_AB_FILES)]:
        ab_info = merge_ab_country(country, fmap)
        manifest["files"].update(ab_info)

    man_path = MERGED / "_manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2, default=str))
    print(f"\nWrote {man_path}")

    write_construct_map(manifest)
    write_readme()

    # final verification print
    print("\n========== VERIFICATION ==========")
    for fname, info in manifest["files"].items():
        print(
            f"{fname}: n={info['n']} ncols={info['ncols']} years={info.get('years')} "
            f"country={info.get('country')}"
        )
        if "n_by_year" in info:
            print(f"  n_by_year={info['n_by_year']}")
        if "weight_col" in info:
            print(f"  weight={info.get('weight_col')} nonnull={info.get('weight_nonnull')}")
        if "waves" in info:
            for w in info["waves"]:
                print(
                    f"  wave {w['year']}: n={w['n']} core_missing={w['trust_core_missing']} "
                    f"{w['weight_notes']}"
                )

    # hard asserts
    assert manifest["files"]["USA_WVS_wave7.parquet"]["n"] > 2000
    assert manifest["files"]["MEX_WVS_wave7.parquet"]["n"] > 1500
    assert manifest["files"]["USA_Barometer_2012_2019.parquet"]["years"] == [2012, 2014, 2017, 2019]
    assert manifest["files"]["MEX_Barometer_2012_2019.parquet"]["years"] == [2012, 2014, 2017, 2019]
    usa_n = sum(manifest["files"]["USA_Barometer_2012_2019.parquet"]["n_by_year"].values())
    mex_n = sum(manifest["files"]["MEX_Barometer_2012_2019.parquet"]["n_by_year"].values())
    assert usa_n == 6000, usa_n  # 4 × 1500
    assert mex_n >= 6000, mex_n  # ~6238 (waves not exactly 1500)
    assert usa_n == manifest["files"]["USA_Barometer_2012_2019.parquet"]["n"]
    assert mex_n == manifest["files"]["MEX_Barometer_2012_2019.parquet"]["n"]
    print("\nASSERTS OK")


if __name__ == "__main__":
    main()
