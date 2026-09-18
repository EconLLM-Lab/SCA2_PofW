# Priority fixes before arXiv

Living list. Headline surface is 16 countries × 23 items; trust adapter–GPS = **0.80**.

## Closed in this freeze

1. Identification language: omitting country names closes a prompting channel. It does not identify human preferences or erase pretrained associations. **In the draft.**
2. Sign-only labeling, 13 profiles / 16 countries, Russia's different holdout. Magnitudes do not enter labels. **In the draft.**
3. DPO as reparameterized Bradley–Terry. GPS country scores are survey measures selected through experimental validation. **In the draft.**
4. One trust composite on the 16×23 rectangle (9 items, no Q69–Q71). Frozen in `analysis/phase2/outputs/paper_a/` and `reproduce_tables.py`. The older 30-item 0.78 table is superseded.
5. Egypt kept. Q69–Q71 reported on the 15-country subset and on the 42-country human map.
6. Q43/Q50 split everywhere.
7. Phi-4 contamination demoted to an unused diagnostic.
10. Public eval zip of option-probability CSVs. Cold fetch verified:
    https://drive.google.com/uc?export=download&id=1lIAx0ueSpgaZPmAzNbFSD31ddGQH7Nqo
11. Hugging Face adapters may stay private; the paper says weights are optional for table regen.

## Still open (paper polish, not new compute)

8. Figure/caption mismatches on leftover 30-item exhibits. The current draft's Figure 2 is the 16×23 associations plot.
9. SMR abstract ≤150 words when that venue is in play. Not required for arXiv.
12. Git history still contains old WVS/Barometer blobs. Do not rewrite history. A journal pack should use a fresh zip.
13. `profiling_and_datagen.ipynb` and `training.ipynb` remain optional protocol demos.

## Not required before a narrow preprint

Retraining 16 adapters; QC-gated bank; OpenRouter rewiring of the historical bank; operator-sensitivity GPU panel; flipping the whole Drive bucket public; making Hugging Face public (authors can flip `Bonorinoa/SCA2-phase2-adapters` when ready).
