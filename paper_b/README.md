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
| `eval_config.py` | WVS readout constants (separate from the frozen training protocol) | — |
| `eval_lib.py` | pure readout logic: spec parsing, prompt, populations, metrics | — |
| `score_cohort.py` | scores the cohort on the WVS readout; `--gate-cpu` / `--gate` | — / GPU |
| `compute_ledger.py` | publication clocks and the live append log | — |
| `compute/` | harvested snapshot: `ledger.jsonl`, `publication_estimate.json` | — |
| `test_eval_lib.py` | CPU tests pinned to the archived Paper A surface | — |

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

## 4. Scoring (the Paper B product)

```bash
# 4a. CPU gate — no GPU, no token. Validates the readout against the archived
#     Paper A surface (population distributions + every metric).
python paper_b/score_cohort.py --gate-cpu
python -m pytest paper_b/test_eval_lib.py -q

# 4b. GPU gate — reproduce the archived base-on-CHN option logprobs.
python paper_b/score_cohort.py --gate

# 4b'. Adapter availability across the hub and Drive (no GPU). Needs HF_TOKEN.
python paper_b/score_cohort.py --inventory

# 4c. Score the cohort (all 42 adapters + base; optionally the persona arm).
export SCA2_PB_DATA_ROOT=/content/drive/MyDrive/SCA2_paper_b
python paper_b/score_cohort.py --arms base,adapter
python paper_b/score_cohort.py --arms base,adapter,persona
```

Writes to `scores/`: `{model}_option_probabilities.csv` per model,
`population_response_distributions.csv`, `survey_option_evaluation_all_models.csv`,
`survey_question_metrics_all_models.csv`, and `score_manifest.json`.

Because the unconditioned readout is population-independent, each adapter is
scored once and compared against every population, so `--pairs all` (matched +
cross) costs no extra GPU time.

## Compute ledger

Publication clocks live in `paper_b/compute/`. `publication_estimate.json` is rebuilt from the harvested sources, and each clock names its scope. Optimizer minutes, the reference-cache forward pass, the training-loop wall clock, and the score-upload span are separate. They are not added into one GPU-hour total, and a Colab balance is not an invoice.

```bash
python paper_b/compute_ledger.py publish \
  --sources paper_b/compute/sources --out paper_b/compute
```

A live training or scoring run appends to `$SCA2_PB_DATA_ROOT/compute_ledger.jsonl`. Scoring also uploads that file to `runs/<run_id>/compute/ledger.jsonl` on the artifacts repo. An append failure does not fail a completed unit.

## Frozen values (do not drift)

- cohort: the 42 GPS∩WVS7 countries in `config.COHORT`
- bank: `synthetic_generation/outputs/gps_sign_relabel_all/` (658 rows/country, `deterministic_sign`)
- split: `TRAIN_FRAC=0.80`, `SEED=42` → 526 / 132
- model: `meta-llama/Llama-3.1-8B-Instruct`, QLoRA r=16 α=32 dropout=0.05 [q,k,v,o]
- DPO: β=0.1, lr=1e-4, 1 epoch, max_length=768, batch 1 × accum 16
- decisions: twins kept and reported as reliability contrast; near-zero = primary full bank + robustness variant (|z|≥0.10)
