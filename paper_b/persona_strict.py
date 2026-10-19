"""C8: the country-named persona arm against the GPS, beside the three banked routes (strict battery, 42 countries).

Design, locked before scoring: planning/sprint_2026-10-11/paper-b-tier1/C8_PERSONA_DESIGN.md.

Routes (country x surface composites, all through `analyze_factorial.unit_composites`):
  C1  cohort-1 country adapters (bank 1)            `paper_b_inputs/cohort1_strict.csv`
  B2  bank-2 profile adapters mapped to countries   `paper_b_inputs/adapter_strict_v1.csv`
  SP  sign-profile prompt, 64 cells mapped          `paper_b_inputs/signprompt_strict_64.csv`
  P   country-named persona prompt, base weights    `paper_b_inputs/persona_strict.csv` (fetched with --fetch)

E1 persona-GPS Spearman per surface (profile-block bootstrap); E2 the one test: trust, C1 minus P, paired
profile-block bootstrap; E3 descriptive paired differences for the other routes and surfaces; E4 the country
bootstrap of E1 and E2 (the preprint's convention); E5 C1 and P on the preprint's 16 development countries.
Replay checks: C1 and B2 reproduce the banked C3 rows exactly; the sign-prompt file reproduces the banked
factorial trust effect. Human data are never read here.

  python paper_b/persona_strict.py --fetch          # Hub -> paper_b_inputs/persona_strict.csv (needs HF_TOKEN)
  python paper_b/persona_strict.py                  # analysis -> results/persona/
"""
from __future__ import annotations

import argparse
import csv
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
import factorial_effects as FE  # noqa: E402
import factorial_report as FR  # noqa: E402
import score_plan as SPL  # noqa: E402

SURFACES = list(BT.SURFACES)
GPS_DIMS = ["trust", "risktaking", "patience", "altruism", "posrecip", "negrecip"]
SIGNPROMPT_STRICT_64 = BT.INPUT_DIR / "signprompt_strict_64.csv"
PERSONA_STRICT = BT.INPUT_DIR / "persona_strict.csv"
PARITY_SUFFIX = "_base_parity.json"             # fetch() writes the G3 record beside the persona CSV
OUT_DIR = BT.OUT_DIR / "persona"
JSON_NAME = "persona_strict.json"
MD_NAME = "PERSONA_STRICT.md"
BANKED_C3 = BT.OUT_DIR / BT.JSON_NAME
NUMBERS_TABLE = BT.REPO / "planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv"
DRAWS = AS.BOOT_DRAWS
SEED = AS.BOOT_SEED
COUNTRY_SEED = AS.COUNTRY_BOOT_SEED
DEV16 = ["CHN", "JPN", "GBR", "USA", "MEX", "ARG", "DEU", "RUS",
         "IND", "IDN", "NGA", "EGY", "TUR", "NLD", "BRA", "GRC"]
PRIMARY = ("C1", "trust")


def _dim(surface: str) -> str:
    return surface.split(":")[0]


def reading(lo: float, hi: float) -> str:
    if not (math.isfinite(lo) and math.isfinite(hi)):
        return "unresolved"
    if lo > 0:
        return "adapters closer"
    if hi < 0:
        return "persona closer"
    return "unresolved"


def _q(v: np.ndarray) -> tuple[float, float]:
    v = v[np.isfinite(v)]
    if v.size == 0:
        return float("nan"), float("nan")
    lo, hi = np.quantile(v, [0.025, 0.975])
    return float(lo), float(hi)


