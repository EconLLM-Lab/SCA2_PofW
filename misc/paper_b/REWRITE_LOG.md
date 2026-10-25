# REWRITE_LOG: card CP26-M1 (framing, option A), writer profile

Baseline before any edit (HEAD 64c0a28, paper/paper-b-draft): latexmk exit 0, 48 pp, 0 overfull, 0 undefined, audit PASS,
anonymity grep empty, abstract 149 words, texcount main text 12,666 words (all `\input` sections, captions and tables included).
Originals of every edited file are kept outside the repo in the writer scratch directory.

## 1. abstract.tex

What changed: the abstract was a screening-result summary; it is now the anchor -> instrument -> respondents chain in words.
It states, in this order: the question (a model has to hold at each link), the instrument (adapters from declared country-level
signs, scored on new items without naming the country), what holds (label installation on unseen pairs; the trust order, also under
a sign prompt), what fails (entangled dimensions; a weak preregistered screen judged against a retrospective criterion that the
registered comparisons do not separate from questionnaire readers; no detectable adapter-respondent agreement), the order versus
distribution contrast (adapters farther from the survey's answer distributions than the base model, country-named prompt closer
with no trust order), and the boundary (complements human pretesting; pre-piloting untested). Words only, no citations.
Keywords: dropped "direct preference optimization", added "measurement validity".
Claim ids: none (words only; every sentence maps to a row family in the numbers table, listed under section 2).
Word count: 149 (limit 150).
UNSURE: "Training installs the synthetic labels on unseen pairs" rests on C9 rows that are descriptive and not preregistered; the
150-word cap left no room to say so in the abstract. The main text says it (introduction part 4, Discussion).
UNSURE: "as does a prompt stating the same signs" is true of PX_signprompt_trust_rho; the abstract does not say that the
adapter-minus-prompt screen contrast (SP_D_own) is unresolved. The sentence implies it ("the signs carry"), the Discussion states it.

## 2. introduction.tex

What changed (full rewrite, about 1,620 words against 1,185 before): part 1 states the chain and the contribution on the first page;
part 2 places the work in the cautionary literature, separates prompted and distribution-trained models (the human survey sits
inside their training signal) and separates pretesting-as-flaw-detection from screening; part 3 defines the three links
(anchor GPS, instrument adapters, respondents WVS-7) and adopts the measurement lens with a citation instead of claiming it;
part 4 describes the construction with its narrow novelty (six declared signs, no human answers, group unnamed at evaluation);
part 5 describes the four parts of the evaluation and says which follow the preregistration and which are descriptive follow-ups;
parts 6 to 8 give findings by link (holds / weak / order versus distribution) in words; then three numbered contributions;
then the closing "what the paper shows / does not show" paragraph with the intended-use clause and the roadmap.
Novelty audit (N1) followed: no "first", "new method", "we introduce"; "which we call" kept; "diagnostic of entanglement" is now
"a factorial over sign profiles" with dangmasud2026 cited as prior evidence of entanglement; "scoring instrument" kept with the narrow
novelty sentence; "rarely tested" avoided; wangc2026 cited as the foil and the persona result scoped to one benchmark's trust order.
Claim ids used: none as numbers (words only). Design constants through \dc: 16 (dev_countries), 64 (cells), 223 (pool_items).
The words rest on these rows: C9_label_recovery_*; B2_cohort1_trust_rho, B2_bank2_trust_rho; PX_persona_trust_rho,
PX_signprompt_trust_rho; SP_D_own; C9_W1_*; SCR_A_primary, SCR_p_perm, SCR_A_over_ceiling; CMP_*; C9_a_adapter_human_*,
C9_a_human_gps_*; C9_TVD_adapter_minus_base_profile_block, C9_TVD_persona_minus_base_profile_block.
References added (all cited): santurkar2023, durmus2024, dominguezolmedo2024, chen2026, wallach2025, wangc2026, dasilva2026,
dangmasud2026 (from N1) and sturgis2026 (retrieved here; Survey Futures Working Paper 15, April 2026).
Bib handling: preprint entries carry `note = {Preprint}` plus an `eprint` field, because the anonymity grep in the gates matches the
string "arxiv" anywhere in the PDF and chicago.bst prints a note but not eprint or url.
UNSURE: "a prompt that names the country does not [keep the GPS trust order]" and "keep it when the scenario bank is replaced" are
true on trust only (B2_*, PX_*); the sentence says "On trust" and the Discussion repeats the scope.
UNSURE: "the registered contrasts do not distinguish the adapters from careful readers of the questionnaire on the few items they
share" compresses CMP_*; the results section carries the overlap counts (5 and 9 items).
UNSURE: chen2026 and wallach2025 are cited for one sentence each; "found to be weak proxies for it" is the paper's own title.
Entries should be checked against the publisher pages before submission (TODO(Augusto) comment in references.bib).
Gates after this file: see the block below.

    latexmk exit 0
    overfull boxes: 0
    undefined refs/cites: 0
    pages: Pages:           50
    audit exit 0
    RESULT: PASS
    anonymity grep exit 1 (1 = empty)
    abstract words: 149
    Sum count: 14
    Sum count: 0
    Sum count: 164
