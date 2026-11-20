# Replication

This folder is the public front door. It does **not** retrain sixteen adapters.

## Two tiers

**Tier A (no extra data).** Confirm that committed analysis artifacts in git match `HASHES.md`. The headline file is `paper_a/outputs/paper_a/country_item_scores.csv` (16 countries, 27 items, 8 model arms; trust adapter-GPS = 0.744).

**Tier B (lab or licensed WVS).** Regenerate tables:

```bash
# frozen surface: 16 countries, 27 items, 8 model arms; no extra data
# 42-country human map: licensed WVS extracts under data/wvs_eval_full/
env -u PYTHONPATH .venv/bin/python paper_a/reproduce_tables.py
```

Option-probability zip posted 2026-09-17 (model outputs only). It is not required to reprint 0.744, and it is not the source of that number:

```
https://drive.google.com/uc?export=download&id=1lIAx0ueSpgaZPmAzNbFSD31ddGQH7Nqo
```

Set `SCA2_EVAL_URL` to that URL only if you want a local copy of those scoring files. Reprint the headline from the committed country–item scores.

Adapter weights are at Hugging Face `Bonorinoa/SCA2-phase2-adapters`, commit `03c43dfd27c9535283feb78ffa727da3bfa1b966`. A Hugging Face account and acceptance of the repository gate are required to download them. Reprinting the committed tables does not require them.

## Notebooks

| File | Job |
|---|---|
| [`evaluation.ipynb`](./evaluation.ipynb) | Tier A hash check; documents Tier B. |

## Environment (table regen only)

```bash
uv sync          # reads pyproject.toml + uv.lock (Python >= 3.14, 7-day cooldown pinned in pyproject)
```

The survey data are not shipped. See [`../../DATA.md`](../../DATA.md), or hand [`../../REPLICATE_WITH_AN_AGENT.md`](../../REPLICATE_WITH_AN_AGENT.md) to an agent.

This is the CPU analysis stack (pandas, scipy, pyarrow, matplotlib, pyreadstat, huggingface-hub, pytest). The GPU/DPO stack is the optional extra `gpu` (`uv sync --extra gpu`) and is meant for Colab.

## What this folder does not contain

WVS or GPS microdata. Adapter weights are not in this git tree. They are at Hugging Face `Bonorinoa/SCA2-phase2-adapters`, commit `03c43dfd27c9535283feb78ffa727da3bfa1b966`.

See [`ARXIV_GATES.md`](./ARXIV_GATES.md) for the remaining preprint checklist.

Data-generation and training notebooks are not part of this release. The scenario bank is in
`synthetic_generation/`, and adapters are on the Hugging Face Hub (see `DATA.md`).
