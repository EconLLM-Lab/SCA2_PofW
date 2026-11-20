# paper_a/inputs

`model_option_probs.csv` holds model outputs only: `arm, country, question_id, option_value, model_prob`. It has no
human column and no value derived from survey respondents. `tvd_rebuild.py` joins it with your own WVS and GPS
downloads to rebuild the per-cell model-to-human distance (see [DATA.md](../../DATA.md)).

- Rows: 12,250. Arms: `adapter`, `adapter_persona`, `base`, `base_fixed_USA`, `persona`. 428 (country, item) cells per
  arm (16 countries, 27 items), full float precision, one row per option, sorted by arm, country, item, option value.
- sha256: `1b57a585c4e790689fceaadee651f2a5c2d79f1b4637b83ea39a18d903a3cd11` (pinned in `paper_a/tests/test_tvd_rebuild.py`).
- The other three arms (`armA`, `armB`, `uniform`) are not stored: they are computed from the GPS file and the option grid.

## Provenance

Built by `paper_a/build_model_option_probs.py` (lab-only; needs the raw eval outputs). Free-text numeric items
(`is_numeric_open`) are excluded, and rows are restricted to the cells of the frozen score table.

| Arm | Source (under `data/phase2/raw/wvs/`, `<bank>` = `ksenias_base8` for CHN JPN GBR USA MEX ARG DEU RUS, `co2_8` for IND IDN NGA EGY TUR NLD BRA GRC) |
|---|---|
| `adapter` | `<bank>/model_option_probabilities_<CC>_adapter_on_<CC>.csv`, rows with `eval_country == CC` |
| `base` | `<bank>/model_option_probabilities_base_on_<CC>.csv`; **USA and MEX** from git history instead (below) |
| `base_fixed_USA` | the USA base file from git history, repeated for every country |
| `persona` | `persona_baseline/model_option_probabilities_persona_base_on_<CC>.csv` |
| `adapter_persona` | `persona_adapter/model_option_probabilities_<CC>_adapter_persona.csv`; these files repeat option rows, so duplicates on `option_value` are dropped (first kept) |

Git-history extraction: `git show a2eb08b:DPO_eval_WVS/eval_results_wvs_wave7/model_option_probabilities_base_on_{USA,MEX}.csv`
(commit a2eb08b, 2026-08-04, "Add evaluation notebooks and result tables"). The raw USA/MEX base files differ from
these, and the frozen scores were computed from the history versions.