(gates above were run after the introduction and bibliography edit, before the 'complement' sentence fix)

## 3. discussion.tex

What changed (rewrite, about 1,550 words against 1,263 before): the contribution-led paragraphs are now chain-led. Order:
opening roadmap; "From anchor to instrument: what holds" (label recovery, trust order across banks, retraining noise, sign prompt
versus named country, adapter-minus-sign-prompt contrast unresolved, the claim scoped to trust); "Why the signs carry the trust order"
(W1 behavioral decomposition: own part mechanical, other five signs add little on trust and most elsewhere, one surface against six,
no graded relation, labels independent of a second dimension); "Entanglement" (factorial, both routes, dangmasud2026 as prior
evidence, contrast makes no claim about recipe); "From instrument to respondents" (retrospective screen, comparators, follow-up
agreement, GPS-respondent link loose, anchor-versus-instrument attribution explicitly untested); "Order and distribution" (the
contrast, the sign-only training signal carries no magnitudes, not tested why, persona result scoped to one benchmark's trust order,
wangc2026 and dasilva2026 cited); "Limits" (five limits, text unchanged); "Intended use" (one clause changed to a complement phrase).
Claim ids used (all via \cl/\ci): C9_label_recovery_{recovery,accuracy,base_accuracy}_profile_block; PX_signprompt_trust_rho;
PX_persona_trust_rho; C9_W1_patience_Q43_spearman_own_vs_gps; C9_W1_posrecip_spearman_own_vs_gps; C9_W1_trust_cross_var_share;
C9_W1_trust_spearman_full_vs_gps; C9_W1_negrecip_cross_var_share; C9_W1_patience_Q43_cross_var_share;
C9_TVD_adapter_minus_base_profile_block; C9_TVD_persona_minus_base_profile_block. All values are copied from results.tex; audit PASS.
Dropped from the old Discussion: the sentence that Section 5.8 to 5.11 rows "earn no claim" is kept in the order paragraph; the old
"Fidelity to labels" paragraph is split between the anchor paragraph and the order-and-distribution paragraph.
Not used on purpose: "bottleneck"; a sentence that would blame the anchor ("a weak target limits ...") was removed after drafting
because it leans toward that framing.
UNSURE: "the labels themselves do not depend on a second dimension" rests on C9_W1_bank1/bank2_label_mismatches (both 0) and carries no
number here; Results 5.10 gives the rows.
UNSURE: "The training signal suggests a reading that we offer without testing" is the reason requested by the card (signs carry no
magnitudes). It is hedged and it is not a result; Augusto may prefer to cut the two sentences after it.
UNSURE: "an unseeded retraining of one profile leaves their readings nearly unchanged" compresses RP_*; it bounds noise for one unit
only, which the Limits paragraph says.

## 4. conclusion.tex

