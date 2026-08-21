# REVISION CHECKLIST — position_paper_sca2 (Positioning A: protocol paper with honest results)

Status: DRAFT for discussion — 2026-08-20
Locked positioning (Augusto, 2026-08-20): **A** — keep five-link spine, replace shells with dissociation results, noise floor + weights-vs-prompt as headline; target PNAS Nexus this cycle.
Source of all new numbers: `Downloads/SCA2_phase2_report.pdf` (2026-08-20 internal, audited after 19 Aug draft); replication in `analysis/phase2/01..14 *.py` + `analysis/phase2/outputs/`.

## Task map (dependency order)

| # | Task | Effort | Depends on | Evidence verified in repo |
|---|------|--------|-----------|---------------------------|
| R1 | Verify status/title/venue of 14 candidate references (web + primary sources; preprints flagged as such) | S | — | landscape ref `sca-methodology-paper-literature-landscape.md`; report refs [1]–[8] |
| R2 | Add refs to `.tex` + cite in text where each belongs (see mapping below) | M | R1 | — |
| R3 | Reference-preservation gate: all 8 original refs still present after pass | S | R2 | grep |
| V1 | Re-derive report headline numbers from `analysis/phase2/outputs/` CSVs (Table 1 TVD/JSD/entropy/std/topmatch; Table 2 bridge ρ; Table 3 dev ρ + partials; held-out 0.89–0.99; temp 0.47→0.33; CF ST ranks; 3.7× compression) | M | — | `analysis/phase2/outputs/` |
| N1 | Rewrite §7 "Planned reporting structure" → results section: filled main table (adapter/base/persona/noise × TVD/bridge/dev), noise-floor discussion, CF ST vs PCA subsection, dissociation as headline | L | V1 | outputs CSVs + figures |
| N2 | Update §5 Table 2 five rejection points with verdicts: transmission ✓, encoding ✓, relevance ⏳(placebo pending), external transport ⚠️ partitioned (TVD fail / trust bridge pass), robustness ⏳/partial | M | V1 | — |
| N3 | Update cover status paragraph + abstract: predeclared shells → 16-country results + honest negative + pending placebo; keep "not a public preregistration" for pending links | M | N1, N2 | — |
| N4 | Appendices: A retitle/reframe (pilot superseded, kept as fixed-policy-proximity diagnostic); B add note that deterministic-sign is now default (commit `04f9e2a`); C verify vs current training config (526 pairs / 658 bank, β=0.1, r=16/α=32) | S | V1 | `DPO_train_test/`, git log |
| N5 | Operator diagnostics subsection: temperature scaling 0.47→0.33 (shape fix, location structural), soft-DPO/|z|<0.1 as planned ablation, extended-prompt bank as planned lever, explicit "what we will not do" (KL-to-WVS / moment matching = contamination) | M | N1 | report §5–6 |
| F1 | 2–3 code-generated figures from `14 report figures.py` outputs adapted to paper style (TVD heatmap/violin; bridge bars; dev scatter) | M | V1 | `analysis/phase2/outputs/` |
| G1 | Number-preservation gate: grep every original figure + every new headline number after all passes | S | N1–N5, F1 | — |
| C1 | Compile in temp dir ×2 (0 errors, 0 undefined refs), md5-verify copy, `git status` shows M, commit with message file; user pushes (403 on this Mac) | M | G1 | — |

## Reference mapping (14 additions)

Must-cites (competitors/neighbors — §2 positioning table + §1): Suh et al. 2025 SubPOP (ACL); Cao et al. 2025 (NAACL); Krsteski et al. 2026 (ACL); Abels et al. 2026 (VALE); Pfeifer & Dalloul 2026 (SSRN 6703798 — mode collapse, same base model, §1/§5/§N5); Boelaert et al. 2025 (SMR, "Machine Bias"); Tao et al. 2024 (PNAS Nexus — venue precedent + cultural alignment, §2).
Formal apparatus: LMR 2026 (ARE — conditional probability fn, §3.2/§4); Dell & Rambachan 2026 (NBER SI lectures — construct validity as partial ID, §5); Muthukrishna et al. 2020 (CF ST, §5.3/results); Inglehart & Welzel 2005 (§2/§6.2 anchors); Sharifnassab et al. 2024 SPO (soft-DPO discussion, §5 or appendix).
Own lane: SCA1 (Capra, Gonzalez-Bonorino & Pantoja, REE forthcoming — §1); cvprofiles v8 companion WP (§2/§6.3, one citation only).

## Original figures that must survive (grep gate, paper as it stands)

Pilot appendix: 0.4882 / 0.5211 / 0.6377 / 0.1495 / [0.0964, 0.2152] / 0.3888 / 0.3958 / 0.5258. Training config Table 5: r=16, α=32, dropout 0.05, β=0.1, lr 1e-4, warmup 0.03, 1 epoch, eff. batch 16, 2,875 train split seed 42. Equations (1)–(6). GPS six dimensions. 35-item pilot map, 30 mapped + 5 demographics.

## New headline numbers to introduce (all from report, verified in V1)

