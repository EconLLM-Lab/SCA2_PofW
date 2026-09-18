# WVS Wave 7 evaluation extracts (local rebuild)

These `{ISO3}_WVS_wave7.parquet` files are **licensed respondent extracts**. They are not redistributed in git.

Rebuild after you obtain `data/WVS/WVS_wave7.dta` from the World Values Survey Association and GPS country scores from Falk et al. / briq:

```bash
env -u PYTHONPATH .venv/bin/python data/wvs_eval_full/_build_wvs_eval_full.py
```

`_manifest.json` records countries and item coverage. `_build_wvs_eval_full.py` is the scientific object in this folder.
