# Paper B analysis module — implementation report (2026-10-11)

Worker: Paper B analysis subagent. Scope honored: ONLY new
`paper_b/analyze_surface.py` + `paper_b/test_analyze_surface.py` created; no
existing scorer/eval_lib siblings edited; no GPU, no uploads, no commits, no
manuscript edits; original data files only read, never written.

## Files created (repo)

- `paper_b/analyze_surface.py` — CPU-only analysis module (no torch/HF/network).
- `paper_b/test_analyze_surface.py` — 64 tests, strict vertical RED/GREEN
  (every production function was watched failing first; two RED rounds caught
  real bugs, listed below).

Full suite at handoff: **81 passed** (64 new + 17 pre-existing
`test_eval_lib.py`, untouched and green).

## What the module implements (all predeclared in PARENT_DECISIONS/analysis draft)

- **Recodes**: exactly the locked E[recode] map over STRICT_ITEMS (23 items;
  Q43/Q50 separate; Q57 binary; 5−x for the 1–4 block including Q69–71;
  11−x for Q177/Q179). `expected_recode` enforces the FULL option domain per
  item (missing option ⇒ loud ValueError), probability sum-to-one, and
  accepts int- or str-typed option_code (CSV dtype hazard).
- **Three-column table**: country-equal Spearman per dimension for
  adapter–GPS, adapter–human (profile-block bootstrap, 2000 draws,
  seed 20261011 as baseline — any seed/draws configurable) and human–GPS
  (country bootstrap, seed 20260905, Paper A convention). Degenerate draws
  counted explicitly, never swallowed; n reported next to every rho.
- **Profile-equal sensitivity**: mean each variable within profile, THEN
  rank the 26 profile means — labeled `estimand=profile-equal` in its own
  table, never mixed with the country-equal primary.
- **Base arm**: no base correlation rows are ever emitted (composites
  constant across countries ⇒ rho UNDEFINED). Predeclared object is the
  paired adapter-minus-base mean |E[recode] − human mean| per country on
  identical complete-case support → `base_differences.csv`.
- **Reliability**: within-profile SD/range per (model, dimension, profile),
  descriptive only; docstring states it must not be called pure fitting
  noise until full data/config equality is verified.
- **Missingness ledger**: per (country, item) adapter/human presence;
  complete-case membership per dimension printed (JOR absent on Q178 ⇒
  risktaking human n=41 verified on real data). Available-case is available
  via `complete=False` but is not the primary.
- **Manifest**: sha256 + path of ALL consumed inputs (model probs, human
  means, GPS z JSON), membership counts (42 countries, 23 items, 26
  profiles, 12 multi-member), seeds, draws baseline, output counts.
- **Figures**: optional; graceful skip if matplotlib absent.
- **Human-only reproduction**: `--reproduce-human-means` rebuilds the
  committed `human_item_means_42.csv` from local WVS parquets (locked
  recode/weighting).

## Verification on REAL data (human-only; no adapter outcomes exist yet)

- Reproduced **1088/1088** present (country,item) means of
  `human_item_means_42.csv` from `data/wvs_eval_full` parquets:
  max |diff| = 1.8e-15 (JOR Q178 correctly absent).
- Reproduced the committed `human_gps_map.csv` point estimates EXACTLY
  through my estimators: trust 42×9 complete ρ=+0.350782, Q43 −0.532615,
  Q50 +0.388056, risktaking complete (n=41) −0.058711 — and the committed
  2000-draw country-bootstrap CIs reproduce to 4 decimals with seed
  20260905, confirming the Paper A bootstrap convention.
- Real profile structure from `gps_z_vectors.json`: 42 countries → 26
  sign profiles, 12 multi-member groups (28 members) + 14 singletons.
- Trust profile-equal sensitivity on real data: ρ=+0.3361 over 26 profiles
  vs country-equal +0.3508 (different estimand, both reported).

## Dry runs (synthetic fixtures, scratch only — purged after)

- Positive known-signal fixture (42 countries, JOR/EGY gaps built in):
  pipeline end-to-end exit 0; known trust signal recovered (human-GPS
  ρ>0.9, adapter-GPS ρ>0.8); all tables + manifest written.
- Deliberately invalid variants FAIL LOUDLY with nothing written:
  (a) incomplete option grid → ValueError naming the item;
  (b) probabilities not summing to 1 → ValueError.
- Fixture outputs written only under pytest tmp / active-profile scratch;
  purged (`paperb_dryrun/`, `pb_dbg_*`, `pb_final/` removed). Repo
  `analysis/`, `data/` untouched.

## Bugs caught by RED tests (fixed in the same cycle)

1. **Silent cluster drop**: profile bootstrap silently excluded countries
   missing a cluster id → now loud ValueError naming units.
2. **Silent profile drop**: profile-equal estimator silently dropped
   unmapped countries → now loud ValueError.
3. **Manifest provenance**: manifest hashed the repo-default human path
   instead of the file actually consumed → `human_means_path`/`probs_path`
   now required and hashed.
4. **Base arm correlations**: a base arm present in the probs frame
   produced all-degenerate correlation rows (rho=NaN × 10 draws) instead of
   being excluded → base now enters ONLY the paired-difference table
   (test asserts `'base' not in three_column.model`).

## Ambiguities / notes for parent

- A1–A7 from the design draft are implemented as recommended there
  (complete-case primary, Q178 kept primary, Q69–71 secondary, profile
  clustering for adapter columns + country bootstrap predeclared for the
  human column per A6). No new ambiguity introduced.
- Module tolerates multi-model probs frames (per-model rows); the paired
  base difference supports several adapter models vs one base.
- `Q57_UNIFORM`/`Q43_UNIFORM` etc. in the test file are fixture helpers.
- 2000 draws at seed 20261011 is the baseline; `--draws/--seed` exist so
  the baseline is not a cap (test pins that alternate seeds run).
- TVD machinery (`total_variation_distance`, `per_item_tvd`,
  `paired_base_difference`) is tested and ready; `run_analysis` currently
  emits mean |recode error| paired differences; per-item TVD vs base can be
  wired into the same table without new estimand decisions if wanted.
- All actual cohort adapter results WAIT for the verified scorer; nothing
  here reads or invents adapter outcomes.