TVD: adapter 0.469 / base 0.443 / persona 0.375 / noise 0.338 (JSD 0.279/0.249/0.188/0.145; entropy err −0.737/−0.540/−0.438/0.568; std err −0.647/−0.535/−0.449/0.845; topmatch 0.452/0.452/0.479/0.331). Bridge ρ (adapter/human/persona): trust 0.78/0.41/0.06, patience 0.42/0.32/0.60, risktaking 0.57/−0.08/−0.11, posrecip 0.48/−0.00/0.01, negrecip 0.06/0.42/0.34, altruism 0.24/0.03/−0.23. Dev ρ: trust +0.13 (partial +0.50), patience +0.29 (+0.46), persona overshoot trust +0.73. Held-out pair accuracy 0.89–0.99 (n=132). Temperature 0.47→0.33 TVD. CF ST median own-country rank 18.5/42 (chance 21.5), 11/16 nearest CAN, BRA ranks 9/2. Sign profiles 35 from 76 countries; twin partial ρ=−0.09. Family–outgroup gradient compressed 3.7× (16/16). Anti-leakage price ≈0.09 TVD. 526 training pairs from 658 bank.

## Open questions (answers recorded in RESOLVED below)

1. **Title** — keep current ("Synthetic Cultural Agents from Aggregate Anchors: A Falsifiable Protocol for Constructing Population-Level Choice Policies") or adjust to reflect results?
2. **Non-LLM aggregate baseline** — exact estimator. Proposal: GPS-moment parametric predictor (z→option distribution per item, parameters fixed a priori from sign rule + declared concentration), never fit to WVS. Compute this cycle or next?
3. **Discussion scope** — how much of report §5–7 (interpretation, journal landscape) enters the paper? Proposal: dissociation + dispersion-bound + "what we cannot claim" paragraph in; venue ladder stays internal.
4. **Persona baseline** — keep country-named persona in every table (report recommendation)? Proposal: yes.
5. **Imprint dimensions** — risktaking/posrecip/altruism "imprint" interpretation: in Results or exploratory appendix?
6. **4-country subset** (Ksennia's extended-prompt run) — which countries? Proposal: one confirmatory trust/patience pair, one exploratory, one NLD-like conflict, one sign-twin.

## RESOLVED (Augusto, 2026-08-20 — checklist locked)

1. **Title** — Keep "Synthetic Cultural Agents from Aggregate Anchors". Change subtitle; delete the "Population-level" footnote. Proposal (recommended): "A Falsifiable Protocol for Constructing Aggregate-Anchored Choice Policies". Alternates: "Where Preference Direction Lives: Weights, Prompts, and the Noise Floor" (results-flavored), "A Weights-Only Protocol for Aggregate-Anchored Choice Policies with an Honest Boundary". "population-level" survives only in the abstract/body where it is defined once.
2. **Non-LLM aggregate baseline** — Adopt the maximum-entropy moment-constrained construction (equivalently iterative proportional fitting / raking from a uniform seed; Deming & Stephan 1940; Jaynes 1957; Golan, Judge & Miller 1996). Objective: same information budget as adapters (declared GPS anchors; no WVS, no microdata, no LLM); isolates location from concentration given the report's flatness insight. Add a second degenerate arm: the sign-follower (all mass on the anchor-sign option — the adapters' training signal realized mechanically). Predeclare the z→item-moment mapping (μ = grid midpoint + b·z, fixed b) before outcome inspection. Not standardized in the LLM-survey literature (SubPOP/Krsteski/Cao use real data or prompts) — we name it as our declared benchmark; classically grounded. **Run this cycle (numpy only, no GPU).**
3. **Discussion scope** — Venue ladder and lab-internal material excluded. "Next steps" section becomes a predeclared plan of experiments we will actually run (extended-prompt subset + placebo + non-LLM baseline + 2×2 persona arm). **PNAS Nexus preprint policy VERIFIED** (oup.com/pnasnexus/pages/general-instructions, "Preprint and self-archiving policy"): "Authors retain the right to make an Author's Original Version (preprint) available through various channels, and this does not prevent submission to the journal." arXiv/SSRN-first is permitted; on acceptance, update the preprint with the published DOI. No embargo; Accepted Manuscript posted ~1 week after acceptance; concurrent-submission rule only bars simultaneous submission to another journal. Data/code must be in a public repository on publication (GitHub repo satisfies). APC applies (~$3.6k research report) — check ASU OUP Read & Publish coverage at submission. AI use must be disclosed in Methods (LLM writing assistance + pipeline LLMs). **PNAS Nexus participates in Registered Reports** — option for the next-wave protocol; target article type: Research Report.
4. **Persona baseline** — Confirmed: keep the country-named persona in every table (it is the mainstream method we challenge and the anti-leakage price meter). **New arm (later, after paper update)**: adapter×persona 2×2 — run each country-adapter under the same persona prompt (weights: base/adapter × prompt: unconditioned/persona) to quantify complementarity. Cheap (~1–2 T4-hr for 16 countries). Until it runs, Results must phrase the dissociation as "prompting **on the base** fails the trust bridge" — not "prompting fails" — so the 2×2 cannot contradict a written claim.
5. **Imprint dimensions** — Poor WVS instrument mapping is a finding, not a bug: address in Results with measurement-invariance context (Davidov et al. 2014 ARE-SR; Steenkamp & Baumgartner 1998 JMR; MTMM Campbell & Fiske 1959; our own gender-gap-alignment logic). **New application claim (yes, with boundaries)**: adapters as a new-instrument alignment probe — score a new survey through the adapter's construct bridge, calibrate against the human-layer ρ and noise/persona baselines; aligned ≈ ρ near human layer; imprint ≈ ρ ≫ human layer where humans show ≈0; missing ≈ ρ≈0 where human layer is strong. Boundaries: country-level only; direction/ordering only; valid only on trust/patience (verified proxies); predictive-criterion screening, not construct recovery. Upgrades the AmericasBarometer OOS from instrument redundancy to a probe demonstration (USA/MEX pilot possible now).
6. **Training strategy** — All further training (extended-prompt subset, soft DPO) belongs to Ksennia; our own soft-DPO/other runs only after the position paper update. Compute: 270 Colab units available (agonz439@asu.edu) — ample (subset ≈ 8 units, 2×2 ≈ 2 units, placebo ≈ 3 units, soft-DPO ablation cheap).

