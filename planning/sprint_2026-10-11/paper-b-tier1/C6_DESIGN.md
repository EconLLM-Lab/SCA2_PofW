# C6 — Near-zero margin refit: design note (no GPU spent)

Card T3 (t_448c23d1), 2026-10-17. Status: DESIGN FOR REVIEW. Nothing was trained, uploaded or scored.
Producers: `paper_b/near_zero_bank.py` (tests: `paper_b/test_near_zero_bank.py`).
Outputs, local only: `/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/near_zero/{GBR,COL}/` and
`.../near_zero/subset_declaration.json`.

## 0. Three things the reviewer must see first

1. The filter removes whole dimensions, not scattered rows. The GPS z is one number per (country,
   dimension), so a dimension with |z| < 0.10 loses all its pairs. GBR keeps trust and patience only. COL keeps
   patience, negrecip and posrecip only. The refit adapter has no training signal on the dropped dimensions.
2. The refit also has far less data and fewer optimizer steps (GBR 164 of 526 training rows, COL 260). So
   "refit minus baseline" mixes three things: near-zero removal, less data, and no signal on the dropped
   dimensions. Section 5 says how I propose to read it. Section 7 lists the decisions I need from you.
3. The multi-member pick is a one-row margin (COL 266 vs RUS 265 near-zero training rows). The rule is
   deterministic and used no score, so I applied it as written.

## 1. Definition, and the label-equality proof

Claim from the card: a real cohort country's bank-2 labels equal the labels of its sign-profile unit.

Proof in code (`near_zero_bank.country_rows` rebuilds the labels from the country's real z with its own
copy of the sign rule, chosen = A iff z >= 0; `factorial.label_row` builds the unit's labels; `label_key` =
(triplet_id, chosen, rejected)):

| Check | Result | Source |
|---|---|---|
| 42 cohort countries x 658 triplets, real-z labels vs `factorial.label_row(unit_of_z(z))` | 0 mismatches | `/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/near_zero/logs/build.txt` line 1; `test_every_cohort_country_labels_equal_its_profile_unit_labels` |
| On-disk `gps_sign_relabel_bank2/D_syn_<CC>.jsonl` (written by relabel.py, the independent producer) vs the unit labels, 42 countries | equal | `test_relabel_country_files_on_disk_equal_profile_labels` |
| On-disk profile files (3 units) vs `factorial.label_row` | equal | `test_profile_files_on_disk_equal_label_row` |
| Test file | 12 passed, 0 skipped | `/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/near_zero/logs/test.txt` |

The CLI refuses to build any bank if this check fails.

Near-zero refit for country c in profile u (definition used everywhere below):

    reduced bank(c) = bank-2 rows of unit u, minus rows whose gps_dimension d has |z_c,d| < 0.10   (config.NEAR_ZERO)
    baseline        = the existing bank-2 adapter of unit u (Hub, revision 902f262e...)
    split           = the pipeline's shared split of the FULL 658-row bank (lib.make_shared_split, seed 42, 0.80)

The z file is `analyze_surface.DEFAULT_GPS_JSON` (`gps_sign_relabel_all/gps_z_vectors.json`). Written files hold
dimension names and counts only, no z values.

## 2. The subset, declared now, from exposure only

Rule (no score of any kind): among cohort countries with at least one dimension at |z| < 0.10, take the
singleton-profile country and the multi-member-profile country with the most near-zero TRAINING rows. Ties go
to the alphabetically first ISO3. "Singleton" = the only cohort country in its profile (26 cells, 42 countries).

32 of the 42 countries have at least one near-zero dimension (full list: `subset_declaration.json`). Top of each class:

| Class | Country | Profile | Near-zero dimensions | Near-zero training rows |
|---|---|---|---|---|
| singleton | **GBR** | P_1_1_1_1_0_1 | altruism, negrecip, posrecip, risktaking | 362 (next: DEU 272) |
| multi-member (2 in cell) | **COL** | P_1_0_0_1_1_0 | altruism, risktaking, trust | 266 (next: RUS 265, PER 260) |

Row counts (`near_zero/<CC>/manifest.json`):

| | Source rows | Kept | Dropped | Train: full -> kept (dropped) | Eval kept | Dimensions kept in training |
|---|---|---|---|---|---|---|
| GBR | 658 | 220 | 438 | 526 -> 164 (362) | 56 | trust 82, patience 82 |
| COL | 658 | 328 | 330 | 526 -> 260 (266) | 68 | patience 82, negrecip 90, posrecip 88 |

