# Paper B manuscript outline (SMR)

Card T10, writer profile, 2026-10-18. Route: anthropic / claude-opus-5-5 (ASU seat).

Claim source: `planning/TWO_PAPER_CLAIM_LOCK.md`, "Amendment C7 2026-10-18", with
`planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv` (sha256 90f0f467...0ec1f, 220 rows). Wording follows
`C7_CLAIM_LOCK_AMENDMENT_DRAFT.md` sections 1 to 8 as modified by the amendment (C5 strict reading: every surface-H
result is a retrospective screen and the word "transport" is never used for it; the general transport sentence stays
unwritten). Methods source: `paper_b/heldout/PREREGISTRATION.md` (sections 1 to 12), `results/TIER1_ANALYSIS_20261017.md`,
`VERIFICATION.md`, `review/PAPER_WORDING_CHECKLIST.md`.
Venue rubric: `~/.hermes/profiles/writer/venue-cards/sociological-methods-and-research.md` (confirmed 2026-10-18).

Every number in the .tex carries a `% claim:` comment with its claim_id, so a rebuilt table is a mechanical swap.
Design constants that are not statistics (223 items, 42 countries, 64 cells, 2,000 resamples, 10,000 draws, error df 42,
|t| >= 2, top 25 percent) are cited to the preregistration section that fixes them and are listed in the audit allowlist.

Target: about 9,000 to 10,000 words in the main text, six display items at most, everything else in the online supplement.
Abstract: at most 150 words, words only.

## Front matter

- Title (at most 20 words). Working: "Screening New Survey Items with Synthetic Respondents Trained on Aggregate Anchors:
  A Preregistered Held-Out Test". Claim ids: none.
- Title page (separate file, not in the anonymized manuscript): Augusto Gonzalez-Bonorino, Kseniia Biriukova, Monica Capra.
  `% TODO(Augusto): confirm author block and order`. Claim ids: none.
- Abstract. Problem (choosing items before fielding), instrument (synthetic respondents trained on declared aggregate
  signs), test (second scenario bank; preregistered screen of held-out WVS-7 items), findings in words (a real but weak
  screening signal, one dimension carries it, the dimensions are entangled, prompting with the same signs does worse on
  the factorial), boundary (retrospective criterion; pre-piloting untested; complement to fielding). Claim ids: none.

## 1. Introduction

Gap: survey designers screen candidate items for cross-national constructs with human pretests, which are slow; LLM
synthetic respondents are cheap but their validity as a screen is unknown. The instrument (Gonzalez-Bonorino et al. 2026,
third person). What this paper adds: a preregistered, blinded test on items no adapter was built for, a second-bank check,
and a factorial diagnostic. Numbered contributions (construction as instrument; preregistered screening protocol; the
diagnostic of entanglement), then a bridge paragraph into Section 2. Claim ids: none (results in words only).

## 2. Background: synthetic respondents as measurement instruments

Silicon sampling and its critics (Argyle et al.; Boelaert et al.; Lyman et al.; Kozlowski and Evans); LLMs as informative
observations beside humans (Broska et al.); cross-national composites and comparability (Bratt; Pokropek et al.); the
construct, measure and anchor distinction; the GPS as declared aggregate moments; DPO as regularized Bradley-Terry.
Closer names the empty cell (a held-out, preregistered screen of a trained synthetic-respondent instrument against a
human criterion) and defers checks to Results. Claim ids: none.

## 3. The instrument

3.1 From declared signs to a shared pair bank (sign rule, no country name in scenario text, no WVS wording).
3.2 DPO as a regularized Bradley-Terry pairwise choice model; one adapter per sign profile.
3.3 Two cohorts: 42 country adapters on bank 1; 64 sign-profile adapters on bank 2 (the full 2^6 design); the sign-profile
    prompt route as the same information through a different channel.
3.4 Readout: expected response code from option log-probabilities, no country name in any evaluation prompt.
Claim ids: none (design constants from the preregistration sections 1 to 3 and VERIFICATION.md V1, V2).

## 4. Evaluation design

