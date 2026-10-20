"""C9-2: the 2x2 {adapter, no adapter} x {country-named persona prompt, none} on 42 countries, TVD to human WVS.

Cells (the key names are the contract with `summarize`):
  base             base weights, neutral prompt          paper-b-20261011/model_probs.csv  (model == "base")
  adapter          cohort-1 country adapter, own country  paper-b-20261011/model_probs.csv  (model == "adapter")
  persona          base weights, country-named prompt     run persona-strict-v1-20261019
  adapter_persona  adapter + country-named prompt         run adapter-persona-strict-v1-20261019 (card C9-4)

`adapter_persona` is "pending" until its scores exist; the same `summarize` call fills it with no code change.
Everything here is DESCRIPTIVE / NOT PREREGISTERED. Human distributions are read from a local-only file and no
per-country human value is written out.

  env -u PYTHONPATH .venv/bin/python paper_b/c9_tvd.py [--draws N] [--no-fetch]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze_factorial as AF  # noqa: E402
import analyze_surface as AS  # noqa: E402
import bank2_transport as BT  # noqa: E402
import score_plan as SPL  # noqa: E402

REPO = HERE.parent
COHORT1_DIR = REPO / "planning/sprint_2026-10-11/paper-b-20261011"
MODEL_PROBS = COHORT1_DIR / "model_probs.csv"
HUMAN_DISTS = COHORT1_DIR / "local_eval/population_response_distributions.csv"   # local-only, licensed
METRICS_ALL = COHORT1_DIR / "local_eval/survey_question_metrics_all_models.csv"
RESULTS = REPO / "planning/sprint_2026-10-11/paper-b-tier1/results"
OUT_DIR = RESULTS / "c9"
PERSONA_STRICT = BT.INPUT_DIR / "persona_strict.csv"
PERSONA_RUN = "persona-strict-v1-20261019"
ADAPTER_PERSONA = BT.INPUT_DIR / "adapter_persona_strict.csv"
ADAPTER_PERSONA_RUN = "adapter-persona-strict-v1-20261019"
HF_ENV = Path("/Users/bonorinoa/.hermes/profiles/sca/.env")

CELLS = ["base", "adapter", "persona", "adapter_persona"]
COUNTRIES = list(SPL.PERSONA_COUNTRIES)
DRAWS = AS.BOOT_DRAWS
LABEL = "DESCRIPTIVE / NOT PREREGISTERED"
ITEM_DIM = {q: dim for dim, qs in AS.STRICT_ITEMS.items() for q in qs}
DIMS = list(AS.STRICT_ITEMS)


# ------------------------------------------------------------------ the cell TVD
def cell_tvd(scores: pd.DataFrame, human: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, str]]]:
    """TVD = 1/2 sum_j |P_model(j) - P_human(j)| per (eval_country, question), over the union of option codes.

    `scores`: eval_country, question_id, option_code, model_prob (one model per country).
    `human`:  eval_country, question_id, option_code, human_prob.
    A code absent on one side has mass 0 there. A model cell with no human distribution is skipped and listed
    (never dropped silently). Both sides must sum to 1.
    """
    hum = {k: dict(zip(g.option_code.astype(str), g.human_prob.astype(float)))
           for k, g in human.groupby(["eval_country", "question_id"], sort=True)}
    rows, skipped = [], []
    for (cc, q), g in scores.groupby(["eval_country", "question_id"], sort=True):
        if (cc, q) not in hum:
            skipped.append((str(cc), str(q)))
            continue
        codes = g.option_code.astype(str)
        if codes.duplicated().any():
            raise ValueError(f"{cc}/{q}: duplicate option_code rows (more than one model in the cell?)")
        rows.append({"country": str(cc), "item": str(q),
                     "tvd": AS.total_variation_distance(dict(zip(codes, g.model_prob.astype(float))), hum[(cc, q)])})
    return pd.DataFrame(rows, columns=["country", "item", "tvd"]), skipped


# ------------------------------------------------------------------ aggregation
def country_equal_mean(t: pd.DataFrame) -> float:
    """Mean over countries of each country's mean TVD (every country weighs the same)."""
    return float(t.groupby("country")["tvd"].mean().mean())


def pooled_mean(t: pd.DataFrame) -> float:
    """Mean over all (country, item) rows: the weighting of the preprint's 2x2 script."""
    return float(t["tvd"].mean())


