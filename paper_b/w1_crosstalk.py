#!/usr/bin/env python3
"""W1 'why trust works': own-bit vs cross-talk decomposition of the factorial main effects.

DESCRIPTIVE / NOT PREREGISTERED (the 10-11 surface has already been seen). Synthetic model
quantities plus GPS z (published, Falk et al. 2018). No human respondent data is read.

Model. Each surface composite over the 64 sign cells is fit with the probe design
(factorial_effects.fit: intercept, six main effects with x = +/-0.5, fifteen two-way terms). For a
country with sign bits b_k, the main-effects prediction of surface s is

    full(c, s)  = sum_k beta[k, s] * (b_k(c) - 0.5)
    own(c, s)   = beta[dim(s), s] * (b_dim(s)(c) - 0.5)
    cross(c, s) = full - own

Outputs: planning/sprint_2026-10-11/paper-b-tier1/results/c9/w1_why_trust.{json,md}

  python paper_b/w1_crosstalk.py [--out DIR] [--reading FILE]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
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
import factorial_effects as FE  # noqa: E402
from probe_select import design  # noqa: E402

INPUTS = Path("/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs")
OUT = REPO / "planning/sprint_2026-10-11/paper-b-tier1/results/c9"
BANK1 = REPO / "synthetic_generation/outputs/gps_sign_relabel_all"
BANK2 = REPO / "synthetic_generation/outputs/gps_sign_relabel_bank2"
NUMBERS = REPO / "planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv"
SURFACES = ["trust", "risktaking", "patience:Q43", "patience:Q50", "altruism", "posrecip", "negrecip"]
SURF_DIM = {s: s.split(":")[0] for s in SURFACES}

# Keyword families are declared here, before any count (stems; matched at word start).
KEYWORDS = {
    "trust": ["trust", "rely", "relies", "honest", "faith", "suspicio", "betray", "doubt", "confid"],
    "risktaking": ["risk", "gambl", "uncertain", "bold", "venture", "safe", "stable", "secure", "leap"],
    "patience": ["patien", "wait", "later", "future", "immediate", "save", "saving", "delay",
                 "long-term", "short-term", "invest"],
    "altruism": ["donat", "volunteer", "give", "giving", "charit", "generous", "selfless",
                 "sacrific", "community", "help"],
    "posrecip": ["grateful", "gratitude", "thank", "repay", "return the", "favor", "owe",
                 "reciproc", "appreciat", "kindness"],
    "negrecip": ["reveng", "retaliat", "punish", "wrong", "insult", "unfair", "payback", "get back",
                 "deserve", "betray", "hurt"],
}


# ------------------------------------------------------------------ model pieces
def effect_matrix(comp: pd.DataFrame) -> pd.DataFrame:
    """6 x 7 main-effect matrix (rows = bit, cols = surface), main effect per bit flip 0 -> 1."""
    return FE.effect_matrix(comp[comp.unit.isin(F.all_units())])[SURFACES]


def decompose(matrix: pd.DataFrame, surface: str, bits: pd.DataFrame) -> pd.DataFrame:
    """full / own / cross predictions per row of `bits` (columns = F.DIMS, values 0/1)."""
    x = bits[F.DIMS].astype(float) - 0.5
    beta = matrix[surface].reindex(F.DIMS)
    full = x.mul(beta, axis=1).sum(axis=1)
    dim = SURF_DIM[surface]
    own = x[dim] * float(beta[dim])
    return pd.DataFrame({"full": full, "own": own, "cross": full - own})


def cross_variance_share(d: pd.DataFrame) -> float:
    """Var(cross) / Var(full) over the rows (population variance)."""
    v = float(np.var(d["full"].to_numpy(float)))
    return float(np.var(d["cross"].to_numpy(float)) / v) if v > 0 else float("nan")


def cross_cov_share(d: pd.DataFrame) -> float:
    """Cov(cross, full) / Var(full): the covariance-based share (own's share is 1 minus this)."""
    v = float(np.var(d["full"].to_numpy(float)))
    if v <= 0:
        return float("nan")
    return float(np.cov(d["cross"], d["full"], bias=True)[0, 1] / v)


def _y64(y: pd.Series) -> np.ndarray:
    order = {u: i for i, u in enumerate(F.all_units())}
    yy = np.full(len(order), np.nan)
    for u, v in y.items():
        yy[order[u]] = float(v)
    if np.isnan(yy).any():
        raise ValueError("surface is missing factorial cells")
    return yy


def main_effect_share(y: pd.Series) -> float:
    """Share of the 64-cell variance (about the mean) carried by the six main effects."""
    X, _ = design()
    yy = _y64(y)
    beta = np.linalg.lstsq(X, yy, rcond=None)[0]
    fitted = X[:, :7] @ beta[:7]
    tot = float(np.sum((yy - yy.mean()) ** 2))
    return float(np.sum((fitted - yy.mean()) ** 2) / tot) if tot > 0 else float("nan")


def full_model_prediction(y: pd.Series, bits: pd.DataFrame) -> pd.Series:
    """Main + two-way fitted value of the 64-cell surface, evaluated at the countries' cells."""
    X, _ = design()
    yy = _y64(y)
    fitted = X @ np.linalg.lstsq(X, yy, rcond=None)[0]
    order = {u: i for i, u in enumerate(F.all_units())}
    return pd.Series([fitted[order[F.unit_of_bits(list(r))]] for r in bits[F.DIMS].to_numpy(int)],
                     index=bits.index)


def rho(a: pd.Series, b: pd.Series) -> float:
    """Country-equal Spearman; NaN (never an error) when a series is constant."""
    return float(AS.spearman_country_equal(a, b)[0])


# ------------------------------------------------------------------ data loading
def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"option_code": str, "question_id": str})


