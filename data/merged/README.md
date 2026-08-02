# SCA2 Tier-2 evaluation surfaces

Four country × survey **parquet** files for **frozen** USA / MEX DPO adapter out-of-sample evaluation.

## Start here

| File | What it is |
|------|------------|
| **`DATASET_GUIDE.md`** | Full documentation: selection criteria, limitations, **exact survey item wording**, intended use |
| **`01_merge_quality_and_usage.ipynb`** | Merge QA, exploratory moments, colleague load/benchmark recipe |
| `CONSTRUCT_MAP.md` | Compact GPS → WVS / AB construct map |
| `_manifest.json` | Per-wave coverage (machine-readable) |

## Data files

| Parquet | Content |
|---------|---------|
| `USA_WVS_wave7.parquet` | USA WVS7 (2017), pre-registered items |
| `MEX_WVS_wave7.parquet` | MEX WVS7 (2018), same items |
| `USA_Barometer_2012_2019.parquet` | USA AmericasBarometer 2012–2019, trust-core |
| `MEX_Barometer_2012_2019.parquet` | MEX AmericasBarometer 2012–2019, trust-core |

## Load

From repo root:

```python
from pathlib import Path
import pandas as pd
DATA = Path("data/merged")
usa_wvs = pd.read_parquet(DATA / "USA_WVS_wave7.parquet")
```

Requires: `pandas`, `pyarrow`. Optional plots: `matplotlib`, `seaborn`.

## Rules of use

- **Do not retrain** adapters on these surveys.
- **Do not** row-stack WVS with AmericasBarometer.
- Values are **raw** (no reverse-coding). Mask missing codes (88/98/…) before means.
- GPS is the in-sample identification instrument — not included here.

Lab rebuild (raw `.dta` required): `python _build_merge.py`
