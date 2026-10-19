## Shared rules for every Paper B card (read these first)

Project: SCA2 Paper B, EconLLM lab. You work for Augusto Gonzalez-Bonorino. The orchestrator (the `sca`
profile) reviews your output before anything is committed or written into the paper.

Repository: /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW, branch `feat/paper-b-cohort`.
Python: run `env -u PYTHONPATH .venv/bin/python` from the repository root.
Tests: `env -u PYTHONPATH -u VIRTUAL_ENV .venv/bin/python -m pytest -q paper_b/`. The baseline is
347 passed, 4 failed (`test_eval_lib.py`) and 3 errors (`test_evaluate_local.py`). Those 7 are old. Any
other failure is yours.

Read before you start:
1. `planning/sprint_2026-10-11/paper-b-tier1/results/TIER1_ANALYSIS_20261017.md` (all results so far).
2. `paper_b/heldout/PREREGISTRATION.md` (sections 1 to 12).
3. `.hermes/plans/2026-10-11_233701-paper-b-journey.md` (checkpoints C0 to C7).

Rules:
1. Write only the files that your card names. Do not commit, push, rebase or change branch, unless your
   card says so.
2. Do not change these files: `paper_b/heldout/FREEZE.json`, `selection_amended_20261016.csv`,
   `pool_skeleton.csv`, `overrides.json`, `face_valid.csv`, `comparator_review.json`, `jev/*`,
   `PREREGISTRATION.md`, existing entries of `paper_b/score_plan_pins.json`. On the Hugging Face Hub,
   never write to `adapters/<CC>` and never change `config.BANK_RUN_ID`.
3. Human data stays on this Mac. `data/WVS/*.dta` and `data/GPS/*` must not be uploaded. Do not print
   respondent rows. Do not write country-level human means into the repository or the Hub. Correlations,
   intervals and other aggregate statistics are permitted.
4. Secrets: the Hugging Face token is the `HF_TOKEN=` line in /Users/bonorinoa/.hermes/profiles/sca/.env.
   Read it in code. Never print it, log it or copy it to another file. Pass `token=` to every
   `huggingface_hub` call: a private repository without a token looks like "Repository Not Found".
5. Every number you report must come from a script that you wrote and ran. Cite the output file. Never
   type a number by hand. If a step fails, stop, write the exact error on the card and block the card.
   Do not invent a result.
6. Test first: write the failing test, see it fail, then write the code.
7. When you finish, write one comment on the card with: (a) the files that you wrote, (b) the commands
   that you ran, (c) the key numbers with their source file, (d) everything that failed or is not
   certain. Then complete the card (or request review, if your card says so).

Skills from the `sca` profile that you can read by absolute path:
- /Users/bonorinoa/.hermes/profiles/sca/skills/llm-pipeline-engineering/SKILL.md
- /Users/bonorinoa/.hermes/profiles/sca/skills/llm-pipeline-engineering/references/dpo-adapter-batch-workflow.md
- /Users/bonorinoa/.hermes/profiles/sca/skills/mlops/colab-cli-headless-runs/SKILL.md
- /Users/bonorinoa/.hermes/profiles/sca/skills/research/experiment-launch-validation/SKILL.md
- /Users/bonorinoa/.hermes/profiles/sca/skills/llm-pipeline-engineering/sca2-canonical-surface/SKILL.md

Synthetic inputs that are already downloaded (no human data):
/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/ — `adapter_strict_v1.csv` (64 bank-2 profiles,
strict battery), `cohort1_strict.csv` (42 cohort-1 country adapters), `signprompt_strict_raw.csv`
(26-profile sign-prompt cell), `fetch_fact_inputs.py` (re-downloads all three from the Hub).
