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

### Amendment C7 2026-10-18 (Paper B; orchestrator, under Augusto's delegation)

Paper A is untouched by this amendment.

**Claim source.** Paper B numbers come only from
`planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv` (220 rows, sha256 `90f0f467…0ec1f`, built by
`paper_b/build_numbers_table.py`). Each number carries its surface label (S1, S2, H, F, R, N; defined in
`C7_CLAIM_LOCK_AMENDMENT_DRAFT.md` section 1). For wording, the draft's sections 1–8 apply, as modified below.
If the draft and this amendment disagree, this amendment wins.

**Status of the two additional claims.** Neither one is earned. Neither appears as a result.

- *Transport.* No imprint dimension passes both checks. On the bank-2 strict battery (S2), only trust keeps
  an interval above 0: 0.803 [0.615, 0.876]. On the held-out screen (H), only risk taking does, under the
  registered primary rule: 0.158 [0.015, 0.290], 13 items. After a Bonferroni adjustment over the four
  imprint dimensions (exploratory, same draws), that interval is [−0.026, 0.326]. The general transport
  sentence stays unwritten.
- *Pre-piloting.* Untested. The only allowed sentence is "a prospective use that this paper does not test".

**C5 is not passed (decision on draft §9.7).** The journey plan states that "C5 fails if that file is the
only human source", and WVS-7 is the only human source. Every H result is a **retrospective screen**:

- Say "retrospective" first.
- Never use the word "transport" for an H result.

The screen itself is reported as registered: A 0.061 [−0.007, 0.126], one-sided permutation p 0.0097, 8.1%
of the wave-6/7 ceiling. The null is rejected and the signal is weak.

**What Paper B is.** A preregistered evaluation of the sign compiler as a scoring instrument. Its findings:

- *Holds.* Trust on a second scenario bank. A weak, retrospective held-out screen. All seven own effects of
  the adapter factorial point the intended way.
- *Fails.* V5 (2 of 6). No dimension passes both checks. Positive reciprocity points the wrong way on H.
  The comparators do not distinguish the adapters from a careful reader (5 and 9 shared items).
- *Untested.* Pre-piloting. The near-zero filter (C6) is a footnote: it is not promoted and no reversal is
  claimed.

**Accepted wording.** Draft §8 for F7 (both pool hashes), F8 ("an unseeded retrain"; no weight cosine) and
F11 ("unchanged when `SCA2_PB_PROTOCOL` is not set to `bank2`"). Draft §6.2 for C6. Draft §5 for the
comparators: "does not distinguish", with the registered phrase beside it. Draft §7 for the non-claims, plus
one more: the primary-rule risk-taking interval does not survive adjustment for four dimensions.

**"Required before those claims" status.**

| Item | Status |
|---|---|
| 1. 42 countries | Done |
| 2. Second bank | Done (sign-retrain not done) |
| 3. Sign-profile prompt cell | Done (64 cells) |
| 4. Independent human check | **Not done**. This is the gap that keeps both claims prospective. |
| 5. Optional protocol papers | Unchanged |

**Pending.** The provenance card `t_ef474f3c` compares the archived scores with today's scorer. If it finds
drift, the table is rebuilt with the same claim_ids. A rebuilt table needs a new dated amendment of this
file.

### Amendment C7.1 2026-10-18 (Paper B numbers table rebuilt; orchestrator, under Augusto's delegation)

This amendment changes the claim source only. The C7 wording, the claim status and the "Holds / Fails /
Untested" reading stay as written above.

**New claim source.** `NUMBERS_TABLE.csv` now has 225 rows, sha256 `20ea003b…0f08e`
(`20ea003b5fe12e396d7e706787f84c353c24034b642f8ce1a50646e560e8f08e`). It replaces the 220-row table
`90f0f467…0ec1f`. Each of the 220 earlier rows keeps its value, interval and n.

**Five added rows.** These are the two registered descriptives that the C7 table did not carry.
Preregistration sections 6 and 8 register them, and `paper_b/heldout/analyze_heldout.py` computes them:

| claim_id | What it is |
|---|---|
| `SCR_absA_n_kept`, `SCR_absA_A_kept`, `SCR_absA_share_pos_kept` | Section 8: the selected items with \|a_i\| ≥ 0.15. Descriptive only, and never the primary. The cut conditions on the criterion, so the kept-item A is not an inference. |
| `CMP_face_valid_A_all`, `CMP_face_valid_all_negrecip_A` | Section 6: the face-valid reader's A on all of its items, with negative reciprocity included. After Amendment 2 the reader has 29 items, one fewer than the registered 30. |

The re-run of `analyze_heldout.py` read the human surface through `require_freeze()` against the same
frozen selection. Every earlier key of `heldout_analysis.json` came back identical, and `heldout_items.csv`
came back byte-identical. The only change is the new `s8_abs_a_descriptive` block.

**Provenance fix.** The nine `RO_*` rows were built from a scratch folder that is pruned after a day without
use. They now read the byte-identical copies in `results/robustness/`, and the new in-repo driver
`paper_b/heldout/readout_robustness.py` produces them. Only their `producing_script` and `output_file`
fields changed.

**Provenance card closed.** Card `t_ef474f3c` (`paper-b-tier1/provenance/ARCHIVE_PROVENANCE_20261018.md`)
returned NOT REPRODUCED and says no table rebuild is needed. NF4 quantization explains the main archive
gap. The commit that produced the cohort-1 archive cannot be identified, because the archive records only
a code-bundle digest. The "Pending" note above is therefore resolved without a rebuild.

### Amendment C8 2026-10-18 (Paper B; the country-named persona arm; orchestrator, under Augusto's delegation)

**Why.** Augusto decided on 2026-10-18 that the SMR manuscript is the journal version of arXiv:2610.06562 and not a
sequel. The manuscript therefore stops citing the preprint as prior work, and the preprint's main comparison,
country adapters against a prompt that names the country, is re-run inside Paper B on all 42 countries and on the
Paper B frozen stack. The design was locked before scoring (`paper-b-tier1/C8_PERSONA_DESIGN.md`, commit 2a6dfcb).
The code is in commit f33a2a7, and the run is `persona-strict-v1-20261019` (Hub, 42 personas plus the base model,
spec pin `ed3bb964…`, 0.98 Colab units).

**Gates.** G2: the adapter-path gate passed on `P_1_0_1_1_0_1`, with adapter parity and switch-back both 0.0.
G3: the fresh base model equals the banked strict base of `bank2-strict-v1-20261016` on all
140 option rows (max |Δ log p| = 0.0). The persona column is therefore on the same
stack as every adapter column. An exhaustive audit of the 42 units found 0 problems in rows, grids or probability
sums. No persona equals the base model, and no two personas are equal.

**New claim source.** `NUMBERS_TABLE.csv` now has 271 rows, sha256 `51ddcce1…97855` (`51ddcce1dd205ee29ecf6e3450fd30bf09948399e98adb32abfc0846e1b97855`). It
replaces the 225-row table `20ea003b…8f08e`. All 225 earlier rows are unchanged, and a test pins them against
commit 92406dd. The 46 added rows are `PX_*`, built by `paper_b/persona_strict.py`. The replay checks pass:
the script reproduces the banked cohort-1 and bank-2 GPS rows exactly, and the sign-prompt trust effect.

**Readings.**

| Estimand (design §3) | Value | Reading |
|---|---|---|
| E2, the one test: trust, cohort-1 adapters minus persona, paired profile-block | 0.716 [0.191, 1.154] | interval above 0: the adapters track the GPS trust order more closely than the named-country prompt |
| E1, persona–GPS on trust | 0.028 [−0.339, 0.381] | the named-country prompt does not track the GPS trust order |
| E4, E2 under the country bootstrap | 0.716 [0.325, 1.075] | same reading |
| E5, the 16 development countries (descriptive) | cohort-1 0.818 [0.554, 0.926]; persona −0.038 [−0.565, 0.480] | Paper B stack; not compared with the preprint's own numbers |
| Sign prompt–GPS, trust (descriptive) | 0.773 [0.584, 0.844] | the sign prompt states the same signs and tracks trust as well as the adapters |
| Persona–GPS, patience Q50 and Q43 (descriptive) | 0.509 [0.157, 0.730]; −0.491 [−0.771, −0.124] | the country name carries some patience ordering, with opposite signs on the two items |