def paired_diff(a: pd.Series, b: pd.Series, y: pd.Series, clusters: pd.Series | None = None,
                draws: int = DRAWS, seed: int = SEED, min_n: int = 8) -> dict:
    """rho(a, y) - rho(b, y), both recomputed on every resample of the same rows.

    The resampling consumes the generator exactly as `analyze_surface.bootstrap_spearman` does, so each column's
    own interval inside the contrast equals that function's interval for the same seed and clusters. Rows must be
    the same countries in all three series (no silent intersection), and every row needs a cluster when blocks
    are used.
    """
    if not (a.index.equals(b.index) and a.index.equals(y.index)) and not (
            set(a.index) == set(b.index) == set(y.index)):
        raise ValueError("the two routes and the target must cover the same countries")
    d = pd.concat([a.rename("a"), b.rename("b"), y.rename("y")], axis=1)
    if clusters is not None:
        if not set(d.index) <= set(clusters.index):
            raise ValueError(f"cluster id missing for {sorted(set(d.index) - set(clusters.index))}")
        d = d.join(clusters.rename("cl"))
    if d[["a", "b", "y"]].isna().any().any():
        raise ValueError("missing composite or target value")
    n = len(d)
    if n < min_n:
        raise ValueError(f"only {n} rows")
    xa, xb, yy = (d[c].to_numpy(float) for c in ("a", "b", "y"))
    ra, rb = AS._spearman_arrays(xa, yy), AS._spearman_arrays(xb, yy)
    rng = np.random.default_rng(seed)
    if clusters is None:
        takes = list(rng.integers(0, n, size=(draws, n)))
    else:
        cl = d["cl"].to_numpy()
        uniq = pd.unique(cl)
        pos = {c: np.where(cl == c)[0] for c in uniq}
        pick = rng.integers(0, len(uniq), size=(draws, len(uniq)))
        takes = [np.concatenate([pos[uniq[j]] for j in pick[i]]) for i in range(draws)]
    da = np.array([AS._spearman_arrays(xa[t], yy[t]) for t in takes])
    db = np.array([AS._spearman_arrays(xb[t], yy[t]) for t in takes])
    diff = da - db
    lo, hi = _q(diff)
    alo, ahi = _q(da)
    blo, bhi = _q(db)
    return {"point": ra - rb, "ci_lo": lo, "ci_hi": hi, "rho_a": ra, "rho_a_lo": alo, "rho_a_hi": ahi,
            "rho_b": rb, "rho_b_lo": blo, "rho_b_hi": bhi, "n": int(n), "draws": int(draws), "seed": int(seed),
            "degenerate_draws": int(np.sum(~np.isfinite(diff)))}


def _rho(x: pd.Series, y: pd.Series, clusters, draws, seed) -> dict:
    return BT._r(AS.bootstrap_spearman(x, y, clusters=clusters, draws=draws, seed=seed))


def estimates(routes: dict, gps: pd.DataFrame, clusters: pd.Series, *, draws: int = DRAWS, seed: int = SEED,
              country_seed: int = COUNTRY_SEED) -> dict:
    """E1-E5 from country x surface tables. `routes` maps C1, B2, SP, P to frames indexed by country."""
    countries = list(routes["P"].index)
    for name, tab in routes.items():
        if set(tab.index) != set(countries):
            raise ValueError(f"route {name} covers other countries than the persona column")
    tabs = {k: v.loc[countries] for k, v in routes.items()}
    g = gps.loc[countries]
    cl = clusters.reindex(countries)
    P = tabs["P"]
    out = {"E1": {s: _rho(P[s], g[_dim(s)], cl, draws, seed) for s in SURFACES}}
    route, surface = PRIMARY
    e2 = paired_diff(tabs[route][surface], P[surface], g[_dim(surface)], cl, draws, seed)
    out["E2"] = {**e2, "route": route, "surface": surface, "resampling": "profile-block",
                 "reading": reading(e2["ci_lo"], e2["ci_hi"])}
    out["E3"] = {}
    for r in ("C1", "B2", "SP"):
        out["E3"][r] = {s: {**paired_diff(tabs[r][s], P[s], g[_dim(s)], cl, draws, seed),
                            "resampling": "profile-block"}
                        for s in SURFACES if (r, s) != PRIMARY}
    e4 = paired_diff(tabs[route][surface], P[surface], g[_dim(surface)], None, draws, country_seed)
    out["E4"] = {"persona": {s: _rho(P[s], g[_dim(s)], None, draws, country_seed) for s in SURFACES},
                 "E2_country_bootstrap": {**e4, "resampling": "country",
                                          "reading": reading(e4["ci_lo"], e4["ci_hi"])}}
    dev = [c for c in DEV16 if c in countries]
    if len(dev) == len(DEV16):
        out["E5"] = {"countries": dev, "resampling": "country",
                     "C1_trust": _rho(tabs["C1"].loc[dev, "trust"], g.loc[dev, "trust"], None, draws, country_seed),
                     "P_trust": _rho(P.loc[dev, "trust"], g.loc[dev, "trust"], None, draws, country_seed)}
    return out


