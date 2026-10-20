#!/usr/bin/env python3
"""C9-4 experiment B, laptop side: held-out synthetic-label recovery on the 42 cohort-1 adapters.

Input: the VM run `label-recovery-cohort1-v1-20261019` (paper_b/colab/vm_c9_label_recovery.py), one file per
country, runs/<run>/logps/<CC>.jsonl, rows {i, ref_chosen, ref_rejected, adapter_chosen, adapter_rejected}: the
summed log-probabilities of the chosen and rejected completion of each of the 132 held-out training-scenario pairs,
under that country's adapter and under the base model (the reference).

Definitions (the preprint's, computed per country over its 132 pairs):
  adapter_margin = adapter_chosen - adapter_rejected        ref_margin = ref_chosen - ref_rejected
  recovery  = share of pairs with adapter_margin > ref_margin   (the adapter moved toward its own label)
  accuracy  = share of pairs with adapter_margin > 0            (the adapter prefers its own label outright)
  base_accuracy = share of pairs with ref_margin > 0            (what the base model already gets)
These are construction checks (did training install the synthetic labels on unseen scenarios), not evidence about
GPS country order. DESCRIPTIVE / NOT PREREGISTERED.

Intervals: the cohort mean is the country-equal mean of the 42 per-country values, with a profile-block bootstrap
(26 sign profiles redrawn with replacement, all member countries move together; c9_tvd.bootstrap_mean) and a
country bootstrap. Per country, a Wilson 95% interval over its 132 pairs: it describes pair sampling for that one
fixed adapter, and the 132 pairs are the same scenarios in every country, so country intervals are not independent.

  python paper_b/c9_label_recovery.py            # fetch from the Hub (token from the sca .env), write results/c9/
  python paper_b/c9_label_recovery.py --logps-dir DIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c9_tvd as T  # noqa: E402  (bootstrap_mean, load_profiles, token helper, cohort list)

RUN_ID = "label-recovery-cohort1-v1-20261019"
ARTIFACTS_REPO = "Bonorinoa/SCA2-paper-b-artifacts"
N_PAIRS = 132
COLUMNS = ("i", "ref_chosen", "ref_rejected", "adapter_chosen", "adapter_rejected")
LABEL = "DESCRIPTIVE / NOT PREREGISTERED (construction check)"
OUT_DIR = T.OUT_DIR


def country_stats(rows: pd.DataFrame) -> dict:
    """The per-country rates over its pairs. Raises unless there are exactly N_PAIRS distinct, finite pairs."""
    missing = [c for c in COLUMNS if c not in rows.columns]
    if missing:
        raise ValueError(f"missing columns {missing}")
    if len(rows) != N_PAIRS or rows["i"].nunique() != N_PAIRS:
        raise ValueError(f"expected {N_PAIRS} distinct pairs, got {len(rows)} rows / {rows['i'].nunique()} ids")
    vals = rows[list(COLUMNS[1:])].to_numpy(float)
    if not math.isfinite(vals.sum()):
        raise ValueError("non-finite log-probability")
    am = rows["adapter_chosen"] - rows["adapter_rejected"]
    rm = rows["ref_chosen"] - rows["ref_rejected"]
    return {"n_pairs": int(len(rows)),
            "recovery": float((am > rm).mean()),
            "accuracy": float((am > 0).mean()),
            "base_accuracy": float((rm > 0).mean()),
            "mean_margin_shift": float((am - rm).mean())}


def wilson(p: float, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return mid - half, mid + half


def summarize(per_country: dict[str, pd.DataFrame], clusters: pd.Series, *, countries=None,
              draws: int = T.DRAWS) -> dict:
    countries = sorted(countries or T.COUNTRIES)
    got = sorted(per_country)
    if got != countries:
        raise ValueError(f"countries differ from the cohort: missing {sorted(set(countries) - set(got))}, "
                         f"extra {sorted(set(got) - set(countries))}")
    table = pd.DataFrame({cc: country_stats(per_country[cc]) for cc in countries}).T
    table.index.name = "country"
    res = {"label": LABEL, "run_id": RUN_ID, "n_countries": len(countries), "n_pairs_per_country": N_PAIRS,
           "draws": int(draws), "seed_profile_block": T.AS.BOOT_SEED, "seed_country": T.AS.COUNTRY_BOOT_SEED,
           "n_profiles": int(clusters.reindex(countries).nunique()), "cohort": {}, "countries": {}}
    for m in ("recovery", "accuracy", "base_accuracy", "mean_margin_shift"):
        v = table[m].astype(float)
        res["cohort"][m] = {"profile_block": T.bootstrap_mean(v, clusters, draws=draws, seed=T.AS.BOOT_SEED),
                            "country": T.bootstrap_mean(v, None, draws=draws, seed=T.AS.COUNTRY_BOOT_SEED)}
    for cc in countries:
        r = table.loc[cc]
        res["countries"][cc] = {
            "profile_id": str(clusters[cc]),
            **{m: float(r[m]) for m in ("recovery", "accuracy", "base_accuracy", "mean_margin_shift")},
            "recovery_wilson95": list(wilson(float(r["recovery"]), N_PAIRS)),
            "accuracy_wilson95": list(wilson(float(r["accuracy"]), N_PAIRS))}
    return res


def render_csv(res: dict) -> pd.DataFrame:
    rows = []
    for cc, r in res["countries"].items():
        rows.append({"country": cc, "profile_id": r["profile_id"], "recovery": r["recovery"],
                     "recovery_lo": r["recovery_wilson95"][0], "recovery_hi": r["recovery_wilson95"][1],
                     "accuracy": r["accuracy"], "accuracy_lo": r["accuracy_wilson95"][0],
                     "accuracy_hi": r["accuracy_wilson95"][1], "base_accuracy": r["base_accuracy"],
                     "mean_margin_shift": r["mean_margin_shift"], "interval": "wilson95 over 132 shared pairs"})
    for m, d in res["cohort"].items():
        for unit, b in d.items():
            rows.append({"country": f"COHORT_MEAN[{m}]", "profile_id": "", m: b["point"], f"{m}_lo": b["ci_lo"],
                         f"{m}_hi": b["ci_hi"], "interval": f"{unit} bootstrap, {b['draws']} draws, seed {b['seed']}"})
    return pd.DataFrame(rows)


def render_md(res: dict, inputs: dict) -> str:
    c = res["cohort"]

    def line(m, label):
        pb, ct = c[m]["profile_block"], c[m]["country"]
        return (f"| {label} | {pb['point']:.3f} | [{pb['ci_lo']:.3f}, {pb['ci_hi']:.3f}] | "
                f"[{ct['ci_lo']:.3f}, {ct['ci_hi']:.3f}] |")
    L = [f"# C9-4 B: held-out synthetic-label recovery, 42 cohort-1 adapters ({LABEL})", "",
         f"Run `{res['run_id']}`: {res['n_countries']} countries x {res['n_pairs_per_country']} held-out training-scenario "
         f"pairs (shared split TRAIN_FRAC=0.80, SEED=42). Cohort means are country-equal; {res['n_profiles']} sign "
         f"profiles in the profile-block bootstrap ({res['draws']} draws).", "",
         "| Quantity | Mean | Profile-block 95% | Country 95% |", "|---|---|---|---|",
         line("recovery", "Recovery (adapter margin > base margin)"),
         line("accuracy", "Accuracy (adapter margin > 0)"),
         line("base_accuracy", "Base accuracy (base margin > 0)"),
         line("mean_margin_shift", "Mean margin shift, nats"), "",
         "Reading: recovery and accuracy say whether training installed each country's synthetic labels on scenarios "
         "it never saw. They are construction checks; they say nothing about whether the labels order countries like "
         "GPS. The preprint reported 0.942 / 0.819 on its 16 development countries with different (preprint) adapters "
         "and banks; that is context, not a replication target, and is not re-computed here.", "",
         "Per-country values and Wilson intervals (pair sampling for one fixed adapter; pairs are shared across "
         "countries) are in the CSV/JSON.", "", "Inputs:", ""]
    L += [f"- {k}: {v}" for k, v in inputs.items()]
    return "\n".join(L) + "\n"


def load_logps(logps_dir: Path | None) -> tuple[dict[str, pd.DataFrame], dict]:
    if logps_dir is not None:
        files = {p.stem: p for p in sorted(Path(logps_dir).glob("*.jsonl"))}
        source = str(logps_dir)
    else:
        from huggingface_hub import HfApi, hf_hub_download
        tok = T._hf_token()
        if not tok:
            raise RuntimeError("no HF token: pass --logps-dir")
        prefix = f"runs/{RUN_ID}/logps/"
        names = sorted(f for f in HfApi(token=tok).list_repo_files(ARTIFACTS_REPO, repo_type="dataset")
                       if f.startswith(prefix) and f.endswith(".jsonl"))
        files = {Path(f).stem: Path(hf_hub_download(ARTIFACTS_REPO, f, repo_type="dataset", token=tok)) for f in names}
        source = f"hub:{ARTIFACTS_REPO}/{prefix}"
    data = {cc: pd.read_json(p, lines=True) for cc, p in files.items()}
    digest = hashlib.sha256(b"".join(files[cc].read_bytes() for cc in sorted(files))).hexdigest()
    return data, {"source": source, "files": len(files), "sha256_concat_sorted": digest}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logps-dir", type=Path)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--draws", type=int, default=T.DRAWS)
    a = ap.parse_args(argv)
    data, prov = load_logps(a.logps_dir)
    res = summarize(data, T.load_profiles(T.COUNTRIES), draws=a.draws)
    inputs = {"logps": f"{prov['source']} ({prov['files']} files, sha256 {prov['sha256_concat_sorted'][:16]})",
              "producer": "paper_b/colab/vm_c9_label_recovery.py (gates in runs/<run>/gates.json)"}
    res["inputs"] = inputs
    a.out_dir.mkdir(parents=True, exist_ok=True)
    (a.out_dir / "c9_label_recovery.json").write_text(json.dumps(res, indent=2) + "\n")
    render_csv(res).to_csv(a.out_dir / "c9_label_recovery.csv", index=False)
    (a.out_dir / "c9_label_recovery.md").write_text(render_md(res, inputs))
    c = res["cohort"]
    print(f"recovery {c['recovery']['profile_block']['point']:.4f} | accuracy {c['accuracy']['profile_block']['point']:.4f}"
          f" | base accuracy {c['base_accuracy']['profile_block']['point']:.4f} -> {a.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
