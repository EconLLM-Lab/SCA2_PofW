RESULT: REPRODUCED-WITH-NOTES

# Replication of Paper B, model-only surfaces (card CP26-RP1, t_bfaf8f2a)

Branch `feat/paper-b-cohort`, HEAD `6e69065`, run 2026-10-24 (MST). The numbers come out of the banked inputs: every one
of the 276 model-only rows of the 562-row `NUMBERS_TABLE.csv` was rebuilt from re-run result files and matches the
tracked row, with 0 mismatches. The notes are about what this does and does not show (section "Notes"), not about any
number that moved.

## What was done

1. **Manifest** (written before any re-run): `MANIFEST_model_only.md`, file to command to inputs.
2. **Inputs**: every model-only score file was fetched again from `Bonorinoa/SCA2-paper-b-artifacts` (read only, head
   `b8522a95…`), spec and adapter-revision checks run by the fetchers. The sha256 of every input that a tracked result
   JSON recorded (all 20 recorded hash entries, covering the score CSVs, the near-zero manifests and the GPS z file; the near-zero bank bundle also matches its pin, and the 42 label-recovery files match the concatenated hash the tracked result recorded)
   is identical to the fresh copy. The inputs are bit-identical to those of the banked runs.
3. **Re-run**: 10 producer commands, all exit 0, in a copy of the tree under `.replication_2026-10-25/model_only/rtree/`
   (path in `.git/info/exclude`). The only patch to the copies is the hard-coded `paper_b_inputs` directory in four
   scripts. The in-scope result files were deleted from the copy before the run, so nothing could be reused. No tracked
   file changed (`git diff HEAD -- paper_b planning/sprint_2026-10-11` is empty).
4. **Compare**: `compare_results.py`. Part 1 compares 23 re-run JSON and CSV files field by field with the tracked
   ones (about 20,000 fields). Part 2 rebuilds the numbers table with the copy's `build_numbers_table.py` and compares the 276
   in-scope rows column by column (floats exact for seeded-bootstrap families, 1e-9 elsewhere).
5. **Check that the comparison can fail**: I changed one float by 1e-6 and one count by 1 in the copy; the script
   reported 6 mismatching keys and exited 1. After restoring, it printed `0 mismatches`, exit 0.

Environment: Python 3.14.9, numpy 2.5.2, pandas 3.0.5, scipy 1.18.0, statsmodels 0.14.6 (repo `.venv`, run with
`env -u PYTHONPATH`).

## Results

Verification command (exit code captured without a pipe): 
`env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python planning/checkpoint_2026-10-26/replication/compare_results.py --show-size > <log>; echo $?` gives exit 0 and `0 mismatches`.

| Row family | Result file | Command | Rows compared | Mismatches | Note |
|---|---|---|---|---|---|
| `B2_*` (bank 2 and bank-to-bank) | `bank2_transport_strict.json` | `bank2_transport.py` (defaults) | 30 | 0 | Seeded bootstrap (20261011, 2000 draws), exact match, max diff 0. No recorded command: script defaults |
| `FX_*` (factorial, 64 cells) | `factorial/factorial_report.json`, `mtmm_adapter.csv`, `mtmm_signprompt.csv` | `analyze_factorial.py` then `factorial_report.py` | 58 | 0 | Recorded command. Max float difference in the files 2.8e-13 (BLAS order), far under 1e-9 |
| `FX26_*` (26-cell, superseded) | `factorial/factorial_report.json` | same two commands | 4 | 0 | Recorded command. Max file difference 7e-15 |
| `RP_*` (unseeded replicate) | `replicate/replicate_analysis.json` | `analyze_replicate.py` | 17 | 0 | Recorded command. Max difference 0. This replicates the analysis of the two banked runs, not the retrain |
| `NZ_*` (near-zero) | `near_zero/near_zero_analysis.json` | `analyze_near_zero.py` | 32 | 0 | Recorded command. Max difference 0. Reads the re-run `replicate_surface_diff.csv` as the noise floor, so it also checks the chain RP to NZ |
| `RO_*` (readout robustness) | `robustness/selection_heldout_{reverse,para_a,para_b}.csv` | `readout_robustness.py --go` | 9 | 0 | Selections rebuilt from the three variant runs (64 units x 223 items each); selected sets identical. No recorded command (docstring) |
| `PX_*` (persona and sign-prompt GPS rows) | `persona/persona_strict.json` | `persona_strict.py` | 46 | 0 | Seeded bootstraps, exact match. Replay checks pass (C1, B2, inputs, SP). No recorded command (docstring) |
| `C9_W1_*` | `c9/w1_why_trust.json` | `w1_crosstalk.py` | 66 | 0 | Max file difference 3e-15. No recorded command (docstring) |
| `C9_label_recovery_*` | `c9/c9_label_recovery.json` | `c9_label_recovery.py` | 8 | 0 | Seeded bootstraps, exact. The 42 log-prob files fetched again; recovery 0.9398, accuracy 0.8162, base accuracy 0.4894 as banked. No recorded command (docstring) |
| `HASH_*` | none (hashes of tracked files and git blobs) | `build_numbers_table.py` | 6 | 0 | Same working-tree bytes (copied), same git blobs and tag. The CRLF working-tree row depends on this Mac's checkout |
| **Total in scope** | 23 files | 10 commands | **276** | **0** | |

