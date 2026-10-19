# Paper B analysis design — pre-outcome specification (draft 2026-10-11)

> **Record, not status.** Written 2026-10-11. Lines about what is done, blocked or next describe that date, not today. Current status: [STATUS.md](../../STATUS.md).

**Status:** DRAFT for parent/user sign-off. Written before any adapter outcome was
inspected; no adapter score has been read. Derived from `TWO_PAPER_CLAIM_LOCK.md`,
`PAPER_B_PROTOCOL_DRAFT.md` (frozen 2026-10-09), `paper_b/eval_config.py`,
`paper_b/eval_lib.py`, `paper_b/score_cohort.py`, and
`analysis/phase2/22_paper_a_surface.py` + `outputs/paper_a/human_item_means_42.csv`.
No repo files were edited; no GPU run; no outcome numbers are quoted here.

---

## 1. Derivation of the primary battery (what the code actually says)

**Item grid.** The readout grid (`eval_lib.build_question_specs` over
`DPO_eval_WVS/question_map_wvs_edited.csv`) covers the mapped WVS7 questions:
Q43, Q50, Q57–Q64, Q69–Q71, Q73, Q81, Q99, Q101, Q103, Q106, Q107, Q109,
Q174, Q176–Q179, Q195, plus numeric-open Q261/Q262 and nominal Q174/Q260
(`eval_config.NOMINAL_QUESTION_IDS`; numeric-open optional, `MAX_NUMERIC_SUPPORT=150`).

**The locked 23-item primary rectangle.** From the claim lock: "23 single-choice
WVS7, common support. Egypt not asked Q69–Q71; GBR not asked Q174; those items
out everywhere in the primary rectangle." Cross-checking
`human_item_means_42.csv` (26 distinct items appear; Q174 is absent because it
is nominal, Q260–Q262 are demographics/numeric-open):

> **Primary 23 = Q43, Q50, Q57–Q64, Q73, Q81, Q99, Q101, Q103, Q106, Q107,
> Q109, Q176, Q177, Q178, Q179, Q195** (i.e. the 26-item human-means grid minus
> the Q69/Q70/Q71 block). Q69–Q71 are a *secondary* trust extension only
> (complete-case, 41 countries); Q174/Q260/Q261/Q262 are not battery items.

**Removed-from-primary items and why:**
- Q69, Q70, Q71 — not asked in Egypt (verified: EGY absent, 41/42 in the file);
  kept only in the `q69q71_complete` secondary surface.
- Q174 — not asked in GBR and nominal (no ordering ⇒ no E[recode]); out of all
  rectangles.
- Q260 (sex), Q261 (year of birth), Q262 (age) — demographics / numeric-open,
  not attitude items; numeric grids are country-observed support and would not
  be comparable across the archive vs 42-cohort (the gate pins the archived grid).

**Recodes (from `22_paper_a_surface.py::recode_value` — this is the locked
`E[recode]`, not `recode(E[raw])`):**
- Invert 1→4 scale (`5 − x`): Q58, Q59, Q60, Q61, Q62, Q63, Q64, Q69, Q70,
  Q71, Q73, Q81.
- Invert 1→10 scale (`11 − x`): Q177, Q179.
- Binary (Q57): `1 if x==1 else 0`.
- All others (Q43, Q50, Q101, Q103, Q106, Q107, Q109, Q176, Q178, Q195): raw.
- Missing mask: `v ≥ 0`, finite, positive survey weight (`weight` column)
  **before** recode; weighted mean with `W_WEIGHT`; per-item minimum
  n = 50 valid responses (`MIN_N=50`).

**Composites (per GPS dimension, unweighted mean of item means — same as
Paper A):**
- trust: Q57–Q64, Q73 (TRUST9; Q57 binary, rest 1–4 inverted except none)
- patience: **Q43 and Q50 UNPOOLED** (each matched against GPS patience
  separately; never averaged)
- risktaking: Q106, Q107, Q109, Q178
- posrecip: Q81 alone
- negrecip: Q176, Q177, Q179, Q195
- altruism: Q99, Q101, Q103

