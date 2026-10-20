# C9-1 Human-agreement rows on 42 countries + sign-mate permutation test (CPU)

Card `t_c13b7536`, board sca2-paper-b, assignee `sca`, status at export: done
Created 2026-10-19 16:36 MST. Exported 2026-10-19 by the CP assembly card as a dated record, not status.

## Body

FIRST read /Users/bonorinoa/.hermes/cache/scratch/c9_explore/common.md (shared rules, paths, deadline 22:00 MST).

Context: Amendment C9 brings the preprint's human-agreement results onto the 42-country Paper B cohort. Augusto decided (2026-10-19): cohort-1 country adapters carry the rows; bank-2 profile adapters (mapped to countries) are a robustness column; all rows DESCRIPTIVE. The PM's exploratory run found that the human between-profile share on the 12 multi-member sign profiles (28 countries) is at chance on every surface (permutation p 0.05-0.75) while adapters sit at ~1.00. Your job is to compute this properly and bank-ready.

Write: `paper_b/c9_human_agreement.py`, `paper_b/test_c9_human_agreement.py`, outputs `planning/sprint_2026-10-11/paper-b-tier1/results/c9/c9_human_agreement.{json,csv}` (long format: claim_id-style key, statistic, value, ci_low, ci_high, n, interval type, surface_label).

Compute, for the 7 surfaces in `analyze_phase.SURFACES`:
a. Cohort-1 three columns (adapter-GPS, adapter-human, human-GPS). Assert they reproduce `paper-b-20261011/analysis/three_column_table.csv` exactly (test).
b. Bank-2 adapter-human: bank-2 profile adapters mapped to countries (`paper_b_inputs/adapter_strict_v1.csv`, profile per country from `analyze_surface.sign_profiles`), same estimator and profile-block interval. Also bank-2 adapter-GPS, and assert it matches NUMBERS_TABLE rows `B2_bank2_*_rho`.
c. Between-profile share (adapter and human; all-country and multi-member) and a permutation test of the multi-member share: shuffle profile labels among the multi-member countries preserving group sizes, 10,000 permutations, seed 20261019; report observed, chance mean, one-sided p. Also a power simulation: smallest true between-share excess detectable at 80% power with these 12 groups.
d. Sign-mate agreement: Spearman of each multi-member country's human composite with the mean of its sign-mates (leave-one-out), n=28, profile-block interval. Label it "sign-mate agreement, NOT a ceiling".
e. GPS-side sign-copier references per dimension: Spearman(sign(z), z) over 42; leave-one-out profile-mean of z vs z (n=28); adapter-GPS divided by the own-sign reference.
f. Preprint comparison items on 42: Q57 human-GPS alone (preprint reported 0.15 on 16), patience human-GPS Q43 and Q50, risk with and without JOR (complete case n=41 is the human side).
Finish with a plain-language reading of (c)-(e): what do they say about where the limit on human prediction sits (anchor vs model)?

## Runs

- run 49 sca: done/completed  C9-1 completed: paper_b/c9_human_agreement.py + test + banked JSON/CSV (167 rows, parts a-f + power); 12 logic tests pass; full paper_b 564 pass; cohort-1 3-col reproduced exactly; B2 adapter-GPS reproduced; permutation p's 0.06-0.74 human / 0.00 adapter; sign-mate agreement non-significant; GPS own-sign 0.82-0.87; power needs true share ~0.57 for 80%. Reading: limit sits at the anchor (profile carries little observable human info, not primarily a model failure), but 12 groups is underpowered.

## Comments

### sca 2026-10-19 16:44

