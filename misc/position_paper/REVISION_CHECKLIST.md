# SCA 2.0 Position Paper — Revision Checklist (draft for discussion)

Date: 2026-08-06 · Repo: `misc/position_paper/` · Target: ~16 → 12–13 pages, numbers unchanged.
Status: PRE-IMPLEMENTATION PLAN — discussed with Augusto, not yet executed. Each item lists the
evidence verified in the repo on 2026-08-06 (marked [VERIFIED]) so implementation does not re-derive it.

---

## Sequencing principle

Dependencies run top-down: **Task 0 grounds Tasks 2, 3, 4** (they all quote the z-score story);
**Task 5 (Figure 1 redesign) is independent** of prose edits and can be drafted in parallel;
**Task 8 (compression) is last** so cuts happen on the final text, not twice.

```
0 → (2 → 3 → 4) → 6 → 7 → 8     (1 and 5 independent; 1 can go any time after 2)
```

Estimated effort per item is relative (S/M/L). Build-verify (pdflatex, 2 passes, 0 errors,
0 undefined refs) is required after every item that touches the .tex — run once at the end of
each batch rather than per item.

---

## Task 0 — Ground the GPS "anchoring" story in the pipeline code [EFFORT: M] [BLOCKS: 2,3,4]

**Why:** The paper currently asserts a "GPS cultural state vector" without stating the
transformation or the labeling rule. The interpretation of every Tier-2 number depends on it.

**Evidence already verified in the repo (2026-08-06):**
- `synthetic_generation/sca2_datagen/profiles.py:63` prints the GPS state vector as
  "standardized deviations from global mean" — i.e., **z-scores**, not raw country means. [VERIFIED]
- Synthetic labeling uses the **sign** of the z-score: `chosen_option = "A" if z_c[dim_key] >= 0 else "B"`
  (`synthetic_generation/tests/test_generate.py:271`). [VERIFIED]
- WVS items are pre-registered in `WVS_ITEM_MAP` (`synthetic_generation/sca2_datagen/config.py:90–119`)
  with a **tier field**: tier 2 = evaluation items, **tier 3 = held-out moments reserved for
  validation (never used in training or testing)**. [VERIFIED]

**Deliverable:** a short prose block for §3.1 "Primitives" that states, in order:
1. GPS country scores are standardized deviations from the global mean (Falk et al. 2018
   convention, as read from the pipeline config);
2. the state vector entering the pipeline is therefore interpretable as "country c sits
   $z$-SDs above/below the global mean on dimension $d$";
3. the labeling rule is sign-based: for each scenario the country's $z_c$ selects the option
   whose behavioral content loads positively on that dimension;
4. **interpretation caveat (one sentence):** the adapter is trained toward a
   *GPS-instrument-measured* construct, so Tier-2 alignment is with that proxy, not with
   "Mexican preferences" in the abstract.

**Verify before writing:** read `profiles.py` `load_gps_data`/`extract_gps_vector` and the
pair-generation function to confirm (a) the z-score source file, (b) that option-level scoring
uses the sign rule (and what happens at $z_c \approx 0$), (c) whether thresholds other than 0
are used anywhere. Do NOT quote the z-score convention from the test file alone — confirm in
the generation code path itself.

---

## Task 1 — Title/positioning decision (keep vs. pivot) [EFFORT: S] [INDEPENDENT]

