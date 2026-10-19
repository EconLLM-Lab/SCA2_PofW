# SCA2 Working-Paper Revision Plan

> **Record, not status.** Written 2026-09-08. Lines about what is done, blocked or next describe that date, not today. Current status: [STATUS.md](../../STATUS.md). Paper A revision plan, carried out before arXiv.

**Goal:** Revise the supplied SCA2 manuscript into a coherent, reproducible methods demonstration, preserving verified results while removing identification and utility claims unsupported by the design.

**Scope:** Discussion/plan only in this turn. No manuscript edits, deletions, commits, publication, or GPU inference. This proposed consolidated plan supersedes the reasoning in `replication/ARXIV_GATES.md` where explicitly corrected below; that file has not been edited. Current local HEAD: f0d1128 (packaging), ahead of origin; circulating PDFs and pre-existing author edits stay untouched.

**Architecture:** SCA-first construction → explicit input restrictions → empirical application → distinct encoding, anchor-transfer, and human-agreement readouts → limitations and prospective uses. Use one auditable analysis source per reported surface. Keep future construction experiments separate from reproduction of fitted policies.

**Sources inspected:** `Downloads/20-Minute Working Paper Slide Deck.md`; supplied `Downloads/SCA_2/main.md`; repo protocol, scorer, evaluation notebook, scripts and generated tables; external audit workspace, especially `external/results/` and `twobytwo_rescore/results/`; primary papers and venue instructions listed below.

## 1. Fact-check of the Gemini conversation

- The suggested presentation sequence is sound: context, problem, construction diagram, selected component details, evaluation design, evidence, unresolved questions. Negative findings remain limitations as well as useful diagnostics.
- Country-token omission removes explicit country names from the primary inference prompt. It does not remove pretrained knowledge, instruction tuning, generator priors, or optimization variation. The declared population input is distinct from the model's entire information content.
- Six aggregate coordinates do not identify a joint distribution of human preferences. Here their signs label a common pair bank. A fitted checkpoint specifies a computational response policy; its construction does not identify a human latent policy or distribution.
- One country adapter is a jointly trained profile-conditioned policy. Reporting trust performance is not equivalent to training a separate country-trust adapter. One Argentina output cannot establish a cross-country ranking or country-specific human validity.
- Construct validity is appropriate vocabulary for the research question, but divergence cannot isolate instrument non-equivalence from imperfect anchor measurement, ecological confounding, bank semantics, optimization failure, scoring choices, sampling, or temporal differences. A correlation network provides cumulative evidence, not a conclusive construct-sharing test.[10]
- The four main plotted series have the stated pairings: human–GPS, adapter–GPS, adapter–human, persona–human. The last pair is missing an important comparison for the headline: persona–GPS must be available in a table or companion panel.
- Risk adapter–human Spearman is exactly zero on the strict panel. Recomputed from banked option probabilities plus weighted human parquets: no ties, centered rank cross-product zero, sum of squared rank differences 680, n=16. Saved interval [-0.4843917804, 0.5059541738]. This is zero sample rank association, not proof of independence, no relationship, or distinct constructs.
- Trust adapter–GPS 0.80, human–GPS 0.3911764706, adapter–human 0.3264705882, persona–GPS -0.0676470588 reproduce. Saved trust adapter–human interval [-0.2344453886, 0.7357911375]; human–GPS interval [-0.1791216651, 0.7859620648]. Human agreement remains unresolved.
- Trust adapter–GPS leave-one-country-out range recomputed: 0.7785714286 to 0.85. This checks influence within the observed panel, not unseen-country generalization. The local GPS–WVS intersection has 42 countries, not 35.
- `sequence_logprob` in `DPO_survey_distribution_evaluation.ipynb` uses forward passes on supplied candidate code tokens and sums their conditional log probabilities. Optional sampled text is generated separately. Scoring needs the autoregressive model but no sampled completion. Do not use an encoder/decoder distinction as the contribution.
- DPO's Bradley–Terry/KL-policy interpretation is separate from QLoRA. QLoRA specifies an efficient restricted adaptation parameterization; it does not create the BT likelihood or its reference-policy interpretation. Explain additive reward normalization and synthetic-label assumptions.[8]
- GPS anchors are aggregates of survey measures selected through prior experimental validation, not country-level collections of incentivized choices.[11]
- Intensity weighting is neither sufficient nor universally necessary for useful behavioral prediction. It would change the construction signal. Rectification needs independently justified human validation data and an appropriate estimator, not synthetic outputs treated as truth.[5]
- Varying anchors can define experiments on the construction algorithm. That does not identify human policy counterfactuals. Under fixed bank and sign labeling, changes that preserve signs leave labels unchanged. A changed sign profile requires a corresponding fitted policy, not retraining every existing country; training randomness remains distinct from anchor effects.
- A successful outcome on one scored bank is not robustness to contamination. New-bank experiments test robustness and may reject it; they cannot be promised to demonstrate it.
- Broad novelty claims are false or unsupported: cultural fine-tuning, synthetic augmentation and country-level distribution fitting already exist.[1][2][3] Culturally grounded DPO also exists.[4] This targeted search does not establish universal priority for the exact SCA combination.
- SMR is a plausible audience; acceptance or quality cannot be inferred from a presumed monopoly on an identification strategy. The lab lists SCA1 as forthcoming, but publication/volume labels conflict across the conversation, stored notes and web references. Confirm exact publisher metadata before asserting journal/series/volume status.

