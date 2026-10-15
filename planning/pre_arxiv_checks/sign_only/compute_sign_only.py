#!/usr/bin/env python3
"""Sign-only trust check on the frozen Paper A 16x9 rectangle.

Reads frozen scores and GPS z. Does not call a model, retrain, or write
inside the repository. Stops before any new statistic if the locked
adapter-GPS Spearman is not reproduced.
"""
from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ConstantInputWarning, spearmanr

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
OUT = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/sign_only")
SCORES = REPO / "analysis" / "phase2" / "outputs" / "paper_a" / "country_item_scores.csv"
GPS_JSON = REPO / "synthetic_generation" / "outputs" / "gps_sign_relabel_all" / "gps_z_vectors.json"
LOCK = REPO / "analysis" / "phase2" / "outputs" / "paper_a" / "SURFACE_LOCK.json"

PANEL16 = [
    "ARG", "BRA", "CHN", "DEU", "EGY", "GBR", "GRC", "IDN",
    "IND", "JPN", "MEX", "NGA", "NLD", "RUS", "TUR", "USA",
]
TRUST9 = ["Q57", "Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73"]
BOOT = 2000
BOOT_SEED = 20260905
SANITY_TARGET = 0.80
SANITY_TOL = 0.005
LOCK_RECORDED = 0.7999999999999999


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def arm_composite(items: pd.DataFrame, arm: str, item_list: list[str], countries: list[str]) -> pd.Series:
    """Match analysis/phase2/22_paper_a_surface.py::arm_composite."""
    sub = items[(items.arm == arm) & (items.item.isin(item_list)) & (items.country.isin(countries))]
    sub = sub[np.isfinite(sub["raw"])]
    return sub.groupby("country")["raw"].mean().reindex(countries)


def spearman(a: pd.Series, b: pd.Series) -> float:
    """Match 22_paper_a_surface.spearman. NaN if n < 8 or either series lacks variation."""
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if len(d) < 8 or d["a"].nunique() < 2 or d["b"].nunique() < 2:
        return float("nan")
    return float(spearmanr(d["a"], d["b"]).statistic)


def bootstrap_ci(a: pd.Series, b: pd.Series, seed: int = BOOT_SEED, reps: int = BOOT):
    """Match 22_paper_a_surface.bootstrap_ci, plus a count of undefined replicates.

    The percentile uses np.quantile on the replicate vector, including NaNs.
    A single undefined replicate makes the interval NaN. That is the reference
    helper, not a repaired one.
    """
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    n = len(d)
    if n < 8:
        return float("nan"), float("nan"), float("nan"), 0, n
    x = d["a"].to_numpy()
    y = d["b"].to_numpy()
    rng = np.random.default_rng(seed)
    rhos = np.empty(reps)
    n_undefined = 0
    for i in range(reps):
        idx = rng.integers(0, n, n)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConstantInputWarning)
            stat = spearmanr(x[idx], y[idx]).statistic
        rhos[i] = stat
        if not np.isfinite(stat):
            n_undefined += 1
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConstantInputWarning)
        point = float(spearmanr(x, y).statistic)
    lo = float(np.quantile(rhos, 0.025))
    hi = float(np.quantile(rhos, 0.975))
    return point, lo, hi, n_undefined, n


def rank_biserial(y: pd.Series, sign: pd.Series) -> tuple[float, str]:
    """Rank-biserial of continuous y with binary sign in {0, 1}.

    r = (C - D) / (n1 * n0), where C counts pairs with y(sign=1) > y(sign=0)
    and D counts the reverse. Ties are in the denominator only.
    Equivalent to 2U/(n1*n0) - 1 with Mann-Whitney U for the sign=1 sample
    (ties = 0.5). Undefined if either sign class is empty.
    """
    d = pd.concat([y.rename("y"), sign.rename("s")], axis=1).dropna()
    y1 = d.loc[d["s"] == 1, "y"].to_numpy(dtype=float)
    y0 = d.loc[d["s"] == 0, "y"].to_numpy(dtype=float)
    n1, n0 = int(len(y1)), int(len(y0))
    if n1 == 0 or n0 == 0:
        return float("nan"), "undefined: one sign class is empty"
    diff = y1[:, None] - y0[None, :]
    c = int(np.sum(diff > 0))
    dcount = int(np.sum(diff < 0))
    ties = int(np.sum(diff == 0))
    r = (c - dcount) / (n1 * n0)
    return float(r), f"C={c}; D={dcount}; ties={ties}; n_sign1={n1}; n_sign0={n0}"


