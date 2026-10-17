# Paper B Tier 1: wording and compliance checklist

Every item here is a fact established from the repository or the run records, paired with the
claim that is TRUE and may therefore be written. Apply when the no-paper-edits window closes.
Nothing here changes the estimand, the bank, or the preregistration.

## 1. The replicate is an unseeded retrain (verifier F8)

- `paper_b/train_country.py` makes no seed call, and no artifact records a weight-space cosine.
  The only `cosine` in the repository is `lr_scheduler_type`.
- **Write:** "one profile was retrained under the same protocol as an unseeded retrain, providing
  a noise-floor estimate for the pipeline."
- **Do not write:** that the replicate reproduces the original weights, or cite a weight-space
  cosine. Neither is measured, and LoRA initialisation was not seeded.
- **Do not "fix" this by adding a seed now.** Adding one would make any future retrain differ from
  the 64 banked adapters and contradict the run record. If a seeded protocol is ever wanted, it is
  a protocol change with a new run id, not a patch to the runner.

## 2. `config.py` byte-identity (F11)

- `config.py` is byte-identical to the preregistration tag `prereg-heldout-2026-10-14`; it differs
  only from the cohort-1 runner commits `a43fff2` and `86fbf10`.
- **Write:** "cohort-1 defaults are unchanged when `SCA2_PB_UNITS` is unset."
- **Do not write:** "`config.py` is byte-identical to the cohort-1 runner."

## 3. Pool hashes and line endings (F7)

- Pre-amendment pool: `c78faa75…` as recorded in the preregistration (CRLF working-tree form);
  the same content as a git blob at the tag is `b221d12a…` (LF), because `.gitattributes` sets
  `* text=auto`.
- Amended pool: `19241f6f…`, which equals `sha256sum` of the file in use, and rebuilds byte for
  byte with `python paper_b/heldout/build_pool.py` from `overrides.json` (`0f5cd2bb…`).
- **Write:** the amended pool hash, the one-line convention about LF storage, and the fact that
  the pool is regenerable from `overrides.json`.

## 4. Amendment 1 disclosure

State plainly: the first probe pass was read before the 12 wording repairs were chosen, and two
of the repaired items (Q153, Q157) were in its top 25 percent. The comparator assignment for those
12 items is an open question, because the face-valid and Jev comparators were derived on the
pre-repair wording. Superseded held-out spec prefix `4d799b02…`; amended `46447de6…`.

## 5. The bank-2 gate archive check (report-only)

Per `PAPER_B_STACK_FREEZE.md`, the base-versus-archive comparison is report-only: 343 rows,
`max |dlogprob| 0.46875`, `max |dprob| 0.0558`, worst rows on Q262. The adapter-path and
switch-back checks are fatal and passed.
- **Write:** the gap and its magnitude, attributed to stack drift between the archive and this run.
- **Do not write:** that the archive check passed, or imply the tolerance was met.

## 6. Blinding

No held-out human value has been read; `FREEZE.json` does not exist. Every number quoted for
bank 2 to date is model-side or preregistration bookkeeping. Keep it that way until the user
writes the freeze file.

## 7. Ledger and clocks

`train_minutes` is `trainer.train()` only. The citable object is
`paper_b/compute/publication_estimate.json`, rebuilt with
`python paper_b/compute_ledger.py publish`. The log parsers now accept both unit families
(three-letter codes and `P_<bits>`), so a clock rebuilt from bank-2 logs reports the 64 cells
rather than nothing (fixed in `587df88`).
