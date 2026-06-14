# Plan: Anchored Pilot Generator Run v2

## Goal

Produce the next anchored synthetic sample for DPO with enough rows to make
country-level specialization more stable and dimension-level diagnostics less
fragile, while preserving the current method: each triplet is anchored to one
target GPS dimension and is not explicitly balanced by dimension.

## Target Sample

- Countries: `ARG`, `SWE`, `USA`.
- Target export size: 400-600 QC-passed examples per country.
- Minimum acceptable export size if endpoint cost or QC pass rate is limiting:
  300 examples per country.
- Recommended nested exports: `300,400,500,600`, with
  `sample_size_policy=skip_unavailable`.
- Keep `--use-anchors true`.
- Keep the existing "one target dimension per triplet" design.
- Do not add dimension balancing, minimum per-dimension quotas, or per-country
  dimension quotas in this sprint.

Deferring dimension balancing is intentional. It would add another
methodological degree of freedom at the same time as we are increasing N. For
v2, the cleaner comparison is "same generator logic, larger sample." Minimum
quotas per `(country, gps_dimension)` cell should be considered in a future
sprint after we inspect the larger natural distribution.

## Suggested Run Configuration

From `synthetic_generation/`:

```bash
python run.py \
  --estimate-only \
  --countries ARG SWE USA \
  --scenarios-per-dim 130 \
  --sample-sizes 300,400,500,600 \
  --sample-size-policy skip_unavailable \
  --use-anchors true \
  --output-dir outputs/anchored_pilot_v2
```

Then run the full generation with the same arguments, without
`--estimate-only`:

```bash
python run.py \
  --countries ARG SWE USA \
  --scenarios-per-dim 130 \
  --sample-sizes 300,400,500,600 \
  --sample-size-policy skip_unavailable \
  --use-anchors true \
  --output-dir outputs/anchored_pilot_v2
```

Rationale: 130 scenarios per dimension gives 780 raw fixed triplets per
country before QC. With the current rough QC-pass assumption around 0.65, this
targets about 500 QC-passed rows per country. If the estimate looks too costly,
use `--scenarios-per-dim 90` to target roughly 350 rows per country.

## Reproducibility Requirements

Every exported JSONL row should be traceable without reading separate logs.
The current row format already contains the DPO-critical fields:

- `prompt`
- `chosen`
- `rejected`
- `country`
- `gps_dimension`
- rich metadata such as `z_value`, `contamination_ratio`, and
  `contamination_category`

For v2, add or verify the following low-risk metadata fields before export:

- `run_id`: stable identifier for this generator run, for example
  `anchored_pilot_v2_YYYYMMDD_HHMMSSZ`.
- `export_timestamp`: UTC timestamp for the export.
- `gps_profile_vector`: exact country GPS profile vector used for selection,
  preferably the same dict currently stored in the manifest under `countries`.
- `generator_config`: compact config snapshot or config hash. The full config
  can remain in the manifest, but the row should identify which run/config made
  it.

These fields should be additive only. Do not remove or rename existing fields,
because the DPO notebook expects `prompt`, `chosen`, `rejected`, and metadata
columns to remain available.

## Manifest Requirements

The manifest should make per-country inspection possible without loading all
JSONL files. Add or verify:

- `run_id`.
- `timestamp`.
- `sample_size`.
- `per_country_counts`.
- `per_dim_counts`.
- `per_country_dimension_counts`, shaped like:

```json
{
  "ARG": {"trust": 0, "risktaking": 0, "patience": 0, "altruism": 0, "posrecip": 0, "negrecip": 0},
  "SWE": {"trust": 0, "risktaking": 0, "patience": 0, "altruism": 0, "posrecip": 0, "negrecip": 0},
  "USA": {"trust": 0, "risktaking": 0, "patience": 0, "altruism": 0, "posrecip": 0, "negrecip": 0}
}
```

- `per_country_contamination_counts`, shaped by country and
  `low`/`medium`/`high`.
- `countries`, containing the exact GPS profile vector used for each country.
- `git_hash`.
- `config`.
- `cost_breakdown`.

## Low-Risk Generator Polish

These changes are useful but should stay small and output-compatible:

1. In `export.py`, compute `run_id` once per CLI run and add it to each JSONL
   row plus each manifest.
2. In `export.py`, add `per_country_dimension_counts` to the manifest using
   `groupby(["country", "gps_dimension"]).size()`.
3. In `export.py`, add `per_country_contamination_counts` using
   `groupby(["country", "contamination_category"]).size()`.
4. In `export.py`, write JSONL columns in a stable order with
   `prompt`, `chosen`, `rejected`, `country`, `gps_dimension`, `z_value`,
   `contamination_category`, and `contamination_ratio` near the front. Extra
   metadata can follow.
5. Optionally export DPO-ready train/eval JSONL splits alongside the full
   country JSONL files, using the same deterministic split seed as
   `DPO_anchored_pilot_experiment` (`seed=42`, `train_frac=0.80`). This is only
   a convenience for disconnected Colab use; it should not change the DPO
   training code or integrate training into the generator CLI.

## Handoff to DPO

After generation, copy or point `DPO_anchored_pilot_experiment` to the selected
v2 source files, for example the largest common available size:

- `synthetic_generation/outputs/anchored_pilot_v2/D_syn_ARG_500.jsonl`
- `synthetic_generation/outputs/anchored_pilot_v2/D_syn_SWE_500.jsonl`
- `synthetic_generation/outputs/anchored_pilot_v2/D_syn_USA_500.jsonl`

The DPO step should remain separate. Do not modify the DPO training code or
make the generator CLI launch DPO training.

## Acceptance Checks

- All selected country files exist and have the same per-country sample size.
- Every row has non-empty `prompt`, `chosen`, `rejected`, `country`, and
  `gps_dimension`.
- Every row has `run_id`, `export_timestamp`, `z_value`, and
  `gps_profile_vector`.
- Manifest includes per-country dimension counts and contamination counts.
- No explicit dimension balancing or quotas were applied.
- The selected files remain compatible with the current DPO notebook.
