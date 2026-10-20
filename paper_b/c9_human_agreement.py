#!/usr/bin/env python3
"""Amendment C9 (card C9-1): human-agreement rows on the 42-country cohort.

Brings the preprint's human-agreement results onto the 42 countries. CPU only, no network, no new scoring.
Every row is DESCRIPTIVE / NOT PREREGISTERED (the 2026-10-11 surface has already been seen).

Parts (long-format rows, `part` column):
  a  cohort-1 three columns (adapter-GPS, adapter-human, human-GPS), 7 surfaces; reproduces the banked
     `paper-b-20261011/analysis/three_column_table.csv` exactly
  b  bank-2 profile adapters mapped to the 42 countries: adapter-GPS (reproduces NUMBERS_TABLE `B2_bank2_*_rho`)
     and adapter-human
  c  between-profile variance share (adapter, human; all countries and multi-member profiles), a permutation
     test of the multi-member share, and a power simulation
  d  sign-mate agreement (leave-one-out mean of a country's sign-mates vs the country), "NOT a ceiling"
  e  GPS-side sign-copier references per dimension
  f  preprint comparison items on 42 countries (Q57, patience Q43/Q50, risk with/without JOR)

Intervals: adapter-side and sign-mate quantities use the profile-block bootstrap (2,000 draws, seed 20261011);
human-GPS uses the country bootstrap (2,000 draws, seed 20260905). Permutation tests use 10,000 permutations and
seed 20261019 (one stream per surface and arm, `default_rng([seed, surface_index, arm_index])`).

Human data stay local. Outputs hold correlations, shares, intervals and p values only; no country-level human
means or distributions are written.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "heldout"))
import analyze_phase as P  # noqa: E402
import analyze_surface as A  # noqa: E402
import bank2_transport as B2  # noqa: E402

# --------------------------------------------------------------- constants
SPRINT = REPO / "planning/sprint_2026-10-11"
COHORT1_ROOT = SPRINT / "paper-b-20261011"
COHORT1_PROBS = COHORT1_ROOT / "model_probs.csv"
BANKED_THREE_COLUMN = COHORT1_ROOT / "analysis/three_column_table.csv"
RISK_JOR_BANKED = COHORT1_ROOT / "analysis_phase/risk_jor_sensitivity.csv"
NUMBERS_TABLE = SPRINT / "paper-b-tier1/NUMBERS_TABLE.csv"
OUT_DIR = SPRINT / "paper-b-tier1/results/c9"
ADAPTER_STRICT_V1 = B2.ADAPTER_STRICT_V1

SURFACES = list(P.SURFACES)  # trust, patience:Q43, patience:Q50, risktaking, posrecip, negrecip, altruism
N_PERM = 10_000
PERM_SEED = 20261019
POWER_SEED = 20261019
POWER_GRID = [round(0.05 * i, 2) for i in range(0, 20)]  # 0.00 .. 0.95
POWER_SIMS = 500
POWER_PERMS = 1000
POWER_TARGET = 0.80
ALPHA = 0.05
BOOT_DRAWS = A.BOOT_DRAWS
PROFILE_SEED = A.BOOT_SEED
COUNTRY_SEED = A.COUNTRY_BOOT_SEED
TAG = "DESCRIPTIVE / NOT PREREGISTERED"

INT_PROFILE = f"profile-block bootstrap ({BOOT_DRAWS} draws, seed {PROFILE_SEED})"
INT_COUNTRY = f"country bootstrap ({BOOT_DRAWS} draws, seed {COUNTRY_SEED})"
INT_NONE = "none (point value)"
INT_NULL = f"permutation null 2.5-97.5 percentile ({N_PERM} permutations, seed {PERM_SEED})"


def inputs_available() -> bool:
    need = [COHORT1_PROBS, BANKED_THREE_COLUMN, NUMBERS_TABLE, A.DEFAULT_HUMAN_MEANS,
            A.DEFAULT_GPS_JSON, ADAPTER_STRICT_V1]
    return all(Path(p).exists() for p in need)


# --------------------------------------------------------------- statistics
def between_share(y, labels) -> float:
    """Between-group share of the total sum of squares (1 - within / total)."""
    y = np.asarray(y, float)
    codes, _ = pd.factorize(np.asarray(labels))
    tot = float(((y - y.mean()) ** 2).sum())
    if not tot > 0:
        return float("nan")
    k = codes.max() + 1
    sums = np.bincount(codes, weights=y, minlength=k)
    cnt = np.bincount(codes, minlength=k)
    within = float(((y - (sums / cnt)[codes]) ** 2).sum())
    return 1.0 - within / tot


def _onehot(labels) -> tuple[np.ndarray, np.ndarray]:
    codes, _ = pd.factorize(np.asarray(labels))
    g = np.zeros((len(codes), codes.max() + 1))
    g[np.arange(len(codes)), codes] = 1.0
    return g, g.sum(axis=0)


def _shares_for_rows(y_rows: np.ndarray, g: np.ndarray, sizes: np.ndarray) -> np.ndarray:
    """Between share of each row of y_rows (R x n) under a fixed grouping."""
    mean = y_rows.mean(axis=1, keepdims=True)
    tot = ((y_rows - mean) ** 2).sum(axis=1)
    sums = y_rows @ g
    between = (sums ** 2 / sizes).sum(axis=1) - y_rows.shape[1] * mean[:, 0] ** 2
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(tot > 0, between / tot, np.nan)


def _perm_index(n: int, n_perm: int, rng: np.random.Generator) -> np.ndarray:
    return np.argsort(rng.random((n_perm, n)), axis=1)


def permuted_labels(labels, n_perm: int, rng: np.random.Generator) -> np.ndarray:
    """n_perm random relabelings; group sizes are preserved by construction."""
    lab = np.asarray(labels)
    return lab[_perm_index(len(lab), n_perm, rng)]


def permutation_between(y, labels, n_perm: int, rng: np.random.Generator) -> dict:
    """One-sided permutation test of the between-group share (labels shuffled, sizes preserved)."""
    y = np.asarray(y, float)
    g, sizes = _onehot(labels)
    obs = float(_shares_for_rows(y[None, :], g, sizes)[0])
    idx = _perm_index(len(y), n_perm, rng)
    null = _shares_for_rows(y[idx], g, sizes)
    p = (1 + int(np.sum(null >= obs - 1e-12))) / (n_perm + 1)
    lo, hi = np.quantile(null, [0.025, 0.975])
    return {"observed": obs, "chance_mean": float(np.nanmean(null)), "null_lo": float(lo),
            "null_hi": float(hi), "p_one_sided": float(p), "n_perm": int(n_perm), "n": int(len(y)),
            "n_groups": int(len(sizes))}


def power_simulation(sizes, grid=POWER_GRID, n_sim: int = POWER_SIMS, n_perm: int = POWER_PERMS,
                     seed: int = POWER_SEED, target: float = POWER_TARGET, alpha: float = ALPHA) -> dict:
    """Power of the one-sided permutation test of the between share for the realized group sizes.

    Model: y = group effect + noise, group effects N(0, s), noise N(0, 1 - s), so the population
    between-group share of variance is s. Each simulated dataset gets the same permutation test used on the
    observed data. Reports the smallest grid share reaching `target` power, a linear-interpolated crossing,
    and the mean sample-share excess over chance at that share.
    """
    sizes = [int(s) for s in sizes]
    lab = np.repeat(np.arange(len(sizes)), sizes)
    n = lab.size
    g, gs = _onehot(lab)
    rng = np.random.default_rng(seed)
    idx = _perm_index(n, n_perm, rng)  # exchangeable null: one permutation matrix serves every dataset
    curve = []
    for s in grid:
        eff = rng.normal(size=(n_sim, len(sizes))) * math.sqrt(s)
        y = eff[:, lab] + rng.normal(size=(n_sim, n)) * math.sqrt(1 - s)
        obs = _shares_for_rows(y, g, gs)
        rej = 0
        for i in range(n_sim):
            null = _shares_for_rows(y[i][idx], g, gs)
            p = (1 + np.sum(null >= obs[i] - 1e-12)) / (n_perm + 1)
            rej += p <= alpha
        curve.append({"true_share": float(s), "power": rej / n_sim, "mean_observed_share": float(obs.mean())})
    null_mean = curve[0]["mean_observed_share"] if grid and grid[0] == 0 else (len(sizes) - 1) / (n - 1)
    hit = next((c for c in curve if c["power"] >= target), None)
    interp = float("nan")
    for a, b in zip(curve, curve[1:]):
        if a["power"] < target <= b["power"]:
            w = (target - a["power"]) / (b["power"] - a["power"])
            interp = a["true_share"] + w * (b["true_share"] - a["true_share"])
            break
    return {
        "curve": curve, "n": int(n), "n_groups": len(sizes), "sizes": sizes, "target_power": target,
        "alpha": alpha, "n_sim": n_sim, "n_perm": n_perm, "seed": seed,
        "chance_mean_share": float(null_mean),
        "min_detectable_share": hit["true_share"] if hit else float("nan"),
        "min_detectable_share_interpolated": interp,
        "min_detectable_excess": (hit["mean_observed_share"] - null_mean) if hit else float("nan"),
    }


def loo_mate_mean(series: pd.Series, prof: pd.Series) -> pd.Series:
    """Leave-one-out mean of the other members of each unit's sign profile (NaN for singletons)."""
    prof = prof.reindex(series.index)
    out = {}
    for cc, v in series.items():
        mates = series[(prof == prof[cc]).to_numpy()].drop(cc)
        out[cc] = float(mates.mean()) if len(mates) else float("nan")
    return pd.Series(out, name=series.name)


