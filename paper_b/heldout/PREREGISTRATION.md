# Paper B held-out screen: preregistration

Status: final, approved by Augusto Gonzalez-Bonorino on 2026-10-14 and timestamped by
the git tag prereg-heldout-2026-10-14 (section 10). At the time of the tag no adapter
had scored a held-out item, no selection existed, and no held-out human value had been
read. Nothing in this document has been computed on held-out human data. The only WVS-7 content read
so far is variable labels, value labels, country identifiers and questionnaire text.

## 1. Question and estimator

Question. Do the sign-trained adapters predict how countries differ on WVS-7 items
that played no part in their development, when the item-to-dimension assignment is
fixed from the adapters alone, before any human value is read?

Units. 64 sign-profile adapters (the 2^6 factorial, `paper_b/factorial.py`) trained
on bank 2, plus the base model. Countries enter only through the human criterion
(the 42 GPS ∩ WVS-7 countries).

Model quantity. For adapter u and item i, the expected response code under the
frozen scoring instrument (prompt variant v1, spec below), y_ui.

Probe (section 3) assigns each item a dimension d_i and a sign s_i.

Primary statistic. For each selected item i, the signed Spearman correlation
a_i = s_i · ρ(country weighted mean of item i, GPS z on d_i) over the 42 countries.
The primary estimate is the mean of a_i over the selected items, A = mean_i a_i.

## 2. Pool construction (fixed)

Built by `paper_b/heldout/build_pool.py` at commit 1511995 from WVS-7 metadata
only (`pyreadstat`, `metadataonly=True`).

Rule: `Qnnn` variable; not among the 35 items of
`DPO_eval_WVS/question_map_wvs_edited.csv`; Q < 260 (demographics excluded);
2 to 11 contiguous non-negative codes; ordinal code order.

Text-review overrides (`paper_b/heldout/overrides.json`, reasons recorded per item):
excluded Q56 (code order better/worse/same is not monotone), Q91–Q93 (knowledge
quiz), Q111 (code 3 "Other answer"); 17 items confirmed ordinal by reading their
labels; wording repaired for 10 items whose questionnaire text did not extract.

Result: 223 items. By response-code count: 2 codes 30, 3 codes 34, 4 codes 94,
5 codes 21, 7 codes 1, 8 codes 1, 10 codes 33, 11 codes 9.

Hashes:
  pool_skeleton.csv   c78faa7552a918e7cf840a726fb60c9b3fd1698259a31f6f18aff43bf91ea135
  overrides.json      d851264738aa6f44601c378362a8241bc633235c81ff5cf12484baa9522b09b4
  heldout_v1 spec     4d799b029102d7e7… (spec_sha256 field, 223 questions)

## 3. The probe (fixed)

`paper_b/heldout/probe_select.py`. For each item, OLS of y_ui on the 64 units with an
intercept, six main effects (x_d = ±0.5) and all 15 two-way interactions; error df 42.
t_d is the main-effect t statistic.

  top dimension  d_i = argmax |t_d|, or "none" if max |t_d| < 2.0
  sign           s_i = sign(b_{d_i})
  imprint set    trust, risktaking, posrecip, altruism (the four surfaces with a
                 cohort-1 imprint; patience and negrecip were flat)
  PRIMARY rule   among items with d_i in the imprint set and |t| ≥ 2, the top 25%
                 of all 223 items by |t| (at most 56 items)
  SECONDARY rule d_i in the imprint set and |t| ≥ 2 (fixed threshold)

Known property, stated in advance: under pure noise, about 26% of items cross
|t| ≥ 2 on at least one of six dimensions (documented by
`test_null_items_are_flagged_at_the_familywise_rate`). The selection rule does not
control this rate; the permutation null in section 4 does.

Decided 2026-10-14 (D5): the secondary rule is a reliability check. The primary
rule alone carries the confirmatory test at one-sided alpha 0.05; the secondary
rule's result is reported beside it and does not enter the inference.

## 4. Human criterion and inference

Human values. WVS-7 country means with the survey weight (W_WEIGHT), codes < 0 set
missing, for the selected items only. Read only after FREEZE.json exists.

Inference for A.
  Permutation null over items: draw as many items as were selected, uniformly from
  the 223-item pool, and give them the (d, s) pairs of the selected items in random
  order; 10,000 draws; one-sided p = share of null A ≥ observed A. This null
  absorbs the familywise selection rate in section 3.
  Country bootstrap: 2,000 resamples of the 42 countries for a 95% interval on A.

Also reported (descriptive): the share of selected items with a_i > 0, and A per
dimension.

## 5. Blinding

`paper_b/heldout/freeze.py`. `freeze()` writes FREEZE.json with the SHA-256 of
selection.csv and pool_skeleton.csv, the code revision and the scoring run ids, and
refuses to run twice. Every reader of held-out human data calls `require_freeze()`,
which fails if FREEZE.json is absent or either frozen file has changed. Order of
work: score held-out items (model only) → probe selection → freeze → human join.

## 6. Comparators

Random allocation null: section 4.

