#!/usr/bin/env python3
"""Per-dimension A with a country-bootstrap interval for the held-out screen (journey checkpoint C5).

Card T1. `analyze_heldout.py` reports A per dimension as a point estimate. C5 asks for the interval:
"an imprint dimension whose new-battery interval includes 0 is not transport" (journey plan,
`.hermes/plans/2026-10-11_233701-paper-b-journey.md`, checkpoint C5).

Registered (PREREGISTRATION.md sections 1 and 4):
  A_d        mean of a_i over the items the route assigns to dimension d, where a_i is
             `screen_test.item_agreement`'s signed Spearman against GPS z on d
  interval   95% percentile interval from 2,000 country-bootstrap resamples of the 42 countries,
             the registered country bootstrap of section 4, recomputed per dimension
Not registered (descriptive only, labelled in the output):
  p_perm     one-sided item permutation p per dimension: draw as many pool items as the dimension
             has, give them that dimension and the selected items' signs in random order, 10,000 draws

Routes (step 3 of the card): adapter primary (56 items), adapter secondary rule (185), sign-prompt
primary, face-valid reader (imprint set, Amendment 2's 12 repaired items removed) and Jev majority
(imprint set, repaired items removed). `analyze_heldout.route`, `analyze_heldout.adapter_route` and
`analyze_heldout.REPAIRED` are re-used, so the comparator exclusion cannot drift from Amendment 2.

Human data are read only through `freeze.require_freeze` (via `run_screen.human_surface`, the
registered rule, MIN_N = 1) and `run_screen.load_gps`.

Outputs
  planning/sprint_2026-10-11/paper-b-tier1/results/heldout_per_dimension.json
  planning/sprint_2026-10-11/paper-b-tier1/results/HELDOUT_PER_DIMENSION_20261018.md

usage: per_dimension.py [--signprompt-selection path.csv] [--out path.json] [--note-out path.md]
                        [--boot 2000] [--draws 10000]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "paper_b"))
import analyze_heldout as AH  # noqa: E402
import freeze as FR  # noqa: E402
import run_screen as RS  # noqa: E402
import screen_test as ST  # noqa: E402

RESULTS = REPO / "planning/sprint_2026-10-11/paper-b-tier1/results"
SIGNPROMPT = RESULTS / "signprompt_selection_20261017.csv"
SEED = ST.PERM_SEED              # 20261015, the registered seed
BOOT_DRAWS = ST.BOOT_DRAWS       # 2,000, the registered country bootstrap
PERM_DRAWS = ST.PERM_DRAWS       # 10,000
CI = (2.5, 97.5)
# Exploratory, NOT registered (orchestrator 2026-10-18, for SMR's multiplicity request): a Bonferroni interval
# over the imprint dimensions, read off the same bootstrap draws as the registered 95% interval.
BONF_M = len(AH.IMPRINT)
CI_BONF = (100 * 0.05 / (2 * BONF_M), 100 * (1 - 0.05 / (2 * BONF_M)))

ROUTES = [
    ("adapter_primary", "adapter primary rule (selection_amended_20261016.csv, primary_selected)"),
    ("adapter_secondary", "adapter secondary rule (fixed threshold, secondary_selected)"),
    ("signprompt_primary", "sign-prompt primary (signprompt_selection_20261017.csv, primary_selected)"),
    ("face_valid", "face-valid reader (imprint set, Amendment 2 repaired items removed)"),
    ("jev_majority", "Jev majority (imprint set, Amendment 2 repaired items removed)"),
]
LABEL = dict(ROUTES)


# --------------------------------------------------------------------------- routes

def _imprint(rt: pd.DataFrame) -> pd.DataFrame:
    """Imprint dimensions only, and Amendment 2's repaired items out (as analyze_heldout does)."""
    keep = rt.top_dimension.isin(AH.IMPRINT) & ~rt.question_id.isin(AH.REPAIRED)
    return rt[keep].reset_index(drop=True)


