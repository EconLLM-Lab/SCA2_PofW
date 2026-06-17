# Cost Estimate: Anchored Pilot Generator v2

Run the estimate before launching the full generator. The estimate does not call
the LLM endpoints; it uses the configured token assumptions and Hugging Face
endpoint hourly-rate defaults or environment overrides.

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

If the estimate is above budget, compare the lower-cost configuration:

```bash
python run.py \
  --estimate-only \
  --countries ARG SWE USA \
  --scenarios-per-dim 90 \
  --sample-sizes 300,400,500,600 \
  --sample-size-policy skip_unavailable \
  --use-anchors true \
  --output-dir outputs/anchored_pilot_v2
```

Interpretation:

- `--scenarios-per-dim 130` targets roughly 500 QC-passed rows per country under
  the current estimated QC pass rate.
- `--scenarios-per-dim 90` targets roughly 350 QC-passed rows per country and is
  the compute-constrained fallback.
- Nested exports (`300,400,500,600`) do not multiply LLM calls; they are local
  JSONL/HF/manifest writes after generation and QC.
- The main cost drivers are `scenarios_per_dim`, number of GPS dimensions, and
  number of countries.

After the budget is confirmed, run the full v2 generation:

```bash
python run.py \
  --countries ARG SWE USA \
  --scenarios-per-dim 130 \
  --sample-sizes 300,400,500,600 \
  --sample-size-policy skip_unavailable \
  --use-anchors true \
  --output-dir outputs/anchored_pilot_v2
```

Use the same command with `--scenarios-per-dim 90` if the lower-cost estimate is
selected. Do not add dimension balancing or per-dimension quotas in this sprint.
