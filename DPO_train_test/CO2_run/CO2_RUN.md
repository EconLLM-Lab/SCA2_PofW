# CO2 Run — 8 New Country Adapters (DPO + QLoRA)

Branch: `feat/co2-adapters` · Created: 2026-08-18 · Source of originals: `origin/main` @ `eb226a5`

## Purpose

Train eight additional country-specific DPO adapters on `meta-llama/Llama-3.1-8B-Instruct`
(bank set 2, "CO2"), complementary to Ksennia's base run (CHN, JPN, GBR, US, MEX, ARG, DEU, RUS).
Together the 16-adapter bank spans East Asia ×2, Southeast Asia, South Asia, Anglo ×2,
Latin America ×3, Protestant Europe, Germanic Europe, Southern Europe, Eastern Europe,
Eurasia, Sub-Saharan Africa, and the Arab/MENA world.

## Country set (data-backed)

| CC  | Region                    | WVS7 n | Fieldwork | D_syn signal vs USA (of 658) | mean\|z\| |
|-----|---------------------------|--------|-----------|------------------------------|-----------|
| IND | South Asia                | 1,692  | 2023      | 548 flipped (83%)            | 0.230     |
| IDN | Southeast Asia            | 3,200  | 2018      | 219 flipped                  | 0.224     |
| NGA | Sub-Saharan Africa        | 1,237  | 2018      | 439 flipped                  | 0.223     |
| EGY | Arab / MENA               | 1,200  | 2018      | 219 flipped                  | 0.419     |
| TUR | Eurasia (Muslim bridge)   | 2,415  | 2018      | 329 flipped (50/50)          | 0.240     |
| NLD | Protestant W. Europe      | 2,145  | 2022      | 219 flipped                  | 0.366     |
| BRA | Latin America (major case)| 1,762  | 2018      | 439 flipped                  | 0.255     |
| GRC | Orthodox S. Europe        | 1,200  | 2017      | 548 flipped (83%)            | 0.253     |

Selection gates: no overlap with base-run 8; production `D_syn_<CC>.jsonl` present
(658 rows, prompts identical to USA, chosen≠rejected everywhere); WVS wave-7 eval parquet
present (all 8 have 30/30 mapped items, 100% non-null per `_manifest.json`);
preference signal real (CAN/AUS excluded — their pairs are byte-identical to USA).

## Constraints (hard)

- **Ksennia's notebooks are never modified.** CO2 copies live in `DPO_train_test/CO2_run/`
  with provenance banners; original file hashes recorded at fork time:
  - prep `89101e4781bc` · train `18aa2f70a1a2` · eval `b7b8147ef4a7` (sha256 prefix).
- All work on this branch; no commits to `main` from this branch.

## Drive layout (Colab)

```
MyDrive/DPO_CO2/
├── pre-processing/D_syn_<CC>.jsonl        # 8 files from synthetic_generation/outputs/gps_sign_relabel_all/
├── shared_reference_logps.jsonl           # COPIED from Base_run Drive folder (compatible: same model, prompts, formatting)
├── shared_reference_logps_manifest.json   # written by data prep
├── <CC>_train.jsonl / <CC>_eval.jsonl     # written by data prep (shared 526/132 split)
├── <CC>_train_with_ref.jsonl              # written by data prep
├── dpo_qlora_adapters/<CC>/               # adapter-only weights + tokenizer (train notebook)
└── eval_results/                          # reward recovery CSVs (eval notebook)
```

All country codes map to themselves (no US→USA special case in CO2).

## Run order

1. **`CO2_data_preparation_multi_country_cached_ref.ipynb`** (CPU OK if the shared ref
   cache is reused). Loads `D_syn_<CC>.jsonl` ×8, verifies shared prompts/response pairs,
   writes aligned train/eval splits + `*_train_with_ref.jsonl`. If `shared_reference_logps.jsonl`
   is present it defines the split (526 train / 132 eval) and no GPU pass runs.
2. **`CO2_train_multi_country.ipynb`** (GPU). Trains 8 adapters sequentially.
3. **`CO2_evaluation_cross_evaluation_selective_cached_ref.ipynb`** (GPU). Reward recovery,
   `EVALUATION_MODE="self"` (each adapter on its own 132 held-out pairs), plus generated
   answers. Base-reference log-probs cached in `eval_results/base_reference_logprobs.jsonl`.
4. **WVS OOS calibration (phase 2, pending)** — adapted copy of
   `DPO_eval_WVS/DPO_survey_distribution_evaluation.ipynb` parameterized for the 8 CO2
   countries, scoring on `data/wvs_eval_full/<CC>_WVS_wave7.parquet` (note: weight column
   there is `W_WEIGHT`, unlike `weight` in `data/merged/`), `PROMPT_COUNTRY_CONDITIONING=False`,
   reporting TVD/JSD/Brier/CE/Wasserstein/ECE vs weighted population distributions.

## Hyperparameter record (identical to Base_run — do not drift)

```
base model        meta-llama/Llama-3.1-8B-Instruct
quantization      4-bit NF4, double quant, fp16 compute (bitsandbytes)
LoRA              r=16, alpha=32, dropout=0.05, target q/k/v/o, bias=none
DPO               beta=0.1, max_length=768, truncation_mode=keep_end
optimizer         AdamW-ish via TRL DPOConfig, lr=1e-4, cosine, 1 epoch
batch             per_device=1, grad_accum=16  (effective 16; ~33 steps)
split             TRAIN_FRAC=0.80, SEED=42, 526 train / 132 eval prompts (shared)
prompt format     questionnaire_situation_v1 (no country tokens — anti-leakage)
```

## Pitfalls to respect (lab standing rules)

- No country name in any prompt (`PROMPT_COUNTRY_CONDITIONING=False`).
- Never retrain on WVS/AB; eval surfaces stay untouched.
- Production bank is 658 pairs — do not mix in the QC-599 subset.
- "Matched vs cross" on unconditioned prompts = fixed-distribution proximity, not
  country-conditioned inference. State claims accordingly (identical-probabilities boundary).
- Reference-cache keys include the full formatted prompt — any prompt-format change
  invalidates the cache.

## Status log

- 2026-08-18: branch created from `origin/main`; CO2 notebooks forked (banner + country
  lists + Drive root only); this doc written; no training started yet.
