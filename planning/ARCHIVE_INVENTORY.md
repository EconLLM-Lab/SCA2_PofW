# Archive inventory — do not delete until Augusto signs this list

> **Record, not status.** Written 2026-09-16. Lines about what is done, blocked or next describe that date, not today. Current status: [STATUS.md](../STATUS.md). Paper A era.

**2026-09-16.** Goal: stop *citing* superseded surfaces. Goal is not `rm`.

## Stop. Working-tree hazard

`SCA2_PofW` is `main` ahead of `origin/main` by 1, and the **working tree
has already deleted** the circulating paper source and related files
(`misc/position_paper/position_paper_sca2.{tex,pdf}`, arXiv fork, figures,
protocols, phase-2 report, notebooks). They still exist in `git HEAD`.

The file people are reading is the **untracked**
`misc/position_paper_sca2_revised.pdf`.

**Before any cleanup commit:** restore or explicitly retire those paths.
Proposed restore (needs your yes):

```bash
cd ~/Desktop/Github_Repositories/SCA2_PofW
git checkout HEAD -- misc/position_paper protocols reports notebooks
```

Do not `git clean`. Do not overwrite `position_paper_sca2.pdf` with the
revised PDF; keep a sibling name.

## Cite-never (keep on disk; tombstone in README)

These are real artifacts of older estimands. HASHES.md currently pins several.

| Artifact | Why it pollutes | Fate |
|---|---|---|
| `analysis/phase2/tables/table_construct.tex` (trust 0.78) | 30-item / older recode | Keep; header: not Paper A |
| `analysis/phase2/outputs/construct_bridge_by_dimension.csv` (0.79) | Same | Keep; not Paper A |
| `analysis/phase2/outputs/unified_construct_bridge.csv` (0.70 family) | Script-13 30-item | Keep; not Paper A |
| `analysis/phase2/outputs/2x2_bridge.csv` (0.78 / 0.60 / 0.06) | Not space-prefix 16×23 | Keep; not Paper A |
| `analysis/phase2/outputs/unified_summary_pooled.csv` (TVD 0.469…) | 30-item distributional | Keep; not Paper A |
| `replication/HASHES.md` as currently written | Freezes the rows above | Rewrite hashes **after** Paper A table regen exists |
| Skill `references/phase2-canonical-numbers-2026-08.md` | Calls 0.70 “paper headline” | Stamp SUPERSEDED; pointer to claim lock |
| `Hermes/Projects/SCA2_results_audit/` | Audit trail of 16×23 | **Keep** — this is how 0.80 was built |
| `DPO_train_test/`, `DPO_eval_WVS/` | Historical training/eval | Keep as protocol history |
| `analysis/phase2/19_*`, `20_*`, `21_*`, rung/readout untracked | Different experiments | Do not mix into Paper A tables |
| `Hermes/Projects/SCA2/empirical_application_rewrite.tex` | Partial rewrite, not the PDF | Keep as notes |

## Safe to ignore in context (not delete)

Finder copies (`"runs/.gitignore 2"`), `.DS_Store`, empty `arxiv_preprint/`,
empty `analysis/` except `phase2/`, cvprofiles paper numbers, SCA1 Henrich tables.

## Do not touch

- Frozen option-probability banks under `data/phase2/raw/` (gitignored).
- Adapter checkpoints / HF private repo.
- GPS/WVS microdata.
- `misc/presentation/` (Duch meeting).
- Any file the revised PDF’s evidence ledger names, once that ledger is
  located next to the PDF.

## What actually pollutes future sessions

Not the CSVs. The **skills and memory** that still treat 0.70/0.78/0.469
as current. Fix: load `sca2-canonical-surface` and the claim lock first;
do not quote HASHES construct ρ as the draft.

## Sign-off

- [ ] Restore or retire deleted `misc/position_paper/` from HEAD
- [ ] Point README at the actual PDF path
- [ ] Stamp superseded tables; do not `rm`
- [ ] Regen Paper A tables + new HASHES
- [ ] Augusto yes before any `git add` of deletions
