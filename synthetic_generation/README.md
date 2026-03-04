# SCA 2.0 — Synthetic Data Generation Pipeline

## Overview

This pipeline generates culturally-conditioned synthetic preference pairs for DPO (Direct Preference Optimization) fine-tuning of language models. It conditions a teacher LLM on the Global Preferences Survey (GPS) cultural state vector $z_c \in \mathbb{R}^6$ to produce aligned/contrasting response pairs, scores them on all six GPS dimensions, applies quality control filters, and exports the dataset in formats ready for HuggingFace TRL's `DPOTrainer`.

The pipeline is part of the **Synthetic Cultural Agents (SCA) 2.0** project, which aims to train LLMs that exhibit culturally calibrated behavioral preferences, validated against the World Values Survey (WVS) via a structural econometric framework (Simulated Method of Moments / J-test).

## Quick Start

1. Open `SCA2_SyntheticDataGeneration_v3.ipynb` in Google Colab.
2. Upload the required datasets to the Colab file panel:
   - `country_gps.dta` — GPS country-level preference scores (from [GPS data](https://gps.econ.uni-bonn.de/downloads))
   - `WVS_wave7.dta` — WVS Wave 7 individual-level responses (from [WVS data](https://www.worldvaluessurvey.org/WVSDocumentationWV7.jsp))
3. Set your Anthropic API key in Colab Secrets (key icon in sidebar), named `ANTHROPIC_API_KEY`.
4. **Runtime → Run all**.

The demo run generates ~120 raw pairs (5 scenarios × 6 dimensions × 4 countries), with ~100 passing QC (~84% pass rate).

## Pipeline Architecture

The notebook is organized into six sequential blocks:

### Block A — Master Configuration (Cell 3)
- Imports and shared utilities
- `TARGET_COUNTRIES`: ISO3 codes for target cultures (default: ARG, MEX, USA, PAK)
- `GPS_DIMENSIONS`: Six behavioral dimensions with descriptions and scoring rubrics
- `CONFIG`: Hyperparameters (model, scenarios per dimension, temperature, QC thresholds)
- `WVS_ITEM_MAP`: 30 WVS items mapped to GPS dimensions across three tiers
- `MODEL_PRICING`: Per-token costs for supported models (Claude, Mistral)
- `CostTracker`: Async-safe cost logging with pilot-to-production cost estimation
- `tracked_call()`: LiteLLM wrapper with automatic cost tracking and retry logic

### Block B — Data Ingestion & Profile Construction (Cell 5)
- `extract_gps_vector()`: Loads z_c from GPS .dta file
- `gps_to_profile()`: Converts z_c to an ethnographic system prompt for the teacher
- `extract_wvs_anchors()`: Loads WVS behavioral anchors for contextual grounding

### Block C — Teacher Generation Engine (Cell 7)
- **Stage 1**: Generates N scenarios per GPS dimension (country-independent, 6 API calls)
- **Stage 2**: For each scenario × country, generates aligned + contrasting response pairs

### Block D — 6D Scoring & Quality Control (Cell 10)
- `score_pair()`: Scores both responses on all 6 GPS dimensions in a single API call
- Returns per-dimension score dicts + scorer reasoning
- `run_scoring_qc_export()`: Applies QC filters on the target dimension:
  - **Monotonicity filter**: `(m_diff × sign(z)) > 0` (aligned scores must be directionally correct)
  - **Distance filter**: `|Δm| ≥ 0.20` (minimum separation for structural signal)
- Computes contamination ratio $C_k$ as a diagnostic (not a filter)

### Block E — QC Report, Export, and Cost Summary (Cell 12)
- Per-country and per-dimension QC breakdown with contamination ratios
- Exports per-country JSONL files and combined HuggingFace Dataset
- Generates `manifest.json` with metadata and hyperparameters

### Block F — Pipeline Logic Validation (Cell 13)
- Self-contained mock tests (no API calls)
- Validates score clamping, error handling, QC filters, contamination ratio, and column schema

## Output Format

### JSONL / HuggingFace Dataset Columns

| Column | Type | Description |
|--------|------|-------------|
| `prompt` | str | Scenario text (the decision situation) |
| `chosen` | str | Culturally aligned response (what the student should prefer) |
| `rejected` | str | Opposite-disposition response |
| `gps_dimension` | str | Target GPS dimension for this pair |
| `country` | str | ISO3 country code |
| `m_chosen` | float | Target dimension score for chosen response |
| `m_rejected` | float | Target dimension score for rejected response |
| `m_diff_signed` | float | `m_chosen - m_rejected` (positive if alignment is correct) |
| `m_diff_abs` | float | `|m_chosen - m_rejected|` |
| `z_value` | float | GPS z-score for this country × dimension |
| `contamination_ratio` | float | $C_k$: ratio of non-target dimension movement to target |
| `reasoning` | str | Scorer's justification for the target dimension scores |
| `m_chosen_{dim}` | float | Per-dimension chosen scores (6 columns) |
| `m_rejected_{dim}` | float | Per-dimension rejected scores (6 columns) |

Total: 25 columns (13 core + 12 per-dimension scores).

### manifest.json

Contains run metadata including:
- `config`: All hyperparameters used
- `countries`: GPS z-vectors for each target country
- `qc_stats`: Pass/fail counts by filter type
- `mean_feature_distance`: Mean |Δm| across passing pairs
- `mean_contamination_ratio`: Mean $C_k$ across passing pairs
- `per_dim_contamination`: Mean $C_k$ broken down by GPS dimension
- `tier_2_items` / `tier_3_items`: WVS item codes used for validation

## For the DPO Fine-Tuning Step

### Loading the Dataset

```python
from datasets import load_from_disk, Dataset

# Option 1: Combined dataset
ds = load_from_disk("D_syn_combined_hf")

# Option 2: Per-country JSONL
ds = Dataset.from_json("D_syn_ARG.jsonl")
```

### Key Fields for DPOTrainer

```python
from trl import DPOTrainer, DPOConfig

config = DPOConfig(
    beta=0.1,
    per_device_train_batch_size=16,
    learning_rate=5e-5,
    num_train_epochs=3,
)

trainer = DPOTrainer(
    model=model,
    ref_model=ref_model,
    train_dataset=ds,
    tokenizer=tokenizer,
    args=config,
)
```

The three required fields are `prompt`, `chosen`, and `rejected`. The `manifest.json` file contains suggested hyperparameters.

## Configuration

### Key Parameters in `CONFIG`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `teacher_model` | `"claude-sonnet-4-6"` | Model for generation and scoring |
| `scenarios_per_dim` | `5` | Scenarios per GPS dimension (demo; use 170 for full run) |
| `qc_distance_thresh` | `0.20` | Minimum |Δm| for structural signal |
| `concurrency` | `2` | Async semaphore limit |
| `temperature_gen` | `0.8` | Temperature for paired generation |
| `temperature_score` | `0.1` | Temperature for scoring (low = consistent) |

### Changing Target Countries

Edit `TARGET_COUNTRIES` in Block A. Countries must exist in `country_gps.dta`.

### Cost Estimation

After a pilot run, use the cost estimation module to project full-run costs:

```python
# Project costs for 170 scenarios/dim × 4 countries using default model
cost_tracker.estimate_full_run(170, 4)

# What-if: project using Mistral Large instead
cost_tracker.estimate_full_run(170, 4, model="mistral-large-latest")
```

### Supported Models and Pricing

| Model | API Name | Input ($/MTok) | Output ($/MTok) |
|-------|----------|----------------|-----------------|
| Claude Opus 4.6 | `claude-opus-4-6` | $5.00 | $25.00 |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | $3.00 | $15.00 |
| Mistral Large 3 | `mistral-large-latest` | $0.50 | $1.50 |
| Mistral Medium 3 | `mistral-medium-latest` | $0.40 | $2.00 |
| Magistral Medium | `magistral-medium-latest` | $2.00 | $5.00 |

### Scale Estimates

| Scale | scenarios_per_dim | Countries | Raw Pairs | API Calls | Est. Cost (Sonnet) |
|-------|-------------------|-----------|-----------|-----------|-------------------|
| Demo | 5 | 4 | 120 | 246 | ~$0.50 |
| Pilot | 20 | 4 | 480 | 966 | ~$2.00 |
| Full | 170 | 4 | 4,080 | 8,166 | ~$15-20 |

## Quality Control

### Monotonicity Filter

The core QC check ensures directional consistency: for a pair targeting dimension $k$ in country $c$:

$$(\text{m\_chosen}_k - \text{m\_rejected}_k) \times \text{sign}(z_{c,k}) > 0$$

This means: if the culture scores positively on a dimension, the chosen response must score higher than the rejected response on that dimension (and vice versa for negative z-values).

### Distance Filter

Pairs must have sufficient separation on the target dimension:

$$|\text{m\_chosen}_k - \text{m\_rejected}_k| \geq 0.20$$

This threshold ensures the training signal is strong enough for DPO to learn from.

### Contamination Ratio ($C_k$)

The contamination ratio measures how much non-target dimensions move relative to the target:

$$C_k = \frac{\sum_{j \neq k} |m_j(\text{chosen}) - m_j(\text{rejected})|}{|m_k(\text{chosen}) - m_k(\text{rejected})|}$$

- **Low $C_k$ (< 1.0)**: The pair cleanly varies only the target dimension. Ideal.
- **Moderate $C_k$ (1.0-3.0)**: Some cross-dimension movement. Expected for correlated dimensions.
- **High $C_k$ (> 3.0)**: Non-target dimensions move more than the target. Investigate.

$C_k$ is reported as a **diagnostic only** — it does not filter pairs from the dataset.

## Known Limitations

1. **Weak WVS proxies for patience and positive reciprocity**: These dimensions have only 3-4 WVS items each, with non-significant correlations for patience ($\rho = 0.09$, $p = .52$ for the best proxy). J-test power on these dimensions will be limited.

2. **Same-model scoring**: Using the same model family (Claude Sonnet) for both generation and scoring creates a self-preference bias risk. Human validation benchmarking (Krippendorff's $\alpha \geq 0.7$) is a planned follow-up.

3. **No human validation yet**: The scorer has not been benchmarked against human raters.

4. **Score polarization**: Training-data scores are bimodal by design (the teacher generates maximally contrastive pairs). This does not affect DPO training (ordinal labels only) but means these scores are not suitable for continuous structural estimation. Validation-stage scores will be computed separately on student model outputs.

5. **Scale inversion**: WVS items marked "inv" have raw scales where higher = less of the trait. Currently computed as raw means (fine for contextual anchors) but must be inverted for J-test moment computation.

## File Manifest

| File | Description |
|------|-------------|
| `SCA2_SyntheticDataGeneration_v2.ipynb` | Main pipeline notebook (v3) |
| `CLAUDE_CODE_INSTRUCTIONS.md` | Task specification for notebook updates |
| `README.md` | This file |
| `context/audit_condensed.md` | Condensed audit findings with code changes |
| `context/SCA2_ProjectProposal.pdf` | Project proposal with pipeline specification |
| `raw_data/country.dta` | GPS country-level preference scores |
| `raw_data/WVS_Cross-National_Wave_7_stata_v6_0.dta` | WVS Wave 7 data |
| `D_syn_{COUNTRY}.jsonl` | Per-country preference pair exports (generated) |
| `D_syn_combined_hf/` | Combined HuggingFace Dataset (generated) |
| `manifest.json` | Run metadata and hyperparameters (generated) |
| `checkpoint_raw_pairs.jsonl` | Raw pairs before QC (generated) |
