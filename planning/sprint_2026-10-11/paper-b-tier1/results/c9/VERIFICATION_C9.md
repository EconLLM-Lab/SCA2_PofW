# VERIFICATION_C9 — independent verification of C9-1, C9-2, W1 (and C9-4 status)

Verifier: profile `verifier`, route **openrouter deepseek/deepseek-v4.1-flash** (task `t_b95d3240`; a different
model family from the Claude producers of C9-1 / C9-2 / W1). Date 2026-10-19 (MST), branch `feat/paper-b-cohort`,
HEAD `2e43347`, everything under `results/c9` untracked (nothing committed).

Fence: read-only. I wrote only this file. Nothing under the project root was hand-edited. **Disclosure:** running
the producer's full test suite (which includes `paper_b/test_c9_gpu_jobs.py`) rewrote the two *untracked*
repo-root files `results/c9/c9_label_recovery.{json,csv}` — that test writes to a cwd-relative `results/c9` instead
of `tmp_path`, so its own rerun permutes the per-country row order. Hashes before/after are in my snapshot; no
tracked file changed (`git status` stays `M STATUS.md` + untracked).

## 0. Verdict

- **C9-1 (t_c13b7536): ACCEPT.** Every headline number I recomputed with my own code matches at printed precision;
  labels, interval types, n, and complete-case handling are right; governance clean.
- **C9-2 (t_f388a6cd): ACCEPT** for the three computed cells (base, adapter, persona). The `adapter_persona` cell is
  correctly `pending` and correctly empty — no number was invented for it (operator note 2).
- **W1 (t_4a961051): ACCEPT as a descriptive decomposition** (all numbers reproduce; wording/interpretation caveats
  in §5 travel with the claim).
- **C9-4 (t_8d569fe0): recorded NOT RUN.** No GPU session happened; the only C9-4 output is a 16-country fixture
  summary of the old preprint margins. The 16-country fixture (`analysis/phase2/outputs/gps_reward_recovery_long.csv`,
  2,112 cells) is never a C9-4 result. C9-GV (`results/c9/C9_GPU_VERIFICATION.md`, Claude seat) already blocks it;
  I consume that verdict rather than re-litigating same-family GPU code. A separate C9-4 audit is expected from the
  PM's direct execution.
- No blocking finding against C9-1, C9-2 or W1. Two non-blocking C9-4 findings are recorded in §4 for that audit.

## 1. Commands run (exit codes captured directly, no pipe)

- `HF_TOKEN= env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest paper_b/test_c9_human_agreement.py paper_b/test_w1_crosstalk.py -q -p no:cacheprovider` → **exit 0**, `18 passed in 22.75s`
- `HF_TOKEN= env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest paper_b -q -p no:cacheprovider` → **exit 0**, `599 passed in 252.44s` (the `c9_tvd` collection error C9-GV saw at 17:38 is gone: `paper_b/c9_tvd.py` now exists)
- `colab status` → `[colab] No active sessions.` (exit 0); `colab usage` → balance 181.82 CU, 0.00/hr, 0 active assignments (exit 0)
- My own recomputation scripts (no producer import): `<scratch>/c9v/rc1.py … rc5.py`, all exit 0
- `git status`, `git diff`, `git ls-files`, `shasum` snapshots of `results/` and `.../results/c9/`

## 2. Independent recomputation (my own code, not the producer's modules)

### C9-1 (`c9_human_agreement`) — all values recomputed from `model_probs.csv` + the local human item means + GPS z

Part (a) cohort-1 three columns (mine / producer, both at printed precision):

| surface | adapter-GPS | adapter-human | human-GPS |
|---|---|---|---|
| trust | 0.7441050158 | 0.2951948789 | 0.3507819464 |
| patience:Q43 | -0.0191255725 | 0.1920661305 | -0.5326148610 |
| patience:Q50 | 0.1768900413 | 0.0033222591 | 0.3880560733 |
| risktaking | 0.4345677012 | 0.1195121951 (n=41) | -0.0587108014 |
| posrecip | 0.4875617859 | 0.3235556276 | 0.0543716068 |
| negrecip | -0.0281176566 | 0.3888663804 | 0.4160926991 |
| altruism | 0.4062069524 | 0.1282716149 | 0.0313588850 |

