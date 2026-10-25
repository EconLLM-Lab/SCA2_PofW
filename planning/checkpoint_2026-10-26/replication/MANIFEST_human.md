# MANIFEST_human: producing commands for the human-criterion result files (card CP26-RP2)

Written before any re-run. No data values appear here: only file names, commands, input paths, Hub run ids
and hashes of design files. Repo HEAD when written: `6e69065` on `feat/paper-b-cohort`.

Scope = every `NUMBERS_TABLE.csv` row whose producing code reads `data/` or a local-only human file
(licensed WVS/EVS, GPS-joined human means, local population distributions). Rows come from
`paper_b/build_numbers_table.py`: `screen_rows`, `per_dimension_rows`, `comparator_rows`, `readout_rows`,
`c9_human_agreement_rows`, `c9_tvd_rows`. The other builder functions (bank 2, factorial, replicate, near-zero,
hash, persona, W1, label recovery) read no human data and belong to card RP1 (`t_bfaf8f2a`).

## How the re-runs are isolated

Every producer finds its inputs and outputs from `REPO = Path(__file__).parents[...]`. So the re-run uses a
mirror tree at `.replication_2026-10-25/human/tree/` (untracked, listed in `.git/info/exclude`):

- `paper_b/` is a copy of the tracked code (no edits).
- `data/`, `analysis/`, `synthetic_generation/` and `planning/sprint_2026-10-11/paper-b-20261011/` are symlinks
  to the real read-only inputs.
- `planning/sprint_2026-10-11/paper-b-tier1/results/` starts as a copy of the tracked results. The result files
  being replicated are deleted from the copy first, so a failed re-run cannot pass on a stale file.
- Each command is the recorded one, run with the tree's copy of the script, so its default output path lands in
  the tree. Nothing tracked is written.

## Result files and producing commands

