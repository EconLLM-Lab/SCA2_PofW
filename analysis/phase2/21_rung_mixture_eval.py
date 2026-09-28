#!/usr/bin/env python3
"""21_rung_mixture_eval.py v1.2 — mixture arithmetic + Tests A/B (local, CPU).

Consumes rung_pmfs.csv (from VM) + gate reports. Implements frozen spec v1.2:
  w_q,k = softmax_k(kappa*delta*z_cd*k), kappa=1.0, delta=0.25,
  per-question w from that question's GPS dimension. NOTE: v1.0's additive
  form softmax(beta*z + delta*k) was mathematically independent of z (B8) and
  is superseded; see RUNG_MIXTURE_SPEC.md changelog v1.1 -> v1.2.
Test A: self-consistency inside the OPERATIONAL family (u ~ N(0, 2^2),
        20 draws + 16 country vectors; rho(observed pair-TVD, predicted
        question-averaged w-distance) >= 0.9 else STOP).
Test B: WVS battery vs base / country adapters / persona / uniform noise;
        distance gauge with 10k paired-bootstrap CIs (seed 20260822).

v1.1 changes (audit ledger in RUNG_MIXTURE_SPEC.md):
  B3 arms scored identically on option codes -> comparable surfaces.
  B5 persona filenames fixed + loud asserts (no silent arm drops).
  B7 base-model arm + uniform-noise floor added; Test A moved onto the
     operational manifold; 10k bootstrap CI for both gauges.
"""
from __future__ import annotations

import itertools
import json
import pathlib
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "analysis" / "phase2" / "outputs"
PMFS = OUT / "rung_mix" / "rung_pmfs.csv"
RUNGS = [-3, -2, -1, 1, 2, 3]
DIMS = ["patience", "risktaking", "posrecip", "negrecip", "altruism", "trust"]
KAPPA, DELTA = 1.0, 0.25  # spec v1.2: w_k ∝ exp(kappa * delta * z * k)
SEED = 20260822
N_BOOT = 10_000
C16 = ["ARG", "BRA", "CHN", "DEU", "EGY", "GBR", "GRC", "IDN",
       "IND", "JPN", "MEX", "NGA", "NLD", "RUS", "TUR", "USA"]
BASE8 = ["ARG", "CHN", "DEU", "GBR", "JPN", "MEX", "RUS", "USA"]
CO2 = ["BRA", "EGY", "GRC", "IDN", "IND", "NGA", "NLD", "TUR"]


def log_stage(m):
    print(f"\n=== {m} " + "=" * max(0, 66 - len(m)))


def weights_for(z: float) -> np.ndarray:
    """softmax over rungs of kappa*delta*z*k (k ordered [-3..+3]); spec v1.2.

    z=0 -> uniform; sign(z) tilts toward same-sign rungs; |z| sets concentration.
    (v1.0's additive form softmax(beta*z + delta*k) was z-invariant — B8.)
    """
    logits = np.array([KAPPA * DELTA * z * k for k in RUNGS])
    e = np.exp(logits - logits.max())
    return e / e.sum()


def tvd(p: pd.Series, h: pd.Series) -> float:
    idx = p.index.union(h.index)
    return 0.5 * float((p.reindex(idx, fill_value=0)
                        - h.reindex(idx, fill_value=0)).abs().sum())


