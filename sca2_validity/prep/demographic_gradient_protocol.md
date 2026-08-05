# SCA2 Individual-Level Demographic-Gradient Protocol (DRAFT)

**Status:** DRAFT for Augusto review — not frozen, not pre-registered.
**Owner:** Augusto owns every threshold, cell definition, exclusions, and claim in this document.
**Place in pipeline:** downstream of the country-level P1 criterion profiles (`data/validity/runs/`); answers the next question: *do the facets/adapters track the GPS constructs at sub-country resolution, without revealing the target population?*

---

## 1. Motivation — why individual-level, and why gradients

The country-level P1 profiles (unit = country, 42-country GPS overlap) established:

| Dimension | Verdict at θ=0.30 |
|---|---|
| trust | 3 of 4 facets admissible; survivor composite r=+0.41 vs GPS trust |
| patience | only `financial` (Q50) admissible |
| negrecip | only `justifiability` admissible |
| risktaking / altruism / posrecip | empty M* |

Limitations of that evidence:

1. **Ecological/aggregation bias.** Country means can correlate because both variables track development (GDP, secularization, education), not because the facet measures the construct *in individuals*.
2. **Small effective n** (42 countries) and knife-edge slacks (e.g., trust out-group slack +0.003).
3. **The adapter eval cannot currently claim country-specificity**: `PROMPT_COUNTRY_CONDITIONING=False` makes model probabilities identical across eval countries by design (verified: files differ only in the `eval_country` label). The *fidelity* claim ("adapter distribution is closer to country X's responses") is preserved; the *conditional* claim is not testable from those files.

**The demographic-gradient design fixes all three while keeping the anti-leakage property intact**: instead of revealing the country to the model, we reveal *demographics* (sex, age, education), and test whether the measure reproduces the demographic structure of the construct that the GPS individual data documents.

### Why gradients are valid evidence for construct validity

The GPS individual-level data (Falk et al. 2018; Falk & Hermle 2018, *Science*) shows stable, replicable demographic gradients of each preference. If a WVS facet or an adapter output measures the *same latent construct* as the GPS dimension, then **within-country demographic variation of the facet should align in sign (and roughly in shape) with the GPS dimension's demographic gradient**. Gradient alignment is:

- **robust to the development confound** (it is measured *within* country and across demographic cells, not across countries);
- **testable without matched individuals** (GPS and WVS are different samples; we compare gradient *vectors*, not individual pairs);
- **country-free** (no country names anywhere in adapter prompts).

---

## 2. Data sources (all local, no new collection)

| Source | Path | Use |
|---|---|---|
| GPS individual | `data/GPS/GPS_dataset_individual_level/individual_new.dta` (80,337 respondents, 76 countries) | Criterion: individual preference composites + demographics (gender, age, `subj_math_skills`, `wgt`) |
| WVS wave 7 | `data/WVS/WVS_wave7.dta` (66 countries) | Human facet scores + demographics (Q260 sex, Q262 age, Q275 education, Q288 income) |
| Adapter eval | `DPO_eval_WVS/eval_results_wvs_wave7/model_option_probabilities_*` | **Only for Stream A baseline**; Stream C needs new persona-conditioned inference |
| Protocol | `sca2_validity/prep/protocol.yaml` | Facet recipes (normalize → direction → facet mean) reused verbatim |

**GPS individual variables (verified):** `country, isocode, region, gender, age (15–99), subj_math_skills (0–10), wgt, patience, risktaking, posrecip, negrecip, altruism, trust`. Gender coding (0/1) must be verified against the GPS codebook before paper use (see §9).

---

## 3. Design overview

Three complementary streams, all sharing one principle: **compare demographic gradients, never reveal country identity**.

```
Stream A   GPS benchmark        — estimate demographic gradients of each GPS dimension
Stream B   WVS human gradients  — same gradients for WVS facet scores (human side)
Stream C   Adapter gradients    — same gradients for adapter/base persona-conditioned outputs
        A ↔ B:  does the WVS facet track the construct's demographic structure?   (construct validity of facets)
        B ↔ C:  does the adapter reproduce the human facet gradients?              (validity of adapters)
        A ↔ C:  does the adapter reproduce the GPS demographic structure?          (GPS recovery, indirect)
```

Plus the **cell-mean design** (§6), which sharpens B and C into a correlation test at sub-country resolution.

---

## 4. Stream A — GPS benchmark gradients (criterion side)

**Estimator (per dimension d):**

```
pref_d ~ β0 + β_gender·gender + β_age·age + β_age2·(age/10)² + β_math·subj_math_skills + ε
```