## 2. Corrections to our earlier assessment

1. **Current trust result has a source.** The strict 0.80 is produced by the external audit analysis and figure source; the public script-13 0.78 uses an older, different surface. Preserve the matched result and integrate its actual computation. Do not choose between numbers on grounds of convenience or performance.
2. **Police/courts/government counts and correlations:** EGY Q69–Q71 have no valid observations. Script `06_construct_bridge.py` lines 87–88 recodes before masking; negative raw missing values become valid-looking positive scores. Its old 42-country Q69 0.55 should not enter the paper. Correct weighted correlations, masking before recoding, are Q69=0.4557491289, Q70=0.3989547038, Q71=0.2801393728 across 41 observed countries. On the 15 trained countries excluding EGY they are 0.2392857143, 0.3642857143, 0.40. No longer call Q69 the strongest current item without a complete corrected comparison.
3. **Egypt sensitivity:** retain 16-country/23-item primary surface. Separate country removal from item restoration: with 15 countries and the same nine trust items, human–GPS=0.475 and adapter–GPS=0.8071428571; restoring Q69–Q71 on those same 15 gives 0.5857142857 and 0.7928571429 respectively. These are retrospective point estimates; bootstrap the paired comparison before substantive promotion. Do not optimize sample membership against correlations.
4. **Scorer:** retained historic diagnostics show 540 high among 599 QC-pass unique pairs (about 90%, not 80%). The ratio is off-target absolute differences summed across five dimensions divided by target absolute difference. Bins are unvalidated; comparable-looking [0,1] scales need not be commensurate. Preserve raw scores and provenance, without claiming trait purity or known harmlessness.
5. **Replication:** `evaluation.ipynb` currently checks nine hashes. This verifies file integrity only, not calculations, full coverage, or reproducibility of the current manuscript. Requirements with >= bounds are not a pinned environment. Completing computational replication remains a release task.
6. **Historical compute:** report verified GPU and configuration. Establish actual account/tier and costs from run records before stating free Colab or paid Pro for every run; present-day subscriptions do not prove historical billing.

## 3. Positioning to carry forward

**Proposed claim:** We construct synthetic cultural agents from declared aggregate preference anchors, represent the resulting policies in adapters, and evaluate their transfer to a separate survey battery under prompts without country identifiers. On this diagnostic panel, trust anchor ordering transfers more strongly than the country-named prompting comparator, while correspondence with human survey orderings remains uncertain and trait-dependent.

The method's attractive feature is inspectable population conditioning plus text-responsive scoring. The empirical finding is that anchor retention and survey prediction can separate. The proposed practical use is pre-piloting; demonstrated item-screening benefits remain a future test.

Use a narrow contrast matrix in the literature review:
- CultureLLM: WVS-seeded semantic augmentation and culture-specific fine-tuning.[1]
- Cao et al.: country-level survey response distributions, probability-based fine-tuning, cross-survey evaluation.[2]
- SubPOP: supervised subpopulation-response distributions, including transfer to new surveys/subpopulations.[3]
- Jung and Kim: culturally grounded synthetic triplets and DPO, targeting Korean response coherence.[4]
- Krsteski et al.: human-data allocation between synthesis and rectification.[5]

