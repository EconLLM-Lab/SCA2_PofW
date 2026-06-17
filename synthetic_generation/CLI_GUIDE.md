# CLI Guide

This guide explains how to run the SCA 2.0 synthetic data pipeline from the command line.

**Important**: If you are new to the lab or this project, please read the [README.md](./README.md) first. It explains the research goals and overall architecture.

This guide assumes you have basic comfort with the terminal (cd, ls, python, etc.).


## Before You Start

1. **Activate your virtual environment**
   ```bash
   source .venv/bin/activate
   ```

2. **Make sure you are in the right directory**
   ```bash
   cd synthetic_generation
   ```

3. **Endpoints take time to wake up**
   The first time you run the pipeline (or after a long pause), the Hugging Face endpoints will need 30–90 seconds to start. The pipeline has automatic retries, so just let it run.


## Where to run commands

Always run the CLI from the `synthetic_generation/` directory:

```bash
cd synthetic_generation
python run.py --estimate-only --countries MEX USA
```

The package expects paths relative to this directory, and the default GPS/WVS path search is written with that assumption in mind.
The cost estimates are not reliable (often overestimated) as of **June 16** because we switched to open-source models served via hugginface inference endpoints which charge per hour rather than per token/call. 

Use a virtual environment for reproducible setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"
```

## Recommended workflow

For large jobs, do not jump directly to production settings. Use this order:

1. Run `--estimate-only` to project money and runtime.
2. Run a very small real pilot, such as `--scenarios-per-dim 2`.
3. Inspect the outputs and QC stats.
4. Only then run larger sample sizes like `100,350,500`.

## Common commands

### 1. Estimate only

This does not call any model APIs. It only uses static runtime and token assumptions.

```bash
python run.py \
  --estimate-only \
  --scenarios-per-dim 130 \
  --countries MEX USA \
  --sample-sizes 100,350,500
```

The estimate now reports:

- expected raw pairs per country
- expected QC-passed rows per country
- token usage estimate by teacher / generator / scorer
- endpoint runtime cost estimate using configured defaults or hourly-rate env overrides
- estimated runtime in seconds and `Xh Ym` form

### 2. Small pilot run

```bash
python run.py \
  --scenarios-per-dim 5 \
  --countries MEX ARG \
  --sample-sizes 10 \
  --output-dir ./outputs
```

This creates:

- `outputs/D_syn_MEX_10.jsonl`
- `outputs/D_syn_ARG_10.jsonl`
- `outputs/D_syn_combined_hf_10/`
- `outputs/manifest_10.json`
- `outputs/checkpoint_raw_pairs.jsonl`
- `outputs/checkpoint_scenario_bank.json`

### 3. Resume from a checkpoint

If generation already finished and scoring/export failed, resume from the raw pair checkpoint:

```bash
python run.py \
  --resume ./outputs/checkpoint_raw_pairs.jsonl \
  --countries MEX ARG \
  --sample-sizes 10 \
  --output-dir ./outputs