**Specifications:** pooled all-countries with country fixed effects; and USA-only, MEX-only. Unweighted first (GPS `wgt` retained for sensitivity; SCA2 convention = unweighted safe default). Min-n guard: ≥ 200 respondents per country-dimension cell.

**Benchmark computed 2026-08-05 (real data, unweighted OLS):**

Pooled (n ≈ 78k):

| dim | gender (1=female) | age | age² | math skills |
|---|---|---|---|---|
| patience | −0.045 | +0.014 | −0.017 | +0.045 |
| risktaking | **−0.186** | −0.002 | −0.012 | +0.049 |
| posrecip | +0.069 | +0.014 | −0.014 | +0.042 |
| negrecip | **−0.136** | +0.001 | −0.009 | +0.043 |
| altruism | +0.096 | +0.001 | −0.001 | +0.043 |
| trust | +0.067 | +0.009 | −0.005 | +0.063 |

Directionally consistent with Falk et al. 2018: women more risk-averse, less negatively reciprocal, more altruistic/positively reciprocal/trusting; cognitive ability positively associated with all six.

USA vs MEX contrast (the country-specificity test):

| dim | gender USA | gender MEX | age² USA | age² MEX |
|---|---|---|---|---|
| trust | **+0.387** | −0.018 | +0.007 | +0.012 |
| risktaking | −0.342 | −0.097 | +0.002 | −0.022 |
| altruism | +0.180 | +0.033 | −0.004 | −0.014 |
| negrecip | −0.293 | −0.133 | −0.006 | −0.013 |

**Key feature:** the USA trust gender gap (+0.39, women far more trusting) is *not present* in MEX (−0.02). If the USA adapter encodes USA-specific cultural structure, its persona-conditioned outputs should reproduce the USA trust gender gap and *not* the MEX pattern — a sharp, falsifiable test that does not name either country.

---

## 5. Stream B — WVS human facet gradients

**Estimator (per dimension d, per facet f, per country c ∈ {USA, MEX}):**

```
facet_f ~ β0 + β_sex·sex + β_age·age + β_age2·(age/10)² + β_educ·education + ε
```

- Facet scores: respondent-level, from the frozen `protocol.yaml` recipe (no changes).
- Demographics: Q260 (sex), Q262 (age), Q275 (education). Missing/DK masked per protocol.
- **Sign-agreement metric:** `sign(β_WVS) == sign(β_GPS)` per coefficient, with the *stable* gradients (gender on risktaking/altruism/posrecip/negrecip, math/education on all dims) as confirmatory and age-shape as exploratory (Falk documents cross-country heterogeneity in age profiles).

**Interpretation rules:**

- Sign agreement on the stable gradients = directional construct-validity evidence for that facet.
- Sign *disagreement* = the facet is not tracking the construct's demographic structure — same verdict as a failed `corr_min`, but at individual resolution.

---

## 6. The cell-mean design (the centerpiece)

Aggregate **both** samples to common demographic cells and correlate cell means *within country*. No matched individuals required; development confound removed by within-country demeaning.

**Cell definition (primary):** sex × age band (18–24, 25–34, 35–44, 45–54, 55–64, 65+) = 12 cells. Optional extension: × education tercile = 36 cells (requires education/cognitive comparability — see §9).

**For each country c with both GPS and WVS samples (USA, MEX, and any country in the WVS∪GPS overlap with min cell n ≥ 20):**

1. GPS side: cell means of each GPS dimension (weighted and unweighted).
2. WVS side: cell means of each facet (same recipe).
3. Correlation *across cells within country*: `corr(m_wvs_facet_cell_means, gps_dim_cell_means)`.
4. Pool across countries: country-demean the cell means, then pooled correlation (or country-FE partial correlation).

**Gates (DRAFT thresholds — Augusto owns):**

- Confirmatory (dimensions with non-empty country-level M*): trust facets and survivor composite, patience-financial, negrecip-justifiability.
  - Cell-level r ≥ 0.30 within-country (same bar as the country-level P1) **and** sign-consistent pooled correlation.
- Exploratory: risktaking/altruism/posrecip facets (country-level M* empty — the cell design asks whether individual resolution rescues them).
- Composite-of-survivors: repeat the trust survivor-composite test at cell level (country-level composite r = +0.41 vs GPS trust; the cell-level version is the stronger claim).

---

## 7. Stream C — adapter persona-conditioned gradients (new inference)

**Requires new inference; the existing `model_option_probabilities_*` files are unconditional and cannot answer this.**

**Prompt design (anti-leakage preserved):**

