# Replication

This folder is the public front door. It does **not** retrain sixteen adapters.

## Two tiers

**Tier A (no extra data).** Confirm that committed analysis artifacts in git match `HASHES.md`. That is what GitHub currently can prove.

**Tier B (lab or post-publication pack).** Regenerate tables from option-probability CSVs + locally rebuilt WVS extracts:

```bash
# after licensed WVS extracts exist under data/wvs_eval_full/
# and eval banks exist under data/phase2/raw/wvs/  OR  SCA2_EVAL_URL is set
env -u PYTHONPATH .venv/bin/python analysis/phase2/reproduce_tables.py
```

There is **no** public eval zip and **no** public adapter dump as of this commit. Do not write that into a paper until a URL fetches without authentication.

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

WVS or GPS microdata; adapter weights; the gitignored `data/phase2/raw/` banks until a dedicated public zip exists.

See [`ARXIV_GATES.md`](./ARXIV_GATES.md) for the remaining preprint checklist.