def dimension_means(t: pd.DataFrame) -> dict[str, float]:
    """Country-equal mean TVD within each GPS dimension (dimensions with no rows are absent)."""
    d = t.assign(dim=t["item"].map(ITEM_DIM))
    if d["dim"].isna().any():
        raise ValueError(f"items outside the strict battery: {sorted(d.loc[d['dim'].isna(), 'item'].unique())}")
    return {dim: float(g.groupby("country")["tvd"].mean().mean())
            for dim, g in d.groupby("dim", sort=False)}


# ------------------------------------------------------------------ bootstrap
def bootstrap_mean(values: pd.Series, clusters: pd.Series | None, *, draws: int = DRAWS,
                   seed: int = AS.BOOT_SEED) -> dict:
    """Percentile 95% interval of the mean of per-country values.

    clusters given -> profile-block bootstrap (whole sign profiles are redrawn, all members move together);
    clusters None  -> country bootstrap. Resampling follows `analyze_surface.bootstrap_spearman`.
    """
    v = values.dropna()
    n = len(v)
    if n == 0:
        raise ValueError("no values to bootstrap")
    x = v.to_numpy(float)
    rng = np.random.default_rng(seed)
    if clusters is None:
        unit = "country"
        means = x[rng.integers(0, n, size=(draws, n))].mean(axis=1)
    else:
        unit = "profile_block"
        missing = sorted(set(v.index) - set(clusters.index))
        if missing:
            raise ValueError(f"cluster id missing for {missing}")
        cl = clusters.reindex(v.index).to_numpy()
        uniq = pd.unique(cl)
        pos = {c: np.where(cl == c)[0] for c in uniq}
        pick = rng.integers(0, len(uniq), size=(draws, len(uniq)))
        means = np.array([x[np.concatenate([pos[uniq[j]] for j in pick[i]])].mean() for i in range(draws)])
    lo, hi = (float(q) for q in np.quantile(means, [0.025, 0.975]))
    return {"point": float(x.mean()), "ci_lo": lo, "ci_hi": hi, "n": int(n), "draws": int(draws),
            "seed": int(seed), "unit": unit}


def paired_country_differences(a: pd.DataFrame, b: pd.DataFrame) -> pd.Series:
    """Per-country mean over items of (TVD_a - TVD_b). The two cells must cover the same (country, item) rows."""
    ka, kb = set(zip(a.country, a.item)), set(zip(b.country, b.item))
    if ka != kb:
        raise ValueError(f"cells differ in support: {len(ka - kb)} only in a, {len(kb - ka)} only in b")
    m = a.merge(b, on=["country", "item"], suffixes=("_a", "_b"))
    return (m["tvd_a"] - m["tvd_b"]).groupby(m["country"]).mean()


def _contrast(diff: pd.Series, clusters: pd.Series | None, draws: int, note: str) -> dict:
    out = {"label": f"{LABEL}: {note}", "n_countries": int(diff.notna().sum()),
           "profile_block": bootstrap_mean(diff, clusters, draws=draws, seed=AS.BOOT_SEED) if clusters is not None else None,
           "country": bootstrap_mean(diff, None, draws=draws, seed=AS.COUNTRY_BOOT_SEED)}
    return out


# ------------------------------------------------------------------ trust-GPS
def trust_composite(model_rows: pd.DataFrame) -> pd.Series:
    """Country -> trust composite (the shared recode path) for ONE cell's scores."""
    comp = AF.unit_composites(model_rows)
    return comp[comp.surface == "trust"].set_index("unit")["composite"].rename("trust")


def _trust_gps(df: pd.DataFrame, gps: pd.Series, clusters: pd.Series, draws: int) -> dict:
    comp = trust_composite(df)
    if comp.nunique() < 2:
        return {"status": "undefined", "reason": "trust composite is constant across countries", "n": int(len(comp))}
    g = gps.reindex(comp.index)
    return {"status": "ok",
            "profile_block": AS.bootstrap_spearman(comp, g, clusters=clusters.reindex(comp.index), draws=draws,
                                                   seed=AS.BOOT_SEED),
            "country": AS.bootstrap_spearman(comp, g, clusters=None, draws=draws, seed=AS.COUNTRY_BOOT_SEED)}


