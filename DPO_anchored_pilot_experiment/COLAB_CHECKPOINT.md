# Colab Checkpoint: Anchored DPO Training Run

This is the clean checkpoint for rerunning the anchored DPO pipeline from a
fresh Colab GPU runtime. It assumes the experiment code is on the branch
`feature/scenario-anchors-v1`.

Use one cell per section. Keep generated adapters and results in Google Drive so
runtime disconnects do not erase the run.

## 1. Clone the Experiment Branch

```bash
!git clone --branch feature/scenario-anchors-v1 https://github.com/EconLLM-Lab/SCA2_PofW.git
%cd SCA2_PofW
!ls DPO_anchored_pilot_experiment
```

If the repo was already cloned in the runtime:

```bash
%cd /content/SCA2_PofW
!git fetch origin
!git checkout feature/scenario-anchors-v1
!git pull --ff-only
```

## 2. Install Dependencies

```bash
!pip install -q -r DPO_anchored_pilot_experiment/requirements-colab.txt
```

If Colab asks you to restart the runtime after installing packages, restart and
then run:

```python
%cd /content/SCA2_PofW
```

## 3. Mount Drive and Set Output Root

```python
from google.colab import drive
drive.mount("/content/drive")

OUTPUT_ROOT = "/content/drive/MyDrive/SCA2_DPO_anchored_pilot_v1"
print(OUTPUT_ROOT)
```

For a new larger batch, change only `OUTPUT_ROOT`, for example:

```python
OUTPUT_ROOT = "/content/drive/MyDrive/SCA2_DPO_large_batch_v1"
```

## 4. Hugging Face Login

Use a Hugging Face read token with approved access to
`meta-llama/Llama-3.1-8B-Instruct`.

```python
from huggingface_hub import notebook_login
notebook_login()
```

## 5. Validate Inputs and Prepare Splits

```bash
!python DPO_anchored_pilot_experiment/run_experiment.py check \
  --output-root "$OUTPUT_ROOT"

!python DPO_anchored_pilot_experiment/run_experiment.py prepare \
  --output-root "$OUTPUT_ROOT"
```

Expected for the anchored pilot:

- `ARG`: 172 source, 137 train, 35 eval
- `SWE`: 172 source, 137 train, 35 eval
- `USA`: 172 source, 137 train, 35 eval

## 6. Runtime Smoke Test

```bash
!python DPO_anchored_pilot_experiment/run_experiment.py smoke \
  --output-root "$OUTPUT_ROOT"
```

Proceed only if this loads the tokenizer/model and prints a sample chosen logp.

## 7. Train Adapters

Run one country at a time. This makes failures easier to recover from.

```bash
!python DPO_anchored_pilot_experiment/run_experiment.py precompute \
  --country ARG \
  --output-root "$OUTPUT_ROOT"

!python DPO_anchored_pilot_experiment/run_experiment.py train \
  --country ARG \
  --output-root "$OUTPUT_ROOT"
```

```bash
!python DPO_anchored_pilot_experiment/run_experiment.py precompute \
  --country SWE \
  --output-root "$OUTPUT_ROOT"

!python DPO_anchored_pilot_experiment/run_experiment.py train \
  --country SWE \
  --output-root "$OUTPUT_ROOT"
```

```bash
!python DPO_anchored_pilot_experiment/run_experiment.py precompute \
  --country USA \
  --output-root "$OUTPUT_ROOT"

!python DPO_anchored_pilot_experiment/run_experiment.py train \
  --country USA \
  --output-root "$OUTPUT_ROOT"
```

## 8. Evaluation Smoke Test

```bash
!python DPO_anchored_pilot_experiment/run_experiment.py evaluate \
  --adapter-country ARG \
  --max-examples 2 \
  --no-generate-answers \
  --output-root "$OUTPUT_ROOT"
```

Expected: 2 examples for each of `ARG`, `SWE`, and `USA`.

## 9. Metrics-Only Full Evaluation

Run this first. It produces the main quantitative result without spending time
on generated qualitative answers.

