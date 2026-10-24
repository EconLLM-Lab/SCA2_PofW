## M1 · Manuscript rewrite, part 1: framing (writer)

**Root:** `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW-paper-b-draft` (branch `paper/paper-b-draft`,
sources in `misc/paper_b/`). Start from commit `2c16fcf` or later.

**Goal.** Rewrite the framing of the manuscript to Augusto's chosen positioning (option A, rules block below):
`abstract.tex`, `introduction.tex`, `discussion.tex`, `conclusion.tex`, and the working title in `main.tex` /
`title_page.tex` if it no longer fits (offer the new title in your handoff, at most 20 words). The current draft
already has the C9 results in sections 5.8–5.11 (`results.tex`) and one discussion paragraph; the abstract,
introduction and conclusion do not mention them. After this card they must carry the anchor → instrument →
respondents chain and the order-versus-distribution contrast, using only `\cl`/`\ci`/`\dc` macros with claim ids
that already appear in `results.tex` or the numbers table.

**Inputs to read first:** the rules block below; `misc/paper_b/OUTLINE.md`; the venue rubric
`~/.hermes/profiles/writer/venue-cards/sociological-methods-and-research.md` (abstract at most 150 words, words
only); the novelty audit `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/planning/checkpoint_2026-10-26/NOVELTY_AUDIT.md`
(card N1). Follow its verdict on "first/new" wording; add its recommended references to `references.bib` only if
you cite them.

**Write it well.** This is a real rewrite, not a patch: a methods-paper voice for quantitative social scientists,
one idea per paragraph, the contribution stated in the first page. The introduction should end with what the paper
does and does not show. The discussion should explain why the signs carry the trust order (W1 decomposition) and
why order and distribution diverge (signs carry no magnitudes), without causal or mechanistic language. Keep
the honest boundary sentences (retrospective screen, pre-piloting untested, complement to human pretesting).

**Gates (run them yourself, in `misc/paper_b/`):**
- `latexmk -pdf main.tex`: 0 overfull boxes, 0 undefined references.
- `../../../SCA2_PofW/.venv/bin/python tools/audit_numbers.py --out NUMBER_AUDIT.txt` → `RESULT: PASS`
  (run with `HF_TOKEN= env -u PYTHONPATH`).
- `pdftotext main.pdf - | grep -inE 'arxiv|2610\.06562|earlier study|bonorino|gonzalez|biriukova|capra'` is empty.
- Abstract word count ≤ 150 (report it). Report main-text word count against the outline's 9,000–10,000 target.

**Artifact:** the edited `.tex` files plus `misc/paper_b/REWRITE_LOG.md` (create it): per file, what changed and
why, the claim ids used, gate results, and any sentence you were unsure about marked `UNSURE:`. Append after each
file. **Do not commit**; the PM reviews and commits.

**Fence:** edit only `abstract.tex`, `introduction.tex`, `discussion.tex`, `conclusion.tex`, `main.tex` (title
only), `title_page.tex` (title only), `references.bib`, and `REWRITE_LOG.md`. Leave `results.tex`, `design.tex`,
`background.tex`, `instrument.tex`, tables and the supplement to card M2. Keep every existing `TODO(Augusto)`
comment. Never open `data/`.

**Budget:** about 45 tool calls (your cap is 60). Finish one file completely, gates included, before the next.