def composites_wide(comp: pd.DataFrame) -> pd.DataFrame:
    return comp.pivot(index="unit", columns="surface", values="composite")[SURFACES]


def load_routes() -> dict:
    out = {}
    for route, f in (("adapter", "adapter_strict_v1.csv"), ("signprompt", "signprompt_strict_64.csv")):
        comp = AF.unit_composites(_read(INPUTS / f))
        comp = comp[comp.unit.isin(F.all_units())]
        out[route] = {"comp": comp, "wide": composites_wide(comp), "matrix": effect_matrix(comp)}
    return out


def load_cohort1() -> pd.DataFrame:
    """Cohort-1 country composites (wide: country x surface)."""
    comp = AF.unit_composites(_read(INPUTS / "cohort1_strict.csv"))
    return comp.pivot(index="unit", columns="surface", values="composite")[SURFACES]


def country_frame(countries) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """(bits, gps z, unit) per country from the bank-1 GPS vectors."""
    z = AS.load_gps_z(AS.DEFAULT_GPS_JSON).pivot(index="country", columns="dimension", values="z")
    z = z.reindex(list(countries))[F.DIMS]
    bits = (z >= 0).astype(int)
    units = pd.Series([F.unit_of_bits(list(r)) for r in bits.to_numpy()], index=bits.index)
    return bits, z, units


# ------------------------------------------------------------------ decomposition driver
def surface_block(matrix: pd.DataFrame, observed: pd.Series, bits: pd.DataFrame, z: pd.DataFrame,
                  surface: str, y64: pd.Series | None, profile: pd.Series) -> dict:
    """One surface: decomposition stats against `observed` (country-indexed) and GPS z."""
    dim = SURF_DIM[surface]
    d = decompose(matrix, surface, bits)
    gz = z[dim]
    boot = AS.bootstrap_spearman(observed, gz, clusters=profile.reindex(observed.index),
                                 draws=AS.BOOT_DRAWS, seed=AS.BOOT_SEED)
    cross = matrix[surface].drop(dim)
    top = cross.abs().idxmax()
    row = {
        "surface": surface, "dimension": dim, "n": int(len(d)),
        "own_beta": float(matrix.loc[dim, surface]),
        "largest_cross_bit": str(top), "largest_cross_beta": float(cross.loc[top]),
        "spearman_full_vs_observed": rho(d["full"], observed),
        "spearman_observed_vs_gps": float(boot["point"]),
        "observed_vs_gps_ci": [float(boot["ci_lo"]), float(boot["ci_hi"])],
        "spearman_full_vs_gps": rho(d["full"], gz),
        "spearman_own_vs_gps": rho(d["own"], gz),
        "spearman_cross_vs_gps": rho(d["cross"], gz),
        "cross_var_share": cross_variance_share(d),
        "cross_cov_share": cross_cov_share(d),
    }
    if y64 is not None:
        sh = main_effect_share(y64)
        row["main_effect_share_64"] = sh
        row["interactions_needed"] = bool(sh < 0.8)
        if sh < 0.8:
            fm = full_model_prediction(y64, bits)
            row["spearman_main_plus_2way_vs_observed"] = rho(fm, observed)
            row["spearman_main_plus_2way_vs_gps"] = rho(fm, gz)
    return row


