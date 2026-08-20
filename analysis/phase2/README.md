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
| `08_twin_geometry_reliability_trust.py` | `twin_*.csv`, `trust_class_bridge.csv`, `eval_08_summary.json` | Sign-twin geometry (GPS magnitudes + human CF_ST, permutation nulls); twin-adapter reliability (IDN/EGY, IND/GRC, MEX/RUS); trust-class construct bridge |
| `09_temperature_scaling.py` | `temp_scale_*.csv` | Inference temperature sweep (T=1..3) on existing option probabilities; shape vs location decomposition |
| `10_development_restrictions.py` | `development_*.csv` | Nomological test: composite vs log GDP pc (WDI 2015-2019), GPS/human/adapter layers, education partials |
| `11_twin_gdp.py` | `twin_gdp_pairs.csv` | Sign-twin proximity vs development confound (partial corr on CF_ST) |

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

## Headline results (2026-08-19, session 2: twins, temperature, development)

- **Sign-twins are a coarse-but-real GPS partition, and a development shadow.**
  76 countries -> 35 sign(z) profiles (22 multi-country classes). GPS-magnitude
  distance within class < between (ratio 0.59, perm p=0.000); human CF_ST within
  class < between (ratio 0.70, perm p=0.0005). BUT twin GDP gaps are also smaller
  (0.52 vs 0.92 log pts) and partial corr(CF_ST, twin | GDP gap) = -0.09: the
  WVS proximity of sign-twins is explained by shared development, not residual
  culture. Sign classes are NOT a cultural taxonomy.
- **Twin-adapter reliability.** IDN/EGY (same batch) CF_ST = 7.4e-6 (rank 1/120),
  IND/GRC = 0.0015 (rank 2); MEX/RUS (Ksennia's runs, different environment) =
  0.045 (rank 18). Identical labels reproduce to near-copy only within one batch;
  cross-environment twins diverge ~30x. MEX/RUS divergence is training noise, not
  country signal.
- **Temperature scaling fixes shape, not location.** T=1..3 on existing option
  probs: pooled matched TVD 0.469 -> 0.332; entropy error -0.74 -> +0.12; std error
  -0.65 -> -0.12; binary TVD 0.238 -> 0.144 (reaches base level 0.168 at T~2-3);
  ordered 0.494 -> 0.353. Top-option match UNCHANGED at every T (0.452 pooled) —
  temperature never moves a mode. CF_ST matched rank median 20.5 -> 24.5 (T=2): no
  location gain. T* per family (entropy match): binary 3.0, ordered 2.0. Shape loss
  is largely a softmax artifact; direction/location live in the weights.
- **Development restrictions hold on the confirmatory dimensions.** Adapter trust
  and patience composites correlate with log GDP pc in the same direction as GPS z
  (trust +0.085 vs GPS +0.322; patience +0.291 vs +0.584; partials controlling
  education: trust +0.484, patience +0.460). Exploratory dims fail against both
  layers (risk +0.347 vs human -0.345; negrecip -0.321 vs GPS +0.215) — the imprint
  pattern. GPS z (76 ctry): patience +0.584, trust +0.322; human WVS (42): patience
  +0.092, trust +0.158.

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