```

What `--resume` does:

- skips facet generation, scenario generation, fixed triplet generation, and profile-based selection
- loads the raw pair JSONL you point to
- tries to load `checkpoint_scenario_bank.json` from either the output directory or next to the resume file
- resumes at scoring and export

What `--resume` does **not** do:

- it does not resume halfway through generation
- it does not resume halfway through scoring
- it does not regenerate missing scenario bank metadata if you deleted that file

## Important CLI flags

### Dataset size and countries

- `--scenarios-per-dim N`
  - Number of raw scenarios to generate per GPS dimension before QC.
- `--countries MEX USA ARG`
  - Space-separated ISO3 country codes.
  - Codes are normalized to uppercase. On `--resume`, omitting `--countries` uses the countries found in the checkpoint.
- `--sample-sizes 100,350,500`
  - Final QC-passed rows per country to export. The pipeline runs once, then writes nested subsets.
- `--sample-size-policy {fail_fast,skip_unavailable,degrade_to_feasible}`
  - Controls behavior when requested sample sizes exceed QC-passed rows.
  - Default is `skip_unavailable` (export feasible sizes and record skipped sizes in the manifest).
- `--use-anchors [True|False]`
  - Adds three curated anchors for the current GPS dimension to fixed triplet prompts.
  - A bare `--use-anchors` is equivalent to `--use-anchors True`.

### Endpoint roles

The pipeline is HF-only. Model override flags were removed after the cutover; endpoint aliases are configured in `sca2_datagen/config.py`:

- `hf-teacher`: facet decomposition and scenario generation
- `hf-generator`: fixed high/low triplet generation
- `hf-scorer`: profile-based option selection and QC scoring

Closed-provider model names are not accepted anywhere in the runtime path. If a model alias outside the configured HF endpoints is used programmatically, `tracked_completion()` raises an unsupported-model error.

Required environment:

```bash
HF_TOKEN="hf_..."
```

Use a personal Hugging Face token. Do not pass tokens as CLI flags; command-line arguments can be captured in shell history and process listings.

The repository has lab default endpoint URLs, but you can override them in `.env`:

```bash
HF_TEACHER_ENDPOINT_URL="https://.../v1/"
HF_GENERATOR_ENDPOINT_URL="https://.../v1/"
HF_SCORER_ENDPOINT_URL="https://.../v1/"
```

You can also override URLs for one run:

```bash
python run.py \
  --countries MEX ARG \
  --teacher-endpoint-url https://.../v1/ \
  --generator-endpoint-url https://.../v1/ \
  --scorer-endpoint-url https://.../v1/
```

The pipeline has calibrated default hourly rates for the current lab endpoints:

| Role | Endpoint | Hardware | Default rate |
|------|----------|----------|--------------|
| teacher | `llama-3-3-70b-instruct-gguf-fnk` | Nvidia A100 | `$2.50/hr` |
| generator | `qwen3-32b-chm` | 1x Nvidia H200 | `$5.00/hr` |
| scorer | `phi-4-uid` | Nvidia L40S | `$1.80/hr` |

Optional cost-estimation environment overrides:

```bash
HF_TEACHER_HOURLY_USD="..."
HF_GENERATOR_HOURLY_USD="..."
HF_SCORER_HOURLY_USD="..."
```

If the hourly-rate variables are unset, manifests use the calibrated defaults in
`sca2_datagen/config.py`. If an hourly-rate variable is invalid, the manifest marks it as
invalid and falls back to the config default.

Manifest costs are run-scoped estimates: elapsed CLI wall-clock time multiplied by hourly
endpoint rates. The manifest also records historical provider-console spend since endpoint
creation as calibration metadata. That historical spend is not added to each run because it
can include endpoint uptime before or after the CLI process.

### Reliability and throughput controls

- `--concurrency`
  - Max in-flight generation/scoring requests.
- `--max-retries`
  - Max retry attempts for transient API failures (429/timeout/network/503 cold starts).
- `--request-timeout-s`
  - Request timeout passed to LiteLLM calls.
- `--retry-backoff-min-s`, `--retry-backoff-max-s`, `--retry-jitter-s`
  - Exponential backoff and jitter controls between retries.
- `--error-rate-window`, `--max-error-rate-for-continue`
  - Early-stop guard for Stage 2 generation when sustained failures indicate the run is unlikely to succeed.

### Paths

- `--output-dir ./outputs`
  - Where manifests, JSONL files, Hugging Face datasets, and checkpoints go.
- `--gps-path PATH`
  - Override the GPS dataset path.
- `--wvs-path PATH`
  - Override the optional WVS path.


## Reading the outputs

### JSONL files

Each `D_syn_{country}_{N}.jsonl` file contains the final QC-passed training pairs for one country and one sample size.

Use outputs from a fresh run or from `outputs/`. Legacy closed-provider sample outputs have been removed from the repository; current validation should use freshly generated HF-only outputs.

### Hugging Face dataset directory

Each `D_syn_combined_hf_{N}/` directory contains the combined final dataset across countries for that sample size.

### Manifest

Each `manifest_{N}.json` file records:

- config snapshot
- country GPS vectors
- QC statistics
- contamination summaries
- token usage and endpoint runtime cost summary
- git hash
- scenario bank counts

This manifest is the first file you should inspect when you want to understand what happened in a run.