Two composite conventions exist in the code and must be pinned: **complete**
(retain only countries observed on every item of the composite) vs
**available** (all countries with ≥1 item). Paper A's 42-country table used
complete for the composite rows. Recommendation: primary = complete-case
composites; report available-case as sensitivity. Complete-case membership
must be printed per composite (it differs by arm: for the adapter–human
column, JOR is missing on Q178 — see §4 ambiguity A2).

**Readout (frozen in `eval_config.py`):** leading-space option-code logprob
(`COMPLETION_PREFIX=" "`), softmax at T=1 over the *supplied* option codes,
no length normalization, no country name in the primary prompt, survey
weights on (`weight`), `EVAL_MAX_PROMPT_TOKENS=768`.

---

## 2. Estimand and inference for the 42-cohort

**The country-level n is 26, not 42.** The cohort carries 26 distinct GPS sign
profiles in 12 multi-member groups (AUS CAN USA · BRA MAR · COL JOR · CZE JPN ·
EGY IDN · GRC IND · GTM MEX ROU RUS · IRQ TUR · KAZ VEN · KEN ZWE · NGA PAK PER ·
SRB UKR — 28 countries) plus 14 singletons. Twins are *reliability replicates*,
not independent observations. Every adapter comparison is a **country-level
descriptive with profile-clustered inference**:

- **Point estimates:** Spearman rank correlations over all 42 countries for
  each column (adapter–GPS, adapter–human) and each dimension composite —
  reported as descriptive. Rank correlations are the Paper A convention;
  keep them.
- **Interval / test estimator:** profile-level block bootstrap (resample the
  26 profiles with replacement, keep all members of a drawn profile;
  2,000 draws, seed fixed a priori, e.g. 20261011). This is the only interval
  that reflects the dependence structure. Report alongside: the naive
  country bootstrap (Paper A convention, seed 20260905) **labelled as
  anti-conservative** for comparability only.
- **Human-only analyses do not automatically have n = 26.** Human–GPS and
  adapter–human use the human battery; the dependence structure of *human*
  means across twin countries is an empirical question (two countries with
  identical GPS signs need not have identical human distributions — indeed
  their divergence is the interesting part). Recommendation: primary human
  intervals also profile-clustered (defensible ex ante), with a plain
  country bootstrap reported alongside; state explicitly that profile
  clustering is an *upper-bound* dependence assumption for human columns.
- **Country-equal estimand (predeclared):** the primary estimand is the rank
  association over the 42-country GPS∩WVS7 intersection, each country
  weighted equally. The alternative **profile-equal estimand** (mean within
  profile first, then rank correlation over the 26 profile means) is the
  predeclared sensitivity. If the two differ materially (point estimates on
  opposite sides of 0, or non-overlapping clustered intervals), say so in the
  text rather than choosing the flattering one.
- **Within-profile reliability diagnostic (pre-outcome):** for each of the 12
  multi-member groups, report the within-group SD (or range) of (a) each
  adapter composite and (b) each human composite, per dimension. Under the
  frozen protocol, twin divergence in the adapter column is fitting noise;
  quantifying it is the reliability contrast promised in frozen decision (A).
  This is descriptive; no pass/fail.

**Bootstrap details (frozen here):** 2,000 replicates; profile bootstrap =
resample profiles (clusters), keep all member countries of each draw;
percentile 95% intervals; seeds: profile bootstrap 20261011, country
bootstrap 20260905 (inherited). No GPS measurement error in intervals
(carry the Paper A caveat). Bootstrap the (composite, GPS z) pair jointly,
dropping countries missing either side per dimension.

