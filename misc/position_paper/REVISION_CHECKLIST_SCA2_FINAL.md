# SCA2 position paper — final-pass revision checklist

**Drafted:** 2026-08-23. **Status:** LOCK PENDING (do not edit `.tex` until the RESOLVED block is filled).
**Artifact:** `misc/position_paper/position_paper_sca2.{tex,pdf}` (last compile 2026-08-21 22:26, 20 pp letter).
**Venue lock for this pass:** PNAS Nexus Research Report is the *ambition*, not a grant. Style conversion is Task S1 and is blocked by G0.

## Pre-declared evaluation (this session)

Rubric locked *before* scoring, from the journal's own instructions
(`academic.oup.com/pnasnexus/pages/general-instructions`, extracted 2026-08-23)
plus the lab's claim-discipline rules:

| ID | Criterion | Source |
|---|---|---|
| R1 | Exceptional importance / outstanding advance | Nexus RR definition |
| R2 | Interdisciplinary breadth | Nexus aims/scope |
| R3 | Novelty vs 2025–26 frontier | lab literature map |
| R4 | Evidentiary support for headline claims | claim discipline |
| R5 | Claim / identification discipline | skill + paper's own boundary |
| R6 | Completeness of the predeclared design | Table 2 five links |
| R7 | Replicability (numbers from committed artifacts) | V1 gate |
| R8 | Presentation / journal readiness | Nexus format + 12-page cap |
| R9 | Desk-reject risk (invert: high = bad) | Tier-1 editorial screen |

**Verdict of this session (see chat):** NO-GO for PNAS Nexus *now*. SMR is the honest current home. Nexus remains the stretch target after G0–C3. arXiv: wait for G0 + identity pass, then yes as a labeled working paper (Nexus explicitly permits preprints).

## Number-preservation gate (grep after every pass)

These strings must still appear *or* be replaced by the single frozen construction chosen in G0, with the replacement recorded here:

- TVD: `0.469`, `0.443`, `0.375`, `0.338`
- Placebo: `0.782`, `0.453`, `p=0.001`
- Held-out: `0.886`, `0.992`, `n=132`
- 2×2: `0.60`, `0.06`, `0.78` uncond, `0.411` / `0.413`
- Temp: `0.469` → `0.332`, top-match `0.452`
- CF_ST: `20.5`, `11` nearest CAN
- Sign profiles: `35`, `13`
- Training: `526`, `658`, `β=0.1`, `r=16`

**Do not grep-preserve `0.70` or `+0.56` until G0 decides which construction they are.**

## Task map

```
G0 (blocker) ──► C1 identity ──► C2 compress ──► C3 SI pack
                      │
                      ├── B1 citations
                      ├── B2 disclosures
                      └── N1 last-48h experiments
                                 │
                                 └── S1 style (Nexus template)  [after C2]
                                          │
                                          └── A1 arXiv checklist
```

### G0 — Number freeze  [L, BLOCKER]

Re-derive Table 2 / development partials / figure captions from one named script + one committed CSV. Record the triple:

- construction name (exact recode + missing-code order)
- file path
- rounded value used in prose

**Observed conflict (2026-08-23, this session):**

| Claim in paper | V1 ledger (2026-08-20) | committed `unified_construct_bridge.csv` / `table_construct.tex` (2026-08-21 07:09) | `2x2_bridge.csv` / placebo |
|---|---|---|---|
| adapter trust ρ `0.70` | `0.70` | **`0.78` / `0.782`** | `0.703` |
| posrecip adapter `0.55` | `0.55` | **`0.48` / `0.479`** | — |
| trust edu-partial `+0.56` | `+0.56` | committed `unified_development.csv` **`0.501`** | — |

Paper footnote currently says unified = 0.70 and majority-threshold = 0.79. That footnote does not describe the file now named `unified_construct_bridge.csv`. Do not write results prose until this is resolved. Do not “pick the nicer number.”

### C1 — Identity pass  [M]

The draft is two papers stapled together: a future-tense protocol and a completed 16-country report.

- Delete or rewrite the cover status box (lab-internal).
- §1 last sentence currently says results are “deliberately not pre-judged.” False.
- §6 still “will archive / before a scaled run.” Either past tense + what *was* frozen, or move the unrun panel to SI as a registered-design remainder.
- Appendix D (“artifacts required for a claim-ready version”) cannot survive a public preprint.
- Appendix B (static audit that could not run tests) is not evidence. Kill or shrink to a one-paragraph provenance note.
- Appendix A stays SI only, labeled superseded.
- Discussion must metabolize the dissociation, 2×2, placebo restriction, non-LLM floor, and sign-profile collapse. Current Discussion is generic.

### C2 — Compress main text  [L]

Target for a Nexus-shaped main file: ≤ ~4,500–5,000 words excl. SI/refs, abstract ≤ 250, ≤ 6 display items in the main file, math carries the object.

**Keep in main (canonical statements, cite once):**
- object + boundary (eqs. protocol, policy)
- DPO as pairwise estimator, not a moment constraint (eq. DPO)
- choice probability + TVD (eqs. choiceprob, TVD)
- five-link table (one page)
- one results spine: shape loss / direction win / placebo / 2×2 one paragraph / non-LLM one paragraph
- cultural-distance *prose* (this is the only culture section — do not collapse to one sentence)

**Move to SI:** operator-sensitivity unrun panel, anchor-source table, training-config table, most of §6, all current Supplementary figures except one shape figure and one bridge figure, two-country pilot, readout τ-grid, mixture-failure note.

