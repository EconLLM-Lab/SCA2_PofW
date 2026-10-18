# Paper B Tier 1 — verification record

Card T8. Every hash, count and minute below was produced by a script that was written and run for this card;
nothing is copied from another note. Sources:

| Output | Produced by |
|---|---|
| `spec`, `frozen`, `revisions` blocks below | `env -u PYTHONPATH .venv/bin/python paper_b/tier1_verification.py hashes` → `…/engineer/cache/scratch/tier1_hashes.json` |
| provenance section below | `… paper_b/tier1_verification.py provenance` → `…/scratch/tier1_provenance.json` |
| compute ledger | `… paper_b/tier1_verification.py ledger` → `…/scratch/tier1_ledger_run.json`, rows in `paper_b/compute/ledger.jsonl`, block in `paper_b/compute/publication_estimate.json` |
| V1 | local re-run of `paper_b/verify_gates.py --scan-text` against the profile bank (gate 5 prints only with that flag; output `…/engineer/cache/scratch/v1_scan_text.out`) |
| V3 | `/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/v3_determinism.py` (not re-run here; value from `results/TIER1_ANALYSIS_20261017.md` §5) |

Run ids in this record are the bank-2 ones. The cohort-1 run `paper-b-20261011` (`sign-prompt-20261011` for its
sign-prompt cell) is unchanged and already in the ledger; it is not re-verified here.

## 1. Artifacts and the run id that produced each

| Artifact | Producer | Run id | Files on the Hub |
|---|---|---|---|
| Bank-2 relabeled bank (64 sign profiles, 658 triplets) | `synthetic_generation/sca2_datagen/relabel.py` | relabel run `gps_sign_relabel_bank2_20261015_062543Z` (generation run `bank2_20261014_20261015T062513Z`) | `banks/bank2_gps_sign_relabel_bank2_20261015_062543Z/` |
| 64 profile adapters (D2 factorial cells) | `paper_b/run_cohort.py --countries <64 profiles>` | bank `gps_sign_relabel_bank2_20261015_062543Z` | `bank2/<run>/profiles/<P_…>/` on the adapter repo |
| Unseeded retrain of `P_1_0_1_1_0_1` (replicate r1) | `paper_b/run_cohort.py` with `SCA2_PB_REPLICATE=r1` | `replicates/r1` | `bank2/<run>/replicates/r1/profiles/P_1_0_1_1_0_1/` |
| 4 near-zero refits/controls (GBR, COL, GBR_control, COL_control) | card T5 | `bank2-nearzero-strict-v1-20261018` (scores), `gate-bank2-nearzero-{GBR,COL,GBR_control,COL_control}-20261018` (gates) | `runs/…`, adapters in `bank2/<run>/near_zero{,_control}/<CC>/` |
| Strict battery scores, base + 64 adapters | `paper_b/score_cohort.py --model-only` | `bank2-strict-v1-20261016` | 65 CSVs + 65 manifests |
| Held-out scores (primary), base + 64 | same | `bank2-heldout-v1-20261016` | 65 + 65 |
| Held-out readout variants (reverse, paraphrase A, paraphrase B) | same | `bank2-heldout-reverse-20261016`, `-para-a-20261016`, `-para-b-20261016` | 65 + 65 each |
| Sign-prompt arm, 64 cells (held-out items) | `paper_b/score_sign_profiles.py` | `bank2-signprompt-heldout-v1-20261016` | 64 + 64 |
| Sign-prompt arm, 64 cells (strict items) | same | `bank2-signprompt-strict-v1-20261018` | 64 + 64 |
| Replicate r1 scores (strict, held-out) | `paper_b/score_cohort.py --model-only` | `bank2-replicate-r1-strict-v1-20261018`, `bank2-replicate-r1-heldout-v1-20261018` | 1 + 1 each |
| Adapter-path gates, two halves | `paper_b/colab/vm_gate.py` | `gate-bank2-A-20261016`, `gate-bank2-B-20261016` | 2 + 2, with `gate_report.json` |
| Item selection and freeze | `paper_b/heldout/probe_select.py`, `paper_b/heldout/freeze.py` | — (commit `5982544`) | `paper_b/heldout/selection_amended_20261016.csv`, `FREEZE.json` |
| Held-out screen, per-dimension intervals, factorial | `run_screen.py`, `analyze_heldout.py`, `per_dimension.py`, `analyze_factorial.py`, `factorial_report.py` | reads the run ids above | `results/SCREEN_RESULT_20261017.md`, `heldout_analysis.json`, `heldout_per_dimension.json`, `factorial/factorial_report.json` |

