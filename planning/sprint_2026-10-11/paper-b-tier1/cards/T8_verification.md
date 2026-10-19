## Card T8 — Verification record and compute ledger

Starts when cards T4 and T5 are done.

Do this:
1. `planning/sprint_2026-10-11/paper-b-tier1/VERIFICATION.md`, in the format of task F3 in
   `.hermes/plans/2026-10-14_204500-paper-b-tier1-factorial-prereg.md` (lines 1748 to 1763): what each
   artifact is and which run id produced it; the hashes (spec SHA-256 per condition, adapter revision,
   selection SHA-256, the SHA-256 of `FREEZE.json`); the acceptance checks V1 to V5 with their measured
   values (V1 to V5 are already measured in `results/TIER1_ANALYSIS_20261017.md`, section 5, and V3 has
   a script at /Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/v3_determinism.py); and, in plain
   language, everything that failed or is not resolved (V5 failed, 2 of 6). Compute every hash with a
   script. Do not copy hashes from other notes.
2. Compute ledger, Phase H of the same plan (lines 1779 to 1785): append every GPU session of 2026-10-15
   to 2026-10-18 to `paper_b/compute/ledger.jsonl` and `paper_b/compute/publication_estimate.json` with
   `paper_b/compute_ledger.py`. Sources: the `compute/ledger.jsonl` files under `runs/*/` on
   `Bonorinoa/SCA2-paper-b-artifacts`, and the final comments of cards T4 and T5. Do not double-count a
   session that is already in the ledger. Report the total units by stage (training, scoring).

Write boundary: `VERIFICATION.md`, the two ledger files, and a helper script if you need one. Do not
commit.