# ------------------------------------------------------------------ country from a model name
def country_of_model(model: str, countries) -> str:
    """The single country code among the `_`-separated tokens of a model name (persona_ARG, ARG_adapter_persona)."""
    cs = set(countries)
    hit = [t for t in str(model).split("_") if t in cs]
    if len(hit) != 1:
        raise ValueError(f"model name {model!r} names {len(hit)} cohort countries; need exactly one")
    return hit[0]


def with_eval_country(df: pd.DataFrame, countries=COUNTRIES) -> pd.DataFrame:
    """Add eval_country from the model name (score files of conditioned runs carry no such column)."""
    out = df.copy()
    if "eval_country" in out.columns and out["eval_country"].notna().all():
        return out
    names = out["model"].astype(str).unique()
    out["eval_country"] = out["model"].astype(str).map({m: country_of_model(m, countries) for m in names})
    return out


# ------------------------------------------------------------------ the whole analysis
def summarize(cells: dict, human: pd.DataFrame, clusters: pd.Series, gps_trust: pd.Series | None, *,
              draws: int = DRAWS) -> dict:
    """cells: name -> long scores (eval_country, question_id, option_code, model_prob) or None/absent = pending."""
    unknown = set(cells) - set(CELLS)
    if unknown:
        raise ValueError(f"unknown cells {sorted(unknown)}")
    res: dict = {"label": LABEL, "draws": int(draws), "seed_profile_block": AS.BOOT_SEED,
                 "seed_country": AS.COUNTRY_BOOT_SEED, "cells": {}, "contrasts": {}}
    tvds: dict[str, pd.DataFrame] = {}
    for name in CELLS:
        df = cells.get(name)
        if df is None or len(df) == 0:
            res["cells"][name] = {"status": "pending", "reason": "scores for this cell are not available yet"}
            continue
        t, skipped = cell_tvd(df, human)
        tvds[name] = t
        res["cells"][name] = {
            "status": "ok", "n_countries": int(t.country.nunique()), "n_cells": int(len(t)),
            "skipped_cells": [f"{c}/{q}" for c, q in skipped],
            "mean_tvd_country_equal": country_equal_mean(t), "mean_tvd_pooled": pooled_mean(t),
            "per_dimension": dimension_means(t),
            "trust_gps": None if gps_trust is None else _trust_gps(df, gps_trust, clusters, draws)}

    def add(key: str, diff: pd.Series, note: str) -> None:
        res["contrasts"][key] = _contrast(diff, clusters, draws, note)

    pair = paired_country_differences
    if {"adapter", "base"} <= set(tvds):
        add("adapter_minus_base", pair(tvds["adapter"], tvds["base"]), "TVD(adapter) - TVD(base); negative = adapter closer")
    if {"persona", "base"} <= set(tvds):
        add("persona_minus_base", pair(tvds["persona"], tvds["base"]), "TVD(persona) - TVD(base); negative = persona closer")
    if "adapter_persona" in tvds:
        for other, note in (("base", "TVD(adapter+persona) - TVD(base)"), ("adapter", "TVD(adapter+persona) - TVD(adapter)"),
                            ("persona", "TVD(adapter+persona) - TVD(persona)")):
            if other in tvds:
                add(f"adapter_persona_minus_{other}", pair(tvds["adapter_persona"], tvds[other]), note + "; negative = adapter+persona closer")
        if {"adapter", "base", "persona"} <= set(tvds):
            inter = pair(tvds["adapter_persona"], tvds["persona"]) - pair(tvds["adapter"], tvds["base"])
            add("interaction", inter, "(adapter+persona - persona) - (adapter - base): does the adapter shift differ with a persona prompt")
    return res


# ------------------------------------------------------------------ inputs
def load_cohort1_scores() -> pd.DataFrame:
    return pd.read_csv(MODEL_PROBS, dtype={"option_code": str, "question_id": str})


def load_human(path: Path = HUMAN_DISTS) -> pd.DataFrame:
    h = pd.read_csv(path, usecols=["eval_country", "question_id", "option_code", "population_prob"],
                    dtype={"option_code": str, "question_id": str})
    return h.rename(columns={"population_prob": "human_prob"})


def load_persona(path: Path = PERSONA_STRICT) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"option_code": str, "question_id": str})
    bad = sorted(set(df.model.astype(str)[~df.model.astype(str).str.startswith("persona_")]))
    if bad:
        raise ValueError(f"not a persona model: {bad[:5]}")
    df = with_eval_country(df)
    if sorted(df.eval_country.unique()) != sorted(COUNTRIES):
        raise ValueError("persona file does not cover the 42 cohort countries")
    return df