**What may be written.** On trust, the country adapters track the GPS order more closely than a prompt that names
the country. The interval excludes zero under both resampling models. This is a comparator result on one
dimension. The prompt that states the same six signs tracks trust as closely as the adapters do, so the contrast
separates declared signs from a country name. It does not separate weights from prompts. All other differences
(E3) are descriptive and none of them is a test.

**What does not change.** Neither additional Paper B claim (transport, pre-piloting) is earned. No registered
held-out number moves. The held-out screen keeps its registered comparators, because the probe is defined on the
64 profile cells and the persona route has no profile structure. The C7 and C7.1 readings stand.

### Amendment C9 2026-10-20 (Paper B; descriptive human-agreement, distributional and cross-talk rows; orchestrator under Augusto's delegation; coauthor sign-off pending)

**Why.** Paper B is the journal version of arXiv:2610.06562, not a sequel. It re-runs the preprint's human-agreement
and distributional results on the frozen Paper B stack (42 countries, strict 23-item battery) and carries no preprint
number over. Augusto approved the C9 analyses on 2026-10-19 (`planning/DECISIONS.md`). This amendment banks what
those runs returned, and says what they do not show. It changes the claim source only.

**New claim source.** `NUMBERS_TABLE.csv` now has 554 rows, sha256 `02c5d0cf…9dd1`
(`02c5d0cf9281f2927b8222386160412f1276437bf9dca8f70eafdc042dda9dd1`). It replaces the 271-row table
`51ddcce1…97855`. All 271 earlier rows are unchanged, byte for byte and in order. A test pins them against commit
`1cf9db7`, next to the older pin against `92406dd`. The 283 added rows carry the prefix `C9_`.

**Label.** Every added row is DESCRIPTIVE / NOT PREREGISTERED. The 2026-10-11 surface had already been seen when
these were computed. None of them is a test, none enters a preregistered family, and none earns a claim.

**Verification.** Card `t_b95d3240`, a verifier on a different model family from the producers (route openrouter
`deepseek/deepseek-v4.1-flash`; report `paper-b-tier1/results/c9/VERIFICATION_C9.md`). It recomputed 96 headline
values with its own code and found every one equal at printed precision. The full `paper_b` suite passed (599
tests). Labels, interval types, n and the JOR complete case checked out. The two untracked outputs of C9-4 were
not part of that acceptance.

**What was added, and the estimand of each row.**

| Rows | Producer | Estimand |
|---|---|---|
| `C9_a_*`, `C9_b_*` (cohort-1 and bank-2 adapters) | `paper_b/c9_human_agreement.py` | Spearman across the 42 countries, per surface, of: adapter composite against GPS; adapter composite against the WVS-7 human item-mean composite; human composite against GPS. Adapter-side intervals: profile-block bootstrap (26 clusters). Human-GPS intervals: country bootstrap. Risk-taking has n = 41, because JOR has no valid Q178 answers. |
| `C9_c_*` | same | Between-profile share of variance among the 28 countries in the 12 multi-member sign profiles, with a one-sided permutation p against a label shuffle that keeps group sizes, and a simulated power curve for that design. |
| `C9_d_*` | same | Agreement of each country's human composite with the mean of its sign-mates (leave one out). A measure of sign-mate agreement, not a ceiling. |
| `C9_e_*` | same | Reference scorers built from the GPS signs, for scale. Mechanical, not success tests. |
| `C9_f_*` | same | Item-level and complete-case variants of the preprint's human-agreement readouts. |
| `C9_TVD_*` | `paper_b/c9_tvd.py` | Mean total variation distance between the model's option probabilities and the survey-weighted human answer shares, per country-item cell, for four cells: base model, cohort-1 country adapters, country-named persona prompt, and the two together (the rows the 2026-10-19 run added). The interaction contrast tests whether the two interventions add. The headline is country-equal (mean of country means), with the preprint's pooled mean beside it. n = 42 countries and 965 cells (42 × 23, less the JOR/Q178 cell). |
| `C9_W1_*` | `paper_b/w1_crosstalk.py` | W1, a behavioral factorial decomposition: the six bank-2 main effects on each surface, split into an own-bit term and a cross-bit term, and the Spearman of each prediction with GPS across the 42 countries. Model quantities and published GPS z only, no human rows. |

