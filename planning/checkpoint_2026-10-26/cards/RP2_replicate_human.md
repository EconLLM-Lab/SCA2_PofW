## RP2 · Replicate every Paper B result and table from banked inputs: human-criterion surfaces (engineer)

**Root:** `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW` (branch `feat/paper-b-cohort`, HEAD `79abcee` or
later). Card RP1 replicates the model-only surfaces in parallel; do not touch those.

**Why this card runs on the ASU Anthropic seat:** it reads licensed WVS/EVS data in `data/`. Read held-out human
data only through `paper_b/heldout/freeze.require_freeze()`. No respondent row, per-country human value or
model–human join may leave the machine, enter a commit, a report, a log line or a card comment.

**Scope (no GPU).** Every row of `planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv` whose result reads
human data: the retrospective screen (`SCR_*`, per-dimension `PD_*`), the sign-prompt screen arm (`SP_*`), the
comparators (`CMP_*`), readout robustness (`RO_*`, from `paper_b/heldout/readout_robustness.py`), the Tier-1 surface
rows that use the wave-6/7 ceiling, and C9 human agreement, grouping and TVD (`C9_a_*`, `C9_b_*`, `C9_c_*`,
`C9_TVD_*`, and any of `C9_d_*`, `C9_e_*`, `C9_f_*` or `PX_*` whose producing code reads `data/`). Read `paper_b/build_numbers_table.py` to map each row family to its result file.

**Steps (append to the report after each):**
1. **Manifest.** For each result file in scope, find its producing command in the result notes
   (`planning/sprint_2026-10-11/paper-b-tier1/results/*.md`, `results/c9/`, e.g. `SCREEN_RESULT_20261017.md`) or
   card texts. Write `planning/checkpoint_2026-10-26/replication/MANIFEST_human.md` (file → command → input paths
   and Hub run ids; no data values). A result with no recorded command is a finding.
2. **Re-run** each command with outputs redirected into
   `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.replication_2026-10-25/human/` (add the path to
   `.git/info/exclude`). Never overwrite a tracked result. If a script has no output flag, run a copy with a changed
   output path and record that. Fetch model-only Hub scores with your profile's `HF_TOKEN`; never print it.
3. **Compare** with `planning/checkpoint_2026-10-26/replication/compare_results.py` if RP1 has written it (reuse it;
   otherwise write `compare_results_human.py` with the same rules): exact for counts, `abs ≤ 1e-9` for floats,
   exact for seeded bootstraps and permutations re-run with the recorded seed. Rebuild the table rows in scope from
   the replicated files and compare row by row with the tracked table. Print only `0 mismatches` or mismatching
   claim ids.
4. **Classify** each mismatch (seed/environment with its size, missing command, real discrepancy). Edit nothing that
   is tracked.

**Artifact:** `planning/checkpoint_2026-10-26/replication/REPLICATION_human.md`, first line `RESULT: REPRODUCED |
REPRODUCED-WITH-NOTES | NOT-REPRODUCED`, then a table: row family, result file, command, rows compared, mismatches,
note. Before committing, grep the report and manifest for any number that is not a claim id's table value, a
count or a mismatch size. Commit the report, the manifest and any compare script by explicit path on
`feat/paper-b-cohort` (do not push). Never commit the replication dir.

**Fence:** do not edit `paper_b/` code, results, the claim lock or `STATUS.md`; do not touch `data/` except to read
it through the pipeline's own loaders. Commands at most about 3 minutes each; long ones go to a background process.

**Budget:** about 90 tool calls (your cap is 150).
