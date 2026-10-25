# Manifest: model-only result files of Paper B (card CP26-RP1, t_bfaf8f2a)

Written 2026-10-24 before any re-run. Branch `feat/paper-b-cohort`, HEAD `6e69065`. For each result file that
`paper_b/build_numbers_table.py` reads in the model-only scope: the command that produced it, and its inputs.
"Recorded" means a result note or card gives the command. "Docstring" means no note gives the command, so the
script's own usage line and its defaults are used; that is a finding (see the last section), not an invented command.

Hub: dataset `Bonorinoa/SCA2-paper-b-artifacts`. Hub head sha at fetch time: `b8522a95cad0f7781de2e7914904d43204df7fea`
(read only; nothing was written). The "revision" the notes pin for score files is the spec hash plus the adapter
revision in each run's manifests, plus the sha256 of each fetched file; those are the keys used below.

Pins (`paper_b/score_plan_pins.json`): `strict_v1` spec `ed3bb964…fbf6`; `heldout_v1` `46447de6…3b38`; adapter revision
`902f262e…3319ff3a1` (bank 2); near-zero adapter revision `c4b0f36e…8359131f`.

## Inputs (all fetched fresh from the Hub into `.replication_2026-10-25/model_only/`, none read from the old local cache)

| Input file | Hub run id (path) | Fetch command | sha256 (12) | Matches sha recorded in the tracked result JSON |
|---|---|---|---|---|
| `inputs/cohort1_strict.csv` | `paper-b-20261011` (`synthetic/<CC>_adapter_option_probabilities.csv`, 42) | `fetch_fact_inputs.py` | `047cd0e45959` | yes |
| `inputs/adapter_strict_v1.csv` | `bank2-strict-v1-20261016` (`synthetic/P_<bits>_adapter_…`, 64; manifest spec = strict pin) | `fetch_fact_inputs.py` | `3683d2211767` | yes |
| `inputs/signprompt_strict_raw.csv` | `sign-prompt-20261011` (26 profiles) | `fetch_fact_inputs.py` | not recorded | n/a |
| `inputs/signprompt_strict_64.csv` | `bank2-signprompt-strict-v1-20261018` (64, spec = strict pin) | `fetch_t6_inputs.py` | `bf05e0773973` | yes |
| `t6/replicate_strict_v1.csv` | `bank2-replicate-r1-strict-v1-20261018` (`P_1_0_1_1_0_1_adapter`) | `fetch_t6_inputs.py` | `104941fd6d0e` | yes |
| `t6/replicate_heldout_v1.csv` | `bank2-replicate-r1-heldout-v1-20261018` | `fetch_t6_inputs.py` | `0c48e9612722` | yes |
| `t6/original_heldout_unit.csv` | `bank2-heldout-v1-20261016` (unit `P_1_0_1_1_0_1`, held-out pool v1) | `fetch_t6_inputs.py` | `7aa8d19611d5` | yes |
| `inputs/near_zero/strict/{GBR,COL,GBR_control,COL_control}_strict.csv` | `bank2-nearzero-strict-v1-20261018` (spec = strict pin, adapter revision `c4b0f36e…`) | `fetch_nz_inputs.py` | `406bd10fc10b`, `aaf71beed39d`, `43db67bc8fac`, `407d37da16fe` | yes (all four) |
| `inputs/near_zero/{GBR,COL}/manifest.json` | `banks/near_zero_gps_sign_relabel_bank2_20261015_062543Z/near_zero_banks.tgz` (sha256 `816fe88d…bae68` = pin) | `fetch_nz_bank.py` | `68d1bcebebc8`, `a4ae5cd175a5` | yes |
| `inputs/persona_strict.csv` (+ `_base_parity.json`) | `persona-strict-v1-20261019` (`persona_<CC>`, 42; G3 base parity pass) | `paper_b/persona_strict.py --fetch` | `efd663a50af3` | yes |
| GPS z vectors | repo, `synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json` (tracked) | none | `02972f0ec4a8` | yes |
| label-recovery log-probs | `label-recovery-cohort1-v1-20261019` (`logps/<CC>.jsonl`, 42) | fetched inside `c9_label_recovery.py` | recorded `c31640a78d7f4831` (concat) | checked at re-run |
| readout variants | `bank2-heldout-{reverse,para-a,para-b}-20261016`, spec pins `d30bc4aa…`, `cbd63283…`, `0680dffb…` | fetched inside `build_probe_input.py` | spec checked by the script | spec pin enforced |

The fetch scripts are copies of the recorded fetchers `paper_b_inputs/fetch_{fact,t6,nz}_inputs.py` with output
paths and the `.env` path changed (sed; originals under `/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/`).
They read the token from the engineer profile `.env` and never print it.

## Commands per result file

All re-runs execute in a copy of the tree (`rtree/`: `paper_b/` copied, the two `synthetic_generation/outputs/gps_sign_relabel_*`
dirs symlinked, `results/` and `NUMBERS_TABLE.csv` copied). Every script resolves its output directory from its own
location, so a copy writes into the copy. One constant is patched in the copies: the hard-coded
`/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs` (in `bank2_transport.py`, `persona_strict.py`, `w1_crosstalk.py`,
`analyze_near_zero.py`) now points at the fresh inputs. No tracked file is touched.