## 2. Hashes

Scoring spec SHA-256, rebuilt in this working tree by `score_plan.build_spec` at HEAD (`d1ab226`) and compared
with the pin the VM refuses to run without. `spec_pin_mismatches = []` — all ten conditions reproduce:

| Condition | Spec SHA-256 | Questions | Pinned |
|---|---|---|---|
| `strict_v1` (`bank2-strict-v1-20261016`) | `ed3bb964b606a163c792a68eea2ea9e6cc679bb724ead6726c173f36d9a1fbf6` | 23 | same |
| `heldout_v1` (`bank2-heldout-v1-20261016`) | `46447de63f7cc161c016bdc38a3a7c9e8d351be308c44cf1ccd28d9091d13b38` | 223 | same |
| `heldout_reverse` (`…-reverse-20261016`) | `d30bc4aa67d15430e52e09fdd2f8dd621a4b6aeee1559b6e26abf61a22d87e6c` | 223 | same |
| `heldout_para_a` (`…-para-a-20261016`) | `cbd63283b4d99f6b41a6119148821a56093acb2296845f0662c4185c2f115f47` | 223 | same |
| `heldout_para_b` (`…-para-b-20261016`) | `0680dffbf3d5c67bdf040a93d8454fc3de1ec08e04afdd8fd49360a6d8b30934` | 223 | same |
| `signprompt_heldout_v1` (`bank2-signprompt-heldout-v1-20261016`) | `46447de63f7cc161c016bdc38a3a7c9e8d351be308c44cf1ccd28d9091d13b38` | 223 | same |
| `signprompt_strict_v1` (`bank2-signprompt-strict-v1-20261018`) | `ed3bb964b606a163c792a68eea2ea9e6cc679bb724ead6726c173f36d9a1fbf6` | 23 | same |
| `replicate_strict_v1` (`bank2-replicate-r1-strict-v1-20261018`) | `ed3bb964…` | 23 | same |
| `replicate_heldout_v1` (`bank2-replicate-r1-heldout-v1-20261018`) | `46447de6…` | 223 | same |
| `nearzero_strict_v1` (`bank2-nearzero-strict-v1-20261018`) | `ed3bb964…` | 23 | same |

Frozen inputs (re-hashed here, and checked against what `FREEZE.json` recorded):

| Item | SHA-256 | Check |
|---|---|---|
| `paper_b/heldout/selection_amended_20261016.csv` | `782b7d2123f9758ea5641c56ddac6bf778fa4a01e3b6e7ce11402d224480bf21` | matches `FREEZE.json` |
| `paper_b/heldout/pool_skeleton.csv` | `19241f6f103c51d64e295045162bb370920223b7ffad7c5f3c8991f5c101bd44` | matches `FREEZE.json` |
| `paper_b/heldout/FREEZE.json` | `56c31d6dffd33844f00f90cbec0e820f23e035957834e4ad0419c4d2209191c4` | frozen `2026-10-17T22:39:57.692303+00:00`; `code_revision` `357adde4…`; `scoring_code_revision` `2126045d…`; 56 of 223 items selected |
| `paper_b/heldout/overrides.json` | `0f5cd2bbd88ef6eaca9cca9ded24e8a5e056276be055b21c1d92b941dd7d3849` | equals PREREGISTRATION §11 (amended) |
| `paper_b/heldout/face_valid.csv` | `047c05a3c819385740bca5bf17442e95b928067be7336cdf2f9193ff3963122b` | equals PREREGISTRATION §10 |
| `paper_b/heldout/comparator_review.json` | `5ad6decd53cadf2a8551bff4edd3acbf9a49dc1bc323114b59a7f656c1dd7bb7` | equals PREREGISTRATION §10 |

