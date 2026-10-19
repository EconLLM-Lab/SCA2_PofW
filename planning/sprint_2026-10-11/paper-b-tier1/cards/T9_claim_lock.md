## Card T9 — Claim-lock amendment (checkpoint C7): draft, numbers table, wording decisions

Starts when cards T1, T2, T6 and T7 are done. This card does not edit the lock itself. The orchestrator
reviews your draft and applies it.

Inputs: `planning/TWO_PAPER_CLAIM_LOCK.md`; every note in `planning/sprint_2026-10-11/paper-b-tier1/
results/` (TIER1_ANALYSIS, SCREEN_RESULT, READOUT_ROBUSTNESS, PROBE_AMENDED, HELDOUT_PER_DIMENSION,
BANK2_TRANSPORT, REPLICATE_AND_PROMPT64, NEAR_ZERO); `review/PAPER_WORDING_CHECKLIST.md`,
`review/VERIFIER_REPORT_20261016.md`, `review/F7_F11_RESOLUTION_20261016.md`; the journey plan (C5, C7).

Do this:
1. `planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv`, one row per number the paper may cite,
   with these columns: claim_id, sentence_use, statistic, value, ci_low, ci_high, n, surface_label,
   run_id, producing_script, output_file. Build it with a script
   (`paper_b/build_numbers_table.py`) that reads the JSON outputs. No number typed by hand.
2. `planning/sprint_2026-10-11/paper-b-tier1/C7_CLAIM_LOCK_AMENDMENT_DRAFT.md`, a dated amendment that
   contains only numbers that C3 to C5 (and C6, the factorial, the replicate) actually produced. Each
   number carries its surface label. It must state:
   - Transport (retrospective): the held-out screen result, per dimension under the C5 rule (card T1),
     and the bank-2 imprint result under the C3 rule (card T2).
   - Pre-piloting: NOT supported. The WVS-7 join is retrospective, and the journey plan's own risk list
     says that a retrospective file cannot pass the pre-piloting checkpoint. No prospective human route
     exists in 2026. The claim stays prospective and is not written as a result.
   - The factorial: own effects in the intended direction, V5 failed, the cross-talk, and the route
     contrast with the 64-cell sign-prompt result.
   - The comparators (Amendment 2) and the readout robustness.
   - What the paper must not claim (copy and extend the "explicit non-claims" style of the lock).
3. Wording decisions, with one recommendation each and the reason: F7 (record both hashes of
   `pool_skeleton.csv`, the CRLF working copy and the LF git blob, and state the convention), F8 (the
   replicate is "an unseeded retrain"; no weight-space cosine), F11 (the exact sentence about
   `config.py`: cohort-1 defaults unchanged when the environment variable is not set). Put them in a
   section of the draft.
4. REQUEST REVIEW on this card when done. Do not complete it.

Write boundary: the script, `NUMBERS_TABLE.csv`, and the draft. Do not commit.