Describe our combination precisely: aggregate economic-preference signs → a shared synthetic contrast bank → adapter fitting → country-unconditioned scoring on a separate instrument. No 'first cultural fine-tuning', 'only constructive paper', 'first aggregate method', or 'no one worried about priors' claims. Whether the entire combination is unprecedented remains unproven by a targeted search.

## 4. Final prioritized edit list

### P0 — protect the estimand and evidence

1. **Freeze one current analysis specification (M).** Primary 16 countries, 23 shared single-choice items, nine-item trust aggregate; separate patience Q43/Q50. Archive recodes, aggregation weights, missing codes, fitted checkpoints, prompt/code prefix and all three association targets. Distinguish the broader shape panel. Preserve verified numbers unless a documented calculation correction changes them.
2. **Replace identification overclaims throughout (M).** Define construct, measurement, anchor and fitted policy separately. State that aggregate moments are construction inputs, not enforced moment restrictions on human-equivalent outputs. Explicitly explain joint six-sign training versus dimension-specific evaluation; no joint-human-distribution claims.
3. **Repair evaluation interpretation (M).** Report encoding separately from external anchor transfer and human prediction. Show uncertainty on human–GPS and policy–human. Remove the claim that two anchor correlations establish construct sharing. Remove the product-of-correlations 'noisy copy' mechanism claim or label it a descriptive numerical comparison without identifying power. Do not turn failures into validation.
4. **Correct formal/scoring exposition (M).** Retain the conditional-probability object, explain DPO and QLoRA separately, reward gauge normalization, synthetic deterministic choices, and support/parameterization limits. Replace general 'pairwise identifies an ordering' claims with which observed synthetic contrasts are fitted. Explain teacher-forced candidate code likelihoods, optional generation, tokenization and normalization. Correct GPS provenance.
5. **Add limited diagnostics from existing data (M).** Reproduce full-precision zero, intervals, leave-country/item-out and sign-profile sensitivity. Retain Egypt; use a matched 15-country nine-versus-twelve-item check with uncertainty. Update or retire historical permutation results; do not present invariant rank permutations or old-panel p-values as current evidence. Label post-hoc analyses.

### P1 — make the methodological contribution readable

6. **Reframe introduction and literature (M).** Lead with group-level research need, costly human measurement and inspectable conditioning. Explain why aggregates are useful without assuming aggregation solves identification. Position against the verified training literature. Narrow the empirical claim rather than retreat into a generic software description.
7. **Make construction concrete (M).** One complete diagram and worked real bank example: anchor sign, shared scenario, opposing responses, labels, fitted adapter, scored new item. Clarify that profile prose/magnitudes are documentation in the production sign path. Include concise pseudocode and exact prompts/model/version/split details in the supplement.
8. **Demote QC coherently (S).** Remove scorer and ratio from the essential method pipeline if they did not determine training. Keep an accurately labeled historical diagnostic appendix: formula rationale, sum-vs-average, denominator instability, no validated cutoffs, no independence from model-method errors, no exclusion gate. Do not retrospectively alter the training bank. New no-scorer runs are a separately declared protocol revision.
9. **Restructure results and repair figures (M).** Application/design → held-out synthetic encoding → cross-survey associations → distributional fit and weights×prompts sensitivity. Explain the four bar series and place persona–GPS comparison within easy reach. Split patience consistently. Treat 2×2 as configuration sensitivity, not a general direction/shape decomposition or separation of latent priors; a same-anchor prompt comparator is future evidence for isolating the conditioning route.
10. **Rewrite discussion and conclusion (M).** Reusable scoring, group portability as methodological scope, prospective pre-pilot use. One-country scoring cannot certify item validity. Distinguish synthetic construction counterfactuals from human causal predictions; no demographic-shock claim. Explain purposive selection and untested new-country/bank/model generalization. Remove unsupported survey-AI feedback-loop assertions or move to a brief explicitly speculative limitation. Reduce repeated information-budget slogans, defensive negations and numbered conclusions.
11. **Clean the public artifact and supplement (M).** Resolve figure/caption mismatch, empty pipeline export, obsolete two-country material, unresolved references, author metadata and bibliography. Keep only supplementary figures used in an argument. Match current paper to replication entry and model availability, including ethical/data-use disclosures. No silent deletion of historical artifacts. Use narrative author voice, abstracts in words, and a 150-word SMR abstract when preparing that submission.[12]