```bash
!python DPO_anchored_pilot_experiment/run_experiment.py evaluate \
  --no-generate-answers \
  --output-root "$OUTPUT_ROOT"

!python DPO_anchored_pilot_experiment/run_experiment.py summarize \
  --output-root "$OUTPUT_ROOT"
```

## 10. Print Main Results

```python
from pathlib import Path
import pandas as pd

root = Path(OUTPUT_ROOT)

files = [
    "results/reward_recovery_adapter_summary.csv",
    "results/specialization_matrix_mean_reward_delta.csv",
    "results/specialization_matrix_preference_accuracy.csv",
    "results/own_vs_other_summary.csv",
]

for f in files:
    print("\n\n###", f)
    print(pd.read_csv(root / f).to_string(index=False))

print("\n\n### reports/run_report.md")
print((root / "reports/run_report.md").read_text())
```

## 11. Pairwise Transfer Summary

Use this to distinguish strict own-country specialization from cluster-like
cross-country transfer.

```python
from pathlib import Path
import pandas as pd

root = Path(OUTPUT_ROOT)
s = pd.read_csv(root / "results/reward_recovery_adapter_summary.csv")
cross = s[s["adapter_country"] != s["eval_country"]].copy()

pair_rows = []
for pair, g in cross.assign(
    pair=lambda d: d.apply(
        lambda r: "-".join(sorted([r["adapter_country"], r["eval_country"]])),
        axis=1,
    )
).groupby("pair"):
    pair_rows.append({
        "pair": pair,
        "mean_cross_reward_delta": g["mean_reward_delta"].mean(),
        "mean_cross_preference_accuracy": g["preference_accuracy"].mean(),
        "directions": "; ".join(
            f"{r.adapter_country}->{r.eval_country}: "
            f"delta={r.mean_reward_delta:.3f}, acc={r.preference_accuracy:.3f}"
            for r in g.itertuples()
        ),
    })

pair_transfer = pd.DataFrame(pair_rows).sort_values(
    "mean_cross_reward_delta",
    ascending=False,
)
print(pair_transfer.to_string(index=False))
```

## 12. Dimension Summary

```python
from pathlib import Path
import pandas as pd

root = Path(OUTPUT_ROOT)
dim = pd.read_csv(root / "results/reward_recovery_dimension_summary.csv")

print("### dimension summary, sorted")
print(
    dim.sort_values(
        ["adapter_country", "eval_country", "gps_dimension"]
    ).to_string(index=False)
)

print("\n### weak/negative own-country dimension cells")
own_dim = dim[dim["adapter_country"] == dim["eval_country"]]
print(
    own_dim.sort_values("mean_reward_delta").to_string(index=False)
)
```

## 13. Optional Qualitative Evaluation

Only run this after metrics-only evaluation succeeds. It regenerates the combined
evaluation CSV with `generated_answer` populated.

```bash
!python DPO_anchored_pilot_experiment/run_experiment.py evaluate \
  --output-root "$OUTPUT_ROOT"

!python DPO_anchored_pilot_experiment/run_experiment.py summarize \
  --output-root "$OUTPUT_ROOT"
```

## 14. Artifact Locations

Main outputs:

```bash
!find "$OUTPUT_ROOT" -maxdepth 3 -type f | sort
```

Important files:

- `$OUTPUT_ROOT/results/reward_recovery_adapters_combined.csv`
- `$OUTPUT_ROOT/results/reward_recovery_adapter_summary.csv`
- `$OUTPUT_ROOT/results/reward_recovery_dimension_summary.csv`
- `$OUTPUT_ROOT/results/specialization_matrix_mean_reward_delta.csv`
- `$OUTPUT_ROOT/results/specialization_matrix_preference_accuracy.csv`
- `$OUTPUT_ROOT/results/own_vs_other_summary.csv`
- `$OUTPUT_ROOT/reports/run_report.md`
- `$OUTPUT_ROOT/adapters/dpo_qlora_adapter_llama3_ARG/`
- `$OUTPUT_ROOT/adapters/dpo_qlora_adapter_llama3_SWE/`
- `$OUTPUT_ROOT/adapters/dpo_qlora_adapter_llama3_USA/`
