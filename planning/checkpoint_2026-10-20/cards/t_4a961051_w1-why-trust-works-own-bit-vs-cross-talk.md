# W1 Why trust works: own-bit vs cross-talk decomposition + bank composition (CPU)

Card `t_4a961051`, board sca2-paper-b, assignee `sca`, status at export: done
Created 2026-10-19 16:36 MST. Exported 2026-10-19 by the CP assembly card as a dated record, not status.

## Body

FIRST read /Users/bonorinoa/.hermes/cache/scratch/c9_explore/common.md (shared rules, deadline 22:00 MST).

Question: why do the adapters order the 42 countries like GPS on trust (0.744) but not on the other five dimensions? The PM's exploratory run ruled out two explanations: (1) sign balance — a perfect sign-copier reaches 0.82-0.87 on every dimension; (2) item count — a single trust item already gives median 0.69. Lead hypothesis: cross-talk. In the bank-2 64-cell factorial every own-bit effect has the right sign (direction holds), but other bits move surfaces as much or more (risk bit on altruism 0.983 vs altruism's own 0.242; risk bit on negrecip -0.668 vs own 0.625), which can scramble the country ORDER. Test it.

Inputs: factorial outputs `planning/sprint_2026-10-11/paper-b-tier1/results/factorial/` (+ `paper_b/factorial_effects.py`, `analyze_factorial.py`), `paper_b_inputs/adapter_strict_v1.csv`, `cohort1_strict.csv`, `signprompt_strict_raw.csv`, GPS z (`analyze_surface.load_gps_z`), banks `synthetic_generation/outputs/gps_sign_relabel_all/` and `gps_sign_relabel_bank2/`.

Write `paper_b/w1_crosstalk.py`, `paper_b/test_w1_crosstalk.py`, outputs `planning/sprint_2026-10-11/paper-b-tier1/results/c9/w1_why_trust.{json,md}`.
a. The 6-bit × 7-surface main-effect matrix for the adapter and sign-prompt routes; assert own-bit betas equal NUMBERS_TABLE `FX_*_own_beta`.
b. For each surface s and each of the 42 countries: full prediction = sum_b beta[b,s]·bit_b(country); own-only = beta[s,s]·bit_s; cross-only = full - own. Report Spearman(full, observed bank-2 composite) [does the main-effects model explain the surface?], Spearman with GPS z of full / own-only / cross-only, and the cross-only share of variance in the full prediction. Then: across the 7 surfaces, does the cross-talk share rank the surfaces like their adapter-GPS failure? (descriptive, n=7; also show the 7 pairs). Repeat with cohort-1 composites as the observed surface (bank-2 betas as the model). Include interactions only if main effects explain < 80% of the 64-cell variance on a surface; say which.
c. Same decomposition for the sign-prompt route (which inverts risk).
d. Bank composition, aggregates only: pairs per dimension in bank 1 and bank 2; whether each pair's label depends on one dimension's sign; mean prompt/response length per dimension; share of pairs whose text contains the dimension's keyword family.
e. A paragraph: which explanation survives, which is ruled out, and the single most informative mechanistic follow-up for the workbench (which pair of one-bit-apart countries and which items).

## Runs

- run 51 sca: done/completed  W1 cross-talk decomposition complete (CPU). Cross-talk survives and explains why adapters order like GPS only on trust; sign-copier (own-only) orders on all 7. Deliverables: w1_crosstalk.py + test (6 new tests; full suite 558 pass), outputs w1_why_trust.{json,md}, reading file (e). All descriptive / NOT PREREGISTERED; NUMBERS_TABLE pins (14) verified; no secrets/human data leaked.

## Comments

### sca 2026-10-19 16:45

Finished W1 cross-talk (CPU). Deliverables (local-only):
- paper_b/w1_crosstalk.py (460 lines) + test_w1_crosstalk.py (90 lines) — 6 new tests pass, 558 full-suite pass
- planning/sprint_2026-10-11/paper-b-tier1/results/c9/w1_why_trust.{json,md} (descriptive, NOT PREREGISTERED)
- same dir: w1_reading.txt (paragraph (e))

What ran (citations in .md point to these):
- load_routes() asserts own-bit betas == NUMBERS_TABLE FX_*_own_beta (14 pins, 0 mismatches)
- adapter + signprompt routes: 6x7 main-effect matrix reproduced; bank2-composite (full) rho vs GPS 0.835 (trust) -> 0.104 (risktaking); cohort1-composite with bank2 betas 0.744 (trust) -> -0.028 (negrecip)
- own-bit-only predictions stay GPS-aligned on all 7 surfaces (rho abs 0.82-0.87); full predictions keep it only on trust (rho 0.834 / 0.811 signprompt) — cross share 0.147 / 0.008 respectively; other surfaces cross share 0.83 to 1.05 => ordering collapses. Spearman(cross-share, failure) 0.821 (bank2, n=7) vs 0.286 (cohort1) — one surface vs six, not graded.
- interactions: needed on 4 adapter surfaces (<80% main-eff share); lift to observed composite but do NOT rescue GPS ordering (main+2way GPS rho 0.331 risktaking, -0.066 patience:Q43, 0.287 posrecip, 0.210 negrecip).
- bank composition: 658 pairs/dim each; 27,636 label rows/bank, 0 mismatches vs own-dimension sign (label depends on one dimension); keyword-family shares show heavy cross-family overlap (e.g. trust pairs contain patience 0.76/0.75, altruism 0.56/0.65) and bank1 marker gaps show trust pairs already separate A/B on posrecip (0.47) and risktaking (0.41) — text co-loading is present for every dimension, so it doesn't distinguish trust. Bank2 has no marker scores.
- follow-up (a priori rule): risktaking is the leakiest bit; 27 one-bit-apart cohort pairs; JOR vs KAZ (min |z| 0.125) is the cleanest; items Q101/Q99/Q103 (altruism) and Q179/Q177 (negrecip) carry the largest leaked effect.

What is uncertain / needs human decision before calling anything banked:
- (e) paragraph is descriptive, not a claim-lock; the rank correlation relies on 7 surfaces with trust as the single low-failure outlier.
- Cohort-1 composites as "observed" against bank-2 betas reproduce the failure pattern but shift absolute rhos (cohort1 risktaking 0.435 vs bank2 0.210); mechanism conclusion is the same (cross-talk dominates) but magnitude isn't stable across banks.
- The workbench follow-up pair selection is rule-fixed, not outcome-selected, but JOR/KAZ's margin (|z| 0.125) is near the 0.10 near-zero cutoff; replication with IDN vs IRN (|z| 0.103) is the stated caveat.
- Nothing in this run modifies NUMBERS_TABLE, pins, freeze.json, preregistrations, or tracked artifacts; no country-level human means were printed/logged/copied; HF_TOKEN not exposed (tests run with it blanked, no upload).
- Next: apply (e) mechanism (pair + top-5 leaked items) to the workbench adapter-brain-activation stream; new card if needed, do not extend this one.

