## M2 · Manuscript rewrite, part 2: body pass (writer)

**Root:** `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW-paper-b-draft` (branch `paper/paper-b-draft`,
`misc/paper_b/`). Gated on M1; M1's edits are on disk, uncommitted. Do not revert them.

**Goal.** Bring the body in line with the new framing that M1 wrote (read `misc/paper_b/REWRITE_LOG.md` and the new
`introduction.tex` first): `background.tex`, `instrument.tex`, `design.tex`, `results.tex`, and the prose of
`supplement.tmpl.tex`. This is a prose pass:
- signpost each results subsection to the chain (anchor → instrument → respondents) the introduction promises;
- cut repetition and hedging stacks; move detail that only a referee needs into the supplement template;
- aim the main text toward the outline's 9,000–10,000 words without dropping any registered result or any honesty
  clause (retrospective, descriptive, not preregistered, no claim earned);
- keep the persona and sign-prompt comparisons and the `SP_D_own` caveat visible in the main text.

**Never change a number, an interval, a claim id or a table.** Move a `\cl` sentence if you must; do not
re-derive it. Supplement: edit `supplement.tmpl.tex` only, then `tools/render_supplement.py`.

**Gates (in `misc/paper_b/`, with `HF_TOKEN= env -u PYTHONPATH` and
`/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.venv/bin/python`):**
- `latexmk -pdf main.tex` and the supplement build: 0 overfull, 0 undefined.
- `tools/audit_numbers.py --out NUMBER_AUDIT.txt` and
  `tools/audit_numbers.py --files supplement.tex --out SUPPLEMENT_NUMBER_AUDIT.txt` → both `RESULT: PASS`.
- `git diff a467da0 -- misc/paper_b | grep -oE '\\cl\{[^}]*\}\{[A-Za-z0-9_]+\}' | sort -u` compared before/after:
  list in the log any claim id that disappeared from the paper, with the reason.
- The anonymity grep on both PDFs is empty (pattern as in M1).

**Artifact:** edited files; append a `## M2` section to `misc/paper_b/REWRITE_LOG.md` (per file: what changed, word
count before/after, gates). **Do not commit.**

**Fence:** do not edit M1's four files except to fix a cross-reference; do not touch tables, `macros.tex`,
`supplement.tex` by hand, `tools/`, or `submission/`. Never open `data/`.

**Budget:** about 50 tool calls (your cap is 60). One file at a time, log after each.
