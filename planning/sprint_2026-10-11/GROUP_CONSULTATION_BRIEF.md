# Paper B group consultation brief

> **Record, not status.** Written 2026-10-11. Lines about what is done, blocked or next describe that date, not today. Current status: [STATUS.md](../../STATUS.md).

For @data-scientist, @adversarial-tester, @evaluation-strategist. User requested this consultation; this brief contains project work explicitly approved for group discussion.

## Objective
Today's sprint is data science and analysis to choose the next experiment. Writing/editing is deferred until reproducible ground truth exists.

## Verified state
- Fresh full 42-country cohort; 26 distinct six-sign training profiles, 12 multi-member groups. All countries retained.
- Private adapter repo Bonorinoa/SCA2-paper-b-adapters, pinned SHA 7550fd4cfe514470bb8d80918a43c9ae424d26b5. Parent read all42 run records and confirmed shared bank gps_sign_relabel_all_20260816_004545Z.
- Parent ran full paper_b CPU suite: 139 passed in7.45s. This does not establish GPU scoring validity.
- Real cohort scoring has NOT run. No new adapter outcome has been analyzed.
- Private model-only artifact repo Bonorinoa/SCA2-paper-b-artifacts created; small metadata upload/readback bytes verified at commit ae15922ca3cfc8a876e48828030feed2e7953255. No human uploads.

## Approved architecture
Human respondent data, source GPS files, population distributions, and model–human joins stay local pending permissions. Colab receives only approved question/option specs and model weights; synthetic probabilities persist to HF per completed unit. Drive removed from future critical path; historical copies preserved. GPU scoring should need no respondent records.

## Known integration blockers
Worker created score_runtime.py/build_scoring_spec.py plus local evaluate_local.py/analyze_surface.py, but old CLI/VM wrapper still not wired to new runtime. Parent found wrong real HF download-directory layout, fake-client-only persistence interfaces, weak n_train enforcement, cache fingerprints omitting prompt/actual dirty code, gate keys omitting option_code, weak finite/duplicate checks, and unbound gate marker. Repairs underway with a Nous Portal GLM5.3 Flash worker. Independent evaluator/analysis review also underway. No GPU until repaired real interfaces, CPU fixtures, and exact-weights adapter gates pass.

## Analysis defaults approved
- Preserve existing23 STRICT_ITEMS, Q69–Q71 secondary, patienceQ43/Q50 separate, E[recode].
- JOR/Q178 has zero valid answers (parent verified): retain item, explicit risk human-related complete-case n=41; no fictitious full42x23 observed rectangle.
- Country-equal descriptives; profile-block resampling for adapter-related uncertainty; country resampling human–GPS and profile sensitivity. State the resampling assumptions for a full intersection; no automatic effective-n or conservative-bound claims.
- Profile-equal sensitivity means aggregate each variable within profile first, then correlate26 profile means; different estimand.
- Unconditioned base composite constant across countries -> Spearman undefined. Base comparator uses paired TVD/mean-error differences, not correlation lift.
- Within-profile spread descriptive; fitting-noise interpretation needs complete training/config identity.
- Near-zero exclusion requires refitting adapters, not filtering outcomes.

## Concrete consultation questions
@data-scientist: challenge weighting, profile bootstrap, complete-case matched samples, composite scaling, and distributional base contrasts. Which diagnostics most clearly separate map failure from adapter failure?

@adversarial-tester: propose the smallest falsification battery for real scoring and persistence. Insist exact weights for parity; positive fixtures AND broken variants; complete gate key matching; cache revision binding; clean adapter A-B-A switching and base disable. Identify a remaining false-green path.

@evaluation-strategist: recommend an experiment-choice framework conditional on the first frozen results. Separate label-causality placebo, second training-bank robustness, same-signs-in-prompt route comparison, and held-out human item-selection validation. A zero-crossing interval is uncertainty, not proof of no transfer; two seed reruns cannot calibrate a95th-percentile noise distribution. Prioritize the experiment that resolves the evidence bottleneck.

## Requested output
One concrete recommendation per role, explicit assumptions, smallest decisive check, and what result would change the recommendation. Do not edit files, launch GPU, alter frozen protocols, or invent outcome numbers during consultation.

Authoritative project files: TWO_PAPER_CLAIM_LOCK.md, PAPER_B_PROTOCOL_DRAFT.md, sprint_2026-10-11/PARENT_DECISIONS.md under /Users/bonorinoa/Hermes/Projects/SCA2. Worker drafts are advisory, not frozen authority.
