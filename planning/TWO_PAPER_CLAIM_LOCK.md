# SCA2 two-paper claim lock
**Frozen 2026-09-16 (post Duch / Kseniia meeting).**  
Supersedes every earlier ρ, item count, and TVD as a *current* paper number.

**Wording amendment 2026-09-22.** Panel noun only. Census and production are retired. Superseded 2026-09-25: do not write “convenience sample.”

**Disclosure confirmation 2026-09-25.** Augusto confirmed that the study had no funding and that no author has a competing interest. The manuscript sentence is final.

**Number amendment 2026-09-25.** The frozen 0.80 used an older USA/Mexico testing evaluation in place of the first-wave file. That testing evaluation was removed. Headline adapter scores now come only from `ksenias_base8` (CHN JPN GBR USA MEX ARG DEU RUS) and `co2_8` (IND IDN NGA EGY TUR NLD BRA GRC). Trust adapter–GPS is **0.74** [0.44, 0.88]. Paired adapter-minus-persona difference is **0.81** [0.16, 1.31]. Adapter mean TVD on the 23-item rectangle is **0.487**. Persona −0.07 and persona TVD 0.369 are unchanged. Human–GPS is unchanged. Do not quote 0.80 as current. The 0.67 adapter-plus-persona cell is not amended; its source file is still unidentified. The sixteen are a purposively selected development panel from two saved jobs, not one forward pass, and not a probability sample.

Numbers for Paper A come only from the 16-country × 23-item matched surface
in `misc/position_paper_sca2_revised.pdf` (and the audit that produced it).
If a CSV, skill, README, or memory disagrees, the PDF surface wins until a
dated amendment of this file.

---

## Paper A — arXiv methods preprint

**Object.** An inspectable compiler from declared GPS `sign(z)` through a
shared A/B bank into one joint QLoRA-DPO adapter per group
(*anchored synthetic choice policy*; GPS–WVS instances = *anchored SCAs*).

**Claims this draft may make**

1. Construction: public GPS signs label a shared pair bank; one joint adapter;
   evaluation prompts omit country names.
2. Evaluation keeps three columns separate: human–GPS (map coherence),
   adapter–GPS (anchor retention on new text), adapter–human (agreement).
   Encoding of held-out synthetic pairs is a construction check, not GPS recovery.
3. On the trust map, the profile adapter with a country-name-free prompt transfers the coarse GPS sign. The Spearman with continuous GPS trust is 0.74 [0.44, 0.88]. That is not recovery of within-sign magnitudes. The country-prompt comparison stays in the results and is not an abstract claim. Human agreement remains unresolved.

**Claims this draft may not make**

- Recovered culture, a GPS coordinate, magnitudes, or a human distribution.
- Isolated a single GPS dimension (joint six-sign adapters).
- Demonstrated survey pre-piloting or that scoring new items replaces people.
- Weights keep order / prompts keep shape (configuration sensitivity, not a law).
- Assignment permutation (\(p=0.002\)) is a sign-retrain (adapters were not refit).
- Nomological restrictions (trust∼rule of law, income–altruism) substitute for
  a human criterion. They are consistency screens, not ground truth.

**Construct-validity argument (Paper A only)**

| Column | Role | Status on locked surface |
|---|---|---|
| GPS \(z\) | Declared anchor (different method from the LLM) | Given |
| Human–GPS | Criterion for the *map* | 0.39 [−0.18, 0.79] on \(n=16\); underpowered; Q57 = 0.15 |
| Adapter–GPS | Retention of the coarse sign on new text | Trust 0.74 [0.44, 0.88]; persona −0.07 unchanged |
| Adapter–human | Predictive criterion vs people | Trust 0.32 [−0.22, 0.77] — unresolved |
| Nomological / GDP | Optional appendix restrictions | Not the validity case |

Campbell–Fiske: the human surveys are the other method. Borsboom: the network
is consistency, not causation. Wide intervals and empty conclusions stay.

**Locked panel and readout**

- Countries (purposively selected development panel; two saved jobs; not a probability sample):
  base8 CHN JPN GBR USA MEX ARG DEU RUS;
  co2_8 IND IDN NGA EGY TUR NLD BRA GRC.
  16 units, 13 sign profiles. Twins: MEX≡RUS, IND≡GRC, IDN≡EGY.