Adapter revisions (pinned, from `score_plan_pins.json`, not typed):

| Pin | Value |
|---|---|
| `adapter_revision` (all bank-2 profile/replicate runs) | `902f262e92bea5450f69335aa3977f28319ff3a1` |
| `nearzero_adapter_revision` (the 4 T5 adapters) | `c4b0f36eae0c15e508f72b606861798c8359131f` |
| Bank inputs (`paper_b/bank2_pins.json`) | bundle `cccf7b05dd576044b8a6a9443d50c8bab5f5c673f2cb90f0073be82d0bbde7ea`; reference cache `beb06ba8cc996cf85a36efa7c6a32a05f7bc10fdaf4247930bcbdb466de1c4a5` (1052 rows), manifest `9b6975925227e2274ad0219375bf397e8d52aeca0ce8cf6c9737339e334ea93a`; near-zero banks `816fe88de9e349643adcbd28945e287f3ac0e57a5f3294b90a771fa9b24bae68` |

## 3. Provenance of the scoring runs (not "byte-identical")

`score_runtime.py` and `score_cohort.py` changed AFTER the Tier-1 scoring, in three commits, and `score_plan.py`
gained the T4/T5 conditions. The precise claim is therefore per run id, and it is the one the VM itself enforces
(no model is loaded unless `build_spec` reproduces the pinned spec hash — see §2).

For each scoring run id: the code revision its own manifests record, and `git diff <revision>..HEAD` over the
readout path (`score_runtime.py`, `score_plan.py`, `score_cohort.py`, `build_scoring_spec.py`, `eval_lib.py`,
`eval_config.py`). `build_scoring_spec.py`, `eval_lib.py` and `eval_config.py` appear in **no** diff: the prompt
builder, the option parsing and the frozen readout constants (T=1, completion `" "+code`, 768-token prompt, no
length normalisation) are untouched. Only add/remove counts and the files touched are shown; the removed lines
are in `tier1_provenance.json`.

| Run id | Code revision the VM ran | Manifests | Diff to HEAD (readout path) |
|---|---|---|---|
| `bank2-heldout-v1-20261016` | `2126045d…` | 65/65 agree | `score_cohort.py` 4, `score_plan.py` +176/-?, `score_runtime.py` 37; 11 removed lines |
| `bank2-heldout-reverse-20261016` | `2126045d…` | 65/65 | same as above (11 removed) |
| `bank2-heldout-para-a-20261016` | `2126045d…` | 65/65 | same (11 removed) |
| `bank2-heldout-para-b-20261016` | `2126045d…` | 65/65 | same (11 removed) |
| `bank2-signprompt-heldout-v1-20261016` | `2126045d…` | 64/64 | same (11 removed) |
| `bank2-strict-v1-20261016` | `51333871…` (62) **and** `f34a79f2…` (3: `P_0_1_1_1_1_1`, `P_1_1_1_1_1_0`, `P_1_1_1_1_1_1`) | 65, **not all equal** | from `51333871…`: 18 removed lines; from `f34a79f2…`: 18 removed lines |
| `bank2-replicate-r1-strict-v1-20261018` | `b2dbbfb…` | 1/1 | 13 removed lines |
| `bank2-replicate-r1-heldout-v1-20261018` | `b2dbbfb…` | 1/1 | 13 removed lines |
| `bank2-signprompt-strict-v1-20261018` | `b2dbbfb…` | 64/64 | 13 removed lines |
| `gate-bank2-A-20261016` | `2126045d…` (1) and `51333871…` (1) | not equal | 11 removed |
| `gate-bank2-B-20261016` | `51333871…` (1) and `2126045d…` (1) | not equal | 18 removed |
| `gate-bank2-{GBR,COL,GBR_control,COL_control}-20261018` | `3b68cab…` | 1/1 each | 3 removed lines |
| `bank2-nearzero-strict-v1-20261018` | `d1ab226…` (= HEAD) | 4/4 | **no diff** |

