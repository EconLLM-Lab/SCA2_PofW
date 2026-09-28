# Softmax Readout Experiment (Option 4) — Results

**Date:** 2026-08-22 · **Scripts:** `analysis/phase2/19_softmax_readout.py`, `19b_readout_figures.py`
**Status:** COMPLETE — validation gate PASSED, all 16 adapters, zero GPU (arithmetic on banked option logprobs)

## Predeclared spec (frozen before any result was computed)

Readout `P̂_τ(o|q) ∝ P(o|q)^(1/τ)` over banked `model_prob` columns (verified to be exactly
`softmax(option_logprob)`; max deviation 0.0 on spot checks). τ grid {1,2,3,4,6}; τ=3 primary,
inheriting the paper's already-published T=3 diagnostic. Arms: 16 matched adapters, per-bank
base, persona (16 countries), uniform-noise reference. Metrics: TVD, normalized EMD (ordered
scales only), signed mean error, ordinal calibration ρ, policy-pair distance gauge.

## Validation gate

At τ=1 recomputed TVD reproduces `wvs_question_metrics_long.parquet` exactly:
**100.0% of 1,322 shared question rows within 1e-6** (median |diff| 1.1e-16). GATE: PASS.

## How each number was constructed

- Panel: 18,486 option-level rows = 4 families (usamex canonical, ksenias_base8, co2_8,
  persona) × matched (model, eval_country) files × 35 questions, merged to each family's
  `population_response_distributions.csv` (unweighted human distributions, missing codes masked upstream).
- TVD = ½Σ|P̂_τ − P_hum|; EMD normalized by option-value range (ordered scales only);
  calibration ρ = Spearman(model_mean, human_mean) over ordered-scale questions per arm.
- Distance gauge: TVD between two countries' adapter PMFs on matched questions, averaged
  within GPS dimension → Spearman ρ(|Δz_dim|, policy-pair TVD) over 161 (base8) / 168 (co2_8)
  pair×dim cells. Two aggregations reported (see Eval A caveat).

## Results

### Pooled dispersion recovery (arm_kind × τ, mean TVD)

| arm | τ=1 | τ=2 | τ=3 | τ=4 | τ=6 |
|---|---|---|---|---|---|
| adapter | .503 | .406 | .359 | .336 | .315 |
| base    | .467 | .381 | .345 | .329 | .314 |
| persona | .413 | .340 | .319 | .311 | .305 |

(Figures F5a, F5b in `outputs/figures/`.)

- Readout recovers large dispersion for everyone; the ordering adapter > base > persona
  (all worse than persona on TVD) is preserved at every τ.
- The **adapter−base TVD penalty shrinks monotonically** (+.036 at τ=1 → +.001 at τ=6):
  flattening erases the shape penalty without ever flipping the sign. Direction advantages
  must be claimed on the bridge/calibration axis, not TVD — consistent with the paper's partitioned verdict.

### Eval B — ordinal calibration is τ-robust

Per-arm ρ(model_mean, human_mean) moves little from τ=1 to τ=3 (full table:
`readout_ordinal_calibration.csv`). Movers: DEU .927→.839, GRC .922→.825, JPN .869→.791,
BRA .932→.903 (degrade); MEX .855→.916, RUS .899→.935 (improve). Median |Δρ| ≈ .02.
Calibration is a location property — readout temperature doesn't buy or destroy it.

### Eval A — distance gauge: NULL on current sign-only adapters

Spearman ρ(|Δz|, policy-pair TVD): base8 ρ=−.01 (p=.44), co2_8 ρ=+.02..+.13
(p=.10–.39) depending on cell aggregation (pair×dim cells vs question-level cells;
both reported in `readout_distance_gauge.csv` and figure F5c respectively).

The scatter (F5c) shows why: a **dense near-zero TVD floor** — most country pairs' adapter
policies are nearly identical regardless of GPS gap — with high-divergence outliers at
*small* |Δz|. Current sign(z)-trained adapters carry almost no magnitude information, so
sign-sharing countries collapse onto the same policy. This is an honest negative for
Ksennia's "gauge distance between countries" hypothesis *on this adapter generation* —
and it is precisely the prediction of the one-mean-agent-per-anchor-sign diagnosis.
A working gauge requires magnitude-carrying training (extended-prompt rungs or rung-mixtures).

### Eval C — bias-aware shape metrics

Normalized EMD tracks TVD closely at every τ (`readout_arm_by_tau.csv`, `emd_mean`
column); conclusions are metric-invariant, pre-empting the Wasserstein upward-bias
concern (arXiv:2608.09863).

## Noise floors & references

Uniform-noise pooled TVD ≈ .338 (paper Table 2). At τ=6 persona (.305) sits below it;
adapters (.315) approach it from above. Base at τ=1 (.467) matches the paper's published
base figures; adapter τ=1 (.503) matches the published .469–.526 adapter band (family mix).

## Anti-leakage statement

No parameter was fit to WVS. τ is a reported sweep, not a tuned constant; primary τ=3 was
predeclared from the paper's existing diagnostic. Human distributions enter evaluation only.

## Outputs

- `outputs/readout_question_metrics.csv` (question × arm × τ)
- `outputs/readout_arm_by_tau.csv`, `readout_pooled_by_tau.csv`
- `outputs/readout_distance_gauge.csv`, `readout_ordinal_calibration.csv`
- `outputs/readout_option_panel.parquet` (option-level panel, reused by future arms)
- `outputs/figures/F5a..F5d*.png`

## Status & next steps

1. Paper main body: untouched, pending discussion of full results (per decision 2026-08-22).
2. The distance-gauge null upgrades the case for magnitude-carrying arms — Option 3
   (rung-mixtures) brief delivered in chat; Ksennia's extended-prompt v2 remains parallel.
3. Open question for her: does her v1 eval include any policy-pair (cross-country) statistic?
   If not, our gauge becomes the shared predeclared test for both adapter generations.