Part (b) bank-2 adapter-GPS, my own unit mapping (`P_…` sign rule) vs the 42 countries: trust 0.8032452596,
patience:Q43 0.0053538868, patience:Q50 0.1606166041, risktaking 0.2100994973, posrecip 0.3656055731,
negrecip 0.2389780383, altruism 0.3636587052 — identical to the producer's rows and to the `B2_bank2_*_rho` pins
(spot-checked `B2_bank2_trust_rho` = 0.8032452595902299). I also independently confirmed the bank-2 unit partition
equals the `sign_profiles` partition: 26 profiles, 12 multi-member, 28 multi-member countries, sizes [2×8, 3, 3, 4].

Part (c) between-profile share of the **human** composites (my code, multi-member only) and permutation p:
trust 0.3836173181 / p 0.551245; patience:Q43 0.3176761870 / 0.738226; patience:Q50 0.4958034367 / 0.250675;
risktaking 0.5072307083 / 0.219178 (n=26, JOR drops); posrecip 0.5312634810 / 0.168783; negrecip 0.6258098505 /
0.059194; altruism 0.4251385268 / 0.421158. Chance means 0.4055 / 0.4079 / 0.4055 / 0.4017 / 0.4054 / 0.4080 /
0.4056 — all match the producer's rows exactly. Adapter-side shares are 0.957–0.9999 with p = 9.999e-05.

Part (c) power: smallest detectable true share at 80% power = **0.60** (interpolated 0.5684210526),
simulated chance mean at s=0 = 0.4108851874 — exact reproduction of the producer's three power rows.

Part (d) sign-mate agreement (human, LOO mean of profile mates): trust -0.1209633279, patience:Q43 -0.3503010400,
patience:Q50 -0.0213464696, risktaking 0.1104273504 (n=26), posrecip 0.0853858785, negrecip 0.3316912972,
altruism -0.1220580186 — exact.

Part (e) own-sign reference `Spearman(sign(z), z)`: trust 0.8623333645, patience 0.8167281126 (both Q43/Q50),
risktaking 0.8623333645, posrecip/negrecip 0.8662709803, altruism 0.8573859148 — exact; ratio rows follow.

### C9-2 (`c9_tvd`) — recomputed from `model_probs.csv` + `persona_strict.csv` + the local population distributions

| cell | countries | cells | mean TVD country-equal (mine) | pooled (mine) |
|---|---|---|---|---|
| base | 42 | 965 | 0.470047 | 0.470023 |
| adapter | 42 | 965 | 0.515477 | 0.515450 |
| persona | 42 | 965 | 0.364905 | 0.364903 |

Producer wrote 0.470 / 0.515 / 0.365 (and pooled equal to 3 dp). Contrasts: `adapter_minus_base` +0.045430 (producer
+0.045), `persona_minus_base` -0.105142 (producer -0.105), n=42 both. Trust-GPS: adapter 0.744105, persona 0.027794
(producer 0.744 / 0.028), base constant → undefined. 965 = 42×23 − 1, i.e. exactly the JOR/Q178 complete-case drop.

### W1 (`w1_crosstalk`) — recomputed the effect matrix, the decomposition, the 64-cell shares and the label check

Main-effect matrix (6 bits × 7 surfaces) reproduced to **1.4e-15** elementwise (adapter route). Decomposition over
the 42 cohort countries: `rho(full,GPS)` trust 0.834 (producer 0.834), risktaking 0.104 (0.104), patience:Q43 -0.020
(-0.020), patience:Q50 0.176 (0.176), altruism 0.422 (0.422), posrecip 0.378 (0.378), negrecip 0.386 (0.386);
`rho(own,GPS)` 0.817–0.866; `cross_var_share` trust 0.147, risktaking 0.999, patience:Q43 1.049, patience:Q50 0.914,
altruism 0.850, posrecip 0.854, negrecip 0.830 — all reproduce. 64-cell main-effect share: trust 0.806,
risktaking 0.609, patience:Q43 0.483, patience:Q50 0.891, altruism 0.925, posrecip 0.711, negrecip 0.666 — all
reproduce. Bank-1 label dependence: **27,636 country-pair rows, 0 mismatches** — reproduced. Cross-route check: the
own bit is the largest |beta| in its own column on **1 of 7** adapter surfaces (trust only), which is exactly the
pattern the claim rests on.

