# SCA2 status

**Last verified: 2026-10-19 (MST) by the `sca` profile**, against git and the Hugging Face Hub with the commands in
[How to re-verify](#how-to-re-verify). This file is the single status page for every person and agent working on
SCA2. It indexes the evidence; it is not the evidence. When it disagrees with git or the Hub, git and the Hub win:
fix this file in the same commit.

## Truth order

1. **What exists:** git (branches, commits, tags) and the two private Hub datasets below.
2. **What we may say:** [the claim lock](planning/TWO_PAPER_CLAIM_LOCK.md) (Paper A table, Paper B amendments) and
   [NUMBERS_TABLE.csv](planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv) (every Paper B number).
3. **Where we are:** this file and [planning/DECISIONS.md](planning/DECISIONS.md).
4. **Everything else is a dated record.** Plans, sprint reports, worker logs and kanban results describe the day
   they were written. Never quote their status lines as current. On 2026-10-19 a bot quoted a 10-Oct plan and
   reported that training, bank 2 and scoring had not happened; all three had.

## Workstreams

| Stream | State | Where |
|---|---|---|
| **Paper A** (preprint) | Posted: arXiv:2610.06562 v1, 2026-10-05. Frozen. | tag `arxiv-2610.06562-v1` (`5664026`); [misc/arxiv-submission-2026-10-05/](misc/arxiv-submission-2026-10-05/) |
| **Paper B** (the journal version of the preprint, for SMR) | Compute and analysis done through Amendment C8. Manuscript drafted. Waiting on the decisions listed under [Open](#open). | code `feat/paper-b-cohort`; manuscript `paper/paper-b-draft` |
| **Workbench** (Adapter-Brain-Vizualization) | Independent stream with its own owner and audit (`workbench/AUDIT.md` on its branch). Its compute and results are never Paper B's. | worktree `.worktrees/adapter-brain-vizualization`, branch `Adapter-Brain-Vizualization` |
| **Phase 3** (activation engineering, latent space) | Not started. | — |

## Git

| Ref | Head | Note |
|---|---|---|
| `paper/paper-b-draft` | merge of everything below, pushed 2026-10-19 | **The single merged branch to pull.** It holds the manuscript in `misc/paper_b/` (worktree `../SCA2_PofW-paper-b-draft`) plus all of `feat/paper-b-cohort`. |
| `feat/paper-b-cohort` | code branch (this worktree), pushed 2026-10-19 | Paper B code, results, claim lock. Merged into the branch above after every commit. |
| `Adapter-Brain-Vizualization` | `e5fea0b` | Workbench. Not merged anywhere. |
| `main` | local `2e4989b`, origin `305d820` | Local main is 1 commit ahead (the arXiv upload package), unpushed. Paper B is not merged to main. |
| tags | `arxiv-2610.06562-v1`, `prereg-heldout-2026-10-14` | |

## What exists on the Hub

Two private datasets, read with the `HF_TOKEN` in the `sca` profile `.env` (never print it).

| Object | Location | Count | Identity |
|---|---|---|---|
| Cohort-1 adapters (bank 1, one per country) | `Bonorinoa/SCA2-paper-b-adapters` `adapters/<CC>` | 42 / 42 with weights | every `run_record.json` carries bank `gps_sign_relabel_all_20260816_004545Z`; pinned revision `7550fd4c…` |
| Bank 2 (second scenario bank, same sign rule) | repo `synthetic_generation/outputs/gps_sign_relabel_bank2/` | 658 pairs | `gps_sign_relabel_bank2_20261015_062543Z` |
| Bank-2 adapters (one per sign profile, full 2^6 factorial) | `bank2/<bank id>/profiles/<P_…>` | 64 / 64 | same bank id |
| Bank-2 extras | `bank2/<bank id>/replicates/r1`, `near_zero/`, `near_zero_control/` | 1 + 2 + 2 | unseeded replicate; GBR and COL near-zero refits with size-matched controls |
| Model-only scores | `Bonorinoa/SCA2-paper-b-artifacts` `runs/<run_id>` | 21 runs | listed below |
| Workbench phase-1 cohort | same dataset, `workbench_cohort/phase1_nf4_t4/` | 8,628 files | workbench, not Paper B |

Hub heads at verification: adapters `c4b0f36e`, artifacts `e1687cf0`. Human respondent rows and model–human joins
never go to the Hub; they stay in local `data/` (licensed, not redistributable).

Scoring runs (`runs/`): `paper-b-20261011` (cohort 1, 42 countries), `sign-prompt-20261011` (26 profiles),
`bank2-strict-v1-20261016`, `bank2-heldout-v1-20261016` and its three readout variants (`-reverse-`, `-para-a-`,
`-para-b-`), `bank2-signprompt-heldout-v1-20261016`, `bank2-signprompt-strict-v1-20261018`,
`bank2-replicate-r1-{strict,heldout}-v1-20261018`, `bank2-nearzero-strict-v1-20261018`,
`persona-strict-v1-20261019` (country-named persona, 42 countries), and eight gate runs (`gate-…`).

## Paper B claims

The claim lock's dated amendments decide what Paper B may say: **C7** (after Tier 1), **C7.1** (table rebuilt),
**C8** (persona arm), all 2026-10-18. In short: neither additional locked claim is earned. Paper B is a
preregistered evaluation of the sign compiler as a scoring instrument: what holds, what fails, and what is untested.
The held-out result is a *retrospective* screen against WVS-7, never "transport". Pre-piloting is untested, and no
human route exists in 2026.

[NUMBERS_TABLE.csv](planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv): 271 rows, sha256
`51ddcce1dd205ee29ecf6e3450fd30bf09948399e98adb32abfc0846e1b97855`. A rebuilt table needs a new dated amendment
and an update here; `paper_b/test_status_doc.py` fails until both match.

## Headline numbers

Read from the table at the printed precision. Interval types are in each row's `surface_label`. The test suite
checks every value below against the table.

| Quantity | Value | Claim id |
|---|---|---|
| Trust adapter–GPS, cohort-1 adapters, 42 countries | 0.744 [0.500, 0.865] | `B2_cohort1_trust_rho` |
| Trust adapter–GPS, bank-2 adapters, 42 countries | 0.803 [0.615, 0.876] | `B2_bank2_trust_rho` |
| Trust bank-to-bank agreement, 26 sign cells | 0.907 [0.774, 0.957] | `B2_bank_to_bank_trust_spearman` |
| Held-out screen statistic A, 56 items (retrospective) | 0.061 [−0.007, 0.126] | `SCR_A_primary` |
| Held-out screen permutation p | 0.0097 | `SCR_p_perm` |
| A as a share of the wave-6/7 human ceiling | 0.081 | `SCR_A_over_ceiling` |
| Sign-prompt arm A, same probe | 0.028 [−0.109, 0.158] | `SP_A_primary` |
| Sign-prompt arm permutation p | 0.51 | `SP_p_perm` |
| Adapter minus sign prompt, own items (unresolved) | 0.033 [−0.083, 0.143] | `SP_D_own` |
| Adapter minus Jev, shared items (tie) | −0.002 [−0.064, 0.061] | `CMP_jev_D_common` |
| Adapter minus face-valid reader, shared items (tie) | 0.020 [−0.181, 0.215] | `CMP_face_valid_D_common` |
| Largest shift from an unseeded retrain, in profile SDs | 0.11 | `RP_max_abs_surface_diff_sd` |
| Trust persona–GPS (country named, no adapter) | 0.028 [−0.339, 0.381] | `PX_persona_trust_rho` |
| Trust sign-prompt–GPS (six signs, no adapter) | 0.773 [0.584, 0.844] | `PX_signprompt_trust_rho` |
| C8 primary: cohort-1 minus persona, trust | 0.716 [0.191, 1.154] | `PX_D_cohort1_trust` |
| Trust adapter–GPS, 16 development countries | 0.818 [0.554, 0.926] | `PX_dev16_cohort1_trust_rho` |
| Trust persona–GPS, 16 development countries | −0.038 [−0.565, 0.480] | `PX_dev16_persona_trust_rho` |

## Manuscript

`paper/paper-b-draft`, `misc/paper_b/`: main text 40 pages and supplement 9 pages at `ae1099f`, with number audits
311/311 and 297/297 and an independent check showing 0 mismatches. Overleaf review copy: a new project per
version. The current one is "Synthetic Cultural Agents as Scoring Instruments… (1)", uploaded 2026-10-19; Augusto
has still to confirm the page count. The older Overleaf projects are untouched. The preprint is disclosed only on
the title page and in `submission/COVER_LETTER_DRAFT.md`; the manuscript never cites it.

## Open

Nothing is scheduled. These items wait for the next planning session.

**Augusto only:** coauthor sign-off on C7, C7.1 and C8; author list and order; OSF registration; the anonymous
mirror; IRB, COI, funding, compute and AI-use statements; SMR's preprint policy; the Overleaf page count.

**First item on the next planning session (Augusto, 2026-10-19):** the journal version does not yet carry the preprint's human-agreement and
distributional results on the 42 countries: adapter–human, human–GPS, trust sign check, label recovery, the TVD
2×2, and the between-profile share. Most of these are already computed in
[paper-b-20261011/](planning/sprint_2026-10-11/paper-b-20261011/) but have no numbers-table rows. The proposal is
Amendment C9: add those rows, then a manuscript section. One TVD cell needs about 1 Colab unit.

## Compute

Colab Pro, 100 units a month. Last observed balance: 181.82 units (2026-10-18 22:00). Spend for 2026-10-12 → 10-18
was measured by differencing the tool-observed balance readings in the profiles' `state.db` files: **Paper B 87.77
units**, workbench 3.86. Cohort-1 training (10–11 Oct) is outside that window; its clocks are in
`paper_b/compute/publication_estimate.json`. A Colab balance is not an invoice: publication clocks come from the
ledger, not from the balance.

## Document map

Every Markdown file under `planning/` must appear here, by itself or through its folder;
`paper_b/test_status_doc.py` enforces this.

### Live (current reference)

- [TWO_PAPER_CLAIM_LOCK.md](planning/TWO_PAPER_CLAIM_LOCK.md): claims, Paper A table, Paper B amendments C7, C7.1, C8
- [CANONICAL_LESSONS.md](planning/CANONICAL_LESSONS.md): standing rules
- [DECISIONS.md](planning/DECISIONS.md): dated decision log with sources
- [KANBAN_LEDGER.md](planning/KANBAN_LEDGER.md): every SCA2 kanban card, generated by `planning/kanban_ledger.py`
- [PAPER_B_PROTOCOL_DRAFT.md](planning/PAPER_B_PROTOCOL_DRAFT.md): frozen cohort-1 run protocol (2026-10-09)
- [PAPER_B_STACK_FREEZE.md](planning/sprint_2026-10-11/PAPER_B_STACK_FREEZE.md): frozen scoring stack
- [paper_b/heldout/PREREGISTRATION.md](paper_b/heldout/PREREGISTRATION.md): held-out screen, Amendments 1–2
- [paper-b-20261011/RESULTS.md](planning/sprint_2026-10-11/paper-b-20261011/RESULTS.md): cohort-1 surface (Gate 1)
- [paper-b-signprompt/RESULTS.md](planning/sprint_2026-10-11/paper-b-signprompt/RESULTS.md): C1 sign-prompt cell
- [paper-b-tier1/VERIFICATION.md](planning/sprint_2026-10-11/paper-b-tier1/VERIFICATION.md): Tier-1 verification record
- [C6_DESIGN.md](planning/sprint_2026-10-11/paper-b-tier1/C6_DESIGN.md) and [C8_PERSONA_DESIGN.md](planning/sprint_2026-10-11/paper-b-tier1/C8_PERSONA_DESIGN.md): design locks
- [paper-b-tier1/results/](planning/sprint_2026-10-11/paper-b-tier1/results/): result notes, one per analysis
- [paper_b/RUNBOOK.md](paper_b/RUNBOOK.md) and [paper_b/README.md](paper_b/README.md): how to run

### Record (dated; each opens with a "Record, not status" banner)

- [ARCHIVE_INVENTORY.md](planning/ARCHIVE_INVENTORY.md), [PRE_ARXIV_CHECKLIST.md](planning/PRE_ARXIV_CHECKLIST.md), [pre_arxiv_checks/](planning/pre_arxiv_checks/), [rewrite_pre_edit_20260925/](planning/rewrite_pre_edit_20260925/): Paper A, before arXiv
- [PAPER_B_NEXT_STEPS_PLAN.md](planning/PAPER_B_NEXT_STEPS_PLAN.md): 10-Oct plan, superseded (the source of the 19-Oct bot error)
- [plans/2026-09-08_205322-sca2-final-paper-revision.md](planning/plans/2026-09-08_205322-sca2-final-paper-revision.md): Paper A revision plan
- [plans/2026-10-11_233701-paper-b-journey.md](planning/plans/2026-10-11_233701-paper-b-journey.md): checkpoints C0–C7 (their definitions still apply)
- [plans/2026-10-14_204500-paper-b-tier1-factorial-prereg.md](planning/plans/2026-10-14_204500-paper-b-tier1-factorial-prereg.md): Tier-1 plan, implemented
- [PARENT_DECISIONS.md](planning/sprint_2026-10-11/PARENT_DECISIONS.md), [GROUP_CONSULTATION_BRIEF.md](planning/sprint_2026-10-11/GROUP_CONSULTATION_BRIEF.md): 11-Oct sprint decisions and brief
- [SCORER_INTEGRATION_STATUS.md](planning/sprint_2026-10-11/SCORER_INTEGRATION_STATUS.md), [STORAGE_VERIFICATION.md](planning/sprint_2026-10-11/STORAGE_VERIFICATION.md), [storage_rights_audit.md](planning/sprint_2026-10-11/storage_rights_audit.md): 11-Oct sprint reports
- [analysis_design_draft.md](planning/sprint_2026-10-11/analysis_design_draft.md), [analysis_implementation.md](planning/sprint_2026-10-11/analysis_implementation.md), [local_eval_implementation.md](planning/sprint_2026-10-11/local_eval_implementation.md), [scorer_implementation.md](planning/sprint_2026-10-11/scorer_implementation.md), [scorer_readiness_audit.md](planning/sprint_2026-10-11/scorer_readiness_audit.md): 11-Oct worker reports
- [paper-b-bank2/EASE_OF_REPLICATION.md](planning/sprint_2026-10-11/paper-b-bank2/EASE_OF_REPLICATION.md): 11-Oct note; bank 2 was finished later
- [C7_CLAIM_LOCK_AMENDMENT_DRAFT.md](planning/sprint_2026-10-11/paper-b-tier1/C7_CLAIM_LOCK_AMENDMENT_DRAFT.md): draft, applied as Amendment C7
- [paper_b/BANK2_LAUNCH.md](paper_b/BANK2_LAUNCH.md): launch note, executed
- [paper-b-tier1/review/](planning/sprint_2026-10-11/paper-b-tier1/review/), [paper-b-tier1/provenance/](planning/sprint_2026-10-11/paper-b-tier1/provenance/): verifier and provenance records
- [paper-b-tier1/cards/](planning/sprint_2026-10-11/paper-b-tier1/cards/): handoff texts of kanban cards T1–T10 and the board script

## Keeping this file true

- When you bank a run, change a claim, or close a card, update this file in the same commit.
  `paper_b/test_status_doc.py` fails if this file quotes a number the table does not hold, pins an old table
  hash, has a broken link, or leaves a planning document out of the map.
- A decision by Augusto gets a row in [planning/DECISIONS.md](planning/DECISIONS.md) with a source: a file, a
  commit or a session id.
- Hermes writes plans to `.hermes/plans/`, which is gitignored. An approved plan moves to `planning/plans/`.
- A superseded document keeps its content and gets the banner `> **Record, not status.** …` under its title.
  Delete only exact duplicates.
- Kanban: SCA2 cards go on board `sca2-paper-b`, and every card result names an artifact path. Refresh
  [planning/KANBAN_LEDGER.md](planning/KANBAN_LEDGER.md) with `python3 planning/kanban_ledger.py`.
- Locks: no country name in evaluation prompts; `data/` stays local; held-out human data only through
  `require_freeze()`; never overwrite Hub `adapters/<CC>` or a bank prefix; pins and amendments are append-only;
  never print `HF_TOKEN`; no push, tag, publish or merge to `main` without Augusto's decision.

## How to re-verify

```bash
cd ~/Desktop/Github_Repositories/SCA2_PofW
git fetch -q origin && git branch -vv && git worktree list && git ls-remote --tags origin
HF_TOKEN= env -u PYTHONPATH .venv/bin/python -m pytest paper_b -q    # includes test_status_doc.py
python3 planning/kanban_ledger.py                                     # refresh the card ledger
```

For the Hub inventory, list `Bonorinoa/SCA2-paper-b-adapters` and `Bonorinoa/SCA2-paper-b-artifacts` with
`huggingface_hub.HfApi.list_repo_files(..., repo_type="dataset")`, and count `adapter_model.safetensors` under
`adapters/` and `bank2/`. Coverage means a `run_record.json` with the right bank id, not just a folder.
