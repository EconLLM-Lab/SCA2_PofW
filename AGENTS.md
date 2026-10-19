# AGENTS.md: SCA2_PofW

Instructions for every agent working in this repository: Hermes profiles, Codex, Claude Code and others.
EconLLM Lab, Synthetic Cultural Agents (SCA) project, phase 2. Owner: Augusto Gonzalez-Bonorino.

## Read first, in this order

1. [STATUS.md](STATUS.md): where every workstream stands, what exists on git and the Hub, what is open.
2. [planning/DECISIONS.md](planning/DECISIONS.md): dated decisions and who authorized them.
3. [planning/TWO_PAPER_CLAIM_LOCK.md](planning/TWO_PAPER_CLAIM_LOCK.md): what Paper A and Paper B may claim.
4. `planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv`: the only source of Paper B numbers.

Truth order: git and the Hub > claim lock and numbers table > STATUS.md > everything else. Plans, sprint
reports, worker logs, kanban results and agent memory are dated records. Never report their status lines as
current. Check git and the Hub before you say what has or has not been done.

## Workstreams and fences

- **Paper B** (the journal version of arXiv:2610.06562): code on `feat/paper-b-cohort`; manuscript on
  `paper/paper-b-draft` (worktree `../SCA2_PofW-paper-b-draft`). The manuscript never cites the preprint as
  prior work.
- **Workbench** (`.worktrees/adapter-brain-vizualization`, branch `Adapter-Brain-Vizualization`): an independent
  stream. Do not edit it from Paper B work, and never count its compute or results as Paper B's.
- **Paper A**: frozen at tag `arxiv-2610.06562-v1`. Do not edit `misc/arxiv-submission-2026-10-05/`.

## Locks (these override convenience)

- No country name in evaluation prompts (anti-leakage). The country-named persona arm is a declared comparator.
- `data/` holds licensed, local-only microdata. Never commit it and never upload human rows to the Hub.
  Read held-out human data only through `paper_b/heldout/freeze.require_freeze()`.
- Never overwrite Hub `adapters/<CC>` (cohort 1) or a bank's `bank2/<bank id>/` prefix. A new bank gets a new id.
- Pins, preregistrations and claim-lock amendments are append-only. A rebuilt numbers table needs a new dated
  amendment, and the old rows must be proved unchanged by a test.
- Never print, log or copy `HF_TOKEN`. Run tests with `HF_TOKEN=` blank.
- Colab Pro has 100 units a month. GPU spend needs Augusto's go. Dry-run on fixtures first, never cap gate checks
  to save time, and stop every VM you start.
- Do not push, tag, publish, merge to `main`, or rewrite history without an explicit decision from Augusto.

## Running

```bash
env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest paper_b -q   # main worktree only
```

Commit by explicit path (never `git add -A`). Edit the supplement through `supplement.tmpl.tex`, never
`supplement.tex`.

## Keeping the record straight

Follow "Keeping this file true" at the end of [STATUS.md](STATUS.md): a status-changing commit updates
STATUS.md, a decision gets a row in `planning/DECISIONS.md`, approved plans move to `planning/plans/`, and
superseded documents get the "Record, not status" banner instead of being deleted.
