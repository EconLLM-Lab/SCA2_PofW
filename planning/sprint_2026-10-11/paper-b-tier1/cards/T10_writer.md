## Card T10 — Draft the Paper B manuscript for Sociological Methods & Research

This card starts BLOCKED. The orchestrator unblocks it after it approves the claim-lock amendment
(card T9) and creates your worktree.

Workspace: the git worktree /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW-paper-b-draft on
branch `paper/paper-b-draft`. Write the manuscript in `misc/paper_b/`. Paper A sources are in
`misc/position_paper/` and `misc/arxiv-submission-2026-10-05/` (arXiv 2610.06562). Fork their structure
(main.tex, section files, tables/). Never overwrite Paper A files. You may commit on `paper/paper-b-draft`. Do not push.

Load these skills before you write: `augusto-academic-voice`, `latex-paper-revision`,
`academic-position-paper`. SMR author guidelines: https://journals.sagepub.com/author-instructions/SMR

Sources (the only sources of numbers and claims):
- The approved amendment in `planning/TWO_PAPER_CLAIM_LOCK.md` and
  `planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv`. A number that is not in the table does
  not go in the paper. Every number carries its surface label.
- For methods: `paper_b/heldout/PREREGISTRATION.md` (with Amendments 1 and 2),
  `results/TIER1_ANALYSIS_20261017.md`, `VERIFICATION.md`, `review/PAPER_WORDING_CHECKLIST.md`.

Augusto's standing preferences:
- SCA-first framing. Narrative paragraphs. Positive claims. No ", not" tails and no "X, not Y" kickers.
- Terms: "response distributions" (not histograms), "synthetic respondents", "scoring instrument", DPO
  described as regularized Bradley-Terry.
- The abstract has words only, no statistics.
- Methods say how each number was built (estimator, resampling, seed, run).
- Report the weak result and the failures plainly: the screen is real but weak (about 8% of the human
  wave-6/7 ceiling); V5 failed; posrecip points the wrong way; pre-piloting is not claimed.
- Never use a "humanizer" pass.

Authors (confirm with Augusto, leave a TODO comment): the Paper A block, Augusto Gonzalez-Bonorino,
Kseniia Biriukova, Monica Capra.

Do this:
1. Outline first (`misc/paper_b/OUTLINE.md`), with one line per section and the NUMBERS_TABLE claim_ids
   that each section uses. Commit it.
2. Write the full draft. Build the PDF (`latexmk -pdf`), fix every error and every undefined reference.
3. Run a self-check: every number in the .tex appears in NUMBERS_TABLE.csv. Use a small script that
   extracts the numbers and compares them; put its output in `misc/paper_b/NUMBER_AUDIT.txt`.
4. Commit on `paper/paper-b-draft`. Final comment: the PDF path, the page count, the word count, the
   audit result, and the open questions for the coauthors. Coauthor sign-off (checkpoint C7) is still
   needed after your draft.
