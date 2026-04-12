# SCA 2.0 — Synthetic Data Generation Pipeline

> **EconLLM Lab** · Arizona State University
> Part of the [Synthetic Cultural Agents](https://www.econllm-lab.com/) research project

## What is this project?

This folder contains the data generation pipeline for **SCA 2.0** (Synthetic Cultural Agents, second generation). The goal is to create synthetic preference datasets that can be used to fine-tune open-source language models so they behave in ways that reflect the cultural preferences of specific populations — not just WEIRD (Western, Educated, Industrialized, Rich, Democratic) ones.

**The big idea:** The Global Preferences Survey (GPS) by Falk et al. (2018) measured six economic preferences — trust, risk-taking, patience, altruism, positive reciprocity, and negative reciprocity — across 76 countries. We use these measurements as a "cultural state vector" to condition a large language model to generate training data. A student model is then fine-tuned on this data using Direct Preference Optimization (DPO), which is mathematically equivalent to maximum likelihood estimation under the Bradley-Terry paired comparison model. This equivalence allows us to import structural econometrics tools (identification, overidentification testing, counterfactual analysis) into the fine-tuning process.

**Where this fits in the research agenda:**

| Paper | Focus | Status |
|-------|-------|--------|
| Paper 1 | DPO as BT MLE (theory) | Working paper complete |
| **Paper 2** | **Empirical validation (this pipeline)** | **Active development** |
| Paper 3 | Teacher bias bounds | Planned |
| Paper 4 | Counterfactual analysis | Planned |
| Paper 5 | Sequential extension (Soft Bellman) | Planned |

If you're new to the lab, start by reading:
- The [lab mission document](https://www.econllm-lab.com/) for context on what we do and why
- Falk et al. (2018), "Global Evidence on Economic Preferences," *QJE* — the GPS paper
- Capra, Gonzalez-Bonorino & Pantoja (2024), "LLMs Model Non-WEIRD Populations" — SCA 1.0
- The SCA 2.0 project proposal (in the `/docs` folder)

---

## Pipeline architecture

The pipeline has five blocks that run sequentially. Each block is a self-contained module.

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Block A    │───▶│   Block B    │───▶│   Block C    │───▶│   Block D    │───▶│   Block E    │
│   Config     │    │  Profiles    │    │  Generation  │    │ Scoring / QC │    │   Export     │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

### Block A — Configuration
Defines target countries, GPS dimensions, model choices, hyperparameters, WVS item mappings, and cost tracking. This is where you set `scenarios_per_dim`, choose the teacher and scorer models, and configure quality control thresholds.

**Key design decision:** We use a tiered model strategy. A frontier model generates scenarios (only 6 API calls total), a cost-effective model generates paired responses (the bulk of the cost), and a *different* model family scores them (to avoid self-preference bias).

### Block B — Data ingestion and profile construction
Loads the GPS dataset (`country_gps.dta`), extracts the 6-dimensional cultural state vector z_c for each target country, and builds a natural-language ethnographic profile. This profile becomes the system prompt for the teacher model.

**Key file:** `country_gps.dta` — contains GPS z-scores for 76 countries. Download from [briq-institute.org](https://gps.briq-institute.org).

### Block C — Teacher generation engine
Two-stage architecture:
1. **Scenario generation** (Stage 1): For each of the 6 GPS dimensions, the model generates diverse scenarios. These are country-independent, so we generate them once and reuse across all countries.
2. **Paired generation** (Stage 2): For each scenario × country, a single API call produces both an "aligned" response (matches the country's GPS disposition) and a "contrasting" response (opposite disposition). This contrastive approach avoids the "strawman" problem.

### Block D — Scoring and quality control
Each pair is scored on all 6 GPS dimensions in a single API call. Two QC filters are applied on the target dimension:
- **Monotonicity:** The score difference must point in the correct GPS direction.
- **Feature distance:** The absolute score difference must exceed a minimum threshold (default: 0.20).

A contamination ratio diagnostic tracks how much non-target dimensions bleed into the scoring.

### Block E — Export and cost summary
Exports the filtered dataset as `.jsonl` files (one per country) and a consolidated HuggingFace Dataset. Generates a `manifest.json` with full metadata: GPS scores, hyperparameters, QC statistics, and cost breakdown.

---

## Getting started

### Prerequisites
- Python 3.10+
- API keys for at least one LLM provider (Anthropic, DeepSeek, or OpenAI)
- The GPS dataset (`country_gps.dta`)

### Setup

```bash
# From the monorepo root
cd synthetic_generation

# Install dependencies
pip install -r requirements.txt

# Copy the environment template and add your API keys
cp .env.example .env
# Edit .env with your keys
```

### Running a pilot

```bash
# Small pilot run (20 scenarios per dimension, 2 countries)
python run.py --scenarios-per-dim 20 --countries MEX USA

# Incremental sample sizes for comparison
python run.py --sample-sizes 100,350,500 --countries MEX USA

# Full production run (use with caution — costs real money)
python run.py --scenarios-per-dim 170 --countries MEX USA ARG SWE
```

### Cost estimation

Before committing to a large run, always estimate costs first:

```bash
python run.py --estimate-only --scenarios-per-dim 170 --countries MEX USA ARG SWE
```

---

## Key concepts you should understand

### GPS dimensions
| Symbol | Dimension | What it measures |
|--------|-----------|------------------|
| τ | Trust | Belief that others have good intentions |
| γ | Risk-taking | Willingness to take risks |
| δ | Patience | Willingness to defer gratification |
| α | Altruism | Willingness to give to good causes |
| ξ+ | Positive reciprocity | Willingness to return a favor |
| ξ- | Negative reciprocity | Willingness to punish unfair behavior |

### DPO (Direct Preference Optimization)
The fine-tuning method we use. It takes pairs of (preferred, dispreferred) responses and adjusts model weights so the preferred response becomes more likely. The key insight of this project is that DPO's training objective is mathematically identical to the Bradley-Terry log-likelihood — which means we can use econometric tools to validate the trained model.

### The J-test
Our main validation tool. After fine-tuning, we check whether the model's behavior matches out-of-sample moments from the World Values Survey (WVS Wave 7). The J-statistic tells us whether our structural model is overidentified — i.e., whether 6 GPS parameters are enough to explain 30+ behavioral moments.

---

## Repository structure

```
synthetic_generation/
├── README.md                    ← You are here
├── run.py                       ← CLI entrypoint
├── pyproject.toml               ← Package metadata
├── requirements.txt             ← Python dependencies
├── .env.example                 ← API key template
├── sca2_datagen/
│   ├── config.py                ← Block A: constants and runtime config
│   ├── profiles.py              ← Block B: GPS ingestion and profiles
│   ├── generate.py              ← Block C: scenario + pair generation
│   ├── score.py                 ← Block D: scoring and QC
│   ├── export.py                ← Block E: export + manifest
│   └── utils.py                 ← Shared utilities
├── tests/                       ← Unit and integration tests (mocked APIs)
├── sample_output/               ← Example outputs
└── SCA2_SyntheticDataGeneration_v3.ipynb
```

---

## Contributing

### For undergraduates joining the project

1. **Read the project proposal** (`../SCA2_ProjectProposal.pdf`) — understand the hypotheses (H1–H4) and where your work fits.
2. **Run a small pilot** (20 scenarios/dim, 2 countries) to see how the pipeline works end-to-end.
3. **Look at the output** — open the `.jsonl` files and examine the generated pairs. Do the "chosen" responses feel culturally aligned? Do the "rejected" responses feel like genuine alternatives?
4. **Check the QC report** — what are the monotonicity pass rates? Which dimensions have the highest contamination ratios?

### Development workflow
- Create a branch for your changes
- Test with a small pilot run before pushing
- Document any prompt changes in the commit message — prompt wording matters significantly for output quality
- If using a coding agent (Claude Code, Codex), provide it with this README and the relevant module file

### What NOT to do
- Do not modify the WVS item map (`WVS_ITEM_MAP` in config.py) after a training run has started — this is a pre-registration decision
- Do not commit API keys to the repository
- Do not run production-scale generation without first running `--estimate-only`

---

## Design decisions and known limitations

These are documented here so new members understand *why* things are the way they are:

1. **English-only generation:** Confirmed that cross-language behavior shifts are minimal for our purposes. Keeps the pipeline simpler and cheaper.
2. **Contrastive pair generation:** Both responses generated in a single API call. This avoids the "strawman" problem and costs half as much as generating separately.
3. **Multi-model scoring:** Using a different model family for scoring than for generation reduces self-preference bias (a known limitation of v3).
4. **No nationality references:** Responses should NOT contain phrases like "As a Mexican..." — we express cultural dispositions through behavioral choices, not identity labels. This distinguishes SCA 2.0 (structural) from SCA 1.0 (persona prompting).
5. **Monotonicity filter on target dimension only:** QC filters check only the target GPS dimension, not all six. Cross-dimensional contamination is tracked but not filtered on.

**Known limitations:**
- Positive reciprocity has only 3 WVS proxy items — J-test power will be low on this dimension
- No human validation yet (Krippendorff's α ≥ 0.7 target is a planned follow-up)
- Patience and risk-taking WVS proxies have questionable face validity (flagged for review)

---

## References

- Falk, A., Becker, A., Dohmen, T., Enke, B., Huffman, D., & Sunde, U. (2018). Global evidence on economic preferences. *The Quarterly Journal of Economics*, 133(4), 1645–1692.
- Rafailov, R., Sharma, A., Mitchell, E., Ermon, S., Manning, C. D., & Finn, C. (2023). Direct Preference Optimization: Your language model is secretly a reward model. *NeurIPS 2023*.
- Capra, C. M., Gonzalez-Bonorino, A., & Pantoja, E. (2024). LLMs model non-WEIRD populations: Experiments with Synthetic Cultural Agents. *SSRN Working Paper No. 5082714*.
- Gonzalez-Bonorino, A. (2026). Synthetic Cultural Agents via Structural Preference Estimation: DPO as Bradley-Terry MLE. *Working paper, EconLLM Lab, ASU*.
