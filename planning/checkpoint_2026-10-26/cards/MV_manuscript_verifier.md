## MV · Independent check of the rewritten manuscript (verifier, cross-family)

**Root:** `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW-paper-b-draft` (`misc/paper_b/`). The rewrite by
cards M1 and M2 (writer, Claude) is on disk, uncommitted; the baseline is commit `a467da0`'s manuscript (use
`git diff` against HEAD). You run on a different model family on purpose.

**Goal.** Decide whether the rewritten manuscript can be shown on Monday as a trusted checkpoint. Check, in order,
and append each result to the review file as you go:
1. **Numbers.** Rebuild both PDFs; rerun both number audits (must PASS). Independently, with your own short script
   in `misc/paper_b/review_probes/`, compare every `\cl{value}{id}` and `\ci{lo}{hi}{id}` in all `.tex` files with
   `NUMBERS_TABLE.csv` at the printed precision (the table is
   `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv`).
   Print only `0 mismatches` or the mismatching ids.
2. **No number changed meaning.** For each claim id whose sentence was rewritten, check the new sentence describes
   the same estimand, direction and interval as the old one (diff against HEAD).
3. **Claim lock.** Against the rules block below and `planning/TWO_PAPER_CLAIM_LOCK.md` (Amendments C7–C9.1):
   no positive tool claim, no "transport", every held-out result called retrospective, C9 called descriptive, the
   sign-prompt caveat (`SP_D_own`) present where the trust result is credited, no "anchor is the bottleneck", no
   causal or mechanistic wording for W1, no "persona matches respondents".
4. **Novelty wording** matches the verdict in
   `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/planning/checkpoint_2026-10-26/NOVELTY_AUDIT.md`.
5. **Anonymity.** `pdftotext` grep of both PDFs for author names, arXiv, `2610.06562`, "earlier study" is empty;
   `references.bib` has no entry for the preprint.
6. **Build hygiene.** 0 overfull, 0 undefined; abstract ≤ 150 words; report main-text word count.
7. **Read it.** Read the abstract, introduction and conclusion as a referee would and list any overclaim or
   unclear sentence with file:line.

**Artifact:** `misc/paper_b/MANUSCRIPT_REVIEW_2026-10-25.md`, first line `VERDICT: PASS | PASS-WITH-WORDING |
BLOCK`. Each finding has file:line, the problem and the required wording. Do not edit the manuscript; do not commit.

**Fence:** read-only except the review file and `review_probes/`. Never open `data/`.

**Budget:** about 60 tool calls.
