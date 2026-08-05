#!/usr/bin/env python3
"""Build the adapter pilot score matrix (USA/MEX only — n=2 pilot, NOT main evidence).

For each adapter/base model and each evaluation country (matched setting), compute
predicted item scores from option probabilities:

    predicted_item_score = sum_k p_k * scored(option_value_k)

where scored() applies the SAME normalization + direction as prep/protocol.yaml.
Dimension score = mean over that dimension's facet scores (protocol facets).

Outputs data/validity/scores_adapter.csv:
  iso3 (USA, MEX)
  m_adapter_<dim>   — matched adapter predicted country score (adapter on own country)
  m_base_<dim>      — base model predicted country score
  m_wvs_<dim>_<facet> — WVS facet country means (reference, from scores_full.csv)
  gps_<dim>          — GPS criterion (reference)

LIMITATION (read before use): with two countries, correlation-based restrictions
are degenerate. Use only mean_order-style restrictions (group = is_usa) with a
pre-declared direction, e.g. the sign of the GPS USA - MEX difference. Everything
here is directional pilot evidence, not construct-validity proof.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml

REPO = Path(__file__).resolve().parents[2]
EVAL_DIR = REPO / "DPO_eval_WVS" / "eval_results_wvs_wave7"
PROTOCOL = yaml.safe_load((Path(__file__).resolve().parent / "protocol.yaml").read_text())
OUT = REPO / "data" / "validity"

SCALES = {
    "binary_1_2": {"min": 1, "max": 2},
    "likert_1_4": {"min": 1, "max": 4},
    "scale_1_3": {"min": 1, "max": 3},
    "scale_1_10": {"min": 1, "max": 10},
    "member_0_2": {"min": 0, "max": 2},
}

MODELS = ["USA_adapter", "MEX_adapter", "base"]
COUNTRIES = {"USA": "USA", "MEX": "MEX"}


def item_specs(protocol: dict) -> dict[str, dict]:
    specs: dict[str, dict] = {}
    for dim, ds in protocol["dimensions"].items():
        for facet_name, fs in ds["facets"].items():
            for item, ispec in fs["items"].items():
                specs[item] = {"dim": dim, "facet": facet_name, **ispec}
    return specs


def normalize(v: float, scale: str) -> float:
    lo, hi = SCALES[scale]["min"], SCALES[scale]["max"]
    return (float(v) - lo) / (hi - lo)


def predicted_item_score(rows: pd.DataFrame, spec: dict) -> float | None:
    """sum_k p_k * scored(option_value) using the protocol direction."""
    scale = spec["scale"]
    direction = float(spec["direction"])
    total = 0.0
    for _, r in rows.iterrows():
        p = float(r["model_prob"])
        v = float(r["option_value"])
        norm = normalize(v, scale)
        s = norm if direction > 0 else 1.0 - norm
        total += p * s
    return total


def load_probabilities(model: str, country: str) -> pd.DataFrame:
    path = EVAL_DIR / f"model_option_probabilities_{model}_on_{country}.csv"
    return pd.read_csv(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    specs = item_specs(PROTOCOL)
    dims = list(PROTOCOL["dimensions"])

    rows: list[dict] = []
    for country in COUNTRIES:
        row: dict = {"iso3": COUNTRIES[country]}
        for model in MODELS:
            probs = load_probabilities(model, country)
            facet_scores: dict[str, list[float]] = {d: [] for d in dims}
            for qid, grp in probs.groupby("question_id"):
                if qid not in specs:
                    continue
                s = predicted_item_score(grp, specs[qid])
                if s is not None:
                    facet_scores[specs[qid]["dim"]].append(s)
            for d in dims:
                if facet_scores[d]:
                    row[f"m_{model}_{d}"] = float(sum(facet_scores[d]) / len(facet_scores[d]))
                else:
                    row[f"m_{model}_{d}"] = None
        rows.append(row)

    out = pd.DataFrame(rows)

    # reference columns from the full country panel
    full = pd.read_csv(args.out / "scores_full.csv")
    for d in dims:
        out[f"gps_{d}"] = out["iso3"].map(full.set_index("iso3")[f"gps_{d}"])
        for f in PROTOCOL["dimensions"][d]["facets"]:
            out[f"m_wvs_{d}_{f}"] = out["iso3"].map(full.set_index("iso3")[f"m_{d}_{f}"])

    args.out.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out / "scores_adapter.csv", index=False)
    roles = {
        "unit_id": "iso3",
        "measures": [f"m_{m}_{d}" for m in MODELS for d in dims],
        "aux": [f"gps_{d}" for d in dims],
        "outcome": None,
    }
    (args.out / "roles_adapter.json").write_text(json.dumps(roles, indent=2) + "\n")

    # pilot networks: mean_order(group=is_usa, direction=sign(GPS USA - MEX))
    gps = full.set_index("iso3")
    for d in dims:
        diff = float(gps.loc["USA", f"gps_{d}"]) - float(gps.loc["MEX", f"gps_{d}"])
        direction = 1 if diff > 0 else -1
        net = {
            "name": f"pilot_adapter_gps_sign_{d}",
            "delta": 0.0,
            "restrictions": [
                {
                    "id": f"r_mean_order_adapter_{d}",
                    "type": "mean_order",
                    "theta": 0.0,
                    "params": {"group": "is_usa", "direction": direction, "min_count": 1},
                }
            ],
            "_note": (
                f"direction={direction} = sign(GPS {d}: USA - MEX = {diff:.4f}). "
                "PILOT ONLY (n=2 countries). Augusto owns direction/threshold."
            ),
        }
        net_path = args.out / "pilot_networks" / f"{d}.yaml"
        net_path.parent.mkdir(parents=True, exist_ok=True)
        net_path.write_text(yaml.safe_dump(net, sort_keys=False))

    print("wrote data/validity/scores_adapter.csv (n=2 pilot):")
    print(out[["iso3"] + [f"m_{m}_{d}" for m in MODELS for d in dims]].to_string(index=False))
    print("\nGPS USA-MEX sign per dim (pilot network directions):")
    for d in dims:
        diff = float(gps.loc["USA", f"gps_{d}"]) - float(gps.loc["MEX", f"gps_{d}"])
        print(f"  {d:12s} USA-MEX = {diff:+.4f}  direction={1 if diff > 0 else -1}")


if __name__ == "__main__":
    main()
