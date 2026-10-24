## RV · Independent check of the replication (verifier, cross-family)

**Root:** `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW`. Cards RP1 and RP2 (engineer, Claude) replicated
the Paper B results; you are a different model family on purpose.

**You may not open `data/` or `.replication_2026-10-25/human/`** (licensed human data; your route is not
ASU-approved for it). For the human surfaces you check the method, not the values.

**Check, appending each result to the review file:**
1. **Coverage.** Every `claim_id` in `planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv` falls in exactly
   one of RP1's or RP2's row families, or is listed as out of scope with a reason (for example a design constant).
   Write your own short script for this in `planning/checkpoint_2026-10-26/replication/probes_rv/`.
2. **Model-only values, re-derived.** Pick three model-only row families from RP1 (one must be `C9_W1_*` or the
   factorial, one `C9_label_recovery_*`). From the files in `.replication_2026-10-25/model_only/` and the Hub
   inputs RP1's manifest names, recompute their table rows with your own code (not RP1's compare script) and compare
   them with the tracked table. Print only `0 mismatches` or the keys. Use the `HF_TOKEN` in your profile `.env` only
   if you must fetch; never print it.
3. **Commands are the real ones.** For six manifest entries (three per card), confirm the command matches the
   producing command recorded in the result note it cites, and that the replication ran the tracked code at the
   recorded commit or says why not.
4. **Compare scripts are honest.** Read `compare_results*.py`: tolerances as briefed, no silent skip of a missing
   file, mismatches cannot be swallowed. Mutation test: copy one replicated model-only file, change one value, run
   the compare script on the copy, confirm it reports the mismatch.
5. **Nothing leaked.** The committed replication files contain no respondent rows and no per-country human values;
   `git log -p` of the RP1/RP2 commits adds nothing under `data/` and nothing from `.replication_2026-10-25/`.
6. **Verdicts follow from the evidence.** Each card's RESULT line matches its own table.

**Artifact:** `planning/checkpoint_2026-10-26/replication/REPLICATION_VERIFICATION.md`, first line `VERDICT: PASS |
PASS-WITH-NOTES | BLOCK`, findings with file:line. Do not edit or commit anything else; the PM commits your file.

**Budget:** about 60 tool calls.
