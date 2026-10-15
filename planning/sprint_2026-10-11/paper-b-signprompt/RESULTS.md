# Sign-profile prompt cell, 2026-10-11

Run `sign-prompt-20261011`. Base model only, frozen stack (`transformers` 4.46.3, chat date `26 Jul 2024`). Twenty-six sign profiles scored, one forward pass per profile, no adapter, no country name. Twenty-nine minutes on one T4. Files on the Hub at `Bonorinoa/SCA2-paper-b-artifacts`, `runs/sign-prompt-20261011`.

The cell delivers the *same six signs* by prompt instead of by weights. It is not the Paper A country-name persona: a country name carries far more than six signs.

Country-equal Spearman over the 42. Sign columns use profile-block bootstrap, same seed as the banked surface. Adapter column is the banked `paper-b-20261011` surface, repeated for reference.

| Surface | Sign-prompt vs GPS | Sign-prompt vs adapter | Adapter vs GPS |
|---|---|---|---|
| Trust | 0.77 [0.58, 0.84] | 0.83 | 0.74 [0.50, 0.86] |
| Patience Q43 | −0.20 [−0.55, 0.22] | 0.54 | −0.02 [−0.41, 0.45] |
| Patience Q50 | 0.18 [−0.30, 0.57] | 0.88 | 0.18 [−0.31, 0.58] |
| Risk taking | **−0.45 [−0.72, −0.05]** | −0.27 | 0.44 [0.08, 0.69] |
| Positive reciprocity | 0.49 [0.15, 0.71] | 0.85 | 0.49 [0.12, 0.69] |
| Negative reciprocity | 0.00 [−0.44, 0.45] | −0.30 | −0.03 [−0.42, 0.41] |
| Altruism | 0.54 [0.20, 0.75] | 0.86 | 0.41 [0.02, 0.68] |

Profile-equal sensitivity (26 units, matching on member countries rather than on the profile-id string) tracks the country-equal column: 0.79, −0.15, 0.12, −0.45, 0.49, 0.03, 0.49. The result is not a country-weighting artifact.

## What the cell says

**Three of the four imprint dimensions survive the route change.** Trust, positive reciprocity, and altruism clear zero in the prompt cell at magnitudes at or above the banked adapter column. The same six signs, delivered as text with no adapter, recover the same country order. That is what the cell was built to test.

**Risk taking inverts.** The prompt gives −0.45, clearing zero on the wrong side, while the adapter on the identical sign vector gives +0.44. The two routes disagree with each other, so the sign vector alone does not imply the GPS risk order. One of the two is not reading the sign the way the other is.

**Negative reciprocity stays flat on both routes** (0.00 prompt, −0.03 adapter) against a human map that works (0.42). It is the one dimension neither route reaches.

**Patience Q43 is a map failure, not a route failure.** The human map is −0.53.

The high sign-versus-adapter column on five surfaces (0.83–0.88 for trust, Q50, positive reciprocity, altruism) says the prompt route and the weight route are largely redundant representations of the same sign information, with risk taking as the exception.

## Caveats

- The prompt route is a different object from the adapter route. Agreement on five surfaces is a finding about redundancy, not about which one is correct.
- Profile ids in `sign_profiles.json` are written in `sign_prompt.DIMS` order, while `analyze_surface.sign_profiles` uses `PROF_DIMS` order. The two write the same partition with different strings, so the profile-equal column matches on member countries. Do not join them on the id string.
- This cell does not carry either locked Paper B claim. It is a route comparison on the existing battery.
