# A Amendment C9 + numbers-table rebuild (old rows proved unchanged) + STATUS update

Card `t_b8060b80`, board sca2-paper-b, assignee `engineer`, status at export: done
Created 2026-10-19 16:42 MST. Exported 2026-10-19 by the CP assembly card as a dated record, not status.

## Body

FIRST read /Users/bonorinoa/.hermes/cache/scratch/c9_explore/common.md. Then read: the sca2-canonical-surface skill (Writing a claim-lock amendment), `planning/TWO_PAPER_CLAIM_LOCK.md` Amendments C7, C7.1 and C8 as format models, `paper_b/build_numbers_table.py`, and `results/c9/VERIFICATION_C9.md` from parent card V. Deadline 06:00 MST.

Only start if V passed. If V blocked, comment and block this card with V's findings.

1. **Fill the 4th TVD cell.** If C9-4's run `adapter-persona-strict-v1-20261019` is on the Hub and C9-2 left the adapter+persona cell pending, rerun `paper_b/c9_tvd.py` so the cell is filled.
2. **Extend the numbers table.** Add the C9 rows to `paper_b/build_numbers_table.py`: C9-1, C9-2, C9-4 and W1, every row labelled descriptive / not preregistered, with surface labels. Rebuild `NUMBERS_TABLE.csv`, then add a test proving that every pre-existing row (all 271 in sha `51ddcce1…97855`) is unchanged. Keep `test_rows_of_the_c71_table_are_unchanged_by_later_additions` green.
3. **Write Amendment C9.** Append it to `planning/TWO_PAPER_CLAIM_LOCK.md` (append only), dated 2026-10-20, "orchestrator under Augusto's delegation; coauthor sign-off pending". Include:
   - what was added and why: Paper B is the journal version and re-runs the preprint's human-agreement and distributional results on the frozen stack;
   - the estimand of each row;
   - the verifier's rulings on I1 and I2, with their caveats;
   - what C9 does NOT change: no claim earned, held-out stays retrospective, pre-piloting untested.
   Check every number quoted in the amendment against the new table with a script that rounds to printed precision.
4. **Update STATUS.md:** the new table hash and row count, headline rows for the new results (only claim ids that exist in the table), and the document map entry for `results/c9/`. `paper_b/test_status_doc.py` and the full suite must pass.
5. **Commit and merge.** Commit on `feat/paper-b-cohort` by explicit paths. Then merge into `paper/paper-b-draft` in the worktree `../SCA2_PofW-paper-b-draft`. Do not push.

## Runs

- run 74 engineer: done/completed  Amendment C9 applied: numbers table rebuilt to 536 rows (sha 9d56145d…642df) with the 271 earlier rows byte-identical and pinned by a test; amendment appended to the claim lock (dated 2026-10-20); STATUS.md and DECISIONS.md updated; committed 096e27b on feat/paper-b-cohort and merged into paper/paper-b-draft (f7afd21). Nothing pushed. C9-4 did not run, so it has no rows and no amendment claim.

## Comments

### default 2026-10-19 16:49

PM clarification for C9 amendment: producer cards done is NOT banked/accepted; await V. Do not say I1 establishes 'anchor not LM': low power of grouping and null results do not identify a primary bottleneck. Call human grouping inconclusive, and distinguish population-level simulations from realized between-share. W1 is behavioral factorial decomposition, not a neural mechanism. `Var(cross)/Var(full)` is a ratio, can exceed 1 through covariance, not an additive percentage explained. Own-only GPS alignment is mechanical for a positive coefficient on sign(z), not a new success test. Read V's final rulings before adding language. Actual bank size 658 TOTAL each, ~109–110/dimension; producer notification had a typo. Targeted tests independently run by PM: 18 passed (exit 0).