Small print: `rho(cross,GPS)` differs from the producer by up to 0.016 on 4 surfaces (e.g. altruism 0.301 vs 0.285)
because several cross values are exact ties whose break depends on floating-point equality; with the producer's own
betas stored in the JSON the value reproduces exactly (0.284532). Not a finding.

## 3. Labels, estimators, n, complete-case, governance

- **Rows labelled:** 167/167 C9-1 rows carry `DESCRIPTIVE / NOT PREREGISTERED`; the W1 JSON label and every
  `c9_tvd.csv` row (33 rows) carry it too.
- **Interval types:** every `human-GPS` row uses the **country bootstrap** (11 rows) and no adapter-side row does;
  adapter / bank-2 / sign-mate / own-sign rows use the **profile-block bootstrap**; ratio, share, p-value and power
  rows are explicitly `none (point value)` with the permutation-null percentile shown on the chance-mean rows. This
  matches sprint rule 6 exactly.
- **n:** `adapter-human` risktaking n=41 and `human-GPS` risktaking n=41 are the only sub-42 rows, both from the JOR
  complete case; between-share multi-member rows are n=28 (n=26 on risktaking, where JOR's profile drops below 2
  members after the same drop).
- **Complete-case ledger:** `local_eval/skipped_population_questions.csv` lists exactly EGY/Q69, EGY/Q70, EGY/Q71,
  GBR/Q174, JOR/Q178 (`no_valid_responses`). Q69–71 and Q174 are **not** strict-battery items (trust Q57–Q64,Q73;
  risktaking Q106,Q107,Q109,Q178; patience Q43,Q50; posrecip Q81; negrecip Q176,Q177,Q179,Q195; altruism
  Q99,Q101,Q103), so "only JOR/Q178 removes a battery cell here" is correct and the 965-cell count confirms it.
- **Pins untouched:** `NUMBERS_TABLE.csv` and `paper_b/heldout/FREEZE.json` are tracked and `git status` reports no
  change for either. `FX_adapter64_*_own_beta` and `B2_bank2_*_rho` pins are present and match my recomputation.
- **Human-data governance:** `human_item_means_42.csv` and `population_response_distributions.csv` are gitignored,
  local-only. No file under `results/c9/` or repo-root `results/` mentions `human_prob` / `population_prob`, and the
  known human item mean (ARG/Q57) appears nowhere in them; the C9 outputs hold only correlations, shares, intervals
  and p-values. No country-level human means were written anywhere I can see.
- **Prompts:** the country-named arm is only the declared C8 comparator (`persona_<CC>`, `persona-strict-v1-20261019`);
  the adapter/base rows carry no country name. The C9-4 adapter+persona run — the other country-named arm — never ran.
- **Secrets:** no `hf_…` token string in any C9 script or output; `c9_tvd.py` reads `HF_TOKEN=` from
  `/Users/bonorinoa/.hermes/profiles/sca/.env` in code and never prints it. `git status` shows only `M STATUS.md`
  plus the untracked C9 files; nothing committed, pushed or tagged.

## 4. C9-4: recorded NOT RUN (consuming C9-GV's BLOCK)

Tool-observed compute state at 18:45–19:00 MST: `colab usage` balance **181.82 CU**, rate 0.00/hr, 0 active
assignments; `colab status` "No active sessions". That is the same balance reported before the card ran, so
tool-observed CU spend is 0 and no VM is leaking. The card's 5 CU cap is therefore not exceeded — trivially, because
nothing ran.

Two findings to carry into the C9-4 audit (neither is a block from me, since C9-4 is not run and the PM is executing
it directly):

1. **`c9_gpu_run.md` contradicts its own code.** `results/c9/c9_gpu_run.md:7` says "Units: 42 … using real adapter
   weights" and :28 "uses the actual cohort-1 adapter", while `c9_gpu_jobs.py:182` states the same call is the
   "planning/launch script, NOT the adapter loader". `PERSONA_SPEC_SHA` (c9_gpu_jobs.py:12) is defined and never
   used. The only numbers in the C9-4 outputs come from the 16-country fixture, which is stamped with the real
   `label-recovery-v1-20261019` run id and the real adapter pin (c9_gpu_jobs.py:137-138) — a mislabel to remove.
