#!/usr/bin/env python3
"""Stream B — WVS human demographic gradients for SCA2 validity.

For each GPS dimension, regress the protocol's respondent-level WVS facet
scores on demographics (sex, age, age^2, education) and compare the signs of
the resulting gradients to the GPS individual-level benchmark (Stream A).

Benchmark source (criterion side):
  Falk, Becker, Dohmen, Enke, Huffman & Sunde (2018, QJE), Table 5,
  country-FE specification, coefficient on "1 if female" etc.
  -> GPS gender coding confirmed: gender == 1 means female (sign agreement
     with the published table across all six dimensions).

WVS demographics (verified from the local Codebook.pdf):
  Q260  Sex: 1 = Male, 2 = Female
  Q262  Age: numeric years
  Q275  Education: ISCED 2011, 0 (none) .. 8 (doctorate)
  Q275R Education recoded: 1 = Lower, 2 = Middle, 3 = Higher

Method (per demographic_gradient_protocol.md, Stream B):
  - facet scores: respondent-level, frozen protocol.yaml recipe
    (normalize -> direction -> facet mean over non-missing items)
  - OLS: facet ~ female + age/100 + (age/100)^2 + education
  - specs: USA-only, MEX-only, pooled all WVS countries with country FE
  - sign-agreement vs the GPS benchmark on the stable gradients
    (gender: all six dims; cognitive/education: all six dims;
     age-shape: patience, risk, posrecip, negrecip)

Outputs (data/validity/, reproducible):
  - gradients_wvs.csv        coefficient table
  - gradients_wvs_summary.json  sign-agreement summary
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

REPO = Path(__file__).resolve().parents[2]
WVS = REPO / "data" / "WVS" / "WVS_wave7.dta"
PROTOCOL = Path(__file__).resolve().parent / "protocol.yaml"
OUT = REPO / "data" / "validity"

SCALES = {
    "binary_1_2": {"min": 1, "max": 2},
    "likert_1_4": {"min": 1, "max": 4},
    "scale_1_3": {"min": 1, "max": 3},
    "scale_1_10": {"min": 1, "max": 10},
    "member_0_2": {"min": 0, "max": 2},
}

# GPS benchmark: expected sign of each gradient per dimension (Falk et al. 2018,
# Table 5, country-FE spec; signs only — the protocol compares directions).
# None = no stable expectation (age-shape for altruism/trust is country-specific).
BENCHMARK_SIGNS: dict[str, dict[str, int | None]] = {
    "patience": {"female": -1, "educ": +1, "age2": -1},
    "risktaking": {"female": -1, "educ": +1, "age2": -1},
    "posrecip": {"female": +1, "educ": +1, "age2": -1},
    "negrecip": {"female": -1, "educ": +1, "age2": -1},
    "altruism": {"female": +1, "educ": +1, "age2": None},
    "trust": {"female": +1, "educ": +1, "age2": None},
}


def load_protocol(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("protocol must be a YAML mapping")
    return data


def item_specs(protocol: dict) -> dict[str, dict]:
    specs: dict[str, dict] = {}
    for dim, ds in protocol["dimensions"].items():
        for facet_name, fs in ds["facets"].items():
            for item, ispec in fs["items"].items():
                specs[item] = {"dim": dim, "facet": facet_name, **ispec}
    return specs


def normalize(value: pd.Series, scale: str) -> pd.Series:
    lo, hi = SCALES[scale]["min"], SCALES[scale]["max"]
    return (value - lo) / (hi - lo)


def build_respondent_facets(wvs: pd.DataFrame, protocol: dict) -> pd.DataFrame:
    """Respondent-level facet scores (frozen recipe)."""
    dims = protocol["dimensions"]
    specs = item_specs(protocol)

    out = wvs[["B_COUNTRY_ALPHA"]].copy()
    out["iso"] = wvs["B_COUNTRY_ALPHA"].astype(str).str.strip()

    item_cols: dict[str, str] = {}
    for item, spec in specs.items():
        direction = float(spec["direction"])
        raw = pd.to_numeric(wvs[item], errors="coerce")
        valid = raw >= 0  # negative codes are missing (DK/NA/not asked)
        norm = normalize(raw, spec["scale"])
        s = norm.where(valid)
        if direction < 0:
            s = (1.0 - norm).where(valid)
        col = f"item_{item}"
        out[col] = s
        item_cols[item] = col

    for dim, ds in dims.items():
        for facet_name, fs in ds["facets"].items():
            cols = [item_cols[it] for it in fs["items"]]
            out[f"m_{dim}_{facet_name}"] = out[cols].mean(axis=1, skipna=True)
            out.loc[out[cols].isna().all(axis=1), f"m_{dim}_{facet_name}"] = np.nan
    return out


def add_demographics(facets: pd.DataFrame, wvs: pd.DataFrame) -> pd.DataFrame:
    """Sex (1=female), age/100, (age/100)^2, education ISCED 0-8."""
    d = facets.copy()
    sex = pd.to_numeric(wvs["Q260"], errors="coerce")
    age = pd.to_numeric(wvs["Q262"], errors="coerce")
    educ = pd.to_numeric(wvs["Q275"], errors="coerce")
    d["female"] = (sex == 2).astype(float)  # Q260: 1=Male, 2=Female
    d["age100"] = age.where(age >= 0) / 100.0
    d["age2"] = d["age100"] ** 2
    d["educ"] = educ.where(educ >= 0)
    return d


def ols_coefs(y: np.ndarray, X: np.ndarray) -> tuple[np.ndarray, int]:
    """OLS coefficients + n (no SEs needed for sign-agreement)."""
    Xc = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(Xc, y, rcond=None)
    return beta, len(y)


def ols_se(y: np.ndarray, X: np.ndarray, cluster: np.ndarray | None = None) -> np.ndarray:
    """Standard errors for OLS; cluster-robust when cluster ids given.

    Falk et al. 2018 Table 5 clusters at country level; we mirror that for
    the pooled spec and use HC1 (no clustering) for single-country specs.
    """
    Xc = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(Xc, y, rcond=None)
    resid = y - Xc @ beta
    k = Xc.shape[1]
    n = len(y)
    if cluster is None:
        sigma2 = resid @ resid / (n - k)
        XtX_inv = np.linalg.inv(Xc.T @ Xc)
        return np.sqrt(np.diag(sigma2 * XtX_inv))
    # cluster-robust (Liang-Zeger)
    meat = np.zeros((k, k))
    gids = pd.Series(cluster)
    for _, idx in gids.groupby(gids).groups.items():
        Xg = Xc[idx]
        eg = resid[idx]
        score = Xg.T @ eg
        meat += np.outer(score, score)
    bread = np.linalg.inv(Xc.T @ Xc)
    V = bread @ meat @ bread
    # small-sample correction (n-1)/(n-k) * G/(G-1)
    G = gids.nunique()
    V = V * ((n - 1) / (n - k)) * (G / (G - 1))
    return np.sqrt(np.diag(V))


def fit_facet(d: pd.DataFrame, facet: str, spec: str = "pooled") -> dict:
    """Fit facet ~ female + age100 + age2 + educ for a spec; return coefs + SEs."""
    df = d[["female", "age100", "age2", "educ", facet]].dropna().copy()
    if spec == "pooled":
        # country FE: absorb iso means by demeaning (equivalent for coefs)
        df = df.join(d[["iso"]])
        demean_cols = ["female", "age100", "age2", "educ", facet]
        for col in demean_cols:
            df[col] = df[col] - df.groupby("iso")[col].transform("mean")
        y = df[facet].values
        X = df[["female", "age100", "age2", "educ"]].values
        beta, n = ols_coefs(y, X)
        se = ols_se(y, X, cluster=df["iso"].to_numpy())
    else:
        y = df[facet].values
        X = df[["female", "age100", "age2", "educ"]].values
        beta, n = ols_coefs(y, X)
        se = ols_se(y, X)
    return {
        "facet": facet,
        "spec": spec,
        "n": n,
        "b_female": float(beta[1]),
        "b_age": float(beta[2]),
        "b_age2": float(beta[3]),
        "b_educ": float(beta[4]),
        "se_female": float(se[1]),
        "se_age": float(se[2]),
        "se_age2": float(se[3]),
        "se_educ": float(se[4]),
    }


def sign(x: float) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


def main() -> None:
    protocol = load_protocol(PROTOCOL)
    dims = list(protocol["dimensions"])

    print("loading WVS wave 7 ...")
    wvs = pd.read_stata(WVS, convert_categoricals=False)
    print(f"  {wvs.shape[0]} respondents, {wvs['B_COUNTRY_ALPHA'].nunique()} countries")

    facets = add_demographics(build_respondent_facets(wvs, protocol), wvs)

    rows: list[dict] = []
    for dim in dims:
        facets_dim = [c for c in facets.columns if c.startswith(f"m_{dim}_")]
        for facet in facets_dim:
            for spec in ("USA", "MEX", "pooled"):
                if spec in ("USA", "MEX"):
                    d = facets[facets["iso"] == spec]
                else:
                    d = facets
                rows.append(fit_facet(d, facet, spec))

    out = pd.DataFrame(rows)
    out_path = OUT / "gradients_wvs.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)

    # --- sign-agreement summary ---
    summary: dict[str, dict] = {}
    for dim in dims:
        bm = BENCHMARK_SIGNS[dim]
        facets_dim = sorted({r["facet"] for r in rows if r["facet"].startswith(f"m_{dim}_")})
        summary[dim] = {}
        for facet in facets_dim:
            rec = {"benchmark": bm}
            for spec in ("USA", "MEX", "pooled"):
                r = next(x for x in rows if x["facet"] == facet and x["spec"] == spec)
                agree: dict[str, bool | None] = {}
                zstats: dict[str, float | None] = {}
                for key, expected in bm.items():
                    if expected is None:
                        agree[key] = None
                        zstats[key] = None
                        continue
                    b = {"female": r["b_female"], "educ": r["b_educ"], "age2": r["b_age2"]}[key]
                    se = {"female": r["se_female"], "educ": r["se_educ"], "age2": r["se_age2"]}[key]
                    z = float(b / se) if se > 0 else 0.0
                    zstats[key] = z
                    # gradient counts only if significant (|z|>=1.96) AND sign matches
                    agree[key] = bool(abs(z) >= 1.96 and sign(b) == expected)
                rec[spec] = {"n": r["n"], **{k: float(v) for k, v in
                             {"b_female": r["b_female"], "b_age": r["b_age"],
                              "b_age2": r["b_age2"], "b_educ": r["b_educ"]}.items()},
                             "z_female": zstats["female"], "z_educ": zstats["educ"],
                             "z_age2": zstats["age2"],
                             "agree": agree}
            summary[dim][facet] = rec

    summary_path = OUT / "gradients_wvs_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    print("\n=== Stream B: WVS human gradient sign-agreement vs GPS benchmark ===")
    print("(benchmark signs: female/educ/age2 per dim; None = no stable expectation)")
    print("(✓ requires |z|>=1.96 AND sign match; ✗ = significant opposite sign; '~' = not significant)")
    for dim in dims:
        print(f"\n-- {dim} --")
        for facet, rec in summary[dim].items():
            for spec in ("USA", "MEX", "pooled"):
                a = rec[spec]["agree"]
                agree_str = "/".join(
                    ("✓" if v is True else ("–" if v is None else ("✗" if v is False else "?"))) for v in a.values()
                )
                zf = rec[spec]["z_female"]
                za = rec[spec]["z_age2"]
                ze = rec[spec]["z_educ"]
                zf_s = f"{zf:+.1f}" if zf is not None else "  –"
                za_s = f"{za:+.1f}" if za is not None else "  –"
                ze_s = f"{ze:+.1f}" if ze is not None else "  –"
                print(f"  {facet:32s} {spec:6s} n={rec[spec]['n']:6d}  "
                      f"female={rec[spec]['b_female']:+.3f} (z={zf_s}) "
                      f"age2={rec[spec]['b_age2']:+.3f} (z={za_s}) "
                      f"educ={rec[spec]['b_educ']:+.3f} (z={ze_s})  "
                      f"agree[female/educ/age2]={agree_str}")

    print(f"\nwrote {out_path}")
    print(f"wrote {summary_path}")


if __name__ == "__main__":
    main()