def _hf_token() -> str | None:
    tok = os.environ.get("HF_TOKEN")
    if tok:
        return tok
    if HF_ENV.is_file():
        for line in HF_ENV.read_text().splitlines():
            if line.startswith("HF_TOKEN="):
                return line.split("=", 1)[1].strip().strip("\"'") or None
    return None


def load_adapter_persona(fetch: bool = True) -> tuple[pd.DataFrame | None, dict]:
    """The fourth cell: a local file if present, else the Hub run `adapter-persona-strict-v1-20261019`; else None.

    Returns (scores or None, provenance). An incomplete run (not 42 countries) is an error, not a partial cell.
    The C9-4 gates (adapter loaded, base parity) are NOT re-verified here; the provenance says where the rows came from.
    """
    if ADAPTER_PERSONA.is_file():
        df = pd.read_csv(ADAPTER_PERSONA, dtype={"option_code": str, "question_id": str})
        prov = {"source": str(ADAPTER_PERSONA), "sha256": AS.sha256_file(ADAPTER_PERSONA)}
    else:
        tok = _hf_token() if fetch else None
        if not tok:
            return None, {"source": None, "reason": "no local file and Hub not queried"}
        from huggingface_hub import HfApi, hf_hub_download
        prefix = f"runs/{ADAPTER_PERSONA_RUN}/synthetic/"
        files = sorted(f for f in HfApi(token=tok).list_repo_files(SPL.ARTIFACTS_REPO, repo_type="dataset")
                       if f.startswith(prefix) and f.endswith("_option_probabilities.csv"))
        if not files:
            return None, {"source": None, "reason": f"no files under {SPL.ARTIFACTS_REPO}/{prefix} on the Hub"}
        parts = [pd.read_csv(hf_hub_download(SPL.ARTIFACTS_REPO, f, repo_type="dataset", token=tok),
                             dtype={"option_code": str, "question_id": str}) for f in files]
        df = pd.concat(parts, ignore_index=True)
        prov = {"source": f"hub:{SPL.ARTIFACTS_REPO}/{prefix}", "files": len(files)}
    df = with_eval_country(df)
    if sorted(df.eval_country.unique()) != sorted(COUNTRIES):
        raise ValueError(f"adapter+persona scores cover {df.eval_country.nunique()} countries, not 42")
    return df, prov


def load_trust_gps(countries=COUNTRIES) -> pd.Series:
    z = AS.load_gps_z(AS.DEFAULT_GPS_JSON)
    return z[(z.dimension == "trust") & z.country.isin(set(countries))].set_index("country")["z"].sort_index()


def load_profiles(countries) -> pd.Series:
    z = AS.load_gps_z(AS.DEFAULT_GPS_JSON)
    return AS.sign_profiles(z, countries, BT.PROF_DIMS).set_index("country")["profile_id"]


# ------------------------------------------------------------------ outputs
def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not math.isfinite(float(o)) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    return o


def _f(x) -> str:
    return "n/a" if x is None or not math.isfinite(float(x)) else f"{float(x):.3f}"


def _ci(r: dict | None) -> str:
    return "n/a" if not r else f"{_f(r['point'])} [{_f(r['ci_lo'])}, {_f(r['ci_hi'])}]"


