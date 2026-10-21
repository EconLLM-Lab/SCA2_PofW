#!/usr/bin/env python3
"""Build viewer/public/sca2/sca2_data.json: the SCA2 story data the viewer reads.

One-way read of Paper B artifacts. Nothing in Paper B reads this file. DESCRIPTIVE / NOT PREREGISTERED.

Run from the MAIN repo root with its venv (it imports the locked recode path from paper_b/):

    cd ~/Desktop/Github_Repositories/SCA2_PofW
    env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
        .worktrees/adapter-brain-vizualization/workbench/scripts/build_sca2_data.py

What goes in (model outputs, aggregate C9 claims and GPS signs; no respondent rows):
- countries: the 42 cohort countries, each with six GPS signs as 0/1 bits (sign rule factorial.unit_of_z).
  The GPS z values themselves are read in memory and never written.
- routes: per country and surface, the frozen-recode composite (analyze_factorial.unit_composites)
  for cohort-1 country adapters, bank-2 profile adapters (mapped to countries by profile),
  the 64 sign prompts (mapped the same way) and the country-named persona prompt.
- crosstalk: the 6 bits x 7 surfaces main effects (mtmm_<route>_cells.csv), copied with source path and
  sha256, re-derived here from the 64-unit composites as a check, with NUMBERS_TABLE claim ids
  attached wherever a claim's value equals the cell.
- bit_pairs / featured: cohort country pairs whose profiles differ in exactly one bit, and the
  adapter and sign-prompt click-through links the story uses (their run .bin files go into the deploy bundle).
- c9: four country-equal TVD cell means, profile-block contrasts and label-recovery summaries selected
  from NUMBERS_TABLE by exact claim id, plus per-country model-only label recovery/accuracy dots.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

MAIN = Path(__file__).resolve().parents[4] if ".worktrees" in str(Path(__file__)) else Path.cwd()
WB = Path(__file__).resolve().parents[1]
INPUTS = Path.home() / "Hermes/Projects/SCA2/paper_b_inputs"
FACT = Path("planning/sprint_2026-10-11/paper-b-tier1/results/factorial")
NUMBERS = Path("planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv")
EXPORT = WB / "exports/phase1_nf4_t4"
PROMPT_EXPORT = WB / "exports/phase1_promptroute_nf4_t4"
OUT = WB / "viewer/public/sca2/sca2_data.json"
SURFACES = ["trust", "risktaking", "patience:Q43", "patience:Q50", "altruism", "posrecip", "negrecip"]
BASE_KEY = "llama31_8b_nf4_dequant_float64_cpu_45cc5d4b_46079e27"
# Story click-throughs: each bit on its own surface(s), plus the cross-talk example of step 3.
FEATURED = [("trust", "trust"), ("risktaking", "risktaking"), ("patience", "patience:Q43"),
            ("patience", "patience:Q50"), ("altruism", "altruism"), ("posrecip", "posrecip"),
            ("negrecip", "negrecip"), ("risktaking", "altruism")]
DEFAULT_UNITS = [("USA", "wvs_Q81")]   # the default A vs B view of the existing tabs


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(MAIN))
    except ValueError:
        # External model-only inputs are identified by logical path + immutable
        # digest, never by the owner's private home-directory topology.
        return "paper_b_inputs/" + p.name


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", type=Path, default=MAIN)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args(argv)
    main_repo = a.main.resolve()
    sys.path[:0] = [str(main_repo / "paper_b"), str(main_repo / "paper_b/heldout")]
    import analyze_factorial as AF  # noqa: E402
    import analyze_surface as AS  # noqa: E402
    import factorial as F  # noqa: E402
    import factorial_effects as FE  # noqa: E402
    from ceiling import surface_items  # noqa: E402

    sources = []

    def src(role: str, p: Path) -> Path:
        p = p if p.is_absolute() else main_repo / p
        sources.append({"role": role, "path": rel(p), "sha256": sha256(p)})
        return p

    def scores(path: Path) -> pd.DataFrame:
        df = pd.read_csv(path)
        df["option_code"] = df["option_code"].astype(str)
        if "eval_country" not in df:   # persona: one prompt per country, named in the model column
            df["eval_country"] = df["model"].str.removeprefix("persona_")
        return df

    c1 = scores(src("cohort-1 country adapters (model probabilities)", INPUTS / "cohort1_strict.csv"))
    b2 = scores(src("bank-2 profile adapters (model probabilities)", INPUTS / "adapter_strict_v1.csv"))
    sp = scores(src("sign prompts, 64 profiles (model probabilities)", INPUTS / "signprompt_strict_64.csv"))
    pe = scores(src("country-named persona prompt (model probabilities)", INPUTS / "persona_strict.csv"))
    gps = json.loads(src("GPS signs (only sign(z) is kept)", AS.DEFAULT_GPS_JSON).read_text())

    ccs = sorted(c1.eval_country.unique())
    unit = {cc: F.unit_of_z(gps[cc]) for cc in ccs}
    del gps   # continuous values never leave this function
    countries = [{"cc": cc, "unit": unit[cc], "bits": list(F.bits_of_unit(unit[cc]))} for cc in ccs]
    profiles: dict[str, list[str]] = {}
    for cc in ccs:
        profiles.setdefault(unit[cc], []).append(cc)

    def wide(df: pd.DataFrame) -> pd.DataFrame:
        comp = AF.unit_composites(df)
        return comp.pivot(index="unit", columns="surface", values="composite")[SURFACES]

    w = {"cohort1": wide(c1), "bank2": wide(b2), "signprompt": wide(sp), "persona": wide(pe)}
    routes = {}
    meta = {
        "cohort1": ("cohort-1", "one DPO LoRA per country (bank 1), trained on its sign profile", "country"),
        "bank2": ("bank-2", "one DPO LoRA per sign profile (64, bank 2); a country gets its profile's score", "profile"),
        "signprompt": ("sign prompt", "the base model prompted with the six signs (64); a country gets its profile's score", "profile"),
        "persona": ("persona", "the base model prompted with the country's name; no signs", "country"),
    }
    for k, df in w.items():
        name, desc, of = meta[k]
        rows = {cc: {s: float(df.loc[unit[cc] if of == "profile" else cc, s]) for s in SURFACES} for cc in ccs}
        # within-profile spread vs spread over all 42 countries (workbench-computed, descriptive)
        frame = pd.DataFrame(rows).T
        frame["unit"] = [unit[cc] for cc in frame.index]
        within = {}
        for s in SURFACES:
            g = frame.groupby("unit")[s]
            multi = g.std(ddof=0)[g.size() >= 2]
            within[s] = {"within_profile_sd_mean": float(multi.mean()), "sd_all": float(frame[s].std(ddof=0)),
                         "n_profiles_with_2plus": int(len(multi))}
        routes[k] = {"name": name, "desc": desc, "unit_of_score": of, "scores": rows, "within": within}

    # ------------------------------------------------ cross-talk: copy cells, re-derive, attach claims
    nt = pd.read_csv(src("NUMBERS_TABLE (claim ids)", NUMBERS), float_precision="round_trip")
    fact_claims = nt[nt.output_file.astype(str).str.contains("results/factorial/")]
    claims: dict[str, dict] = {}

    def claim_ids(v: float) -> list[str]:
        hit = fact_claims[(fact_claims.value.astype(float) - v).abs() < 1e-12]
        for _, r in hit.iterrows():
            claims[r.claim_id] = {"value": float(r.value), "statistic": r.statistic, "use": r.sentence_use,
                                  "output_file": r.output_file}
        return sorted(hit.claim_id)

    crosstalk = {}
    for route, units_frame in (("adapter", w["bank2"]), ("signprompt", w["signprompt"])):
        cells_p = src(f"factorial main effects, {route} (6 bits x 7 surfaces)", FACT / f"mtmm_{route}_cells.csv")
        cells = pd.read_csv(cells_p)
        long = units_frame.reset_index().melt(id_vars="unit", var_name="surface", value_name="composite")
        mine = FE.effect_matrix(long[long.unit.isin(F.all_units())])
        gap = 0.0
        out = []
        for _, r in cells.iterrows():
            gap = max(gap, abs(float(mine.loc[r.dimension, r.surface]) - float(r.beta)))
            out.append({"bit": r.dimension, "surface": r.surface, "beta": float(r.beta), "se": float(r.se),
                        "t": float(r.t), "t_lenth": float(r.t_lenth), "claims": claim_ids(float(r.beta)),
                        "own": r.dimension == r.surface.split(":")[0]})
        if gap > 1e-9:
            raise SystemExit(f"{route}: re-derived main effects differ from {cells_p} by {gap}")
        crosstalk[route] = {"cells": out, "reproduced_max_abs_gap": gap,
                            "source": rel(cells_p), "units": "composite units (frozen recode)"}
    for cid in ("FX_adapter64_own_effects_wrong_signed", "FX_signprompt64_own_effects_wrong_signed",
                "FX_adapter64_columnwise_hits", "FX_signprompt64_columnwise_hits"):
        r = nt[nt.claim_id == cid].iloc[0]
        claims[cid] = {"value": float(r.value), "statistic": r.statistic, "use": r.sentence_use,
                       "output_file": r.output_file}

    # ------------------------------------------------ C9: exact claim-id selection; no country-level TVD
    def c9_claim(cid: str) -> dict:
        hit = nt[nt.claim_id == cid]
        if len(hit) != 1:
            raise SystemExit(f"Expected one NUMBERS_TABLE row for {cid}; found {len(hit)}")
        r = hit.iloc[0]

        def optional_float(value):
            return None if pd.isna(value) or value == "" else float(value)

        return {"claim_id": cid, "value": float(r.value), "ci_low": optional_float(r.ci_low),
                "ci_high": optional_float(r.ci_high), "statistic": str(r.statistic)}

    tvd_cells = {name: c9_claim(f"C9_TVD_{name}_mean_tvd_country_equal")
                 for name in ("base", "adapter", "persona", "adapter_persona")}
    contrast_names = ("adapter_minus_base", "adapter_persona_minus_adapter",
                      "adapter_persona_minus_base", "adapter_persona_minus_persona",
                      "persona_minus_base", "interaction")
    contrasts = {name: c9_claim(f"C9_TVD_{name}_profile_block") for name in contrast_names}
    recovery_names = ("recovery", "accuracy", "base_accuracy", "mean_margin_shift")
    recovery_summary = {name: c9_claim(f"C9_label_recovery_{name}_profile_block")
                        for name in recovery_names}
    recovery_path = src("C9 label recovery by country (model-only)",
                        Path("planning/sprint_2026-10-11/paper-b-tier1/results/c9/c9_label_recovery.csv"))
    recovery_frame = pd.read_csv(recovery_path, float_precision="round_trip")
    recovery_frame = recovery_frame[recovery_frame.country.isin(ccs)]
    if len(recovery_frame) != len(ccs) or set(recovery_frame.country) != set(ccs):
        raise SystemExit("C9 label-recovery countries do not match the 42-country cohort")
    recovery_countries = [{"cc": str(r.country), "recovery": float(r.recovery),
                           "accuracy": float(r.accuracy)}
                          for _, r in recovery_frame.sort_values("country").iterrows()]
    c9 = {"label": "descriptive, not preregistered; cross-family audited", "tvd_cells": tvd_cells,
          "contrasts": contrasts,
          "label_recovery": {"summary": recovery_summary, "countries": recovery_countries}}

    # ------------------------------------------------ click-through pairs and featured links
    bit_pairs = {}
    for i, d in enumerate(F.DIMS):
        bit_pairs[d] = [[x, y] for x in ccs for y in ccs
                        if F.bits_of_unit(unit[x])[i] == 0 and F.flip(unit[x], d) == unit[y]]
    idx = json.loads((EXPORT / "index.json").read_text())
    prompt_idx = json.loads((PROMPT_EXPORT / "index.json").read_text())
    if prompt_idx.get("schema") != idx.get("schema"):
        raise SystemExit("Adapter and prompt-route capture schemas differ")
    marker = " + sign prompt "
    prompt_models = {m["label"].split(marker, 1)[1]: key for key, m in prompt_idx["models"].items()
                     if marker in str(m.get("label", ""))}
    prompt_pairs = {(p["a"], p["b"], p["item_id"]) for p in prompt_idx["pairs"]}
    dm = {(p["b"], p["item_id"]): p["d_margin"] for p in idx["pairs"] if p["a"] == BASE_KEY}
    jplus = {}
    for r in idx["runs"]:
        if r["model"].startswith(BASE_KEY):
            m = json.loads((EXPORT / r["file"]).read_text())["item"]
            jplus.setdefault(r["item_id"], set()).add((m["j_plus"], m["j_minus"]))
    if any(len(v) != 1 for v in jplus.values()):
        raise SystemExit("j+/j- differ across runs of one item; a country-vs-country margin is not comparable")
    sitems = surface_items(AS.STRICT_ITEMS)
    key = lambda cc: f"{BASE_KEY}_{cc.lower()}"   # noqa: E731
    featured = []
    for bit, surf in FEATURED:
        item = "wvs_" + sitems[surf][0]
        cand = [(x, y) for x, y in bit_pairs[bit] if (key(x), item) in dm and (key(y), item) in dm]
        x, y = max(cand, key=lambda p: (abs(dm[(key(p[1]), item)] - dm[(key(p[0]), item)]), p))
        prompt_x = prompt_models[unit[x].removeprefix("P_")]
        prompt_y = prompt_models[unit[y].removeprefix("P_")]
        if (BASE_KEY, prompt_x, item) not in prompt_pairs or (BASE_KEY, prompt_y, item) not in prompt_pairs:
            raise SystemExit(f"Missing W2 prompt-route capture for {x}/{y} on {item}")
        featured.append({"bit": bit, "surface": surf, "item": item, "x": x, "y": y,
                         "prompt_x": prompt_x, "prompt_y": prompt_y,
                         "n_candidates": len(bit_pairs[bit]), "n_with_exports": len(cand),
                         "rule": "largest |d_margin(y) - d_margin(x)| on the item among the candidate pairs"})

    main_sha = subprocess.run(["git", "-C", str(main_repo), "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    data = {
        "schema": "sca2-workbench/story-data@1",
        "label": "DESCRIPTIVE / NOT PREREGISTERED. Workbench display of Paper B artifacts (one-way read). "
                 "Model outputs, aggregate claim-locked C9 statistics and GPS signs; no respondent rows, "
                 "country-level TVD, human means or distributions.",
        "generated_by": "workbench/scripts/build_sca2_data.py",
        "main_repo_head": main_sha,
        "sources": sources,
        "dims": list(F.DIMS),
        "surfaces": SURFACES,
        "surface_items": {s: list(q) for s, q in sitems.items()},
        "countries": countries,
        "profiles": dict(sorted(profiles.items())),
        "routes": routes,
        "crosstalk": crosstalk,
        "claims": dict(sorted(claims.items())),
        "c9": c9,
        "bit_pairs": bit_pairs,
        "featured": featured,
        "export": {"src": "phase1_nf4_t4", "prompt_src": "phase1_promptroute_nf4_t4",
                   "base": BASE_KEY, "country_key": BASE_KEY + "_<cc lower>",
                   "default_units": [{"cc": cc, "item": it} for cc, it in DEFAULT_UNITS],
                   "j_plus": {k: sorted(v)[0][0] for k, v in jplus.items()},
                   "j_minus": {k: sorted(v)[0][1] for k, v in jplus.items()}},
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(data, indent=1, sort_keys=False) + "\n")
    print(f"wrote {a.out} ({a.out.stat().st_size} bytes); {len(countries)} countries -> {len(profiles)} profiles; "
          f"cross-talk gaps adapter {crosstalk['adapter']['reproduced_max_abs_gap']:.2e}, "
          f"signprompt {crosstalk['signprompt']['reproduced_max_abs_gap']:.2e}; {len(claims)} claims")
    for f in featured:
        print(f"featured {f['bit']:>10} -> {f['surface']:<13} {f['item']:<9} {f['x']} -> {f['y']} "
              f"(of {f['n_candidates']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