- No country names, no population labels — only demographics:
  `"You are a [35-year-old] [woman] with [some college education]. Answer the following survey questions as this person would."`
- Persona grid: sex (2) × age band (6) × education (3) = 36 personas per model.
- Same 35 WVS items, same option set, log-prob extraction, softmax → predicted option distribution (identical pipeline to the existing eval; `PROMPT_COUNTRY_CONDITIONING=False` stays).
- Determinism: temperature 0; repeat each persona × item k times (draft: 3) to bound persona-inference variance.

**Outputs per model (base, USA_adapter, MEX_adapter):**

- Persona-level facet scores (protocol recipe applied to predicted option probabilities).
- Gradient regressions identical in form to Stream B.
- Cell means on the same grid as §6.

**Comparison metrics (directional first, magnitude exploratory):**

| Metric | Question | Draft gate |
|---|---|---|
| Sign agreement (B↔C) | does the adapter reproduce the human facet gradients? | ≥ 4 of 6 stable coefficients agree in sign, per facet |
| Sign agreement (A↔C) | does the adapter reproduce GPS demographic structure? | USA trust gender gap reproduced by USA_adapter; not by MEX_adapter (sharp test) |
| Cell-level correlation (B↔C) | do adapter cell means track human cell means? | r ≥ 0.30 per facet |
| Magnitude recovery | | exploratory, appendix only |

---

## 8. Hypotheses (FROZEN 2026-08-05 — Stream C pre-registration)

**Freeze authority:** Augusto (task instruction 2026-08-05). Thresholds below are fixed before any Stream C inference. The freeze incorporates the cell-mean validation (§13): the **survivor composite** is the WVS-side reference; the **education gradient** and the **institution-trust gender gradient** are the confirmatory channels; trust-general gender is explicitly NOT a gate (country-heterogeneous per Falk & Hermle 2018).

- **H-Grad-1** (confirmatory, trust, **FROZEN**): the trust **survivor composite** reproduces GPS trust's stable demographic gradients in sign — education gradient positive (|z| ≥ 1.96, same sign as GPS), institution-trust gender gradient positive in USA (|z| ≥ 1.96). Reference: Stream B results (composite educ z = +7.6 pooled; institution gender z = +4.1 USA, +5.4 pooled).
- **H-Grad-2** (confirmatory, adapters, **FROZEN**): USA_adapter reproduces the USA trust gender gap (positive, |z| ≥ 1.96); MEX_adapter reproduces MEX's near-zero trust gender gap (|z| < 1.96). Sharp test: the two adapters must differ in the USA gender-gap direction.
- **H-Grad-3** (exploratory, not gated): individual resolution changes admissibility for risktaking/altruism/posrecip facets relative to the empty country-level M*.
- **H-Grad-4** (exploratory, not gated): patience-financial and negrecip-justifiability replicate at cell level.

**Frozen pre-registration items** (no changes after this date without a dated amendment): cell definition = sex × 6 age bands (18–24, 25–34, 35–44, 45–54, 55–64, 65+); min cell n = 20 respondents; min 6 cells/country; exclusions = missing sex/age, WVS negative codes, GPS missing dim; unweighted primary, GPS-`wgt`-weighted sensitivity; persona grid = sex (2) × age band (6) × education (3) = 36 personas; repetition = 3 per persona × item; sign-agreement metric = |z| ≥ 1.96 AND sign match; **WVS-side reference measure = `m_trust_survivor_composite`** (NOT Q57); gates = H-Grad-1 and H-Grad-2 as written above.

---

## 9. Known limitations and open items (Augusto decides)

1. **Gender coding in `individual_new.dta`** is 0/1 with overall mean 0.547; coding direction (0=male,1=female?) is inferred from sign consistency with Falk et al. but **must be verified against the GPS codebook** before any paper claim.
2. **Education (WVS Q275) vs cognitive skills (GPS `subj_math_skills`) are different constructs.** Use them only as same-sign human-capital gradients, never as identical cell dimensions. The primary cell design uses sex × age only.
3. **Cell-mean correlation is still ecological** (at cell, not person, level). It is *much* less confounded than country-level (within-country demeaning removes development), but it is not individual matching.
4. **Personas are approximations.** LLM persona conditioning is a known technique with validity limits (Argyle et al. 2023 lineage); report persona-repetition variance.
5. **Weights:** GPS `wgt` exists; WVS `W_WEIGHT` mean ≈ 1.0. Unweighted primary per SCA2 merge convention; weighted sensitivity appended.
6. **Thresholds:** 0.30 and the sign-agreement counts are drafts — Augusto owns them and they must be fixed before Stream C inference.
7. **New inference cost:** Stream C = 3 models × 36 personas × 35 items × 3 repeats ≈ 11k log-prob extractions — small relative to the original eval; no new training, no retraining of adapters.

