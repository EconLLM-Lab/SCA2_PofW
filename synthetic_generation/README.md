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
- Capra, Gonzalez-Bonorino & Pantoja (2025), "LLMs Model Non-WEIRD Populations" — SCA 1.0
- The SCA 2.0 project proposal (in [`context/SCA2_ProjectProposal.pdf`](./context/SCA2_ProjectProposal.pdf))

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
Defines target countries, GPS dimensions, Hugging Face endpoint role aliases, hyperparameters, WVS item mappings, and cost tracking. This is where you set `scenarios_per_dim` and configure quality control thresholds.

**Key design decision:** We use three dedicated Hugging Face Inference Endpoints. The teacher endpoint handles facet and scenario generation, the generator endpoint creates fixed high/low triplets once per scenario, and the scorer endpoint handles profile-based selection plus QC scoring.

### Block B — Data ingestion and profile construction
Loads the GPS dataset (`country_gps.dta`), extracts the 6-dimensional cultural state vector z_c for each target country, and builds a natural-language ethnographic profile. This profile is used by the scorer endpoint when selecting which fixed response option matches a country.

**Key file:** `country_gps.dta` — contains GPS z-scores for 76 countries. Download from [briq-institute.org](https://gps.briq-institute.org).

### Block C — Generation engine

**Anchor Usage (v1):** Anchors are now used as *positive structural exemplars* rather than negative constraints. The generator is instructed to emulate facet logic and core tradeoff style while varying surface context.
Four-step architecture:
1. **Facet decomposition** (Stage 0): For each of the 6 GPS dimensions, the teacher model first breaks the trait into 4–6 concrete sub-dimensions.
2. **Scenario generation** (Stage 1): For each facet, the teacher model generates diverse scenarios. These are country-independent, so we generate them once and reuse across all countries.
3. **Fixed triplet generation** (Stage 2): For each scenario, the generator endpoint creates fixed high/low response options once, independent of country.
4. **Profile-based selection** (Stage 2b): For each country, the scorer endpoint selects which fixed option best matches that country's GPS disposition. This keeps the response options fixed across countries while preserving country-specific preferences.

### Block D — Scoring and quality control
Each pair is scored on all 6 GPS dimensions in a single API call. For the target GPS dimension,
`m_chosen` and `m_rejected` are the scorer's 0-1 ratings for the selected and rejected
responses. `m_diff_signed = m_chosen - m_rejected`, `m_diff_abs` is its absolute value, and
`z_value` is the country's standardized GPS score on that dimension.

**Quality Control (updated v1 behavior):**
Examples are no longer hard-dropped on QC failure. Instead, they are retained with metadata:
- `qc_status`: "pass" | "mono_fail" | "dist_fail" | "score_fail"
- `failure_reason`: human-readable explanation
- `mono_pass`, `dist_pass` booleans

This enables downstream filtering, down-weighting, or targeted recovery while preserving transparency.

`contamination_ratio` measures non-target movement: the sum of absolute score differences across
the other five GPS dimensions divided by the target-dimension difference. `contamination_category`
bins that diagnostic as `low` (<0.3), `medium` (<0.7), or `high` (>=0.7). We track it to identify
pairs that pass target-dimension QC but may also encode other cultural traits.

For DPO and structural validation, a high-quality generated dataset should have strong QC pass
rates, low monotonicity and distance failure rates, contamination concentrated in the low/medium
buckets, and signed differences aligned with the country GPS `z_value`. High-contamination
dimensions should be reviewed before downstream use, but contamination remains diagnostic rather
than an additional hard filter.

### Block E — Export and cost summary
Exports the filtered dataset as `.jsonl` files (one per country and sample size) and a consolidated HuggingFace Dataset. Generates `manifest_{N}.json` files with full metadata: GPS scores, hyperparameters, QC statistics, token usage, elapsed-runtime endpoint cost estimate, and git hash.

---

## Getting started

### Prerequisites
- Python 3.10+
- A personal Hugging Face token in `HF_TOKEN` with permission to call the configured Inference Endpoints.
- Hugging Face Inference Endpoint URLs. The repository includes lab defaults, but you can override them in `.env` or with CLI flags.
- Endpoint hourly-rate defaults are configured for the current lab Hugging Face endpoints:
  teacher `llama-3-3-70b-instruct-gguf-fnk` on Nvidia A100 at `$2.50/hr`,
  generator `qwen3-32b-chm` on 1x Nvidia H200 at `$5.00/hr`, and scorer
  `phi-4-uid` on Nvidia L40S at `$1.80/hr`.
- Optional endpoint hourly-rate env vars override those defaults when endpoints change:
  `HF_TEACHER_HOURLY_USD`, `HF_GENERATOR_HOURLY_USD`, and `HF_SCORER_HOURLY_USD`.
- The GPS dataset (`country_gps.dta`)

### Setup

```bash
# From the monorepo root
cd synthetic_generation

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies, including test dependencies
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"

# Copy the environment template and add your personal HF token
cp .env.example .env
# Edit .env with HF_TOKEN and, optionally, endpoint URL/rate overrides
```

Place `country_gps.dta` in one of the default locations listed in `sca2_datagen/config.py`, or pass it explicitly:

```bash
python run.py --estimate-only --gps-path /path/to/country_gps.dta --countries MEX USA
```

### Before you run anything expensive

Always do these in order:

1. Run `--estimate-only` first.
2. Run a tiny pilot (for example `--scenarios-per-dim 2` and one or two countries).
3. Only then run larger sample sizes such as `100,350,500`.

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

Cost estimates are run-scoped: the manifest multiplies the pipeline wall-clock runtime by
the configured endpoint hourly rates. Historical provider-console spend is also included
as calibration metadata, but it is not added to every run. Provider-console totals can be
higher than manifest totals when endpoints remain active before or after the CLI run.

### Using the CLI

The CLI has grown enough that it now deserves its own guide:

- Read [CLI_GUIDE.md](./CLI_GUIDE.md) for the full command reference
- Use `--resume` if generation already finished and you want to restart from scoring
- Model override flags were removed after the Hugging Face cutover. Endpoint roles are configured in `sca2_datagen/config.py`.

The most common commands are:

```bash
# Estimate money and runtime only (no API calls)
python run.py --estimate-only --scenarios-per-dim 130 --countries MEX USA --sample-sizes 100,350,500

# Run a small real pilot
python run.py --scenarios-per-dim 5 --countries MEX ARG --sample-sizes 10 --output-dir ./outputs

# Resume from a saved raw-pair checkpoint and skip generation
python run.py --resume ./outputs/checkpoint_raw_pairs.jsonl --countries MEX ARG --sample-sizes 10 --output-dir ./outputs
```

### Long-running runs and GitHub Codespaces

If your laptop is unreliable for multi-hour generations, GitHub Codespaces is a reasonable fallback.

- Codespaces stop after inactivity. GitHub’s current default idle timeout is 30 minutes, and personal settings can raise it up to 240 minutes for new codespaces.
- Codespaces also auto-delete stopped environments after a retention period, so keep outputs you care about inside the repository workspace and push them or download them when needed.
- The safest pattern is: estimate first, run a tiny pilot second, then launch the large run in a Codespace terminal.
- If you expect to disconnect from the browser, use a terminal multiplexer such as `tmux` inside the Codespace so you can reconnect cleanly.
- This pipeline now writes `checkpoint_raw_pairs.jsonl` and `checkpoint_scenario_bank.json` after generation. If scoring fails later, you can restart from `--resume` instead of paying to regenerate the raw pairs.

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
├── CLI_GUIDE.md                 ← Operational guide for the command-line interface
├── run.py                       ← CLI entrypoint
├── pyproject.toml               ← Package metadata
├── requirements.txt             ← Python dependencies
├── .env.example                 ← API key template
├── sca2_datagen/
│   ├── config.py                ← Block A: constants and runtime config
│   ├── profiles.py              ← Block B: GPS ingestion and profiles
│   ├── generate.py              ← Block C: scenarios, fixed triplets, selection
│   ├── score.py                 ← Block D: scoring and QC
│   ├── export.py                ← Block E: export + manifest
│   └── utils.py                 ← Shared utilities
├── tests/                       ← Unit and integration tests (mocked APIs)
└── outputs/                     ← Runtime outputs and checkpoints (not hand-edited)
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
- If using a coding agent, provide it with this README and the relevant module file
- If you are editing CLI behavior, also update `CLI_GUIDE.md`

### What NOT to do
- Do not modify the WVS item map (`WVS_ITEM_MAP` in config.py) after a training run has started — this is a pre-registration decision
- Do not commit API keys to the repository
- Do not run production-scale generation without first running `--estimate-only`

---

## Design decisions and known limitations

These are documented here so new members understand *why* things are the way they are:

1. **English-only generation:** Confirmed that cross-language behavior shifts are minimal for our purposes. Keeps the pipeline simpler and cheaper.
2. **Facet-first scenario generation:** Each GPS dimension is first decomposed into 4–6 facets before scenario generation. This raises scenario diversity compared with the original notebook.
3. **Fixed triplet generation:** The high/low response options are generated once per scenario, independent of country, then reused across countries. This removes the old country-specific pair generation flow and makes cross-country comparisons cleaner.
4. **Separate scoring endpoint:** The scorer endpoint handles both profile-based selection and QC scoring, reducing generator self-preference bias relative to a single-endpoint pipeline.
5. **No nationality references:** Responses should not contain phrases like "As a Mexican..." or "As an American...". We express cultural dispositions through behavioral choices, not identity labels.
6. **Monotonicity filter on target dimension only:** QC filters check only the target GPS dimension, not all six. Cross-dimensional contamination is tracked diagnostically but not filtered on.
7. **Checkpoint after generation:** The pipeline writes raw pairs and a scenario bank checkpoint before scoring so long runs can be resumed without paying for generation twice.
8. **Policy-based sample-size export:** When requested sample sizes exceed QC-passed rows, behavior is policy-controlled (`fail_fast`, `skip_unavailable`, `degrade_to_feasible`).
9. **Early-stop reliability guard:** Stage 2 can stop early on sustained generation failure rates to avoid wasting long runs under heavy provider throttling.

**Known limitations:**
- Positive reciprocity has only 3 WVS proxy items — J-test power will be low on this dimension
- No human validation yet (Krippendorff's α ≥ 0.7 target is a planned follow-up)
- Patience and risk-taking WVS proxies have questionable face validity (flagged for review)
- The pipeline retries transient API failures and can stop early when failure rates remain too high, but it does **not** fall back to closed-provider models or alternate endpoints. See [CLI_GUIDE.md](./CLI_GUIDE.md) for exact behavior.

---

## References

- Falk, A., Becker, A., Dohmen, T., Enke, B., Huffman, D., & Sunde, U. (2018). [Global Evidence on Economic Preferences](https://doi.org/10.1093/qje/qjy013). *The Quarterly Journal of Economics*, 133(4), 1645–1692.
- Rafailov, R., Sharma, A., Mitchell, E., Manning, C. D., Ermon, S., & Finn, C. (2023). [Direct Preference Optimization: Your Language Model is Secretly a Reward Model](https://openreview.net/forum?id=HPuSIXJaa9). *Advances in Neural Information Processing Systems 36*.
- Capra, C. M., Gonzalez-Bonorino, A., & Pantoja, E. (2025). [LLMs Model Non-WEIRD Populations: Experiments with Synthetic Cultural Agents](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5082714). *SSRN Working Paper No. 5082714*.
- Gonzalez-Bonorino, A. (2026). Synthetic Cultural Agents via Structural Preference Estimation: DPO as Bradley-Terry MLE. *Working paper, EconLLM Lab, ASU*.
