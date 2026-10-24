## RP1 · Replicate every Paper B result and table from banked inputs: model-only surfaces (engineer)

**Root:** `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW` (branch `feat/paper-b-cohort`, HEAD `79abcee` or
later). Card RP2 replicates the surfaces that read human data, in parallel; do not touch those.

**Goal.** Show, by re-running the code, that the paper's numbers come out of the banked inputs. Augusto asked for a
replication of the results and tables that made the paper before the 2026-10-26 checkpoint. The tables in
`misc/paper_b/tables/` and the supplement are tied to `NUMBERS_TABLE.csv` by `\cl`/`\ci` macros, so reproducing the
table rows reproduces the tables.

**Scope (no GPU, no Colab: re-scoring is out of scope and needs Augusto's go).** Every row of
`planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv` produced from **model-only** inputs: bank 2 and
bank-to-bank (`B2_*`), the factorial and W1 (`FX_*`, `FX26_*`, `C9_W1_*`), the replicate (`RP_*`), near-zero
(`NZ_*`), persona and sign-prompt model-only rows (`PX_*` that do not read humans), label recovery
(`C9_label_recovery_*`), hash rows (`HASH_*`). Read `paper_b/build_numbers_table.py` to map each row family to the
result file it reads. The table's prefixes are SCR, PD, CMP, SP, RO, B2, FX, FX26, RP, NZ, HASH, PX, C9_a to C9_f,
C9_TVD, C9_W1, C9_label. A family whose producing code reads `data/` (including any of C9_d, C9_e, C9_f, or PX rows
that do) belongs to RP2; say in your report which families you left to RP2 and why.

**Steps (append to the report after each):**
1. **Manifest.** For each result file that `build_numbers_table.py` reads in your scope, find its producing command
   in the result notes (`planning/sprint_2026-10-11/paper-b-tier1/results/*.md`, `results/c9/`) or the card texts
   (`planning/checkpoint_2026-10-20/cards/`, `paper-b-tier1/cards/`). Write
   `planning/checkpoint_2026-10-26/replication/MANIFEST_model_only.md`: file → command → inputs (Hub run id and
   revision, local paths). A result with no recorded command is a finding, not a reason to invent one.
2. **Inputs.** Fetch model-only scores from the Hub (`Bonorinoa/SCA2-paper-b-artifacts`, `runs/<run_id>`, the
   revisions the notes pin) with the `HF_TOKEN` in your profile `.env`; never print it. Never write to the Hub.
3. **Re-run** each command with outputs redirected into
   `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.replication_2026-10-25/model_only/` (create it; add the
   path to `.git/info/exclude`, not `.gitignore`). Never overwrite a tracked result file. If a script has no output
   flag, copy it to the replication dir and run the copy with a changed output path, and record that.
4. **Compare.** Write `planning/checkpoint_2026-10-26/replication/compare_results.py`: for each re-run file vs its
   tracked counterpart, compare every numeric field (exact for counts and hashes; `abs ≤ 1e-9` for floats unless
   the result comes from a seeded bootstrap that was re-run with the same seed, which must match exactly). Then
   rebuild the numbers table from the replicated files (run `build_numbers_table.py` against a copy of the tree, or
   with patched paths, writing to the replication dir) and compare it row by row, in your scope, with the tracked
   562-row table. Print only `0 mismatches` or the mismatching keys, never rows.
5. **Classify** each mismatch: seed/environment (show the size), a missing command, or a real discrepancy. Do not
   edit any tracked result, the table, or code that produced a banked run.

**Artifact:** `planning/checkpoint_2026-10-26/replication/REPLICATION_model_only.md`, first line
`RESULT: REPRODUCED | REPRODUCED-WITH-NOTES | NOT-REPRODUCED`, then a table: row family, result file, command, rows
compared, mismatches, note. Plus the manifest and `compare_results.py`. Commit those three files by explicit path
on `feat/paper-b-cohort` (do not push). Never commit the replication dir.

**Fence:** do not open `data/` (RP2 owns the human surfaces). Do not edit `paper_b/` code, results, the claim lock
or `STATUS.md`. Commands at most about 3 minutes each; long ones go to a background process with a log.

**Budget:** about 90 tool calls (your cap is 150). Append to the report after each row family.