SHA-256 of the reduced banks:
GBR `3fa619125d2ff2660050a1ba6d9a3331a50b71f2914d97fb6cede473d77590c8`,
COL `87a9cf9db1ae478b6435fc9126e9836e6bededcbbb7cbabcb7358d3be7652fa5`.

Journey wording was "one multi-member profile and one singleton". Both are satisfied.

## 3. Training plan

Same configuration as the bank-2 profile adapters; only the data file changes. All values read from
`paper_b/config.py` and `paper_b/train_country.py`:

| Setting | Value |
|---|---|
| Base model | meta-llama/Llama-3.1-8B-Instruct, 4-bit nf4 |
| LoRA | r 16, alpha 32, dropout 0.05, q/k/v/o |
| DPO | beta 0.1, lr 1e-4, cosine schedule, 1 epoch, max_length 768 (keep_end) |
| Batch | per-device 1, gradient accumulation 16 |
| Split | TRAIN_FRAC 0.80, SEED 42 |

What the smaller row count changes:

- The split is NOT recomputed. Re-splitting 220 or 328 rows would pick a different training set. The reduced bank
  keeps each row's `split` from the full-bank split, so the training rows are exactly the baseline's training rows
  minus the dropped ones. Eval rows are unused by training; they are kept only for the record.
- Reference log-probs come from the pinned bank-2 reference cache (1052 rows = 526 x 2, keyed by
  (prompt, completion)). A subset of the training rows is covered. No new reference pass is needed.
- Optimizer steps drop with the data: floor(n/16) is 32 for the baseline (526 rows), 10 for GBR (164), 16 for COL
  (260). Ceil gives 33, 11, 17. I did not run the trainer, so the exact count is unverified. The engineer must log
  the trainer's `max_steps` and `global_step` and put them in the run record. The cosine schedule is stretched over
  the shorter run, so the learning rate decays in fewer steps. `save_steps=5` is unchanged.
- The shuffle order differs from the baseline run (a different dataset length gives a different order), and the T4
  card calls the replicate retrain "unseeded" (`score_plan.py` comment), so I treat training noise as real.
  Expect it on top of any real effect.

## 4. Where things live

| Item | Path |
|---|---|
| Hub adapter repo (dataset type) | `Bonorinoa/SCA2-paper-b-adapters` |
| New adapters | `bank2/gps_sign_relabel_bank2_20261015_062543Z/near_zero/GBR/` and `.../near_zero/COL/` |
| Never written | `adapters/<CC>`; `config.BANK_RUN_ID`; the existing `bank2/<run>/profiles/` adapters and `.../replicates/` |
| Scoring run id (strict battery) | `bank2-nearzero-strict-v1-20261018` (the launch date stamps it; check that it is unused at launch) |
| Scoring artifacts | `runs/bank2-nearzero-strict-v1-20261018/` in `Bonorinoa/SCA2-paper-b-artifacts` |
| Spec | strict_v1, SHA-256 `ed3bb964b606a163c792a68eea2ea9e6cc679bb724ead6726c173f36d9a1fbf6` (existing pin, unchanged) |

Hub check run for this note (read-only, with token, `/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/near_zero/logs/hub_check.txt`): `.../near_zero/` is empty; no
`nearzero` file exists in the artifacts repo; both baseline adapters (P_1_1_1_1_0_1, P_1_0_0_1_1_0) are present
under `bank2/<run>/profiles/` with weights and run_record.

Two pins this needs that do not exist yet:
- A new adapter-repo commit SHA after upload. `score_plan.ADAPTER_REVISION` (902f262e...) predates the near_zero
  files, so scoring them at that revision would fail. The new SHA goes in a NEW key of `score_plan_pins.json`;
  existing entries stay untouched.
- A gate marker made on the exact refit weights (the T4 replicate gate is the template: the marker carries the
  adapter SHA-256).

## 5. The comparison, and how I propose to read it

Per strict surface s (trust, risktaking, patience:Q43, patience:Q50, altruism, posrecip, negrecip), the composite
is `analyze_factorial.unit_composites` (frozen recode, mean over the surface's items):

    delta_s = ( composite_s[refit adapter of c, scored on strict_v1] - composite_s[baseline adapter of u] ) / SD_s

SD_s = SD (ddof 1) of the 64 profile composites of surface s, from `adapter_strict_v1.csv` (`/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/near_zero/logs/sd_baseline_composites.txt`):

| Surface | SD of 64 composites | GBR baseline composite | COL baseline composite |
|---|---|---|---|
| trust | 0.2221 | 2.8879 | 2.8256 |
| risktaking | 0.2984 | 5.3665 | 5.3593 |
| patience:Q43 | 0.1104 | 1.9904 | 2.0000 |
| patience:Q50 | 0.3147 | 6.8417 | 6.3684 |
| altruism | 0.6235 | 1.9439 | 0.1727 |
| posrecip | 0.3214 | 3.2794 | 3.0109 |
| negrecip | 0.6440 | 7.5270 | 6.9354 |

patience:Q43 has a small SD (0.11) and the baseline composites sit at the ceiling (2.0), so its delta is noisy and
bounded. Report it, do not lean on it.

Intended direction of surface s for unit u: up if the unit's bit for that dimension is 1, down if 0 (the factorial's
own-effect direction; every own effect was positive in TIER1 section 4).

