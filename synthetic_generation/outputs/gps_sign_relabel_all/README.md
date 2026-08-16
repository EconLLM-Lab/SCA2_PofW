# GPS sign-relabel panel (all 76 countries)

**Status:** deterministic re-label of a shared synthetic A/B bank. No new LLM calls.

**For:** a multi-country DPO baseline Kseniia can train on immediately. Trim the country list later; do not treat this as a new generation run.

## What this is

The June 23 USA/MEX pipeline (`usa_mex_dpo_anchored_110_b6_c4_06232026`) already wrote **658 country-independent triplets**: each scenario has a fixed Response A (positive loading on the target GPS dimension) and Response B (negative loading). This export assigns those same 658 pairs to every country in Falk et al. (2018) `country_gps.dta` by the sign of that country's target-dimension z-score:

```
chosen = A  if  z_{c,k} >= 0
chosen = B  if  z_{c,k} <  0
```

`z == 0` is labeled A (non-negative). Magnitude is discarded. The 76 GPS countries all have complete six-dimension vectors, so the panel is rectangular:

| | count |
|---|---|
| Shared triplets | 658 |
| Countries | 76 |
| Rows | 50,008 |
| Rows with \|z\| < 0.10 | 12,388 |

On the original USA/MEX checkpoint this rule agrees with the LLM selector on **1,314 / 1,316** labels (99.85%). The two disagreements are both MEX patience at \(z = -0.11\).

## How to use a country file

Each `D_syn_{ISO3}.jsonl` is one JSON object per line. DPO training needs `prompt`, `chosen`, `rejected`.

```python
import json
from pathlib import Path

rows = [json.loads(line) for line in Path("D_syn_JPN.jsonl").read_text().splitlines()]
assert len(rows) == 658
assert {row["chosen_option"] for row in rows} <= {"A", "B"}
```

`gps_z_vectors.json` is the 76 × 6 anchor table used for labeling. `triplets_bank.jsonl` is the shared A/B bank with no country labels. `manifest.json` records the run id, the per-country sign pattern, and the source checkpoint.

## What this is not

- Not a new scenario/triplet generation. Every country trains on the **same 658 situations**.
- Not individual-level or distribution-matching data. The protocol still uses a point-estimate anchor.
- Not a fresh QC pass. `source_qc_status` and contamination fields are inherited from the USA/MEX scorer and rotated onto A/B; they are diagnostics, not admission.
- Not an identification claim. The object is an aggregate-anchor-induced preference pair.

## Regenerate

From `synthetic_generation/`:

```bash
python -m sca2_datagen.relabel \
  --checkpoint outputs/usa_mex_dpo_anchored_110_b6_c4_06232026/checkpoint_raw_pairs.jsonl \
  --output-dir outputs/gps_sign_relabel_all
```

The module is deterministic given the checkpoint and GPS vectors. Tests: `pytest tests/test_relabel.py`.
