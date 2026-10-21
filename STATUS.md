# SCA2 status

**Last verified: 2026-10-20 evening (MST) by the orchestrator (`default`)**: git, the claim lock (Amendment C9.1 and its audit note), the numbers table, the manuscript commit, the deployed Space (file-by-file) and the board cards. The Hub inventory below dates from 2026-10-19 and was not recounted. Commands are in
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
| **Paper B** (the journal version of the preprint, for SMR) | Compute and analysis done through Amendment C9. C9-4 experiment A ran on 42 countries and fills the adapter+persona TVD cell. Experiment B ran on 42 adapters and is banked by Amendment C9.1 (8 rows). The cross-family audit of both (card `t_b4030219`, Codex) ACCEPTED them on 2026-10-20; all C9 rows are descriptive and quotable as such. The manuscript carries the C9 results since `a467da0` (sections 5.8 to 5.11, a discussion paragraph, supplement Tables S9 to S15; both number audits PASS; abstract, introduction and conclusion not yet updated). Waiting on the decisions listed under [Open after the checkpoint](#open-after-the-checkpoint). | code `feat/paper-b-cohort`; manuscript `paper/paper-b-draft` |
| **Workbench** (Adapter-Brain-Vizualization) | SCA2-specific viewer that reads Paper B artifacts, one way only: Paper B claims never depend on workbench results, and its compute stays separate. Private precomputed Space, redeployed 2026-10-20 as v1.1 with the C9 step (polished for projection) and the W2 prompt-route captures (WB3 and WB3.1, both independently verified; no human data, no weights, no inference). Its analyses (W2 prompt route, W3 mechanisms) are not Paper B evidence; see `workbench/AUDIT.md` §17 on its branch. | worktree `.worktrees/adapter-brain-vizualization`, branch `Adapter-Brain-Vizualization`; [workbench README](https://github.com/EconLLM-Lab/SCA2_PofW/blob/Adapter-Brain-Vizualization/workbench/README.md) |
| **Phase 3** (activation engineering, latent space) | Not started. | — |

## Checkpoint 2026-10-20 (co-author review)

Assembled by card `t_5b53fef3` on 2026-10-19 evening for the 08:00 MST 2026-10-20 co-author meeting. The sections below
name what exists and what does not. Git decides the heads: the commits listed are the ones this section builds on, and
the checkpoint commit and its merge sit on top (`git log -3` on each branch).

| Item | State |
|---|---|
| Git heads entering final assembly | `feat/paper-b-cohort` `16de598` (C9-4 experiment A admitted); `paper/paper-b-draft` `a75bf1a` (merge of `16de598`); `Adapter-Brain-Vizualization` `e27e279` (checkpoint documentation; later W2/W3b files remain local and unpushed) |
| Numbers table | 562 rows, sha256 `71ee7c8c68eb856bf7215165dd836aef7cc3f67993a6523790cee4b22ce186a4` (Amendment C9.1 appended 8 label-recovery rows); the 271 C8 rows and the 554 C9 rows are unchanged and pinned by tests |
| Amendment C9 (2026-10-20) | 283 descriptive, not preregistered rows: C9-1 human agreement, C9-2 TVD (all four cells, the adapter+persona cell filled by the 2026-10-19 C9-4 run), W1 cross-talk decomposition. No claim earned. Coauthor sign-off pending. In [the claim lock](planning/TWO_PAPER_CLAIM_LOCK.md) |
| Verifier record | [VERIFICATION_C9.md](planning/sprint_2026-10-11/paper-b-tier1/results/c9/VERIFICATION_C9.md) (cross-family): C9-1 ACCEPT, the original three-cell C9-2 ACCEPT, W1 ACCEPT as descriptive, 96 headline values recomputed with 0 mismatches; insights I1 and I2 both WEAK. [C9_GPU_VERIFICATION.md](planning/sprint_2026-10-11/paper-b-tier1/results/c9/C9_GPU_VERIFICATION.md) BLOCKED the first C9-4 attempt because it executed neither experiment. [C9_4_VERIFICATION.md](planning/sprint_2026-10-11/paper-b-tier1/results/c9/C9_4_VERIFICATION.md) (cross-family, Codex `gpt-5.6-sol`): the genuine C9-4 experiments A and B ACCEPT on all six checks, 42/42 countries on the Hub for both runs, independent recomputation equal to the 562-row table, mutation test caught. `workbench/plans/W2_VERIFICATION.md` on the workbench branch: W2 PASS-WITH-NOTES |
| Private Space | https://huggingface.co/spaces/EconLLM/sca2-workbench (static, private). v1.1 deployed 2026-10-20 from workbench commit `67200ce`: 142 of 142 bundle files equal the WB3.1 manifest by sha256 and size (payload 0.918 GB), stage RUNNING, the C9 step and its data serve with HTTP 200; WB3.1-V (`t_42d33a08`) PASS. The Space has a 1 GB storage cap; keep the payload at 0.95 GB or less. Moved to the EconLLM organization on 2026-10-19. Co-author access still needs invites from EconLLM (Augusto) |
| Hub runs added | `adapter-persona-strict-v1-20261019`: 42 of 42 countries, gates G1/G2/G3 passed before any scoring, about one compute unit (balance 181.82 → 180.75). `label-recovery-cohort1-v1-20261019`: experiment B, scoring the 42 cohort-1 adapters on the 132 held-out pairs, gates passed (base reproduces the banked cohort-1 reference log-probs with max gap 0, ARG adapter effect 71 nats, switchback exact); 42 of 42 adapters scored and read back; banked by Amendment C9.1. Both runs together: 181.82 → 178.87, about three compute units; session stopped |
| Workbench cards | WB1 PASS, WB2 deployed, WB3 (C9 step + prompt-route captures) PASS and deployed as v1. W2 prompt-route queue: FINISHED 2026-10-19 23:32 MST, 598 of 598 units; code committed (`74d3a06`); W2-V (`t_5a3e5144`) PASS-WITH-NOTES (parity with the archived run within about 0.11 nats); the 17 GB capture is local only, nothing uploaded. W3: verifier BLOCK, no W3 number is quotable. W3b produced a post-checkpoint run, figure and report, but its independent audit BLOCKED an unregistered p<0.05 classifier; no W3b number is accepted |
| Brief | [COAUTHOR_BRIEF.md](planning/checkpoint_2026-10-20/COAUTHOR_BRIEF.md): two pages, every number by claim id (25 ids, 49 values, 0 mismatches against the table); refreshed after experiment A and the Space transfer without adding an unaudited C9-4 number |
| Gate | V and A are done. Final assembly starts from code `16de598`, manuscript merge `a75bf1a` and workbench checkpoint `e27e279`; all three matched origin before the final documentation commits. C9-4 experiments A and B are banked and accepted by the cross-family audit. W2 finished and PASSED its verification with notes. W3 and W3b remain blocked and are not Paper B evidence. See the assembly recheck below |

### Assembly recheck, 2026-10-19 evening

The first C9-4 producer attempt supplied only a 16-country fixture and was correctly BLOCKED by the independent audit.
The orchestrator later ran genuine experiment A on all 42 countries. Those outputs exposed a real builder defect:
`build_numbers_table.py` only knew three TVD cells and raised `KeyError('adapter_persona')`. The fix adds the fourth
cell and its interaction contrast; the table was rebuilt to 554 rows, the 271 earlier rows stayed byte-identical, and
the claim lock and this file were updated. The current main-worktree `paper_b` suite is green (611 passed). The new
rows remain unquotable until an independent cross-family audit accepts the genuine run. Experiment B finished later
(42 of 42) and is banked by Amendment C9.1, under the same audit.

**Internal presentation checkpoint: CLOSED 2026-10-20 19:30 MST** (readiness card `t_ed70bc80`, all six checks PASS):
C9-4 audit ACCEPT; manuscript carries the C9 results with both number audits PASS (482/482, 525/525); Space v1.1 equals
its manifest (142/142); all three branches match origin. W2 finished 598 of 598 units and is verified. The only
uncommitted workbench file is `analysis/w3b/run_w3b.py`, which belongs to W3b (post-presentation). W3b's independent audit reproduced its registered numbers but
BLOCKED the artifact because its results and report add an unregistered p<0.05 classifier. The three unfinished W3b
orchestration cards are explained in the completion comment and remain outside Paper B.

The main and manuscript worktrees were clean before this final documentation pass. The full suite is run only from
the main worktree, as required by `AGENTS.md`; the manuscript worktree lacks local-only data and its own `.venv` and
is not an equivalent validation environment.

## Git

| Ref | Head | Note |
|---|---|---|
| `paper/paper-b-draft` | see [Checkpoint](#checkpoint-2026-10-20-co-author-review) | **The single merged branch to pull.** It holds the manuscript in `misc/paper_b/` (worktree `../SCA2_PofW-paper-b-draft`) plus all of `feat/paper-b-cohort`. |
| `feat/paper-b-cohort` | code branch (this worktree) | Paper B code, results, claim lock. Merged into the branch above after every commit. |
| `Adapter-Brain-Vizualization` | see [Checkpoint](#checkpoint-2026-10-20-co-author-review) | Workbench. Not merged anywhere. |
| `main` | local `2e4989b`, origin `305d820` | Local main is 1 commit ahead (the arXiv upload package), unpushed. Paper B is not merged to main. Untouched at the checkpoint. |
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
**C8** (persona arm), all 2026-10-18, and **C9** (descriptive human-agreement, TVD and cross-talk rows, 2026-10-20;
coauthor sign-off pending). In short: neither additional locked claim is earned, and C9 earns none. Paper B is a
preregistered evaluation of the sign compiler as a scoring instrument: what holds, what fails, and what is untested.
The held-out result is a *retrospective* screen against WVS-7, never "transport". Pre-piloting is untested, and no
human route exists in 2026.

[NUMBERS_TABLE.csv](planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv): 562 rows, sha256
`71ee7c8c68eb856bf7215165dd836aef7cc3f67993a6523790cee4b22ce186a4`. It replaces the 271-row table `51ddcce1…97855`;
those 271 rows are unchanged and a test pins it. The 283 `C9_` rows are all descriptive and not preregistered.
A rebuilt table needs a new dated amendment and an update here; `paper_b/test_status_doc.py` fails until both match.

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
| C9, descriptive: trust adapter–human, cohort-1 adapters, 42 countries | 0.295 [−0.044, 0.547] | `C9_a_adapter_human_trust_spearman_rho` |
| C9, descriptive: trust human–GPS, 42 countries | 0.351 [0.088, 0.564] | `C9_a_human_gps_trust_spearman_rho` |
| C9, descriptive: human between-profile share on trust, 28 multi-member countries (inconclusive; low power) | 0.384 | `C9_c_human_trust_between_share_multi_member` |
| C9, descriptive: true between-share needed for 80% power, 12 groups | 0.568 | `C9_c_design_12_group_multi_member_design_interpolated_true_between_share_at_80_power` |
| C9, descriptive: mean TVD to humans, base model | 0.470 | `C9_TVD_base_mean_tvd_country_equal` |
| C9, descriptive: mean TVD to humans, cohort-1 adapters | 0.515 | `C9_TVD_adapter_mean_tvd_country_equal` |
| C9, descriptive: mean TVD to humans, country-named persona | 0.365 | `C9_TVD_persona_mean_tvd_country_equal` |
| C9, descriptive: TVD, adapters minus base (profile-block) | 0.045 [0.006, 0.093] | `C9_TVD_adapter_minus_base_profile_block` |
| C9, descriptive: TVD, persona minus base (profile-block) | −0.105 [−0.122, −0.086] | `C9_TVD_persona_minus_base_profile_block` |
| C9 W1, descriptive: trust, main-effects prediction vs GPS (behavioral decomposition) | 0.834 | `C9_W1_trust_spearman_full_vs_gps` |
| C9 W1, descriptive: trust, covariance share of the cross-bit term | 0.287 | `C9_W1_trust_cross_cov_share` |

## Manuscript

`paper/paper-b-draft`, `misc/paper_b/`: main text 40 pages and supplement 9 pages at `ae1099f`, with number audits
311/311 and 297/297 and an independent check showing 0 mismatches. Overleaf review copy: a new project per
version. The current one is "Synthetic Cultural Agents as Scoring Instruments… (1)", uploaded 2026-10-19; Augusto
has still to confirm the page count. The older Overleaf projects are untouched. The preprint is disclosed only on
the title page and in `submission/COVER_LETTER_DRAFT.md`; the manuscript never cites it.

## Open after the checkpoint

Targets are proposals for Augusto. "Blocked by" names the decision or card that must come first.

| Item | Owner | Target date | Blocked by |
|---|---|---|---|
| Coauthor sign-off on C7, C7.1, C8 and C9 | Augusto | co-author meeting 2026-10-20 | the meeting |
| Author list and order | Augusto | 2026-10-20 | the meeting |
| OSF registration | Augusto | before SMR submission | sign-off |
| Anonymous mirror | Augusto | before SMR submission | author list |
| IRB, COI, funding, compute and AI-use statements | Augusto | before SMR submission | none |
| SMR preprint policy (disclosure of arXiv:2610.06562) | Augusto | before SMR submission | none |
| Overleaf page count (project "… (1)") | Augusto | 2026-10-21 | none |
| Invite co-authors to the EconLLM Hugging Face organization and grant access to the transferred private Space | Augusto | 2026-10-20 | none |
| Confirm the definition of "recursive generalization" | Augusto | 2026-10-21 | none |
| Optional: the label-fidelity finding in the abstract, introduction and conclusion (C9 is in results and discussion only) | Augusto, writer | before co-author sharing | Augusto's go |
| Optional v1.2 of workbench step 4: supporting text at 14 px or more, recovery-dot jitter (WB3.1-V N1, N2) | `engineer`, verifier | before projection | Augusto's look at v1.1 |
| `build_deploy_bundle.py`: drop the hard-coded engineer scratch path; resolve symlinked scratch (WB3.1-V N3) | `engineer` | with the next bundle build | none |
| Novelty audit "LM evaluation for social-science measurement" | `sca` | 2026-10-23 | none |
| Space landing footer wording contradicts the journal-version framing | `engineer` | 2026-10-21 | none |
| Upload the W2 prompt-route captures to the Hub (17 GB, local only); weights-versus-prompt analysis of the risk inversion | `engineer` | 2026-10-21 | none |
| Resolve the W3b audit BLOCK: owner decision on removing the unregistered p<0.05 classifier (recommended) or labelling it as dated exploratory output; package the renderer/report; complete the existing verifier lane; repeat W3 with the prompt route | Augusto, `engineer`, verifier | 2026-10-22 | Augusto's scope decision; W2 for the prompt-route repeat |
| Clean the workbench tree: WB1 findings F1 to F5 (W2 code committed, W3 stubs quarantined in `_discarded_W3/`) | `engineer` | 2026-10-22 | W3b finished |
| Extract a general (non-SCA2) workbench repository | `engineer` | 2026-10-23 | WB cleanup |
| Parity reference in float64 for the next capture run | `engineer` | with the next capture run | next run |
| Live adapter chat card with a cost and data-rights check | `engineer` | 2026-10-26 | Augusto's go |
| Public workbench release | Augusto | after co-author review | sign-off; data-rights check |
| Data review before Paper B is shared: purge or keep the git history of the six untracked human-derived CSVs; the three copies on `main`; tracked bank-1 `D_syn_*.jsonl`; `paper_a/country_item_scores.csv`; GPS PDFs | Augusto | with SMR submission prep | the decision on a force-push |
| Paper C candidate: magnitude-graded compiler design and preregistration | Augusto, `sca` | early November | the sign-profile evaluation concluded |
| Housekeeping: the creative profile's false positive in the no-PAYG check; data-scientist `max_turns` and a real-browser profile; the check script needs `pyyaml` | `sca` | 2026-10-24 | none |

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

- [TWO_PAPER_CLAIM_LOCK.md](planning/TWO_PAPER_CLAIM_LOCK.md): claims, Paper A table, Paper B amendments C7, C7.1, C8, C9
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
- [paper-b-tier1/results/c9/](planning/sprint_2026-10-11/paper-b-tier1/results/c9/): C9 outputs (human agreement, TVD, W1 decomposition), the cross-family verification `VERIFICATION_C9.md` and the C9-4 audit `C9_GPU_VERIFICATION.md` (BLOCK); descriptive, not preregistered. Nothing in that folder is a C9-4 result
- [planning/checkpoint_2026-10-20/](planning/checkpoint_2026-10-20/): the co-author brief `COAUTHOR_BRIEF.md`, the shared sprint rules `common_rules.md`, and `cards/` (texts of the 2026-10-19 sprint cards, exported as dated records)
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
