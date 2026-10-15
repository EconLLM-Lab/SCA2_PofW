#!/usr/bin/env python3
"""Sign-profile prompt cell: does the same six signs work through the prompt route?

The 26 sign profiles are scored on the base model with no country name and no
adapter. This script broadcasts each profile's composite to its member
countries and contrasts three things per surface:

  sign-prompt vs GPS      country-equal, and profile-equal
  sign-prompt vs adapter  country-equal against the banked Paper B surface
  adapter vs GPS          the same column already banked, for reference

It reads the banked cohort scores and never rewrites them.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_surface as A  # noqa: E402
import analyze_phase as P  # noqa: E402

DEFAULT_BANKED = Path(
    "/Users/bonorinoa/Hermes/Projects/SCA2/sprint_2026-10-11/paper-b-20261011"
)


def load_sign_items(sign_dir: Path, domains: dict) -> pd.DataFrame:
    frames = []
    for csv in sorted(sign_dir.glob("*_option_probabilities.csv")):
        df = pd.read_csv(csv, dtype={"option_code": str, "question_id": str})
        if "profile_id" not in df.columns:
            raise SystemExit(f"{csv.name}: no profile_id column")
        df = df.rename(columns={"profile_id": "eval_country"})
        df["model"] = "sign_prompt"
        frames.append(df)
    if not frames:
        raise SystemExit(f"no sign CSVs in {sign_dir}")
    probs = pd.concat(frames, ignore_index=True)
    items = A.model_item_table(probs, domains=domains)
    # each profile is one unit here; broadcast happens after composites
    return items


def profile_table(items: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for surface, questions in P.SURFACES.items():
        series = P.surface_values(items, "sign_prompt", surface, questions)
        for pid, value in series.items():
            rows.append({"profile_id": pid, "surface": surface,
                         "composite": float(value)})
    return pd.DataFrame(rows)


def broadcast(profile_frame: pd.DataFrame, profiles: list[dict]) -> pd.DataFrame:
    members = {row["profile_id"]: row["members"] for row in profiles}
    rows = []
    for _, r in profile_frame.iterrows():
        for cc in members.get(r.profile_id, []):
            rows.append({"country": cc, "surface": r.surface,
                         "composite": float(r.composite)})
    return pd.DataFrame(rows)


def country_series(frame: pd.DataFrame, surface: str) -> pd.Series:
    sub = frame[frame.surface == surface]
    return sub.set_index("country")["composite"].sort_index()


def profile_series(frame: pd.DataFrame, surface: str) -> pd.Series:
    sub = frame[frame.surface == surface]
    return sub.set_index("profile_id")["composite"].sort_index()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sign-dir", required=True)
    ap.add_argument("--profiles", required=True)
    ap.add_argument("--spec", required=True, help="strict scoring spec, for option domains")
    ap.add_argument("--banked", default=str(DEFAULT_BANKED))
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    spec = pd.DataFrame(json.loads(Path(a.spec).read_text())["questions"])
    spec = spec.rename(columns={"question_id": "question_id"})
    domains: dict[str, list[str]] = {}
    for _, row in spec.iterrows():
        domains[str(row["question_id"])] = [str(c) for c in row["codes"]]
    A.register_option_domains(pd.DataFrame({
        "question_id": [q for q, codes in domains.items() for _ in codes],
        "option_code": [c for codes in domains.values() for c in codes],
    }))

    profiles = json.loads(Path(a.profiles).read_text())
    sign_items = load_sign_items(Path(a.sign_dir), domains)
    prof_frame = profile_table(sign_items)
    prof_frame.to_csv(out / "sign_profile_composites.csv", index=False)

    countries = sorted({cc for row in profiles for cc in row["members"]})
    broadcast_frame = broadcast(prof_frame, profiles)
    broadcast_frame.to_csv(out / "sign_country_composites.csv", index=False)

    banked = Path(a.banked)
    probs = pd.read_csv(banked / "model_probs.csv",
                        dtype={"option_code": str, "question_id": str})
    adapter_items = A.model_item_table(probs, domains=domains)
    gps = A.load_gps_z(A.DEFAULT_GPS_JSON)
    z = gps.pivot(index="country", columns="dimension", values="z")
    profile_ids = A.sign_profiles(gps, countries, P.PROF_DIMS).set_index("country")["profile_id"]

    dim_for = {"trust": "trust", "patience:Q43": "patience", "patience:Q50": "patience",
               "risktaking": "risktaking", "posrecip": "posrecip",
               "negrecip": "negrecip", "altruism": "altruism"}

    rows = []
    for surface in P.SURFACES:
        questions = P.SURFACES[surface]
        target = z[dim_for[surface]]
        adapter = P.surface_values(adapter_items, "adapter", surface, questions)
        sign_c = country_series(broadcast_frame, surface)
        sign_p = profile_series(prof_frame, surface)

        clusters = profile_ids.reindex(sign_c.index)
        r_gps = A.bootstrap_spearman(sign_c, target.reindex(sign_c.index),
                                     clusters=clusters, draws=A.BOOT_DRAWS, seed=A.BOOT_SEED)
        r_adapter = A.bootstrap_spearman(sign_c, adapter.reindex(sign_c.index),
                                         clusters=clusters, draws=A.BOOT_DRAWS, seed=A.BOOT_SEED)
        # Profile-equal: one unit per sign profile, no cluster step.
        # Profile ids in sign_profiles.json are written in sign_prompt.DIMS order,
        # while analyze_surface.sign_profiles uses PROF_DIMS order. The two orders
        # name the same partition with different strings, so match on MEMBERS,
        # never on the id string.
        members_by_pid = {row["profile_id"]: row["members"] for row in profiles}
        pv = sign_p.copy()
        gz, av = {}, {}
        for pid, members in members_by_pid.items():
            if pid not in pv.index:
                continue
            t = target.reindex(members).dropna()
            s = adapter.reindex(members).dropna()
            if len(t) and len(s):
                gz[pid] = float(t.mean())
                av[pid] = float(s.mean())
        gz = pd.Series(gz)
        av = pd.Series(av)
        common = pv.index.intersection(gz.index).intersection(av.index)
        rho_pe_gps = A.spearman_country_equal(pv.loc[common], gz.loc[common])[0]
        rho_pe_adapter = A.spearman_country_equal(pv.loc[common], av.loc[common])[0]
        # adapter vs GPS on 42, the banked reference column
        acl = profile_ids.reindex(adapter.index)
        r_adapter_gps = A.bootstrap_spearman(adapter, target.reindex(adapter.index),
                                             clusters=acl, draws=A.BOOT_DRAWS, seed=A.BOOT_SEED)
        rows.append({
            "surface": surface,
            "sign_gps_country": r_gps["point"], "sign_gps_lo": r_gps["ci_lo"],
            "sign_gps_hi": r_gps["ci_hi"], "n_countries": r_gps["n"],
            "sign_gps_profile_equal": rho_pe_gps,
            "sign_adapter_country": r_adapter["point"],
            "sign_adapter_lo": r_adapter["ci_lo"], "sign_adapter_hi": r_adapter["ci_hi"],
            "sign_adapter_profile_equal": rho_pe_adapter,
            "adapter_gps_country": r_adapter_gps["point"],
            "adapter_gps_lo": r_adapter_gps["ci_lo"],
            "adapter_gps_hi": r_adapter_gps["ci_hi"],
        })

    table = pd.DataFrame(rows)
    table.to_csv(out / "sign_vs_banked.csv", index=False)
    pd.set_option("display.width", 200)
    print(table.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print("\nwrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