def build_routes(sel: pd.DataFrame, sp_sel: pd.DataFrame, face: pd.DataFrame,
                 jev: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """The five routes of card step 3, each as question_id / top_dimension / sign (abstentions dropped)."""
    return {
        "adapter_primary": AH.adapter_route(sel, "primary_selected"),
        "adapter_secondary": AH.adapter_route(sel.assign(primary_selected=sel.secondary_selected),
                                              "primary_selected"),
        "signprompt_primary": AH.adapter_route(sp_sel, "primary_selected"),
        "face_valid": _imprint(AH.route(face, dim_col="dimension", sign_col="sign")),
        "jev_majority": _imprint(AH.route(jev, dim_col="dimension", sign_col="sign")),
    }


def dimension_order(dims) -> list[str]:
    """Imprint dimensions first in the preregistration's order, then anything else alphabetically."""
    return [d for d in AH.IMPRINT if d in dims] + sorted(d for d in dims if d not in AH.IMPRINT)


def dimension_groups(sel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """{dimension: the route's rows for it}, route order kept inside each group."""
    return {d: sel[sel.top_dimension == d].reset_index(drop=True)
            for d in dimension_order(set(sel.top_dimension))}


# --------------------------------------------------------------------------- statistics

def _aligned(human: pd.DataFrame, gps: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    countries = human.index.intersection(gps.index)
    return human.loc[countries], gps.loc[countries]


def _a_i(sel: pd.DataFrame, human: pd.DataFrame, gps: pd.DataFrame) -> np.ndarray:
    """Signed Spearman per item; rows of `human` and `gps` must be aligned (duplicates allowed)."""
    h = human[list(sel.question_id)].to_numpy(float)
    g = gps[list(sel.top_dimension)].to_numpy(float)
    return sel.sign.to_numpy(float) * ST._spearman_cols(h, g)


def point_interval(sel: pd.DataFrame, human: pd.DataFrame, gps: pd.DataFrame, *,
                   boot: int = BOOT_DRAWS, seed: int = SEED) -> dict:
    """A_d, its item count and a percentile 95% interval from `boot` country resamples.

    Every dimension is resampled with the same seed, so all dimensions see the same country draws
    (common random numbers) and the intervals are comparable.
    """
    human, gps = _aligned(human, gps)
    ia = ST.item_agreement(sel, human, gps)          # the registered a_i, and the abstention guard
    out: dict = {}
    for d, g in dimension_groups(sel).items():
        sub = ia[ia.top_dimension == d]
        rng = np.random.default_rng(seed)
        draws = np.empty(boot)
        for b in range(boot):
            r = rng.integers(0, len(human), len(human))
            hs = human.iloc[r].reset_index(drop=True)
            gs = gps.iloc[r].reset_index(drop=True)
            draws[b] = float(np.nanmean(_a_i(sub, hs, gs)))
        out[d] = {"A": float(sub.a_i.mean()), "n": int(len(sub)),
                  "ci95": [float(np.nanpercentile(draws, CI[0])), float(np.nanpercentile(draws, CI[1]))],
                  "boot": int(boot), "seed": int(seed),
                  "ci_bonf": [float(np.nanpercentile(draws, CI_BONF[0])),
                              float(np.nanpercentile(draws, CI_BONF[1]))],
                  "bonf_m": int(BONF_M)}
    return out


def perm_p(sel: pd.DataFrame, human: pd.DataFrame, gps: pd.DataFrame, pool: list[str], *,
           draws: int = PERM_DRAWS, seed: int = SEED) -> dict:
    """One-sided permutation p per dimension. NOT REGISTERED: descriptive only (card step 4).

    Each draw takes as many items from `pool` as the dimension has, gives them that dimension and
    the dimension's selected signs in random order, and averages their a_i. p = share of the null
    at or above the observed A_d, with no +1 correction (as in screen_test.screen).
    """
    human, gps = _aligned(human, gps)
    ia = ST.item_agreement(sel, human, gps)
    pool = [q for q in pool if q in human.columns]
    hm = human[pool].to_numpy(float)
    out: dict = {}
    for d, g in dimension_groups(sel).items():
        obs = float(ia[ia.top_dimension == d].a_i.mean())
        signs = g.sign.to_numpy(float)
        gcol = np.repeat(gps[d].to_numpy(float)[:, None], len(g), axis=1)
        rng = np.random.default_rng(seed)
        null = np.empty(draws)
        for b in range(draws):
            idx = rng.choice(len(pool), size=len(g), replace=False)
            perm = rng.permutation(len(g))
            null[b] = float(np.nanmean(signs[perm] * ST._spearman_cols(hm[:, idx], gcol)))
        out[d] = {"p": float((null >= obs).sum()) / draws, "obs_A": obs, "n": int(len(g)),
                  "null_mean": float(null.mean()), "null_q95": float(np.quantile(null, 0.95)),
                  "draws": int(draws), "seed": int(seed)}
    return out


def c5_reading(ci: list[float]) -> str:
    """Journey C5, read mechanically off the interval (its sign is in the A_d column)."""
    if ci[0] > 0 or ci[1] < 0:
        return "interval excludes 0: transport"
    return "interval includes 0: not transport"


def route_report(name: str, sel: pd.DataFrame, human: pd.DataFrame, gps: pd.DataFrame,
                 pool: list[str], *, boot: int = BOOT_DRAWS, draws: int = PERM_DRAWS,
                 seed: int = SEED) -> dict:
    pi = point_interval(sel, human, gps, boot=boot, seed=seed)
    pp = perm_p(sel, human, gps, pool, draws=draws, seed=seed)
    per_dim = {}
    for d in dimension_groups(sel):
        v = dict(pi[d])
        v["excludes_zero"] = bool(v["ci95"][0] > 0 or v["ci95"][1] < 0)
        v["reading"] = c5_reading(v["ci95"])
        v["p_perm_descriptive"] = pp[d]["p"]        # not registered (card step 4)
        v["null_mean"] = pp[d]["null_mean"]
        v["null_q95"] = pp[d]["null_q95"]
        per_dim[d] = v
    return {"route": name, "label": LABEL[name], "n_items": int(len(sel)), "pool_n": int(len(pool)),
            "per_dimension": per_dim}


def cross_check(res: dict, committed_path: Path) -> dict:
    """Compare the adapter primary A_d/n with the committed point estimates (analyze_heldout)."""
    committed = json.loads(committed_path.read_text())["s4_descriptives"]["per_dimension"]
    ours = res["routes"]["adapter_primary"]["per_dimension"]
    per = {d: {"A_ours": ours[d]["A"], "A_committed": float(v["A"]),
               "A_abs_diff": abs(ours[d]["A"] - float(v["A"])),
               "n_ours": ours[d]["n"], "n_committed": int(v["n"]), "n_match": ours[d]["n"] == int(v["n"])}
           for d, v in committed.items()}
    return {"source": str(committed_path.relative_to(REPO)),
            "note": "the same statistic A_d; the committed values are point estimates only",
            "per_dimension": per,
            "A_max_abs_diff": float(max(v["A_abs_diff"] for v in per.values())),
            "n_all_match": bool(all(v["n_match"] for v in per.values()))}


# --------------------------------------------------------------------------- outputs

def render_note(res: dict) -> str:
    L = ["# Per-dimension held-out agreement (checkpoint C5)", "",
         "Produced by `paper_b/heldout/per_dimension.py`; every number is read from",
         "`heldout_per_dimension.json`, written by the same run.", "",
         f"- Seed {res['seed']}, {res['boot']:,} country-bootstrap resamples, {res['perm_draws']:,} permutation",
         f"  draws; {res['n_countries']} countries (GPS ∩ WVS-7), pool {res['pool_n']} items.",
         "- A_d and its interval are registered (PREREGISTRATION.md sections 1 and 4): a_i is",
         "  `screen_test.item_agreement`'s signed Spearman against GPS z, A_d its mean over the items",
         "  the route assigns to dimension d, and the interval the 2.5/97.5 percentiles of the",
         "  registered country bootstrap.",
         "- The permutation p is **not registered**: it is descriptive only (card T1 step 4).",
         "- C5 rule, quoted from `.hermes/plans/2026-10-11_233701-paper-b-journey.md`: \"An imprint",
         "  dimension whose new-battery interval includes 0 is not transport.\" The reading below",
         "  applies that rule mechanically to the interval; the sign of A_d is in its own column.",
         ""]
    for name, r in res["routes"].items():
        nd = len(r["per_dimension"])
        L += [f"## {r['label']}", "",
              f"{r['n_items']} items over {nd} dimension{'s' if nd != 1 else ''}.", "",
              "| dimension | items | A_d | 95% country-bootstrap interval | p (perm, not registered) | C5 |",
              "|---|---|---|---|---|---|"]
        for d, v in r["per_dimension"].items():
            L.append(f"| {d} | {v['n']} | {v['A']:.3f} | "
                     f"[{v['ci95'][0]:.3f}, {v['ci95'][1]:.3f}] | {v['p_perm_descriptive']:.4f} | "
                     f"{v['reading']} |")
        L += ["", "C5 reading, one line per dimension:", ""]
        for d, v in r["per_dimension"].items():
            L.append(f"- {d}: {v['reading']} (A_d {v['A']:.3f}, n {v['n']}, "
                     f"interval [{v['ci95'][0]:.3f}, {v['ci95'][1]:.3f}])")
        L.append("")
    cc = res["cross_check"]
    L += ["## Exploratory: Bonferroni-adjusted intervals (not registered)", "",
          f"Added 2026-10-18 by the orchestrator for SMR's multiplicity request. Bonferroni over the "
          f"{BONF_M} imprint dimensions,",
          f"read off the same {res['boot']:,} draws: percentiles {CI_BONF[0]:.3f} and {CI_BONF[1]:.3f}. "
          "The registered 95% intervals above are unchanged.", "",
          "| route | dimension | items | A_d | registered 95% | Bonferroni |", "|---|---|---|---|---|---|"]
    for name in ("adapter_primary", "adapter_secondary"):
        for d, v in res["routes"][name]["per_dimension"].items():
            if d in AH.IMPRINT:
                L.append(f"| {name} | {d} | {v['n']} | {v['A']:.3f} | [{v['ci95'][0]:.3f}, {v['ci95'][1]:.3f}] | "
                         f"[{v['ci_bonf'][0]:.3f}, {v['ci_bonf'][1]:.3f}] |")
    L.append("")
    L += ["## Sanity check against the committed point estimates", "",
          f"`{cc['source']}` reports the same A_d without intervals. Largest absolute difference here:",
          f"{cc['A_max_abs_diff']:.2e}; item counts all match: {cc['n_all_match']}.", ""]
    for d, v in cc["per_dimension"].items():
        L.append(f"- {d}: A_d {v['A_ours']:.4f} (committed {v['A_committed']:.4f}), n {v['n_ours']}")
    L += ["", "Amendment 2: the repaired items leave both comparator routes in code; present in the",
          f"frozen comparator files and excluded here: {res['amendment2']['excluded_from_face']} (face-valid),",
          f"{res['amendment2']['excluded_from_jev']} (Jev).", ""]
    return "\n".join(L)


def build(*, signprompt: Path = SIGNPROMPT, boot: int = BOOT_DRAWS, draws: int = PERM_DRAWS,
          seed: int = SEED) -> dict:
    frozen = FR.require_freeze(HERE / "FREEZE.json")
    sel = pd.read_csv(frozen["selection_path"])
    pool = [str(q) for q in pd.read_csv(frozen["pool_path"])["Question"]]
    human, meta = RS.human_surface(pool)
    gps = RS.load_gps()
    routes = build_routes(sel=sel, sp_sel=pd.read_csv(signprompt),
                          face=pd.read_csv(HERE / "face_valid.csv"),
                          jev=pd.read_csv(HERE / "jev/majority_face_valid_jev.csv"))

    res: dict = {"generated_by": "paper_b/heldout/per_dimension.py",
                 "frozen_at": frozen["frozen_at"], "selection_sha256": frozen["selection_sha256"],
                 "pool_sha256": frozen["pool_sha256"], "human_cells_not_fielded": meta["cells_empty"],
                 "n_countries": int(len(human.index.intersection(gps.index))), "pool_n": len(pool),
                 "seed": int(seed), "boot": int(boot), "perm_draws": int(draws),
                 "registered": ["A_d", "ci95"],
                 "not_registered": ["p_perm_descriptive", "null_mean", "null_q95", "ci_bonf"],
                 "c5_rule": "an imprint dimension whose interval includes 0 is not transport",
                 "routes": {}}
    for name, rt in routes.items():
        res["routes"][name] = route_report(name, rt, human, gps, pool, boot=boot, draws=draws, seed=seed)
    face_all = AH.route(pd.read_csv(HERE / "face_valid.csv"), dim_col="dimension", sign_col="sign")
    jev_all = AH.route(pd.read_csv(HERE / "jev/majority_face_valid_jev.csv"),
                       dim_col="dimension", sign_col="sign")
    res["amendment2"] = {"excluded_from_face": sorted(set(face_all.question_id) & set(AH.REPAIRED)),
                         "excluded_from_jev": sorted(set(jev_all.question_id) & set(AH.REPAIRED))}
    res["cross_check"] = cross_check(res, RESULTS / "heldout_analysis.json")
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--signprompt-selection", default=str(SIGNPROMPT))
    ap.add_argument("--out", default=str(RESULTS / "heldout_per_dimension.json"))
    ap.add_argument("--note-out", default=str(RESULTS / "HELDOUT_PER_DIMENSION_20261018.md"))
    ap.add_argument("--boot", type=int, default=BOOT_DRAWS)
    ap.add_argument("--draws", type=int, default=PERM_DRAWS)
    a = ap.parse_args()

    res = build(signprompt=Path(a.signprompt_selection), boot=a.boot, draws=a.draws)
    Path(a.out).write_text(json.dumps(res, indent=2, default=float) + "\n")
    Path(a.note_out).write_text(render_note(res))
    print(json.dumps({n: {d: {"A": round(v["A"], 4), "n": v["n"], "ci95": [round(x, 4) for x in v["ci95"]],
                            "p": round(v["p_perm_descriptive"], 4), "c5": v["reading"]}
                           for d, v in r["per_dimension"].items()} for n, r in res["routes"].items()}, indent=1))
    print(f"cross-check A_max_abs_diff {res['cross_check']['A_max_abs_diff']:.2e}, "
          f"n_all_match {res['cross_check']['n_all_match']}")
    print("wrote", a.out)
    print("wrote", a.note_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