What changed (rewrite, about 320 words against 219): words only, three short paragraphs: the chain and what holds between anchor
and instrument (including the sign-prompt equality, so the weights are not credited); what is weak between instrument and respondents
(retrospective screen, no dimension passes both checks, no detectable adapter-respondent agreement); the order versus distribution
contrast as a descriptive, non-preregistered reading; and the intended-use clause with the prospective test that would license more.
Claim ids: none (words only).
UNSURE: the conclusion states the order versus distribution contrast in words; a reader may want one number there. The venue
and author voice favor words, so none was added.

## 5. main.tex and title_page.tex (title only)

Old (15 words): "Synthetic Cultural Agents as Scoring Instruments: A Preregistered Held-Out Evaluation of Survey Item Screening".
New (15 words): "Synthetic Cultural Agents as Measurement Instruments: A Preregistered Evaluation from Cross-National Anchor to Survey Respondents".
Why: "Survey item screening" is now one link of the chain, not the contribution. All existing TODO(Augusto) comments are untouched
(main.tex 1, title_page.tex 5). The title page's "Prior posting" paragraph is untouched; it is not input by main.tex.
Alternatives for Augusto: "Where a Language-Model Measurement Instrument Holds: A Preregistered Evaluation from Benchmark Signs to
Survey Respondents" (16 words); keep the old title if he wants the screening framing in the title.

## Final gates (after the last edit)

    latexmk exit 0
    overfull boxes: 0
    undefined refs/cites: 0
    pages: Pages:           51
    audit exit 0
    RESULT: PASS
    anonymity grep exit 1 (1 = empty)
    abstract words: 149
    Sum count: 15
    Sum count: 0
    Sum count: 164

Words (detexed, macros printed): introduction 1,625 (was 1,185); discussion 1,553 (was 1,263); conclusion 319 (was 219); abstract 149 (was 167).
texcount main text, whole manuscript: 12,666 before, 13,499 after (the count includes design, results, tables and backmatter that this card
does not touch). The outline target is 9,000 to 10,000 words. The framing files grew by about 830 words and the draft was already above
target before this card, so the cut has to come from card M2 (design.tex 3,547 and results.tex 3,619 source words).
voice_audit.py on the detexed text: zero fail flags. Warnings: low_we (3.8 to 7.9 per 1,000 words; the Discussion states findings
in the third person on purpose) and missing_boundary on the conclusion (the heuristic matches the singular words "limit" and "complement";
the boundary sentences are present, with "complement" added to the conclusion). Grep for ", not" on the four files: empty.
Grep for transport, bottleneck, earlier study, novel, first to, we introduce, histogram, stand-in, stereotype, causal, mechanis: empty.
Pages: 48 before, 51 after (the PDF is double-spaced; the extra pages are the framing files).

## Premise flags for the PM

1. The card asks the abstract, introduction and conclusion to use \cl/\ci/\dc macros. The venue rubric (abstract words only) and the
   author-voice lock (numbers in Results) argue for no statistics there, so those three files carry only design constants through \dc
   (introduction: 16, 64, 223). Claim ids appear as numbers only in the Discussion.
2. The rules block lists `B2_bank_to_bank_trust_spearman`; results.tex prints `B2_bank_to_bank_trust_pearson` (the Spearman version is in the
   supplement per the outline). No number from either row is used in M1.
3. The old title still appears outside this card's fence: supplement.tmpl.tex line 18 (the supplement title, and therefore the generated
   supplement.tex), and submission/COVER_LETTER_DRAFT.md line 7. M2 may update the template title through tools/render_supplement.py;
   the cover letter needs a PM or Augusto decision once the title is chosen.
4. NUMBER_AUDIT.txt and main.pdf are tracked files and changed because the gates rewrite them. Commit them or restore them, PM's call.
5. Bibliography entries from N1 were not re-opened one by one (chen2026 was re-checked against nature.com); the TODO(Augusto) comment in
   references.bib asks for a publisher-page check before submission. sturgis2026 is a working paper (Survey Futures), April 2026.

---

## M2: body pass (card CP26-M2, writer profile)

