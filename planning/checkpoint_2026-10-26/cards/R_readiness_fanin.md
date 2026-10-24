## R · Checkpoint 2026-10-26 readiness: triage now, final check last (sca)

**The work cards already exist. Do not decompose this card and do not create cards.** This is the fan-in of
N1 (novelty audit), M1 → M2 → MV (manuscript rewrite and its cross-family check), and E1 → EV → ED (workbench
v1.6: wording, builder fix, hygiene, check, deploy). Spec texts are in
`/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/planning/checkpoint_2026-10-26/cards/`.

**Phase 1, triage (now).** Read every work card's spec and the rules block below. Check scope, order, gates,
fences and model routing (producers on the Claude seat, verifiers on `z-ai/glm-5.3` via openrouter, a different
family). Post any correction as a comment on the specific card, marked "binding" only if it is a lock violation.
Then move yourself to todo. Spend at most 10 tool calls here.

**Phase 2, final check (after all parents are done).** Answer from live evidence, not from card summaries:
1. MV verdict line, and every finding either fixed or listed as wording for the PM. Re-run both number audits and
   the anonymity grep yourself in `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW-paper-b-draft/misc/paper_b`.
2. `git status` in the paper worktree lists only the rewrite's files (uncommitted is expected; the PM commits).
3. EV verdict and ED deploy record; the Space serves the new footer (fetch it).
4. The main worktree suite: `cd /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW && HF_TOKEN= env -u PYTHONPATH
   PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest paper_b -q` is green.
5. N1's verdict is reflected in the introduction's wording.

**Artifact:** `planning/checkpoint_2026-10-26/READINESS.md` in the main worktree: one verdict line ("ready" / "not
ready"), a table check / evidence / status, and what the PM must still do (commit, merge, push, STATUS, Overleaf).
If any check fails, write the file, then `kanban_block` with `kind=needs_input`. Do not commit; never open `data/`.