The adapter+persona TVD cell now has rows. Run `adapter-persona-strict-v1-20261019` scored all 42 countries on
2026-10-19 (cohort-1 adapters at revision `7550fd4c` plus the country-named persona prompt, strict battery, pinned
spec `persona_strict_v1`). Its gates passed before any country was scored: the fresh base reproduced the banked
strict base, the ARG adapter without persona reproduced its banked cohort-1 rows and differed from base, and
disabling the adapter returned the base. `c9_tvd.py` fetched the run from `Bonorinoa/SCA2-paper-b-artifacts` and
filled the fourth cell, so all four cells and their contrasts are in the table as `C9_TVD_*`.

**C9-4 ran twice, and only the second run counts.** The first attempt produced a 16-country fixture summary under a
42-country run name and spent nothing; card `t_433e7ef5` ruled it BLOCK (`C9_GPU_VERIFICATION.md`) and those files
are out of the tree. The genuine run was executed by the orchestrator directly on a Colab T4 on 2026-10-19, about
one compute unit for experiment A. Experiment A (adapter plus persona, 42 countries) is what fills the fourth TVD
cell. Experiment B (held-out synthetic-label recovery on the 42 cohort-1 adapters) was still scoring when this
amendment was written; it has no row here, and when it finishes it needs its own dated amendment, as the rule at the
end of this section says. Both the run and this amendment still owe a cross-family audit: the orchestrator wrote the
C9-4 code and ran it, so the verifier that accepted C9-1, C9-2 and W1 cannot be the one that accepts C9-4.

**Readings (all descriptive).**

*C9-1, three columns.*

- Cohort-1 adapters track GPS on trust: 0.744 [0.500, 0.865]. Against the human composite on trust they reach
  0.295 [−0.044, 0.547]. All seven adapter-human intervals include 0.
- Human-GPS on trust is 0.351 [0.088, 0.564], on patience Q50 0.388 [0.095, 0.628] and on negative reciprocity
  0.416 [0.173, 0.586]. On patience Q43 it is −0.533 [−0.741, −0.266]. The other three intervals include 0.
- The bank-2 adapters give the same picture: trust adapter-GPS 0.803 [0.615, 0.876], trust adapter-human
  0.340 [−0.025, 0.586]. Positive reciprocity is the only adapter-human interval that excludes 0 (0.366
  [0.007, 0.636]), and only just.

