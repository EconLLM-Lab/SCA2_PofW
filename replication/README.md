# Replication

This folder is the public front door. It does **not** retrain sixteen adapters.

## Two tiers

**Tier A (no extra data).** Confirm that committed analysis artifacts in git match `HASHES.md`. That is what GitHub currently can prove. The headline freeze is `analysis/phase2/outputs/paper_a/` (16×23; trust adapter–GPS = 0.80).

**Tier B (lab or licensed WVS).** Regenerate tables:

```bash
# frozen 16×23 adapter numbers: no extra data
# 42-country human map: licensed WVS extracts under data/wvs_eval_full/
env -u PYTHONPATH .venv/bin/python analysis/phase2/reproduce_tables.py
```

Option-probability zip (model outputs only; cold fetch verified 2026-09-17):

```
https://drive.google.com/uc?export=download&id=1lIAx0ueSpgaZPmAzNbFSD31ddGQH7Nqo
```

Set `SCA2_EVAL_URL` to that URL if you want a local copy of the scoring files. It is not required to reprint 0.80 from the frozen country–item scores.

Adapter weights on Hugging Face `Bonorinoa/SCA2-phase2-adapters` remain private until the authors flip that repository. They are optional for table regeneration.

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
