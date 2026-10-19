# C7 claim-lock amendment: DRAFT for orchestrator review

> **Record, not status.** Written 2026-10-17. Lines about what is done, blocked or next describe that date, not today. Current status: [STATUS.md](../../../STATUS.md). Applied, with changes, as Amendment C7 in planning/TWO_PAPER_CLAIM_LOCK.md; the lock wins.

Card T9 (checkpoint C7). Draft date 2026-10-17 (MST); the result notes carry the 20261018 UTC tag.
Status: **draft, not applied.** This file does not edit `planning/TWO_PAPER_CLAIM_LOCK.md`. The orchestrator
reviews it and applies it. Nothing here is committed.

Every number below is filled from `planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv` by a template
renderer, not typed. The table is built by `paper_b/build_numbers_table.py` from the JSON/CSV outputs named in
its `output_file` column. Claim ids are cited in square brackets so each sentence can be traced. Each number
carries its surface label (section 1). Numbers from different surfaces are never merged.

Paper A is untouched by this amendment. Its locked numbers, panel and non-claims stand as written.

---

## 1. Surfaces (the labels every number carries)

| Label | Surface |
|---|---|
| S1 | Strict 23-item battery. 42 cohort-1 country adapters (bank 1, run `paper-b-20261011`). Adapter-GPS Spearman over 42 countries, profile-block bootstrap (26 clusters). Model side against the declared GPS coordinate; no human data. |
| S2 | Same battery. 64 bank-2 sign-profile adapters (run `bank2-strict-v1-20261016`), each of the 42 countries mapped to its sign-profile unit. Same statistic and bootstrap as S1. |
| H | Held-out screen. 223 WVS-7 items that no adapter was built for (pool v1, amended). Items assigned to a dimension and sign by the adapters alone. Criterion: WVS-7 survey-weighted country means against the GPS z of the assigned dimension, 42 countries. **Retrospective**: the human file existed before the probe. |
| F | Factorial. Strict battery, 64 sign-profile cells, main effects of six sign bits on seven surfaces. Two routes: bank-2 adapters, and the sign-profile prompt (run `bank2-signprompt-strict-v1-20261018`). Model side only. |
| R | Replicate. One unit (`P_1_0_1_1_0_1`) retrained without a fixed seed, scored on the strict battery and on pool v1. Model side only. |
| N | Near-zero refit. Two predeclared refits (GBR, COL) and size-matched controls, strict battery. Model side only. |

---

## 2. Transport (retrospective): two checks, and they disagree by dimension

The two checks measure different things and are reported side by side. They are not averaged and neither
overrides the other.

- **C3 (surface S2).** Do the trained battery surfaces keep their adapter-GPS agreement when the scenario bank is
  replaced? Same rule, new generator, same 23 items, no humans. Pass rule fixed at C0: an imprint interval that
  includes 0 drops that dimension's transport sentence.
- **C5 (surface H).** Do the items the adapters assign to a dimension track the human country map in the assigned
  direction, on items no adapter was built for? `A_d` is the mean over the items assigned to dimension `d` of
  `sign_i x Spearman(country mean of item i, GPS z on d)`. Rule fixed at C5: an imprint dimension whose
  interval includes 0 is not transport. The interval is the registered 2,000-resample country bootstrap.

### 2.1 Table: both checks, per imprint dimension

| Dimension | C3, S2: bank-2 adapter-GPS rho [95% interval] | C3 reading | C5, H: A_d, adapter primary rule [95% interval], items | C5 reading | Passes both? |
|---|---|---|---|---|---|
| trust | 0.803 [0.615, 0.876] | holds | 0.062 [-0.047, 0.173], 12 | not transport | no |
| risk taking | 0.210 [-0.199, 0.584] | dropped | 0.158 [0.015, 0.290], 13 | **transport** | no |
| positive reciprocity | 0.366 [-0.068, 0.652] | dropped | -0.071 [-0.281, 0.154], 11 | not transport | no |
| altruism | 0.364 [-0.057, 0.653] | dropped | 0.069 [-0.036, 0.177], 20 | not transport | no |

