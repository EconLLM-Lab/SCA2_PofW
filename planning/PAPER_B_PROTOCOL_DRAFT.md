# Paper B protocol — FROZEN 2026-10-09

**Frozen:** 2026-10-09 · Hermes (SCA profile) · decisions (A) and (B) approved by Augusto
**Status:** FROZEN. Companion to `TWO_PAPER_CLAIM_LOCK.md`
(which governs *claims*; this governs *the run*).

## Frozen decisions (approved 2026-10-09)

- **(A) Twin reporting.** All 42 stay in the cohort; the 12 twin groups are reported
  as a within-run reliability contrast (divergence under the frozen protocol is
  fitting noise). No country dropped to deduplicate.
- **(B) Near-zero exposure.** Primary = full 658-pair bank under the frozen sign
  rule (no filtering). Robustness = a near-zero-excluded variant (`|z| ≥ 0.10`)
  for affected countries, with per-country exposure reported alongside results.


---

## 1. Object

One DPO adapter per country for the full GPS∩WVS7 intersection, under a single
frozen protocol, for the Paper B "scoring instrument" extension. This replaces
the two-saved-jobs 16-country development cohort of Paper A; the 16 stay
untouched and archived.

## 2. Cohort (the 42)

`data/wvs_eval_full/*_WVS_wave7.parquet` enumerates exactly the 42-country
GPS∩WVS7 intersection:

ARG AUS BGD BOL BRA CAN CHL CHN COL CZE DEU EGY GBR GRC GTM IDN IND IRN IRQ JOR
JPN KAZ KEN KOR MAR MEX NGA NIC NLD PAK PER PHL ROU RUS SRB THA TUR UKR USA VEN
VNM ZWE

No discretionary subsetting. Random-sample fallback is not used.

## 3. Training data

Source: `synthetic_generation/outputs/gps_sign_relabel_all/D_syn_<CC>.jsonl`
(generated 2026-08-16, `run_id=gps_sign_relabel_all_20260816_004545Z`).

Verified on 2026-10-09 (probe scripts, Hermes scratch):

| Gate | Result |
|---|---|
| All 42 cohort countries present as relabel files | YES (files exist for 76 countries; 42/42 present) |
| Rows per country file | 658 everywhere |
| Shared bank — identical prompt/response_a/response_b content across countries | YES (hashed multiset identical) |
| Labels match the deterministic sign rule `chosen=A iff z_dim ≥ 0` | YES, zero mismatches across all 76 files |
| Row order identical across the cohort (⇒ common split) | YES |
| WVS outcomes present in training text | NO (bank is GPS-sign-labelled scenarios only) |
| Country names in training text | NO |

`labeling_rule = deterministic_sign`. No magnitude enters any label.

## 4. Frozen training configuration

Extracted from `DPO_train_test/Base_run/DPO_train_599_multi_country.ipynb` and
`DPO_data_preparation_599_multi_country_cached_ref (1).ipynb`:

- Base model: `meta-llama/Llama-3.1-8B-Instruct` (4-bit QLoRA)
- LoRA: `r=16, lora_alpha=32, lora_dropout=0.05, target_modules=[q_proj,k_proj,v_proj,o_proj], bias=none`
- DPO: `beta=0.1`, `learning_rate=1e-4`, `num_train_epochs=1`, `max_length=768`
- Batch: `per_device=1`, `gradient_accumulation=16`
- Split: `TRAIN_FRAC=0.80`, `SEED=42` → **526 train / 132 held-out** (identical across countries given row-order identity)
- Prompt: `questionnaire_situation_v1` wrapper (`build_user_prompt`)
- Precision: fp16, `TRANSFORMERS_NO_BF16=1`, `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`

## 5. Reference cache (compute once)

The shared bank has **1316 unique `(prompt, completion)` pairs** (658 prompts ×
2 responses); only the **526 train-split prompts** need reference log-probs, so
the cache holds **1052 pairs**. The base-model reference log-probability is
country-independent, so the cache is computed **once** and reused for all 42
countries' data-prep.

- Existing caches (`co2_8`: 264 rows, `ksenias_base8`: 476 rows) are partial and
  belong to the Paper A banks; they do **not** cover this cohort.
- New cache: `base_reference_logprobs.jsonl`, schema
  `(cache_key, base_model, max_prompt_tokens, max_completion_tokens, prompt, completion, logp)`,
  `max_prompt_tokens=max_completion_tokens=256`.
- Computed on one GPU session; stored on Drive; all country data-prep is then
  CPU-only.

## 6. Decisions to freeze (sign-off required)

**(A) Twin reporting rule.** The 42 carry **26 distinct sign profiles** in **12
twin groups** (identical sign vectors ⇒ identical labels ⇒ same fitting problem
up to training noise):

```
AUS CAN USA · BRA MAR · COL JOR · CZE JPN · EGY IDN · GRC IND ·
GTM MEX ROU RUS · IRQ TUR · KAZ VEN · KEN ZWE · NGA PAK PER · SRB UKR
```

Proposed: report twins as a **within-run reliability contrast** (their divergence
is fitting noise under a frozen protocol) and keep all 42 in the cohort. No
country is dropped to deduplicate. *Confirm.*

**(B) Near-zero exposure.** `near_zero_z` flags rows whose target coordinate has
`|z| < 0.10` (`NEAR_ZERO=0.10`), i.e. the sign label is least meaningful there.
Exposure is uneven and material:

```
GBR 438 · BOL 330 · COL/PER/RUS 329 · DEU/PAK 328 · ARG/AUS/CHL/CHN/KOR/MAR/TUR/VEN 219-220 · most others 109-110
```

Proposed: **primary = full 658-pair bank under the frozen sign rule** (no
filtering, matching the construction's definition); **robustness = a
near-zero-excluded variant** computed for the affected countries and reported as
a sensitivity, with per-country exposure printed alongside the results.
*Confirm.*

## 7. Compute plan (resumable, 2-session cap)

1. **Ref cache** — one GPU session, 1052 forward passes (526 train prompts × 2). *Cost driver #1.*
2. **Pilot** — one representative mixed-profile country end-to-end (data-prep →
   train → save → eval CSV on Drive). Verify artifacts + provenance.
3. **Waves** — remaining 41 countries in 2-session waves; per-country adapter +
   eval CSV saved to Drive on completion; the runner skips completed countries.
4. Every run logs T4-hours and appends provenance (config hash, bank hash,
   git SHA) to a run manifest.

## 8. Non-goals for this run

Sign-retrain placebo, second scenario bank, and the sign-profile prompt cell are
**separate Paper B gates** (claim lock §Paper B) and are not part of this first
cohort run. They follow once the 42-cohort surface exists.

---

*Drafted from a read-only reconnaissance of the repository on 2026-10-09. No
training job has been launched.*