| # | Result file (tracked) | Table rows | Producing command (as recorded) | Where recorded | Inputs | Hub run ids / hashes |
|---|---|---|---|---|---|---|
| 1 | `paper_b/heldout/screen_result.json` | `SCR_A_primary`, `SCR_p_perm`, `SCR_null_mean`, `SCR_null_q95` | `python paper_b/heldout/run_screen.py` | `results/SCREEN_RESULT_20261017.md` line 5; `results/TIER1_ANALYSIS_20261017.md` table | `paper_b/heldout/FREEZE.json` via `require_freeze()`; `data/WVS/WVS_wave7.dta`; `data/GPS/GPS_dataset_country_level/country_gps.dta`; frozen selection `selection_amended_20261016.csv`; pool `pool_skeleton.csv` | `bank2-heldout-v1-20261016` (spec `46447de6`) behind the frozen selection; selection sha `782b7d21` |
| 2 | `results/ceiling_heldout/{ceiling_items.csv,ceiling_sanity.json,ceiling_surfaces.csv,ts_crosswalk.json}` | feeds `SCR_ceiling_*`, `SCR_A_over_ceiling`, `SCR_one_third_ceiling` (through #3) | `paper_b/heldout/ceiling.py --items ceiling_heldout/items.json` (the `--out` value is not recorded; the tracked outputs sit in `results/ceiling_heldout/`) | `results/TIER1_ANALYSIS_20261017.md` line 10 | `results/ceiling_heldout/items.json`; `data/WVS/timeseries/WVS_Time_Series_1981-2022_stata_v5_0.dta`; `data/WVS/WVS_wave7.dta`; `analysis/phase2/outputs/paper_a/human_item_means_42.csv` (sanity only); `FREEZE.json` guard | none |
| 3 | `results/heldout_analysis.json`, `results/heldout_items.csv` | `SCR_*` (rest), `PD_*` (4 rows), `CMP_*`, `SP_*` | `python paper_b/heldout/analyze_heldout.py --signprompt-selection <path>` | table row in `TIER1_ANALYSIS_20261017.md`; `--signprompt-selection` value is not recorded, but the file `results/signprompt_selection_20261017.csv` carries the recorded sha `ed20902c…` | `FREEZE.json`; `paper_b/heldout/screen_result.json` (#1); `results/ceiling_heldout/ceiling_items.csv` (#2); `face_valid.csv`; `jev/majority_face_valid_jev.csv`; sign-prompt selection; WVS-7 and GPS through `run_screen.human_surface` | sign-prompt run `bank2-signprompt-heldout-v1-20261016` |
| 4 | `results/heldout_per_dimension.json` (note `HELDOUT_PER_DIMENSION_20261018.md`) | `PD_*` (23 rows) | `python paper_b/heldout/per_dimension.py` (defaults; seed 20261015, 2,000 bootstrap, 10,000 permutation draws; usage line in the script and the note) | `HELDOUT_PER_DIMENSION_20261018.md` header; `paper_b/heldout/per_dimension.py` docstring | same human inputs as #3; compares with #3 (`cross_check`) | as #3 |
| 5 | `results/robustness/selection_heldout_{reverse,para_a,para_b}.csv` | `RO_*` (9 rows; counts recomputed by the builder) | `python paper_b/heldout/readout_robustness.py --go`, which runs `build_probe_input.py --run-id <run> --spec-sha <pin> --out items_<v>.csv` then `probe_select.py --items items_<v>.csv --out selection_<v>.csv` | `readout_robustness.py` docstring. The note `READOUT_ROBUSTNESS_20261017.md` line 45 names an earlier `scratch/readout_robustness.py` (not in the repo) | Hub scores only; no human data (the builder compares with the frozen selection) | `bank2-heldout-reverse-20261016` (spec `d30bc4aa`), `bank2-heldout-para-a-20261016` (`cbd63283`), `bank2-heldout-para-b-20261016` (`0680dffb`) |
| 5b | `results/signprompt_selection_20261017.csv` (input of #3 and #4, not a table file) | none directly | `build_probe_input.py --arm signprompt` + `probe_select.py` | `TIER1_ANALYSIS_20261017.md` line 11 (arguments not recorded) | Hub scores | `bank2-signprompt-heldout-v1-20261016`, spec `46447de6`; selection sha `ed20902c…` |
| 6 | `results/c9/c9_human_agreement.json` (+ `.csv`) | `C9_a_*`, `C9_b_*`, `C9_c_*`, `C9_d_*`, `C9_e_*`, `C9_f_*` (167 rows) | `python paper_b/c9_human_agreement.py` (defaults: 2,000 bootstrap draws; seeds 20261011, 20260905; 10,000 permutations, seed 20261019) | script docstring; card `planning/checkpoint_2026-10-20/cards/t_c13b7536_*` (no command line, only file names) | `planning/sprint_2026-10-11/paper-b-20261011/model_probs.csv`; `/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/adapter_strict_v1.csv`; `analysis/phase2/outputs/paper_a/human_item_means_42.csv`; `synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json`; tracked `NUMBERS_TABLE.csv` (self-consistency check on `B2_bank2_*`) | cohort 1 `paper-b-20261011`; bank 2 `bank2-strict-v1-20261016` |
| 7 | `results/c9/c9_tvd.json` (+ `.csv`, `.md`) | `C9_TVD_*` (50 rows) | `env -u PYTHONPATH .venv/bin/python paper_b/c9_tvd.py [--draws N] [--no-fetch]` (the docstring form; the banked run used the defaults and the Hub fetch, because the adapter+persona cell is filled) | script docstring; card `t_f388a6cd_*`; reruns for the fourth cell are in card `t_b8060b80_*` | `model_probs.csv`; `planning/sprint_2026-10-11/paper-b-20261011/local_eval/population_response_distributions.csv` (local-only); `paper_b_inputs/persona_strict.csv`; Hub `runs/adapter-persona-strict-v1-20261019/synthetic/*_option_probabilities.csv`; GPS z | persona `persona-strict-v1-20261019`; `adapter-persona-strict-v1-20261019` (Hub fetch, needs `HF_TOKEN`) |
| 8 | `results/ceiling_{items,surfaces}.csv`, `results/ceiling_sanity.json`, `results/ts_crosswalk.json` | none (the pre-freeze battery ceiling, superseded for the screen by #2) | not recorded as a command; the script's usage line gives `python paper_b/heldout/ceiling.py --items strict --out <dir>` | `ceiling.py` docstring only | 23 battery items, same data files as #2 | none |

## Findings from the manifest step

1. No result file in scope lacks a producing script. Four lack a complete recorded command line:
   #2 (`--out` missing), #3 (`--signprompt-selection` value missing), #5b (arguments missing), #8 (only the usage
   line). For #3 the argument is fixed by the sha of the file the note names.
2. #5 names a driver that no longer exists (`scratch/readout_robustness.py`). The committed
   `paper_b/heldout/readout_robustness.py` is a different file; this replication runs the committed one's two
   steps with a cache directory inside the replication dir (its default cache is `/tmp/pb_scores`).
3. `c9_tvd.py` falls back to a token in another profile's `.env` (`HF_ENV`). This run supplies `HF_TOKEN` from the
   engineer profile through the environment, so the fallback is not read.
4. `c9_human_agreement.py` and `c9_tvd.py` read inputs from absolute paths outside the repo
   (`/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/`). They are local-only; the replication reads the same
   files. Their sha256 prefixes are checked against the hashes recorded in the result JSON where it records them.

## Commands as actually run (differences from the recorded ones)

All run from the mirror tree root with `env -u PYTHONPATH`, the repo `.venv` Python and `HF_TOKEN` from the
engineer profile's `.env` (set by `.replication_2026-10-25/human/runenv.sh`, never printed; `PYTHONDONTWRITEBYTECODE=1`).

| # | Run as | Difference from the recorded command |
|---|---|---|
| 1 | `paper_b/heldout/run_screen.py` | none; default `--out` lands in the tree |
| 2 | `paper_b/heldout/ceiling.py --items <results>/ceiling_heldout/items.json --out <results>/ceiling_heldout` | `--out` filled in (not recorded) |
| 3 | `paper_b/heldout/analyze_heldout.py --signprompt-selection <results>/signprompt_selection_20261017.csv` | the argument is the file regenerated in step 5b (not the tracked copy); ran in the background (over the three-minute guideline) |
| 4 | `paper_b/heldout/per_dimension.py` | none; ran in the background |
| 5 | per variant: `build_probe_input.py --run-id <run> --spec-sha <pin from score_plan_pins.json> --out items_<v>.csv --cache-dir <replication dir>` then `probe_select.py --items items_<v>.csv --out selection_<v>.csv` | the two steps of `readout_robustness.py` run directly, with a cache dir inside the replication dir instead of `/tmp/pb_scores` |
| 5b | `build_probe_input.py --arm signprompt --run-id bank2-signprompt-heldout-v1-20261016 --spec-sha <signprompt_heldout_v1 pin> ...` then `probe_select.py` | arguments chosen from the recorded run id and pin; the output is byte-identical to the tracked selection, which settles the choice |
| 6 | `paper_b/c9_human_agreement.py` | none |
| 7 | `paper_b/c9_tvd.py` | none (defaults; Hub fetch of the adapter+persona run) |
| 8 | `paper_b/heldout/ceiling.py --items strict --out <results>` | from the usage line |
