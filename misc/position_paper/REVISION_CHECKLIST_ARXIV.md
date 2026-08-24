# ArXiv cut — section-by-section revision (2026-08-23)

**Target only:** `misc/position_paper/position_paper_sca2_arxiv.{tex,pdf}`
**Do not touch:** `position_paper_sca2.{tex,pdf}` (circulating; hash `b3b625c07f8eb33c15835f026c9ea7e6`)

Locked from the user's notes + our reply. Execute in order. Do not skip a section.

## Number gate (must survive)

`0.469` `0.443` `0.375` `0.338` `0.782` `0.453` `p=0.001` `0.886` `0.992` `n=132` `0.60` `0.06` `0.411` `0.413` `0.332` `0.452` `20.5` `526` `658` `0.78` `+0.50` `+0.46`

Forbidden in figures or headline prose: adapter trust `0.70`, posrecip `0.55` as the official cells.

## Sequence

```
S0 figures ──► S1 front/§1 ──► S2 fold §5–6 ──► S3 results ──► S4 appendix prompts
                                                                    │
                                                                    ▼
                                                              compile arXiv
                                                                    │
                                                                    ▼
                                                         adversarial audit + patch
```

### S0 — Figures [S]
Copy G0 heatmap from `analysis/phase2/outputs/figures/fig_heatmap_construct.png` over the paper copy (Aug 20 file still shows 0.70/0.55). Diff other paper PNGs vs analysis outputs; refresh any that differ.

### S1 — Front matter and §1 [M]
- Abstract: method is any declared aggregate; GPS is the first implementation; drop “only these six dimensions” as the method’s scope.
- Drop “scientifically precarious.” Critique of prompting = uninterpretable channel + risk of spurious country orderings. Persona-best-TVD is not a contradiction (still loses to noise).
- Contributions: object, protocol, tests, sixteen-country result. A stated use is not a contribution. Instrument language stays in Discussion.
- Spine stays construction-then-test, not “we decompose DPO vs prompting.”

### S2 — Fold §5 and §6 [L]
- Delete §5 as a section. Keep the five-link table as a short design card at the end of §4.
- Placebo definition moves next to the placebo result (or one paragraph in the card).
- Choice-prob / TVD equations move next to Table 1 or stay in the card.
- §6 shrinks to one short “What we ran” subsection (country frame, GPS as first source, four families + 2×2). Anchor-source table and unrun operator panel stay appendix.

### S3 — Results [M]
- Retitle: not “four surfaces.” Four families on the unconditioned prompt, plus the weights×prompt 2×2.
- One-sentence Falk prior before the development table (patience/trust vs log GDP).
- Do not restate the dissociation after the 2×2.

### S4 — Appendix [M]
- Prompts: teacher, pair generator, profile rendering, training, unconditioned eval, persona eval. Transcribe from code, not memory.
- Leakage audits (scenario text, re-identifiability, country classifier): labeled deferred, not done.

### After
Compile arXiv only. Confirm circulating PDF hash unchanged. Dispatch a read-only adversarial auditor (self-contained brief, <700 words). Patch only confirmed defects.
