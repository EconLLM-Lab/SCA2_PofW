#!/usr/bin/env python3
"""Paper B 42-cohort analysis module — CPU-only, no adapter outcomes read.

Implements the predeclared estimands from the 2026-10-11 analysis design
(parent-reviewed), on top of two kinds of local inputs:

  * model option probabilities with columns (model, eval_country,
    question_id, option_code, model_prob) — produced by paper_b/score_cohort.py
  * local specs and human aggregates: the committed
    analysis/phase2/outputs/paper_a/human_item_means_42.csv, the GPS sign
    vector JSON, and (optionally) WVS parquets for a human-only
    reproduction of the committed means.

Predeclared estimands (nothing here re-litigates the design):
  * recodes: exactly the locked E[recode] map over STRICT_ITEMS (23 items;
    Q43/Q50 separate; Q57 binary; 1-4 and 1-10 inversions) applied to each
    (model, country, item) option probability vector.
  * three-column table: adapter-GPS, adapter-human, human-GPS Spearman per
    dimension (country-equal primary estimand).
  * uncertainty: profile-block bootstrap (26 GPS-sign profiles) for the two
    adapter columns; country bootstrap for human-GPS; 2000 draws,
    seed 20261011 (baseline, not a cap); percentile intervals.
  * profile-equal sensitivity: mean each variable within profile, THEN rank
    the 26 profile means — a different estimand, labeled as such.
  * base arm: composites constant across countries by construction, so
    base-GPS / base-human Spearman is UNDEFINED (point and interval);
    only paired adapter-minus-base differences (TVD / mean recode error)
    are reported; degenerate draws are counted, never swallowed.
  * reliability: within-profile spread of composites (descriptive only;
    NOT claimed to be pure fitting noise).
  * missingness ledger: per (country, item) adapter/human availability,
    including the JOR/Q178 complete-case consequence (risktaking human
    sample n=41).

No GPU, no network, no uploads; outputs go only to the user-supplied --out
directory (dry runs use the active-profile scratch; fixture outputs are
purged and never written into the repo).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

# ---------------------------------------------------------------- paths
REPO = Path(__file__).resolve().parents[1]
DEFAULT_HUMAN_MEANS = REPO / "analysis/phase2/outputs/paper_a/human_item_means_42.csv"
DEFAULT_GPS_JSON = REPO / "synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json"

# ------------------------------------------------- locked recode surface
TRUST9 = ["Q57", "Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73"]
PATIENCE_ITEMS = ["Q43", "Q50"]  # kept separate by frozen decision
RISK_ITEMS = ["Q106", "Q107", "Q109", "Q178"]
POSRECIP_ITEMS = ["Q81"]
NEGRECIP_ITEMS = ["Q176", "Q177", "Q179", "Q195"]
ALTRUISM_ITEMS = ["Q99", "Q101", "Q103"]

STRICT_ITEMS: dict[str, list[str]] = {
    "trust": TRUST9,
    "patience": PATIENCE_ITEMS,
    "risktaking": RISK_ITEMS,
    "posrecip": POSRECIP_ITEMS,
    "negrecip": NEGRECIP_ITEMS,
    "altruism": ALTRUISM_ITEMS,
}


def all_strict_items() -> list[str]:
    """The 23 unique primary-battery items, in canonical order."""
    out: list[str] = []
    out = []
    for qs in STRICT_ITEMS.values():
        for q in qs:
            if q not in out:
                out.append(q)
    return out


INVERT_1_4 = {"Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q69", "Q70",
              "Q71", "Q73", "Q81"}  # locked map includes the Q69-71 extension
INVERT_10 = {"Q177", "Q179"}
BINARY = {"Q57"}

BOOT_DRAWS = 2000
BOOT_SEED = 20261011            # profile / paired bootstrap baseline seed
COUNTRY_BOOT_SEED = 20260905    # inherited Paper A convention seed

# Option-code domains as supplied by the frozen scoring grid. May be
# overridden by register_option_domains() from the local question map.
OPTION_DOMAINS: dict[str, list[str]] = {}


def _domain(item: str) -> list[str]:
    if OPTION_DOMAINS:
        d = OPTION_DOMAINS.get(item)
        if d is not None:
            return [str(c) for c in d]
    if item in BINARY:
        return ["1", "2"]
    if item == "Q43":
        return ["1", "2", "3"]
    if item in {"Q99", "Q101", "Q103"}:
        return ["0", "1", "2"]
    if item in INVERT_1_4:
        return ["1", "2", "3", "4"]
    if item in INVERT_10 or item in {"Q50"} or item in {
        "Q106", "Q107", "Q109", "Q176", "Q178", "Q195",
    }:
        return [str(c) for c in range(1, 11)]
    raise KeyError(f"no option domain registered for {item!r}")


def register_option_domains(spec: pd.DataFrame) -> None:
    """Pin option domains from a local spec frame (question_id, option_code)."""
    for qid, grp in spec.groupby("question_id"):
        OPTION_DOMAINS[str(qid)] = [str(c) for c in grp["option_code"].tolist()]


# ------------------------------------------------------- recodes (locked)
def recode_value(raw: float, item: str) -> float:
    s = float(raw)
    if item in INVERT_1_4:
        return 5.0 - s
    if item in INVERT_10:
        return 11.0 - s
    if item in BINARY:
        return 1.0 if s == 1.0 else 0.0
    return s


def expected_recode(option_codes: Sequence, probabilities: Sequence[float],
                    item: str) -> float:
    """E[recode] = sum_k p_k * recode(code_k) over the FULL supplied grid.

    Requires every option of the item's domain to be present (a missing
    option would silently bias E[recode]); probabilities must be finite,
    non-negative and sum to 1.
    """
    codes = [str(c) for c in option_codes]
    p = np.asarray(probabilities, dtype=float)
    if p.shape[0] != len(codes):
        raise ValueError(
            f"{item}: {len(codes)} option codes but {p.shape[0]} probabilities")
    if not np.all(np.isfinite(p)) or np.any(p < 0):
        raise ValueError(f"{item}: probabilities must be finite and non-negative")
    if abs(float(p.sum()) - 1.0) > 1e-6:
        raise ValueError(f"{item}: probabilities sum to {float(p.sum())}, not 1")
    domain = set(_domain(item))
    missing = domain - set(codes)
    if missing:
        raise ValueError(
            f"{item}: scored grid missing option(s) {sorted(missing)} of its domain")
    extra = set(codes) - domain
    if extra:
        raise ValueError(f"{item}: code(s) {sorted(extra)} outside its domain")
    e = 0.0
    for c, pk in zip(codes, p):
        e += pk * recode_value(float(c), item)
    return float(e)


def total_variation_distance(p: dict, q: dict) -> float:
    """TVD between two distributions over string codes.

    Codes with zero mass on both sides are ignored; a code present on one
    side is mass 0 on the other. Each distribution must sum to 1.
    """
    def _norm(d: dict) -> dict[str, float]:
        out = {str(k): float(v) for k, v in d.items()}
        vals = list(out.values())
        if not np.all(np.isfinite(vals)) or any(v < 0 for v in vals):
            raise ValueError("probabilities must be finite and non-negative")
        if abs(sum(vals) - 1.0) > 1e-6:
            raise ValueError(f"probabilities sum to {sum(vals)}, not 1")
        return out

    pp, qq = _norm(p), _norm(q)
    codes = set(pp) | set(qq)
    return 0.5 * sum(abs(pp.get(c, 0.0) - qq.get(c, 0.0)) for c in codes)


# ------------------------------------------------------ GPS sign profiles
def load_gps_z(path: Path) -> pd.DataFrame:
    raw = json.loads(Path(path).read_text())
    rows = []
    for cc, dims in raw.items():
        for d, v in dims.items():
            rows.append({"country": cc, "dimension": d, "z": float(v)})
    return pd.DataFrame(rows)


def sign_profiles(z: pd.DataFrame, countries: Sequence[str],
                  dimensions: Sequence[str]) -> pd.DataFrame:
    """profile_id per country from sign(z) over the six GPS dimensions."""
    sub = z[z.country.isin(set(countries)) & z.dimension.isin(set(dimensions))]
    wide = sub.pivot(index="country", columns="dimension", values="z")
    missing = sorted(set(countries) - set(wide.index))
    if missing:
        raise ValueError(f"GPS z missing for countries: {missing}")
    pid = pd.Series(
        ["_".join(str(int(np.sign(wide[d].iloc[i]))) for d in dimensions)
         for i in range(len(wide))],
        index=wide.index,
    )
    return pid.rename("profile_id").reset_index().rename(columns={"index": "country"})


# ------------------------------------------------------------- estimators
def _spearman_arrays(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2 or np.all(x == x[0]) or np.all(y == y[0]):
        return float("nan")
    rho = float(spearmanr(x, y).statistic)
    return rho if math.isfinite(rho) else float("nan")


def spearman_country_equal(a: pd.Series, b: pd.Series,
                           min_n: int = 8) -> tuple[float, int]:
    """Country-equal Spearman over the pairwise-complete intersection.

    Returns (rho, n); rho is NaN (never silently dropped) when degenerate.
    """
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    n = len(d)
    if n < min_n or d["a"].nunique() < 2 or d["b"].nunique() < 2:
        return (float("nan"), n)
    rho = _spearman_arrays(d["a"].to_numpy(float), d["b"].to_numpy(float))
    return (rho, n)


def bootstrap_spearman(a: pd.Series, b: pd.Series,
                       clusters: pd.Series | None = None,
                       draws: int = BOOT_DRAWS,
                       seed: int = BOOT_SEED,
                       min_n: int = 8) -> dict:
    """Paired bootstrap of the country-equal Spearman.

    clusters: profile_id per unit -> resample whole profiles (all members
    of a drawn profile move together). clusters=None -> plain country
    bootstrap (Paper A comparability convention). Degenerate draws are
    counted explicitly, never swallowed.
    """
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1)
    if clusters is not None:
        d = d.join(clusters.rename("cl"))
    d = d.dropna(subset=["a", "b"])
    if clusters is not None and d["cl"].isna().any():
        unmapped = sorted(str(i) for i in d.index[d["cl"].isna()])
        raise ValueError(f"cluster id missing for units: {unmapped}")
    n = len(d)
    if n < min_n:
        return {"point": float("nan"), "ci_lo": float("nan"), "ci_hi": float("nan"),
                "n": n, "degenerate_draws": draws, "draws": draws}
    x, y = d["a"].to_numpy(float), d["b"].to_numpy(float)
    point = _spearman_arrays(x, y)
    rng = np.random.default_rng(seed)
    if clusters is None:
        idx_all = rng.integers(0, n, size=(draws, n))
        rhos = np.array([_spearman_arrays(x[ix], y[ix]) for ix in idx_all])
    else:
        cl = d["cl"].to_numpy()
        uniq = pd.unique(cl)
        pos = {c: np.where(cl == c)[0] for c in uniq}
        pick = rng.integers(0, len(uniq), size=(draws, len(uniq)))
        rhos = np.empty(draws)
        for i in range(draws):
            take = np.concatenate([pos[uniq[j]] for j in pick[i]])
            rhos[i] = _spearman_arrays(x[take], y[take])
    deg = int(np.sum(~np.isfinite(rhos)))
    valid = rhos[np.isfinite(rhos)]
    if valid.size == 0:
        lo = hi = float("nan")
    else:
        lo, hi = (float(v) for v in np.quantile(valid, [0.025, 0.975]))
    return {"point": point, "ci_lo": lo, "ci_hi": hi,
            "n": n, "degenerate_draws": deg, "draws": draws}


def profile_equal_spearman(a: pd.Series, b: pd.Series,
                           profiles: pd.DataFrame) -> tuple[float, int]:
    """Profile-equal sensitivity estimand: mean EACH variable within its
    profile first, then Spearman across the profile means.

    DIFFERENT estimand from the country-equal rank correlation; callers
    must label it as sensitivity, never swap it for the primary.
    """
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1).join(
        profiles.set_index("country")["profile_id"])
    if d["profile_id"].isna().any():
        unmapped = sorted(str(i) for i in d.index[d["profile_id"].isna()])
        raise ValueError(f"profile id missing for countries: {unmapped}")
    d = d.dropna(subset=["a", "b"])
    gm = d.groupby("profile_id")[["a", "b"]].mean()
    n = len(gm)
    if n < 8 or gm["a"].nunique() < 2 or gm["b"].nunique() < 2:
        return (float("nan"), n)
    rho = float(spearmanr(gm["a"], gm["b"]).statistic)
    return (rho if math.isfinite(rho) else float("nan"), n)


# ------------------------------------------------- adapter-side composites
def model_item_table(probs: pd.DataFrame,
                     domains: dict[str, list[str]] | None = None) -> pd.DataFrame:
    """(model, eval_country, question_id) probabilities -> E[recode] rows."""
    domains = domains if domains is not None else OPTION_DOMAINS
    need = {"model", "eval_country", "question_id", "option_code", "model_prob"}
    missing = need - set(probs.columns)
    if missing:
        raise ValueError(f"model probabilities missing columns: {sorted(missing)}")
    battery = set(all_strict_items())
    sub = probs[probs.question_id.astype(str).isin(battery)].copy()
    sub["question_id"] = sub["question_id"].astype(str)
    sub["option_code"] = sub["option_code"].astype(str)  # preserve string keys
    rows = []
    for (model, cc, qid), g in sub.groupby(["model", "eval_country", "question_id"],
                                           sort=True):
        if g["option_code"].duplicated().any():
            raise ValueError(f"{model}/{cc}/{qid}: duplicate option_code rows")
        dom = set(domains[qid]) if (domains and qid in domains) else set(_domain(qid))
        if set(g.option_code) != dom:
            raise ValueError(
                f"{model}/{cc}/{qid}: option grid {sorted(g.option_code)} != "
                f"domain {sorted(dom)}")
        p = g["model_prob"].to_numpy(float)
        if not np.all(np.isfinite(p)) or np.any(p < 0):
            raise ValueError(f"{model}/{cc}/{qid}: invalid model_prob")
        if abs(p.sum() - 1.0) > 1e-6:
            raise ValueError(f"{model}/{cc}/{qid}: model_prob sums to {p.sum()}")
        e = float(np.dot(p, np.array([recode_value(float(c), qid) for c in g.option_code])))
        rows.append({"model": model, "country": cc, "item": qid,
                     "e_recode": e, "n_options": len(g)})
    return pd.DataFrame(rows)


def arm_composites(items: pd.DataFrame, item_lists: dict[str, list[str]],
                   complete: bool = True) -> pd.DataFrame:
    """Per (model, country, dimension): unweighted mean of the dimension's
    item E[recodes]. complete=True keeps only countries observed on every
    item of that composite (dimension-specific complete-case: JOR drops
    from risktaking)."""
    rows = []
    for (model, cc), g in items.groupby(["model", "country"], sort=True):
        for dim, qs in item_lists.items():
            s = g[g.item.isin(qs)]
            if complete and s.item.nunique() != len(qs):
                continue
            if s.empty:
                continue
            rows.append({"model": model, "country": cc, "dimension": dim,
                         "composite": float(s.e_recode.mean()),
                         "n_items_observed": int(s.item.nunique())})
    return pd.DataFrame(rows)


# ------------------------------------------------------ distribution diffs
def per_item_tvd(model_items: pd.DataFrame) -> pd.DataFrame:
    """Adapter-vs-human TVD per (model, country, item).

    model_items carries the probability long frame joined to the human
    distribution: columns (model, country, item, option_code, model_prob,
    human_prob). TVD is paired per item; the paired adapter-minus-base TVD
    is then derived by paired_base_difference.
    """
    need = {"model", "country", "item", "option_code", "model_prob", "human_prob"}
    missing = need - set(model_items.columns)
    if missing:
        raise ValueError(f"per_item_tvd needs columns {sorted(need)}; "
                         f"missing {sorted(missing)}")
    rows = []
    for (model, cc, qid), g in model_items.groupby(
            ["model", "country", "item"], sort=True):
        p = dict(zip(g.option_code.astype(str), g.model_prob.astype(float)))
        q = dict(zip(g.option_code.astype(str), g.human_prob.astype(float)))
        rows.append({"model": model, "country": cc, "item": str(qid),
                     "tvd": total_variation_distance(p, q)})
    return pd.DataFrame(rows)


def paired_base_difference(adapter_metric: pd.DataFrame,
                           base_metric: pd.DataFrame,
                           value_col: str = "tvd") -> pd.DataFrame:
    """Paired adapter-minus-base differences per (model, country).

    The base arm is one unconditioned distribution broadcast to all
    populations: its composites are constant across countries, so base-GPS
    and base-human Spearman are UNDEFINED (parent fixture returned nan).
    Only these paired differences are predeclared; support must match.
    """
    need = {"model", "country", value_col}
    missing = need - set(adapter_metric.columns)
    if missing:
        raise ValueError(f"adapter metric missing columns: {sorted(missing)}")
    base = base_metric[["country", value_col]].drop_duplicates("country")
    m = adapter_metric.merge(base, on="country", how="left",
                             validate="many_to_one", suffixes=("", "_base"))
    if m[value_col + "_base"].isna().any():
        raise ValueError(f"base metric missing for "
                         f"{int(m[value_col + '_base'].isna().sum())} rows")
    m["adapter_minus_base"] = m[value_col] - m[value_col + "_base"]
    return m[["model", "country", value_col, value_col + "_base",
              "adapter_minus_base"]]


# -------------------------------------------------------------- reliability
def within_profile_spread(comp: pd.DataFrame, profiles: pd.DataFrame,
                          value_col: str = "composite") -> pd.DataFrame:
    """Descriptive within-profile spread per (model, dimension, profile):
    SD and range across member countries. Descriptive only — never claimed
    to be pure fitting noise until full data/config equality is verified."""
    d = comp.merge(profiles[["country", "profile_id"]], on="country", how="left")
    if d.profile_id.isna().any():
        unmapped = sorted(d.country[d.profile_id.isna()].astype(str))
        raise ValueError(f"unmapped countries in composite frame: {unmapped}")
    g = d.groupby(["model", "dimension", "profile_id"])
    out = g.agg(n_members=(value_col, "size"),
                sd=(value_col, lambda s: float(np.std(s, ddof=1)) if len(s) > 1 else float("nan")),
                lo=(value_col, "min"),
                hi=(value_col, "max"))
    out["range"] = out["hi"] - out["lo"]
    return out[out.n_members > 1].reset_index()


# ------------------------------------------------------------- missingness
def missingness_ledger(model_items: pd.DataFrame, human_means: pd.DataFrame,
                       countries: Sequence[str]) -> pd.DataFrame:
    """Per (country, item): adapter-side present? human-side present?

    The complete-case consequence (JOR absent on Q178 -> risktaking human
    complete-case n=41) is a derived fact of this ledger, not an input.
    """
    battery = all_strict_items()
    mi = set(zip(model_items.country, model_items.item))
    hi = set(zip(human_means.country, human_means.item))
    rows = [{"country": cc, "item": it,
             "adapter_present": (cc, it) in mi,
             "human_present": (cc, it) in hi}
            for cc in countries for it in battery]
    return pd.DataFrame(rows)


def complete_case_countries(items_long: pd.DataFrame, dim: str,
                            item_lists: dict[str, list[str]]) -> list[str]:
    qs = set(item_lists[dim])
    have = items_long[items_long.item.isin(qs)].groupby("country")["item"].apply(
        lambda s: qs.issubset(set(s)))
    return sorted(have[have].index)


# ------------------------------------------------------------ human inputs
def human_composites(human_means: pd.DataFrame,
                     item_lists: dict[str, list[str]],
                     complete: bool = True) -> pd.DataFrame:
    """Human composite per (country, dimension) from the committed item
    means (already recoded upstream). Mirrors arm_composites."""
    rows = []
    for cc, g in human_means.groupby("country", sort=True):
        for dim, qs in item_lists.items():
            s = g[g.item.isin(qs)]
            if complete and s.item.nunique() != len(qs):
                continue
            if s.empty:
                continue
            rows.append({"country": cc, "dimension": dim,
                         "composite": float(s["mean"].mean()),
                         "n_items_observed": int(s.item.nunique())})
    return pd.DataFrame(rows)


def load_human_means(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


# ------------------------------------------------------------- reproduction
def reproduce_human_item_means(wvs_dir: Path, min_n: int = 50) -> pd.DataFrame:
    """Human-only reproduction of the committed item means from the local
    WVS parquets (locked recode/weighting, Paper A convention). Reads
    respondent microdata locally, writes nothing, touches no adapter output.
    """
    import pyarrow.parquet as pq
    items = all_strict_items() + ["Q69", "Q70", "Q71"]
    rows = []
    for f in sorted(Path(wvs_dir).glob("*_WVS_wave7.parquet")):
        cc = f.name.split("_")[0]
        available = set(pq.ParquetFile(f).schema.names)
        wcol = "W_WEIGHT" if "W_WEIGHT" in available else (
            "weight" if "weight" in available else None)
        if wcol is None:
            continue
        cols = [wcol] + [q for q in items if q in available]
        df = pd.read_parquet(f, columns=cols)
        w = df[wcol].fillna(0).astype(float)
        for it in [q for q in items if q in df.columns]:
            v = df[it].astype(float)
            mask = (v >= 0) & np.isfinite(v) & (w > 0)
            if int(mask.sum()) < min_n:
                continue
            rec = np.array([recode_value(float(x), it) for x in v[mask].to_numpy()])
            ww = w[mask].to_numpy()
            rows.append({"country": cc, "item": it,
                         "mean": float((rec * ww).sum() / ww.sum()),
                         "n": int(mask.sum())})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- manifest
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def build_manifest(input_paths: dict, frame_members: dict, counts: dict) -> dict:
    return {
        "inputs": {k: {"path": str(Path(p)), "sha256": sha256_file(Path(p))}
                   for k, p in input_paths.items()},
        "input_membership": frame_members,
        "counts": counts,
        "seeds": {"profile_bootstrap": BOOT_SEED,
                  "country_bootstrap": COUNTRY_BOOT_SEED},
        "draws_baseline": BOOT_DRAWS,
    }


# ------------------------------------------------------------------ driver
def run_analysis(probs: pd.DataFrame, human_means: pd.DataFrame,
                 gps_z_path: Path, out_dir: Path,
                 draws: int = BOOT_DRAWS, seed: int = BOOT_SEED,
                 make_figures: bool = True,
                 human_means_path: Path | None = None,
                 probs_path: Path | None = None) -> dict:
    """Full predeclared pipeline; writes tables + manifest into out_dir.

    human_means_path and probs_path are the files the DataFrames were loaded
    from; the manifest hashes THOSE paths (never a default) so provenance
    reflects actual inputs.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if human_means_path is None:
        raise ValueError("human_means_path is required for provenance")
    if probs_path is None:
        raise ValueError("probs_path is required for provenance")

    battery_items = all_strict_items()
    dims = list(STRICT_ITEMS.keys())
    countries = sorted(set(probs.eval_country.astype(str)) &
                       set(human_means.country.astype(str)))
    z = load_gps_z(gps_z_path)
    prof_dims = ["altruism", "negrecip", "patience", "posrecip", "risktaking", "trust"]
    profiles = sign_profiles(z, countries, prof_dims)
    gps = z.pivot(index="country", columns="dimension", values="z")
    prof_idx = profiles.set_index("country")["profile_id"]
    item_lists = dict(STRICT_ITEMS)

    mitems = model_item_table(probs)
    acomp = arm_composites(mitems, item_lists, complete=True)
    hcomp = human_composites(human_means, item_lists, complete=True)
    # base composites are constant across countries by construction; the base
    # arm never enters the correlation loops (UNDEFINED rho) — it only
    # enters the paired adapter-minus-base differences below.
    corr_models = sorted(set(acomp.model.unique()) - {"base"})

    three_rows: list[dict] = []
    sens_rows: list[dict] = []

    def emit_adapter(model: str, column: str, surface: str,
                     s_m: pd.Series, tgt: pd.Series) -> None:
        prof = prof_idx.reindex(s_m.index)
        r = bootstrap_spearman(s_m, tgt, clusters=prof, draws=draws, seed=seed)
        rho_pe, n_pe = profile_equal_spearman(s_m, tgt, profiles)
        three_rows.append({
            "model": model, "column": column, "surface": surface,
            "rho": r["point"], "ci_lo": r["ci_lo"], "ci_hi": r["ci_hi"],
            "n": r["n"], "degenerate_draws": r["degenerate_draws"],
            "draws": r["draws"], "cluster": "profile"})
        sens_rows.append({
            "model": model, "column": column, "surface": surface,
            "estimand": "profile-equal", "rho": rho_pe, "n_profiles": n_pe})

    def emit_human(country_series: pd.Series, surface: str) -> None:
        tgt = gps[surface.split(":")[0]].reindex(country_series.index)
        r = bootstrap_spearman(country_series, tgt, clusters=None,
                               draws=draws, seed=COUNTRY_BOOT_SEED)
        rho_pe, n_pe = profile_equal_spearman(country_series, tgt, profiles)
        three_rows.append({
            "model": "(human)", "column": "human-GPS", "surface": surface,
            "rho": r["point"], "ci_lo": r["ci_lo"], "ci_hi": r["ci_hi"],
            "n": r["n"], "degenerate_draws": r["degenerate_draws"],
            "draws": r["draws"], "cluster": "country"})
        sens_rows.append({
            "model": "(human)", "column": "human-GPS", "surface": surface,
            "estimand": "profile-equal", "rho": rho_pe, "n_profiles": n_pe})

    for dim in dims:
        qs = item_lists[dim]
        # human-GPS rows (country bootstrap, predeclared for the human column)
        if dim == "patience":
            for q in qs:
                emit_human(human_means[human_means.item == q]
                           .set_index("country")["mean"], f"patience:{q}")
        else:
            hs = hcomp[hcomp.dimension == dim].set_index("country")["composite"]
            emit_human(hs, dim)

        # adapter rows per model (base excluded — see corr_models)
        for model in corr_models:
            if dim == "patience":
                # unpooled: composite over one item only == that item's E[recode]
                for q in qs:
                    s_q = (mitems[(mitems.model == model) & (mitems.item == q)]
                           .set_index("country")["e_recode"])
                    emit_adapter(model, "adapter-GPS", f"patience:{q}",
                                 s_q, gps["patience"].reindex(s_q.index))
                    hq = human_means[human_means.item == q].set_index("country")["mean"]
                    emit_adapter(model, "adapter-human", f"patience:{q}",
                                 s_q, hq.reindex(s_q.index))
            else:
                s_m = (acomp[(acomp.model == model) & (acomp.dimension == dim)]
                       .set_index("country")["composite"])
                emit_adapter(model, "adapter-GPS", dim,
                             s_m, gps[dim].reindex(s_m.index))
                emit_adapter(model, "adapter-human", dim,
                             s_m, hcomp[hcomp.dimension == dim]
                             .set_index("country")["composite"].reindex(s_m.index))

    three = pd.DataFrame(three_rows)
    sens = pd.DataFrame(sens_rows)

    # --- base arm: paired differences ONLY, never correlations.
    # The unconditioned base is one distribution broadcast to all populations:
    # its composites/TVDs are constant across countries, so base-GPS and
    # base-human Spearman are UNDEFINED (point and interval). The predeclared
    # object is the paired adapter-minus-base difference of the per-country
    # mean |E[recode] - human mean| over the dimension-specific complete-case
    # battery; a human item absent in a country is excluded from BOTH sides.
    base_differences = pd.DataFrame(columns=[
        "model", "country", "adapter_mean_abs_error", "base_mean_abs_error",
        "adapter_minus_base_mean_abs_error", "n_items"])
    if "base" in set(mitems.model.unique()):
        a_models = sorted(set(mitems.model.unique()) - {"base"})
        base_item = mitems[mitems.model == "base"].set_index(["country", "item"])
        hm_idx = human_means.set_index(["country", "item"])["mean"]
        rows = []
        for am in a_models:
            ai = mitems[mitems.model == am].set_index(["country", "item"])
            joined = pd.DataFrame({
                "adapter": ai["e_recode"],
                "base": base_item["e_recode"].reindex(ai.index),
                "human": hm_idx.reindex(ai.index)}).dropna()
            per = (joined.assign(
                        ae=(joined.adapter - joined.human).abs(),
                        be=(joined.base - joined.human).abs())
                   .groupby("country")
                   .agg(adapter_mean_abs_error=("ae", "mean"),
                        base_mean_abs_error=("be", "mean"),
                        n_items=("ae", "size")))
            per["adapter_minus_base_mean_abs_error"] = (
                per.adapter_mean_abs_error - per.base_mean_abs_error)
            per = per.reset_index()
            per.insert(0, "model", am)
            rows.append(per)
        base_differences = pd.concat(rows, ignore_index=True)
    ledger = missingness_ledger(mitems, human_means, countries)
    cc_rows = [{"dimension": dim,
                "adapter_complete_case": complete_case_countries(mitems, dim, item_lists),
                "human_complete_case": complete_case_countries(human_means, dim, item_lists)}
               for dim in dims]
    ccm = pd.DataFrame(cc_rows)
    rel = within_profile_spread(acomp, profiles)

    man = build_manifest(
        {"gps_z": gps_z_path,
         "human_means": human_means_path},
        {"countries": len(countries), "battery_items": len(battery_items),
         "profiles": int(profiles.profile_id.nunique()),
         "multi_member_profiles": int((profiles.groupby("profile_id").size() > 1).sum())},
        {"three_column_rows": len(three), "sensitivity_rows": len(sens),
         "ledger_rows": len(ledger), "reliability_rows": len(rel),
         "base_difference_rows": len(base_differences)})
    (out_dir / "manifest.json").write_text(json.dumps(man, indent=2) + "\n")

    three.to_csv(out_dir / "three_column_table.csv", index=False)
    sens.to_csv(out_dir / "profile_equal_sensitivity.csv", index=False)
    ledger.to_csv(out_dir / "missingness_ledger.csv", index=False)
    ccm.to_csv(out_dir / "complete_case_membership.csv", index=False)
    rel.to_csv(out_dir / "reliability_within_profile.csv", index=False)
    base_differences.to_csv(out_dir / "base_differences.csv", index=False)

    figures: list[str] = []
    if make_figures:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(7, 4.5))
            plot_df = three.dropna(subset=["rho"])
            y = {c: i for i, c in enumerate(sorted(plot_df.surface.unique()))}
            for col, marker in (("adapter-GPS", "o"), ("adapter-human", "s"),
                                ("human-GPS", "^")):
                d = plot_df[plot_df.column == col]
                ax.scatter([y[s] for s in d.surface], d.rho, marker=marker, label=col)
            ax.set_yticks(range(len(y)))
            ax.set_yticklabels(list(y.keys()), fontsize=7)
            ax.invert_yaxis()
            ax.set_xlabel("country-equal Spearman")
            ax.axvline(0.0, lw=0.5, color="grey")
            ax.legend(fontsize=8)
            fig.tight_layout()
            fig.savefig(out_dir / "three_column_fig.png", dpi=150)
            plt.close(fig)
            figures.append("three_column_fig.png")
        except ImportError:
            figures = []
    man["inputs"]["model_probs"] = {"path": str(Path(probs_path)),
                                    "sha256": sha256_file(Path(probs_path))}
    man["figures"] = figures
    (out_dir / "manifest.json").write_text(json.dumps(man, indent=2) + "\n")
    return {"three_column": three, "sensitivity": sens, "ledger": ledger,
            "complete_case": ccm, "reliability": rel,
            "base_differences": base_differences, "manifest": man}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Paper B 42-cohort analysis (CPU-only)")
    ap.add_argument("--model-probs", default=None,
                    help="CSV: model, eval_country, question_id, option_code, model_prob "
                         "(required unless --reproduce-human-means)")
    ap.add_argument("--human-means", default=str(DEFAULT_HUMAN_MEANS))
    ap.add_argument("--gps-z", default=str(DEFAULT_GPS_JSON))
    ap.add_argument("--out", required=True, help="output dir (local; dry runs -> scratch)")
    ap.add_argument("--draws", type=int, default=BOOT_DRAWS)
    ap.add_argument("--seed", type=int, default=BOOT_SEED)
    ap.add_argument("--no-figures", action="store_true")
    ap.add_argument("--reproduce-human-means", metavar="WVS_DIR", default=None,
                    help="human-only reproduction of the committed item means")
    args = ap.parse_args(argv)

    if args.reproduce_human_means:
        rep = reproduce_human_item_means(Path(args.reproduce_human_means))
        ref = load_human_means(Path(args.human_means))
        m = rep.merge(ref, on=["country", "item"], suffixes=("_repro", "_committed"))
        m["abs_diff"] = (m.mean_repro - m.mean_committed).abs()
        print(f"reproduced {len(m)} (country,item) means; "
              f"max |diff| = {m['abs_diff'].max():.3e}")
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        m.to_csv(out / "human_means_reproduction.csv", index=False)
        return 0 if len(m) and m["abs_diff"].max() < 1e-9 else 1

    probs = pd.read_csv(args.model_probs)
    probs["option_code"] = probs["option_code"].astype(str)  # preserve string keys
    human_means = load_human_means(Path(args.human_means))
    res = run_analysis(probs, human_means, Path(args.gps_z), Path(args.out),
                       draws=args.draws, seed=args.seed,
                       make_figures=not args.no_figures,
                       human_means_path=Path(args.human_means),
                       probs_path=Path(args.model_probs))
    print(res["three_column"].to_string(index=False))
    print(f"manifest: {args.out}/manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
