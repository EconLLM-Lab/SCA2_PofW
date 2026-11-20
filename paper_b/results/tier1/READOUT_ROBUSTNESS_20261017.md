# Readout robustness: reversed options and paraphrase (2026-10-17)

Model-side only. Held-out selection is the base surface; each variant is re-estimated under its own pinned
spec (reverse `d30bc4aa`, para_a `cbd63283`, para_b `0680dffb`). A variant whose manifests do not carry its
pin is refused, not mixed.

## The registered statistic (preregistration sections 8 and 9)

Among the **selected** items, the share whose `(d_i, s_i)` — top dimension AND sign — is unchanged.
Section 9 reads "more than half of the selected items" changed as the adverse outcome: the selection
depends on prompt wording.

| Variant | Primary size | `(d_i, s_i)` unchanged | Registered verdict |
|---|---|---|---|
| `heldout_reverse` | 56 vs 56 | **39 of 56 = 0.696** | within the bound |
| `heldout_para_a` | 56 vs 56 | **39 of 56 = 0.696** | within the bound |
| `heldout_para_b` | 56 vs 56 | **30 of 56 = 0.536** | within the bound, closest to it |

No variant triggers the preregistered adverse condition, but the margin differs a lot: `para_b` leaves
30 of 56 unchanged against a bar of 28, so three more items changing would have flipped it. Reverse and
`para_a` are comfortable at 39 of 56.

## Two separate things, and they disagree in an informative way

- **Item-level assignment is fairly stable.** Dimension agreement within the primary set is 0.696 for both
  variants, and in every case where the dimension agrees the sign agrees too, which is why the `(d,s)`
  figure equals it exactly.
- **Set membership is churny in all three variants.** Agreement is 18 of 56 under reversal, 29 of 56 under
  `para_a`, and 16 of 56 under `para_b`. Membership is a top-25 % *ranking cut*, and many items sit close to
  that boundary, so small |t| shifts reshuffle it while each item's own reading stays put.
- Secondary counts also move with the surface: 185 base, 174 reverse, 168 `para_a`, 190 `para_b`.

Supporting detail: `|t_top|` correlation with the base is r = 0.176 under reversal, r = 0.546 under
`para_a`, and r = 0.271 under `para_b`. Magnitudes move a great deal on every surface, even where the
registered `(d,s)` criterion is met.

## What this means for the freeze

The blocked claim is about *screening held-out items*, whose registered robustness check passes. But anyone
reading the frozen set as "the 56 items the instrument selects" should know that 38 of them are not the same
56 under reversed options. Options to put to the user: freeze the registered `heldout_v1` primary set as
planned and report the membership churn beside it; or additionally name the **stable core** (the 39 items
whose `(d,s)` survives both variants) as a secondary surface. Nothing is frozen either way.

Artefacts: `scratch/robustness/items_*.csv`, `selection_*.csv`, driven by `scratch/readout_robustness.py`.