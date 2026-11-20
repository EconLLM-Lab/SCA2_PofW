# Paper supplement status

Headline surface is 16 countries × 23 items. Trust adapter–GPS is **0.74** [0.44, 0.88]. Do not quote 0.80.

The committed source of that number is `paper_a/outputs/paper_a/country_item_scores.csv`. That 16 × 23 surface is the arXiv v1 headline; the 16 × 27 count in the README is the full scored surface, which includes four extra items.

## Closed for this preprint

1. Omitting the country name closes a prompting channel. It does not erase pretrained associations.
2. Labels are GPS signs. Sixteen countries, thirteen sign profiles. Russia's holdout differs. Magnitudes do not enter the labels.
3. The trust result is coarse sign transfer on the nine-item map. Human agreement is unresolved.
4. The country-prompt comparison is in the results. Checkpoint parity was not established, so it is not an abstract claim.
5. Q43 and Q50 stay separate.
6. The Egypt numeric table that used the superseded score file is not part of the paper folder.
7. The superseded USA/Mexico testing evaluation was removed. Both waves of eight remain.
8. No funding. No competing interests. Confirmed by Augusto on 2026-09-25.
9. Adapter weights are released at `Bonorinoa/SCA2-phase2-adapters`, commit `03c43dfd27c9535283feb78ffa727da3bfa1b966`. Download requires a Hugging Face account and acceptance of the repository gate. Reprinting the committed tables does not require them.

## Not the paper supplement

- The retired phase-1 scoring notebooks were removed in the public-layout restructure; they are not the result archive.
- The Drive zip posted 2026-09-17 is an earlier model-output archive. It is not the source of 0.74.
- Seminar notes under `manuscripts/talks/` are not the paper.

## Not required before posting

Retraining, a second contrast bank, and a matched anchor-prompt arm.
