# G0 replication ledger — third-party rerun (2026-08-23)

**Question:** can a third party regenerate the paper's headline numbers by running the committed `analysis/phase2/` scripts on banked eval artifacts (no GPU, no adapters)?

**Answer:** the *scripts* reproduce themselves exactly. They do **not** reproduce the paper's trust-bridge headline. Two constructions are live in the repo. The public GitHub tree is not sufficient to rerun from scratch.

## What was run

Working tree `SCA2_PofW` at `main` = `origin/main` (`3300994…`).
Snapshot of `analysis/phase2/outputs` taken first → `/tmp/sca2_g0_snapshot/`.
Then, from repo root, `env -u PYTHONPATH .venv/bin/python analysis/phase2/<script>.py` for:

`01_build_unified_eval.py` → `13_unified_comparison.py` → `03_sign_vector_profiles.py` → `07_cultural_distance.py` → `09_temperature_scaling.py` → `16_non_llm_baseline.py` → `17_anchor_permutation_placebo.py` → `18_2x2_analysis.py`

All eight exited 0. Log: `/tmp/sca2_g0_rerun.log`.
pandas 3.0.5 / numpy 2.5.2 / scipy 1.18.0.

## Byte identity vs pre-run snapshot

`unified_{summary_pooled,construct_bridge,development,direction}.csv`, `cd_matched_rank.csv`, `2x2_{bridge,tvd}.csv`, `reward_accuracy_16.csv`, `gps_sign_vectors_16.csv` — **md5-identical** to the files that were already on disk. The analysis layer is deterministic given the local eval mirror.

## Paper vs regenerated (script 13 = current “unified” pipeline)

Construction in `13_unified_comparison.py`: **E[recode(V)]** — recode each option code, then take the probability-weighted mean. Docstring: “Never apply this to a mean: binary recodes are nonlinear.”

| Claim | Paper | This rerun | Match? |
|---|---|---|---|
| pooled TVD adapter / base / persona / noise | 0.469 / 0.443 / 0.375 / 0.338 | 0.4694 / 0.4434 / 0.3751 / 0.3378 | YES (3-dec) |
| adapter trust ρ | **0.70** | **0.7824** | **NO** |
| adapter posrecip ρ | **0.55** | **0.4794** | **NO** |
| other adapter/persona/human bridge cells | as Table 2 | within 0.01 | YES |
| trust edu-partial | **+0.56** | **+0.5010** | **NO** |
| patience edu-partial | +0.46 | +0.4602 | YES |
| CF_ST median own-rank / n nearest CAN | 20.5 / 11 | 20.5 / 11 | YES |
| sign profiles in the 16 | 13 | 13 | YES |
| placebo real trust / q95 / p | 0.703 / 0.438 / 0.003 | 0.7029 / 0.438 / 0.0030 | YES (script 17) |
| 2×2 adapter-uncond / adapter-persona / base-persona | 0.70 / 0.60 / 0.06 | 0.7029 / 0.5971 / 0.0647 | YES (script 18) |

## Why 0.70 and 0.78 both exist

They are not two recodes of the same script. They are two estimators.

- **Script 13 (current, and `table_construct.tex`):** `mean = Σ recode(option) · p(option)` = E[recode(V)]. Adapter trust **0.782**.
- **Scripts 17 and 18 (placebo, 2×2):** `mean = recode(Σ option · p(option))` = recode(E[V]). For binary Q57, E[V] is never exactly 1, so recode(E[V]) = 0 in every country and Q57 drops out of the ranks. Adapter trust **0.703**.

The paper Table 2 and footnote quote the *old* script-13 number (0.70) and call it “unified exact-equality.” That sentence describes recode(E[V]), which current script 13 no longer does. The Aug-20 README already recorded the move 0.70 → 0.78 after the E[recode] fix. The paper was not updated. Placebo/2×2 were written later and re-introduced recode(E[V]).

Human-side analog: survey composites recode each respondent then average. E[recode] is the matching model-side object. recode(E[V]) is the bug the README named.

**Recommended freeze (not applied):** one construction, E[recode(V)], script 13. Then patch 17/18 to the same line, re-run placebo and 2×2, and replace every `0.70` / `+0.56` / posrecip `0.55` in the tex. Do not mix 0.70 (placebo) with 0.78 (table).

## What a stranger with only GitHub can do

- **Can:** re-read the committed `analysis/phase2/outputs/*.csv` (81 output files are tracked). That is transcription, not replication.
- **Cannot:** rerun scripts 01/13/16/17/18 from the public tree. `data/phase2/raw/` is gitignored. Tracked `DPO_eval_WVS/` is the USA/MEX pilot only. The 16-country banks (`ksenias_base8`, `co2_8`, persona) live on Drive (`sca2drive:SCA2_phase2`). Adapters are on HF (`Bonorinoa/SCA2-phase2-adapters`), 7.6 GB, also gitignored.
- Paper availability statement claims “frozen evaluation artifacts … are available at” the GitHub URL. That is currently overstated.

Adapters are **not** required to recompute tables if the option-probability CSVs are present. They **are** required to regenerate those CSVs.

## Third-party recipe (once raw is published)

```
git clone https://github.com/EconLLM-Lab/SCA2_PofW
# obtain data/phase2/raw/wvs/{usamex_canonical,ksenias_base8,co2_8,persona_*}
# obtain data/wvs_eval_full/*.parquet and data/GPS/.../country_gps.dta
env -u PYTHONPATH .venv/bin/python analysis/phase2/01_build_unified_eval.py
env -u PYTHONPATH .venv/bin/python analysis/phase2/13_unified_comparison.py
# assert vs analysis/phase2/tables/table_*.tex
```

No GPU.