**Recommendation (from discussion):** keep **"Synthetic Cultural Agents 2.0: Beyond
Persona-Prompting"**; do not move "verifiable research loop" into the title.
- *Why:* the title challenges the status quo (SCA 1.0's own method included) and signals an
  upgrade path, which is a constructive-reviewer framing. "Verifiable research loop" promises
  the mechanism without saying what the fight is about.
- *Actions:* (a) optionally weave loop language into the subtitle or the final intro
  paragraph ("…closes a verifiable research loop: estimation → evaluation → measurement
  validation → retraining"); (b) add **one sentence in §2.5 distinguishing the Dell–Rambachan
  *proposal* from our *operational instrument* with frozen-run discipline** — this is a
  positioning risk the current draft leaves open; (c) in print, soften "spurious" claims about
  persona-prompting literature to "reduced-form / under-identified" (the draft already uses
  "reduced-form"; keep that register).

**Decision needed from Augusto:** (1) keep title as-is (recommended), (2) keep title + loop
language in subtitle, (3) full pivot. Item (c) is non-negotiable for a PNAS/Nature-class venue.

---

## Task 2 — Abstract: split into two clean paragraphs, raise info density [EFFORT: S]

**Current problem:** one ~240-word block mixing pipeline, instrument, applied result, and
application taxonomy.

**Target structure:**
- ¶1 (problem + pipeline): WEIRD-alignment problem → indirect encoding (state enters only via
  training labels; the country is never named) → pipeline = synthetic experiments on cultural
  states. **Drop:** QLoRA/Llama-3.1-8B specifics (move to §3.1), the word "six-dimensional"
  (keep "six GPS dimensions" only if it fits), the reliable/unreliable taxonomy (belongs in §5).
- ¶2 (instrument + evidence): nomological network as partial identification → cvprofiles
  (score/restrict/identify/report) → trust example headline (3 of 4 facets admissible, Q57
  rejected at 0.30, survivor composite 0.41) → MEX 97.1% / ΔTVD 0.1495, USA caveat → one
  sentence on what this buys (measurement-fragility quantification).
- Aim: ~110 words each. Keep the numbers identical.

---

## Task 3 — Introduction: indirect-vs-direct contrast, de-duplication, clearer contributions [EFFORT: M]

**Current problems (from discussion + read-through):**
- the two-contribution paragraph is hard to follow; the *indirect vs. direct information*
  contrast — the paper's sharpest design idea — is never stated explicitly;
- two paragraphs both claim to be "the methodological spine" (§1 ¶5 and §1 ¶6 are ~80%
  redundant, ~120 words);
- "the paper proceeds as follows" paragraph lists sections but not the tier structure.

**Target structure for §1 (in order):**
1. LLMs as simulators + WEIRD default alignment (keep, trim);
2. SCA 1.0 = reduced-form (keep, trim);
3. **NEW — the core contrast, ~60 words:** *direct* information (country name, persona,
   ethnographic context at inference) vs. *indirect* information (the state enters only
   through training labels). State the advantage: the model is never told which population it
   represents, so the anti-stereotyping property is a design feature, not a post-hoc check;
4. core conjecture (keep as quote);
5. two contributions (keep, tightened — 3 sentences each, max);
6. equivalences spine (keep, **delete the duplicate "connection between the two literatures"
   paragraph**; fold its one non-redundant point — "the same formal object at the center of
   the partial-identification literature" — into §2.5);
7. empirical vehicle + road map (add one clause naming the tier ladder: T1 synthetic
   recovery, T2 survey OOS, T3 held-out/experimental — planned).

---

## Task 4 — §3.1 Primitives: operationalize the GPS→label path [EFFORT: M] [USES TASK 0]

Place the Task-0 block (z-scores → sign rule → caveat) right after the $z$ vector definition.
Also add the **interpretation of $\phi(z)$**: with z-scored inputs and a linear reward,
$\phi$ maps "SDs from global mean" into reward weights — make the units explicit once.

---

## Task 5 — Figure 1 redesign: five-component system with feedback loops [EFFORT: L] [INDEPENDENT]

**Current problem:** Figure 1 is a loose A→E chain; it does not show the *system* (the
measurement layer sits in a different section and the figure implies it is downstream of
Tier-1 only).

**Target (agreed with Augusto, 5 components):**
1. **Generation** — GPS $z_c$ → culture-conditioned synthetic preference pairs;
2. **Clean/label** — QC scoring (monotonicity / distance / contamination) + sign-based labels;
3. **DPO** — QLoRA student, unconditioned prompts (label this node "country never named");
4. **Evaluation** — Tier-1 (implied Δr, held-out synthetic) and Tier-2 (WVS option
   likelihood, external human criterion); Tier-3 (held-out/experimental) drawn as a
   *future* (dashed) branch;
5. **Validation** — cvprofiles layer: adapter-as-candidate-measure $m_{AI}(X)$ enters the
   menu; admissible set + $[L,U]$;
   **feedback loops (dashed):** (a) validation rejection → new menu / new training labels
   (the "theoretically-aligned models" frontier, already in §5); (b) Tier-2 mismatch → revisit
   generation/labeling (calibration stream).

Use distinct visual encodings: **solid** = executed, **dashed** = planned/future;
fill/shape = data artifacts vs. model artifacts. Caption must state the anti-stereotyping
design (unconditioned prompts) — it is the figure's most important annotation.

---

## Task 6 — §4 Empirical Results: methodology intro, tier ladder defined, unified presentation [EFFORT: M]

**Current problems:**
- the section opens on Tier-1 tables with no setup ("Tier" is used before being defined);
- Tier-3 is never mentioned, but the WVS_ITEM_MAP pre-registers it [VERIFIED — see Task 0];
  readers cannot tell executed from planned;
- construct-validity results sit in §4 without being tied to the evaluation design.

**Target structure:**
1. **New intro paragraph (~120 words):** evaluation methodology (frozen adapters,
   unconditioned prompts, matched-vs-cross design, WVS as external non-AI criterion) and the
   three-tier ladder defined *as an experimental design*:
   - **Tier 1** — synthetic pair recovery (in-sample; shared ancestry caveat);
   - **Tier 2** — out-of-sample survey moments (executed: $N=35$ items);
   - **Tier 3** — held-out validation moments + experimental/behavioral data
     (pre-registered in `WVS_ITEM_MAP`; **experiments/games not yet run — state this
     explicitly**);
2. one paragraph per tier with key evidence; keep the existing tables (Tier-1 cross-eval,
   Tier-2 WVS) but add a **compact "key evidence" table** at the top of the section
   (one row per tier: question, design, headline number, status executed/planned);
3. move the construct-validity subsection AFTER the tier paragraphs and open it with one
   sentence explaining the three result families (see Task 7).

---

## Task 7 — §4 construct validity: explain the "three families" [EFFORT: S]

**Current problem:** "[…] produces three families of results" enumerates without explaining.

**Fix (from discussion):** the families are three *question types* the framework answers —
(a) *admissibility* (which candidate measures survive the network? → typology table),
(b) *consequentiality* (does representation choice change downstream conclusions? → Q57 vs.
survivor composite), (c) *structure* (does the surviving measure reproduce GPS demographic
patterns? → demographic-gradient results). One lead-in sentence; no content change.

---

## Task 8 — Compression pass: ~16 → 12–13 pages, numbers unchanged [EFFORT: M] [LAST]

Order of cuts (safest first — all verified non-numeric):
1. delete the duplicate spine paragraph in §1 (Task 3 does this);
2. §5 frontier applications 6 → 4: fold "power-test analysis" + "pre-piloting survey
   questions" into one item (both are pre-field design loops); drop "simulating human-subject
   responses at country or individual level" or fold into item on population simulators;
3. §5 "Positioning: measurement and developing economics" — cut to 3 sentences (it restates
   the significance statement) or delete and leave the significance statement to do that job;
4. §2 related-work subsections: tighten each by one sentence (keep the SCA-first scaffolding);
5. abstract detail (Task 2 covers this);
6. §3.2 "Inference and reproducibility" — compress to: bootstrap over units → percentile
   bands + empty-replicate count; λ-grid for threshold sensitivity; frozen inputs + hash
   run-ids (3 sentences max).

**Hard constraint:** after the pass, `grep` that every original figure (0.785, 0.700, 0.520,
0.455, 0.1495, 0.0964, 0.2152, 0.4882, 0.2010, 0.5258, 0.3958, 0.3888, 97.1%, 34/35, 0.278,
0.349, 0.303, 0.332, 0.410, 0.371, 0.624, 0.174, 0.752, 17.5%, 0.568, 0.005, 0.999, 0.087,
0.334, 0.234, 0.415) still appears in the .tex.

---

## Open questions for Augusto (resolve before implementation)

**RESOLVED 2026-08-06 (all five):**
1. **Title:** KEEP "Synthetic Cultural Agents 2.0: Beyond Persona-Prompting" (no pivot; loop
   language may still be woven into the intro's final paragraph per Task 1).
2. **Appendix example:** ADD the patience/Q50 age-shape diagnostic as a second worked example
   (Task 2 of implementation). *Prerequisite:* confirm the Q50 U-shaped-vs-hump-shaped
   numbers from `sca2_validity` outputs before drafting.
3. **Tier-3 wording:** CONFIRMED — tier-3 WVS items are pre-registered holdouts; experimental
   games (dictator/ultimatum) are planned, not yet run. Paper states exactly this.
4. **Figure 1:** OK to redraw as the 5-component system diagram (Task 5). Placement: use
   in-flow portrait placement unless it overflows, then one-page landscape.
5. **"Families" rename:** no preference — use "three questions the validity layer answers"
   (or equivalent) at implementation discretion.

---