Face-valid rule (decided 2026-10-14). What a careful reader would assign from the
questionnaire alone, built by `paper_b/heldout/comparator.py` with the fixed
procedure in its docstring: a construct lexicon assigns an item to a dimension
only when exactly one dimension's words occur in its wording; the direction is
read from the response labels; a person may only confirm, flip, or abstain, with
a written reason per change (`comparator_review.json`). No model output and no
human response were used.

Result on the 223-item pool: 30 items assigned (trust 20, risktaking 4, negrecip 4,
altruism 2); 9 lexicon matches set to "none" and 3 directions flipped, each with
its reason. Of these, 26 fall in the imprint set used by the primary rule.

Test. A_face is the section-1 statistic computed on the comparator's own assigned
items and signs, restricted to the imprint set (26 items) as the primary rule is.
The quantity of interest is D = A_adapter − A_face, with a 95% interval from the
same 2,000 country-bootstrap resamples used for A (both statistics recomputed on
each resample). Readings:
  D's interval above 0  → the adapters find structure the wording does not reveal
  D's interval covers 0 → the adapters match a careful reader
  D's interval below 0  → the reader's rule screens better
A_face on all 30 items (including negrecip) is reported beside it.

Known limitation, stated now: the face-valid rule is concentrated on trust (20 of
30 items, mostly the institutional-confidence battery), so D partly compares
dimension coverage as well as assignment quality; per-dimension A for both routes
is reported.

System One comparator (decided 2026-10-14, before any held-out item was scored by an
adapter). A typed decision model that returns calibrated probabilities instead of
text (TypeSafe AI, jev-1.13.0, pinned; typesafe-sdk 0.7.5) reads only an item's
wording and response options, codes in ascending order
(`paper_b/heldout/jev_comparator.py`, whose docstring states the rule). Call 1 is a
choice over the six GPS construct definitions plus "none"; these are the definitions
used to generate the training data (measurement-method clauses removed) and contain
no country, model-output or human-response information, so the contrast is not
circular. One run assigns an item when the top choice is not "none" and its
probability is at least 0.5 (untuned). Call 2, for an assigned item only, asks
whether the lowest code reveals more of that trait than the highest; sign is −1 when
that probability is at least 0.5, else +1. Exact ties: probability 0.5 resolves to −1,
call-1 ties resolve by definition order.

Repeat-call rule. A single call proved unstable at the threshold: two complete runs
disagreed on 5 of 223 pool items, all with top probability within 0.03 of 0.5 or a
direction probability within 0.04 of 0.5, while the 23 battery items were identical.
The comparator of record is therefore five independent runs, and an item is assigned
only when at least three runs give the same dimension and sign. All five runs' requests
and answers are archived (`jev/run1`…`jev/run5`) and frozen with the selection.

Results. Battery validation (reported, never used for tuning): 12 of 23 frozen
dimensions recovered (trust 9 of 9, altruism 2 of 3, negative reciprocity Q195; Q81
positive reciprocity read as trust), 12 of 12 directions correct; the other 10 items
are abstentions, mostly items the earlier direction audit classed as non-aligned or
ambiguous. This design cannot say whether those abstentions reflect the comparator or
the battery, and neither reading is claimed. Pool: 42 of 223 items assigned (trust 33,
altruism 7, risk-taking 1, negative reciprocity 1); 39 unanimous; Q210 holds its sign
by 3 of 5 runs and is flagged. On the 23 items both comparators assign, they agree on
dimension and sign 23 of 23.

Test. Abstentions never enter a statistic (`screen_test` refuses sign-0 rows). The
primary reading of the contrast with each comparator is coverage-matched: D_common =
A_adapter − A_comparator computed on the items both the adapter selection and the
comparator assign, so the same items enter both statistics, with a 95% interval from
the paired 2,000-resample country bootstrap. Reported beside it: D over each route's
own items, D per dimension, and each route's coverage by dimension. Readings as for the
face-valid rule.

Known limitations, stated now: both comparators concentrate on trust (Jev 33 of 42,
face-valid 20 of 30), which is why the coverage-matched and per-dimension contrasts are
primary; jev-1.13.0 is a closed model with stochastic probabilities, so the archived
runs, not a re-query, are the record.

## 7. Human ceiling

For items fielded in both waves, the Spearman correlation of country means between
WVS wave 6 and wave 7 (WVS time series, 28 countries with both waves), averaged over
the selected items, with the same signed construction against GPS z. This gives the
agreement two human surveys achieve on these items, the reference against which A
is read.

## 8. Planned sensitivity

  secondary threshold rule (section 3)
  dropping items whose |a_i| < 0.15 is NOT used for the primary; reported only as
  item-level descriptives
  leave-one-country-out range of A
  readout variants: the probe re-estimated under reverse_options and both
  paraphrases; the share of items whose (d_i, s_i) is unchanged
  sign-prompt arm: the same probe applied to the 64 sign-prompt profiles

## 9. What would count against the claims

  Primary: A not above the permutation null at one-sided 0.05 → the adapters do
  not screen held-out items better than random assignment.
  A above the null but below one-third of the wave-6/7 ceiling → screening signal
  exists but is weak; reported as such.
  Readout variants changing (d_i, s_i) for more than half of the selected items →
  the selection depends on prompt wording.

