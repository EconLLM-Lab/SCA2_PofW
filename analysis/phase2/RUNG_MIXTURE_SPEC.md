# Rung-Mixture Pilot — Predeclared Spec (v1.2.1, 2026-08-22)

**Status:** v1.2.1 is a hygiene / resume-safety bump on frozen v1.2. Scientific constants
are unchanged. One adapter (`adapter_rung_-3`) already exists on the Hub from the
2026-08-22 v2.0 launch that OOMed at the −2 load; remaining rungs resume under this
file. Constants below are declared ex ante; none may be tuned against WVS or
AmericasBarometer. Further deviations require a version bump and a note here.

## Changelog v1.0 → v1.1

No scientific constants changed (β = 1.0, δ = 0.25, s_w = 1.0, seeds, gate thresholds).
All changes are implementation-validity fixes found in the 2026-08-22 forensic audit of
the failed first launch (session `sca/20260822_094955_4692a1`; 0 adapters saved):

| # | Deviation from v1.0 practice | Fix | Why |
|---|---|---|---|
| B1 | `prepare_model_for_kbit_training` called AFTER `get_peft_model` froze the LoRA weights → optimizer with zero trainable params → `No inf checks` crash | Call order: k-bit prep on the fresh quantized base FIRST, then `get_peft_model`; hard assert `any(p.requires_grad for p in model.parameters())` before `Trainer` | crash root cause |
| B2 | SFT wrapper welded ONE question's option-list suffix onto every training example | SFT context = shared canonical PRE + scenario + `"\n\nAnswer:"`; no per-question suffixes in training | context pollution |
| B3 | Rung PMFs scored on `option_label` text while every banked comparison arm scores the numeric option code | Score PMFs on option CODES under verbatim `formatted_prompt` (identical surface to base/adapters/persona); SFT targets stay free-text (intensity signal lives there) | cross-arm comparability |
| B4 | Per-rung independent 80/20 shuffles → same-sign holdout overlap only 18–26 prompts | ONE shared stratified partition of the 599 prompts applied to all rungs; holdout = same 120 prompts everywhere (fully paired) | Gate-2 power |
| B5 | Persona arm silently dropped (filename glob mismatch) | Correct filenames (`model_option_probabilities_{C}_adapter_persona.csv`) + loud assert on arm counts | silent-drop class |
| B6 | Double BOS in SFT tokenization | `add_special_tokens=False` for all pre-wrapped text (train + eval) | train/eval consistency |
| B7 | GPU runner lived in /tmp; Test B missing noise floor + CI; Test A drew Dirichlet w off the operational manifold | Runner is repo-versioned (`colab/rung_sft_vm.py`), md5 recorded in run log; uniform-noise arm + 10k bootstrap CI added; Test A w drawn from the operational softmax family | reproducibility |

## Object

Six global SFT adapters π_k, k ∈ {−3,−2,−1,+1,+2,+3}, trained on Ksennia's variant bank
(`DPO_train_test/generated_response_variants_3.csv`, 599 prompts × 6 rungs = 3,594 rows).
No country information anywhere in training. Country policies are then *declared mixtures*:

    P_c(q) = Σ_k w_c,k · P_k(q),   w_c,k = softmax_k(κ · δ · z_{c,dim} · k)

