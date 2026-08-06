# Position Paper: v1 vs v2

Two positionings of the same research program and the same empirical results.
**No number differs between them.** What differs is the argument, what is claimed
as the contribution, and which audience the paper is written for.

| | **v1 — `SCA2_PositionPaper.tex`** | **v2 — `position_paper_v2.tex`** |
|---|---|---|
| **Title** | Synthetic Cultural Agents 2.0: Beyond Persona-Prompting | Cheap Measures, Scarce Validity |
| **Length** | 17 pages | **8 pages** |
| **Thesis** | Culture can be encoded structurally into model weights; measurement validates it | Measurement choice is an unmanaged degree of freedom; validity is partial identification |
| **Lead contribution** | The synthetic-agent pipeline (generation → DPO → evaluation) | The admissibility framework + `cvprofiles` instrument |
| **Role of `cvprofiles`** | Validation layer for the pipeline | The paper itself |
| **Role of the adapters** | The main object; the thing being built | One entry in the candidate menu, screened like any other |
| **Organizing spine** | Three cross-literature equivalences (DPO≡Bradley–Terry, option-likelihood≡RUM, network≡moment inequalities) | One equivalence, developed in depth (construct validity ≡ partial identification) |
| **Primary audience** | Econ + AI methods; SCA research program | General social science; measurement/econometrics |
| **USA adapter failure** | A limitation with unresolved mechanism | Evidence the screen works — a measure that should not be admitted |
| **Structure** | 6 sections + 3-tier ladder + frontier applications | 4 sections: bottleneck → framework → two applications → discussion |

## The substantive difference

**v1 is a systems paper.** It argues that persona prompting is reduced-form, that
structural encoding is better, and that measurement discipline is required to make
the claim credible. The pipeline is the achievement; `cvprofiles` protects it. This
framing makes the empirical burden heavy — the adapters must work, and one of the
two does not.

**v2 is a measurement paper.** It argues that AI has made candidate measures abundant,
which converts a scarcity problem into a selection problem economics has no procedure
for. The admissibility framework is the achievement; the adapters are a *demonstration*
that the framework extends to machine-generated measures. This inverts the burden of
proof in a useful way: the AI results become an application of the thesis rather than
the thesis itself.

### Why the inversion matters for the USA adapter

This is the single sharpest difference. The same result reads two ways:

- **v1:** "the matched USA adapter performs worse than both the base model and the
  cross MEX adapter … the mechanism is not identified by this design." A component
  failed, and the paper must absorb it as a limitation.
- **v2:** "a candidate measure was constructed, screened against an external human
  criterion, and *should not be admitted*. The framework's value is precisely that it
  issues this verdict without regard to the measure's provenance."

v2 does not hide the failure — it uses it. A framework that only ever admits its
authors' own measures would be worthless; a framework that rejects one of two
in-house adapters is demonstrating exactly the discipline it advocates.

## Honest disclosure added in v2

v2 introduces a boundary v1 does not state explicitly: **no formal `cvprofiles`
network has yet been run over the adapter menu.** The AI comparison uses out-of-sample
distributional fit against human responses, not a stated set of moment restrictions.
v2 flags this in the body text and names it as the immediate next step. This weakens
the paper's claim slightly and strengthens its credibility considerably.

## What v2 drops

To reach 8 pages, v2 omits: the separate literature-review section (folded into §1),
the Tier-1/2/3 ladder diagram and its detailed provenance discussion, the reliable-vs-
unreliable applications taxonomy (compressed to one paragraph), the frontier-applications
enumeration (compressed into the agenda), the demographic-gradient Stream-B results,
and roughly half the bibliography. These are not errors in v1 — they are the cost of a
tighter argument, and several belong in a methods appendix rather than a position paper.

## Aesthetic changes in v2

- Warmer three-colour palette (ink navy / teal / burnt-orange accent) replacing v1's
  monochrome blue
- Two reusable framed environments: `\panel` (neutral, for framing text) and
  `\callout` (accent border, for headline findings) — used to give the two key claims
  visual weight without bolding entire paragraphs
- Run-in `\paragraph` headings, tighter leading, one figure instead of two
- Tables reduced from `\scriptsize` to `\small` with fewer columns (the v1 six-column
  results table became four columns)

## Build status

Both compile clean with `pdflatex` (two passes, 0 errors, 0 undefined references):

- v1 → 17 pages
- v2 → 8 pages (limit was 12)

A `\cdot` in v1's `fancyhead` — a math-mode command in a text-mode header — was
opening math mode at every page shipout past page 1 and causing a fatal
`Missing $ inserted`. Fixed to `\textperiodcentered`; v2 uses the same corrected idiom.

## Recommendation

These are complements, not competitors. v2's framing is the stronger one for a
general-science venue: the measurement thesis is broader, the claim is better supported
by what has actually been executed, and the honest treatment of the USA adapter turns
the program's weakest empirical result into evidence for its central argument. v1
remains the better document for an audience that wants the pipeline in full detail.

The decision worth making deliberately: whether the SCA program is *a way to build
cultural agents* (v1) or *a way to know which measures of culture can be trusted* (v2).