def ratio(num: float, den: float) -> float:
    if not (math.isfinite(num) and math.isfinite(den)) or den == 0:
        return float("nan")
    return num / den


# --------------------------------------------------------------- row ledger
def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


class Ledger:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, part: str, column: str, surface: str, statistic: str, value: float,
            lo: float = float("nan"), hi: float = float("nan"), n: int | None = None,
            interval: str = INT_NONE, note: str = "") -> None:
        cid = "C9_" + "_".join([part.split("_")[0], _slug(column), _slug(surface), _slug(statistic)])
        label = f"{surface} | {column} | {note + ' | ' if note else ''}{TAG}"
        self.rows.append({
            "claim_id": cid, "part": part, "column": column, "statistic": statistic,
            "value": _f(value), "ci_low": _f(lo), "ci_high": _f(hi),
            "n": None if n is None else int(n), "interval_type": interval,
            "surface_label": label, "surface_label_short": surface, "note": note,
        })

    def boot(self, part: str, column: str, surface: str, statistic: str, r: dict,
             interval: str, note: str = "") -> None:
        self.add(part, column, surface, statistic, r["point"], r["ci_lo"], r["ci_hi"], r["n"],
                 interval, note)


def _f(x) -> float | None:
    x = float(x)
    return x if math.isfinite(x) else None


