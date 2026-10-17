# Verifier brief: independent review of Paper B work to date (2026-10-16)

Reviewer: `verifier` profile. Requester: Augusto Gonzalez-Bonorino (EconLLM lab). Repo: `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW`, branch `feat/paper-b-cohort`.

## Purpose
Find mistakes before they carry into the held-out scoring, the analysis and the paper. Be adversarial. Report what is wrong, what is unverified, and what is fine, with the evidence for each.

## Hard rules
- READ-ONLY. Do not edit, commit, push or delete anything in the repo, on the Hub or on Drive.
- Do not read, print, join or summarise held-out human data (`Z*P_heldout_human.csv`, any WVS respondent file). `paper_b/heldout/FREEZE.json` does not exist and must not be created.
- No GPU, no Colab session, no HF inference endpoint (all paused). The Colab balance is shared.
- No credentials: never print `.env` values or tokens. Hub reads use the token in `/Users/bonorinoa/.hermes/profiles/sca/.env` without echoing it.
- Write exactly one file: `planning/sprint_2026-10-11/paper-b-tier1/review/VERIFIER_REPORT_20261016.md`. Scratch work goes under `$TMPDIR`.
- Run Python as `env -u PYTHONPATH .venv/bin/python`. Write probes as scripts, not inline `python -c`.

## What to review (commit range: `git log prereg-heldout-2026-10-14^..HEAD` plus the preregistration itself)

1. **Bank 2 (statistically similar to bank 1, not byte-identical).** `synthetic_generation/outputs/bank2_20261014/`, `gps_sign_relabel_bank2*/`, `paper_b/bank_similarity.py`, `planning/sprint_2026-10-11/paper-b-tier1/results/bank_similarity.json`. 658 of 660 triplets (2 `KeyError: 'response_a'` failures, nothing padded). Labels come only from `deterministic_sign`. Check the audit's claims: per-dimension counts, prompt and response length medians, overlap 0.15%, text-leak gate, country gate, 64 distinct sign profiles.
2. **Factorial design.** `paper_b/factorial.py`, `protocol_bank2.py`, `config.py` (must be byte-identical to cohort 1). Unit naming `P_<bits>` over [trust, risktaking, patience, altruism, posrecip, negrecip], bit 1 = positive z. Check bit order is the same everywhere it is used (training units, sign prompts, probe design matrix, analysis).
3. **Training and artifacts.** 64/64 adapters on `Bonorinoa/SCA2-paper-b-adapters` under `bank2/gps_sign_relabel_bank2_20261015_062543Z/profiles/<unit>`; replicate at `.../replicates/r1/profiles/P_1_0_1_1_0_1`. Check run records, the resume and upload logic (`run_cohort.py`, `train_country.py`, `hub_io.py`), and whether the replicate comparison was read correctly (weight-space cosine about 0; is LoRA init seeded? `config.SEED=42` exists but `train_country.py` does not obviously use it).
4. **Drive to Hub migration.** `paper_b/migrate_drive_to_hub.py`, `planning/sprint_2026-10-11/paper-b-tier1/results/MIGRATION_MANIFEST_20261015.json`. Verify hashes on a sample, that all three repos are private, that nothing from `SCA2_phase2/public_eval` or raw WVS respondent data was copied, and that cohort-1 `adapters/<CC>` was not modified.
5. **Held-out preregistration and tooling.** `paper_b/heldout/` (`PREREGISTRATION.md`, `build_pool.py`, `probe_select.py`, `freeze.py`, `screen_test.py`, `ceiling.py`, comparators, Jev 5-run majority rule). Check: the 223-item pool rule; probe OLS (64 units, intercept + 6 main effects + 15 two-way interactions, error df 42); the PRIMARY rule (top 25% of 223 by |t| among imprint-set items, at most 56); the permutation null and bootstrap; the FREEZE guard fails closed; section 10 hashes match the files at tag `prereg-heldout-2026-10-14`; the preregistration text matches what the code does.
6. **Scoring plan (about to run).** `paper_b/score_plan.py`, `score_plan_pins.json`, `build_scoring_spec.py`, `score_runtime.py`, `score_sign_profiles.py`, `paper_b/colab/vm_gate_factorial.py`, `vm_score_units.py`, `vm_score_half_{a,b}.py`. Check: spec hashes (heldout_v1 equals the preregistered `4d799b029102d7e7`); the prompt variants really differ and reverse_options reverses display order only; the adapter revision pin `902f262e…` holds all 64 adapters; halves partition the 64 units; resume reads the Hub; the gate runs one unit per half (is that enough?); the sign-prompt arm does not use the gate marker (is that a gap?); sign-prompt ids equal adapter units; no country leaks in prompts.
7. **Known open items to confirm or dispute.** `paper_b/compute_ledger.py` does not recognise `P_…` units for publication clocks; pre-existing failures (4 failed and 3 errors in `test_eval_lib.py` and `test_evaluate_local.py`; 3 in `synthetic_generation` for `--diagnostic-scorer`) are claimed unrelated; Jev comparator instability (5 of 223 flips at the 0.5 threshold) is handled by the registered majority rule.
8. **Claims.** `skill sca2-canonical-surface` lists the Paper A numbers; flag any Paper B number or claim in notes or plans that is not backed by a banked artifact.

## Deliverable
`VERIFIER_REPORT_20261016.md` with: (a) a findings table (id, severity BLOCKER/MAJOR/MINOR, file:line, evidence, suggested fix), (b) a list of checks that PASSED with the command or file read, (c) things you could not verify and why. Say BLOCKER only when a finding would invalidate the scoring run or a preregistered claim. Do not fix anything; the author applies fixes.
