## Shared rules (SCA2 checkpoint sprint, 2026-10-19; read first)

You work for Augusto Gonzalez-Bonorino (EconLLM Lab). The PM (`default` profile) reviews your output; a verifier
on a different model family checks it before anything is banked. Target: a stable checkpoint for co-author review at
08:00 MST Tue 2026-10-20 (Augusto, 2026-10-19). Producer cards finish or block with an exact reason by 01:00 MST;
the verifier by 04:00; amendment and deploy by 06:00; checkpoint assembly by 07:30.

Repository: /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW (main worktree, branch `feat/paper-b-cohort`).
Read first: `AGENTS.md`, then `STATUS.md` (truth order, locks), then `planning/DECISIONS.md` (last 6 rows).
Python: `env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python` from the repo root.
Tests: `HF_TOKEN= env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest paper_b -q` (baseline 552 passed).

Rules:
1. Write only the files your card names (plus their tests). Do not commit, push, rebase or change branch unless
   the card says so. Never edit `paper_b/heldout/FREEZE.json`, preregistration files, pins, or the numbers table
   (`NUMBERS_TABLE.csv` is rebuilt only by the amendment step after verification).
2. Human data stays on this Mac. Do not print respondent rows. Do not write country-level human means or
   distributions into git-tracked files or the Hub. Correlations, intervals, shares and test statistics are fine.
   The six human-derived CSVs listed in `.gitignore` (section "human-derived tables") are local-only inputs.
3. Secrets: HF token = the `HF_TOKEN=` line in /Users/bonorinoa/.hermes/profiles/sca/.env. Read it in code, never
   print/log/copy it. Pass `token=` to every huggingface_hub call.
4. Every number you report comes from a script you wrote and ran; cite the output file. Never type a number by
   hand. If a step fails, stop, write the exact error on the card and block it. Never invent a result.
5. Test first for new code (failing test, then code).
6. Label every new statistic DESCRIPTIVE / NOT PREREGISTERED (the 10-11 surface has already been seen).
   Intervals on adapter-side quantities use the profile-block bootstrap (`analyze_surface.bootstrap_spearman`
   with profile clusters, 2000 draws, seed 20261011); human–GPS uses the country bootstrap. Say which.
7. Finish with one card comment: (a) files written, (b) commands run, (c) key numbers with source file,
   (d) what failed or is uncertain, (e) a plain-language reading in 3-5 sentences. Then complete the card.

Useful paths: cohort-1 banked surface `planning/sprint_2026-10-11/paper-b-20261011/` (model_probs.csv,
analysis/, analysis_phase/, local_eval/); Tier-1 results `planning/sprint_2026-10-11/paper-b-tier1/results/`
(factorial/, persona/, replicate/); analysis library `paper_b/analyze_surface.py`, `paper_b/analyze_phase.py`;
synthetic inputs (no human data) `/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/`.
Exploratory PM scripts that already ran (re-implement properly, do not import from scratch):
`/Users/bonorinoa/.hermes/cache/scratch/c9_explore/explore_ceilings.py`, `perm_between.py`.
Output folder for this sprint: `planning/sprint_2026-10-11/paper-b-tier1/results/c9/` (create it).
