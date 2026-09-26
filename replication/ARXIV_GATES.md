# Paper supplement status

Headline surface is 16 countries × 23 items. Trust adapter–GPS is **0.74** [0.44, 0.88]. Do not quote 0.80.

The committed source of that number is `analysis/phase2/outputs/paper_a/country_item_scores.csv`. The file `country_item_scores_SUPERSEDED_stitched_20260925.csv` is the older USA/Mexico testing merge. It is kept so the change can be audited. It is not a paper result.

## Closed for this preprint

1. Omitting the country name closes a prompting channel. It does not erase pretrained associations.
2. Labels are GPS signs. Sixteen countries, thirteen sign profiles. Russia's holdout differs. Magnitudes do not enter the labels.
3. The trust result is coarse sign transfer on the nine-item map. Human agreement is unresolved.
4. The country-prompt comparison is in the results. Checkpoint parity was not established, so it is not an abstract claim.
5. Q43 and Q50 stay separate.
6. The Egypt numeric table that used the superseded score file is not part of the paper folder.
7. The USA/Mexico testing evaluation in `DPO_eval_WVS/eval_results_wvs_wave7/` was removed. Both waves of eight remain.
8. No funding. No competing interests. Confirmed by Augusto on 2026-09-25.
9. Adapter weights are released at `Bonorinoa/SCA2-phase2-adapters`, commit `03c43dfd27c9535283feb78ffa727da3bfa1b966`. Download requires a Hugging Face account and acceptance of the repository gate. Reprinting the committed tables does not require them.

## Not the paper supplement

- `DPO_eval_WVS/` holds scoring notebooks. It is not the result archive.
- The Drive zip posted 2026-09-17 is an earlier model-output archive. It is not the source of 0.74.
- Seminar notes under `misc/presentation/` are not the paper.

## Not required before posting

Retraining, a second contrast bank, and a matched anchor-prompt arm.
