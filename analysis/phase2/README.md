# Phase-2 Analysis Layer (adapter evaluation, unified)

All scripts run from the repo root with the project venv: `unset PYTHONPATH && .venv/bin/python analysis/phase2/<script>.py`

## Pipeline

| Script | Outputs | Purpose |
|---|---|---|
| `01_build_unified_eval.py` | `outputs/wvs_question_metrics_long.{parquet,csv}`, `gps_reward_recovery_long.*` | Long-format unified eval tables (model-agnostic; soft-DPO wave drops in as new rows) |
| `02_heatmaps_and_scale.py` | corr heatmaps, matched-vs-cross TVD, scale layer, modal collapse | Per-dimension alignment, CO2 8x8 specificity, binary-vs-MC scale effects |
| `03_sign_vector_profiles.py` | `gps_sign_vectors_16.csv` | GPS sign(z) profile classes: 16 adapters -> 13 (MEX==RUS, EGY==IDN, GRC==IND) |
| `04_direction_cardinal.py` | `fig_direction_ordinal.png`, `fig_magnitude_cardinal.png` | FIG A (direction: GPS pairs + WVS composite Spearman) / FIG B (no magnitude) |
| `05_trust_split.py` | trust class TVD, over-generalization, CHN/JPN spotlights | Trust target split (family/ingroup/outgroup/institutions) |
| `06_construct_bridge.py` | `construct_bridge_by_{dimension,item}.csv`, `fig_construct_bridge.png` | WVS-GPS alignment: human layer (42 ctry, Falk-style) vs adapter layer (16) |
| `07_cultural_distance.py` | `cd_*.csv`, `fig_cultural_distance_map.png`, `fig_cd_matched_rank.png` | CF_ST (Muthukrishna et al. 2020) cultural-distance replication |

Helpers: `_dump_items.py` (item roster), `_inspect_parquet.py` (WVS surface schema), `_check_trust.py` (reconciliation diagnostic).

## Headline results (2026-08-19)

- **Direction (ordinal):** recovered on GPS held-out pairs (0.89-0.98) and, at the
  composite level on WVS items, for trust (rho +0.79), patience (+0.42), risk (+0.57),
  posrecip (+0.55); NOT for negrecip (+0.06) or altruism (+0.24). Per-cell movement
  signs are compressed (modal collapse) — the composite Spearman is the right test.
- **Magnitude (cardinal):** NOT captured — paired |bias| improves on 48% of questions
  (mean 1.31 -> 1.35); adapter bias vs GPS z: r = 0.04, sign agreement 55%.
- **Specificity:** matched-vs-mean-cross TVD ~ 0 (50% of cells); CF_ST matched-country
  rank median 20.5 of 42 (chance 21.5); 11/16 adapters nearest to CAN (mid-scale).
- **Trust over-generalization:** adapter family-vs-outgroup contrast (-0.34) is ~4x
  compressed vs population (-1.26) in 100% of 16 countries; CHN/JPN replicate the
  meeting's qualitative findings item-by-item.
- **Human instrument layer (42 countries):** trust rho 0.38 (Falk 0.49), patience 0.33
  (beats Falk's Q13-only 0.09; Q13 alone 0.41), negrecip 0.43 (bonus), risk -0.08,
  altruism 0.03, posrecip 0.02. CONSTRUCT_MAP priors confirmed: trust + patience are
  the decent proxies; exploratory dims stay exploratory.

## Metric note (cultural distance)

CF_ST = fixation index on survey traits (Muthukrishna et al. 2020, Psych. Science
31(6):678-701): questions = loci, answers = alleles; pairwise distance = mean over
items of F_ST = sigma2_g/sigma2_T (continuous formulation; between/total variance of
the two response distributions). Pinned from the published PDF (LSE repository copy,
2026-08-19). Atari et al. (2023, "Which Humans?", PsyArXiv 10.31234/osf.io/5b26t)
use this WEIRD-distance framing (LLMs resemble WEIRD populations; r = -0.70 with
distance from WEIRD). Our replication: 42 WVS7 countries (survey-weighted option
distributions) + 16 adapters + base (option-likelihood distributions), all on the 30
mapped items. Divergence from the original: our item set is the CONSTRUCT_MAP 30-item
mapping (their item set differs); the metric itself is implemented per the source.