2. **The recovery-definition citation is imprecise.** The definition *is* in the preprint: `results.tex:28`
   ("The former records a positive improvement in the chosen–rejected margin over the reference; the latter records
   a positive adapted-model margin itself") and, more precisely, `methodology.tex:68`. The stored citation says
   "results.tex line 28, methodology.tex line 24", but `methodology.tex:24` is a figure caption
   (`\caption{Construction and readout…}`) and states nothing about recovery. Point the citation at
   `methodology.tex:68` and give a cell reference inside
   `DPO_train_test/Base_run/DPO_evaluation_cross_evaluation_selective_cached_ref.ipynb` (the file exists).

## 5. Rulings on the two candidate insights

**I1 — "Countries that share a GPS six-sign profile are no more alike on the WVS battery than random groups of the
same sizes, so the main limit on human prediction is the anchor, not the language model." → WEAK.**

Reason. The non-rejection reproduces exactly (multi-member shares 0.318–0.626 against chance means ≈0.406, one-sided
permutation p 0.059–0.738; negrecip at 0.059 is the closest to significant, and its observed share 0.626 sits above
chance), but my independent power run confirms the design is underpowered: with the realized 12 groups you need a
true between-share of **0.57–0.60** for 80% power, and only negrecip's observed value reaches that region. So the
first clause is "cannot detect an excess", not "no grouping". The second clause is not warranted by any test here:
non-rejection does not locate a bottleneck, and no comparison in this card identifies anchor-side versus
model-side error. What the card *does* support is the weaker companion pattern — sign-mate agreement among human
composites is flat (−0.35 … +0.33, every interval spanning 0), human–GPS rho is small (0.03–0.42) while adapter–GPS
is large (0.43–0.74) — i.e. the profile carries little *detectable* human signal and the adapter tracks GPS far
better than either tracks humans.

Caveat that must travel: "not rejected under 12 groups of size 2–4, at ~0.57 true share for 80% power"; the
bottleneck sentence ("the anchor, not the language model") is an interpretation, not an identified result. Also note
that neither the LOO mate correlation nor human–GPS rho bounds an arbitrary profile-constant or nonlinear scorer.

**I2 — "Cross-talk between sign bits explains why adapters keep each bit's direction but lose the GPS country order
on most dimensions; trust is the exception because its own bit dominates." → WEAK.**

Reason. The descriptive core is solid and I reproduced all of it: own-beta signs are right-signed for the adapter
route on all 7 surfaces; the own-only prediction ranks like GPS on all 7 (|rho| 0.817–0.866, mechanically the
sign–GPS correlation); the main-effects prediction retains the GPS order only on trust (0.834) and loses it on the
other six (0.104 / −0.020 / 0.176 / 0.422 / 0.378 / 0.386); the own bit is the largest |beta| in its column on
**trust alone** (1 of 7); and the cross term's share of Var(full) is 0.147 for trust versus 0.83–1.05 elsewhere.
What makes the claim WEAK is the word "explains/why" plus one metric choice. `cross_var_share = Var(cross)/Var(full)`
is **not a bounded share** — it is 1.049 on patience:Q43 and 0.999 on risktaking — so it cannot be quoted as a
percentage of variance. The producer did also compute the covariance-based share (`cross_cov_share`, bounded and
additive: trust 0.287 vs 0.727–0.985 elsewhere) and it tells the same story; **quote that one**. Beyond that, this
is a decomposition of a 6-main-effect linear model, not a neural mechanism: two-way interactions are needed on 4 of
7 adapter surfaces (main effects 0.48–0.71 of 64-cell variance) and, while they do not rescue the GPS ordering
(main+2way rho vs GPS 0.331 / −0.066 / 0.287 / 0.210), the "shared direction" mechanism is untested — it is exactly
the follow-up the card proposes.

Caveat that must travel: state it as a **behavioral decomposition** of trained systems (synthetic model quantities
plus published GPS z; no human rows); replace `cross_var_share` percentages with `cross_cov_share`; the rank
correlation between cross-talk and GPS failure is 0.821 against bank-2 composites but 0.286 against cohort-1
composites and is driven by one surface (trust) against six, so it is not a graded relationship; the own-only
correlation is mechanical, not independent evidence of generalization; and nothing here establishes neural
mechanism or human-preference causality (cohort-1 transfer is weakest on risk and negative reciprocity).
