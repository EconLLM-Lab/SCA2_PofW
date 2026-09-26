# Replication

This folder is the public front door. It does **not** retrain sixteen adapters.

## Two tiers

**Tier A (no extra data).** Confirm that committed analysis artifacts in git match `HASHES.md`. The headline file is `analysis/phase2/outputs/paper_a/country_item_scores.csv` (16×23; trust adapter–GPS = 0.74). Do not open the superseded stitch in that folder.

**Tier B (lab or licensed WVS).** Regenerate tables:

```bash
# frozen 16×23 adapter numbers: no extra data
# 42-country human map: licensed WVS extracts under data/wvs_eval_full/
env -u PYTHONPATH .venv/bin/python analysis/phase2/reproduce_tables.py
```

Option-probability zip posted 2026-09-17 (model outputs only). It is not required to reprint 0.74, and it is not the source of that number:

```
https://drive.google.com/uc?export=download&id=1lIAx0ueSpgaZPmAzNbFSD31ddGQH7Nqo
```

Set `SCA2_EVAL_URL` to that URL only if you want a local copy of those scoring files. Reprint the headline from the committed country–item scores.

Adapter weights are at Hugging Face `Bonorinoa/SCA2-phase2-adapters`, commit `03c43dfd27c9535283feb78ffa727da3bfa1b966`. A Hugging Face account and acceptance of the repository gate are required to download them. Reprinting the committed tables does not require them.

## Notebooks

| File | Job |
|---|---|
| [`evaluation.ipynb`](./evaluation.ipynb) | Tier A hash check; documents Tier B. |
| `profiling_and_datagen.ipynb` | Not written yet. Protocol demo only (user-supplied GPS `.dta`; toy bank). |
| `training.ipynb` | Not written yet. One-adapter Colab recipe. The 16-country run was not free-tier Colab. |

## Environment (table regen only)

```bash
python -m pip install -r replication/requirements-tables.txt
```

This is pandas/scipy/pyarrow. It is not the Colab DPO stack.

## What we will not ship here

WVS or GPS microdata; adapter weights.

See [`ARXIV_GATES.md`](./ARXIV_GATES.md) for the remaining preprint checklist.
