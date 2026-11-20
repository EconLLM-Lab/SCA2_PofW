## Tier B (not run here)

`paper_a/reproduce_tables.py` rebuilds tables from option-probability CSVs.
Those CSVs are gitignored. There is no default public URL.

If you are on a lab machine with `data/phase2/raw/wvs/` already populated and
`data/wvs_eval_full/*.parquet` rebuilt from WVSA files:

```python
# not executed in this notebook
# !env -u PYTHONPATH python paper_a/reproduce_tables.py
```

This notebook does not need the Hugging Face adapters. They are public behind a gate (see `DATA.md`) and are
not required to check committed tables.