4.1 Six surfaces and what each permits (Table 1: S1, S2, H, F, R, N).
4.2 Second-bank check (C3): profile-block bootstrap, 26 clusters, seed 20261011, 2,000 draws, percentile interval; rule fixed
    in advance (an imprint interval that includes 0 drops that dimension).
4.3 Held-out screen (preregistration sections 1 to 9): 223-item pool, probe (OLS on 64 units, error df 42), primary and
    secondary rules, criterion (survey-weighted WVS-7 country means), permutation null (10,000 draws, one-sided), country
    bootstrap (2,000), wave-6/7 ceiling, comparators, readout variants, sign-prompt arm, decision rules of section 9.
    Retrospective status stated here.
4.4 Blinding and amendments: freeze guard; Amendment 1 (12 wording repairs, first probe pass read before them, Q153 and Q157
    in its top quartile); Amendment 2 (the 12 leave both comparator routes; only Q82 affected).
4.5 Factorial analysis on the strict battery: main effects of six sign bits, OLS, error df 42; V5 rule; two scale-free views.
4.6 Retraining noise (one unseeded retrain) and the near-zero margin (two predeclared refits, size-matched controls).
Figure 1: pipeline and order of work (TikZ). Claim ids: none (design constants); hashes go to the supplement and the
availability statement (HASH_pool_worktree, HASH_pool_git_blob_lf, HASH_overrides, HASH_selection_amended_20261016).

## 5. Results

5.1 Second scenario bank (surface S2 against S1).
    B2_bank2_{trust,risktaking,posrecip,altruism}_rho; B2_cohort1_{trust,risktaking,posrecip,altruism}_rho;
    B2_bank2_{negrecip,patience:Q43,patience:Q50}_rho; B2_n_imprint_kept; B2_n_imprint_dropped;
    B2_bank_to_bank_{trust,altruism,posrecip,negrecip,risktaking}_pearson.
5.2 Retrospective held-out screen (surface H).
    SCR_A_primary; SCR_p_perm; SCR_null_mean; SCR_null_q95; SCR_share_a_pos; SCR_ceiling_mean; SCR_A_over_ceiling;
    SCR_one_third_ceiling; SCR_cells_not_fielded; SCR_secondary_A; SCR_secondary_p_perm; SCR_loco_min; SCR_loco_max;
    SCR_A_wave6; SCR_A_wave7 (exploratory).
    Per dimension: PD_adapter_primary_{trust,risktaking,posrecip,altruism}_A;
    PD_adapter_secondary_{trust,risktaking,posrecip,altruism}_A; PD_adapter_primary_{posrecip,risktaking}_share_pos.
    Exploratory multiplicity (not registered): PD_adapter_primary_{trust,risktaking,posrecip,altruism}_A_bonf;
    PD_adapter_secondary_{trust,risktaking,posrecip,altruism}_A_bonf (Bonferroni over four imprint dimensions, same
    2,000 draws). The primary-rule risk-taking interval does not survive the adjustment; say so plainly.
    Table 2: both checks per imprint dimension (C3 and the retrospective screen side by side, never averaged).
5.3 Comparators and the prompt route.
    CMP_face_valid_{D_common,D_own,A_imprint,common_same_dim_sign}; CMP_jev_{D_common,D_own,A_imprint,common_same_dim_sign};
    SP_A_primary; SP_p_perm; SP_D_own; SP_D_common; SP_overlap_with_adapter; SP_overlap_same_dim_sign.
    Table 3: screen and comparator contrasts.
5.4 Readout robustness.
    RO_heldout_{reverse,para_a,para_b}_ds_unchanged; RO_heldout_{reverse,para_a,para_b}_membership_agreement;
    RO_heldout_{reverse,para_a,para_b}_abs_t_corr.
