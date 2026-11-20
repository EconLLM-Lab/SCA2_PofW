# Third-party notices

The MIT license in [LICENSE](LICENSE) covers our code. It does not cover the material below, which stays under its
owners' terms.

## World Values Survey (WVS) question wording

Our model prompts restate WVS Wave 7 items. To make the prompts transparent, this repository includes the prompt text
we used: the standalone question stems we wrote for the 35 development items, the answer labels we edited, the 22
held-out stems we repaired by hand, and the prompt template. Much of it follows, or quotes, the WVS-7 Master
Questionnaire. The wording of the WVS instrument belongs to the World Values Survey Association.

Files that carry WVS-derived wording:

- `sca2/data/question_map_wvs_edited.csv` (stems and answer labels used in prompts; the verbatim questionnaire
  columns are removed, see `PUBLIC_REDACTIONS.md`)
- `paper_a/outputs/rung_mix/wvs_scoring_bundle.parquet` (the formatted prompts)
- `paper_b/heldout/pool_skeleton.csv`, `paper_b/heldout/pool_skeleton_at_prereg_tag.csv`,
  `paper_b/heldout/overrides.json`, `paper_b/heldout/face_valid.csv` (the held-out item pool, frozen by hash). These
  also carry the WVS-7 Stata variable labels (`VariableLabel`, `variable_label`) and endpoint answer labels, because
  the preregistered screen read them; changing the files would break the registered hashes.
- `paper_b/results/item_table/item_measurement_table.csv` (abbreviated wording)

The full questionnaire, the codebook and the respondent data are not included. Download them from
[worldvaluessurvey.org](https://www.worldvaluessurvey.org/WVSDocumentationWV7.jsp) (see [DATA.md](DATA.md)).
`paper_b/heldout/build_pool.py` rebuilds the held-out pool from those downloads.

Cite: Haerpfer, C., Inglehart, R., Moreno, A., Welzel, C., Kizilova, K., Diez-Medrano, J., Lagos, M., Norris, P.,
Ponarin, E. and Puranen, B. (eds.) (2022). *World Values Survey: Round Seven, Country-Pooled Datafile Version 6.0.0.*
Madrid and Vienna: JD Systems Institute and WVSA Secretariat. doi:10.14281/18241.24

## Global Preferences Survey (GPS)

The synthetic scenario bank carries only the sign (above or below the world mean) of each country's GPS score. No
country-level GPS values are included; claim-level correlations with GPS (one statistic per dimension, with its
interval) are. The Paper A PDF is reproduced as published on arXiv.

One GPS-derived fact is shipped on purpose: the Paper B near-zero results
(`paper_b/results/tier1/near_zero/`, `NEAR_ZERO_20261018.md`) name which dimensions of the two near-zero countries fall
below the near-zero threshold. Those cells are the design of the preregistered near-zero experiment, so the result
cannot be read without them. No GPS value is shipped with them. Cite Falk, A., Becker, A., Dohmen, T., Enke, B., Huffman, D. and Sunde, U. (2018). Global
Evidence on Economic Preferences. *Quarterly Journal of Economics* 133(4), 1645–1692. doi:10.1093/qje/qjy013

## Model outputs

Model probabilities and generated text come from Meta Llama 3.1 models and are subject to the
[Llama 3.1 Community License](https://www.llama.com/llama3_1/license/). Built with Llama.