- Bank: 658 shared pairs, 526/132, β=0.1, LoRA r=16, one epoch.
  USA = 658×A; Mexico = 658×B (global polarity, not six traits).
- Items: 23 single-choice WVS7, common support. Egypt not asked Q69–Q71;
  GBR not asked Q174; those items out *everywhere* in the primary rectangle.
  Patience Q43 and Q50 unpooled. Recode = \(E[g_q(J)]\), mask missing before recode.
- Readout: leading-space option-code logprob, softmax over supplied codes, no country name.

**Locked numbers (quote only these)**

| Quantity | Value |
|---|---|
| Encoding | recovery 0.942, accuracy 0.819, 2,112 cells |
| Trust adapter–GPS | **0.74** [0.44, 0.88] |
| Trust persona–GPS | −0.07 [−0.55, 0.45] |
| Trust adapter−persona | 0.81 [0.16, 1.31] |
| Trust adapter–human | 0.32 [−0.22, 0.77] — unresolved |
| Trust human–GPS | 0.39 [−0.18, 0.79] |
| Q57 human–GPS (this panel) | 0.15 |
| Risk adapter–GPS | 0.52 [−0.03, 0.80] |
| Risk adapter–human | −0.04 |
| 2×2 trust–GPS / mean TVD | adapter 0.74 / 0.487; persona −0.07 / 0.369; adapter+persona cell 0.67 not amended |
| Patience human–GPS | Q43 −0.56; Q50 +0.62 |
| Assignment placebo | not recomputed on the two-wave file; do not cite p=0.002 as a check of 0.74 |
| Egypt / Q69–Q71 | not recomputed on the two-wave file; do not cite 0.79–0.81 as current |

**Duch sample rule for Paper A.**  
The 16 are a purposively selected development panel from two saved jobs. They were chosen to include both global polarities, the three duplicated sign profiles, mixed profiles, and geographic spread. Write that as a design, not “compute constraints.”
It is not a random sample of the 42-country GPS∩WVS7 intersection.
Do not cherry-pick a subset of the 16 after seeing ρ.

**Out of Paper A (do not run in order to arXiv)**

Magnitude relabel+retrain; mixture-of-LoRAs; 35/42-country adapters;
new human data collection; merging cvprofiles into this manuscript.

**Pre-arXiv work (time, not new science)**

1. Freeze this surface in the tex *and* `reproduce_tables.py` (today HASHES
   still pin the old 30-item 0.78 construct table).
2. Polish the three-column validity prose; keep pre-piloting prospective.
3. Replication: public option-probability zip, hashes of *this* surface,
   evaluation notebook. Restore the on-disk paper source (see inventory).
4. Cheap map check: 42-country human–GPS on Table 2 recodes, plus Q69–Q71
   on the countries that have them (no GPU, no new adapters).
5. Appendix protocol for a future human item-screen (ethics, estimand, N) —
   do not field it for arXiv.

---

## Paper B — journal extension (SMR after arXiv + sign-off)

**Object.** The same compiler as a *scoring instrument for new item text*,
with a human criterion on items the probe selects.

**Additional claims (none allowed until the evidence exists)**

- A new battery’s adapter–GPS can be interpreted as transport of the anchor
  after calibration against human–GPS / imprint / missing.
- Pre-piloting changes item selection relative to a human-only path.

**Required before those claims**

1. **No discretionary country set:** train every GPS∩WVS7 country (42), or
   a predeclared random sample of that 42. Prefer 42: twins become a
   reliability contrast rather than a collapsed profile. 35 unique signs
   is acceptable only if the twin rule is frozen before seeing results.
2. Sign-retrain (relabel, refit) and/or a second scenario bank.
3. Sign-profile prompt cell (same information, different route).
4. Independent human check of probe-selected items.
5. Magnitude / per-dimension adapters remain optional protocol papers,
   not patches on Paper A’s object.

cvprofiles stays a **separate** paper (validator lane). Do not fuse.

---

## Never quote as current

0.70 (unified 30-item script 13); 0.78 (`table_construct.tex` / HASHES);
0.79 (mid-audit); 30-item TVD 0.469 / 0.375 / 0.443 / 0.338;
`2x2_bridge.csv` 0.78 / 0.60 / 0.06; “35 mapped items” (30+5 demographics);
`recode(E[raw])` as the production recode.

Dated amendment required to change this file. No silent number drift.