Ids: `B2_bank2_<dim>_rho`, `PD_adapter_primary_<dim>_A`. Interval of each cell: n = 42
countries on the C3 side. **No imprint dimension passes both checks.** Imprint dimensions kept on C3:
1 of 4; dropped: 3.

### 2.2 C3 in more detail (surface S2 against S1)

The banked cohort-1 surface S1 is reproduced exactly by `paper_b/bank2_transport.py` (trust
0.744 [0.500, 0.865]). Beside the bank-2 column above, the S1 values are: risk taking
0.435 [0.085, 0.686], positive reciprocity
0.488 [0.120, 0.695], altruism 0.406
[0.020, 0.676] [`B2_cohort1_<dim>_rho`]. On bank 2 the three non-imprint surfaces stay flat and are
reported only: negative reciprocity 0.239 [-0.237, 0.604], patience Q43
0.005 [-0.403, 0.470], patience Q50 0.161
[-0.343, 0.557].

Bank-to-bank agreement over the 26 shared sign cells (Pearson [95% interval]): trust
0.909 [0.797, 0.965], altruism
0.949 [0.859, 0.989], positive reciprocity
0.898 [0.775, 0.960], negative reciprocity
0.708 [0.488, 0.861], risk taking
0.598 [0.229, 0.819]
[`B2_bank_to_bank_<surface>_pearson`]. Risk taking is the least bank-stable surface, which fits its
drop on C3. A bank-to-bank correlation shows that the bank changes the instrument little on a cell mean; it is not
a human criterion.

### 2.3 C5 in more detail (surface H)

The registered primary test. A = 0.061 [-0.007, 0.126] over 56 selected items
[`SCR_A_primary`]. The one-sided permutation p is 0.0097 (null mean 0.012, 95th percentile
0.046) [`SCR_p_perm`, `SCR_null_mean`, `SCR_null_q95`]. Preregistration section 9 reading: the null is
rejected and the signal is **weak**. Against the registered wave-6 versus wave-7 ceiling (mean
0.746 over 34 items fielded in both waves), A is 8.1% of
the ceiling; one third of it would be 0.249 [`SCR_A_over_ceiling`]. The bootstrap interval
touches 0 while the permutation test rejects the null: the sign of the finding is clearer than its size. The
ratio is a benchmark; the two statistics are built differently (per-item over 42 countries against per-surface over the countries fielded in both waves).

Reliability checks (not inference): the secondary rule gives A = 0.070 over
185 items [`SCR_secondary_A`]. Leave-one-country-out A ranges 0.051 to
0.072 [`SCR_loco_min`, `SCR_loco_max`]. On the 34 items fielded in both waves, A is
0.043 on wave-6 means and 0.047 on wave-7 means (exploratory) [`SCR_A_wave6`, `SCR_A_wave7`].
174 item-country cells were never fielded and enter as missing.

Per dimension, secondary rule beside the primary (A_d [interval], items): risk taking
0.143 [0.045, 0.229], 50
(excludes 0); trust 0.092 [-0.019, 0.199],
44; positive reciprocity -0.049
[-0.198, 0.117], 22; altruism
0.040 [-0.038, 0.117], 69.
Both rules agree: only risk taking excludes 0. Positive reciprocity has a negative point estimate in both, and
only 18.2% of its 11 primary
items have a positive item agreement, against 92.3% of
13 for risk taking [`PD_adapter_primary_<dim>_share_pos`]. The
per-dimension permutation p in `heldout_per_dimension.json` is descriptive and unregistered. It points the other way
from the registered interval for altruism on the primary rule, so the paper reports the registered interval and
says that.

Per-dimension cells are small (item counts above). An interval that excludes 0 by a small margin
([0.015, 0.290], 13 items) is one dimension out of four on
one pool, and it is not the dimension the bank-2 check supports.

### 2.4 What the paper may write on transport