---

## 10. Relation to existing prep pipeline

| Piece | Reuse | Change |
|---|---|---|
| `prep/protocol.yaml` | facet recipes | none |
| `build_country_scores.py` | normalization/direction/masking logic | add respondent-level gradient columns output |
| `prep/networks/*.yaml` | P1 criterion networks | not used directly; gates move to gradient/cell metrics |
| `sca2_validity` engine | slack/M*/range machinery | optionally reused: units = demographic cells, measures = facets, aux = GPS cell means, restriction = `corr_min` |

**Sequencing:** Stream A (already computed above) → Stream B (human gradients, no new data) → cell-mean design (no new inference) → Stream C last (persona inference), with thresholds frozen before Stream C runs.

---

## 11. Stream B results (computed 2026-08-05, local WVS wave 7)

**Implementation:** `sca2_validity/prep/build_wvs_gradients.py` → `data/validity/gradients_wvs.csv` + `gradients_wvs_summary.json`. Specification: OLS `facet ~ female + age/100 + (age/100)² + education(ISCED)`, USA/MEX single-country (HC1 SEs) and pooled all-countries with country-FE demeaning and country-clustered SEs (mirroring Falk et al. 2018 Table 5). Agreement requires |z| ≥ 1.96 **and** sign match; "✗" = significant opposite sign; "–" = no stable benchmark expectation.

### Headline findings

1. **Education (cognitive) gradient: the most reproducible channel.** The WVS facets significantly reproduce GPS's positive cognitive gradient for trust facets (all specs), patience-financial, negrecip-justifiability, and altruism-membership (USA). This is the strongest individual-level agreement with the GPS benchmark.

2. **Gender gradient: largely NOT reproduced — and one sharp reversal.** GPS: women more trusting (+0.066 pooled), less patient (−0.056), more altruistic/posrecip, less negrecip. WVS:
   - **trust-general (Q57) and out-group: significant NEGATIVE female coefficients in USA and pooled (z = −3.0, −5.6)** — the opposite of GPS trust's female gradient. Only **institution** trust reproduces it (USA z = +4.1; pooled z = +5.4). This is a substantive finding: GPS trust ("people have only the best intentions") and WVS generalized trust ("most people can be trusted") differ in their gender structure — direct evidence they are not interchangeable measures.
   - patience child-qualities: significant POSITIVE female (z = +3.3 USA) — opposite of GPS patience.
   - posrecip child-tolerance: significant NEGATIVE female (z = −5.5 USA, −9.4 pooled) — opposite of GPS posrecip.

3. **Age-shape test catches the financial-satisfaction-as-patience proxy.** GPS patience is hump-shaped (age +0.72, age² −1.45). WVS patience-financial (Q50) is **U-shaped** (age² +1.41, z = +7.3 USA): financial satisfaction rises with age — the *opposite* curvature. The country-level correlation (r = 0.43) passes, but the individual-level age structure fails.

4. **Risktaking facets fail every gradient** (female positive where GPS is negative; educ negative where GPS is positive), consistent with the empty country-level M* — the mapped economic-values items do not behave like GPS risk preferences at any resolution.

### Interpretation for the protocol

- The **education gradient** gives the facets real individual-level construct signal — worth keeping the trust facets + negrecip-justifiability + patience-financial as candidates.
- The **gender and age-shape failures** are diagnostic, not fatal: they identify *which channel* each facet does and does not share with the GPS construct. For the paper, Stream B supports: "WVS trust facets track GPS trust's cognitive gradient but not its gender gradient; GPS trust and WVS generalized trust are related but not equivalent."
- **Pre-registration implication:** the confirmatory gate should be the *education* gradient (stable, reproduced) and the *institution* trust facet's gender gradient; the gender-trust benchmark should be treated as country-heterogeneous (Falk et al.: women more trusting in only ~2/3 of countries, significant in ~1/3), so agreement on trust-general gender should NOT be a hard gate.

### Open items after Stream B

- Revisit protocol direction choices flagged `confidence: low` (Q13/Q14/Q43 patience; Q106/Q107/Q109 risktaking): Stream B shows risktaking facets with inverted education gradient, consistent with a direction or construct-mapping problem.
- Stream C persona inference is now well-specified: the adapter must reproduce the *education* gradients (testable) and the USA-specific institution-trust gender gradient (z = +4.1).
- Cell-mean design (§6) remains the no-new-inference next step using the existing respondent files.