5.5 The factorial: own effects, V5, cross-talk, route contrast.
    FX_adapter64_<surface>_own_beta and _own_t (seven surfaces); FX_adapter64_V5_hits; FX_adapter64_V5_p_binomial;
    FX_adapter64_rowwise_standardized_hits; FX_adapter64_columnwise_hits; FX_adapter64_own_effects_wrong_signed;
    FX_adapter64_risktaking_bit_on_{altruism,negrecip}; FX_adapter64_trust_bit_on_{patience_Q50,posrecip};
    FX_adapter64_surfaces_largest_mover_is_trust_bit; FX_adapter64_pc1_share; FX_adapter64_mean_abs_inter_surface_r;
    FX_signprompt64_V5_hits; FX_signprompt64_V5_p_binomial; FX_signprompt64_pc1_share;
    FX_signprompt64_mean_abs_inter_surface_r; FX_signprompt64_surfaces_largest_mover_is_trust_bit;
    FX_signprompt64_own_effects_wrong_signed; FX_signprompt64_{risktaking,patience_Q43,negrecip}_own_beta and _own_t;
    FX_signprompt64_trust_bit_on_{risktaking,patience_Q50}.
    Table 4: own effects by route; Table 5: route contrast (first direction, inter-surface correlation, trust-bit reach,
    wrong-signed own effects). Tables 4 and 5 may merge to stay within six display items.
5.6 Retraining noise and the near-zero margin (short; margin in a footnote, never a headline).
    RP_strict_max_abs_prob_diff; RP_strict_mean_abs_prob_diff; RP_strict_pearson_expected_codes;
    RP_heldout_max_abs_prob_diff; RP_heldout_mean_abs_prob_diff; RP_heldout_pearson_expected_codes;
    RP_max_abs_surface_diff_sd; NZ_COL_posrecip_refit_minus_control_sd; NZ_COL_posrecip_noise_floor_sd;
    NZ_GBR_trust_refit_minus_control_sd; NZ_GBR_max_abs_control_minus_baseline_sd; NZ_COL_max_abs_control_minus_baseline_sd;
    NZ_blockD_against_beyond_floor.

## 6. Discussion

One paragraph per contribution: the instrument (what the second bank shows and does not); the screen (real, weak, carried
by one dimension that the second-bank check does not support; posrecip points the wrong way; adapters indistinguishable from
a careful reader on few items); the diagnostic (entanglement on both routes; prompting more entangled with wrong-signed own
effects). Limits: retrospective criterion; pre-piloting is a prospective use this paper does not test; one base model;
signs carry no magnitudes; group-level unit of analysis. Complement to fielding and pretesting, never a replacement.
Claim ids: none (no statistic restated; pointers to Tables 2 to 5).

## 7. Conclusion

Short. What a researcher may do with the instrument now, and the test that would license more (a prospective human check of
probe-selected items, declared before the join). Claim ids: none.

## Backmatter (SMR order)

Preregistration statement (git tag prereg-heldout-2026-10-14; amendments 1 and 2; retrospective criterion;
`% TODO(Augusto): OSF registration`). Code, materials and data availability (anonymized link TODO; hashes
HASH_pool_worktree, HASH_pool_git_blob_lf, HASH_overrides, HASH_selection_amended_20261016; human microdata not
redistributed). Institutional review (public secondary data; TODO confirm). Conflicts and funding (lock: no funding, no
competing interest). Generative AI declaration (TODO confirm wording).

## Online supplement (separate PDF, later card)

Hash convention (F7), config sentence (F11), bank-2 archive gate gap, VM plumbing sentence, comparator per-dimension cells
(PD_face_valid_*, PD_jev_majority_*), full bank-to-bank table (Spearman), cohort-1 non-imprint surfaces, replicate
per-surface shifts (RP_surface_diff_sd_*), full near-zero block (NZ_*). The 26-cell factorial (FX26_*) is superseded and not
cited.

## Not claimed anywhere (draft amendment section 7)

Anchor transport for any single dimension; a prospective or independent human check; pre-piloting in any degree; that the
bank-2 trust value revises Paper A; that the screen is large; that adapters beat a careful reader or beat prompts on the
screen; separable sign dimensions; risk taking as "the" transported dimension; the 56 items as what the instrument selects
(without the churn sentence); weight reproduction or weight-space cosine; any near-zero reversal; per-dimension permutation
p values in place of registered intervals; the 64 cells as realized country profiles; human country-level values;
magnitudes or recovered GPS coordinates; patience and negative reciprocity as imprint or transport results.