1. "On the 23-item strict battery, the trust adapter-GPS agreement carries over to a second scenario bank
   (rho 0.803 [0.615, 0.876], 42 countries, 26 sign-profile cells). Risk taking,
   positive reciprocity and altruism do not keep an interval that excludes 0 on the second bank."  [S2]
2. "On 56 of 223 WVS-7 items that no adapter was built for, selecting items with adapter-assigned
   dimensions and signs predicts the direction of the human country differences better than random assignment
   (A 0.061, one-sided permutation p 0.0097); the signal is weak (8.1% of
   the wave-6/7 benchmark) and its country-bootstrap interval [-0.007, 0.126] touches 0."  [H, retrospective]
3. "Within that screen only the items assigned to risk taking exclude 0 (A_d 0.158
   [0.015, 0.290]); trust, positive reciprocity and altruism do not."  [H, retrospective]
4. "No imprint dimension passes both the bank-2 check and the held-out check. The paper therefore reports two partial
   results on two surfaces and does not claim that the anchor transports for any single dimension."

**Recommendation (a scope decision; escalate to Augusto).** Keep the general Paper B transport sentence of the
lock ("a new battery's adapter-GPS can be interpreted as transport of the anchor") **unwritten**. It stays a
conditional claim whose condition (an imprint dimension that passes both checks) is not met. Sentences 1 to 4 are
what the evidence supports.

---

## 3. Pre-piloting: NOT supported

The claim stays prospective and is not written as a result.

- The WVS-7 join is **retrospective**: the survey existed before the probe, the pool and the adapters. The journey
  plan's own risk list says "C5 fails if that file is the only human source", and that is the case here.
- C0 required a named human route: existing public microdata outside the battery, or a collaborator's secured
  fielding plan. Existing public microdata is the route used, and it is retrospective. No prospective route exists
  in 2026.
- C5's pre-piloting checkpoint (the probe-selected set differs from what a human-only rule would have kept, with the
  human-only rule declared before the join) was not run. The claim is not written.
- The comparison that comes closest, adapter against the face-valid reader and the Jev System One reader (section
  5), is a comparison of two item-to-dimension rules against the same retrospective map. It is not a test that
  pre-piloting changes what a researcher would field.

Allowed: "pre-piloting is a prospective use of the instrument that this paper does not test."
Not allowed: any sentence in which pre-piloting is demonstrated, supported, or partly supported.

---

## 4. The factorial (surface F): own effects, V5, cross-talk, route contrast

Full 2^6 design over 64 cells, seven surfaces, main effects (error df 42).

**Own effects in the intended direction (adapter route).** All seven own effects are positive:
trust 0.364 (OLS t 16.7), negative reciprocity
0.625 (t 11.6), altruism
0.242 (t 6.3), patience Q50
0.133 (t 6.1), risk taking
0.140 (t 4.1), patience Q43
0.049 (t 3.6), positive reciprocity
0.124 (t 3.0) [`FX_adapter64_<surface>_own_beta`,
`_own_t`]. Own effects against the intended direction: 0 of
7.

