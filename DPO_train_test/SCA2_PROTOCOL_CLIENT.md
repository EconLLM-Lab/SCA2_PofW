# Optional protocol client (do not replace Drive paths)

The existing Colab notebooks remain the GPU path. This file is a
copy-paste cell you can add **above** the hard-coded constants if you
want to read a frozen `sca2 train` / `sca2 eval` plan instead.

Do not delete `DATA_DIR = Path("/content/drive/MyDrive/DPO")`.
Run All on the old notebooks must still work without this cell.

## Train notebook (`DPO_train.ipynb`)

```python
# OPTIONAL — protocol client. Skip this cell to keep Drive paths.
# Requires the repo root on PYTHONPATH (or %cd to SCA2_PofW).
from pathlib import Path
from sca2.notebook import labeled_file, load_plan, to_iso3, train_knobs

PLAN = Path("runs/<run_id>/train_plan.json")  # from `python -m sca2 train`
plan = load_plan(PLAN)
knobs = train_knobs(plan)

RUN_COUNTRY = "USA"                 # ISO3; "US" also works
DATA_COUNTRY_CODE = to_iso3(RUN_COUNTRY)
ADAPTER_TAG = DATA_COUNTRY_CODE
RAW_FILE = labeled_file(plan, RUN_COUNTRY)
MODEL_NAME = knobs["MODEL_NAME"]
TRAIN_FRAC = knobs["TRAIN_FRAC"]
SEED = knobs["SEED"]

print("protocol client")
print("  model   ", MODEL_NAME)
print("  beta    ", knobs["beta"], "lora_r", knobs["lora_r"])
print("  raw     ", RAW_FILE)
print("  execute ", knobs["execute"], "(False means plan only)")
```

Then keep using the notebook's existing split / DPO cells. Point
`DATA_FILE` at a local copy of `RAW_FILE` if you are not on Drive.

## Eval notebooks

```python
# OPTIONAL — protocol client for the WVS item map.
from pathlib import Path
from sca2.notebook import eval_claim, load_plan

PLAN = Path("runs/<run_id>/eval_plan.json")  # from `python -m sca2 eval`
plan = load_plan(PLAN)
print(plan["surface"], plan["n_mapped"], "mapped items")
print(eval_claim(plan))
```

`matched_vs_cross_means` is `fixed_policy_proximity`. Do not write
"the adapter knows Mexico" from a TVD table.