DEFINITION = """\
## Step 1: the preprint's TVD definition (source lines, as found)

Per cell (country c, item q), `misc/arxiv-submission-2026-10-05/methodology.tex:72`:

    \\mathrm{TVD}_{cq}=\\tfrac12\\sum_j|\\widehat P_c(j\\mid x_q)-P_c^{H}(j\\mid q)|,

with P^H "the survey-weighted share of valid human answers to item q in group c that equal code j" (methodology.tex:73).

Producer of `analysis/phase2/outputs/2x2_tvd.csv`: `analysis/phase2/18_2x2_analysis.py`.
- Join (line 195): model and population probabilities are merged on `option_value` with `how="inner"`; a cell with
  fewer than 2 matched options is dropped (line 196: `if len(merged) < 2: continue`).
- Renormalisation (lines 201-202): both vectors are divided by their sums after the inner join.
- TVD (line 203): `tvd = 0.5 * np.abs(pm - pp).sum()`.
- Aggregation (lines 222-223): `metrics.groupby("cell")[["tv_distance","top_option_match"]].mean()`, i.e. a POOLED
  mean over all (country, item) rows of a cell. Countries are not weighted equally when the item counts differ.
- Item set: the script applies no item filter; it averages whatever items the score files hold. The paper text says
  "TVD averages 368 country-item cells" (results.tex:54), which is 16 countries x 23 strict items.
- Skipped cells: a (country, item) without a human distribution is absent from the population file and is dropped by
  the inner join with no ledger. In the 42-country stack the ledger `local_eval/skipped_population_questions.csv` lists
  EGY/Q69, EGY/Q70, EGY/Q71, GBR/Q174 and JOR/Q178 (no valid responses); Q69-71 and Q174 are not strict-battery items,
  so only JOR/Q178 removes a battery cell here.

Differences in this Paper B re-run (declared, not silent):
- Headline mean TVD is COUNTRY-EQUAL (mean of country means), as the card asks; the preprint's pooled mean is reported
  beside it as `mean_tvd_pooled`. With one skipped cell the two differ only through JOR.
- Join is on `option_code` over the UNION of codes (a code missing on one side has mass 0), with no renormalisation;
  both sides must already sum to 1. This is the repo's audited convention (`eval_lib.calculate_question_metrics`) and is
  checked against `local_eval/survey_question_metrics_all_models.csv` (see the test).
- The adapter cell is each country's own adapter evaluated on that country (relationship "matched").
- Every number comes from the frozen Paper B stack; no preprint value is carried over.
"""


def render_md(res: dict, inputs: dict) -> str:
    L = ["# C9-2: 2x2 TVD on the 42 cohort countries", "",
         f"{LABEL}. Produced by `paper_b/c9_tvd.py`; aggregates only (no per-country human values).", "",
         DEFINITION, "## Inputs", ""]
    L += [f"- {k}: `{v.get('path') or v.get('source')}` sha256 `{(v.get('sha256') or '-')[:12]}`" for k, v in inputs.items()]
    L += ["", f"Bootstrap: {res['draws']} draws; profile-block seed {res['seed_profile_block']}, country seed "
          f"{res['seed_country']}; percentile 95%. Persona cells are not profile-constant, so both resampling units are shown.",
          "", "## Cells", "",
          "| Cell | Status | Countries | Cells | Mean TVD (country-equal) | Mean TVD (pooled) | Trust-GPS rho, profile-block | Trust-GPS rho, country |",
          "|---|---|---|---|---|---|---|---|"]
    for name in CELLS:
        c = res["cells"][name]
        if c["status"] != "ok":
            L.append(f"| {name} | pending | - | - | - | - | - | - |")
            continue
        g = c.get("trust_gps")
        gp = "not computed" if g is None else (g.get("reason", "n/a") if g["status"] != "ok" else _ci(g["profile_block"]))
        gc = "-" if g is None or g["status"] != "ok" else _ci(g["country"])
        L.append(f"| {name} | ok | {c['n_countries']} | {c['n_cells']} | {_f(c['mean_tvd_country_equal'])} | "
                 f"{_f(c['mean_tvd_pooled'])} | {gp} | {gc} |")
    L += ["", "Skipped cells (no human distribution): " + ", ".join(
        sorted({s for c in res["cells"].values() if c["status"] == "ok" for s in c["skipped_cells"]})) + ".", "",
        "## Mean TVD by GPS dimension (country-equal within dimension)", "",
        "| Cell | " + " | ".join(DIMS) + " |", "|---|" + "---|" * len(DIMS)]
    for name in CELLS:
        c = res["cells"][name]
        L.append(f"| {name} | " + (" | ".join(_f(c["per_dimension"].get(d)) for d in DIMS) if c["status"] == "ok"
                                    else " | ".join("-" for _ in DIMS)) + " |")
    L += ["", "## Paired differences (country means of per-item TVD differences; negative = first cell closer to humans)", "",
          "| Contrast | Profile-block 95% | Country 95% | n |", "|---|---|---|---|"]
    for k, c in res["contrasts"].items():
        L.append(f"| {k} | {_ci(c['profile_block'])} | {_ci(c['country'])} | {c['n_countries']} |")
    if "adapter_persona" in res["cells"] and res["cells"]["adapter_persona"]["status"] != "ok":
        L += ["", "The adapter+persona cell is PENDING (run `adapter-persona-strict-v1-20261019` is not available). "
              "Re-running this script fills it and adds the adapter_persona_* and interaction contrasts, with no code change."]
    L += ["", "Base trust-GPS is undefined: the base model has no country conditioning, so its trust composite is the same "
          "for every country.", ""]
    return "\n".join(L)