**Base comparator.** The base (unconditioned) model arm is scored once and
broadcast to all 42 populations (`score_cohort.build_pairs`, `pairs=matched`
gives base vs each country's own population). Base–GPS and base–human
correlations are reported on the same surfaces as the adapter column; the
adapter-minus-base difference in rank correlation is the predeclared
"adapter lift" descriptive, with the same profile-clustered intervals.
The persona arm (country-named prompt) is reported but is **not** equivalent
to a sign-profile prompt cell (see §6) and is not part of the primary claim.

**Near-zero exposure.** Frozen decision (B): primary = full 658-pair bank;
robustness = `|z| < 0.10` exclusion. Per the protocol this requires a
**refit** (retrain the affected countries' adapters on the filtered bank),
not outcome filtering — filtering scored outcomes post hoc is not the frozen
variant and must not appear. Per-country near-zero exposure counts
(GBR 438, BOL 330, COL/PER/RUS 329, DEU/PAK 328, the 219–220 band, most
others 109–110) are printed beside results. The robustness column is
reported for affected countries only and is labelled a sensitivity, never
promoted to the headline.

---

## 3. Prospective vs retrospective item-screening (Paper B's actual claim)

- **Retrospective (this run, diagnostic only):** comparing adapter vs human
  distributions on the *existing* 23-item battery — i.e. asking whether the
  adapter's implied rankings would have "selected" the same items humans
  answer consistently — is a consistency analysis of already-collected items.
  It supports no pre-piloting claim.
- **Prospective (the Paper B claim):** the adapter screens *new item text*
  (second bank / new battery) before humans see it, and the human check is
  fielded on probe-selected items only. The claim lock requires "independent
  human check of probe-selected items." No prospective screen exists yet;
  nothing in this run should be written as one.
- Rule for the manuscript: any sentence that says "pre-piloting" or
  "screening" must refer to the prospective design, which needs the second
  bank and a human fielding plan. The retrospective 42-cohort analysis can
  only say "the instrument's rankings on the existing battery are/is not
  consistent with human rankings on the same items."

---

## 4. Ambiguities requiring parent/user choice (flagged, not invented)

- **A1 — exact 23-item membership.** The lock says 23; the natural derivation
  (26-item grid − Q69–71; Q174 nominal-excluded) gives exactly 23. Confirm
  this enumeration, especially that Q69–Q71 are secondary-only and Q178 stays
  primary despite JOR (see A2).
- **A2 — JOR/Q178 has zero valid responses** in the WVS file (verified:
  0 valid weighted answers), so JOR drops out of the risktaking complete-case
  composite (n=41 there), while the lock's "GBR not asked Q174" is the only
  stated deletion. Recommend: keep Q178 primary (41-country complete-case for
  risktaking, printed), rather than deleting Q178 globally — but this is a
  judgement call above my authority. The adapter column still produces a Q178
  distribution for JOR; the adapter–human cell for (JOR, Q178) is absent.
- **A3 — complete vs available composites** for the primary column (§1).
  Recommend complete-case primary, available-case sensitivity.
- **A4 — numeric-open items** (Q261/Q262): recommend excluded from all
  batteries (grids are observed support, not comparable across archive vs
  cohort; the gate itself pins the archived grid). Confirm.
- **A5 — weight column.** `weight` vs `W_WEIGHT` — identical in shipped files
  (verified on CHN per `eval_config.py` comment); no action, recorded here
  for provenance.
- **A6 — profile-clustered intervals for human columns** (§2): upper-bound
  dependence assumption. Confirm or opt for country bootstrap as primary for
  human-only rows.
- **A7 — GPS z source for profile assignments:** profiles are defined by
  `sign(z)` from `gps_z_vectors.json` (the training labels). Confirm no
  re-derivation from the .dta.

---

## 5. Pre-outcome analysis specification (the frozen plan, in order)

1. **Provenance gate before any scoring read:** 42 adapters whose
   `run_record.json` carries the frozen `bank_run_id`
   (`gps_sign_relabel_all_20260816_004545Z`); `--inventory` UNION (hub ∪ Drive)
   is the only true count; both gates pass (`--gate-cpu`, `--gate`) with the
   archived numeric grid pinned. A passed `--gate` validates plumbing, not the
   adapter path.
2. **Score:** `score_cohort.py` arms base,adapter (persona optional,
   secondary), pairs=matched + all. No outcome inspection before steps 3–5
   are frozen in code.
3. **Recode & composites** exactly per §1; print per-composite complete-case
   country membership and items dropped.
4. **Surfaces:** per dimension — adapter–GPS, adapter–human, human–GPS
   (human–GPS on the 42 uses the existing `human_item_means_42.csv`;
   trust also on the 12-item extension, secondary); patience Q43 and Q50
   separate; TVD / JSD / Wasserstein per item × country as distributional
   descriptives (adapter vs own population), summarized per dimension, with
   the profile-level decomposition (within-profile vs between-profile
   variance share) — this is the twin reliability contrast operationalized.
5. **Inference:** profile-block bootstrap (primary), country bootstrap
   (comparability), profile-equal estimand (sensitivity), adapter-minus-base
   lift (descriptive), near-zero refit variant (sensitivity, after refits).
6. **Reporting rules:** no discretionary subsetting of the 42 after seeing ρ
   (Duch rule, extended to Paper B); intervals quoted with the clustering
   stated; any number not in the eventual frozen table is not quotable.

---

## 6. Next experiment — options and a testable pre-outcome decision rule

**Options (claim lock §Paper B, frozen as separate gates):**
1. **Second scenario bank** (new items, same signs) — tests whether the
   adapter carries signs to *new text*; prerequisite for prospective screening.
2. **Sign-retrain placebo** (permute/relabel signs, refit) — tests whether the
   *sign labels* are the causal carrier (Paper A's assignment permutation was
   explicitly not a sign-retrain).
3. **Same-signs-in-prompt arm** (identical sign vector in the prompt, no
   adapter) — route comparison; **not** equivalent to a country persona
   (country name carries far more than six signs; persona stays a separate
   comparator, never a stand-in for this cell).

**Predeclared decision rule (no data-mined numeric cutoffs):**

- **R1 (coherence precondition).** If the profile-clustered 95% interval for
  trust adapter–GPS *includes* 0 (no sign transfer), the instrument claim is
  not alive; the next gate is a **diagnostic replication** (seed replication
  on 2–3 countries, e.g. two twin-group members retrained with different
  seeds) to separate "no signal" from "training noise swamping signal" — not
  a new bank or placebo.
- **R2 (reliability precondition).** Estimate the *noise null* for within-
  profile divergence: retrain at least two countries (ideally from different
  twin groups) with a second seed under the frozen protocol; the observed
  within-profile SD across the 12 groups is compared to this seed-noise SD
  by a simple exceedance statement (how many groups exceed the seed-noise
  95th percentile). If material within-profile divergence beyond seed noise
  exists, **reliability work precedes any placebo**: a sign-retrain read on a
  noisy instrument is uninterpretable. This is a testable rule — the
  comparison is against an empirically estimated noise distribution, not a
  chosen constant.
- **R3 (placebo ordering).** If R1 and R2 hold, run the **sign-retrain
  placebo** next: it is the gate that distinguishes the mechanism claim
  ("signs cause the transfer") from construction artifacts, and it was
  explicitly identified as missing in Paper A.
- **R4 (second bank).** Run after R3 passes: the second bank is the step that
  creates the prospective-screening object (new item text), and it should be
  scored blind (no outcome peeking at the 42-cohort results beyond the
  frozen tables) to keep the screening claim prospective.
- **R5 (prompt cell).** The same-signs-in-prompt arm is last and conditional:
  it is informative only if the adapter route works (R1–R2) — it tests route
  vs weights ("configuration sensitivity"), and it must use the sign vector,
  not a country name.

Sequencing summary: **R1 diagnostics → R2 seed-noise reliability → R3
sign-retrain → R4 second bank → R5 prompt cell.** Each step's go/no-go is a
predeclared comparison (interval contains 0? within-profile SD vs seed-noise
distribution?) rather than a threshold invented after seeing results.

---

## 7. What this draft deliberately does NOT do

No adapter outcome analysis, no scoring run, no GPU session, no uploads, no
repo edits, no disclosure of respondent-level data (only schema/counts of the
aggregated `human_item_means_42.csv` were read). All §4 items need explicit
sign-off before any outcome is computed.