Reading, from C6 ("if an imprint surface moves against the profile's intended direction, say so and do not promote
the filter; if not, the margin stays a footnote"). Imprint surfaces = trust, risktaking, posrecip, altruism
(journey, "Imprint"). Because of point 1 in section 0, I propose two blocks, fixed before scoring:

- Block R, retained dimensions (the test of the C6 rule): surfaces whose dimension is still in training.
  GBR: trust (imprint), patience (not imprint). COL: posrecip (imprint), patience, negrecip (not imprint).
  The C6 rule applies here to the imprint surfaces: GBR trust, COL posrecip.
- Block D, dropped dimensions (a loss-of-signal check, not the C6 rule): GBR altruism, risktaking, posrecip
  (imprint), negrecip. COL altruism, risktaking, trust (imprint). Expectation if the near-zero rows carried the
  imprint: delta moves toward the untrained base model, i.e. down for bit-1 surfaces, up for bit-0 (the base-model composites
  are in the strict run `bank2-strict-v1-20261016`, model `base`; not read here). That is
  "against the intended direction" by construction and is NOT a reason to reject the filter.

Applying the C6 sentence literally to block D would trigger "do not promote" in every case. That is why I ask for
the split in section 7.

Noise reference: a move counts only if it is larger than the retraining noise. The T4 replicate (unseeded retrain
of P_1_0_1_1_0_1, `bank2-replicate-r1-strict-v1-20261018`) gives that noise per surface in the same SD units, but
it is not scored yet (0 files on the Hub on 2026-10-17) and it covers one unit. If it is not available at
reading time, say "noise floor unknown" and do not claim a direction. Two refits are a screen, not a test: no
interval is claimed.

## 6. What the engineer will run

Done in this card (local, CPU; exit codes captured with `echo exit=$?`, no pipe):

    cd /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW
    env -u PYTHONPATH -u VIRTUAL_ENV .venv/bin/python -m pytest -q -rs paper_b/test_near_zero_bank.py     # 12 passed, exit 0
    env -u PYTHONPATH .venv/bin/python paper_b/near_zero_bank.py \
        --out-dir /Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/near_zero                          # exit 0

Needed after you approve, as a follow-up card with a wider Fence (this card may write only the two .py files,
this note and the local folder). Test first for each item:

1. `protocol_bank2`: a near-zero mode (env `SCA2_PB_NEARZERO=<dir>`). Hub prefix
   `bank2/<run>/near_zero`; adapters are keyed by country (GBR, COL); local adapter dir separate from the
   profile adapters; the guard `hub_adapter_path_from_prefix` and `hub_io._guard` keep refusing `adapters/`. The
   reduced banks hold 220 and 328 rows, so `load_bank_manifest`'s 640-660 band must still be applied to the FULL
   bank-2 manifest, never to the reduced one.
2. `near_zero_prepare.py`: write `<CC>_train_with_ref.jsonl` from the reduced bank's `split == "train"` rows and the
   pinned reference cache (`bank2_pins.json`, sha256 `beb06ba8...`), with the same normalization as
   `prepare_data.py`. Fail if any (prompt, completion) is missing from the cache. Assert the counts 164 and 260.
3. `score_plan`: condition `nearzero_strict_v1` (run id above, spec = the existing strict_v1 pin, units GBR and COL,
   adapter revision = the new SHA), plus a gate marker check that compares the adapter SHA-256.

Then on the Colab VM (same setup as `vm_fact_*`; `colab-cli-headless-runs` skill), after the local run above has been
re-verified against the manifests' SHA-256:

    export SCA2_PB_PROTOCOL=bank2 SCA2_PB_UNITS=profiles SCA2_PB_DATA_ROOT=/content/pb_data
    export SCA2_PB_BANK2_DIR=.../gps_sign_relabel_bank2 SCA2_PB_PROFILE_DIR=.../gps_sign_relabel_bank2_profiles
    export SCA2_PB_NEARZERO=/content/pb_data/near_zero            # new, item 1
    python paper_b/near_zero_prepare.py --countries GBR COL       # new, item 2
    python paper_b/run_cohort.py --countries GBR COL              # trains, uploads to bank2/<run>/near_zero/<CC>
    python paper_b/colab/vm_gate_factorial.py                     # gate on the refit weights (marker carries SHA-256)
    python paper_b/colab/vm_score_t4.py nearzero_strict_v1        # new condition, item 3

Back on the Mac, after scoring (names are the strict run's usual files):

    env -u PYTHONPATH .venv/bin/python paper_b/analyze_factorial.py ...   # composites; then delta_s per section 5

and write the sensitivity table, one row per (country, surface), with the block label (R or D) and the noise
reference. The comparison script is part of follow-up item 3 and gets its own test.

## 7. Decisions for you (nothing below is made without them)

1. Reading rule: apply the C6 "do not promote" sentence to block R only, with block D reported as a loss-of-signal
   check (my proposal), or literally to all imprint surfaces (it then fires by construction)?
2. Noise threshold for "moves against": use the T4 replicate's per-surface |delta| as the floor, or fix a number
   now? I have not invented one.
3. Controls: do you want matched controls (same profile, same number of training rows dropped from retained
   dimensions) to separate the near-zero effect from the data-size effect? That is two more adapters and I have
   not planned them.
4. Subset: the rule gives GBR (362 of 526 rows removed) and COL (266). GBR leaves two dimensions. If a
   gentler singleton is wanted (e.g. DEU, ARG), that is a new rule, and it must be declared before any score.
5. GPU budget and the follow-up card's Fence (section 6, items 1-3).

## 8. Not certain

- Optimizer step counts (section 3) are arithmetic, not a trainer run.
- The strict `delta_s` has never been computed: no refit exists.
- `vm_score_t4.py` and the replicate gate were written by another card (T4) and were not read in full; item 3
  assumes they can take a new condition.
- The tests that read real bank-2 data skip when those gitignored outputs are absent; on this Mac they ran (0 skipped).

## 9. Decisions (orchestrator review, 2026-10-17, before any refit is trained or scored)

Checked before deciding: `paper_b/test_near_zero_bank.py` re-run by the orchestrator, 12 passed (with the
T2 tests, 22 passed). The label-equality proof (section 1) is accepted.

1. Reading rule. The C6 sentence applies to block R only (imprint surfaces whose dimension stays in training:
   GBR trust, COL posrecip). Block D is reported as a loss-of-signal check. It is not evidence for or against
   the filter, because a dimension with no training rows moves toward the base model by construction.
2. Controls: YES. For each country, one size-matched control adapter: the same profile unit, trained on a
   uniform random subsample of that unit's 526 bank-2 TRAINING rows, of the same size as the refit's training
   set (GBR 164, COL 260), drawn with `numpy.random.default_rng(20261018)` without replacement, every
   dimension eligible. Same frozen training configuration, same split field, same reference cache. Four adapters
   in total: refit GBR, refit COL, control GBR, control COL. Hub paths: `bank2/<run>/near_zero/<CC>/` for the
   refits and `bank2/<run>/near_zero_control/<CC>/` for the controls.
3. Primary C6 contrast (block R, imprint surfaces): delta = (refit composite - control composite) / SD_s. It
   isolates which rows were removed from how many. Also reported for every surface: refit - baseline and
   control - baseline (the data-size effect), in SD_s units.
4. Noise floor. A move "counts" only when |delta| is larger than the replicate's |delta| on the same surface
   (`bank2-replicate-r1-strict-v1-20261018`, P_1_0_1_1_0_1 retrain vs original, in SD_s units). It is one
   unseeded retrain, so the floor is thin. Two refits are a screen: no interval is claimed. If the replicate is
   not scored, write "noise floor unknown" and claim no direction.
5. Reading. If a block-R imprint surface moves against its intended direction beyond the floor: say so, and do
   not promote the filter. Otherwise the margin stays a footnote.
6. Subset unchanged: GBR (singleton) and COL (multi-member), by the exposure-only rule in section 2.
7. Scope. Card T5 implements section 6 items 1 to 3 plus the control banks (test first), then trains the four
   adapters, gates them, and scores them on strict_v1 under `bank2-nearzero-strict-v1-20261018` (units GBR,
   COL, GBR_control, COL_control, or the naming the code needs; state it). New pins go in NEW keys of
   `score_plan_pins.json`. Budget: at most 15 compute units. T5 starts only after T4 has finished, because
   both cards edit `paper_b/score_plan.py`.
