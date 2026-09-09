# Priority fixes before arXiv

Living list after the 2026-09-08 methods review and public-repo hygiene pass.
Editorial score remains below 85 until the **paper** claim/figure pass lands. This file tracks what still gates that editing, and what can wait.

Status of **repo packaging** (this commit): public README matches the 16-country paper; survey extracts untracked; Finder copies removed; `replication/` is the front door; no inference; Drive/HF not flipped public.

## Still gates prose edits (do these in the paper, not more compute)

1. Narrow identification language. Omitting country names closes a prompting channel. It does not identify human preferences or erase pretrained associations.
2. State sign-only labeling, 13 profiles / 16 countries, and Russia's different holdout. Magnitudes in the profile do not enter labels.
3. Correct DPO as reparameterized Bradley–Terry (partition term cancels in pairwise comparisons). GPS country scores are survey measures selected through experimental validation, not directly incentivized choices.
4. One trust composite. Script 13 uses 12 items including Q69–Q71; the draft mapping table uses 9 items without them. Committed freeze is adapter–GPS trust **0.78**; the draft 16×23 figure is **0.80**. Pick one surface and freeze it in both tex and `reproduce_tables.py`.
5. Keep Egypt. Report Q69–Q71 on the 15-country subset as robustness (Q69 is the strongest human–GPS trust item). Do not let three not-asked items delete that map. GBR/Q174 is almost free.
6. Split Q43/Q50 everywhere (prose, tables, main figure).
7. Demote Phi-4 contamination to an unused diagnostic. No theory of the ratio. No gating.
8. Fix figure/caption mismatches (temperature vs response-scale chart; two-country vs multi-country matched-vs-cross). Restore pipeline figure + bibliography in the release PDF.
9. SMR abstract ≤150 words when that venue is in play. Not required for arXiv.

## Packaging still open (not paper prose)

10. **Publish a public eval zip** of option-probability CSVs only, then put the URL in `SCA2_EVAL_URL` and in the paper. Until a cold fetch works, the paper must not say “public Google Drive.”
11. Hugging Face adapters may stay private for arXiv if the paper says weights are optional for table regen.
12. History still contains the WVS/Barometer parquets that this commit untracks. Do not rewrite git history. A journal pack should use a fresh zip, not `git clone` of old blobs.
13. `profiling_and_datagen.ipynb` and `training.ipynb` are optional protocol demos. Evaluation notebook is enough to start editing.

## Not required before a narrow preprint

Retraining 16 adapters; QC-gated bank; OpenRouter rewiring of the historical bank; operator-sensitivity GPU panel; flipping the whole Drive bucket public.