Left to RP2 (286 rows, only counted here): `SCR_*` (25), `PD_*` (27), `CMP_*` (10), `SP_*` (7), `C9_a_*` (21), `C9_b_*` (14),
`C9_c_*` (60), `C9_d_*` (21), `C9_e_*` (42), `C9_f_*` (9), `C9_TVD_*` (50). The producers of `SCR`, `PD`, `CMP`, `SP`
(`run_screen.py`, `analyze_heldout.py`, `per_dimension.py`) read the WVS-7 held-out criterion through
`freeze.require_freeze()`. `c9_human_agreement.py` reads human country means. `c9_tvd.py` reads the licensed
`population_response_distributions.csv`. 276 + 286 = 562, and no row was left unassigned. I did not open `data/`.

## Mismatches

None, so nothing to classify as seed or environment, a missing command or a real discrepancy. The only non-zero differences
(2.8e-13 in the factorial regression outputs, 3e-15 in W1) sit in unseeded linear algebra, are 4 to 6 orders of magnitude
under the 1e-9 bar, and do not reach the table (their rows compare at 0 within `FX_*`, and at 3e-15 for `C9_W1_*`).

## Notes (why this is REPRODUCED-WITH-NOTES and not REPRODUCED)

1. **Five families have no recorded command.** `B2_*`, `RO_*`, `PX_*`, `C9_W1_*` and `C9_label_recovery_*` appear in no
   result note or card with a command line. I ran the script defaults and docstring usage. They match the banked
   numbers, so the defaults give the banked numbers; the original invocations are still not on record. For `RO_*` the
   original driver was a scratch script that is not in the repo.
2. **The scores themselves were not re-made.** The scope was no GPU. This shows the tables and results follow from the
   banked Hub scores; it does not show that re-scoring the models gives the same scores. `provenance/ARCHIVE_PROVENANCE_20261018.md`
   already lists the rescore sensitivity as unquantified, and that has not changed.
3. **`factorial/bank_robustness.csv` is unverified.** It is tracked in the factorial folder but neither recorded command
   regenerates it (it needs `analyze_factorial.py` flags that no note records). The numbers table does not read it.
4. **The persona replay check is partly self-referential.** `persona_strict.py` compares its C1, B2 and SP values to the
   tracked `bank2_transport_strict.json` and `NUMBERS_TABLE.csv`. Its rows are recomputed from the CSVs, and the
   table rebuild is the independent check; the script's own pass line is not.
5. **`w1_crosstalk.py` reads the tracked `NUMBERS_TABLE.csv`** for its pin check. Its values come from the factorial
   regression of the fetched scores.
6. **Scope boundary.** `SP_*` rows are made from model-only sign-prompt scores, but every value is computed against the
   human criterion, so I left them to RP2.

## Reproduce

```
bash .replication_2026-10-25/model_only/fetch/fetch_all.sh        # Hub to inputs/ (read only; token from the profile .env)
env -u PYTHONPATH .venv/bin/python .replication_2026-10-25/model_only/fetch/fetch_nz_bank.py
bash .replication_2026-10-25/model_only/run_all.sh                 # 10 producers in rtree/, logs in logs/
env -u PYTHONPATH .venv/bin/python planning/checkpoint_2026-10-26/replication/compare_results.py
```

The replication directory is not committed (excluded in `.git/info/exclude`); the commit holds this report, the manifest
and `compare_results.py`.