---

## 12. Stream B extension — cross-country gender-gap alignment (trust)

**Implementation:** `sca2_validity/prep/trust_gender_gap_alignment.py`. For each of 42 countries with both WVS and GPS individual data: estimate the female coefficient on each WVS trust facet (controlling age, education) and on GPS trust (controlling age, math skills), then correlate these per-country gender gaps across countries.

| WVS measure | corr(gender gaps) | same-sign | USA (WVS, GPS) | MEX (WVS, GPS) |
|---|---|---|---|---|
| trust-general (Q57) | **+0.005** | 14/42 | (−0.059, +0.387) | (+0.011, −0.018) |
| trust-in-group | +0.466 | 24/42 | (−0.001, +0.387) | (0.000, −0.018) |
| trust-out-group | +0.580 | 24/42 | (+0.009, +0.387) | (−0.009, −0.018) |
| trust-institution | +0.276 | 27/42 | (+0.030, +0.387) | (+0.016, −0.018) |
| **survivor composite** | **+0.568** | 25/42 | (+0.013, +0.387) | (+0.002, −0.018) |

**Reading:**

1. **The single-item Q57 has ZERO demographic-structure alignment with GPS trust** (cross-country gender-gap correlation r = +0.005; same sign in only 14/42 countries). Country means correlate (r = 0.28 here, 0.49 in Falk et al.), but *who* is trusting within a country is structurally unrelated between the two instruments.
2. **USA is the sharpest divergence**: GPS says women are far more trusting (+0.387), WVS Q57 says women are less trusting (−0.059) — a sign flip in the largest English-speaking economy.
3. **Multi-item measures align.** out-group (r = +0.58) and the survivor composite (r = +0.57) reproduce GPS's cross-country gender structure; institution is weaker (r = +0.28).

**Economic-model implication (the headline):** the two instruments agree on *average* trust but disagree on *who* has it. Any economic model that interacts trust with gender, or uses demographic composition as a control or shifter, will obtain GPS-inconsistent trust×demographic effects when fed Q57 — the canonical WVS trust item used across the empirical literature. The survivor composite is the WVS measure that preserves both the country-level alignment (r = 0.41) and the demographic-structure alignment (r = 0.57). This is a second, independent channel on which the composite dominates the single item.

---

## 13. Cell-mean design results (computed 2026-08-05, local data)

**Implementation:** `sca2_validity/prep/cell_mean_design.py`. Units = sex × 6 age-band cells per country (min cell n = 20 respondents, min 6 cells/country, 42 countries). WVS cell means of trust facets + survivor composite vs GPS trust cell means; within-country correlation across cells; pooled via country-demeaning (removes the cross-country development confound); 2000-rep country-cluster bootstrap.

| measure | median r (within-country) | % countries r>0 | pooled r | 95% CI | P(> Q57) |
|---|---|---|---|---|---|
| trust-general (Q57) | +0.059 | 55% | **+0.087** | [−0.068, +0.216] | — |
| trust-in-group | +0.245 | 67% | +0.225 | [+0.131, +0.316] | — |
| trust-out-group | +0.183 | 64% | +0.304 | [+0.204, +0.381] | — |
| trust-institution | +0.206 | 76% | +0.254 | [+0.171, +0.333] | — |
| **survivor composite** | +0.229 | 71% | **+0.334** | [+0.234, +0.415] | **0.999** |

Sensitivity (GPS cell means weighted by `wgt`): composite pooled r = +0.302, CI [+0.214, +0.381]; Q57 r = +0.075, CI [−0.071, +0.204].

**Reading — the ecological-fallacy fork resolved:**

1. **The composite survives within-country demeaning** (pooled r = +0.334, CI excludes 0; robust to weighting). The country-level alignment is **not** purely development-driven: the composite tracks GPS trust's demographic structure *inside* countries, across sex and age cells. This is the strongest no-inference construct-validity evidence in the whole chain.
2. **Q57 alone does not** (pooled r = +0.087, CI crosses 0; only 55% of countries positive). The canonical single item has no within-country demographic alignment with GPS trust — consistent with the gender-gap finding (r = +0.005).
3. **Implication for Stream C:** the benchmark is now validated at cell level. Stream C gates should use the **survivor composite** (not Q57) as the WVS-side reference, with the education gradient and institution-trust gender gradient as the confirmatory channels. The composite is the measure that behaves like GPS trust at every resolution tested (country level r = 0.41; gender-gap r = 0.57; cell level r = 0.33).