Scope: background.tex, instrument.tex, design.tex, results.tex, supplement.tmpl.tex (prose, one new section, title). Nothing committed.
M1's four files were not edited (no cross-reference needed fixing). Tables, macros.tex, tools/, submission/ and the generated
supplement.tex (except by tools/render_supplement.py) were not touched. `data/` was not opened. Originals of every file sit
outside the repo in the writer scratch directory (and in /var/folders/.../T/m2).
Method: every `\cl`/`\ci`/`\dc` sentence that stayed was copied verbatim; sentences that moved to the supplement were re-expressed
as placeholders and rendered from NUMBERS_TABLE.csv. A script compared the printed value of every claim id before and after: no id
prints a value it did not print before, and no `\dc` pair is new.

### Word counts (texcount -inc, which counts a claim id as a word, and a detexed count that prints each macro's number once)

| file | texcount before | after | detexed before | after |
|---|---|---|---|---|
| background.tex | 832 | 572 | 847 | 582 |
| instrument.tex | 847 | 830 | 826 | 812 |
| design.tex (incl. Table 1, Figure 1) | 3,221 | 2,429 | 3,394 | 2,609 |
| results.tex (incl. the four tables) | 5,003 | 4,036 | 4,562 | 4,034 |
| whole main text | 13,499 | 12,133 | 13,791 | 12,199 |
| supplement.tmpl.tex (source words) | 5,164 | 5,873 | | |

Pages: main 51 -> 47; supplement 15.

**The 9,000 to 10,000 target is not reached (12,133 by texcount). This is a flag for Augusto/PM, not a quiet miss.** The body files
M2 may edit held 9,903 words before and hold 7,867 now, so the body is already down 21 percent. Getting the whole text to 10,000
needs about 2,100 more words. M2's fence leaves three ways to do it, and each is a decision about scope:
(a) trim introduction.tex (1,612) and discussion.tex (1,643), which M1 grew by about 830 words and which restate the findings in
words that Results then states with numbers (a card for M1's files, about 1,000 words); (b) move the four descriptive follow-up
subsections 5.8 to 5.11 (surface D, about 1,900 words with their table) to the supplement and leave a half-page summary in the
main text, which keeps every result but makes the respondent link thinner in the main text; (c) accept about 12,000 words and say so
to the venue (the venue card, not this log, decides whether that is acceptable). I did not do (b) because it changes which results
the main text shows, and the chain framing leans on 5.8 and 5.9 (agreement with respondents and distance).

### 1. background.tex (832 -> 572 texcount)
Changed: the first paragraph no longer repeats the critics' evidence that the introduction already gives (it points there and keeps
silicon sampling, homo silicus, the review, fine-tuning, and the two reviews that ask for a criterion); the paragraph on construct,
measure and anchor now says that instrument-anchor, instrument-people and anchor-people agreement are the three comparisons the chain
makes; the Bradley-Terry/DPO paragraph is removed because instrument.tex section 3.2 carries the same correspondence (the citation
to bradleyterry1952 moved there); "the empty cell" is reframed as the question of what the instrument preserves link by link.
Nothing in this file carries a claim id. Citations dropped from this file: none (all keys still used elsewhere or in this file).
UNSURE: "The question here is, link by link, what an instrument ... preserves" avoids "first" and "little work", per the N1 novelty audit;
Augusto may want one sentence naming a gap in the literature.

### 2. instrument.tex (847 -> 830)
Changed: opens by placing the instrument as the middle link; Bradley-Terry sentence now cites bradleyterry1952 and absorbs the
background paragraph; repeated sentences on the sign-profile route and the labels trimmed. Equations, constants (`\dc`) and the
readout unchanged. This file was already tight; the saving is small on purpose.