What the removed lines are. Every removal in `2126045d..HEAD` and `f34a79f2..HEAD` classifies as one of:

- `countries = [c.upper() for c in (a.countries or C.COHORT)]` (2×) and `country = country.upper()` → replaced by
  `C.resolve_units`, which returns a name that is already in `C.COHORT` **unchanged** and upper-cases anything
  else. For the 42 cohort-1 ISO codes and the 64 `P_…` profile units that is the identity (commit `d1ab226`);
  it differs only for a near-zero name such as `GBR_control`.
- `record["n_train"] != C.TRAIN_ROWS` → `!= want_n`, with `want_n = config.EXPECTED_N_TRAIN.get(unit,
  C.TRAIN_ROWS)` (commit `979cf73`). `EXPECTED_N_TRAIN` is `{}` unless the near-zero switch is set, so for every
  cohort-1 and profile unit the check is the same integer 526.
- `CONDITIONS = {` → annotated `CONDITIONS: dict[str, dict] = {`; `score_cohort_args(...)` gained a
  `revision` parameter that defaults to `ADAPTER_REVISION`; `pins = {...}` → `{**old, ...}` in `write_pins`;
  `_present`/`todo_units` gained the optional `spec_sha` argument; two docstring lines. Additive or
  signature-compatible (commit `b2dbbfb`).
- `run_unit`/`run_cohort` gained a named `TypeError` when `production_scorer`, `reference_scorer` or
  `switchback_scorer` is not callable (commit `49d1c9d`). With all three present — every real run — behaviour is
  unchanged; the commit's own message records that it is defensive only.

So: the readout path is **not** byte-identical between the earlier scoring runs and HEAD, and this record does
not claim it is. What is verified is (a) the spec pins, which is what gates a scoring run, are reproduced at
HEAD for all ten conditions; (b) the scoring arithmetic (prompt building, forward pass, `option_logprob` →
`model_prob`) is in files that no diff touches; (c) the three changes are a unit-name resolution that is the
identity for every bank-2 profile unit, an `n_train` check that is the same integer for them, and a guard.

## 4. Acceptance checks V1–V5