def rank_pairs(rows: list[dict], key: str = "cross_var_share") -> dict:
    """Does the cross-talk share rank the surfaces like their adapter-GPS failure? (n = 7, descriptive)."""
    fail = pd.Series({r["surface"]: 1.0 - r["spearman_observed_vs_gps"] for r in rows})
    share = pd.Series({r["surface"]: r[key] for r in rows})
    return {"statistic": key, "n": int(len(rows)),
            "spearman_share_vs_failure": float(AS.spearman_country_equal(share, fail, min_n=5)[0]),
            "pairs": [{"surface": s, "cross_share": float(share[s]),
                       "observed_gps_rho": float(1 - fail[s]), "failure_1_minus_rho": float(fail[s])}
                      for s in share.index]}


# ------------------------------------------------------------------ bank composition
def _words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", text or ""))


def load_bank(path: Path) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def keyword_shares(rows: list[dict]) -> pd.DataFrame:
    """Rows = pair dimension, cols = keyword family: share of those pairs whose text
    (prompt + both responses) contains a stem of the family."""
    pats = {k: re.compile(r"\b(?:" + "|".join(re.escape(s) for s in v) + ")", re.I)
            for k, v in KEYWORDS.items()}
    dims = sorted({r["gps_dimension"] for r in rows})
    out = pd.DataFrame(index=dims, columns=list(KEYWORDS), dtype=float)
    for d in dims:
        sub = [r for r in rows if r["gps_dimension"] == d]
        texts = [" ".join([r["prompt"], r["response_a"], r["response_b"]]) for r in sub]
        for k, p in pats.items():
            out.loc[d, k] = sum(bool(p.search(t)) for t in texts) / len(sub)
    return out


def label_check(bank_dir: Path, countries) -> dict:
    """Every pair's chosen side must follow the sign of the PAIR'S OWN dimension only."""
    z = AS.load_gps_z(AS.DEFAULT_GPS_JSON).pivot(index="country", columns="dimension", values="z")
    n = bad = 0
    countries = list(countries)
    for cc in countries:
        for r in load_bank(bank_dir / f"D_syn_{cc}.jsonl"):
            want = "A" if float(z.loc[cc, r["gps_dimension"]]) >= 0 else "B"
            got = r.get("chosen_option")
            if got is None:
                got = "A" if r["chosen"] == r["response_a"] else "B"
            n += 1
            bad += int(got != want)
    return {"rows_checked": n, "label_mismatches_vs_own_dimension_sign": bad,
            "countries": len(countries)}


def bank_composition(bank_dir: Path, countries, label: str) -> dict:
    rows = load_bank(bank_dir / "triplets_bank.jsonl")
    comp = {}
    for d in F.DIMS:
        sub = [r for r in rows if r["gps_dimension"] == d]
        pw = [_words(r["prompt"]) for r in sub]
        aw = [_words(r["response_a"]) for r in sub]
        bw = [_words(r["response_b"]) for r in sub]
        comp[d] = {"pairs": len(sub), "mean_prompt_words": statistics.mean(pw),
                   "mean_response_a_words": statistics.mean(aw),
                   "mean_response_b_words": statistics.mean(bw),
                   "mean_a_minus_b_words": statistics.mean(a - b for a, b in zip(aw, bw))}
    kw = keyword_shares(rows)
    out = {"bank": label, "total_pairs": len(rows), "per_dimension": comp,
           "keyword_share": {d: {k: float(kw.loc[d, k]) for k in kw.columns} for d in kw.index},
           "label_check": label_check(bank_dir, countries)}
    # Bank 1 stores per-response marker scores on all six dimensions: does a pair of one
    # dimension also separate A from B on the other dimensions' markers?
    if rows and rows[0].get("m_a_trust") is not None:
        def gap(d, k):
            v = [float(r[f"m_a_{k}"]) - float(r[f"m_b_{k}"]) for r in rows
                 if r["gps_dimension"] == d and r.get(f"m_a_{k}") is not None
                 and r.get(f"m_b_{k}") is not None]
            return statistics.mean(v) if v else float("nan")
        out["marker_gap_a_minus_b"] = {d: {k: gap(d, k) for k in F.DIMS} for d in F.DIMS}
        out["marker_pairs_with_scores"] = sum(r.get("m_a_trust") is not None for r in rows)
    else:
        out["marker_gap_a_minus_b"] = None
    return out