def render_csv(res: dict) -> pd.DataFrame:
    rows = []
    for name, c in res["cells"].items():
        if c["status"] != "ok":
            rows.append({"row_type": "cell", "name": name, "scope": "all", "metric": "mean_tvd_country_equal",
                         "status": "pending"})
            continue
        rows.append({"row_type": "cell", "name": name, "scope": "all", "metric": "mean_tvd_country_equal",
                     "value": c["mean_tvd_country_equal"], "n": c["n_countries"], "status": "ok"})
        rows.append({"row_type": "cell", "name": name, "scope": "all", "metric": "mean_tvd_pooled",
                     "value": c["mean_tvd_pooled"], "n": c["n_cells"], "status": "ok"})
        for d, v in c["per_dimension"].items():
            rows.append({"row_type": "cell", "name": name, "scope": d, "metric": "mean_tvd_country_equal",
                         "value": v, "status": "ok"})
        g = c.get("trust_gps")
        if g and g["status"] == "ok":
            for unit in ("profile_block", "country"):
                r = g[unit]
                rows.append({"row_type": "cell", "name": name, "scope": "trust", "metric": "gps_spearman",
                             "value": r["point"], "ci_lo": r["ci_lo"], "ci_hi": r["ci_hi"], "unit": unit,
                             "n": r["n"], "status": "ok"})
    for name, c in res["contrasts"].items():
        for unit in ("profile_block", "country"):
            r = c[unit]
            rows.append({"row_type": "contrast", "name": name, "scope": "all", "metric": "mean_tvd_difference",
                         "value": r["point"], "ci_lo": r["ci_lo"], "ci_hi": r["ci_hi"], "unit": unit, "n": r["n"],
                         "status": "ok"})
    out = pd.DataFrame(rows)
    out["label"] = LABEL
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="C9-2 2x2 TVD on 42 countries")
    ap.add_argument("--draws", type=int, default=DRAWS)
    ap.add_argument("--no-fetch", action="store_true", help="do not query the Hub for the adapter+persona run")
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    a = ap.parse_args(argv)
    probs = load_cohort1_scores()
    ap_scores, ap_prov = load_adapter_persona(fetch=not a.no_fetch)
    cells = {"base": probs[probs.model == "base"], "adapter": probs[probs.model == "adapter"],
             "persona": load_persona(), "adapter_persona": ap_scores}
    gps = load_trust_gps()
    clusters = load_profiles(sorted(gps.index))
    res = summarize(cells, load_human(), clusters, gps, draws=a.draws)
    inputs = {"cohort1_model_probs": {"path": str(MODEL_PROBS.relative_to(REPO)), "sha256": AS.sha256_file(MODEL_PROBS)},
              "persona_run": {"path": f"{PERSONA_RUN} via {PERSONA_STRICT.name}", "sha256": AS.sha256_file(PERSONA_STRICT)},
              "adapter_persona_run": {"path": ADAPTER_PERSONA_RUN, **ap_prov},
              "human_distributions": {"path": str(HUMAN_DISTS.relative_to(REPO)) + " (local-only, not committed)",
                                      "sha256": AS.sha256_file(HUMAN_DISTS)},
              "gps_z": {"path": str(AS.DEFAULT_GPS_JSON.relative_to(REPO)), "sha256": AS.sha256_file(AS.DEFAULT_GPS_JSON)}}
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    res["inputs"] = inputs
    (out / "c9_tvd.json").write_text(json.dumps(_clean(res), indent=2, sort_keys=True) + "\n")
    render_csv(_clean(res)).to_csv(out / "c9_tvd.csv", index=False)
    (out / "c9_tvd.md").write_text(render_md(_clean(res), inputs))
    for name in CELLS:
        c = res["cells"][name]
        print(name, c["status"], _f(c.get("mean_tvd_country_equal")), _f(c.get("mean_tvd_pooled")))
    for k, c in res["contrasts"].items():
        print(k, _ci(c["profile_block"]), _ci(c["country"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
