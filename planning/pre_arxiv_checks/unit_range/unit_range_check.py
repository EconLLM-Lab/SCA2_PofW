#!/usr/bin/env python3
"""Retrospective raw vs 0-1 composite check on the frozen Paper A surface.

Does not call a model. Does not modify repository files.
Raw composite: unweighted mean of frozen recoded item scores (locked surface).
0-1 composite: same mean after mapping each item from its theoretical
post-recode range onto [0, 1]. Sample min/max are not used.

Run:
  cd /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW && \\
    env -u PYTHONPATH .venv/bin/python \\
    /Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/unit_range/unit_range_check.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
OUT = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/unit_range")
SCORES = REPO / "analysis/phase2/outputs/paper_a/country_item_scores.csv"
GPS_JSON = REPO / "synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json"
QUESTION_MAP = REPO / "DPO_eval_WVS/question_map_wvs_edited.csv"

PANEL16 = [
    "ARG", "BRA", "CHN", "DEU", "EGY", "GBR", "GRC", "IDN",
    "IND", "JPN", "MEX", "NGA", "NLD", "RUS", "TUR", "USA",
]
TRUST9 = ["Q57", "Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73"]
# Headline map. Patience items stay unpooled. Q69-Q71 are not in the trust composite.
SPECS = {
    "trust": TRUST9,
    "Q43": ["Q43"],
    "Q50": ["Q50"],
    "risktaking": ["Q106", "Q107", "Q109", "Q178"],
    "posrecip": ["Q81"],
    "negrecip": ["Q176", "Q177", "Q179", "Q195"],
    "altruism": ["Q99", "Q101", "Q103"],
}
GPS_KEY = {
    "trust": "trust",
    "Q43": "patience",
    "Q50": "patience",
    "risktaking": "risktaking",
    "posrecip": "posrecip",
    "negrecip": "negrecip",
    "altruism": "altruism",
}
# Items whose ranges are documented for the table but do not enter a composite here.
EXCLUDED_FROM_COMPOSITE = ["Q69", "Q70", "Q71"]
INVERT_1_4 = {
    "Q59", "Q61", "Q62", "Q63", "Q64", "Q69", "Q70", "Q71",
    "Q58", "Q60", "Q73", "Q81",
}
INVERT_10 = {"Q177", "Q179"}
BINARY = {"Q57"}
BOOT = 2000
BOOT_SEED = 20260905


def recode_value(raw: float, item: str) -> float:
    """Match analysis/phase2/22_paper_a_surface.py::recode_value."""
    s = float(raw)
    if item in INVERT_1_4:
        return 5.0 - s
    if item in INVERT_10:
        return 11.0 - s
    if item in BINARY:
        return 1.0 if s == 1.0 else 0.0
    return s


def spearman(a: pd.Series, b: pd.Series) -> float:
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if len(d) < 8 or d["a"].nunique() < 2 or d["b"].nunique() < 2:
        return float("nan")
    return float(spearmanr(d["a"], d["b"]).statistic)


def bootstrap_ci(a: pd.Series, b: pd.Series, seed: int = BOOT_SEED, reps: int = BOOT) -> tuple[float, float, float, int]:
    """Same country bootstrap as 22_paper_a_surface.bootstrap_ci.

    Returns point, lo, hi, and the count of finite bootstrap draws.
    The interval itself is np.quantile on the draw vector, including any NaNs,
    so it matches the reference function.
    """
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    n = len(d)
    if n < 8:
        return (float("nan"), float("nan"), float("nan"), 0)
    x = d["a"].to_numpy()
    y = d["b"].to_numpy()
    rng = np.random.default_rng(seed)
    rhos = np.empty(reps)
    for i in range(reps):
        idx = rng.integers(0, n, n)
        rhos[i] = spearmanr(x[idx], y[idx]).statistic
    point = float(spearmanr(x, y).statistic)
    return point, float(np.quantile(rhos, 0.025)), float(np.quantile(rhos, 0.975)), int(np.isfinite(rhos).sum())


def arm_composite(items: pd.DataFrame, arm: str, item_list: list[str], value_col: str) -> pd.Series:
    sub = items[(items.arm == arm) & (items.item.isin(item_list)) & (items.country.isin(PANEL16))]
    sub = sub[np.isfinite(sub[value_col])]
    return sub.groupby("country")[value_col].mean().reindex(PANEL16)


def parse_codes(text: str) -> list[float]:
    parts = [p.strip() for p in str(text).split(";") if p.strip() != ""]
    return [float(p) for p in parts]


def theoretical_ranges(question_map: pd.DataFrame) -> pd.DataFrame:
    """Theoretical post-recode min/max from instrument codes, not sample extrema."""
    rows = []
    needed = sorted({q for qs in SPECS.values() for q in qs} | set(EXCLUDED_FROM_COMPOSITE))
    qcol = "Question" if "Question" in question_map.columns else question_map.columns[1]
    for item in needed:
        hit = question_map.loc[question_map[qcol] == item]
        status = "used"
        note = "instrument ResponseCodes after paper recode"
        codes: list[float] = []
        lo = hi = float("nan")
        recode_name = "identity"
        response_type = ""
        if hit.empty:
            status = "unresolved"
            note = "item absent from question map; excluded from 0-1 composite"
        else:
            response_type = str(hit.iloc[0]["ResponseType"])
            raw_codes = hit.iloc[0]["ResponseCodes"]
            if pd.isna(raw_codes) or str(raw_codes).strip() == "":
                status = "unresolved"
                note = "ResponseCodes empty; excluded from 0-1 composite"
            else:
                try:
                    codes = parse_codes(str(raw_codes))
                except ValueError:
                    status = "unresolved"
                    note = f"ResponseCodes not numeric ({raw_codes!r}); excluded from 0-1 composite"
                else:
                    if item in INVERT_1_4:
                        recode_name = "5-v"
                    elif item in INVERT_10:
                        recode_name = "11-v"
                    elif item in BINARY:
                        recode_name = "1{v=1}"
                    recoded = [recode_value(c, item) for c in codes]
                    lo, hi = float(min(recoded)), float(max(recoded))
                    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
                        status = "unresolved"
                        note = "recoded theoretical range is empty or degenerate; excluded from 0-1 composite"
        if item in EXCLUDED_FROM_COMPOSITE and status == "used":
            status = "excluded"
            note = "not in the nine-item trust headline; not entered in either composite"
        rows.append({
            "item": item,
            "response_type": response_type,
            "response_codes": ";".join(str(int(c) if float(c).is_integer() else c) for c in codes),
            "recode": recode_name,
            "theo_min": lo,
            "theo_max": hi,
            "status": status,
            "note": note,
        })
    return pd.DataFrame(rows)


def excludes_zero(lo: float, hi: float) -> bool:
    return bool(np.isfinite(lo) and np.isfinite(hi) and (lo > 0.0 or hi < 0.0))


def fmt(x: float, digits: int = 6) -> str:
    if not np.isfinite(x):
        return "NA"
    return f"{x:.{digits}f}"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scores = pd.read_csv(SCORES)
    required = {"arm", "country", "item", "raw"}
    missing_cols = required - set(scores.columns)
    if missing_cols:
        raise SystemExit(f"frozen scores missing columns: {sorted(missing_cols)}")
    dup = scores.duplicated(["arm", "country", "item"]).sum()
    if dup:
        raise SystemExit(f"frozen scores have {dup} duplicate arm-country-item rows")

    z = json.loads(GPS_JSON.read_text())
    qmap = pd.read_csv(QUESTION_MAP)
    ranges = theoretical_ranges(qmap)
    unresolved = set(ranges.loc[ranges.status == "unresolved", "item"])
    used = ranges[ranges.status == "used"].set_index("item")

    # Unit score from theoretical post-recode range. Do not use the saved
    # `normalized` column as the estimator; compare against it only as a check.
    unit = scores.copy()
    unit["unit"] = np.nan
    for item, row in used.iterrows():
        mask = unit.item == item
        unit.loc[mask, "unit"] = (unit.loc[mask, "raw"] - row.theo_min) / (row.theo_max - row.theo_min)

    saved_check = "saved normalized column absent"
    if "normalized" in scores.columns:
        both = unit[unit.item.isin(used.index) & np.isfinite(unit.raw) & np.isfinite(unit.normalized)]
        if len(both) == 0:
            saved_check = "no overlapping finite saved normalized values"
        else:
            delta = (both.unit - both.normalized).abs()
            saved_check = (
                f"max |recomputed unit - saved normalized| = {float(delta.max()):.3e} "
                f"on {len(both)} cells (saved column is a check only, not the estimator)"
            )

    # Gate: reproduce locked adapter-GPS trust on the raw composite before any 0-1 claim.
    z_trust = pd.Series({c: float(z[c]["trust"]) for c in PANEL16})
    raw_adapter_trust = arm_composite(scores, "adapter", TRUST9, "raw")
    rho_gate = spearman(raw_adapter_trust, z_trust)
    if not np.isfinite(rho_gate) or abs(rho_gate - 0.80) > 0.005:
        raise SystemExit(
            f"STOP: adapter-GPS trust raw Spearman={rho_gate}; expected 0.80 within 0.005. "
            "No 0-1 comparison written."
        )

    trust_items_unit = [q for q in TRUST9 if q not in unresolved]
    if len(trust_items_unit) != len(TRUST9):
        dropped = [q for q in TRUST9 if q in unresolved]
        raise SystemExit(
            f"STOP: trust items with unresolved theoretical range {dropped}. "
            "Headline 0-1 trust composite would not be the nine-item surface."
        )

    arms = sorted(scores.loc[scores.country.isin(PANEL16), "arm"].unique())
    assoc_rows = []
    for dim, items in SPECS.items():
        items_unit = [q for q in items if q not in unresolved]
        gps = pd.Series({c: float(z[c][GPS_KEY[dim]]) for c in PANEL16})
        raw_by_arm = {arm: arm_composite(scores, arm, items, "raw") for arm in arms}
        unit_by_arm = {arm: arm_composite(unit, arm, items_unit, "unit") for arm in arms}
        targets = {"gps": gps}
        if "human" in raw_by_arm:
            targets["human"] = None  # filled per scale below
        for arm in arms:
            for target_name in ("gps", "human"):
                if target_name == "human" and arm == "human":
                    continue
                if target_name == "human" and "human" not in raw_by_arm:
                    continue
                for scale, series_map, item_list in (
                    ("raw", raw_by_arm, items),
                    ("unit", unit_by_arm, items_unit),
                ):
                    left = series_map[arm]
                    right = gps if target_name == "gps" else series_map["human"]
                    n = int(pd.concat([left, right], axis=1).dropna().shape[0])
                    rho = spearman(left, right)
                    ci_lo = ci_hi = float("nan")
                    n_boot_finite = 0
                    bootstrapped = (
                        dim == "trust" and arm == "adapter" and target_name == "gps"
                    )
                    if bootstrapped:
                        rho, ci_lo, ci_hi, n_boot_finite = bootstrap_ci(left, right)
                    assoc_rows.append({
                        "dimension": dim,
                        "gps_key": GPS_KEY[dim],
                        "items": " ".join(item_list),
                        "n_items": len(item_list),
                        "arm": arm,
                        "target": target_name,
                        "scale": scale,
                        "rho": rho,
                        "ci_lo": ci_lo,
                        "ci_hi": ci_hi,
                        "n_countries": n,
                        "n_boot_finite": n_boot_finite if bootstrapped else "",
                        "items_excluded_unresolved": " ".join(q for q in items if q in unresolved),
                    })

    assoc = pd.DataFrame(assoc_rows)

    def pair(dim: str, arm: str, target: str, scale: str) -> pd.Series:
        hit = assoc[(assoc.dimension == dim) & (assoc.arm == arm) & (assoc.target == target) & (assoc.scale == scale)]
        if len(hit) != 1:
            raise SystemExit(f"expected one row for {dim} {arm}-{target} {scale}, found {len(hit)}")
        return hit.iloc[0]

    raw_row = pair("trust", "adapter", "gps", "raw")
    unit_row = pair("trust", "adapter", "gps", "unit")
    raw_rho = float(raw_row.rho)
    unit_rho = float(unit_row.rho)
    raw_lo, raw_hi = float(raw_row.ci_lo), float(raw_row.ci_hi)
    unit_lo, unit_hi = float(unit_row.ci_lo), float(unit_row.ci_hi)
    if not all(np.isfinite(v) for v in (raw_rho, unit_rho, raw_lo, raw_hi, unit_lo, unit_hi)):
        raise SystemExit("STOP: trust adapter-GPS point or interval is not finite")

    sign_flip = (raw_rho > 0 and unit_rho < 0) or (raw_rho < 0 and unit_rho > 0) or (
        (raw_rho == 0) != (unit_rho == 0)
    )
    raw_r2 = round(raw_rho, 2)
    unit_r2 = round(unit_rho, 2)
    round2_move = abs(raw_r2 - unit_r2) >= 0.10 - 1e-12
    raw_excludes = excludes_zero(raw_lo, raw_hi)
    unit_excludes = excludes_zero(unit_lo, unit_hi)
    ci_status_change = raw_excludes != unit_excludes
    material = bool(sign_flip or round2_move or ci_status_change)
    reasons = []
    if sign_flip:
        reasons.append(
            f"sign flip: raw {raw_rho:.6f} vs unit {unit_rho:.6f}"
        )
    if round2_move:
        reasons.append(
            f"two-decimal point estimate moved by >= 0.10: {raw_r2:.2f} -> {unit_r2:.2f}"
        )
    if ci_status_change:
        reasons.append(
            f"95% interval zero-exclusion changed: raw excludes_zero={raw_excludes} "
            f"[{raw_lo:.6f}, {raw_hi:.6f}]; unit excludes_zero={unit_excludes} "
            f"[{unit_lo:.6f}, {unit_hi:.6f}]"
        )

    # Wide comparison for the required pairs, plus every other computed association.
    wide_rows = []
    keys = assoc[["dimension", "arm", "target", "gps_key", "n_items"]].drop_duplicates()
    for rec in keys.itertuples(index=False):
        r = pair(rec.dimension, rec.arm, rec.target, "raw")
        u = pair(rec.dimension, rec.arm, rec.target, "unit")
        wide_rows.append({
            "dimension": rec.dimension,
            "gps_key": rec.gps_key,
            "arm": rec.arm,
            "target": rec.target,
            "n_items_raw": int(r.n_items),
            "n_items_unit": int(u.n_items),
            "n_countries": int(r.n_countries),
            "raw_rho": float(r.rho),
            "unit_rho": float(u.rho),
            "delta_unit_minus_raw": float(u.rho) - float(r.rho),
            "raw_ci_lo": float(r.ci_lo) if rec.dimension == "trust" and rec.arm == "adapter" and rec.target == "gps" else np.nan,
            "raw_ci_hi": float(r.ci_hi) if rec.dimension == "trust" and rec.arm == "adapter" and rec.target == "gps" else np.nan,
            "unit_ci_lo": float(u.ci_lo) if rec.dimension == "trust" and rec.arm == "adapter" and rec.target == "gps" else np.nan,
            "unit_ci_hi": float(u.ci_hi) if rec.dimension == "trust" and rec.arm == "adapter" and rec.target == "gps" else np.nan,
            "sign_flip": bool(
                (float(r.rho) > 0 and float(u.rho) < 0) or (float(r.rho) < 0 and float(u.rho) > 0)
            ) if np.isfinite(r.rho) and np.isfinite(u.rho) else False,
            "round2_raw": round(float(r.rho), 2) if np.isfinite(r.rho) else np.nan,
            "round2_unit": round(float(u.rho), 2) if np.isfinite(u.rho) else np.nan,
        })
    wide = pd.DataFrame(wide_rows).sort_values(["dimension", "target", "arm"]).reset_index(drop=True)

    ranges_out = ranges.copy()
    ranges_out.insert(0, "record_type", "item_range")
    wide.insert(0, "record_type", "association")
    # One CSV, two record types. Association rows carry the Spearmans; range rows carry min/max.
    csv_path = OUT / "unit_range_comparison.csv"
    # Write associations as the primary table, ranges alongside via a second block is awkward
    # in one rectangular file. Store both with a record_type column and union of fields.
    combined = pd.concat([ranges_out, wide], ignore_index=True, sort=False)
    combined.to_csv(csv_path, index=False)

    # Required headline associations for the markdown table.
    focus_dims = list(SPECS)
    focus_pairs = [("adapter", "gps"), ("human", "gps"), ("adapter", "human")]
    lines = []
    lines.append("# Unit-range composite check")
    lines.append("")
    lines.append("Retrospective comparison of the locked raw composite with a 0-1 composite on the frozen 16-country surface. No model was called. Repository files were not modified.")
    lines.append("")
    lines.append("## Precedence")
    lines.append("")
    lines.append("**Label: retrospective.**")
    lines.append("")
    lines.append("Searched for a unit-range or 0-1 WVS composite specified before outcome inspection:")
    lines.append("")
    lines.append("- No analysis-plan file in the repository.")
    lines.append("- `protocols/gps_sign_dpo_wvs.toml` standardizes GPS z and records June 23 scorer 0-1 ratings on synthetic pairs. That is not a WVS item-composite specification.")
    lines.append("- `misc/position_paper/rewrite/appendix.tex` states that proposed dimension composites are unweighted averages of item means without standardizing ranges, and that unit-range recoding is a separate sensitivity in the saved audit. That sentence describes a post-outcome audit, not a pre-inspection spec.")
    lines.append("- `misc/presentation/presentation.tex` and `presentation_20260914.tex` say composites average item means without range standardization.")
    lines.append("- `Hermes/Projects/SCA2/PRE_ARXIV_CHECKLIST.md` (locked 2026-09-25) says no such spec was found in the draft and to treat the check as retrospective unless a file search finds one.")
    lines.append("")
    lines.append("No dated pre-inspection specification was found. The audit bundle `Hermes/Projects/SCA2_results_audit/key_results.json` later stores normalized-scale correlations. Those are saved post-audit results, not a spec that preceded outcome inspection, and they are not the numbers reported here. This check recomputes from `analysis/phase2/outputs/paper_a/country_item_scores.csv` column `raw` and from theoretical ranges.")
    lines.append("")
    lines.append("## Reproduction gate")
    lines.append("")
    lines.append(f"Adapter-GPS trust, nine items, arm `adapter`, raw composite: **{raw_rho:.6f}**. Absolute distance from 0.80 is {abs(raw_rho - 0.80):.6f}, inside 0.005. Gate passed.")
    lines.append("")
    lines.append("Country bootstrap matches `analysis/phase2/22_paper_a_surface.py`: 2000 draws, `numpy` Generator seed 20260905, percentile interval from `np.quantile` at 0.025 and 0.975. Patience Q43 and Q50 are not pooled. Trust uses Q57-Q64 and Q73, not Q69-Q71.")
    lines.append("")
    lines.append("## Theoretical ranges after recode")
    lines.append("")
    lines.append("Min and max are the minimum and maximum of the paper recode applied to the instrument `ResponseCodes` in `DPO_eval_WVS/question_map_wvs_edited.csv`. They are not the sample minimum or maximum of country means. An unresolved range would be excluded from the 0-1 composite. None of the mapped items was unresolved.")
    lines.append("")
    lines.append("| Item | Status | Response codes | Recode | Min | Max |")
    lines.append("|---|---|---|---|---:|---:|")
    for row in ranges.sort_values("item").itertuples(index=False):
        lines.append(
            f"| {row.item} | {row.status} | {row.response_codes} | {row.recode} | {row.theo_min:g} | {row.theo_max:g} |"
        )
    lines.append("")
    lines.append("Q69-Q71 are listed only to record that they are outside the headline trust composite. They are not in either composite in this check.")
    lines.append("")
    lines.append(f"Saved-column check: {saved_check}.")
    lines.append("")
    lines.append("Unit score for a used item is `(raw - min) / (max - min)`. The 0-1 composite is the unweighted country mean of those unit scores, on the same items as the raw composite.")
    lines.append("")
    lines.append("Within every non-trust mapped set, every used item has the same theoretical post-recode range, so the 0-1 map is a common affine transform and Spearman rank correlation is invariant. Trust is the only mapped composite that mixes ranges (Q57 on [0, 1]; Q58-Q64 and Q73 on [1, 4]).")
    lines.append("")
    lines.append("## Associations")
    lines.append("")
    lines.append("Spearman country-rank correlations. Intervals are reported for trust adapter-GPS only, as specified. Other arms present in the frozen file are in `unit_range_comparison.csv`.")
    lines.append("")
    lines.append("| Dimension | Association | Raw rho | 0-1 rho | Raw 95% interval | 0-1 95% interval |")
    lines.append("|---|---|---:|---:|---|---|")
    for dim in focus_dims:
        for arm, target in focus_pairs:
            r = pair(dim, arm, target, "raw")
            u = pair(dim, arm, target, "unit")
            if dim == "trust" and arm == "adapter" and target == "gps":
                raw_ci = f"[{raw_lo:.4f}, {raw_hi:.4f}]"
                unit_ci = f"[{unit_lo:.4f}, {unit_hi:.4f}]"
            else:
                raw_ci = ""
                unit_ci = ""
            lines.append(
                f"| {dim} | {arm}-{target} | {float(r.rho):.4f} | {float(u.rho):.4f} | {raw_ci} | {unit_ci} |"
            )
    lines.append("")
    lines.append("## Trust adapter-GPS materiality")
    lines.append("")
    lines.append(f"- Raw: {raw_rho:.6f} [{raw_lo:.6f}, {raw_hi:.6f}]; rounded to two decimals: {raw_r2:.2f}; excludes zero: {raw_excludes}.")
    lines.append(f"- 0-1: {unit_rho:.6f} [{unit_lo:.6f}, {unit_hi:.6f}]; rounded to two decimals: {unit_r2:.2f}; excludes zero: {unit_excludes}.")
    lines.append(f"- Sign flip: {sign_flip}.")
    lines.append(f"- Two-decimal move of 0.10 or more: {round2_move} (absolute move of rounded estimates = {abs(raw_r2 - unit_r2):.2f}).")
    lines.append(f"- Interval changes whether it excludes zero: {ci_status_change}.")
    lines.append(f"- **Material: {str(material).lower()}.**")
    if reasons:
        lines.append("- Reasons: " + "; ".join(reasons) + ".")
    else:
        lines.append("- No materiality flag fired. The 0-1 trust adapter-GPS estimate stays positive, rounds to the same two-decimal value as the raw estimate or moves by less than 0.10, and the interval does not change its zero-exclusion status.")
    lines.append("")
    lines.append("Finite bootstrap draws: raw " + str(int(raw_row.n_boot_finite)) + f"/{BOOT}; unit " + str(int(unit_row.n_boot_finite)) + f"/{BOOT}.")
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append(f"- Script: `{OUT / 'unit_range_check.py'}`")
    lines.append(f"- Comparison: `{csv_path}`")
    lines.append(f"- This note: `{OUT / 'UNIT_RANGE.md'}`")
    lines.append("")
    (OUT / "UNIT_RANGE.md").write_text("\n".join(lines) + "\n")

    summary = {
        "raw_adapter_gps_trust": raw_rho,
        "unit_adapter_gps_trust": unit_rho,
        "raw_ci": [raw_lo, raw_hi],
        "unit_ci": [unit_lo, unit_hi],
        "material": material,
        "material_reasons": reasons,
        "sign_flip": sign_flip,
        "round2_move": round2_move,
        "ci_status_change": ci_status_change,
        "raw_excludes_zero": raw_excludes,
        "unit_excludes_zero": unit_excludes,
        "precedence": "retrospective",
        "saved_check": saved_check,
        "unresolved_items": sorted(unresolved),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