| Row family | Result file(s) read by `build_numbers_table.py` | Producer and command | Command source |
|---|---|---|---|
| `B2_*` | `results/bank2_transport_strict.json` | `python paper_b/bank2_transport.py` (defaults: cohort1_strict.csv, adapter_strict_v1.csv, GPS json; 2000 draws, seed 20261011) | **Docstring only.** Note `BANK2_TRANSPORT_20261018.md` gives the seeds, not the command |
| `FX_*` | `results/factorial/factorial_report.json`, `factorial/mtmm_adapter.csv`, `factorial/mtmm_signprompt.csv` | `python paper_b/analyze_factorial.py --adapter adapter_strict_v1.csv --signprompt signprompt_strict_64.csv --out results/factorial`, then `python paper_b/factorial_report.py --adapter adapter_strict_v1.csv --signprompt-strict signprompt_strict_raw.csv --signprompt-strict-64 signprompt_strict_64.csv --results results/factorial` | Recorded: `results/REPLICATE_AND_PROMPT64_20261018.md` section 3 |
| `FX26_*` | `results/factorial/factorial_report.json` (`route_contrast_26_cells`) | same two commands as `FX_*` | Recorded (same note) |
| `RP_*` | `results/replicate/replicate_analysis.json` | `python paper_b/analyze_replicate.py --replicate-strict t6/replicate_strict_v1.csv --original-strict adapter_strict_v1.csv --replicate-heldout t6/replicate_heldout_v1.csv --original-heldout t6/original_heldout_unit.csv --out results/replicate` | Recorded: same note, section 3 |
| `NZ_*` | `results/near_zero/near_zero_analysis.json` | `python paper_b/analyze_near_zero.py --refit GBR=… --refit COL=… --control GBR=… --control COL=… --manifest GBR=… --manifest COL=… --baseline adapter_strict_v1.csv --noise results/replicate/replicate_surface_diff.csv --out results/near_zero` | Recorded: `results/NEAR_ZERO_20261018.md` section 6 |
| `RO_*` | `results/robustness/selection_heldout_{reverse,para_a,para_b}.csv` | `python paper_b/heldout/readout_robustness.py --go` (runs `build_probe_input.py --run-id … --spec-sha … --out items_<v>.csv`, then `probe_select.py --items … --out selection_<v>.csv`); selections deleted in the copy first because an existing file is kept | **Docstring only.** `READOUT_ROBUSTNESS_20261017.md` names an earlier `scratch/readout_robustness.py` that is not in the repo |
| `PX_*` | `results/persona/persona_strict.json` | `python paper_b/persona_strict.py` (after `--fetch`); exit 0 only if its replay checks pass | **Docstring only** (usage lines 17-18) |
| `C9_W1_*` | `results/c9/w1_why_trust.json` (and `factorial_report.json` for `n`) | `python paper_b/w1_crosstalk.py` | Docstring only; card `t_4a961051` names the script and outputs, not a command line |
| `C9_label_recovery_*` | `results/c9/c9_label_recovery.json` | `python paper_b/c9_label_recovery.py` (fetches the 42 jsonl from the Hub; 2000 draws) | Docstring only |
| `HASH_*` | none (hashes of tracked files and git objects: `paper_b/heldout/{pool_skeleton.csv,overrides.json,selection_amended_20261016.csv}`, `HEAD:` and tag `prereg-heldout-2026-10-14` blobs) | `build_numbers_table.py` itself (`hash_rows`) | Recorded in `ARCHIVE_PROVENANCE_20261018.md` (6 rows, "hashlib/git show") |

## Families left to RP2 (they read human data)

| Row family | Why it is not RP1 |
|---|---|
| `SCR_*` | read `paper_b/heldout/screen_result.json` and `heldout_analysis.json`; the producers (`run_screen.py`, `analyze_heldout.py`) score the probe against the WVS-7 criterion (human country means, held-out) through `freeze.require_freeze()` |
| `PD_*` | `heldout_per_dimension.json`, same human criterion (`per_dimension.py`) |
| `CMP_*`, `SP_*` | `heldout_analysis.json` (`s6_comparators`, `s8_signprompt`): contrasts of A, which is a correlation with the human criterion. The sign-prompt scores themselves are model-only, but every `SP_*` value is computed against the human criterion |
| `C9_a_*` .. `C9_f_*` | `c9_human_agreement.json`, adapter-human and human-GPS columns, built from the WVS-7 country distributions |
| `C9_TVD_*` | `c9_tvd.json`; `c9_tvd.py` reads `HUMAN_DISTS` (`local_eval/population_response_distributions.csv`, licensed, local only). The adapter-persona cell has no row (run not on the Hub) |

## Findings from the manifest step

1. Five of the ten row families (`B2_*`, `RO_*`, `PX_*`, `C9_W1_*`, `C9_label_recovery_*`) have no producer command in any
   result note or card (`HASH_*` is the builder itself). The re-runs use the script defaults and docstring usage lines.
   A match shows the defaults give the banked numbers; it does not show the original command line.
2. The original run for `RO_*` used a scratch driver that is not in the repo; the in-repo `readout_robustness.py` is a later rewrite.
3. `c9_label_recovery.py` and `c9_tvd.py` look for the token in the `sca` profile `.env` when `HF_TOKEN` is unset; this
   re-run sets `HF_TOKEN` in the environment instead.
4. `results/factorial/bank_robustness.csv` is tracked beside the factorial outputs but neither recorded factorial command
   regenerates it (it would need the `--cohort1` / `--variant` flags of `analyze_factorial.py`, whose values no note
   records). The numbers table does not read it, so it is outside the comparison; it stays unverified.
5. `persona_strict.py` replay checks read the **tracked** `NUMBERS_TABLE.csv` and the tracked `bank2_transport_strict.json`
   (`BANKED_C3`) as references, so its pass is a consistency check against banked rows, not an independent recomputation
   of those rows. The rows themselves are recomputed from the CSVs.
