RESULT: REPRODUCED-WITH-NOTES

# Replication of Paper B, human-criterion surfaces (card CP26-RP2, t_536cff76)

Branch `feat/paper-b-cohort`, HEAD `6e69065`, run 2026-10-24 (MST) on the ASU Anthropic seat. Every producer in scope was
re-run from its local inputs and, for the model-side scores, from the Hub. Outputs went to an untracked mirror tree
(`.replication_2026-10-25/human/tree/`, listed in `.git/info/exclude`), after the result files being replicated had been
deleted from the tree's copy. Nothing tracked was written. Commands, inputs and run ids are in `MANIFEST_human.md`.

**Verdict.** All 295 table rows that read human data were rebuilt from the re-run files and agree with the tracked
table: 0 mismatches, same order, same keys. All 20 re-run result files are also byte-identical to the tracked ones.
The `-WITH-NOTES` is for four documentation gaps and three limits on what "reproduced" means here (below). None is a
mismatch.

Comparator: `compare_results_human.py` (same rules as RP1's `compare_results.py`, whose `Diff` and `read_any` it reuses).
Output of `env -u PYTHONPATH .venv/bin/python planning/checkpoint_2026-10-26/replication/compare_results_human.py --show-size --self-test`:
exit code 0, last line `0 mismatches`. Its self-test (a perturbed float, a dropped row, a changed count, a float
differing by 1e-12 under the exact rule) was detected. A second test on a copy of the tree (one value of
`screen_result.json` moved by 1e-12, one file deleted) reported exactly three keys (the moved field, the deleted file and the one table row
that reads the moved value) and exited 1.

## Results by row family

Rule: exact for counts, strings, seeded bootstraps and permutations re-run with the recorded seed; `abs <= 1e-9` for the
deterministic wave-6/7 ceiling rows and the readout Pearson rows. The largest difference seen anywhere was zero.

| Row family | Result file | Command (as run) | Rows compared | Mismatches | Note |
|---|---|---|---|---|---|
| `SCR_*` | `paper_b/heldout/screen_result.json`, `heldout_analysis.json`, `heldout_items.csv` | `run_screen.py`; `analyze_heldout.py --signprompt-selection <regenerated selection>` | 25 | 0 | `SCR_ceiling_*`, `SCR_A_over_ceiling`, `SCR_one_third_ceiling` read the re-run wave-6/7 ceiling (family "Tier-1 rows using the ceiling") |
| `PD_*` | `heldout_per_dimension.json` (4 rows come from `heldout_analysis.json`) | `per_dimension.py` | 27 | 0 | the script's own cross-check against `heldout_analysis.json` also holds |
| `CMP_*` | `heldout_analysis.json` | `analyze_heldout.py` | 10 | 0 | comparator route with Amendment 2 exclusions |
| `SP_*` | `heldout_analysis.json` | `analyze_heldout.py` | 7 | 0 | sign-prompt arm, from the regenerated sign-prompt selection |
| `RO_*` | `robustness/selection_heldout_{reverse,para_a,para_b}.csv` | `build_probe_input.py` + `probe_select.py` per variant (the two steps of `readout_robustness.py`) | 9 | 0 | model-side only, re-fetched from the Hub; also counted by RP1 |
| `C9_a_*` | `c9/c9_human_agreement.json` | `c9_human_agreement.py` | 21 | 0 | |
| `C9_b_*` | same | same | 14 | 0 | |
| `C9_c_*` | same | same | 60 | 0 | grouping permutation and power rows, recorded seeds |
| `C9_d_*` | same | same | 21 | 0 | sign-mate agreement (labelled not a ceiling) |
| `C9_e_*` | same | same | 42 | 0 | |
| `C9_f_*` | same | same | 9 | 0 | |
| `C9_TVD_*` | `c9/c9_tvd.json` | `c9_tvd.py` (Hub fetch of the adapter+persona run) | 50 | 0 | all four cells report status ok |
| Inputs, no table row | `ceiling_heldout/*`, top-level `ceiling_*`, `ts_crosswalk.json`, `signprompt_selection_20261017.csv` | `ceiling.py` (held-out items; strict battery), `build_probe_input.py --arm signprompt` + `probe_select.py` | files only | 0 | byte-identical; the regenerated sign-prompt selection carries the sha the Tier-1 note records |
| **Total in scope** | 20 files | | **295** | **0** | |

Coverage: RP1 reports 276 rows and RP2 295; they share the 9 `RO_*` rows, so the two cards together cover all 562
rows of the table (the 276 + 295 − 9 count is checked by claim id in a script, with no row left over).

## Classification of mismatches

None to classify: no seed or environment difference, no real discrepancy.

## Notes (documentation gaps, not mismatches)

1. **Four result files have no complete recorded command.** `ceiling_heldout/` (the note gives `--items` but not
   `--out`); `heldout_analysis.json` (the note gives no value for the required `--signprompt-selection`; the file the
   note's sha names reproduces byte for byte); `signprompt_selection_20261017.csv` (arguments not recorded; the
   run id and pin from `FREEZE.json` and `score_plan_pins.json` reproduce it byte for byte); the pre-freeze battery
   ceiling files at the top of `results/` (only the script's usage line). No file lacks a producing script.
2. **Readout robustness driver.** `READOUT_ROBUSTNESS_20261017.md` names `scratch/readout_robustness.py`, which is not
   in the repo. The committed `paper_b/heldout/readout_robustness.py` was not run as is, because its cache dir is
   `/tmp/pb_scores` (a stale cache could pass for a fresh fetch). Its two steps were run with a clean cache dir. The
   outputs equal the tracked ones, so the two drivers agree on this data.
3. **Token fallback in `c9_tvd.py`.** The script reads a token from another profile's `.env` when `HF_TOKEN` is unset.
   This run set `HF_TOKEN` from the engineer profile, so that fallback was not used. The script's own header and the
   recorded note both say "default fetch"; the fourth cell needs the Hub.

## Limits of what "reproduced" means here

- **Same machine and stack.** Byte identity on one host shows the code, inputs and seeds are deterministic. It does not
  test another platform or library version.
- **Local human inputs were read, not re-derived.** The pipeline starts from `analysis/phase2/outputs/paper_a/human_item_means_42.csv`,
  `planning/sprint_2026-10-11/paper-b-20261011/local_eval/population_response_distributions.csv` and the WVS/GPS `.dta`
  files. The screen, the ceiling and the held-out analyses read the `.dta` files directly through `require_freeze()`. The
  two local derived files were not rebuilt from raw respondent data (that step is outside this card). The ceiling
  script's sanity output (Time-Series wave-7 means against `human_item_means_42.csv`) is byte-identical to the tracked one.
- **The model-side Hub scores were re-fetched, the GPU scoring was not re-run.** Re-scoring is a separate decision.

## Data-exposure check

Nothing under `data/` was opened outside the pipeline's own loaders; no respondent row, per-country human value or
model–human join was printed, logged, committed or commented. The comparator prints counts and sizes only. The replication
dir is untracked. One flag for the data steward, not a replication finding: the tracked `results/heldout_items.csv`
holds one human-derived agreement statistic per held-out item (an aggregate over 42 countries, no per-country value). It
is an aggregate of the kind the claim lock allows, but it is a model–human join at item level and belongs on the
pre-sharing review list.

## Reproduce

1. `.replication_2026-10-25/human/` holds the mirror tree, `runenv.sh` and logs (local, untracked). It can be rebuilt from
   `MANIFEST_human.md`.
2. `env -u PYTHONPATH .venv/bin/python planning/checkpoint_2026-10-26/replication/compare_results_human.py --show-size --self-test`