# ------------------------------------------------------------------ inputs
def persona_frame(df: pd.DataFrame) -> pd.DataFrame:
    """A long persona score file -> the same frame with eval_country taken from `persona_<CC>`."""
    models = df["model"].astype(str)
    bad = sorted(set(models[~models.str.startswith("persona_")]))
    if bad:
        raise ValueError(f"not a persona model: {bad[:5]}")
    cc = models.str.removeprefix("persona_")
    want = set(SPL.PERSONA_COUNTRIES)
    missing, extra = sorted(want - set(cc)), sorted(set(cc) - want)
    if missing or extra:
        raise ValueError(f"persona countries missing {missing} / unknown {extra}")
    out = df.copy()
    out["eval_country"] = cc.to_numpy()
    return out


def _wide(comp: pd.DataFrame) -> pd.DataFrame:
    return comp.pivot(index="unit", columns="surface", values="composite")[SURFACES]


def run(cohort1_path=None, bank2_path=None, signprompt_path=None, persona_path=None, gps_json=None, *,
        draws: int = DRAWS, seed: int = SEED) -> dict:
    paths = {"cohort1_strict": Path(cohort1_path or BT.COHORT1_STRICT),
             "adapter_strict_v1": Path(bank2_path or BT.ADAPTER_STRICT_V1),
             "signprompt_strict_64": Path(signprompt_path or SIGNPROMPT_STRICT_64),
             "persona_strict": Path(persona_path or PERSONA_STRICT),
             "gps_z": Path(gps_json or AS.DEFAULT_GPS_JSON)}
    comp_c1 = BT.surface_composites(paths["cohort1_strict"])
    comp_b2 = BT.surface_composites(paths["adapter_strict_v1"])
    comp_sp = FR.signprompt_units(paths["signprompt_strict_64"])
    comp_p = AF.unit_composites(persona_frame(BT.load_scores(paths["persona_strict"])))
    countries = sorted(comp_c1.unit.unique())
    if countries != sorted(SPL.PERSONA_COUNTRIES):
        raise ValueError("cohort-1 file does not cover the 42 cohort countries")
    gps_raw = BT.load_gps_raw(paths["gps_z"])
    z = AS.load_gps_z(paths["gps_z"])
    gps = z.pivot(index="country", columns="dimension", values="z")
    profiles = AS.sign_profiles(z, countries, BT.PROF_DIMS)
    units = BT.country_units(gps_raw, countries)
    clusters = profiles.set_index("country")["profile_id"]
    routes = {"C1": _wide(comp_c1).loc[countries],
              "B2": pd.DataFrame({s: BT.unit_series(comp_b2, s, units) for s in SURFACES}).loc[countries],
              "SP": pd.DataFrame({s: BT.unit_series(comp_sp, s, units) for s in SURFACES}).loc[countries],
              "P": _wide(comp_p).loc[countries]}
    est = estimates(routes, gps, clusters, draws=draws, seed=seed)
    parity_path = paths["persona_strict"].with_name(paths["persona_strict"].stem + PARITY_SUFFIX)
    parity = json.loads(parity_path.read_text()) if parity_path.is_file() else None
    return {
        "base_parity": parity,
        "generated_by": "paper_b/persona_strict.py", "checkpoint": "C8",
        "design": "planning/sprint_2026-10-11/paper-b-tier1/C8_PERSONA_DESIGN.md",
        "run_id": SPL.CONDITIONS["persona_strict_v1"]["run_id"],
        "draws": int(draws), "seed": int(seed), "country_seed": int(COUNTRY_SEED), "ci": [0.025, 0.975],
        "n_countries": len(countries), "n_profiles_sign": int(clusters.nunique()),
        "inputs": {k: {"path": str(p), "sha256": AS.sha256_file(p)} for k, p in paths.items()},
        "routes_vs_gps": {"C1": BT.cohort1_adapter_gps(comp_c1, gps, profiles, draws=draws, seed=seed),
                          "B2": BT.bank2_adapter_gps(comp_b2, gps, units, draws=draws, seed=seed),
                          "SP": BT.bank2_adapter_gps(comp_sp, gps, units, draws=draws, seed=seed)},
        "signprompt_trust_own_beta": float(FE.fit(comp_sp).query("surface == 'trust' and dimension == 'trust'")
                                           ["beta"].iloc[0]),
        "composites": {k: v.round(12).to_dict(orient="index") for k, v in routes.items()},
        **est,
    }