### P2 — complete release verification, without new model inference

12. **Finish the three-notebook replication design (L, mostly packaging/analysis).** Make evaluation notebook actually reconstruct current numbers from approved inputs through the single analysis implementation, in an isolated output directory. Include cold acquisition, source/licensing instructions, minimum sufficient inputs, pinned tested environment, expected numerical tolerances, and fail-loud checks for missing countries/items/empty hash manifest. Preserve profiling_and_datagen.ipynb and training.ipynb in the user's requested scope; distinguish replay of frozen bank from paid new-bank generation, and reuse of frozen adapters from new training. A provider change is an extension, not exact replication. Public posting awaits approved assets and unauthenticated fetch verification. Prior local untracking did not purge public Git history; decide any history remediation separately, not automatically.

## 5. Brief execution sequence and checkpoints

1. **Evidence lock:** reconcile `external/evaluate.py`, `twobytwo_rescore/analyze_2x2.py`, figure inputs and the public analysis script. Reproduce current strict results and the limited missingness/robustness checks in a separate directory. Produce a claim-to-artifact table. Stop on mismatches; no model inference.
2. **Methods/results pass:** fork from the supplied circulating text and preserve existing `rewrite/` work. Edit methods and results first, then their figures/tables and historical QC appendix. Check every number and sample label.
3. **Framing pass:** revise literature, introduction, discussion/conclusion, then abstract/significance, so framing follows the frozen evidence. Give user one coherent patch set with scientific versus stylistic edits distinguished.
4. **Release gate:** run the completed evaluation notebook in an isolated clean environment, compare calculations rather than only bytes, compile the LaTeX fork, check warnings/references, visually inspect rendered figures/pages, hash the delivered PDF and verify source-to-artifact chain. No overwrite of `position_paper_sca2.pdf`; no publication without authorization.

Likely manuscript targets: `misc/position_paper/rewrite/{methodology,results,litreview,introduction,discussion,conclusion,abstract,significance}.tex` (create sibling revision copies where a current file is absent), its references/figures, and an explicitly named top-level revised fork. `Downloads/SCA_2/main.md` remains a read-only reference. Analysis/replication changes must be approved as the computation-integration track; do not silently overwrite committed historic results.

## 6. What is deferred

Fresh countries, fresh scenario banks, fresh training seeds, single-dimension interventions, same-anchor prompt controls, magnitude-aware losses, independent blinded human item-screening pilots, and OpenRouter/HF provider migration. Choose these by the additional claim they test. Neither arXiv nor SMR requires every possible experiment; the paper must accurately state which generality and utility claims remain untested.

## Sources

[1] https://proceedings.neurips.cc/paper_files/paper/2024/hash/9a16935bf54c4af233e25d998b7f4a2c-Abstract-Conference.html — CultureLLM (NeurIPS 2024)
[2] https://aclanthology.org/2025.naacl-long.162 — Cao et al. (NAACL 2025)
[3] https://arxiv.org/html/2502.16761v2 — Suh et al. SubPOP
[4] https://arxiv.org/html/2606.06797v1 — Jung and Kim: Korean cultural DPO (2026 preprint)
[5] https://aclanthology.org/2026.acl-long.498 — Krsteski et al.: synthesis and rectification
[8] https://arxiv.org/html/2305.18290v3 — Rafailov et al. DPO
[10] https://meehl.umn.edu/sites/meehl.umn.edu/files/files/036constructvalidityidx.pdf — Cronbach and Meehl (1955)
[11] https://www.hbs.edu/ris/Publication%20Files/Quarterly%20Journal%20of%20Economics_269d889b-69bb-4412-a7bf-e5dfa7d7bff7.pdf — Falk et al. GPS (2018)
[12] https://journals.sagepub.com/author-instructions/SMR — SMR author guidelines
