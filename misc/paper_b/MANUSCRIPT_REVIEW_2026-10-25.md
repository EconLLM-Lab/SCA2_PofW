VERDICT: PASS-WITH-WORDING

# Manuscript review — CP26-MV (verifier, GLM cross-family, run 149)

Scope: uncommitted M1+M2 rewrite in `misc/paper_b/` vs HEAD `64c0a28` (baseline manuscript `a467da0`).
Fence: read-only except this file and `review_probes/`; `data/` not opened. Card text reviewed:
`planning/TWO_PAPER_CLAIM_LOCK.md` (C7–C9.1), `planning/checkpoint_2026-10-26/NOVELTY_AUDIT.md`,
rules block of card t_c8662397.

Model route: z-ai/glm-5.3 (openrouter) per the task override — a different family from the Claude
(anthropic) producer of M1/M2. **The rewritten manuscript can be shown Monday as a trusted checkpoint.**
Three small wording fixes (W1–W3) should land first or be acknowledged; none touches a number, an
estimand, or a claim-lock rule.

**Findings requiring wording (all minor, none blocking the checkpoint):**

- **W1 · results.tex:73** — "The interaction contrast … is 0.009 [−0.003, 0.022] under profile blocks,
  which includes zero, so the data show no departure from additivity: the adapters' step away from the
  survey and the persona prompt's step toward it add." Problem: an interval that includes zero is
  absence of *detection*, not evidence of absence; the clause asserts additivity as fact (and the
  point estimate 0.009 with country CI [−0.0007, 0.019] sits at the margin). Required wording:
  "…includes zero, so the data show no *detectable* departure from additivity" (or "…so we cannot
  distinguish the contrast from zero"), and hedge or drop the "add" clause.
- **W2 · results.tex:83** — "…so the cross-talk is not inherited from the labels." Problem: "inherited"
  is a mechanism metaphor, and the claim-lock's I2 ruling allows a behavioral decomposition but no
  localization of cause. The factual base (0 mismatches in 27,636 rows) is exactly what the previous
  clause says. Required wording (descriptive restatement): "…so the labels do not carry the
  cross-talk" — the adjacent sentences ("We do not claim a cause…") already keep the rest safe.
- **W3 · abstract.tex:2** — final sentence "It can complement human pretesting; pre-piloting remains
  untested." Problem: the referent of "It" is ambiguous — the preceding sentence's last-mentioned arm
  is the *country-named prompt*, but the intended subject is the instrument. Required wording:
  "The instrument can complement human pretesting; pre-piloting remains untested."
  (Same-family suggestion, not required: "does not detectably agree with respondents" → "with
  respondents' own ordering", matching the body's "respondents' composite".)

**Notes for Augusto / the PM (no manuscript change required by me):**

- **N1 (positioning).** The intended-use family — discussion.tex:17 `\paragraph{Intended use.}`
  ("the instrument has a modest and inspectable use… As a complement to fielding and pretesting it
  has a place"), conclusion.tex:7, abstract.tex:2 and introduction.tex:26 — is the closest the paper
  comes to forbidden option B. I judge it inside the lock: every instance carries the bounds
  ("no dimension passed both checks", "no reason to use it in their place", "pre-piloting remains
  untested"), so it describes a use, not a demonstrated performance. Positioning is Augusto's call;
  he should read those four sentences before Monday.
- **N2 (rules block vs manuscript).** The checkpoint rules block credits
  `B2_bank_to_bank_trust_spearman`; the main text prints `B2_bank_to_bank_trust_pearson` (0.909
  [0.797, 0.965]) and the supplement prints both (Pearson and Spearman 0.907). Both rows are in the
  table and audit PASS; the claim lock itself does not pin bank-to-bank to Spearman. Reconcile the
  rules block or the main text — a wording-source decision, not a numbers violation.
- **N3 (word target).** Main text 11,526 words in text by `texcount -inc -sum main.tex`
  (12,047 including headers 244 and captions/tables 277; M2 reported 12,133 under its own
  aggregation). The 9,000–10,000 target is missed by ~1,500–2,000 words. M2's options (trim
  introduction/discussion; move 5.8–5.11 to the supplement; accept ~12,000) remain open — scope
  decision for Augusto, already flagged by M2. The manuscript is not harmed at this length for a
  checkpoint.
- **N4 (outside my fence).** `submission/COVER_LETTER_DRAFT.md` line 7 still carries the old title
  (M2's flag stands; outside my fence). `title_page.tex` correctly carries the prior-posting
  arXiv:2610.06562 note and is a separate upload never `\input` by main.tex.

## 1. Numbers

**Build (fresh, in place).**
- `tools/render_supplement.py` (venv of the main repo, `env -u PYTHONPATH`): exit 0; output byte-identical
  to the supplement.tex M2 left on disk (deterministic render).
- `latexmk -pdf main.tex`: exit 0, 47 pages, 0 Overfull, 0 undefined.
- `latexmk -pdf supplement.tex`: exit 0, 15 pages, 0 Overfull, 0 undefined.
- `tools/audit_numbers.py --out NUMBER_AUDIT.txt`: exit 0, `RESULT: PASS` — 405 printed, 405 PASS, 0 FAIL,
  0 unexplained numerals, 167 distinct claim ids.
- `tools/audit_numbers.py --files supplement.tex --out SUPPLEMENT_NUMBER_AUDIT.txt`: exit 0,
  `RESULT: PASS` — 551 printed, 551 PASS, 0 FAIL, 0 unexplained numerals, 281 distinct claim ids.
- Table provenance: `NUMBERS_TABLE.csv` sha256 `71ee7c8c…ce186a4`, 562 rows — matches the lock; the
  worktree's copy and the main repo's copy are byte-identical (checked both).

**Independent probe** (`review_probes/check_cl_ci.py`, own implementation, no import from tools/):
```
0 mismatches (745 checks: 201 \ci, 544 \cl, over 18 files)
  per-file: discussion.tex:13+4, results.tex:124+27, supplement.tex:293+127, tab_checks.tex:20+16,
  tab_comparators.tex:20+6, tab_factorial.tex:52+0, tab_human.tex:22+21
```
exit 0. Handles plain decimals, negatives, integers, `{,}` separators, `<0.001`, and the fields
`v/lo/hi/n/pct/abs`; claim ids containing colons (`B2_cohort1_patience:Q43_rho`) are parsed as ids.
Mutation check (in /tmp copy, never the repo): planted (a) wrong value 0.556 vs 0.546, (b) wrong rounding
`0.14` vs `0.147`@2dp→0.15, (c) unknown id `C9_W2_…` — all 3 caught, probe exit 1. The probe can fail.

Item 1: **PASS**.

## 2. No number changed meaning

Probe: `review_probes/check_meaning.py` — pairs every claim id's containing sentence, HEAD vs worktree
(`git show HEAD:...`), macro args masked to `<NUM>`/`<CI>`. Output reviewed in full: 98 rewritten pairs
across the 13 main-text files plus 22 in the rendered `supplement.tex` (all 22 are moves into the new S10;
the template's `«…»` placeholders are covered via the rendered file). Findings:

- **Id inventory: nothing disappeared, nothing invented.** Old ids (main+supplement) = 393; new ids = 393;
  set difference both ways = ∅ (script in session, `git show HEAD:` baseline).
- All 98 rewritten pairs keep the same estimand, direction and interval. 43 ids left the main text; every one
  is still printed in the supplement (verified by the id-set check, not taken from M2's handoff).
- Interpretive additions were checked against the table independently:
  - results.tex:11 "Risk taking is the least stable surface" — Pearson 0.598 is the lowest of the five
    surfaces (trust 0.909, altruism 0.949, posrecip 0.898, negrecip 0.708). Supported.
  - results.tex:73 "country resampling gives the same readings" — adapter−base country 0.045 [0.017, 0.079]
    (farther), persona−base country −0.105 [−0.119, −0.091] (closer): same signs as profile-block. Supported.
  - results.tex:73 "farther… on four of the six dimensions and slightly closer on the other two" — recomputed
    adapter−base per dimension: farther on negrecip +0.097, trust +0.066, posrecip +0.052, risktaking +0.050;
    closer on altruism −0.055, patience −0.010. Matches; supplement table `tab:s-tvd-cells` carries the
    by-dimension rows (M2's open flag resolved).
  - results.tex (C9_a): "interval excludes zero on four of the seven surfaces… positive for trust, negative
    for patience Q43" — exactly 4 of 7 exclude zero (trust +, Q50 +, negrecip +, Q43 −); signs match;
    `tables/tab_human.tex` prints all 7 rows.
  - discussion.tex:7 "The own part orders countries like the GPS on every surface, correlations 0.817 to
    0.866" — own-vs-GPS values 0.8167…0.8663, all positive. Supported.

Item 2: **PASS-WITH-WORDING** (W1, W2 above).

## 3. Claim lock (C7–C9.1 and the rules block)

Checked against `planning/TWO_PAPER_CLAIM_LOCK.md` (read in full) and greps over all manuscript files:

- "transport": **0 matches** in every .tex (main, tables, supplement template). Transport and pre-piloting
  appear only as unearned/prospective.
- "anchor … bottleneck": **0 matches** anywhere.
- "persona matches respondents": the positive claim is **absent**; both mentions are explicit negations
  (introduction.tex:17 "it does not show that any arm matches respondents"; discussion.tex:13 "It does not
  show that the country-named prompt matches respondents, since the same prompt has no trust order").
- Retrospective-first: results.tex:3 global statement ("Everything computed against the WVS Wave~7 file is
  retrospective"), subsection title "the retrospective screen" (results.tex:17), first word of the screen
  result "Retrospectively,…", design.tex:65 "Results on surface H are therefore labelled retrospective
  throughout". Abstract, introduction, discussion, conclusion all carry it.
- C9/descriptive: results.tex:61 "None is preregistered, none enters a registered family, and none earns a
  claim… every statement is retrospective"; design.tex:21 and design.tex:95 label surface D descriptive;
  `tab:human` and `tab:checks` captions say "descriptive and not preregistered; retrospective"; discussion
  TVD paragraph "It is descriptive, it was not preregistered, and it earns no claim".
- Sign-prompt caveat (`SP_D_own`): printed at results.tex:39 with the required reading ("The paper
  therefore cannot credit the trained weights over the prompt on the screen"), and repeated wherever the
  trust order is credited: introduction.tex:13, discussion.tex:5 ("the evidence cannot credit the trained
  weights over a prompt"), conclusion.tex:5. **Present at every credit site.**
- W1 causal/mechanistic wording: results.tex:79 "says nothing about mechanism inside the network";
  results.tex:83 "We do not claim a cause of the loss on every surface. Component-level analysis, and
  interventions for any causal statement, have not been done" (matches the I2 ruling's allowed wording);
  discussion.tex:7 "locates nothing inside the network". design.tex:87's "causal statement about the
  instrument" concerns the randomized factorial (V5) and is explicitly bounded to synthetic labels —
  allowed. Residual: W2 above.
- Positive tool claim: the intended-use family is hedged at every instance (see N1); pre-piloting appears
  only as "a prospective use that this paper does not test" / "remains untested" — the C7-allowed sentence.
- The 16-country panel is "the development stage of this study" (introduction.tex:9) ✓. No country name in
  evaluation prompts is stated as a construction property (introduction.tex:9, design) ✓.

Item 3: **PASS** (W2 and N1, N2 recorded above).

## 4. Novelty wording

Against `planning/checkpoint_2026-10-26/NOVELTY_AUDIT.md`:
- Strong words: "first to", "for the first time", "novel", "we introduce", "we propose",
  "to our knowledge", "rarely", "never been": **0 matches** in all main-text files.
- "which we call synthetic cultural agents" (introduction.tex:9) is naming, not "we introduce"; the same
  paragraph says "We built it in the development stage of this study" — exactly the audit's safe wording.
- All eight references the audit required are now cited where prescribed: santurkar2023, durmus2024,
  dominguezolmedo2024 (intro ¶2), chen2026 (intro ¶3), wallach2025 (intro ¶3), wangc2026 and dasilva2026
  (intro ¶on order-vs-distribution, discussion), dangmasud2026 (entanglement, intro and discussion).
- The order-versus-distribution contrast is written as the audit's safe sentence: "a descriptive contrast
  between two questions" (introduction.tex:17), never as a new conceptual point, with both ESS and
  Population Fidelity cited. "Cheap first reading" (introduction.tex:3) cites the silicon-sampling works
  and pretesting motivation cites sturgis2026.
- "Entanglement" is attributed to prior activation-steering work at every mention ✓.

Item 4: **PASS**.

## 5. Anonymity

`pdftotext` of both freshly built PDFs (my build), grep for author surnames (Gonzalez, Bonorino,
Biriukova, Capra), arXiv, `2610.06562`, "earlier study", preprint, EconLLM, and affiliations
(Arizona State, Claremont, Tempe, Tucumán):
- main.pdf: 2 matches, both the word "Preprint." as the publication venue of **cited** works in the
  bibliography (other papers' arXiv postings). Not a leak. Author names / own preprint id /
  "earlier study": 0.
- supplement.pdf: **0 matches**.
- `references.bib`: no entry for the preprint and no entry authored by any paper author (grep 0);
  `archivePrefix = {arXiv}` occurrences belong to cited external works only.
- `title_page.tex` (separate upload, never `\input` by main.tex — verified in main.tex) carries the
  prior-posting arXiv note, which is the correct place for double-anonymous review.
- Note: the card said "as in M1" but M1's exact grep pattern was never recorded; I used a broader pattern
  than the card's minimum list.

Item 5: **PASS**.

## 6. Build hygiene

- Overfull: main.log 0, supplement.log 0. Undefined references: 0 and 0. latexmk exit 0 both.
- Pages: main 47, supplement 15.
- Abstract: **149 words** (own count of the `abstract` environment; texcount reports 163 for the file
  because it also counts the keywords line) — ≤ 150 ✓.
- Main-text word count (`texcount -inc -sum main.tex`): **11,526 words in text**; 12,047 including
  headers (244) and captions/tables (277). M2's 12,133 used its own per-file aggregation; both counts
  say the same thing: the 9,000–10,000 target is missed (see N3).

Item 6: **PASS** (target miss is N3, a scope decision, not a defect).

## 7. Referee read (abstract, introduction, conclusion)

Read in full at the file level (abstract.tex 5 lines, introduction.tex 26 paragraphs-lines, conclusion.tex).
The chain framing is clear, every strong claim is bounded, and the three-link structure reads as option A
without option-B or option-C drift. Findings beyond items above:

- W3 (abstract.tex:2): ambiguous "It" in the final sentence — see findings block.
- introduction.tex:15 "often by more" (cross effects exceed own effects) — supported by the factorial rows
  (e.g. risktaking bit on altruism vs altruism own effect; trust bit largest mover on most surfaces). OK.
- introduction.tex:19–24 contributions: all three are phrased as evaluations/protocols, not discoveries;
  contribution 2 claims the protocol, not priority ("We specify, register and run"), matching the
  novelty audit. OK.
- conclusion.tex:5 is an accurate compressed restatement of the results; "no dimension passes both the
  second-bank check and the screen" matches Table `tab:checks`; "does not detectably agree with the
  respondents' composite" matches C9_b (all seven adapter–human intervals include 0). OK.
- conclusion.tex:7 / discussion.tex:17: see N1 — the only sentences a hostile referee could read as
  tool-promotion; each carries its own hedge in the same paragraph.

## What I did not verify

- `data/` was never opened (fence). No Hub or Colab interaction; no GPU spend.
- Provenance of the C9-4/GPU rows and the 562-row table is taken from the claim lock's recorded audits
  (C9's deepseek-verifier, C9.1's Codex audit), not re-run — my check is that every printed number equals
  the locked table, which I did independently.
- The bibliographic accuracy of the new `references.bib` entries is taken from the novelty audit's
  grounded-citations ledger; I did not re-open each source.
- I did not edit the manuscript, did not commit, and did not touch M1's framing files beyond reading.
- The build regenerated tracked build artifacts in place (main.pdf, supplement.pdf, supplement.tex via the
  renderer, the two audit files) — required by the card's "rebuild both PDFs; rerun both number audits";
  supplement.tex came back byte-identical to M2's render.

**VERDICT: PASS-WITH-WORDING** — show it Monday; land W1–W3 first if there is time (≈3 sentences).
