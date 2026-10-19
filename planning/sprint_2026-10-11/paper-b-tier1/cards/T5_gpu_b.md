## Card T5 — GPU session B: near-zero refits (checkpoint C6)

This card starts BLOCKED. The orchestrator unblocks it only after it approves
`planning/sprint_2026-10-11/paper-b-tier1/C6_DESIGN.md` (card T3).

Do this:
1. Read `C6_DESIGN.md` in full, and the same skills as card T4. Follow the design exactly. If a step in
   the design is not possible as written, block the card and explain. Do not change the design.
2. Upload the two reduced banks built by T3 (from
   /Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/near_zero/) to the paths that the design names.
   Never write `adapters/<CC>`. Never change `config.BANK_RUN_ID`.
3. Train the two adapters on one T4 VM with the frozen training configuration, upload each adapter to
   the Hub path that the design names, and score both on the strict battery under the design's run id.
   Any code change follows the same rules as card T4 (test first; you may commit and push only your own
   files on `feat/paper-b-cohort`).
4. Verify on the Hub: two adapters, their run records, and the strict scores with the strict spec hash.
5. Stop the VM and confirm that no `pb-` session is left. Budget: at most 10 compute units. Report
   `colab usage` before and after.
6. If a step fails twice, stop the VM, block the card, and write the exact error.

Write boundary: what C6_DESIGN.md names, plus tests for any code change.