## R1 verification log (2026-08-20, all web-verified)

| Ref | Verified record | Notes |
|---|---|---|
| Dalloul & Pfeifer 2026 | SSRN 6703798, "Can LLMs Mimic Household Surveys?: From Representative Agents to Population Distributions", July 21 2026 | **AUTHOR ORDER: Dalloul first** (report/landscape had it reversed). Uses SCE + Llama-3.1-8B-Instruct (same base model). Replication: Harvard Dataverse 10.7910/DVN/CRIRVJ |
| Suh et al. 2025 | ACL 2025 Long Main, 2025.acl-long.1028; arXiv 2502.16761 | SubPOP: 3,362 questions, 70K pairs, up to 46% gap reduction |
| Cao et al. 2025 | NAACL 2025 Long, 2025.naacl-long.162, pp. 3141–3154; arXiv 2502.07068 | Full author list: Cao, Liu, Arora, Augenstein, Röttger, Hershcovich. Fine-tunes on real country-level survey results |
| Krsteski et al. 2026 | ACL 2026 Main, 2026.acl-long.498; arXiv 2510.11408 | Confirm full author list from ACL page at bib time |
| Abels et al. 2026 | arXiv 2605.16193 (May 2026); under review at VALE 2026 (workshop @ IJCAI-ECAI 2026) | Abels, Fernández Domingos, Shah, Lenaerts. Method = mean-preserving exponential tilting q ∝ p^(1/T)exp(βr) — cite as arXiv; direct link to our temperature diagnostic |
| Boelaert et al. 2025 | SMR, DOI 10.1177/00491241251330582 | Full title: "Machine Bias. How Do Generative Language Models Answer Opinion Polls?"; authors Boelaert, Coavoux, Ollion, Petev, Präg |
| Tao et al. 2024 | PNAS Nexus 3(9):pgae346 | 794 citations; Tao, Viberg, Baker, Kizilcec — venue precedent |
| LMR 2026 | Annual Review of Economics 18:283–316; DOI 10.1146/annurev-economics-120925-105620 | NBER WP 33344 (Jan 2025, rev. Dec 2025) |
| Dell & Rambachan 2026 | NBER SI 2026 Methods Lecture, "Estimation and Inference with AI-Generated Data", 2026-07-30 | Slides dell3/dell4/dell6.pdf; cite as methods lecture w/ slide URLs |
| Sharifnassab et al. 2024 | arXiv:2405.00747 (v4), SPO | Confirmed |
| Muthukrishna et al. 2020 | Psychol. Science 31(6):678–701 | From audited report refs — carry over |
| Inglehart & Welzel 2005 | Cambridge UP (book) | Carry over |
| SCA1 | Capra, Gonzalez-Bonorino & Pantoja, REE forthcoming | **Missing from paper refs — add** |
| cvprofiles v8 | Gonzalez-Bonorino, Biriukova & Capra, WP (EconLLM Lab) | Missing — add; one citation only |

→ 14 additions; final count 22 refs. R1 ✅, R2 ready once .tex edits start.

## How-to-proceed (empirical track, contingent on this checklist)

- **Now (paper track)**: R1+R2 references pass, then V1 → N1..N5 → F1 → G1 → C1. No GPU.
- **This week (empirical, parallel)**: Ksennia — extended-prompt 4-country subset (predeclared TVD margin ≈0.05); permutation placebo on same subset; soft-DPO/|z|<0.1 prune ablation cheap in parallel. Non-LLM baseline per Q2.
- **Deferred**: OOS AmericasBarometer (USA/MEX only — instrument redundancy, not power), economic games scenarios, new nomological tests, new cvprofiles network — all behind the extended-prompt decision.