*I1 (the verifier's ruling: WEAK, not SUPPORTED).* The candidate insight was that countries sharing a sign profile
are no more alike than random groups, so the anchor and not the language model limits human prediction. The
verifier's ruling, with its caveats:

- The non-rejection reproduces. Human multi-member between-profile shares run from 0.318 to 0.626, against chance
  means of 0.402 to 0.408 and one-sided permutation p from 0.059 (negative reciprocity) to 0.738.
- It is power-limited. With the realized 12 groups (sizes 2 to 4), 80% power needs a true between-share of about
  0.568 (0.60 on the simulation grid). Only negative reciprocity's observed share (0.626) is in that region. Read
  the human grouping as **inconclusive**: the design cannot detect an excess unless it is large, and none was
  detected. It does not show that profiles carry no human signal.
- Population and sample quantities differ. The power curve's "true between-share" is a parameter of the simulation
  (Gaussian group effects, equal noise). The table's shares are realized sample ratios, and with no group effect at
  all the simulated sample share still averages 0.411. Do not set the two on one axis.
- Adapter composites are almost entirely between-profile: 0.957 to 0.9999 on the same 28 countries. Sign-mate
  agreement among human composites runs from −0.350 to 0.332, every interval spanning 0.
- **Not allowed:** "the anchor, not the language model, is the main bottleneck". No test in C9 locates the
  bottleneck. A null result with this power does not identify one. Neither the sign-mate agreement nor the
  human-GPS correlation bounds an arbitrary profile-constant or nonlinear scorer.

*I2 (the verifier's ruling: WEAK, not SUPPORTED).* The candidate insight was that cross-talk between sign bits
explains why the adapters keep each bit's direction and lose the GPS country order on most dimensions. The
descriptive core reproduces; the word "explains" overreaches.

- Every own effect of the adapter factorial is right-signed (`FX_adapter64_own_effects_wrong_signed`, 0 of 7).
- The own-bit-only prediction orders countries like GPS on all seven surfaces (0.817 to 0.866). This is mechanical.
  It is proportional to sign(z) for a positive coefficient, so it restates the sign-GPS correlation and is not a
  separate test of learning.
- The full main-effects prediction keeps the GPS order on trust only (0.834). On the other six it gives 0.104
  (risk-taking), −0.020 (patience Q43), 0.176 (patience Q50), 0.422 (altruism), 0.378 (positive reciprocity) and
  0.386 (negative reciprocity).
- Quote the covariance share. The cross term's share of Var(full) in covariance terms is 0.287 on trust and 0.727
  to 0.985 elsewhere. Var(cross)/Var(full) is a ratio, not a percentage of variance explained: it is 0.147 on trust,
  0.830 to 1.049 on the rest, and it exceeds 1 on patience Q43 (1.049) through covariance.
- The main effects carry 0.483 to 0.925 of the 64-cell variance. Interactions are needed on four surfaces, and they
  do not restore the GPS order (main plus two-way, 0.331, −0.066, 0.287 and 0.210).
- Across the seven surfaces, the rank correlation between Var(cross)/Var(full) and adapter-GPS failure is 0.821
  against bank-2 composites and 0.286 against cohort-1 composites. It rests on one surface (trust) against six, so it
  is not a graded relation and no dose-response is claimed.
- In both banks, all 27636 country-pair training rows follow the sign of the pair's own dimension (0 mismatches).
- **Allowed wording:** a behavioral decomposition of the adapters' main effects. **Not allowed:** a neural
  mechanism, a cause of the failure on every dimension, or a statement about human preferences. Component-level
  analysis, and interventions for any causal claim, have not been done.

*C9-2, distribution to humans.* Mean TVD, country-equal, lower is closer: base 0.470, cohort-1 adapters 0.515,
country-named persona 0.365 (pooled means equal these at three decimals). Adapters minus base: +0.045 [0.006, 0.093]
(profile-block) and [0.017, 0.079] (country). Persona minus base: −0.105 [−0.122, −0.086] (profile-block) and
[−0.119, −0.091] (country). On this measure the adapters sit farther from the survey distributions than the base
model, and the country-named prompt sits closer. This is a different quantity from the rank agreement above. The
persona prompt has the lowest TVD and a trust-GPS of 0.028 [−0.339, 0.381]; the adapters have the highest TVD and a
trust-GPS of 0.744. The base model's trust-GPS is undefined, since its trust composite is the same for every country.
The preprint's own TVD figures are not compared with these.

**What C9 does not change.**

- No claim is earned. Transport and pre-piloting stay unearned, exactly as in C7, C7.1 and C8.
- The held-out screen stays a retrospective screen. No registered held-out number moves, and C5 stays not passed:
  the WVS-7 composites used here are the same single human source.
- Pre-piloting stays untested.
- The C8 wording stays: declared signs against a country name, not weights against prompts.
- No human row and no country-level human mean or distribution enters git or the Hub. The human inputs stay local.
- C9 adds no preregistered test and no new decision rule. C9-4, if it is run, needs its own dated amendment.
- Both pending items stay pending: the adapter+persona TVD cell and held-out label recovery on 42 adapters.

---

## Never quote as current

0.70 (unified 30-item script 13); 0.78 (`table_construct.tex` / HASHES);
0.79 (mid-audit); 30-item TVD 0.469 / 0.375 / 0.443 / 0.338;
`2x2_bridge.csv` 0.78 / 0.60 / 0.06; “35 mapped items” (30+5 demographics);
`recode(E[raw])` as the production recode.

Dated amendment required to change this file. No silent number drift.