**Do not delete hedges.** Delete *repetition* of the same hedge.

### C3 — SI pack  [M]

Separate `si_sca2.tex` (or an `\appendix` that starts on a new page with S-numbering already in place). Main PDF should be able to hit ≤ 12 Nexus pages after two-column conversion; SI is unlimited.

### B1 — Citations  [S]

Mechanics are clean (30/30 bibitems cited; 0 undefined refs). Remaining content fixes:

- Prose L309: “Pfeifer & Dalloul” → Dalloul & Pfeifer (bib already correct).
- Add a Schwartz cite or drop the name.
- Bib key `inghlehart2005` is a typo (Inglehart). Harmless but ugly.
- `golan1996`: author is Amos Golan, not “J. Golan.”
- Suh 2025: add ACL long locator `2025.acl-long.1028` (already web-verified).
- Orphan floats: 6 equations and `fig:pipeline` are never `\ref`'d. Either cite them or they are decoration.
- Unused SI figure labels (`fig:S-tvd-heat` etc.) are fine if the SI caption is the only pointer; prefer one sentence in SI text.

PNAS Nexus is format-neutral at initial submission (any readable style). Do not restyle the bibliography until S1.

### B2 — Disclosures required by Nexus (and by SMR)  [S]

Missing: Significance Statement (50–120 words), corresponding-author email, funding or no-funding statement, generative-AI disclosure in Methods/Acknowledgments, CRediT (entered in the submission system, not the tex).

### N1 — Last 48 hours of experiments  [S, content decision]

| Experiment | Status | Paper now | Decision (proposed) |
|---|---|---|---|
| Restricted placebo | complete, committed | in | keep; label *restricted* (no retrain) |
| 2×2 weights × prompt | complete, committed | in | keep; one paragraph + SI table |
| Non-LLM maxent / sign-follower | complete, committed | in | keep; one paragraph + SI table |
| Softmax readout τ-grid | complete, **uncommitted**, paper untouched by prior decision | out | SI operator diagnostic only. Confirms: ordering adapter>base>persona at every τ; adapter−base TVD gap → 0 as τ↑; distance-gauge ρ(\|Δz\|, policy TVD) ≈ 0 |
| Rung-mixture intensity basis | Gate 2/3 failed; country blends **never scored** | out | SI/lab note: “we tried to build an intensity basis; +3 left the line.” Not a result. Do not spend another month on it for this paper |

Do **not** let N1 rewrite the thesis. The last two days strengthen the already-stated boundary (direction, not magnitude/shape). They are not a new main-text win.

### S1 — Journal look  [M, blocked by G0+C2]

Convert to the official PNAS Nexus Overleaf class (`oup-authoring-template` / [Overleaf `pnas-nexus`](https://www.overleaf.com/latex/templates/pnas-nexus/wfqcdvjdrqmz)), two-column, Significance Statement, numbered refs. Visual QA via `pdftoppm` after compile. **Do not do this to the current 20-page lab draft.** Cosmetics before the cut produces a Nexus-lookalike that still fails R1/R7/R8.

Fallback if Nexus is abandoned: SMR has no length target (~10k typical), Sage author-date, required preregistration *statement* (“this study was not preregistered” is allowed).

### A1 — arXiv  [S, blocked by G0+C1+B2]

Nexus verbatim: authors may post an Author's Original Version; this does not prevent submission. Sufficient conditions for *this* paper:

1. G0 frozen and grep-clean
2. Identity pass (no “not pre-judged,” no “claim-ready later,” no lab status box)
3. Abstract ≤ 250; Significance drafted
4. Code/data statement names a commit or tag
5. AI + funding statements present
6. Authors sign off on the claim boundary in the abstract

Then: arXiv `econ.EM` + `cs.CL` (or `stat.ME`). Not before.

## Open questions (answer verbatim; I will copy into RESOLVED)

1. **G0 construction.** Which trust-bridge number is the paper's official one: the V1/placebo/2×2 `0.70`/`0.703`, or the committed `unified_construct_bridge.csv` `0.78`? (I will not choose.)
2. **Venue for the *next* compile.** Keep writing toward Nexus (12-page main + SI) or switch the working format to SMR (~10k, less crush)?
3. **Appendix B.** Kill, or one-paragraph “pipeline changed after audit” note?
4. **arXiv timing.** After G0+C1 only (working-paper timestamp), or after the full C2/S1 pass?
5. **Style now.** Confirm: no template conversion until G0+C2.

## RESOLVED

- **Q3 Appendix B.** Kill. Done 2026-08-23 (section removed; training config is now Appendix B).
- **Q5 Style.** Confirmed: no template conversion until G0+C2.
- **Q4 arXiv formatting.** Leave for last. No preprint until G0 is frozen and a stranger can rerun from published artifacts.
- **Q2 Venue.** Locked 2026-08-23: arXiv after G0+public eval banks; **SMR** is the immediate journal target; **NCS** is the stretch compression (3,500-word Article); Nexus is brand/transfer, not the cite argument; PA only with a multi-country political surface (local AB is USA/MEX only).
- **Q1 G0 construction.** Frozen 2026-08-23: **E[recode(V)] / P(option 1)** on binaries; linear recode on Likert. Script 13 = 17 = 18. Official adapter trust **0.782** (tables 0.78). Placebo: real 0.782 vs q95 0.453, p=0.001 (self-check vs script 13 passed). 2×2: uncond 0.782 / persona 0.597 / base-persona 0.065. recode(E[V])=0.70 retired as the Q57-zeroing estimator.
