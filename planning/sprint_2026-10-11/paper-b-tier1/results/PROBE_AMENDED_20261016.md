# Amended held-out readout and preregistered probe (2026-10-16)

Model-side only. No held-out human value was read at any step; `FREEZE.json` does not exist.

## What completed

- `bank2-heldout-v1-20261016` reached **64 of 64 units** (half A 32, half B 32) at 23:24 local, with
  every unit's manifest carrying the pinned amended spec `46447de63f7cc161c016bdc38a3a7c9e8d351be308c44cf1ccd28d9091d13b38`.
  The spec-aware loader refuses any unit whose manifest does not match, so the table cannot mix
  repaired and pre-repair scores.
- Items table: **223 items x 64 units = 14 272 rows**, sha256 `47387b239cc304a4d8b1e05d8107d250a3ef30c83f246fb46d5f21bcaa17e31d`.
- Selection: sha256 `782b7d2123f9758ea5641c56ddac6bf778fa4a01e3b6e7ce11402d224480bf21`, staged in the
  repository as `paper_b/heldout/selection_amended_20261016.csv` (see the freeze note below).

## Result

| | Amended | Pre-amendment |
|---|---|---|
| Primary | **56 of 223** (the registered 25 % share) | 56 |
| Secondary | **185** | 183 |
| Primary by dimension | altruism 20, risktaking 13, trust 12, posrecip 11 | altruism 22, risktaking 12, posrecip 11, trust 11 |

Primary membership is a fixed-size ranking, so it shifts when |t| moves:

- Left: **Q153** (|t| 24.2 → 9.0) and **Q157** (|t| 26.5 → 4.3, altruism → risktaking) — the only two
  repaired items that had been primary.
- Entered: **Q194** (risktaking, |t| 15.28 in BOTH tables — promoted by ranking, not changed by the
  repair) and **Q253** (trust, 13.15 → 15.25).
- **8 of the 12 repaired items changed their top dimension**; the 12 moved by 0.6 to 22 in |t|.
- The impact is confined to what was repaired: **211 of 223 items have identical |t_top|**; only 7
  moved by more than 1 and 3 by more than 5 (all repaired items).

The load-bearing observation for the paper: **Q157 carried the largest |t| in the whole pool (26.5,
altruism) under the broken wording** — an item whose standalone text asked "And what would be the next
most important?" with no antecedent. Under the repaired wording it is a modest risktaking item
(|t| 4.3). The pre-amendment pool would have handed the human screen its strongest synthetic item on
the strength of an artifact, which is the case Amendment 1 was written to disclose.

## Freezing: mechanics and the one trap

`paper_b/heldout/freeze.py` refuses to run twice and `require_freeze()` re-hashes the frozen files on
EVERY read of held-out human data, failing closed if either file changed or is missing.

- **Freeze a repository path, not scratch.** The selection was copied to
  `paper_b/heldout/selection_amended_20261016.csv` (byte-identical, verified with `cmp`) precisely so a
  scratch prune cannot later block the screen. Pool path: `paper_b/heldout/pool_skeleton.csv`,
  sha256 `19241f6f…` (the amended pool recorded in Amendment 1).
- The call takes `selection_path`, `pool_path`, `freeze_path`, `code_revision` (current HEAD), and the
  `run_ids` actually used.

## Open decisions (the user's; raised but unanswered on 2026-10-16)

1. Comparator treatment of the 12 repaired items: exclude and disclose (keeps the comparator route on
   its preregistered wording), re-derive face-valid plus the 5-run Jev majority for those 12 only
   (spends classifier calls), or keep the existing assignments with a caveat.
2. Timing: freeze now (the readout is complete and the variants cannot change the selection) or wait
   for the three readout variants and the sign-prompt arm (roughly the next afternoon).