def fmt(x: float) -> str:
    if not np.isfinite(x):
        return ""
    return repr(float(x))


def side_status(adapter: pd.Series, z: pd.Series, countries: list[str]) -> tuple[str, float]:
    """Exploratory within-side Spearman. Not estimated if n < 8 or ranks do not vary."""
    n = len(countries)
    if n == 0:
        return f"n={n}; not estimated", float("nan")
    a = adapter.reindex(countries)
    zz = z.reindex(countries)
    d = pd.concat([a.rename("a"), zz.rename("b")], axis=1).dropna()
    n_obs = int(len(d))
    if n_obs < 8 or d["a"].nunique() < 2 or d["b"].nunique() < 2:
        return f"n={n_obs}; not estimated", float("nan")
    rho = float(spearmanr(d["a"], d["b"]).statistic)
    return f"exploratory; n={n_obs}; rho={rho!r}", rho


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not SCORES.exists() or not GPS_JSON.exists() or not LOCK.exists():
        raise SystemExit(f"MISSING INPUT scores={SCORES.exists()} gps={GPS_JSON.exists()} lock={LOCK.exists()}")

    scores_hash = sha256(SCORES)
    gps_hash = sha256(GPS_JSON)
    lock = json.loads(LOCK.read_text())
    hash_notes = []
    if scores_hash != lock.get("scores_sha256"):
        hash_notes.append(f"scores sha256 {scores_hash} != lock {lock.get('scores_sha256')}")
    if gps_hash != lock.get("gps_json_sha256"):
        hash_notes.append(f"gps sha256 {gps_hash} != lock {lock.get('gps_json_sha256')}")
    if hash_notes:
        raise SystemExit("SURFACE MISMATCH: " + "; ".join(hash_notes))

    items = pd.read_csv(SCORES)
    sub = items[(items.arm == "adapter") & (items.item.isin(TRUST9)) & (items.country.isin(PANEL16))].copy()
    if sub.duplicated(["country", "item"]).any():
        raise SystemExit("SURFACE MISMATCH: duplicate adapter country-item rows on the trust rectangle")
    counts = sub.groupby("country")["item"].nunique()
    if list(counts.reindex(PANEL16).fillna(0).astype(int)) != [9] * 16:
        raise SystemExit(f"SURFACE MISMATCH: trust rectangle is not 16x9; counts={counts.to_dict()}")
    if not np.isfinite(sub["raw"].astype(float)).all():
        raise SystemExit("SURFACE MISMATCH: non-finite adapter raw on the trust rectangle")

    zmap = json.loads(GPS_JSON.read_text())
    missing = [c for c in PANEL16 if c not in zmap or "trust" not in zmap[c]]
    if missing:
        raise SystemExit(f"SURFACE MISMATCH: GPS trust missing for {missing}")
    z16 = pd.Series({c: float(zmap[c]["trust"]) for c in PANEL16}, dtype=float)
    if not np.isfinite(z16.to_numpy()).all():
        raise SystemExit("SURFACE MISMATCH: non-finite GPS trust z")

    adapter16 = arm_composite(items, "adapter", TRUST9, PANEL16)
    if adapter16.isna().any():
        raise SystemExit(f"SURFACE MISMATCH: adapter composite missing for {list(adapter16.index[adapter16.isna()])}")

    rho_a = spearman(adapter16, z16)
    recorded = float(lock["adapter_gps_trust_16x9"])
    if not np.isfinite(rho_a) or abs(rho_a - SANITY_TARGET) > SANITY_TOL or abs(rho_a - recorded) > SANITY_TOL:
        raise SystemExit(
            "SURFACE MISMATCH: "
            f"adapter-GPS trust={rho_a!r}, lock={recorded!r}, target={SANITY_TARGET}. "
            "Stopped before new statistics."
        )
    if abs(recorded - LOCK_RECORDED) > 0:
        raise SystemExit(f"SURFACE MISMATCH: lock file value {recorded!r} is not the expected {LOCK_RECORDED!r}")

    # Sign rule: exact zero is nonnegative. z is the GPS json coordinate.
    positive = [c for c in PANEL16 if z16[c] > 0.0]
    negative = [c for c in PANEL16 if z16[c] < 0.0]
    zeros = [c for c in PANEL16 if z16[c] == 0.0]
    if len(positive) + len(negative) + len(zeros) != 16:
        raise SystemExit("SIGN RULE FAILURE: a z value was neither >0, <0, nor ==0")
    sign = pd.Series({c: 1.0 if z16[c] >= 0.0 else 0.0 for c in PANEL16}, dtype=float)
    sign_pos = [c for c in PANEL16 if sign[c] == 1.0]
    sign_neg = [c for c in PANEL16 if sign[c] == 0.0]

    sign_varies = int(sign.nunique()) >= 2
    if not sign_varies:
        rho_sz = float("nan")
        ci_lo = float("nan")
        ci_hi = float("nan")
        n_undef = 0
        n_boot = 16
        sign_note = "sign has no variation; Spearman not defined"
    else:
        rho_sz = spearman(sign, z16)
        point_b, ci_lo, ci_hi, n_undef, n_boot = bootstrap_ci(sign, z16)
        if np.isfinite(rho_sz) and abs(point_b - rho_sz) > 1e-12:
            raise SystemExit(f"INTERNAL: bootstrap point {point_b!r} != spearman {rho_sz!r}")
        if np.isfinite(rho_sz) and np.isfinite(ci_lo) and np.isfinite(ci_hi):
            sign_note = "defined; country bootstrap matches 22_paper_a_surface.bootstrap_ci"
        elif np.isfinite(rho_sz):
            sign_note = (
                "point defined; 95% interval not defined under the reference helper "
                f"because {n_undef} of {BOOT} resamples had undefined Spearman and np.quantile propagates NaN"
            )
        else:
            sign_note = "Spearman not defined"

    if sign_neg and sign_pos:
        mean_pos = float(adapter16.reindex(sign_pos).mean())
        mean_neg = float(adapter16.reindex(sign_neg).mean())
        diff = mean_pos - mean_neg
        diff_note = "mean adapter trust composite, positive-sign (z>=0) minus negative-sign (z<0)"
    else:
        mean_pos = float("nan")
        mean_neg = float("nan")
        diff = float("nan")
        diff_note = "undefined: one sign class is empty"

    rb, rb_note = rank_biserial(adapter16, sign)
    inversions = [
        f"{a} adapter {float(adapter16[a])!r} < {b} adapter {float(adapter16[b])!r}"
        for a in sign_pos
        for b in sign_neg
        if float(adapter16[a]) < float(adapter16[b])
    ]
    if not sign_pos or not sign_neg:
        inversion_note = "Pairwise inversions not defined because one sign class is empty."
    elif not inversions:
        inversion_note = "No pairwise inversion: every positive-sign adapter composite exceeds every negative-sign composite."
    else:
        inversion_note = "Pairwise inversions (positive-sign composite below a negative-sign composite): " + "; ".join(inversions) + "."
    within_pos_text, within_pos_rho = side_status(adapter16, z16, sign_pos)
    within_neg_text, within_neg_rho = side_status(adapter16, z16, sign_neg)

    near = [f"{c} ({float(z16[c])!r})" for c in PANEL16 if abs(float(z16[c])) < 0.05]

    country_rows = []
    for c in PANEL16:
        country_rows.append({
            "record_type": "country",
            "country": c,
            "z_trust": float(z16[c]),
            "sign": int(sign[c]),
            "adapter_composite": float(adapter16[c]),
            "statistic": "",
            "estimate": "",
            "ci_lo": "",
            "ci_hi": "",
            "n": "",
            "detail": "exact_zero" if c in zeros else ("positive" if c in positive else "negative"),
            "status": "",
            "notes": "",
        })

    def stat_row(name: str, estimate, n, detail: str, status: str, notes: str, ci_lo="", ci_hi="") -> dict:
        return {
            "record_type": "statistic",
            "country": "",
            "z_trust": "",
            "sign": "",
            "adapter_composite": "",
            "statistic": name,
            "estimate": "" if estimate is None or (isinstance(estimate, float) and not np.isfinite(estimate)) else estimate,
            "ci_lo": "" if ci_lo == "" or (isinstance(ci_lo, float) and not np.isfinite(ci_lo)) else ci_lo,
            "ci_hi": "" if ci_hi == "" or (isinstance(ci_hi, float) and not np.isfinite(ci_hi)) else ci_hi,
            "n": n,
            "detail": detail,
            "status": status,
            "notes": notes,
        }

    stat_rows = [
        stat_row(
            "sanity_adapter_gps_spearman",
            rho_a,
            16,
            "16x9 adapter raw mean vs GPS json trust z",
            "reproduced",
            f"lock={recorded!r}; abs(rho-0.80)={abs(rho_a - 0.80)!r}; tolerance={SANITY_TOL}",
        ),
        stat_row(
            "sign_vs_z_spearman",
            rho_sz,
            16,
            "binary sign vs continuous GPS z; does not use the adapter",
            "defined" if np.isfinite(rho_sz) else "not defined",
            sign_note,
            ci_lo if np.isfinite(rho_sz) else "",
            ci_hi if np.isfinite(rho_sz) else "",
        ),
        stat_row(
            "sign_vs_z_boot_n_undefined",
            n_undef if sign_varies else "",
            BOOT if sign_varies else 0,
            f"seed={BOOT_SEED}; reps={BOOT}",
            "diagnostic",
            "count of resamples with undefined Spearman; not an interval",
        ),
        stat_row("n_positive", len(positive), len(positive), " ".join(positive), "count", "z_trust > 0"),
        stat_row("n_negative", len(negative), len(negative), " ".join(negative), "count", "z_trust < 0"),
        stat_row("n_zero", len(zeros), len(zeros), " ".join(zeros), "count", "z_trust == 0; assigned to nonnegative sign"),
        stat_row(
            "between_sign_adapter_diff",
            diff,
            len(sign_pos) + len(sign_neg),
            f"mean_pos={mean_pos!r}; mean_neg={mean_neg!r}",
            "defined" if np.isfinite(diff) else "not defined",
            diff_note,
        ),
        stat_row(
            "rank_biserial_adapter_vs_sign",
            rb,
            len(sign_pos) + len(sign_neg),
            rb_note,
            "defined" if np.isfinite(rb) else "not defined",
            "positive r: higher adapter composite on the nonnegative GPS-trust side",
        ),
        stat_row(
            "within_positive_spearman",
            within_pos_rho,
            len(sign_pos),
            " ".join(sign_pos),
            within_pos_text,
            "exploratory; positive-sign class is z>=0, including exact zeros",
        ),
        stat_row(
            "within_negative_spearman",
            within_neg_rho,
            len(sign_neg),
            " ".join(sign_neg),
            within_neg_text,
            "exploratory; negative-sign class is z<0",
        ),
    ]

    tab = pd.DataFrame(country_rows + stat_rows)
    csv_path = OUT / "sign_only_results.csv"
    tab.to_csv(csv_path, index=False)

    def rho_text(x: float) -> str:
        return "not defined" if not np.isfinite(x) else repr(float(x))

    if np.isfinite(ci_lo) and np.isfinite(ci_hi):
        ci_text = f"[{ci_lo!r}, {ci_hi!r}]"
    else:
        ci_text = "not defined"

    md = f"""# Sign-only trust check

Pre-arXiv check on frozen scores. Not a claim-lock amendment. No model call, no retrain, no manuscript edit.

## Sanity

Adapter–GPS Spearman on the 16×9 rectangle, matching `arm_composite` and `spearman` in `analysis/phase2/22_paper_a_surface.py`: `{rho_a!r}`.

`SURFACE_LOCK.json` records `{recorded!r}`. Absolute difference from 0.80 is `{abs(rho_a - SANITY_TARGET)!r}`, inside 0.005. Scores sha256 and GPS json sha256 match the lock file. New statistics below were computed only after that check.

The rectangle is 16 countries × 9 trust items (Q57–Q64, Q73), one finite adapter `raw` row per cell. The composite is the country mean of `raw`.

## Sign rule

`s = 1` if GPS trust `z >= 0`, else `0`. Exact zero, if any, is nonnegative. `z` is the `trust` coordinate in `gps_z_vectors.json`, not the adapter score.

## Counts

| Side | Rule | n | Countries |
|---|---|---:|---|
| Positive | z > 0 | {len(positive)} | {" ".join(positive) if positive else "(none)"} |
| Negative | z < 0 | {len(negative)} | {" ".join(negative) if negative else "(none)"} |
| Exact zero | z == 0 | {len(zeros)} | {" ".join(zeros) if zeros else "(none)"} |

Positive-sign class used in the contrasts is z ≥ 0 ({len(sign_pos)} countries: {" ".join(sign_pos) if sign_pos else "(none)"}). Negative-sign class is z < 0 ({len(sign_neg)} countries: {" ".join(sign_neg) if sign_neg else "(none)"}).

Countries with |z| < 0.05: {"; ".join(near) if near else "(none)"}. Classification uses exact comparison, not a tolerance.

## Sign versus continuous z

Spearman of the binary sign with continuous GPS z on the same 16 countries: {rho_text(rho_sz)}.

This number does not use the adapter. It is a property of the threshold split of GPS z on this panel. Within each sign, z still varies, so the correlation is not 1 by construction.

Country bootstrap, same helper as `22_paper_a_surface.bootstrap_ci`: 2000 resamples, seed 20260905, percentile 2.5/97.5. Interval: {ci_text}. Undefined resamples: {n_undef if sign_varies else "not run"}. Status: {sign_note}.

## Adapter contrast by sign

Mean adapter trust composite, positive-sign minus negative-sign: {rho_text(diff)}.

Positive-sign mean: {rho_text(mean_pos)}. Negative-sign mean: {rho_text(mean_neg)}. {diff_note}.

Rank-biserial correlation of the adapter composite with the sign: {rho_text(rb)}. {rb_note}. Definition: (C − D) / (n1 × n0), C = pairs with higher adapter composite on the positive sign, D = the reverse, ties in the denominator only. Positive means the nonnegative GPS-trust side has the higher adapter composite. {inversion_note}

## Within-sign association with continuous z

Both are exploratory. A side with fewer than 8 countries, or with no rank variation in the adapter composite or in z, is not estimated.

- Within positive-sign (z ≥ 0): {within_pos_text}.
- Within negative-sign (z < 0): {within_neg_text}.

## What this file does not say

- It does not amend the claim lock and does not add a paper number.
- The sign-versus-z Spearman is not evidence that the adapter recovered GPS.
- The between-sign adapter difference is a descriptive contrast on this convenience panel, not a sign-retrain.
"""
    md_path = OUT / "SIGN_ONLY.md"
    md_path.write_text(md)

    summary = {
        "sanity_adapter_gps": rho_a,
        "sign_vs_z_spearman": None if not np.isfinite(rho_sz) else rho_sz,
        "sign_vs_z_ci": [None if not np.isfinite(ci_lo) else ci_lo, None if not np.isfinite(ci_hi) else ci_hi],
        "sign_vs_z_note": sign_note,
        "n_boot_undefined": int(n_undef) if sign_varies else None,
        "n_positive": len(positive),
        "n_negative": len(negative),
        "n_zero": len(zeros),
        "positive": positive,
        "negative": negative,
        "zeros": zeros,
        "between_sign_adapter_diff": None if not np.isfinite(diff) else diff,
        "mean_pos": None if not np.isfinite(mean_pos) else mean_pos,
        "mean_neg": None if not np.isfinite(mean_neg) else mean_neg,
        "rank_biserial": None if not np.isfinite(rb) else rb,
        "rank_biserial_note": rb_note,
        "within_positive": within_pos_text,
        "within_negative": within_neg_text,
        "report_path": str(md_path),
        "csv_path": str(csv_path),
        "scores_sha256": scores_hash,
        "gps_json_sha256": gps_hash,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