### 3. design.tex (3,221 -> 2,429)
Changed: opening paragraph is chain-led (anchor to instrument, then instrument to respondents); Table 1 and Figure 1 kept as they were.
Moved to the supplement (new section S10 "Design detail and robustness numbers that the article summarizes"): the full item-pool rule,
the two questionnaire readers' detail, the wording-repair list of Amendment 1, the persona run's base-model rescoring check. Compressed:
probe, human ceiling, per-dimension readings, comparators, readout variants, factorial (two paragraphs into one), noise and near-zero
margin (two into one), the four descriptive analyses. Kept, because they are honesty clauses: first probe pass read before the repairs,
Q153 and Q157 in the top quartile, comparators on pre-repair wording, Amendment 2 and Q82, "the criterion is retrospective", the
provenance gaps (now one sentence that points to the supplement), "not preregistered" for the descriptive analyses, the V5 rule and its
one-in-seven reference, "the selection rule does not control the noise rate".
Dropped from the main text without a home elsewhere in the main text: "The first-cohort values reproduce the banked run exactly" (now in
S10) and the statement that the supplement adds a country bootstrap and the sixteen-country trust correlations (I could not find the
sixteen-country table in the supplement template, so I did not repeat the promise; M1's original sentence may have referred to a
table that was never written. Please check).

### 4. results.tex (5,003 -> 4,036)
Changed: new opening paragraph maps the subsections to the chain (anchor to instrument: 5.1, 5.2, 5.11; inside the instrument: 5.6, 5.7,
5.10; instrument to respondents: 5.3 to 5.5, 5.8, 5.9) and says the surface D follow-ups are not preregistered and that everything
against WVS Wave 7 is retrospective. Subsection titles carry the link. Subsection 5.4 now ends with "the paper therefore cannot credit the trained weights over
the prompt on the screen", next to `SP_D_own`. Numbers that moved to the supplement (S10; the bank, persona and follow-up sections already
held several): the three flat second-bank surfaces and three of five bank-to-bank correlations; the secondary-rule per-dimension
reading and its Bonferroni interval; leave-one-country-out is kept; the wave-6/wave-7 check; the three `|t|` correlations; the
cells-not-fielded count and the positive-item share; the country-resampling TVD intervals, the adapters-plus-persona contrasts,
the trust correlations restated in 5.9; the covariance shares, main-effect shares and two-way correlations of the decomposition; the
rank correlations across surfaces; five bit-on-surface effects of the factorial (new in S10); the near-zero footnote's
dropped-dimension count (new in S10). Honesty clauses kept in the main text: retrospective first for every held-out result, the
Bonferroni loss of the risk-taking interval, "no imprint dimension passes both checks", the comparators rest on few items, the
`SP_D_own` contrast unresolved, "not a graded relation, no dose-response", the base model's accuracy interval includes one half,
"no claim of reversal", "construction checks say nothing about respondents".
Fix made during gating: a sentence said the other bank-to-bank correlations "lie between" the trust and risk-taking values; altruism
(the highest) does not, so it now says the other surfaces "agree more closely".
UNSURE: 5.9 now says the adapters are farther than the base model "on four of the six dimensions and slightly closer on the other two";
that is the old sentence (trust, risk taking, positive reciprocity, negative reciprocity versus patience and altruism) with "dimension"
counting patience once. Please confirm against the by-dimension TVD table in the supplement.
UNSURE: 5.3 says "item--country cells never fielded enter as missing (online supplement)"; the count moved to S10.

### 5. supplement.tmpl.tex (5,164 -> 5,873 source words)
Changed: title updated to the new title (M1 premise flag 3); one sentence added to the opening list; new section S10 with ten paragraphs
(item pool, readers, repairs, persona run, positive items and unfielded cells, reliability checks in full, readout membership,
rank correlations, factorial cross effects, dropped dimensions). All numbers are placeholders rendered by tools/render_supplement.py.
Not touched: every earlier section. supplement.tex was regenerated by the renderer only.

