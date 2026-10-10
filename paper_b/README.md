# paper_b — Paper B cohort runner (frozen protocol 2026-10-09)

Script-driven, resumable replacement for the two Paper A notebooks. Builds the
42-country GPS∩WVS7 cohort of DPO adapters from the shared relabeled bank.

Protocol of record: `~/Hermes/Projects/SCA2/PAPER_B_PROTOCOL_DRAFT.md` (frozen).
Claim binding: `~/Hermes/Projects/SCA2/TWO_PAPER_CLAIM_LOCK.md`.

## Files

| file | role | needs |
|---|---|---|
| `config.py` | frozen constants (cohort, bank, split, model, hyperparams) | — |
| `lib.py` | pure logic mirroring the data-prep notebook | — |
| `verify_gates.py` | data gates (bank shared, labels, common split, twins) | — |
| `prepare_data.py` | writes `{cc}_train/eval/train_with_ref.jsonl` | ref cache |
| `compute_ref_cache.py` | the ONE GPU reference pass (1052 pairs) | GPU + HF_TOKEN |
| `train_country.py` | trains one adapter | GPU + HF_TOKEN |
| `run_cohort.py` | orchestrates waves, resume, manifest | GPU |

## Order of operations

```bash
# 0. gates (any machine, no GPU)
python paper_b/verify_gates.py

# 1. reference cache — ONE GPU session, once for the whole cohort
export HF_TOKEN=...
export SCA2_PB_DATA_ROOT=/content/drive/MyDrive/SCA2_paper_b
python paper_b/compute_ref_cache.py

# 2. pilot one country end-to-end
python paper_b/run_cohort.py --countries ARG

# 3. waves (2 sessions max on Colab Pro)
python paper_b/run_cohort.py --wave 1
python paper_b/run_cohort.py --wave 2
```

Everything after step 1 is resumable: re-running skips completed countries and
pairs, and each adapter + its `run_record.json` is written to Drive on completion.

## Frozen values (do not drift)

- cohort: the 42 GPS∩WVS7 countries in `config.COHORT`
- bank: `synthetic_generation/outputs/gps_sign_relabel_all/` (658 rows/country, `deterministic_sign`)
- split: `TRAIN_FRAC=0.80`, `SEED=42` → 526 / 132
- model: `meta-llama/Llama-3.1-8B-Instruct`, QLoRA r=16 α=32 dropout=0.05 [q,k,v,o]
- DPO: β=0.1, lr=1e-4, 1 epoch, max_length=768, batch 1 × accum 16
- decisions: twins kept and reported as reliability contrast; near-zero = primary full bank + robustness variant (|z|≥0.10)