# ------------------------------------------------------------------ follow-up candidates
def item_effects(probs_path: Path) -> pd.DataFrame:
    """Item-level main effects of the six bits over the 64 cells (probe design)."""
    items = AS.model_item_table(_read(probs_path))
    items = items[items.country.isin(F.all_units())]
    X, _ = design()
    order = {u: i for i, u in enumerate(F.all_units())}
    rows = []
    for it, g in items.groupby("item"):
        y = np.empty(64)
        for u, v in zip(g.country, g.e_recode):
            y[order[u]] = v
        b = np.linalg.lstsq(X, y, rcond=None)[0]
        rows.append({"item": it, **{k: float(b[1 + i]) for i, k in enumerate(F.DIMS)},
                     "sd_cells": float(y.std())})
    return pd.DataFrame(rows).set_index("item")


def one_bit_pairs(z: pd.DataFrame, bit: str) -> list[dict]:
    out = []
    cs = list(z.index)
    for i, a in enumerate(cs):
        for b in cs[i + 1:]:
            diff = [d for d in F.DIMS if (z.loc[a, d] >= 0) != (z.loc[b, d] >= 0)]
            if diff == [bit]:
                out.append({"a": a, "b": b,
                            "min_abs_z_all_dims": min(float(z.loc[a].abs().min()), float(z.loc[b].abs().min())),
                            "z_gap_on_bit": float(abs(z.loc[a, bit] - z.loc[b, bit]))})
    return sorted(out, key=lambda r: -r["min_abs_z_all_dims"])


# ------------------------------------------------------------------ main
def route_report(name: str, matrix: pd.DataFrame, wide: pd.DataFrame, bits, z, units,
                 cohort1: pd.DataFrame) -> dict:
    rep = {"route": name, "matrix": matrix.to_dict(), "bank2_observed": [], "cohort1_observed": []}
    for s in SURFACES:
        obs = pd.Series([wide.loc[u, s] for u in units], index=units.index)
        rep["bank2_observed"].append(surface_block(matrix, obs, bits, z, s, wide[s], units))
        rep["cohort1_observed"].append(surface_block(matrix, cohort1[s].reindex(units.index),
                                                     bits, z, s, None, units))
    rep["rank_bank2_observed"] = rank_pairs(rep["bank2_observed"])
    rep["rank_cohort1_observed"] = rank_pairs(rep["cohort1_observed"])
    return rep


