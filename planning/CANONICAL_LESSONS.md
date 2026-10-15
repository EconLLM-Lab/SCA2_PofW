# SCA2 canonical lessons (rules, not a lab diary)
**Frozen 2026-09-16.** Companion to `TWO_PAPER_CLAIM_LOCK.md`.
If a lesson and the lock conflict, the lock wins.

## Construction

1. Production \(G\) is a frozen country-independent A/B bank plus
   `chosen = A if z>=0 else B`. Magnitudes document the profile; they do not
   label. LLM selectors that re-implement that rule add noise; USA/MEX
   agreement was 1,314/1,316. Mexico patience is \(z=-0.11\), never \(+0.32\).
2. Identical sign vectors induce identical labels. 16 countries ⇒ 13
   profiles. USA all-non-negative and Mexico all-negative are a global
   polarity of the same 658 pairs, not six trait contrasts. Mixed vectors
   are dimension-conditional polarity of one joint adapter.
3. Sign-mates in GPS are magnitude-close (not orthant accidents). Killing
   exact twins with continuous \(z\) does not kill near-twins. Magnitude
   labeling is a different protocol (Paper B+, not a Paper A patch).
4. The shared bank is mixed-trait generator judgment. Phi-4 / contamination
   ratios are unused diagnostics, not a gate, not a theory.
5. Anti-leakage removes the country *token* from the eval prompt. It does
   not wipe pretrained associations, bank semantics, or training noise.

## Fitting and readout

6. DPO is regularized Bradley–Terry on pairwise contests. The scenario
   constant cancels. Pairwise losses recover direction and under-disperse.
   TVD then punishes concentration. Report rank and TVD; do not pick a winner.
7. Encoding: reward recovery = adapter margin > reference margin; raw
   accuracy = adapter margin > 0. Neither is GPS country-order recovery.
   Quote pair-pooled rates when cells are the sample.
8. Primary readout is teacher-forced logprob of ` ` + code, softmax over
   supplied codes. Bare codes are a different estimand. Dispersion of that
   softmax is not population dispersion.
9. Score = \(E[g_q(J)]\) after masking WVS missing (−1…−5). Never
   `recode(mean)`. Never recode negatives before the missing mask
   (historic Q69–Q71 bug). Binary items: \(P(\text{option }1)\), not a
   threshold on the mean.

## Evaluation surface

10. Match countries, items, recodes, option grids, and weights before
    comparing arms. A later placebo/regen on a different composite is a
    different estimand — recompute or omit.
11. Do not delete the strongest GPS-tracking items from every country to
    keep a rectangle (Q69–Q71 unasked in Egypt). Primary = rectangle;
    also report the unbalanced items on the observed subset. Keep Egypt.
12. Do not average items with opposite human–GPS signs (patience Q43 vs Q50).
13. Three columns stay separate. Two large anchor associations do not
    imply adapter–human, construct sharing, or a product of correlations
    as a mechanism.
14. A zero Spearman is zero rank covariance of those country scores at
    this \(n\). Report the interval. It is not independence or discriminant
    validity.
15. Assignment permutation of frozen scores is not a sign-retrain. Caption
    “adapters were not refit.”
16. Country-named persona vs unconditioned adapter mixes information and
    route. Isolating route needs a prompt that receives the same signs.
    Interpret the 2×2 per dimension; trust survival ≠ risk survival.
17. Unconditioned adapters emit one fixed distribution. Matched-vs-cross
    is proximity of that distribution to each population, not
    country-conditioned inference.
18. Headline ρ is the locked 16×23 surface. 30-item / 0.70 / 0.78 / pooled
    TVD 0.469 are construction history. Never print them as current.

## Validity

19. GPS is the declared anchor, not an experimental country-level choice.
20. Human–GPS is the criterion for the map. Adapter–GPS is retention.
    Adapter–human is agreement with people. Nomological restrictions are
    extra screens (cvprofiles lane). None of these is causation.
21. Imprint: adapter–GPS ≫ human–GPS where humans ≈ 0 (risk, posrecip on
    earlier maps). Flag, do not celebrate. OOD item scoring is a screen
    that inherits this failure mode.
22. Pre-piloting is an intended use until a held-out battery plus a human
    check exists. Headline Results with the construct map.
23. Empty M* and wide [L,U] (cvprofiles) are honest. Never auto-loosen θ.
    Do not merge cvprofiles into the SCA2 manuscript.

## Process

24. Claim lock + this file before scoring or writing numbers. After LaTeX
    patches, re-read macros (patch doubles backslashes). Builds unverified
    until hashes match.
25. Never overwrite the circulating `position_paper_sca2.pdf`. Fork a sibling.
    Paper edits and CLI work on separate branches. If shipped data
    contradicts the paper, edit the paper first.
26. Methods vs results: more adapters, a second survey, or cvprofiles do
    not repair an ill-posed comparison. Fix the surface first.
27. Country bootstrap only, unless stated. It omits respondent sampling,
    GPS measurement error, and training seeds.
28. Count wins programmatically. When report and pipeline disagree, cite
    the pipeline and footnote the other construction.
29. Public pack = unauthenticated fetch of option-probability CSVs. Do not
    write “public Drive / HF” until that fetch works. Do not redistribute
    WVS/GPS microdata.
30. Archive superseded artifacts; do not delete them. Deleting is how
    0.70 vs 0.78 vs 0.80 became folklore.

## Compute / ops (only when running jobs)

- Project venv: `env -u PYTHONPATH .venv/bin/python`. Colab CLI: also
  `env -u VIRTUAL_ENV`. Write probes as `/tmp` scripts.
- HF token must be re-set in the Colab kernel after every restart; pass it
  explicitly under CLI exec.
- GitHub push as `hermessinho` → 403 on EconLLM-Lab; user pushes.
- SCA2 is a shared working tree: `git ls-remote origin main` + `status -sb`
  before committing.
- Colab Pro sessions die ~60–120 min; one adapter per exec; ground truth
  is remote artifacts, not wrapper exit codes.