def main() -> None:
    pmfs = pd.read_csv(PMFS)
    log_stage("Loading rung PMFs")
    got_rungs = sorted(pmfs.rung.unique())
    nq = pmfs.question_id.nunique()
    print(f"  rows {len(pmfs)}, questions {nq}, rungs {got_rungs}")
    assert got_rungs == RUNGS, f"missing rungs: {set(RUNGS) - set(got_rungs)}"
    assert nq == 35, f"expected 35 questions, got {nq}"
    wide = pmfs.pivot_table(index=["question_id", "option_code"],
                            columns="rung", values="prob")
    assert not wide.isna().any().any(), "PMF grid incomplete"
    qs_all = wide.index.get_level_values(0).unique()

    gps = pd.read_stata(REPO / "data/GPS/GPS_dataset_country_level/country_gps.dta",
                        convert_categoricals=False)[["isocode"] + DIMS].set_index("isocode")

    # scoring bundle -> question->dimension map (needed by BOTH tests)
    bundle = pd.read_parquet(REPO / "data/phase2/derived/rung_mix/wvs_scoring_bundle.parquet")
    qdim = (bundle.dropna(subset=["gps_dimension"])
                  .groupby("question_id")["gps_dimension"].agg(lambda s: s.mode().iat[0]))
    assert set(qdim.unique()) <= set(DIMS), f"unexpected dimensions: {set(qdim.unique())}"
    # Predeclared scope: the mixture mechanism needs a GPS dimension per question,
    # so demographic items without one (sex/age/education/income) are excluded from
    # ALL arms alike. 35 eval questions -> 30 GPS-mapped questions.
    EXCLUDED_DEMOGRAPHICS = ["Q260", "Q261", "Q262", "Q275", "Q288"]
    qs = sorted(set(qs_all) - set(EXCLUDED_DEMOGRAPHICS))
    assert set(EXCLUDED_DEMOGRAPHICS) <= set(qs_all), "unexpected question ids"
    print(f"  eval scope: {len(qs)} GPS-mapped questions "
          f"(excluded demographics: {EXCLUDED_DEMOGRAPHICS})")

    # operational mixer: per-question mixture PMF from a 6-dim score vector
    def unit_mix(score_vec) -> dict:
        cols = {}
        for q in qs:
            d = qdim[q]
            sub = wide[wide.index.get_level_values(0) == q].droplevel(0)
            w = weights_for(float(score_vec[DIMS.index(d)]))
            m = sum(w[i] * sub[k] for i, k in enumerate(RUNGS))
            cols[q] = m / m.sum()
        return cols

    # ---- Test A: self-consistency INSIDE the operational family -------------
    log_stage("TEST A: self-consistency (operational family, must hit rho >= 0.9)")
    rng = np.random.default_rng(SEED)
    synth_units = rng.normal(0.0, 2.0, size=(20, len(DIMS)))   # covers |z| <= 2 range
    units = [(f"synth{i}", synth_units[i]) for i in range(len(synth_units))]
    units += [(c, gps.loc[c][DIMS].to_numpy(dtype=float)) for c in C16]

    mixes = [(name, unit_mix(v)) for name, v in units]

    def pred_distance(va, vb) -> float:
        """Estimator-symmetric prediction: mean over the SAME eval questions of
        the per-question w-vector Euclidean distance (spec v1.1.1)."""
        return float(np.mean([
            np.linalg.norm(weights_for(float(va[DIMS.index(qdim[q])]))
                           - weights_for(float(vb[DIMS.index(qdim[q])])))
            for q in qs]))

    obs, pred, pair_names = [], [], []
    mix_lookup = dict(mixes)
    for (na, va), (nb, vb) in itertools.combinations(units, 2):
        d_obs = float(np.mean([tvd(mix_lookup[na][q], mix_lookup[nb][q])
                                for q in qs]))
        obs.append(d_obs)
        pred.append(pred_distance(va, vb))
        pair_names.append(f"{na}|{nb}")
    rho_a = spearmanr(obs, pred).statistic
    print(f"  pairs tested: {len(obs)} | rho(observed, predicted) = {rho_a:.4f}")
    verdict_a = "PASS" if rho_a >= 0.9 else "FAIL"
    print(f"  TEST A: {verdict_a}")
    rd = OUT / "rung_mix"
    rd.mkdir(parents=True, exist_ok=True)
    if verdict_a == "FAIL":
        print("  STOP per spec: WVS evaluation uninterpretable without self-consistency.")
        json.dump({"test_A_rho": float(rho_a), "verdict": "FAIL",
                   "n_pairs": len(obs)},
                  open(rd / "testA.json", "w"), indent=2)
        return

    # ---- Test B prep: humans + all comparison arms --------------------------
    log_stage("Loading humans + baselines (same files as Option 4)")
    RAW = REPO / "data/phase2/raw/wvs"
    parts = []
    for fam in ["usamex_canonical", "ksenias_base8", "co2_8"]:
        h = pd.read_csv(RAW / fam / "population_response_distributions.csv")
        h["bank"] = fam.replace("_canonical", "")
        parts.append(h)
    hum = pd.concat(parts, ignore_index=True).drop_duplicates(
        ["bank", "eval_country", "question_id", "option_code"])
    # Predeclared cell-level scope (spec v1.1): country x question cells without a
    # human distribution are dropped from EVERY arm alike.
    avail = set(zip(hum.bank, hum.eval_country, hum.question_id))

    def has_human(c: str, q: str) -> bool:
        bank = "ksenias_base8" if c in BASE8 else "co2_8"
        return (bank, c, q) in avail

    opt_rows = []
    fam_dirs = {"ksenias_base8": BASE8, "co2_8": CO2}
    n_arm = {"country_adapter": 0, "base": 0, "persona": 0}
    for fam_dir, clist in fam_dirs.items():
        for c in clist:
            fa = RAW / fam_dir / f"model_option_probabilities_{c}_adapter_on_{c}.csv"
            fb = RAW / fam_dir / f"model_option_probabilities_base_on_{c}.csv"
            assert fa.exists(), f"B5 guard: missing adapter file {fa.name}"
            assert fb.exists(), f"B7 guard: missing base file {fb.name}"
            da = pd.read_csv(fa, usecols=["question_id", "option_code", "model_prob"])
            da["arm"] = "country_adapter"; da["country"] = c
            db = pd.read_csv(fb, usecols=["question_id", "option_code", "model_prob"])
            db["arm"] = "base"; db["country"] = c
            opt_rows += [da, db]
            n_arm["country_adapter"] += 1; n_arm["base"] += 1
    persona_dir = RAW / "persona_adapter"
    for c in C16:
        fp_ = persona_dir / f"model_option_probabilities_{c}_adapter_persona.csv"
        assert fp_.exists(), f"B5 guard: missing persona file {fp_.name}"
        dp = pd.read_csv(fp_, usecols=["question_id", "option_code", "model_prob"])
        dp["arm"] = "persona"; dp["country"] = c
        opt_rows.append(dp)
        n_arm["persona"] += 1
    opts = pd.concat(opt_rows, ignore_index=True).drop_duplicates(
        ["arm", "country", "question_id", "option_code"])
    print(f"  arms loaded: {n_arm} (expect 8/8/16)")

    # ---- mixture arm TVDs ----------------------------------------------------
    mix_rows = []
    for c in C16:
        sv = gps.loc[c][DIMS].to_numpy(dtype=float)
        mp_by_dim = unit_mix(sv)  # one cache per country; keys are questions
        bank = "ksenias_base8" if c in BASE8 else "co2_8"
        hq = hum[(hum.bank == bank) & (hum.eval_country == c)]
        for q in qs:
            if not has_human(c, q):
                continue
            hh = hq[hq.question_id == q].set_index("option_code").population_prob
            assert len(hh) > 0, f"no human distribution for {c}/{q}"
            mix_rows.append({"country": c, "question_id": q,
                             "gps_dimension": qdim[q],
                             "tvd": tvd(mp_by_dim[q], hh)})
    mixdf = pd.DataFrame(mix_rows)

    # baseline arms + uniform-noise floor
    base_rows = []
    for (arm, c), g in opts.groupby(["arm", "country"]):
        bank = "ksenias_base8" if c in BASE8 else "co2_8"
        hq = hum[(hum.bank == bank) & (hum.eval_country == c)]
        for q, gg in g.groupby("question_id"):
            if not has_human(c, q):
                continue
            hh = hq[hq.question_id == q].set_index("option_code").population_prob
            assert len(hh) > 0, f"no human distribution for {c}/{q}"
            pp = gg.set_index("option_code").model_prob
            assert pp.notna().all(), f"NaN model_prob in {arm}/{c}/{q}"
            base_rows.append({"arm": arm, "country": c, "question_id": q,
                              "tvd": tvd(pp, hh)})
    for c in C16:
        bank = "ksenias_base8" if c in BASE8 else "co2_8"
        hq = hum[(hum.bank == bank) & (hum.eval_country == c)]
        for q in qs:
            if not has_human(c, q):
                continue
            hh = hq[hq.question_id == q].set_index("option_code").population_prob
            pu = pd.Series(1.0 / len(hh), index=hh.index)  # uniform on human support
            base_rows.append({"arm": "uniform_noise", "country": c,
                              "question_id": q, "tvd": tvd(pu, hh)})
    basedf = pd.DataFrame(base_rows)

    log_stage("TEST B1: pooled TVD by arm")
    summary = [("mixture(K=6)", mixdf.tvd.mean())]
    for arm, g in basedf.groupby("arm"):
        summary.append((arm, g.tvd.mean()))
    for name, v in sorted(summary, key=lambda x: x[1]):
        print(f"  {name:22s} {v:.3f}")

    # ---- TEST B2: distance gauges + 10k paired bootstrap --------------------
    log_stage("TEST B2: distance gauge (mixture vs adapter, bootstrap CIs)")

    def gauge_cells(model_by_c: dict) -> pd.DataFrame:
        cells = []
        for a, b in itertools.combinations(C16, 2):
            za, zb = gps.loc[a][DIMS].astype(float), gps.loc[b][DIMS].astype(float)
            tvds = []
            for q in qs:
                qa_cache = model_by_c[a]
                qb_cache = model_by_c[b]
                pa, pb = qa_cache[q], qb_cache[q]
                tvds.append(tvd(pa, pb))
            cells.append({"pair": f"{a}-{b}",
                          "abs_dz": float((za - zb).abs().mean()),
                          "policy_tvd": float(np.mean(tvds))})
        return pd.DataFrame(cells)

    mix_cache = {}
    for c in C16:
        mix_cache[c] = unit_mix(gps.loc[c][DIMS].to_numpy(dtype=float))
    cdf = gauge_cells(mix_cache)
    rho_mix = spearmanr(cdf.abs_dz, cdf.policy_tvd).statistic

    # adapter-arm gauge: pairwise policy distance between trained country adapters
    adpt = opts[opts.arm == "country_adapter"]
    adpt_cache = {(c, q): gg.set_index("option_code").model_prob
                  for (c, q), gg in adpt.groupby(["country", "question_id"])}
    acells = []
    for a, b in itertools.combinations(C16, 2):
        za, zb = gps.loc[a][DIMS].astype(float), gps.loc[b][DIMS].astype(float)
        common_qs = [q for q in qs if (a, q) in adpt_cache and (b, q) in adpt_cache]
        tvds = [tvd(adpt_cache[(a, q)], adpt_cache[(b, q)]) for q in common_qs]
        acells.append({"pair": f"{a}-{b}", "abs_dz": float((za - zb).abs().mean()),
                       "policy_tvd": float(np.mean(tvds))})
    adf = pd.DataFrame(acells)
    rho_adp = spearmanr(adf.abs_dz, adf.policy_tvd).statistic

    rngb = np.random.default_rng(SEED)
    boots_mix, boots_adp = [], []
    for _ in range(N_BOOT):
        cm = cdf.iloc[rngb.integers(0, len(cdf), len(cdf))]
        if cm.abs_dz.nunique() > 1:
            boots_mix.append(spearmanr(cm.abs_dz, cm.policy_tvd).statistic)
        ca = adf.iloc[rngb.integers(0, len(adf), len(adf))]
        if ca.abs_dz.nunique() > 1:
            boots_adp.append(spearmanr(ca.abs_dz, ca.policy_tvd).statistic)
    ci_mix = (float(np.percentile(boots_mix, 2.5)), float(np.percentile(boots_mix, 97.5)))
    ci_adp = (float(np.percentile(boots_adp, 2.5)), float(np.percentile(boots_adp, 97.5)))
    adapter_ci_excludes_mix = bool(ci_adp[0] > rho_mix or ci_adp[1] < rho_mix)
    print(f"  mixture gauge rho = {rho_mix:.4f}  CI95 {ci_mix[0]:.3f}..{ci_mix[1]:.3f}")
    print(f"  adapter gauge rho = {rho_adp:.4f}  CI95 {ci_adp[0]:.3f}..{ci_adp[1]:.3f}"
          f"  | adapter CI excludes mixture point: {adapter_ci_excludes_mix}")

    log_stage("Writing outputs")
    mixdf.to_csv(rd / "mixture_question_metrics.csv", index=False)
    cdf.to_csv(rd / "mixture_distance_cells.csv", index=False)
    adf.to_csv(rd / "adapter_distance_cells.csv", index=False)
    json.dump({"spec_version": "v1.2.1", "seed": SEED,
               "test_A_rho": float(rho_a), "verdict_A": verdict_a,
               "pooled_tvd": {n: float(v) for n, v in summary},
               "distance_gauge": {
                   "mixture_rho": float(rho_mix), "mixture_ci95": ci_mix,
                   "adapter_rho": float(rho_adp), "adapter_ci95": ci_adp,
                   "adapter_ci_excludes_mixture": adapter_ci_excludes_mix}},
              open(rd / "summary.json", "w"), indent=2)
    print(f"  wrote {rd}")


if __name__ == "__main__":
    sys.exit(main())
