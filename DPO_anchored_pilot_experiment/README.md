# Anchored Pilot DPO Replication

This folder is a separate experiment workspace for running DPO on the anchored
synthetic samples in `synthetic_generation/outputs/anchored_pilot_v1/`.
It does not modify `DPO_preliminary_results/`.

## Inputs

The experiment uses the current 172-row anchored samples:

- `D_syn_ARG_172.jsonl`
- `D_syn_SWE_172.jsonl`
- `D_syn_USA_172.jsonl`

Each file is validated for `prompt`, `chosen`, `rejected`, `country`, and
`gps_dimension`, then split deterministically with `TRAIN_FRAC=0.80` and
`SEED=42`.

## Manual Setup

Run training in a Colab GPU runtime. A100 or L4 is preferred; T4 may be slow or
memory constrained.

For the current stable Colab checkpoint, use
[`COLAB_CHECKPOINT.md`](COLAB_CHECKPOINT.md). It starts from cloning the
`feature/scenario-anchors-v1` branch and includes the Drive-backed commands used
for the anchored pilot run.

1. Confirm Hugging Face access to `meta-llama/Llama-3.1-8B-Instruct`.
2. Create or use a Hugging Face token with read access.
3. Upload or clone this repo in Colab.
4. Install dependencies:

```bash
pip install -r DPO_anchored_pilot_experiment/requirements-colab.txt
```

5. Log in to Hugging Face:

```python
from huggingface_hub import notebook_login
notebook_login()
```

No synthetic-generation API key is needed; this sprint uses existing JSONL files.

## Run Order

From the repo root:

```bash
python DPO_anchored_pilot_experiment/run_experiment.py check
python DPO_anchored_pilot_experiment/run_experiment.py prepare
python DPO_anchored_pilot_experiment/run_experiment.py smoke
```

Then run reference-logprob precomputation and training. You can do one country
at a time to manage GPU memory:

```bash
python DPO_anchored_pilot_experiment/run_experiment.py precompute --country ARG
python DPO_anchored_pilot_experiment/run_experiment.py train --country ARG

python DPO_anchored_pilot_experiment/run_experiment.py precompute --country SWE
python DPO_anchored_pilot_experiment/run_experiment.py train --country SWE

python DPO_anchored_pilot_experiment/run_experiment.py precompute --country USA
python DPO_anchored_pilot_experiment/run_experiment.py train --country USA
```

Before the full evaluation, run a small smoke eval:

```bash
python DPO_anchored_pilot_experiment/run_experiment.py evaluate \
  --adapter-country ARG \
  --max-examples 2 \
  --no-generate-answers
```

Then evaluate all adapters on all held-out country splits and summarize:

```bash
python DPO_anchored_pilot_experiment/run_experiment.py evaluate
python DPO_anchored_pilot_experiment/run_experiment.py summarize
```

## Outputs

Generated artifacts are written under:

`DPO_anchored_pilot_experiment/outputs/anchored_pilot_v1_dpo/`

Expected result files:

- `results/reward_recovery_adapters_combined.csv`
- `results/reward_recovery_adapter_summary.csv`
- `results/reward_recovery_dimension_summary.csv`
- `results/specialization_matrix_mean_reward_delta.csv`
- `results/specialization_matrix_preference_accuracy.csv`
- `results/own_vs_other_summary.csv`
- `reports/run_report.md`

Adapters are saved under `outputs/anchored_pilot_v1_dpo/adapters/`.
The output directory is gitignored by default because it can contain large model
artifacts and generated results.

## Interpretation

The main hypothesis is that each adapter should recover preferences better on
its own held-out country than on other countries. The key evidence is whether
the 3x3 adapter/eval matrix has stronger diagonal cells than off-diagonal cells.

These results are exploratory. With 172 source rows per country, each eval split
has 35 rows. The USA source file also has only 1 `negrecip` example, so
that dimension is explicitly underpowered and should not drive conclusions.
