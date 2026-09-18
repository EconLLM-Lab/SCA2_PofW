## Tier B (not run here)

`analysis/phase2/reproduce_tables.py` rebuilds tables from option-probability CSVs.
Those CSVs are gitignored. There is no default public URL.

If you are on a lab machine with `data/phase2/raw/wvs/` already populated and
`data/wvs_eval_full/*.parquet` rebuilt from WVSA files:

```python
# not executed in this notebook
# !env -u PYTHONPATH python analysis/phase2/reproduce_tables.py
```

Do not point this notebook at Hugging Face adapters. That repo is private and is
not required to check committed tables.
