# CLI Guide

This document explains how to run the SCA 2.0 synthetic data pipeline from the command line.

If you are a new undergraduate in the lab, read [README.md](./README.md) first. That file explains the research motivation. This guide is for actually running the code.

## Where to run commands

Always run the CLI from the `synthetic_generation/` directory:

```bash
cd synthetic_generation
python run.py --estimate-only --countries MEX USA
```

The package expects paths relative to this directory, and the default GPS/WVS path search is written with that assumption in mind.

## Recommended workflow

For large jobs, do not jump directly to production settings. Use this order:

1. Run `--estimate-only` to project money and runtime.
2. Run a very small real pilot, such as `--scenarios-per-dim 2`.
3. Inspect the outputs and QC stats.
4. Only then run larger sample sizes like `100,350,500`.

## Common commands

### 1. Estimate only

This does not call any model APIs. It only uses static pricing and runtime assumptions.

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
- cost breakdown by teacher / generator / scorer
- total estimated cost
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

- skips facet generation, scenario generation, and pair generation
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
- `--sample-sizes 100,350,500`
  - Final QC-passed rows per country to export. The pipeline runs once, then writes nested subsets.
- `--sample-size-policy {fail_fast,skip_unavailable,degrade_to_feasible}`
  - Controls behavior when requested sample sizes exceed QC-passed rows.
  - Default is `skip_unavailable` (export feasible sizes and record skipped sizes in the manifest).

### Model selection

The pipeline is cut over to the configured Hugging Face Inference Endpoints. These flags
remain for compatibility, but they only accept the HF endpoint aliases in
`sca2_datagen/config.py`; closed-provider model names are rejected.

```bash
python run.py \
  --teacher-model hf-teacher \
  --generator-model hf-generator \
  --scorer-model hf-scorer \
  --countries MEX USA \
  --scenarios-per-dim 10
```

Current defaults in code are:

- teacher: `hf-teacher`
- generator: `hf-generator`
- scorer: `hf-scorer`

### Reliability and throughput controls

- `--concurrency`
  - Max in-flight generation/scoring requests.
- `--max-retries`
  - Max retry attempts for transient API failures (429/timeout/network).
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

## Long-running runs and GitHub Codespaces

If your laptop is unreliable for a multi-hour run, GitHub Codespaces is a practical fallback.

### Suggested pattern

1. Open the repo in a Codespace.
2. Install dependencies.
3. Run `--estimate-only`.
4. Run a tiny pilot.
5. Launch the larger job only after the pilot looks right.

### Why Codespaces helps

- The machine stays online even if your laptop sleeps.
- Your outputs are written to the repository workspace, not your local laptop filesystem.
- You can reconnect later and continue working from the same environment.

### What to watch out for

- GitHub’s current default idle timeout for Codespaces is 30 minutes.
- GitHub Docs currently say new codespaces can be configured up to 240 minutes of idle timeout in personal settings.
- Codespaces are billed while active, so do not leave them running unnecessarily.
- Stopped codespaces are eventually auto-deleted after a retention period, so keep outputs you care about in the repository workspace and push/download them if needed.

### Practical advice

- Use `tmux` if you expect to disconnect from the browser tab.
- Keep `outputs/` inside the repo workspace, not in `/tmp`.
- Use checkpoints. If scoring fails after generation, `--resume` saves money.

Official docs:

- Idle timeout: <https://docs.github.com/en/codespaces/setting-your-user-preferences/setting-your-timeout-period-for-github-codespaces>
- Retention / auto-deletion: <https://docs.github.com/en/codespaces/setting-your-user-preferences/configuring-automatic-deletion-of-your-codespaces>

## Exact internet-error fallback behavior

This section is intentionally precise, because people often assume the pipeline has provider failover when it does not.

### What the pipeline does

1. **LiteLLM model-cost-map fallback**
   - LiteLLM may try to fetch a remote model cost map.
   - If that download fails, LiteLLM falls back to its local backup.
   - This affects metadata lookup, not the actual generation pipeline logic.

2. **Retry logic for provider API calls**
   - All model calls go through `tracked_completion()` in `sca2_datagen/utils.py`.
  - Retries are configurable from the CLI (`--max-retries`, backoff and timeout flags).
  - If providers return retry hints (for example `retry-after`), the wrapper respects them.

3. **Pair-level failure isolation**
   - Pair generation calls are wrapped by `safe_generate_pair()`.
   - If one pair keeps failing after retries, that pair is dropped and the batch continues.

4. **Sustained-failure early stop**
  - Stage 2 generation tracks rolling failure rates.
  - If the failure rate exceeds configured thresholds for a full window, the run aborts early with an actionable error.

### What the pipeline does not do

- It does **not** automatically switch to another provider if a selected Hugging Face endpoint is down.
- It does **not** automatically retry forever.
- It does **not** checkpoint midway through scoring.

### Consequences by pipeline stage

- **Facet generation fails repeatedly:** the run stops.
- **Scenario generation fails repeatedly:** the run stops.
- **A single pair generation fails repeatedly:** that pair is skipped.
- **Scoring fails repeatedly:** the run stops.

### What to do in practice

- If generation already finished and scoring later fails, rerun with `--resume ./outputs/checkpoint_raw_pairs.jsonl`.
- If generation fails before the checkpoint is written, fix the internet/provider issue and rerun the generation step.
- If you want true provider failover, that would need to be added explicitly in code; it is not a hidden feature of the current CLI.

## Reading the outputs

### JSONL files

Each `D_syn_{country}_{N}.jsonl` file contains the final QC-passed training pairs for one country and one sample size.

### Hugging Face dataset directory

Each `D_syn_combined_hf_{N}/` directory contains the combined final dataset across countries for that sample size.

### Manifest

Each `manifest_{N}.json` file records:

- config snapshot
- country GPS vectors
- QC statistics
- contamination summaries
- cost summary
- git hash
- scenario bank counts

This manifest is the first file you should inspect when you want to understand what happened in a run.