def build() -> dict:
    routes = load_routes()
    cohort1 = load_cohort1()
    countries = list(cohort1.index)
    bits, z, units = country_frame(countries)
    nt = pd.read_csv(NUMBERS).set_index("claim_id").value
    pins = []
    for route, tag in (("adapter", "adapter64"), ("signprompt", "signprompt64")):
        m = routes[route]["matrix"]
        for s in SURFACES:
            dim = SURF_DIM[s]
            key = f"FX_{tag}_{s.replace(':', '_')}_own_beta" if dim == "patience" else f"FX_{tag}_{dim}_own_beta"
            val, got = float(nt[key]), float(m.loc[dim, s])
            assert abs(got - val) < 1e-9, f"{key}: recomputed {got} != numbers table {val}"
            pins.append({"claim_id": key, "numbers_table": val, "recomputed": got})
    report = {"label": "DESCRIPTIVE / NOT PREREGISTERED; synthetic model quantities + GPS z only",
              "ci_method": f"adapter-side Spearman intervals: profile-block bootstrap, "
                           f"{AS.BOOT_DRAWS} draws, seed {AS.BOOT_SEED}",
              "n_countries": len(countries), "own_beta_pins_checked": pins}
    ad, sp = routes["adapter"], routes["signprompt"]
    report["adapter"] = route_report("adapter", ad["matrix"], ad["wide"], bits, z, units, cohort1)
    report["signprompt"] = route_report("signprompt", sp["matrix"], sp["wide"], bits, z, units, cohort1)
    # NOTE: the cohort-1 block of the sign-prompt route uses the sign-prompt betas as the model.
    report["bank_composition"] = {"bank1": bank_composition(BANK1, countries, "bank1"),
                                  "bank2": bank_composition(BANK2, countries, "bank2")}
    m, sd = ad["matrix"], ad["wide"].std()
    leak = {k: float(sum(abs(m.loc[k, s]) / sd[s] for s in SURFACES if SURF_DIM[s] != k)) for k in F.DIMS}
    bit = max(leak, key=leak.get)
    ie = item_effects(INPUTS / "adapter_strict_v1.csv")
    item_dim = {it: d for d, qs in AS.STRICT_ITEMS.items() for it in qs}
    cand = ie.assign(dim=pd.Series(item_dim))
    cand = cand[cand.dim != bit].copy()
    cand["ratio"] = cand[bit].abs() / cand.sd_cells
    top = cand.sort_values("ratio", ascending=False).head(6)
    pairs = one_bit_pairs(z, bit)
    report["follow_up"] = {
        "leak_score_by_bit": leak, "leakiest_bit": bit, "n_pairs": len(pairs), "pairs_top5": pairs[:5],
        "pair_rule": "countries differing in exactly this sign bit; ranked by the smallest |z| over all "
                     "six dimensions of either country (clean signs, rule fixed before any outcome)",
        "items_top6_non_own": [{"item": i, "dimension": str(r.dim), "bit_effect": float(r[bit]),
                                "abs_effect_over_cell_sd": float(r.ratio)} for i, r in top.iterrows()],
    }
    return report


def _f(x, p=3):
    return "nan" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{p}f}"