**Frozen constants:** κ = 1.0 (global temperature, mirrors soft-DPO's κ=1 precedent),
δ = 0.25 (slope: at |z|=2 the adjacent-rung odds ratio is e^{δ·|z|} = e^0.5 ≈ 1.65,
exactly as worded in v1.0's rationale). z = 0 ⇒ uniform 1/6 (neutral); sign(z) tilts
mass toward same-sign rungs; |z| sets concentration. Sensitivity arms: δ ∈ {0.5, 2}
(reported as curves); κ sensitivity secondary.

### Changelog v1.1 → v1.2 (2026-08-22, pre-data)

**B8 — FATAL, found during the local dry run:** the v1.0/v1.1 formula
`softmax_k(β·z + δ·k)` is mathematically independent of z — β·z enters every logit
as the same additive constant and softmax cancels additive constants
(probe: max |w(z=−1.5) − w(z=+1.5)| = 0.0). Every country would have received the
IDENTICAL mixture policy. The corrected interaction form `softmax_k(κ·δ·z·k)` is the
unique parameterization consistent with both v1.0 rationale sentences (the e^{2δ}
at |z|=2 wording and the κ-precedent wording). Discovered because the rebuilt
distance-gauge produced exactly-zero policy TVDs for all 120 country pairs
(ConstantInputWarning → probe → proof). No trained artifact existed at any point;
all other constants, gates, thresholds, and seeds unchanged.

### Changelog v1.2 → v1.2.1 (2026-08-22, one adapter already on Hub)

**B9 — crash, not a scientific constant.** `get_peft_model(base, lora)` wraps in
place. v2.0 did `del model` and kept `base`, so the next `fresh_base()` tried to
place a second 8B copy on a T4 that still held 12.9 GiB. Rung −3 finished
(loss 1.79 → 0.89, pushed to `Bonorinoa/sca2-rung-mix/adapters/adapter_rung_-3/`);
rungs −2…+3 never started. v2.1 does `del model, base` after each save, pulls any
Hub-resident adapter onto a fresh VM before Gate 2, and writes `gate2_raw.json`
(per-prompt choices/margins) so the Gate-2 margin reading can be audited locally.
No constant, threshold, seed, scoring surface, or mixture formula changed.

**Doc-only:** Test A prose below now matches the v1.2 interaction mixer already
implemented in `21_rung_mixture_eval.py` (`softmax_k(κ·δ·u·k)`). The v1.1 paragraph
still described the B8-inert additive form; the code never shipped that form after
the v1.2 bump.

## Stage gates (must pass in order; failure at any gate stops the pipeline)

### GATE 1 — Data split integrity (local, no GPU)
- ONE shared stratified 80/20 train/holdout partition by GPS dimension, seed 20260822,
  applied identically to all six rungs ⇒ every rung's holdout is the same 120 prompts.
- No prompt appears in both sides of any split; universes identical across rungs.
- Holdout is used ONLY by Gate 2; never for adapter selection.

### GATE 2 — Rung purity (per adapter, on the shared 120-prompt holdout; fully paired)
Each π_k must differ from same-sign neighbors **in degree, not direction**:
- Choice-agreement ≥ 85%: π_+1 vs π_+2, π_+1 vs π_+3, π_+2 vs π_+3 (same for −).
  Yardstick: each scenario's original A/B pair, scored under the SFT wrapper.
- Margin monotonicity: Spearman ρ(|k|, margin) ≥ 0.5 per sign (n = 120 paired margins).

### GATE 3 — Intensity separation (cross-rung)
Mean pairwise TVD between rung PMFs P_i(q), P_j(q) over the 35 eval questions:
median(adjacent-sign TVD) > median(cross-sign TVD), Mann-Whitney one-sided p < 0.05.

## SFT & scoring surface (declared)

- SFT example: `<canonical PRE>` + scenario + `\n\nAnswer:` + variant response.
  PRE is the shared system+user header of the canonical eval wrapper (verified identical
  across all 35 eval questions). Completion-only loss: prompt tokens masked −100.
- Scoring: option CODES (e.g. "1", "2") under verbatim `formatted_prompt` from the
  scoring bundle; softmax over codes ⇒ P_k(q, o). Identical convention to all banked arms.

## Eval battery (identical to Option 4's, plus mixture-specific)

**Scope:** the 30 GPS-mapped eval questions. The 5 demographic items without a GPS
dimension (Q260 sex, Q261/Q262 age, Q275 education, Q288 income) are excluded from ALL
arms alike — the mixture mechanism has no z-score to weight them with. Additionally,
country×question cells where the human distribution is unavailable (EGY Q69–Q71,
GBR Q174) are excluded from ALL arms alike at the cell level; every arm's per-country
mean is computed over an identical question set.

Arms at matched countries (16): base / per-country adapters / rung-mixtures / persona /
uniform noise. Metrics: pooled & per-country TVD, ordinal calibration ρ, distance gauge
ρ(|Δz|, policy-pair TVD) with 10k-bootstrap CI (seed 20260822).

### TEST A — Synthetic self-consistency (no humans; runs FIRST)
Draw 20 synthetic w-vectors from the OPERATIONAL family: w = softmax_k(κ·δ·u·k),
u ~ N(0, 2²) i.i.d. per dimension (covers the |z| ≤ 2 range countries occupy), plus the
16 country w-vectors (one per dimension-mixture actually used). Check observed policy-pair
TVD against the predicted distance under the trained P_k. Predeclared criterion:
Spearman ρ(observed, predicted) ≥ 0.9 across all pairs, else STOP.

**v1.1.1 (2026-08-22, pre-data):** predicted distance defined with estimator symmetry —
mean over the SAME eval questions of the per-question w-vector Euclidean distance
‖w_{d(q)}(u) − w_{d(q)}(u′)‖ — replacing the earlier unweighted-RMS-over-dimensions
formulation. Found during the local dry run: the observed side averages over questions
(trust = 12 of 30), so an unweighted-RMS prediction aggregates over a different measure
and injects rank noise. No constant, threshold, or data changed; the dry run's STOP path
fired correctly on the mismatched version, validating the gate mechanics.

### TEST B — WVS battery (only if A passes)
1. Mixture TVD ≤ status-quo adapter TVD; parity acceptable.
2. Distance gauge: mixture ρ > adapter ρ, adapter CI excluding mixture ρ (10k paired
   bootstrap over cells, seed 20260822).
3. Calibration: mixture ρ(model_mean, human_mean) ≥ base-model ρ − 0.02.

### TEST C — AmericasBarometer transport (USA/MEX, `clean` items) — unchanged from v1.0.

## Ablations (predeclared, cheap): K=3 collapse; β ∈ {0.5, 2}; leave-one-rung-out.

## Compute budget
6 × QLoRA SFT (~479 × 3 examples each, T4) ≈ 2.0 units; Gate 2 + PMF scoring ≈ 0.5;
smoke test ≈ 0.1. Total ≈ 2.6 units. Mac stays analysis-only (paper convention).

## Runner & provenance
- GPU runner: `analysis/phase2/colab/rung_sft_vm.py` (version-controlled; VM copy must be
  md5-identical — recorded in run log). Inputs: HF dataset repo `Bonorinoa/sca2-rung-mix`
  (payload tarball, sha256 recorded). Outputs: adapters + `rung_pmfs.csv` +
  `gate_2_3_report.json`, pushed incrementally to the same HF repo per milestone.
- Bank: `generated_response_variants_3.csv` @ commit `9bc6f4f` (dichotomous-reflection,
  2026-07-09). GPS z: `data/GPS/GPS_dataset_country_level/country_gps.dta`.
- Eval surfaces: `data/phase2/raw/wvs/{usamex_canonical,ksenias_base8,co2_8}/`
  + `population_response_distributions.csv` per family; persona arm
  `data/phase2/raw/wvs/persona_adapter/`; AB parquets under `data/merged/`.
- If Gate 2/3 fail: STOP; generator-level root cause; any regenerated bank needs
  Ksennia's sign-off (her generator, her QC conventions) — not a silent patch.
