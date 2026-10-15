# Paper B scoring-stack freeze

Frozen 2026-10-11 by Augusto, after two T4 runs failed to reproduce the August base-on-CHN option probabilities. This file governs the scoring stack. It does not amend Paper A numbers in `TWO_PAPER_CLAIM_LOCK.md`.

## Decision

The August archive is not a bit-level reproduction target for Paper B. Paper A's published numbers stay the result of that run. Paper B is a new surface on the stack below. A later software image that does not match the August CSV within 0.01 log probability is a recorded stack difference, not a failed cohort.

Do not widen the old 0.01 / 0.0001 tolerance and call the archive check passed. Do not spend another session hunting the unpinned August environment.

## Frozen stack (verified on pb-gate2, 2026-10-11)

| Piece | Value | How known |
|---|---|---|
| Base model | `meta-llama/Llama-3.1-8B-Instruct` | Hub name used by the gate |
| Base revision | `0e9e39f249a16976918f6564b8830bc894c89659` | Hub `model_info` the same day; last weight-side commit 2024-09-25 |
| Adapter repo | `Bonorinoa/SCA2-paper-b-adapters` | Existing cohort |
| Adapter revision | `7550fd4cfe514470bb8d80918a43c9ae424d26b5` | Parent read of 42 run records |
| Python | 3.13.15 | Printed by the 2026-10-11 scoring launch |
| transformers | 4.46.3 | Printed by the install cell |
| peft | 0.14.0 | Printed by the install cell |
| huggingface_hub | 0.36.2 | Install pin; not re-printed |
| datasets / accelerate / trl | 2.21.0 / 0.34.0 / 0.14.0 | Install pin; not re-printed |
| bitsandbytes | 0.50.2 | Printed by the 2026-10-11 scoring launch |
| torch | 2.11.0+cu130 | Printed by the 2026-10-11 scoring launch |
| CUDA | 13.0, driver 580.82.07, Tesla T4 | Printed by the 2026-10-11 scoring launch |
| Chat date pin | `26 Jul 2024` | `eval_config.ARCHIVE_CHAT_DATE`; formatted prompts matched the archive |
| Loader | notebook form: no forced fast tokenizer, no `torch_dtype`, `device_map="auto"`, 4-bit NF4, fp16 compute, double quant | `score_cohort.load_base_model_and_tokenizer` after the 2026-10-11 patch |
| Readout | leading-space option code, temperature 1, no length normalization, no country name in the primary prompt | `eval_config.py` |

Those versions were printed by the scoring launch on 2026-10-11 and are now closed. Do not substitute a later image without a new freeze.

## What the gate is now

Before any cohort score:

1. Same frozen adapter weights through the production switch path and an independent loader.
2. Disable the adapter and recover the base readout on the same process.
3. Primary prompt contains no country name.
4. Option probabilities are finite and sum to one.
5. The run record carries the frozen adapter revision, bank id, and the package versions above.

An archive log-probability mismatch is reported, not a stop condition.

## What this freeze does not allow

- Quoting a new 42-country correlation as a bit-level extension of the locked 0.74.
- Scoring until the same-weights adapter check has passed.
- Uploading respondent files or model–human tables to Hugging Face.