def render_md(r: dict, reading: str) -> str:
    L = ["# W1 why trust works: own-bit vs cross-talk decomposition", "",
         f"{r['label']}.", f"Intervals: {r['ci_method']}.", "",
         f"Countries: {r['n_countries']} (cohort 1). Prediction = sum_k beta[k,s]*(bit_k-0.5); "
         "own = own-bit term; cross = the other five bits. Own-bit betas equal the NUMBERS_TABLE "
         f"FX_*_own_beta rows ({len(r['own_beta_pins_checked'])} pins asserted).", ""]
    for route in ("adapter", "signprompt"):
        rep = r[route]
        L += [f"## {route}", "", "### (a) 6 bits x 7 surfaces main effects (composite units)", "",
              "```", pd.DataFrame(rep["matrix"]).loc[F.DIMS, SURFACES].round(3).to_string(), "```", ""]
        for key, title in (("bank2_observed", "observed = the route's own 64-cell composite at each country's sign cell"),
                           ("cohort1_observed", "observed = cohort-1 country composite (model = this route's betas)")):
            L += [f"### (b/c) {title}", "",
                  "surface | own_beta | top cross bit (beta) | rho(full,obs) | rho(obs,GPS) [CI] | "
                  "rho(full,GPS) | rho(own,GPS) | rho(cross,GPS) | cross var share | main-eff share (64 cells)"]
            for b in rep[key]:
                ms = _f(b["main_effect_share_64"]) if "main_effect_share_64" in b else "-"
                L.append(f"{b['surface']} | {_f(b['own_beta'])} | {b['largest_cross_bit']} "
                         f"({_f(b['largest_cross_beta'])}) | {_f(b['spearman_full_vs_observed'])} | "
                         f"{_f(b['spearman_observed_vs_gps'])} [{_f(b['observed_vs_gps_ci'][0])},"
                         f"{_f(b['observed_vs_gps_ci'][1])}] | {_f(b['spearman_full_vs_gps'])} | "
                         f"{_f(b['spearman_own_vs_gps'])} | {_f(b['spearman_cross_vs_gps'])} | "
                         f"{_f(b['cross_var_share'])} | {ms}")
            if key == "bank2_observed":
                extra = [b for b in rep[key] if b.get("interactions_needed")]
                L += ["", "Interactions are reported only where main effects explain < 80% of the 64-cell variance: " +
                      ("; ".join(f"{b['surface']} (share {_f(b['main_effect_share_64'])}, main+2way rho vs obs "
                                 f"{_f(b['spearman_main_plus_2way_vs_observed'])}, vs GPS "
                                 f"{_f(b['spearman_main_plus_2way_vs_gps'])})" for b in extra) or "none")]
            rk = rep["rank_" + key]
            L += ["", f"Cross-talk share vs failure to order like GPS, n=7 (descriptive): Spearman "
                      f"{_f(rk['spearman_share_vs_failure'])}",
                  "surface | cross var share | rho(observed, GPS) | failure (1 - rho)"]
            L += [f"{p['surface']} | {_f(p['cross_share'])} | {_f(p['observed_gps_rho'])} | "
                  f"{_f(p['failure_1_minus_rho'])}" for p in rk["pairs"]]
            L.append("")
    L += ["## (d) Bank composition (aggregates)", ""]
    for bk in ("bank1", "bank2"):
        b = r["bank_composition"][bk]
        L += [f"### {bk}: {b['total_pairs']} pairs", "",
              "dimension | pairs | prompt words | resp A words | resp B words | A minus B words"]
        for d, v in b["per_dimension"].items():
            L.append(f"{d} | {v['pairs']} | {_f(v['mean_prompt_words'], 1)} | {_f(v['mean_response_a_words'], 1)} | "
                     f"{_f(v['mean_response_b_words'], 1)} | {_f(v['mean_a_minus_b_words'], 1)}")
        lc = b["label_check"]
        L += ["", f"Label dependence: {lc['rows_checked']} country-pair rows over {lc['countries']} countries; "
                  f"{lc['label_mismatches_vs_own_dimension_sign']} disagree with the sign of the pair's own dimension "
                  "(0 = every label depends on exactly one dimension's sign).", "",
              "Keyword-family share (rows = pair dimension, cols = family):", "```",
              pd.DataFrame(b["keyword_share"]).T.loc[F.DIMS, F.DIMS].round(2).to_string(), "```", ""]
        if b["marker_gap_a_minus_b"]:
            L += ["Mean marker gap (A minus B) by pair dimension (rows) on each dimension's marker (cols):", "```",
                  pd.DataFrame(b["marker_gap_a_minus_b"]).T.loc[F.DIMS, F.DIMS].round(2).to_string(), "```", ""]
        else:
            L += ["(this bank stores no per-response marker scores)", ""]
    f = r["follow_up"]
    L += ["## (e) Mechanistic follow-up candidates", "",
          "Leak score by bit (sum over non-own surfaces of |beta| / surface SD over 64 cells): " +
          ", ".join(f"{k} {_f(v)}" for k, v in f["leak_score_by_bit"].items()),
          f"Leakiest bit: {f['leakiest_bit']}. {f['n_pairs']} cohort pairs differ in only that bit. Rule: {f['pair_rule']}.", ""]
    L += [f"pair {p['a']} vs {p['b']}: min |z| over six dims {_f(p['min_abs_z_all_dims'])}, "
          f"z gap on the bit {_f(p['z_gap_on_bit'])}" for p in f["pairs_top5"]]
    L += ["", "Items with the largest leaked effect of that bit (|effect| / cell SD), adapter route:"]
    L += [f"{i['item']} ({i['dimension']}): effect {_f(i['bit_effect'])}, ratio {_f(i['abs_effect_over_cell_sd'])}"
          for i in f["items_top6_non_own"]]
    L += ["", "## (e) Reading", "", reading, ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--reading", default=None, help="text of the (e) paragraph; default <out>/w1_reading.txt")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rep = build()
    (out / "w1_why_trust.json").write_text(json.dumps(rep, indent=1, default=float) + "\n")
    rp = Path(a.reading) if a.reading else out / "w1_reading.txt"
    reading = rp.read_text().strip() if rp.exists() else "(reading not yet written)"
    (out / "w1_why_trust.md").write_text(render_md(rep, reading) + "\n")
    print(f"wrote {out}/w1_why_trust.json and .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