def replay_checks(res: dict, banked_c3: Path = BANKED_C3, numbers_table: Path = NUMBERS_TABLE) -> dict:
    """Design section 4: the banked routes come out of this script exactly as they were banked."""
    banked = json.loads(Path(banked_c3).read_text())
    out = {}
    for route, key in (("C1", "cohort1_adapter_gps"), ("B2", "bank2_adapter_gps")):
        out[route] = all(res["routes_vs_gps"][route][s][f] == banked[key][s][f]
                         for s in SURFACES for f in ("point", "ci_lo", "ci_hi", "n"))
    out["inputs"] = (res["inputs"]["cohort1_strict"]["sha256"] == banked["inputs"]["cohort1_strict"]["sha256"]
                     and res["inputs"]["adapter_strict_v1"]["sha256"] == banked["inputs"]["adapter_strict_v1"]["sha256"]
                     and res["inputs"]["gps_z"]["sha256"] == banked["inputs"]["gps_z"]["sha256"])
    with open(numbers_table, newline="") as fh:
        rows = {r["claim_id"]: r for r in csv.DictReader(fh)}
    out["SP"] = res["signprompt_trust_own_beta"] == float(rows["FX_signprompt64_trust_own_beta"]["value"])
    out["all_pass"] = all(out.values())
    return out


# ------------------------------------------------------------------ fetch (Hub -> local input)
def fetch(out_path: Path = PERSONA_STRICT) -> dict:
    """42 persona CSVs + manifests + the G3 record, each checked against the pinned spec, into one long file."""
    from huggingface_hub import HfApi, hf_hub_download
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN is not set")
    c = SPL.CONDITIONS["persona_strict_v1"]
    pin = json.loads(SPL.PINS.read_text())["spec_sha256"]["persona_strict_v1"]
    run = c["run_id"]
    files = set(HfApi(token=token).list_repo_files(SPL.ARTIFACTS_REPO, repo_type="dataset"))

    def get(name):
        return Path(hf_hub_download(SPL.ARTIFACTS_REPO, name, repo_type="dataset", token=token))

    parity = json.loads(get(f"runs/{run}/base_parity.json").read_text())
    if not parity.get("pass"):
        raise SystemExit(f"G3 base parity did not pass: {parity}")
    frames = []
    for cc in SPL.PERSONA_COUNTRIES:
        model = f"persona_{cc}"
        csv_name, man_name = f"runs/{run}/synthetic/{model}_option_probabilities.csv", f"runs/{run}/manifests/{model}_manifest.json"
        if csv_name not in files or man_name not in files:
            raise SystemExit(f"{model}: CSV or manifest missing on the Hub")
        man = json.loads(get(man_name).read_text())
        if man.get("spec_sha256") != pin:
            raise SystemExit(f"{model}: manifest spec {man.get('spec_sha256')} is not the pin")
        p = get(csv_name)
        if man.get("csv_sha256") and AS.sha256_file(p) != man["csv_sha256"]:
            raise SystemExit(f"{model}: CSV hash differs from its manifest")
        frames.append(pd.read_csv(p, dtype={"option_code": str, "question_id": str}))
    df = pd.concat(frames, ignore_index=True)
    persona_frame(df)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    out_path.with_name(out_path.stem + PARITY_SUFFIX).write_text(json.dumps(parity, indent=2) + "\n")
    return {"path": str(out_path), "rows": int(len(df)), "sha256": AS.sha256_file(out_path), "base_parity": parity}


