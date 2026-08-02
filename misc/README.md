# `misc/` — papers and theory archive

| Path | Role |
|------|------|
| **`position_paper/`** | Current short working paper (`.tex` + `.pdf`). Primary prose surface for the August draft track. |
| `SCA2_Methodology_Argentina_Example.md` | Internal methodology memo (moment tiers, ARG example). Design memory, not the submission vehicle. |
| `main.tex`, `appendix.tex` | Longer “Recursive Cognition / DPO–BT” theory note sources. May need `references.bib` (not yet in-repo) to rebuild cleanly. |
| `dpo_bt_pedagogical_notes.tex` | Standalone pedagogical notes source (PhD-oriented). |
| `Main_DPO-BT.pdf`, `LectureNotes_DPO-BT.pdf` | Compiled PDFs of the theory / lecture materials for non-LaTeX readers. |

LaTeX build artifacts (`*.aux`, `*.out`, `*.toc`, `*.log`, …) are gitignored.

**Not here:** training code (`../DPO_train_test/`), data gen (`../synthetic_generation/`), OOS pack (`../data/merged/`).
