## N1 · Novelty audit: LM evaluation as social-science measurement (sca)

**Root:** `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW` (read-only, except the artifact below).

**Goal.** Before the manuscript rewrite (card M1, gated on this one) uses any "first", "new" or "we introduce"
wording, establish what is already published. Audit Paper B's positioning (see the rules block below, section
"Positioning") against the silicon-sample and LLM-opinion-survey literature: Argyle et al. 2023 and its follow-ups,
Santurkar et al. (OpinionQA), Durmus et al. (GlobalOpinionQA), Bisbee et al., Dominguez-Olmedo et al. ("questioning
the survey responses of LLMs"), fine-tuned survey-response models (e.g. SubPOP), LLM persona prompting across
countries, construct-validity / measurement-instrument framings of LLM evaluation, and LLM-based survey pretesting.
Use the `scientific-paper-strategy` skill's novelty-audit procedure and the `grounded-citations` skill; every cited
work needs a resolvable URL or DOI that you opened. 2025–2026 work matters most.

**Answer these, each with sources:**
1. Has anyone compiled declared group-level benchmark signs into adapters and evaluated them as a scoring instrument
   for *new item text*? Closest three works and how Paper B differs.
2. Is the "order of groups versus answer distributions" contrast (adapters keep the anchor's order, a group-named
   prompt is closer on distributions without the order) reported elsewhere?
3. Which framing words are safe ("we evaluate", "we locate"), which need a hedge, and which are taken.
4. Up to eight references the introduction should cite and does not (check `misc/paper_b/references.bib` on branch
   `paper/paper-b-draft` with `git show paper/paper-b-draft:misc/paper_b/references.bib`), as ready BibTeX entries.

**Artifact:** `planning/checkpoint_2026-10-26/NOVELTY_AUDIT.md`. First line `VERDICT: <novel | partly novel |
pre-empted> — <one sentence>`. Append after each numbered answer. Do not commit; the PM commits it.

**Fence:** write only the artifact. Never open `data/`. Do not edit the manuscript.

**Budget:** about 35 tool calls (your cap is 45).