## 10. Version

Code: the commit carrying the tag prereg-heldout-2026-10-14 on feat/paper-b-cohort
(EconLLM-Lab/SCA2_PofW). The pool was built at commit 1511995.

Timestamp (D4, decided 2026-10-14): this document in the project's GitHub repository,
committed and pushed with the tag prereg-heldout-2026-10-14 before any held-out item
is scored. The pushed tag and its commit date are the public record; an OSF copy may
follow later.

Frozen inputs at the tag (SHA-256):
  pool_skeleton.csv                 c78faa7552a918e7cf840a726fb60c9b3fd1698259a31f6f18aff43bf91ea135
  overrides.json                    d851264738aa6f44601c378362a8241bc633235c81ff5cf12484baa9522b09b4
  face_valid.csv                    047c05a3c819385740bca5bf17442e95b928067be7336cdf2f9193ff3963122b
  comparator_review.json            5ad6decd53cadf2a8551bff4edd3acbf9a49dc1bc323114b59a7f656c1dd7bb7
  jev/majority_face_valid_jev.csv   53d0c8b8062f27c311a5bec32d133e56de877365a65ba32d3f667b2af21092c2

Approvals: the 12 face-valid review calls (9 abstentions, 3 direction flips) were
approved by Augusto Gonzalez-Bonorino on 2026-10-14; D5 (secondary rule is a
reliability check) and D4 (timestamp vehicle) decided by him the same day.

## 11. Amendment 1 (2026-10-16): standalone wording repaired before the freeze

What happened. The first held-out scoring pass completed on the pool as registered at tag
`prereg-heldout-2026-10-14` (runs `bank2-heldout-v1-20261016`, 65 files; `bank2-strict-v1-20261016`, 65
files). Reading the item text afterwards found 12 items whose standalone wording cannot be
answered as written: a sentence cut off mid-clause (Q46, Q175, Q253, Q199), a
question left with a stripped country placeholder (Q121, Q254), a grid row truncated to a bare pronoun or
article (Q82, Q255, Q256), and three second-choice follow-ups that refer to a question that does not exist
in a standalone prompt (Q153, Q155, Q157). The same defect classes appear among the ten wording repairs
already recorded in section 2 (for example Q257 and Q258, whose grid rows were truncated in exactly the same
way); the pool rule and the override mechanism are unchanged.

Full disclosure. The first probe pass was computed and read BEFORE the repairs were chosen, and two of the
repaired items (Q153, Q157) fall in that pass's top 25% by |t|. Nothing is frozen: `FREEZE.json` does not
exist and no held-out human value has been read. The first pass output is retained at
`/Users/bonorinoa/.hermes/profiles/sca/cache/scratch/probe_v1/selection.csv` and is superseded.

What changed. 12 items (Q46, Q82, Q121, Q153, Q155, Q157, Q175, Q199, Q253, Q254, Q255, Q256), each repaired from the item's own read-out options or from
its variable label, with the reason recorded per item in `overrides.json`. Pool size is unchanged at 223.
Section 2's rule, the probe (section 3), the criterion (section 4) and the blinding guard (section 5) are
unchanged.

Amended hashes
  pool_skeleton.csv                 19241f6f103c51d64e295045162bb370920223b7ffad7c5f3c8991f5c101bd44
  overrides.json                    0f5cd2bbd88ef6eaca9cca9ded24e8a5e056276be055b21c1d92b941dd7d3849
  heldout_v1 spec_sha256            46447de63f7cc161c016bdc38a3a7c9e8d351be308c44cf1ccd28d9091d13b38
  heldout_reverse spec_sha256       d30bc4aa67d15430e52e09fdd2f8dd621a4b6aeee1559b6e26abf61a22d87e6c
  heldout_para_a spec_sha256        cbd63283b4d99f6b41a6119148821a56093acb2296845f0662c4185c2f115f47
  heldout_para_b spec_sha256        0680dffbf3d5c67bdf040a93d8454fc3de1ec08e04afdd8fd49360a6d8b30934
  signprompt (uses heldout_v1)      46447de63f7cc161c016bdc38a3a7c9e8d351be308c44cf1ccd28d9091d13b38

Superseded. Section 10's `pool_skeleton.csv` hash `c78faa75…` is the pre-amendment file (CRLF working copy;
its LF git blob is `b221d12a…`, the discrepancy the verifier raised as F7). Section 10's `heldout_v1 spec
4d799b029102d7e7…` is the pre-amendment spec.

Consequences.
  The held-out battery is re-scored for all 64 adapters under the amended spec as a single run id, so one
  instrument covers every item. The sign-prompt arm and the three readout variants are re-scored under the
  amended spec too. The strict battery (23 frozen items) is untouched, because its question map is not the
  held-out pool; its 65 files stand.
  Open item, to be decided before the human join: the face-valid rule assignments and the System One (Jev)
  comparator assignments for these 12 items were made on the pre-amendment wording, since both
  comparator files cover all 223 items. Either they are re-derived on the amended wording, or the
  pre-amendment wording is disclosed for those items.