### Claim ids
Compared over all body files and tables, before and after: 206 ids before, 163 after in the main text. **No id disappeared from the paper
(main plus supplement).** 43 ids left the main text; 37 were already in the supplement, 6 were not and now are (S10): the five
`FX_*_bit_on_*` cross effects (FX_adapter64_risktaking_bit_on_negrecip, FX_adapter64_trust_bit_on_patience_Q50,
FX_adapter64_trust_bit_on_posrecip, FX_signprompt64_trust_bit_on_patience_Q50, FX_signprompt64_trust_bit_on_risktaking) and
NZ_blockD_against_beyond_floor. Supplement ids: 247 before, 265 after. The card's literal command (`git diff a467da0 -- misc/paper_b |
grep -oE ...`) is not a before/after test, because results.tex and design.tex were identical to a467da0 until this card edited them,
so their ids enter the diff only now (13 ids at the start of M2, 141 after). The set comparison above is the real check.
Ids the lock names and where they stand in the main text: C9_label_recovery_* (5.11), B2_cohort1_trust_rho, B2_bank2_trust_rho,
B2_bank_to_bank_trust_pearson (5.1; the rules block names the Spearman version, which is not in the main text or in the template:
M1 premise flag 2 stands), RP_max_abs_surface_diff_sd (5.7), PX_persona_trust_rho, PX_D_cohort1_trust, PX_signprompt_trust_rho (5.2),
SP_D_own (5.4), C9_W1_* (5.10), SCR_A_primary, SCR_p_perm, SCR_A_over_ceiling (5.3), CMP_* (5.4), C9_a_adapter_human_* and
C9_a_human_gps_* (5.8), C9_TVD_adapter_minus_base_profile_block and C9_TVD_persona_minus_base_profile_block (5.9). C9_c_* (the grouping
test) is not used in the main text.

### Gates (after the last edit; HF_TOKEN blank, env -u PYTHONPATH, SCA2_PofW .venv python)

    latexmk -pdf main.tex           exit 0; overfull 0; undefined 0; 47 pages
    latexmk -pdf supplement.tex     exit 0; overfull 0; undefined 0; 15 pages
    audit_numbers.py (main)         exit 0; RESULT: PASS
    audit_numbers.py supplement.tex exit 0; RESULT: PASS
    anonymity grep, both PDFs       0 matches (pattern: arxiv|2610.06562|gonzalez|gonzález|bonorino|biriukova|capra|econllm|sca2_pofw|bonorinoa|github|huggingface|augusto|kseniia|monica, case-insensitive; M1's exact pattern was not recorded in this log)
    forbidden-word grep on the four files: only "override mechanism" (Amendment 1) and "says nothing about mechanism inside the network".

Changed by the gates: NUMBER_AUDIT.txt, SUPPLEMENT_NUMBER_AUDIT.txt, main.pdf, supplement.pdf (tracked files, rewritten by the build).
voice_audit.py was not run on these files (not in the card's gates).
Model route: anthropic / claude-sonnet-5-5 as set by the card; not verified from the agent log.

## PM pass after MV (2026-10-24, orchestrator `default`)

MV verdict PASS-WITH-WORDING with three required wordings and four notes. Applied by the PM directly (mechanical,
no new prose):
- **W1** `results.tex` (TVD interaction): "the data show no departure from additivity: … add" → "no *detectable*
  departure …; descriptively … are consistent with adding".
- **W2** `results.tex` (W1 decomposition): "the cross-talk is not inherited from the labels" → "the labels do not
  carry the cross-talk".
- **W3** `abstract.tex`: ambiguous "It can complement human pretesting" → "The instrument can complement human
  pretesting" (abstract now 150 words, cap ≤ 150).
- **N2** `results.tex` (bank-to-bank): main text now quotes the claim lock's headline row, the rank correlation
  `B2_bank_to_bank_trust_spearman` 0.907 [0.774, 0.957] (risk taking 0.544 [0.187, 0.772]), with the Pearson
  values 0.909 / 0.598 left to the supplement, where both columns are printed. No number is new; the rows are in
  the table and both audits PASS.
- **N4** `submission/COVER_LETTER_DRAFT.md`: title updated to the new working title from `main.tex`.

Build after the pass: latexmk exit 0, 47 pages, 0 overfull, 0 undefined, both number audits PASS, anonymity grep
empty. **N1** (the four "intended use" sentences) and **N3** (main text 11,526 words against the 9,000–10,000
target) are Augusto's calls and are unchanged.
