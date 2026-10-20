# Paper B: co-author brief for the checkpoint of 2026-10-20, 08:00 MST

Draft for co-author review. Every number carries its claim id in brackets and comes from `NUMBERS_TABLE.csv`
(`planning/sprint_2026-10-11/paper-b-tier1/`). Intervals are "lo to hi"; each row's `surface_label` gives the
resampling unit. Counts of countries, signs and surfaces are design facts. Rows marked "descriptive" were not
preregistered and earn no claim.

## 1. What Paper B is now

Paper B is the journal version of our first paper: a preregistered evaluation of the sign compiler as a scoring
instrument. For each country, six signs from the Global Preferences Survey (GPS) define a sign profile, and a
language-model adapter is trained on that profile. We ask whether the adapter's country scores order the countries
as the GPS does: a Spearman correlation across 42 countries [B2_cohort1_trust_rho], one dimension at a time. The
held-out item screen is retrospective, against WVS-7, our only human source; we never call it "transport". Neither
extra claim (transport, pre-piloting) is earned.

## 2. What holds, what fails, what is untested

**Holds.**

- Trust ordering. Cohort-1 adapters against GPS: 0.744 (0.500 to 0.865) [B2_cohort1_trust_rho]. Bank-2 adapters:
  0.803 (0.615 to 0.876) [B2_bank2_trust_rho].
- Direction. Wrong-signed own-bit effects: 0 of 7 surfaces [FX_adapter64_own_effects_wrong_signed]. This is an
  average over the other sign bits, not a statement about every pair of profiles.
- Held-out screen, retrospective. A (mean signed Spearman against GPS over the selected items) is 0.061 (-0.007 to
  0.126) [SCR_A_primary], permutation p 0.0097 [SCR_p_perm]. The null is rejected and the signal is weak.
- Against a prompt naming the country, on trust: adapters minus persona 0.716 (0.191 to 1.154) [PX_D_cohort1_trust].
  A prompt stating the six signs does as well as the adapters, 0.773 (0.584 to 0.844) [PX_signprompt_trust_rho], so
  the contrast is declared signs against a country name, not weights against prompts.

**Fails.**

- Other dimensions. Cohort-1 adapter-GPS on patience Q43 is -0.019 (-0.414 to 0.452) [B2_cohort1_patience:Q43_rho].
- Own-surface dominance (V5), where a sign bit's largest effect lands on its own surface: 2 of 6 bits
  [FX_adapter64_V5_hits], short of the registered rule.
- Comparators. Adapter minus a careful reader on shared items: -0.002 (-0.064 to 0.061) [CMP_jev_D_common]. We say
  "does not distinguish".
- Held-out risk taking is 0.158 (0.015 to 0.290) [PD_adapter_primary_risktaking_A] under the registered rule, and
  -0.026 to 0.326 after adjustment across dimensions [PD_adapter_primary_risktaking_A_bonf].
- Human agreement (descriptive). Trust, adapters against the survey composite: 0.295 (-0.044 to 0.547)
  [C9_a_adapter_human_trust_spearman_rho]; GPS against the same composite: 0.351 (0.088 to 0.564)
  [C9_a_human_gps_trust_spearman_rho]. All seven adapter-human intervals include 0.
- Distance to survey answer shares (descriptive; mean total variation distance, TVD, lower is closer): base model
  0.470 [C9_TVD_base_mean_tvd_country_equal], adapters 0.515 [C9_TVD_adapter_mean_tvd_country_equal], country-named
  persona 0.365 [C9_TVD_persona_mean_tvd_country_equal]. This differs from rank agreement.

**Untested.** Pre-piloting. The adapter-plus-persona TVD cell and held-out label recovery on 42 adapters (C9-4): no
GPU run happened, so there are no rows. A weights-level mechanism analysis (W3) has no accepted result; it belongs to
SCA3, not Paper B.

## 3. One methodological insight: not yet

The verifier ruled both candidate insights WEAK. What we learned:

- Profile grouping. Countries sharing a profile are not detectably closer in survey composites than random groups:
  trust share 0.384 [C9_c_human_trust_between_share_multi_member], one-sided p 0.551
  [C9_c_human_trust_permutation_p_one_sided_multi_member]. The design detects only a true between-share near 0.568
  [C9_c_design_12_group_multi_member_design_interpolated_true_between_share_at_80_power]. That is a power limit. It
  is not evidence that humans lack profile structure, and it does not show the anchor is the bottleneck.
- Cross-talk between sign bits. A prediction from all main effects keeps the GPS order on trust, 0.834
  [C9_W1_trust_spearman_full_vs_gps], and loses it on risk taking, 0.104 [C9_W1_risktaking_spearman_full_vs_gps]. The
  cross term's covariance share is 0.287 on trust [C9_W1_trust_cross_cov_share] against 0.727
  [C9_W1_negrecip_cross_cov_share] to 0.985 [C9_W1_patience_Q43_cross_cov_share] elsewhere. This is a behavioral
  decomposition of a linear model, not a neural mechanism. The link to failure rests on trust alone, and a bit-only
  predictor orders countries like GPS by construction.

## 4. How to explore the workbench

Private Space: https://huggingface.co/spaces/Bonorinoa/sca2-workbench. Access is pending: Augusto must create the
Hugging Face organisation, invite you and move the Space, so the address may change. It holds saved scores and GPS
signs only: no survey data, no weights, no live model. It is descriptive, not Paper B evidence. Its landing footer
still calls Paper B an extension of the preprint; that wording is out of date.

1. Open the Space and click "SCA2 story" in the top bar. Section 1 maps signs to profiles to countries.
2. Section 2, "Country scores, by route": pick cohort-1, bank-2, sign prompt or persona. A country-by-surface
   heatmap. Bank-2 and sign-prompt scores are constant inside a profile by construction.
3. Section 3, "Average direction, and behavioral cross-talk": a sign-bit by surface matrix, own-bit cells outlined.
   Off-own cells are cross-talk. Hover for the effect and claim ids.
4. Section 4: each featured country pair opens a saved forward pass in the tensor viewer (readout ladder,
   token-by-layer matrix, 3D object), base model to one adapter. There is no two-country difference view.

## 5. What we ask of you

- Sign-off on Amendments C7, C7.1, C8 and C9 of the claim lock (C9 is descriptive and adds no claim).
- Comments on the framing: instrument evaluation, "retrospective" for the screen, "does not distinguish" for the
  comparators, and whether the human-agreement and TVD rows go in the main text or the supplement.

## 6. What happens next

Targets are proposals for Augusto; the final list is `STATUS.md`, "Open after the checkpoint".

- 2026-10-23: C9 section in the manuscript, after sign-off; novelty audit on LM evaluation for social-science
  measurement.
- Prompt-route capture queue (stopped early), weights-versus-prompt analysis and W3 repeat: dates to be reset by the
  PM. SCA3, not Paper B.
- 2026-10-26: live adapter chat card, with a cost and data-rights check.
- Early November: Paper C candidate (magnitude-graded compiler), after the sign-profile evaluation concludes.
- Augusto only: author list and order, OSF registration, anonymous mirror, ethics, funding and AI-use statements, SMR
  preprint policy, Overleaf page count, review of human-derived files in git history.