| # | Check (pass criterion) | Measured | Verdict |
|---|---|---|---|
| V1 | Bank 2 gates: `ALL GATES PASS`, 640–660 triplets, zero label mismatches, `source_run_id` = bank-2 generation run | Re-run locally for this card on the 64-unit profile bank with `SCA2_PB_PROTOCOL=bank2 SCA2_PB_UNITS=profiles SCA2_PB_PROFILE_DIR=$PWD/synthetic_generation/outputs/gps_sign_relabel_bank2_profiles … verify_gates.py --scan-text` → `cohort: 64 countries`, gates 2/3/4 `PASS`, gate 5 `PASS` (printed only under `--scan-text`), `64 distinct sign profiles; 0 twin groups`, `ALL GATES PASS`, rc 0. Relabel manifest: `n_triplets 658`, `labeling_rule deterministic_sign`, `source_run_id bank2_20261014_20261015T062513Z` = the generation run id pinned in `paper_b/bank2_pins.json`. Profile manifest: `n_triplets 658`, 64 distinct units | **pass** |
| V2 | 64/64 adapters: every `run_record.json` carries the bank-2 `bank_run_id`; hub listing shows 64 | Adapter repo holds 69 bank-2 run records: 64 `profiles/P_…` + 1 `replicates/r1/profiles/P_1_0_1_1_0_1` + 4 `near_zero{,_control}/<CC>`, all with `bank_run_id gps_sign_relabel_bank2_20261015_062543Z` (69 train events in the ledger). Hub listing of `bank2-strict-v1-20261016`: 65 synthetic CSVs + 65 manifests = base + 64 adapters, each manifest carrying spec `ed3bb964…` | **pass** |
| V3 | Readout determinism: 4 gate-run units reproduce `E[recode]` exactly (`max abs diff == 0`) | `results/TIER1_ANALYSIS_20261017.md` §5, from `v3_determinism.py`: 4 units reproduce `strict_v1` exactly, max abs diff 0, 140 rows each; `P_1_1_1_1_1_1` reproduces on both VMs. **Not re-run for this card** (the script reruns 4 Hub CSV pairs; the value is quoted from the analysis) | **pass (quoted)** |
| V4 | Blinding: `FREEZE.json` mtime precedes every read of `Z*P_heldout_human.csv`; guard test passes | `FREEZE.json` frozen `2026-10-17T22:39:57Z`; the freeze was committed at 15:40 and the first held-out human read at `83cd427` `2026-10-17T15:43:42-07:00` (§5 of the analysis: 15:43); the pre-freeze ceiling read only the 23 battery items. `paper_b/heldout/test_freeze.py` and `test_screen_test.py` are green in the suite run | **pass** |
| V5 | Factorial informative: own-surface dominance ≥ 4 of 6 dimensions, adapter route | `factorial/factorial_report.json` → `plan_V5_rowwise_raw: hits 2 of 6` (altruism, negrecip), binomial p 0.21; the two scale-free views beside it agree (2 of 6 standardized, 1 of 7 columnwise, only the trust bit's own effect) | **FAIL** |

## 5. Compute ledger (Phase H)

Command: `env -u PYTHONPATH -u VIRTUAL_ENV .venv/bin/python paper_b/tier1_verification.py ledger`
→ 194 events appended to `paper_b/compute/ledger.jsonl` (254 rows total, all `event_id`s distinct; the 60
cohort-1 rows are untouched) and the `tier1_bank2` block added to `paper_b/compute/publication_estimate.json`
(the cohort-1 `measured`/`discarded_or_incomplete` blocks are unchanged).

Sources: `runs/*/compute/ledger.jsonl` and `bank2/<run>/state/*/compute_ledger.jsonl` on
`Bonorinoa/SCA2-paper-b-artifacts`; the 69 `run_record.json` files under `bank2/<run>/` on
`Bonorinoa/SCA2-paper-b-adapters`; `generation_manifest.json` for the endpoint dollars; and the balance
readings quoted from the final comments of cards T4 and T5.

| Stage | Clocks | Wall minutes | GPU hours |
|---|---|---|---|
| Training (`trainer.train`, one clock per trained adapter: 64 profiles + replicate r1 + 4 near-zero) | 69 | 1087.93 | 18.13 |
| Scoring (`score_and_persist`, deduped per run id and unit) | 98 | 606.98 | 10.12 |
| Reference cache (`forward_passes_after_model_load`) | 1 | 6.33 | — |
| GPU sessions (26 recorded-clock clusters, one column, never summed with the above) | 26 | — | — |

The clocks are not summed into one total: they cover different work (`do_not_sum_clocks: true`).

Endpoint dollars for the bank-2 generation (from `banks/bank2_…/gen_raw/generation_manifest.json`):
`total_cost_usd 13.994752` (teacher 3.76203, generator 7.52406, scorer 2.708662 over 5417.324 s of endpoint
runtime). The manifest's own historical calibration figure is 36.14 USD observed since endpoint creation; it is
not added to the run estimate. Budget band from the plan: ≤ 40 USD endpoints → **13.99 USD for this bank**.
The ≤ 55 Colab-unit band is not checkable from these sources (see §6).

Colab units, quoted from the card comments (Colab reports a remaining balance, not consumption):

| Card | Before | After | Delta | Covers |
|---|---|---|---|---|
| T4 (`192.74 → 189.98`) | 192.74 | 189.98 | 2.76 | replicate r1 (strict + held-out) and the 64 sign-prompt cells (strict) |
| T5 (`188.96 → 186.74`) | 188.96 | 186.74 | 2.22 | T5's own near-zero session (about 1.6 T4 units: 4 trainings + 4 score passes) plus Augusto's separate TPU assignment in the same window |

The pre-existing cohort-1 snapshot (273.63 units remaining at `2026-10-12T06:53Z`) is still in
`balance_snapshot`. Between it and the T4 reading the balance fell 80.89 units, but that interval covers the
whole bank-2 generation, all training waves and all scoring, plus any other work on the account, so it cannot
be split by stage and is reported as a bracket, not as Paper B consumption.

## 6. What failed, or is not resolved

1. **V5 failed: the factorial is not informative by the plan's criterion** — own-surface dominance holds for 2
   of 6 dimensions (altruism, negrecip; ≥ 4 required; binomial p 0.21). The paper reports this outcome.
2. **The readout path is not byte-identical to what the early scoring runs executed.** Three commits
   (`979cf73`, `49d1c9d`, `d1ab226`) touched `score_runtime.py`/`score_cohort.py` after the Tier-1 scoring and
   `score_plan.py` grew the T4/T5 conditions. §3 states what changed line by line. The pins are unchanged and
   reproduced at HEAD, but a claim of "the same code" is not made.
3. **`bank2-strict-v1-20261016` mixes two code revisions** — 62 manifests at `51333871…`, 3 at `f34a79f2…`
   (`P_0_1_1_1_1_1`, `P_1_1_1_1_1_0`, `P_1_1_1_1_1_1`). The two gate runs mix two revisions as well. Both
   revisions are ancestors of HEAD and their readout diffs are listed, but the strict run was not executed on
   one homogeneous checkout.
4. **The sign-prompt scoring has no per-unit ledger.** `score_sign_profiles.py` records no compute event, so the
   64 sign-prompt cells of each sign-prompt run appear in no clock total; their cost only enters through the
   card-T4 balance delta (2.76 units for that whole session). Their cost is therefore unknown, not small.
5. **Ten profile trainings have no session clock.** The `2026-10-15` session ledger was uploaded only as a
   partial drive snapshot, so the units `P_0_0_0_*`…`P_0_0_1_0_0_1` have a surviving training clock in their
   adapter `run_record.json` but no session wall time. Their session clock is missing from the ledger, and the
   imported session clusters are the recorded ones, not a reconstruction.
6. **Colab unit consumption per stage is unknown.** Only two before/after balance pairs exist, both from card
   comments; the two training sessions of 2026-10-15/16 have no balance reading, and the 80.89-unit drop from
   2026-10-12 to the T4 session cannot be attributed (it includes Augusto's stray TPU assignment).
7. **V3 was not re-run for this card.** The measured value is quoted from
   `results/TIER1_ANALYSIS_20261017.md` §5 and the script is named at the top of this file.
8. **Bank-1 endpoint spend is not in the bank-2 manifest**, so the endpoint total above is for bank 2 only; the
   cohort-1 generation cost is not restated here.
9. **Ledger timestamps.** Each appended event carries `recorded_at` = the harvest time, and the time the VM
   actually recorded the clock is in `provenance.observed_at_utc`. Session events are clusters of recorded
   clocks with a 60-minute gap rule (`paper_b/tier1_verification.py`), so a long idle pause inside one VM
   session appears as two clusters.