# --------------------------------------------------------------- the run
def _boot(a: pd.Series, b: pd.Series, prof: pd.Series | None, seed: int) -> dict:
    cl = None if prof is None else prof.reindex(a.index)
    return A.bootstrap_spearman(a, b, clusters=cl, draws=BOOT_DRAWS, seed=seed)


def _sha(p: Path) -> str:
    return A.sha256_file(Path(p))


def run(out_dir: Path | None = None, n_perm: int = N_PERM) -> dict:
    out_dir = Path(out_dir or OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    probs = pd.read_csv(COHORT1_PROBS, dtype={"option_code": str, "question_id": str})
    human = A.load_human_means(A.DEFAULT_HUMAN_MEANS)
    z = A.load_gps_z(A.DEFAULT_GPS_JSON)
    items = A.model_item_table(probs)
    countries = sorted(set(items.country) & set(human.country))
    profiles = A.sign_profiles(z, countries, P.PROF_DIMS)
    prof = profiles.set_index("country").profile_id
    gps = z.pivot(index="country", columns="dimension", values="z").reindex(countries)
    sizes_by_prof = prof.value_counts()
    multi_idx = prof.index[prof.map(sizes_by_prof) > 1]
    n_multi_profiles = int((sizes_by_prof > 1).sum())

    # bank 2 -> countries
    gps_raw = B2.load_gps_raw()
    units = B2.country_units(gps_raw, countries)
    part_a = {frozenset(g.index) for _, g in prof.groupby(prof)}
    part_b = {frozenset(g.index) for _, g in units.groupby(units)}
    same_partition = part_a == part_b
    if not same_partition:
        raise RuntimeError("bank-2 unit partition differs from sign_profiles partition")
    comp_b2 = B2.surface_composites(ADAPTER_STRICT_V1)

    L = Ledger()
    series = {}
    for s, qs in P.SURFACES.items():
        series[s] = {
            "human": P.human_surface(human, qs),
            "adapter": P.surface_values(items, "adapter", s, qs),
            "bank2": B2.unit_series(comp_b2, s, units),
            "gps": gps[s.split(":")[0]],
        }

    # ---- a. cohort-1 three columns
    for s in SURFACES:
        d = series[s]
        L.boot("a_cohort1_three_column", "adapter-GPS", s, "Spearman rho",
               _boot(d["adapter"], d["gps"].reindex(d["adapter"].index), prof, PROFILE_SEED), INT_PROFILE)
        L.boot("a_cohort1_three_column", "adapter-human", s, "Spearman rho",
               _boot(d["adapter"], d["human"].reindex(d["adapter"].index), prof, PROFILE_SEED), INT_PROFILE)
        L.boot("a_cohort1_three_column", "human-GPS", s, "Spearman rho",
               _boot(d["human"], d["gps"].reindex(d["human"].index), None, COUNTRY_SEED), INT_COUNTRY)

    # ---- b. bank-2 adapters mapped to countries (cluster = bank-2 profile cell, as banked)
    for s in SURFACES:
        d = series[s]
        L.boot("b_bank2", "adapter-GPS", s, "Spearman rho",
               _boot(d["bank2"], d["gps"].reindex(d["bank2"].index), units, PROFILE_SEED), INT_PROFILE,
               "bank-2 robustness column")
        L.boot("b_bank2", "adapter-human", s, "Spearman rho",
               _boot(d["bank2"], d["human"].reindex(d["bank2"].index), units, PROFILE_SEED), INT_PROFILE,
               "bank-2 robustness column")

    # ---- c. between-profile share and permutation test
    perm_records = {}
    for i_s, s in enumerate(SURFACES):
        for i_a, arm in enumerate(("human", "adapter")):
            ser = series[s][arm]
            col = arm
            ref = P.variance_share(ser, profiles)
            L.add("c_between_profile", col, s, "between share, all countries",
                  ref["between_share_all"], n=ref["n_countries"],
                  note=f"{ref['n_profiles']} profiles incl. singletons")
            g = prof.reindex(ser.index)
            keep = g.map(g.value_counts()) > 1
            y = ser[keep].to_numpy(float)
            lab = g[keep].to_numpy()
            rng = np.random.default_rng([PERM_SEED, i_s, i_a])
            res = permutation_between(y, lab, n_perm, rng)
            if abs(res["observed"] - ref["between_share_multi_member"]) > 1e-9:
                raise RuntimeError(f"multi-member share mismatch on {s}/{arm}")
            perm_records[(s, arm)] = res
            note = f"{res['n_groups']} multi-member profiles"
            L.add("c_between_profile", col, s, "between share, multi-member", res["observed"],
                  n=res["n"], note=note)
            L.add("c_between_profile", col, s, "chance mean, multi-member", res["chance_mean"],
                  res["null_lo"], res["null_hi"], res["n"], INT_NULL, note)
            L.add("c_between_profile", col, s, "permutation p (one-sided), multi-member",
                  res["p_one_sided"], n=res["n"], note=f"{note}; {res['n_perm']} permutations")
    sizes_multi = sorted(int(v) for v in sizes_by_prof[sizes_by_prof > 1].values)
    power = power_simulation(sizes_multi)
    L.add("c_power", "design", "12-group multi-member design", "smallest true between-share detectable at 80% power",
          power["min_detectable_share"], n=power["n"],
          note=f"{power['n_groups']} groups, sizes {sizes_multi}; grid step 0.05; "
               f"{power['n_sim']} sims x {power['n_perm']} perms; alpha {power['alpha']}")
    L.add("c_power", "design", "12-group multi-member design", "interpolated true between-share at 80% power",
          power["min_detectable_share_interpolated"], n=power["n"], note="linear interpolation on the grid")
    L.add("c_power", "design", "12-group multi-member design", "chance mean of between share (simulated, s=0)",
          power["chance_mean_share"], n=power["n"])
    L.add("c_power", "design", "12-group multi-member design",
          "smallest detectable excess of expected sample share over chance, 80% power",
          power["min_detectable_excess"], n=power["n"])

    # ---- d. sign-mate agreement (NOT a ceiling) and same-sample comparators
    d_note = "sign-mate agreement, NOT a ceiling"
    for s in SURFACES:
        h = series[s]["human"]
        mates = loo_mate_mean(h, prof)
        keep = mates.dropna().index.intersection(multi_idx)
        L.boot("d_sign_mate", "human vs LOO sign-mates", s, "Spearman rho",
               _boot(h.reindex(keep), mates.reindex(keep), prof, PROFILE_SEED), INT_PROFILE, d_note)
        a = series[s]["adapter"].reindex(keep)
        L.boot("d_sign_mate", "adapter-human (same multi-member sample)", s, "Spearman rho",
               _boot(a, h.reindex(keep), prof, PROFILE_SEED), INT_PROFILE,
               "cohort-1 adapters on the sign-mate sample")
        b = series[s]["bank2"].reindex(keep)
        L.boot("d_sign_mate", "bank-2 adapter-human (same multi-member sample)", s, "Spearman rho",
               _boot(b, h.reindex(keep), prof, PROFILE_SEED), INT_PROFILE,
               "bank-2 adapters on the sign-mate sample")

    # ---- e. GPS-side sign-copier references
    e_rows = {}
    for s in SURFACES:
        zz = series[s]["gps"]
        own = _boot(np.sign(zz).rename("sign"), zz, prof, PROFILE_SEED)
        mz = loo_mate_mean(zz, prof)
        keep = mz.dropna().index.intersection(multi_idx)
        loo = _boot(mz.reindex(keep), zz.reindex(keep), prof, PROFILE_SEED)
        a_gps = _boot(series[s]["adapter"], zz.reindex(series[s]["adapter"].index), prof, PROFILE_SEED)
        b_gps = _boot(series[s]["bank2"], zz.reindex(series[s]["bank2"].index), units, PROFILE_SEED)
        a_gps_multi = _boot(series[s]["adapter"].reindex(keep), zz.reindex(keep), prof, PROFILE_SEED)
        L.boot("e_gps_sign_reference", "own-sign reference", s, "Spearman(sign(z), z)", own, INT_PROFILE,
               "perfect sign-copier on GPS")
        L.boot("e_gps_sign_reference", "LOO profile-mean z", s, "Spearman(LOO profile-mean z, z)", loo,
               INT_PROFILE, "multi-member countries only")
        L.add("e_gps_sign_reference", "cohort-1 adapter / own-sign reference", s,
              "ratio of adapter-GPS to own-sign reference", ratio(a_gps["point"], own["point"]),
              n=a_gps["n"], note="ratio of point values; no interval")
        L.add("e_gps_sign_reference", "bank-2 adapter / own-sign reference", s,
              "ratio of adapter-GPS to own-sign reference", ratio(b_gps["point"], own["point"]),
              n=b_gps["n"], note="ratio of point values; no interval")
        L.boot("e_gps_sign_reference", "cohort-1 adapter-GPS (multi-member sample)", s, "Spearman rho",
               a_gps_multi, INT_PROFILE, "same 28 countries as the LOO reference")
        L.add("e_gps_sign_reference", "cohort-1 adapter / LOO profile-mean reference (same n)", s,
              "ratio of adapter-GPS to LOO reference", ratio(a_gps_multi["point"], loo["point"]),
              n=a_gps_multi["n"], note="ratio of point values; no interval")
        e_rows[s] = {"own": own["point"], "loo": loo["point"], "adapter_gps": a_gps["point"]}

    # ---- f. preprint comparison items on 42 countries
    gz_trust = gps["trust"]
    q57_h = human[human.item == "Q57"].set_index("country")["mean"]
    q57_a = items[(items.model == "adapter") & (items.item == "Q57")].set_index("country")["e_recode"]
    L.boot("f_preprint_items", "human-GPS", "trust:Q57 alone", "Spearman rho",
           _boot(q57_h, gz_trust.reindex(q57_h.index), None, COUNTRY_SEED), INT_COUNTRY,
           "preprint reported 0.15 on 16 countries")
    L.boot("f_preprint_items", "adapter-GPS", "trust:Q57 alone", "Spearman rho",
           _boot(q57_a, gz_trust.reindex(q57_a.index), prof, PROFILE_SEED), INT_PROFILE)
    L.boot("f_preprint_items", "adapter-human", "trust:Q57 alone", "Spearman rho",
           _boot(q57_a, q57_h.reindex(q57_a.index), prof, PROFILE_SEED), INT_PROFILE)
    for q in ("patience:Q43", "patience:Q50"):
        d = series[q]
        L.boot("f_preprint_items", "human-GPS", q, "Spearman rho",
               _boot(d["human"], d["gps"].reindex(d["human"].index), None, COUNTRY_SEED), INT_COUNTRY,
               "preprint patience items kept unpooled")
    rk = series["risktaking"]
    human_missing = sorted(set(rk["adapter"].index) - set(rk["human"].index))
    L.boot("f_preprint_items", "human-GPS", "risktaking (complete case)", "Spearman rho",
           _boot(rk["human"], rk["gps"].reindex(rk["human"].index), None, COUNTRY_SEED), INT_COUNTRY,
           "human side is complete case on all 4 items")
    risk_all = rk["adapter"]
    risk_drop = risk_all.drop(labels=["JOR"], errors="ignore")
    L.boot("f_preprint_items", "adapter-GPS", "risktaking with JOR", "Spearman rho",
           _boot(risk_all, rk["gps"].reindex(risk_all.index), prof, PROFILE_SEED), INT_PROFILE)
    L.boot("f_preprint_items", "adapter-GPS", "risktaking without JOR", "Spearman rho",
           _boot(risk_drop, rk["gps"].reindex(risk_drop.index), prof, PROFILE_SEED), INT_PROFILE)
    L.boot("f_preprint_items", "adapter-human", "risktaking (complete case)", "Spearman rho",
           _boot(risk_all, rk["human"].reindex(risk_all.index), prof, PROFILE_SEED), INT_PROFILE,
           "pairwise-complete on the human side")

    # ---- write
    rows = L.rows
    ids = [r["claim_id"] for r in rows]
    if len(ids) != len(set(ids)):
        dup = sorted({i for i in ids if ids.count(i) > 1})
        raise RuntimeError(f"duplicate claim ids: {dup[:5]}")
    by_part: dict[str, int] = {}
    for r in rows:
        by_part[r["part"]] = by_part.get(r["part"], 0) + 1
    meta = {
        "label": TAG,
        "generated_by": "paper_b/c9_human_agreement.py",
        "seeds": {"profile_bootstrap": PROFILE_SEED, "country_bootstrap": COUNTRY_SEED,
                  "permutation": PERM_SEED, "power": POWER_SEED},
        "bootstrap_draws": BOOT_DRAWS, "n_permutations": n_perm,
        "n_countries": len(countries), "n_profiles": int(sizes_by_prof.size),
        "n_multi_member_profiles": n_multi_profiles, "n_multi_member_countries": int(len(multi_idx)),
        "multi_member_profile_sizes": sizes_multi,
        "bank2_partition_identical_to_sign_profiles": bool(same_partition),
        "human_missing_on_risktaking": human_missing,
        "inputs": {
            "cohort1_model_probs": {"path": str(COHORT1_PROBS.relative_to(REPO)), "sha256": _sha(COHORT1_PROBS)},
            "bank2_adapter_strict_v1": {"path": str(ADAPTER_STRICT_V1), "sha256": _sha(ADAPTER_STRICT_V1)},
            "gps_z": {"path": str(A.DEFAULT_GPS_JSON.relative_to(REPO)), "sha256": _sha(A.DEFAULT_GPS_JSON)},
            "human_item_means (local only, not committed)": {
                "path": str(A.DEFAULT_HUMAN_MEANS.relative_to(REPO)), "sha256": _sha(A.DEFAULT_HUMAN_MEANS)},
        },
        "notes": [
            "Bank-2 between-profile share is 1.0 by construction (one adapter per profile), so it is not tabulated.",
            "Sign-mate agreement is a leave-one-out agreement among countries sharing a GPS sign profile, "
            "NOT a ceiling on human prediction.",
            "Power model: Gaussian group effects, equal noise; population share s = effect variance / total.",
        ],
    }
    payload = {"meta": meta, "rows": rows, "rows_by_part": by_part, "power": power}
    (out_dir / "c9_human_agreement.json").write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    cols = ["claim_id", "statistic", "value", "ci_low", "ci_high", "n", "interval_type", "surface_label",
            "part", "column", "surface_label_short"]
    pd.DataFrame(rows)[cols].to_csv(out_dir / "c9_human_agreement.csv", index=False)
    return {"rows": rows, "rows_by_part": by_part, "meta": meta, "power": power,
            "perm": {f"{k[0]}|{k[1]}": v for k, v in perm_records.items()}, "e_rows": e_rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    ap.add_argument("--n-perm", type=int, default=N_PERM)
    a = ap.parse_args(argv)
    res = run(Path(a.out_dir), a.n_perm)
    print("wrote", a.out_dir, res["rows_by_part"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