**V5 failed.** The plan required own-surface dominance for at least four of six bits. The adapter route has
2 of 6 (altruism and negative reciprocity; binomial p
0.207) [`FX_adapter64_V5_hits`]. Standardized rows: 2
of 6. Columns (a surface's largest mover is its own bit):
1 of 7 (trust only). Say so; do not call the
sign bits "separable dimensions".

**Cross-talk.** Each bit moves its own surface in the right direction and also moves the others, often more. The
risk-taking bit moves the altruism surface by 0.983 (altruism's own bit:
0.242) and negative reciprocity by -0.668 (own bit:
0.625). The trust bit moves patience Q50 by 0.495
(own bit: 0.133) and positive reciprocity by
0.418 (own bit: 0.124). The trust bit is the largest
mover on 3 of
7 surfaces. One common direction carries
51.3% of the variance of the seven surfaces (mean absolute inter-surface correlation
0.395).

**Route contrast with the 64-cell sign-prompt result (same 64 cells).** The prompted route fails V5 too, by the same
count (2 of 6; p 0.207), so V5
does not separate the routes. What separates them is the common direction and the sign of the own effects:

| | Adapter route | Sign-prompt route |
|---|---|---|
| Variance on the first common direction | 51.3% | 83.5% |
| Mean absolute inter-surface correlation | 0.395 | 0.807 |
| Surfaces whose largest mover is the trust bit | 3 of 7 | 7 of 7 |
| Own effects against the intended direction | 0 of 7 | 3 of 7 |

On the prompted route the wrong-signed own effects are risk taking -0.457 (OLS t
-22.3), patience Q43 -0.069 (t
-19.8) and negative reciprocity -0.023 (t
-1.80; this one is not distinguishable from 0). The prompted trust bit alone moves risk
taking by -0.858 and patience Q50 by 1.774
[`FX_signprompt64_*`].

Held-out counterpart (surface H): the same probe applied to the prompts does not pass the null (A
0.028 [-0.109, 0.158], p 0.5085), and it assigns its items to a single dimension (trust). The
adapter route passes the null and the prompt route does not, but the direct difference is **unresolved**: adapter
minus prompt 0.033 [-0.083, 0.143] on own items (56), 0.004 [-0.065, 0.075] on the
16 shared items. The two routes share 16 selected items and agree on
dimension and sign for 6 [`SP_*`].

Allowed: "each sign bit moves its own surface in the intended direction on the adapter route; the bits are not
separable, and the prompted route is more entangled and moves three own surfaces the wrong way." The contrast
measures two instruments (trained versus prompted), not two training recipes. Exploratory 26-cell figures from the
earlier note (59.6% against 88.3%) are superseded by the 64-cell
ones and are not cited.

---

## 5. Comparators (Amendment 2) and readout robustness

**Comparators (surface H, Amendment 2 applied: the 12 repaired items leave both routes, which removes only Q82).**
Registered primary contrast, coverage-matched, adapter minus comparator on the items both assign:

| Comparator | Items both assign | D_common [95% interval] | Agree on dimension and sign | D on own items [interval] | Comparator A, own imprint items |
|---|---|---|---|---|---|
| Face-valid reader | 5 | 0.020 [-0.181, 0.215] | 1 of 5 | -0.034 [-0.242, 0.169] | 0.095 (25 items) |
| Jev System One (5-run majority) | 9 | -0.002 [-0.064, 0.061] | 7 of 9 | -0.067 [-0.237, 0.103] | 0.128 (40 items) |

The adapter's own A is 0.061 on 56 items. All four intervals cover 0, so the registered
reading is "the adapters match a careful reader". Say it with its qualifiers: the coverage-matched contrasts rest on
5 and 9 items; both comparators concentrate on trust, so their own-item
A is higher than the adapter's, and higher than the adapter's own trust items (0.062);
per-dimension comparator cells with few items are uninformative by construction and every per-dimension interval
includes 0
(`PD_face_valid_*`, `PD_jev_majority_*`). **Recommendation:** write "the registered contrast does not distinguish the
adapters from a careful reader" and give the registered phrase beside it, because an interval that covers 0 on so few
items does not establish a match.

**Readout robustness (surface H, model side).** The registered statistic is the share of selected items whose
(dimension, sign) is unchanged. Adverse only if more than half changed. Reversed options:
39 of 56; paraphrase A:
39 of 56; paraphrase B:
30 of 56
[`RO_<variant>_ds_unchanged`]. No variant triggers the adverse condition; paraphrase B is closest. Item-level
assignment is fairly stable but set membership churns, because membership is a top-quartile ranking cut: items in
both primary sets are 18, 29
and 16 of 56, and the correlation
of |t_top| with the base is 0.176, 0.546 and
0.271. Allowed: "item assignment is robust to option order and paraphrase; the particular
56-item set is not." Not allowed: "the 56 items are the items the instrument selects" without that sentence.

---

## 6. Replicate (unseeded retrain) and the near-zero margin (C6)

### 6.1 Replicate

One unit (`P_1_0_1_1_0_1`) was retrained from the same recipe with no seed fixed, and scored on both batteries.
Strict battery (140 cells): largest single-cell probability difference
0.0515, mean 0.0060, Pearson of expected codes over the
23 items 0.9998. Held-out pool
(1087 cells): largest difference 0.0916, mean
0.0056, Pearson over 223 items
0.9996. Every strict-surface shift is at most 0.1117 of a profile SD (patience Q50 is the
largest) [`RP_*`]. This bounds retraining noise **for one unit**; it is not
the across-unit retraining variance.

### 6.2 Near-zero margin (footnote, never a headline)

Under the predeclared rule the near-zero filter is **not promoted**. Two retained imprint surfaces were read
against size-matched controls and the replicate's noise floor. COL positive reciprocity moved
-0.092 SD against its intended direction, beyond the declared replicate floor
(0.011 SD). That move is much smaller than the variation between two small-data
trainings: a size-matched control differs from the full-data baseline by up to 1.22
SD for GBR and 1.50 SD for COL. **No reversal is claimed.** GBR trust moved
0.448 SD in its intended direction, which is also within that variation. The
dropped-dimension block is a loss-of-signal check and is not evidence either way
(4 of 7 moves against the intended direction
beyond the floor, as expected when a dimension has no training rows). Two refits are a screen: no interval, no
p-value, no claim across the 42. The declared floor comes from one unseeded retrain on the full 526 rows and is too
small to read small-data refits against; the controls show why [`NZ_*`]. The margin stays a footnote carrying both
facts.

---

## 7. What the paper must not claim (explicit non-claims)

Carried over from the lock, then extended.

- Anchor transport for any single imprint dimension. No dimension passes both C3 and C5.
- That the held-out screen is a prospective or independent human check. It is retrospective.
- Pre-piloting: demonstrated, supported, or partly supported. Section 3.
- That the trust result on bank 2 (0.803) revises the Paper A locked 0.74, or that bank-2 or
  cohort-1 numbers are bit-level extensions of the Paper A surface. S1 and S2 are new surfaces on a new pipeline
  stage; the Paper A 16-country panel is a different panel.
- That the screen is large. It is 8.1% of a benchmark whose own construction differs, and its
  country-bootstrap interval touches 0.
- That the adapters beat a careful reader. No comparator interval excludes 0; the contrasts rest on
  5 and 9 items.
- That the sign bits are separable dimensions, or that the adapter is a "clean compiler". V5 failed
  (2 of 6) and the surfaces share one direction carrying
  51.3% of their variance.
- That adapters beat prompts. On H the routes' difference is unresolved; the factorial contrast is about
  entanglement and wrong-signed own effects, not about screening accuracy.
- That risk taking is "the" transported dimension. It excludes 0 on H only (13
  items), and it drops on C3.
- That the 56 selected items are what the instrument selects, without the churn sentence.
- That the replicate reproduces the original weights, or any weight-space cosine (F8).
- That the near-zero filter helps, hurts or reverses anything. It is not promoted and no reversal is claimed.
- That the probe's per-dimension permutation p values (unregistered) replace the registered intervals.
- That the 64 factorial cells are 64 realized country profiles. They are constructed cells; the country files
  realize fewer distinct sign vectors than there are countries (verifier report).
- Human country-level values. None are in the repository, the table or this draft.
- Magnitudes, within-profile human variation, or a recovered GPS coordinate (unchanged from the lock).
- Patience Q43, Q50 and negative reciprocity as imprint or transport results. They are reported as missing.

---

## 8. Wording decisions (one recommendation each)

### F7. Pool hashes and line endings

Recommendation: record **both** hashes of the amended `pool_skeleton.csv` and state the convention in one line.

- Working copy (CRLF, 81405 bytes): `19241f6f103c51d64e295045162bb370920223b7ffad7c5f3c8991f5c101bd44` [`HASH_pool_worktree`]
- Git blob at HEAD (LF, 81181 bytes): `a1dbceea1a33da05f0432e14e0ff174ba239916b1a5beb9944e9aa0910cd40a5` [`HASH_pool_git_blob_lf`]
- Pre-amendment, CRLF form (the hash in the preregistration, section 10): `c78faa7552a918e7cf840a726fb60c9b3fd1698259a31f6f18aff43bf91ea135`
  (80472 bytes); its LF git blob at the tag: `b221d12aed460772103c729ce3c79860267fa4c5b6940d5de38d6b9967c0e920`
  (80248 bytes).
- `overrides.json` (amended; LF in the tree and in git): `0f5cd2bbd88ef6eaca9cca9ded24e8a5e056276be055b21c1d92b941dd7d3849`.

Convention sentence: "Hashes of text files are given for the working-tree bytes; `pool_skeleton.csv` is written
with CRLF by `build_pool.py`, while the repository stores text with LF (`.gitattributes`: `* text=auto`), so the hash
of the git blob differs; both are given, and the amended pool is regenerable byte for byte from `overrides.json` with
`python paper_b/heldout/build_pool.py`."

Reason: the verifier's F7 is right and fully explained (same 223 items, different line endings). Recording one hash
would invite the same objection. **Related risk, surfaced and not fixed here:** `freeze.require_freeze` hashes raw
bytes and `FREEZE.json` holds the CRLF hash. On a checkout that materialises LF the file hashes to the blob form and
the guard fails closed. A reader must regenerate the pool with `build_pool.py` (which reproduces the CRLF bytes), not
rely on the checkout. Say that in the reproducibility appendix.

### F8. The replicate is "an unseeded retrain"; no weight-space cosine

Recommendation: write "one profile was retrained under the same protocol as an unseeded retrain, providing a
noise-floor estimate for the pipeline" and cite only the scored differences in section 6.1.

Reason: `train_country.py` sets no seed, so LoRA initialisation is unseeded; no artifact records a cosine. A cosine of
independently initialised adapters near 0 would not mean "the updates disagree", and a test in
`paper_b/test_analyze_replicate.py` fails if the module ever calls one. Do not add a seed to the runner to make the
sentence nicer: it would make a future retrain differ from the 64 banked adapters. A seeded protocol is a new run id.

### F11. The sentence about `config.py`

Recommendation, exact sentence: "The cohort-1 defaults of `paper_b/config.py` are unchanged when the environment
variable `SCA2_PB_PROTOCOL` is not set to `bank2`."

Do not write: "`config.py` is byte-identical to the cohort-1 runner", and **do not write "when `SCA2_PB_UNITS` is
unset"**. Two conflicts between the checklist and the code, surfaced here and not resolved silently:

1. **The variable is wrong in the checklist.** In the code the switch is `SCA2_PB_PROTOCOL` (`config.py:86`).
   `SCA2_PB_UNITS` is read only inside `protocol_bank2.apply`, which runs only when `SCA2_PB_PROTOCOL=bank2`. With the
   protocol set to `bank2` and `SCA2_PB_UNITS` unset, `apply` still redirects `BANK_RUN_ID`, `DATA_ROOT`, `N_ROWS`
   and the adapter paths. The sentence "unchanged when `SCA2_PB_UNITS` is unset" would therefore be false.
2. **The byte-identity statement in `F7_F11_RESOLUTION_20261016.md` is stale.** It said `git diff --stat
   prereg-heldout-2026-10-14 HEAD -- paper_b/config.py` is empty. At HEAD it is not: commits `979cf73` and `d1ab226`
   (card T5) added `EXPECTED_N_TRAIN`, `NEARZERO_DIR` and `resolve_units` (9 insertions); the file's git object is no
   longer the tag's. The held-out arm and the strict scoring ran before those commits, so no result is affected. The
   property that remains true, and is the one to state, is behavioural: loading `config.py` with every `SCA2_PB_*`
   variable unset gives the same value for every constant that exists at `a43fff2`, `86fbf10` and the preregistration
   tag. A check run for this draft (`/Users/bonorinoa/.hermes/profiles/engineer/cache/scratch/t9/cfg_check.py`, output
   `cfg_check.out` beside it, exit 0) found zero differing values among the constants each of the three revisions shares with HEAD (counts in that
   file); the constants present only at HEAD are the later additions.

Reason: the sentence must name the real switch and be about behaviour, because byte-identity was never the property
the results depend on, and it is no longer true.

### Carried over from the wording checklist (no new decision)

Amendment 1 disclosure (first probe pass read before the 12 repairs; Q153 and Q157 were in its top quartile;
superseded spec prefix `4d799b02…`, amended `46447de6…`); the bank-2 archive gate is report-only (343 rows, max
|dlogprob| 0.46875, worst rows Q262; write the gap, not "passed"); the held-out pass spans one code revision with
in-place VM plumbing (write the byte-identical-scoring-modules sentence). These numbers are not in
`NUMBERS_TABLE.csv`; the checklist is their source.

---

## 9. Items surfaced for the orchestrator (outside this card's write boundary; nothing changed)

1. **Readout-robustness inputs are not in the tree.** The three variant selections live in the sca profile's scratch
   (`/Users/bonorinoa/.hermes/profiles/sca/cache/scratch/robustness/selection_heldout_*.csv`), which the pruner clears.
   `build_numbers_table.py` recomputes the counts from them and matches the counts recorded in `FREEZE.json`, but it
   will not re-run after a prune. Copy the three files into `results/` (or record their hashes) before then.
2. **Two permutation p values for the sign-prompt arm.** The screen-level p (0.5085, registered
   construction) and the per-dimension note's p differ because the per-dimension null is built differently. The
   per-dimension interval for the prompt route also differs slightly from the screen interval (same A, resampled with
   common random numbers). Cite the screen-level values for the screen and the per-dimension values only for the
   per-dimension table.
3. **`TIER1_ANALYSIS_20261017.md` still carries the 26-cell route contrast** (59.6% against 88.3% on the first direction) in section 4. The
   64-cell numbers supersede it. The notes print the upper bound of the screen interval one unit higher in the third decimal than the script
   ([-0.007, 0.126]); this draft prints the script's rounding. The table keeps the 26-cell rows (`FX26_*`) only for traceability.
4. **The lock's list "Required before those claims"** status after this amendment: item 1 (42 countries) done;
   item 2 (second bank) done, sign-retrain not done; item 3 (sign-profile prompt cell) done; item 4 (independent human
   check of probe-selected items) **not done**; item 5 unchanged (optional protocol papers).
5. **Cohort-1 versus Paper A risk taking.** The lock's Paper A risk adapter-GPS (0.52 on the 16-country panel) and the
   cohort-1 S1 value (0.435, 42 countries) are different panels. Do not place them in one
   column.
6. **Tests for this card.** `paper_b/test_build_numbers_table.py` covers the build. The write boundary names the
   script, the table and the draft; the test file is a flagged deviation so the build is covered.
7. **The journey plan's risk list says "C5 fails if that file [the WVS join] is the only human source".** This draft reads
   that sentence as governing the pre-piloting checkpoint (section 3) and keeps the per-dimension transport reading
   (section 2) as a retrospective result under the C5 interval rule, as card T1 and the orchestrator's note specify.
   If the plan means the whole of C5 fails, the held-out half of section 2 moves from "result" to "not a checkpoint
   pass", and sentences 2 and 3 of section 2.4 would need the word "retrospective" promoted to the front. Your call.

## 10. Index

`NUMBERS_TABLE.csv` has one row per number, columns: claim_id, sentence_use, statistic, value, ci_low, ci_high, n,
surface_label, run_id, producing_script, output_file. Build: `env -u PYTHONPATH .venv/bin/python
paper_b/build_numbers_table.py`. Test: `env -u PYTHONPATH -u VIRTUAL_ENV .venv/bin/python -m pytest -q
paper_b/test_build_numbers_table.py`. No human respondent row, no country-level human mean, no token or secret is in
the table or this draft.