C9-1 report. All rows DESCRIPTIVE / NOT PREREGISTERED.
(a) Files (uncommitted): paper_b/c9_human_agreement.py, paper_b/test_c9_human_agreement.py, planning/sprint_2026-10-11/paper-b-tier1/results/c9/c9_human_agreement.{json,csv} (167 long-format rows; parts a b c d e f plus power).
(b) Commands: tests written first (collection failed, red), then module. `pytest paper_b/test_c9_human_agreement.py` = 12 passed. Full `pytest paper_b` with the other cards' in-progress files ignored (test_c9_tvd.py fails collection, test_w1_crosstalk.py) = 564 passed. Generated the outputs with `.venv/bin/python paper_b/c9_human_agreement.py`.
(c) Key numbers (source: results/c9/c9_human_agreement.csv). Cohort-1 three columns reproduce banked three_column_table.csv to 1e-12 on all 21 rows (test). Bank-2 adapter-GPS reproduces NUMBERS_TABLE B2_bank2_*_rho (value and interval, 7 of 7; test). Bank-2 adapter-human: trust 0.34 [-0.03,0.59], posrecip 0.37 [0.01,0.64], patience Q43 0.22, Q50 0.04, risk 0.21 (n=41), negrecip 0.17, altruism 0.09 (profile-block). Cohort-1 adapter-human: trust 0.30, posrecip 0.32, negrecip 0.39, others below 0.2 (all intervals include 0 except none).
 Between-profile share, multi-member (28 countries, 12 profiles; chance mean about 0.41): human 0.38 (p 0.55) trust, 0.32 (0.74) Q43, 0.50 (0.25) Q50, 0.51 (0.22) risk (n=26), 0.53 (0.17) posrecip, 0.63 (0.059) negrecip, 0.43 (0.42) altruism. Adapters 0.96-1.00, p<0.0001 on every surface. Permutation: 10,000, seed 20261019.
 Power (500 sims x 1000 perms per grid point): 80% power needs true between-share about 0.57 (grid 0.60), i.e. an expected sample-share excess of about 0.32 over chance. The design can detect only a large effect; the human shares (0.32-0.63) sit inside the undetectable zone, so "at chance" means "not distinguishable from chance with 12 groups".
 Sign-mate agreement, NOT a ceiling (n=28; risk n=26): human vs LOO mates -0.12 trust, -0.35 Q43, -0.02 Q50, 0.11 risk, 0.09 posrecip, 0.33 negrecip, -0.12 altruism; every interval includes 0. Adapter-human on the same sample is 0.33 trust, 0.36 Q43, 0.47 negrecip (also all intervals include 0 except none).
 GPS-side: own-sign reference Spearman(sign z, z) is 0.82-0.87 on all dimensions. Cohort-1 adapter-GPS / own-sign: trust 0.86, posrecip 0.56, risk 0.50, altruism 0.47, Q50 0.22, Q43 -0.02, negrecip -0.03. Bank-2: trust 0.93, posrecip 0.42, altruism 0.42, negrecip 0.28, risk 0.24. LOO profile-mean z vs z (n=28): trust 0.88, negrecip 0.82, risk 0.71, posrecip 0.63, altruism 0.59, patience 0.48.
 Preprint items on 42: Q57 human-GPS 0.155 [-0.18,0.48] (preprint 0.15 on 16); patience human-GPS Q43 -0.53 [-0.74,-0.27], Q50 0.39 [0.10,0.63]; risk human-GPS -0.06 (complete case n=41; JOR is the missing country); adapter-GPS risk with JOR 0.435, without JOR 0.437 (matches banked risk_jor_sensitivity.csv).
(d) Uncertain / notes: bank-2 between share is 1.0 by construction so not tabulated. Power model assumes Gaussian equal-variance group effects (documented in JSON). Sign-mate bootstrap holds LOO mate means fixed and resamples profile clusters. Ratios are of point values, no interval. test_c9_tvd.py (another card) currently breaks `pytest paper_b` collection; not mine. Nothing committed.
(e) Reading: Adapters reproduce the GPS sign structure almost perfectly (between share about 1) and, for trust, reach about 0.86-0.93 of what a perfect sign copier could (own-sign reference 0.86). Humans in countries that share a sign profile do not resemble each other more than random country groupings would (shares 0.32-0.63 vs chance 0.41, none significant; negrecip p=0.059), and a country's human value does not track its sign-mates (all intervals include 0). With 12 groups the test only detects a true share of about 0.57+, so this is weak evidence of no structure, not proof. Together this places the limit on predicting humans at the anchor: the 6-sign profile carries little human-observable information on these surfaces, so adapter-human values of 0.1-0.4 are about as high as a profile-level copier could go. It is not primarily a model limit, though the GPS-side gap (risk, altruism, patience, negrecip, 0.0-0.5 of the own-sign reference) shows the model also does not fully recover the sign structure on those dimensions.