# ------------------------------------------------------------------ note
def _f(x) -> str:
    return "nan" if x is None or not math.isfinite(float(x)) else f"{float(x):.3f}"


def _ci(r: dict, p="point", lo="ci_lo", hi="ci_hi") -> str:
    return f"{_f(r[p])} [{_f(r[lo])}, {_f(r[hi])}]"


def render_note(res: dict, checks: dict) -> str:
    L = ["# C8 — country-named persona arm on the strict battery", "",
         f"Produced by `paper_b/persona_strict.py` from `{JSON_NAME}`; design `{res['design']}`.",
         f"Run `{res['run_id']}`. {res['n_countries']} countries, {res['n_profiles_sign']} sign profiles; "
         f"{res['draws']} draws, seed {res['seed']} (profile-block) / {res['country_seed']} (country), percentile 95%.",
         "", "## Inputs", ""]
    L += [f"- {k}: `{v['path']}` sha256 `{v['sha256'][:12]}…`" for k, v in res["inputs"].items()]
    L += ["", f"Replay checks (design section 4): {json.dumps(checks)}", "",
          "## E2 — the one test: trust, cohort-1 adapters minus persona (paired profile-block bootstrap)", "",
          f"D = {_ci(res['E2'])}; reading: **{res['E2']['reading']}** "
          f"(cohort-1 {_ci(res['E2'], 'rho_a', 'rho_a_lo', 'rho_a_hi')}, "
          f"persona {_ci(res['E2'], 'rho_b', 'rho_b_lo', 'rho_b_hi')}). Country bootstrap (E4): "
          f"{_ci(res['E4']['E2_country_bootstrap'])}, {res['E4']['E2_country_bootstrap']['reading']}.", "",
          "## E1 / E3 — every route against the GPS, and each route minus persona (descriptive)", "",
          "| Surface | C1 | B2 | SP | Persona (block) | Persona (country) | C1 − P | B2 − P | SP − P |",
          "|---|---|---|---|---|---|---|---|---|"]
    for s in SURFACES:
        d = {r: (res["E2"] if (r, s) == PRIMARY else res["E3"][r][s]) for r in ("C1", "B2", "SP")}
        L.append(f"| {s} | " + " | ".join(_ci(res["routes_vs_gps"][r][s]) for r in ("C1", "B2", "SP"))
                 + f" | {_ci(res['E1'][s])} | {_ci(res['E4']['persona'][s])} | "
                 + " | ".join(_ci(d[r]) for r in ("C1", "B2", "SP")) + " |")
    if "E5" in res:
        L += ["", "## E5 — the 16 development countries (country bootstrap, descriptive)", "",
              f"Cohort-1 trust {_ci(res['E5']['C1_trust'])}; persona trust {_ci(res['E5']['P_trust'])}. "
              "Paper B stack; not comparable to the preprint's own numbers, which come from another stack."]
    L += ["", "Route columns C1/B2/SP use the banked C3 resampling (B2 and SP cluster on the factorial unit); the "
          "differences use one profile-block resampling for both columns.", ""]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="C8 persona arm (strict battery)")
    ap.add_argument("--fetch", action="store_true", help="pull the persona run from the Hub into paper_b_inputs")
    ap.add_argument("--persona", default=str(PERSONA_STRICT))
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    ap.add_argument("--draws", type=int, default=DRAWS)
    a = ap.parse_args(argv)
    if a.fetch:
        print(json.dumps(fetch(Path(a.persona)), indent=2))
        return 0
    res = run(persona_path=a.persona, draws=a.draws)
    checks = replay_checks(res)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / JSON_NAME).write_text(json.dumps({**res, "replay_checks": checks}, indent=2, sort_keys=True) + "\n")
    (out / MD_NAME).write_text(render_note(res, checks))
    print(f"replay checks: {checks}")
    print(f"E2 trust C1 - persona: {_ci(res['E2'])} -> {res['E2']['reading']}")
    return 0 if checks["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
