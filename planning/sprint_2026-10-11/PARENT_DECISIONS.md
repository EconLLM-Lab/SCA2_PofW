# Paper B sprint: parent-reviewed decisions

Status: proposed for Augusto approval; 2026-10-11. Worker audits are advisory, not frozen specifications. No GPU run or external upload has occurred.

## Storage architecture

Remove Google Drive from future compute and persistence; preserve historical copies.

Keep licensed human respondent files, GPS source data, population distributions, and model–human evaluation tables local pending explicit permission for third-party hosting. Public access and private HF visibility do not establish redistribution permission. GPS downloads explicitly state no third-party transfer without prior approval; WVS wave-specific conditions still need exact verification. Do not classify data/phase2/raw/wvs wholesale as respondent microdata: that directory includes model probabilities and derived metrics; inventory by content.

GPU jobs need model inputs/question text, adapters, and supplied option grids, NOT respondent rows. Build and hash the option grid locally; send only the approved scoring specification to Colab. Compute model probabilities on Colab; persist those to HF after question-text/base-license review. Rejoin model outputs to licensed human populations locally. Numeric demographic grids are outside the primary 23-item battery; archived gate grids are supplied separately.

Proposed minimal durable layout:
- Existing Bonorinoa/SCA2-paper-b-adapters, frozen revision 7550fd4cfe514470bb8d80918a43c9ae424d26b5: do not move weights.
- Proposed private Bonorinoa/SCA2-paper-b-artifacts: runs/<run_id>/synthetic/option_probabilities/, manifests/, gates/, snapshots/ and optional inputs/ once permissions cleared. No human rows or derived human tables yet. A separate manifests-only repo is unnecessary initially.
- Human inputs and model–human outputs remain under existing local ignored data paths; add a user-owned non-Drive backup before treating the local disk as a durable archive. Record source/hash/builder references in release manifests.
- GitHub holds code, protocols, and allowed compact summaries; exact run code hash includes uncommitted file hashes until a code commit is approved.

Upload model-only outputs per completed adapter; include all companion manifests in the commit. Resume requires exact input/artifact revision and readout hash. Verify destination commits and file hashes by readback. Failed persistence is a failed completion milestone; preserve local copy and stop scaling on unresolved upload failure. HF is not a per-line log database: batch log snapshots at milestones.

## Verified scorer issues

Parent inspected score_cohort.py and eval_lib.py and executed a small in-memory reproducer:
- Missing population cell: AssertionError Join lost rows: expected 1, got 0.
- CSV option_code dtype changes string to int64 without explicit dtype.
- Cached scores currently accepted by row count alone; adapters downloaded without a revision pin; provenance not enforced by resolver.

Minimum changes proposed: allow only explicitly recorded missing-population cells (hard-fail all unexpected misses), preserve string keys, validate cache fingerprints, pin model/tokenizer/adapter inputs where resolvable, require run records and complete frozen config, remove implicit Drive fallback, separate GPU model scoring from local population evaluation, persist each scored unit durably.

Adapter-path validation must use THE SAME WEIGHTS for independent reference and production path. Paper B CHN is freshly trained; comparing its scores to Paper A CHN probabilities is not a parity gate. Either score the historical Paper A weights to reproduce their archived outputs, or compare the same frozen Paper B adapter through a simple independent reference loader and the production switch path. Include adapter activation/disable and switch-back checks. Tolerances must be justified and pinned before cohort scoring, not copied from a worker suggestion.

## Analysis defaults proposed

- Primary battery: existing STRICT_ITEMS definition (23 unique items); Q69–Q71 secondary; patience Q43 and Q50 separate.
- Keep Q178. JOR has zero valid Q178 responses (independently verified); use explicit dimension-specific complete-case matched samples, risk human-related comparisons n=41. Describe 23 as common item menu, not a complete 42x23 observed rectangle.
- Preserve construction recodes and composite scales for comparability; no outcome-informed item reweighting. Available-case composites are secondary only.
- Country-equal descriptive correlations; profile-block bootstrap for adapter-related uncertainty; country bootstrap for human–GPS with profile-block sensitivity. Neither method is the uniquely correct sampling law for this full intersection; intervals reflect a stated resampling model, exclude GPS measurement uncertainty, and are not automatically conservative bounds.
- Profile-equal sensitivity must state aggregation explicitly: mean adapter, mean human, mean continuous GPS within profile, then rank the 26 profile means; different estimand.
- Unconditioned base has a constant composite across countries. Its base–GPS/base–human Spearman and adapter-minus-base correlation lift are UNDEFINED (parent fixture returned nan). Use paired adapter-minus-base TVD/mean-error differences instead; report direction clearly.
- Report within-profile spread descriptively; do not call it pure fitting noise until full data/config equality verified.
- Existing missingness and near-zero training exposure are reported before outcome analysis; exclusion robustness requires refit.

## Next-experiment decision

Do not freeze worker R1–R5 ladder. A confidence interval including zero is uncertainty, not proof of no transfer. Two seed reruns cannot estimate a reliable 95th-percentile noise distribution. A second training bank tests bank robustness, not prospective human item screening; that needs a distinct held-out item battery/human criterion. Same-signs-in-prompt is informative even if the adapter route fails, and can be a cheap early diagnostic.

After verified primary analysis choose by failure mode: training/provenance defects -> repair; unreliable fit -> designed seed replication; anchor transport without human agreement -> map/human criterion diagnostics and same-information prompt comparison; stable transfer with unresolved label causality -> relabel-and-refit placebo; stable transfer needing bank robustness -> independent training bank. No new training cohort until the chosen question and contrasts are approved.

## C0 — bank2 contrasts, approved 2026-10-11

No human route is feasible by the end of 2026. Pre-piloting and the probe-selected human check stay prospective. This cycle does not carry either locked Paper B claim.

The approved spend is a second scenario bank under `deterministic_sign`, then a 42-country retrain, plus a sign-profile prompt cell on the existing battery. The retrain is bank robustness. It is not human recovery and not pre-piloting.

Contrasts, frozen before any bank2 training:

- New generator, new seed, same sign rule (`chosen = A if z >= 0 else B`). No magnitude labels. No per-dimension adapters.
- Shared bank, no country name and no WVS question text in scenario or response text.
- Target count is 658 shared prompts, the source run's output (`scenarios_per_dim=110`). If the generator emits another count, stop. Do not pad or drop pairs after seeing the signs.
- After the retrain, the primary contrast is adapter–GPS on the seven surfaces against `paper-b-20261011`, profile-block intervals, seed 20261011. An imprint interval that then includes 0 is a bank move and is reported. It is not dropped.
- Cohort 1 stays pinned: revision `7550fd4cfe514470bb8d80918a43c9ae424d26b5`, Hub path `adapters/<CC>`, bank id `gps_sign_relabel_all_20260816_004545Z`. Bank2 must not write that path.
- Bank2 starts only with `SCA2_PB_PROTOCOL=bank2` and a fresh `SCA2_PB_DATA_ROOT`. The upload prefix is `bank2/<bank_run_id>/adapters/<CC>`. Resume keys on `run_record.bank_run_id`, not on the presence of an adapter file.
- `paper_b/config.py` keeps the cohort-1 constants. The switch is in memory, and only when the environment variable is set.
