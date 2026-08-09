# Direction Audit — `confidence: low` (and bridge) WVS items

**Date:** 2026-08-04 (session)
**Status:** EVIDENCE + RECOMMENDATIONS ONLY — no protocol/score/committed artifact modified.
**Owner of any direction change:** Augusto (protocol.yaml polarity choices are user-owned; the freeze in `demographic_gradient_protocol.md` §8 stands untouched).
**Analysis script:** `/tmp/direction_audit.py` (this session; not committed — can be moved to `prep/` if it should be tracked). Evidence dump: `/tmp/direction_audit_evidence.json`.

---

## 1. Question

`protocol.yaml` flags 9 items as `confidence: low` (polarity not derivable from the construct map) plus 9 bridge items as secondary. Prior Stream A/B work (§11 of `demographic_gradient_protocol.md`) showed their facets FAIL the demographic-gradient test against GPS (Falk et al. 2018), e.g. risktaking facets with an inverted education gradient, patience work-values negatively correlated with GPS patience. Is that failure **(a)** a wrong direction coding, or **(b)** the items genuinely not tracking the GPS construct? This audit separates the two with data, per item, by computing **current-direction vs flipped-direction** versions of the two evidence tests.

## 2. Tests and gates

| Test | What | Gate | Implementation |
|---|---|---|---|
| **P1 (country level)** | Pearson r between the facet country mean and the GPS country z-score of the dimension (min 30 respondents/country, WVS∩GPS overlap n=41–42) | `r ≥ +0.30` (signed `corr_min` θ used in the P1 runs), p < 0.05 | `country_corr()` in audit script; **cross-validated against committed P1 runs**: slack + θ reproduces every committed r exactly (e.g. work_values −0.815+0.30 = −0.515; financial +0.132+0.30 = +0.432) |
| **Stream B (individual gradients)** | OLS `facet ~ female + age/100 + (age/100)² + educ` per spec (USA, MEX, pooled with country FE + country-clustered SEs); agree iff \|z\| ≥ 1.96 **and** sign matches GPS benchmark (female / educ / age² per `build_wvs_gradients.py:BENCHMARK_SIGNS`) | agreement count out of 9 benchmark-defined cells (3 specs × 3 gradients; altruism: 6 cells) | reuses `build_wvs_gradients.py` machinery; **reproduces committed `gradients_wvs.csv` to 2.2e-16** (all 16 facets × 3 specs × 4 coefficients) |

**Flip definition:** only the audited item's direction is negated; other items in the facet keep protocol directions. For single-item facets the flip is exact (facet → 1 − facet).

## 3. Evidence table (required)

| item | dim (facet) | current dir | country r current → flipped | grad agree current → flipped | verdict |
|---|---|---|---|---|---|
| **Q43** | patience (work_values) | +1 | **−0.515** (p=0.0001) → **+0.515** (p=0.0001) | 0/9 → 2/9 | **AMBIGUOUS** — P1 strongly favors flip; gradients don't corroborate |
| **Q50** | patience (financial) | +1 | **+0.432** (p=0.002) → −0.432 | 3/9 → 2/9 | **current confirmed** (both tests favor current; admissible facet) |
| **Q106** | risktaking (economic_values) | +1 | −0.069 → −0.034 | 0/9 → 0/9 | **non-aligned** |
| **Q107** | risktaking (economic_values) | +1 | −0.069 → +0.029 | 0/9 → 1/9 | **non-aligned** |
| **Q109** | risktaking (economic_values) | +1 | −0.069 → −0.053 | 0/9 → **5/9** (flip) | **AMBIGUOUS** — flip aligns gender gradient everywhere (USA/MEX/pooled) + educ (MEX/pooled); P1 stays negative |
| **Q178** | risktaking (rule_breaking) | +1 | +0.011 → −0.011 | 1/9 → **5/9** (flip) | **AMBIGUOUS** — flip aligns educ gradient in all 3 specs + age² USA/MEX; P1 ~ 0 both ways |
| **Q176** | negrecip (moral_clarity) | +1 | +0.074 → −0.074 | 3/9 → 0/9 | **non-aligned** (current weakly better) |
| **Q195** | negrecip (punitiveness) | +1 | +0.083 → −0.083 | 4/9 → 1/9 | **non-aligned** (current better; fails P1) |
| **Q174** ⚠ | posrecip (religion) | +1 | −0.069 → +0.069 | 2/9 → 0/9 | **non-aligned** |
| Q13 | patience (child_qualities) | +1 | −0.258 → −0.058 | 0/9 → 0/9 | non-aligned (bridge) |
| Q14 | patience (child_qualities) | +1 | −0.258 → +0.058 | 0/9 → 4/9 (flip) | ambiguous (bridge) |
| Q12 | posrecip (child_tolerance) | +1 | +0.044 → −0.044 | 0/9 → **5/9** (flip) | ambiguous (bridge) — flip aligns female everywhere |
| Q81 | posrecip (charitable_confidence) | −1 | +0.069 → −0.069 | 2/9 → 1/9 | non-aligned (bridge) |
| Q177 | negrecip (justifiability) | −1 | **+0.361** (p=0.014) → −0.403 | 4/9 → 1/9 | **current confirmed** (admissible facet; direction NOT inverted) |
| Q179 | negrecip (justifiability) | −1 | **+0.361** (p=0.014) → **+0.403** (p=0.005) | 4/9 → 3/9 | **current confirmed** (both pass P1; current slightly better) |
| Q99 | altruism (membership) | +1 | −0.047 → +0.016 | 2/6 → 2/6 | non-aligned (bridge) |
| Q101 | altruism (membership) | +1 | −0.047 → −0.173 | 2/6 → 0/6 | non-aligned (bridge) |
| Q103 | altruism (membership) | +1 | −0.047 → +0.061 | 2/6 → 2/6 | non-aligned (bridge) |

⚠ **Q174** is `confidence: low` in `protocol.yaml` (posrecip/religion) but was not in the task's enumerated list — included here for completeness.

**Verdict rules applied** (per task): flipped direction making **both** P1 positive/significant **and** gradients align → coding error; **neither** direction aligning → item does not track the GPS construct; only one test improving → ambiguous, defer to researcher.

## 4. Recommended action per item

### No definitive flip recommendation
No item satisfies both criteria simultaneously (flip → P1 positive/significant **and** gradients align). **There is no item for which the flipped direction is a confirmed coding error.**

### Construct-non-aligned — keep out of the menu (or document as non-admissible)
- **Q106, Q107** (risktaking/economic_values): P1 negative or ≈0 in both directions (r ∈ [−0.07, +0.03]); gradients ≤ 1/9. These two items do not track GPS risk preferences at any resolution.
- **Q176** (negrecip/moral_clarity), **Q195** (negrecip/punitiveness): P1 fails both directions (|r| ≤ 0.083); current direction is better on gradients (3/9, 4/9) but still weak. Note Q195-current is the best-behaved low-confidence negrecip item (reproduces GPS negrecip female z=−7.42 pooled and age² z=−3.06 pooled) — real partial construct signal, but fails the country-level gate.
- **Q174** (posrecip/religion): P1 fails both ways; gradients 2/9 → 0/9.
- Bridge: **Q13, Q81, Q99, Q101, Q103** — no direction rescues them.

### Current direction confirmed — do NOT flip
- **Q50** (patience/financial): current P1 = +0.432 (p=0.002, passes) and education gradient aligns in all 3 specs (pooled z = +11.06); flipped fails both. This is the admissible patience facet — **"direction TBD" resolved: +1 stays**.
- **Q177, Q179** (negrecip/justifiability): current P1 = +0.361 (p=0.014, passes), education gradient aligns everywhere (pooled z = +5.78); flipping the facet destroys both (all-flip: P1 −0.361, 2/9). The admissible negrecip facet is directionally correct.
- Facet-level: `justifiability_ALL` flip worsens both tests — no facet-level flip for negrecip-justifiability.

### Ambiguous — defer to Augusto (leaning noted)
- **Q43** (patience/work_values): flipping turns the country-level correlation from **−0.515 (p=0.0001, strongly significant NEGATIVE)** to **+0.515 (p=0.0001, strongly positive)** — the single most decisive P1 swing in the audit and exactly the "work-values negative where GPS patience positive" anomaly from §11. But Stream B does not corroborate: 0/9 → 2/9 (only USA-educ and pooled-age² align under flip). **Lean: if this item is used at all, flip it** (the current direction makes the facet significantly negatively correlated with GPS patience, which is hard to defend as a measurement of patience); but it is not a Stream-B-validated measure either way.
- **Q109** (risktaking/economic_values): flip aligns the gender gradient in all 3 specs + education in MEX/pooled (5/9) — the strongest gradient pattern of any risktaking item — and the flipped mapping is also the semantically sensible one ("competition is good → risk-tolerant"; current maps "competition harmful → more risk-taking"). But P1 stays negative (−0.053). **Lean: flip if the item stays in the menu; keep out of the menu otherwise.**
- **Q178** (risktaking/rule_breaking): flip aligns the education gradient everywhere (5/9) but P1 ≈ 0 both ways. Semantically the current direction is defensible ("fare evasion justifiable → more risk-taking"), so a direction error here is less plausible; the gradient pattern under flip may reflect education/income confounds on rule-breaking attitudes.
- Bridge: **Q14** (gradients 0 → 4 flipped, P1 still fails), **Q12** (gradients 0 → 5 flipped — female aligns everywhere — but P1 flips +0.044 → −0.044).

### Facet-level all-flip variants (facets whose items are all audited)
| facet | P1 current → all-flipped | grad current → all-flipped | reading |
|---|---|---|---|
| risktaking/economic_values | −0.069 → +0.069 | 0/9 → 4/9 | flip improves gradients, P1 fails both — ambiguous at facet level |
| patience/child_qualities | −0.258 → +0.258 | 0/9 → 4/9 | same pattern — ambiguous at facet level |
| negrecip/justifiability | +0.361 → −0.361 | 4/9 → 2/9 | **current confirmed — do NOT flip the facet** |
| altruism/membership | −0.047 → +0.047 | 2/6 → 1/6 | non-aligned |

## 5. Stream C gate check (frozen pre-registration, `demographic_gradient_protocol.md` §8)

- **Survivor composite** (`m_trust_survivor_composite`, the frozen WVS-side reference) = mean of `in_group` + `out_group` + `institution` facets (definition in `trust_gender_gap_alignment.py:82-84`) = items **Q58, Q60, Q59, Q61, Q62, Q63, Q64, Q69, Q70, Q71, Q73** — **all `confidence: clean`** (verified programmatically: zero non-clean items in any trust facet).
- **No low-confidence item enters the trust composite.** The 9 low-confidence items (Q43, Q50, Q106, Q107, Q109, Q174, Q176, Q178, Q195) all live in patience/risktaking/negrecip/posrecip facets only.
- **Conclusion: flipping any audited item does NOT change any frozen Stream C gate.** H-Grad-1 (composite education gradient |z| ≥ 1.96; institution-trust gender gradient USA |z| ≥ 1.96) and H-Grad-2 (adapter USA trust gender gap) are computed entirely from trust items.
- **One caveat for scheduling:** Stream C persona inference scores all dimensions, so the exploratory channels (H-Grad-3 risktaking/altruism/posrecip; H-Grad-4 patience-financial, negrecip-justifiability) inherit whatever directions are in `protocol.yaml` at inference time. This audit finds no item that must be flipped before Stream C; but Augusto should disposition the ambiguous items (Q43, Q109, Q178, Q12, Q14) before inference if the exploratory channels are to be interpreted.

## 6. Consistency with prior documentation (honesty check)

- **§11 "risktaking facets fail every gradient (female positive where GPS is negative; educ negative where GPS is positive)" — reproduced exactly**: current-direction pooled economic_values female z = +5.70 (GPS expects −), educ z = −1.98 (GPS expects +); rule_breaking educ z = −4.08 (significantly inverted). This holds for the **current** directions only; under flipped Q109/Q178 the gradient picture improves (5/9) — i.e. §11's "fail every gradient" is direction-contingent.
- **§11 "patience work-values negative where GPS patience is positive"** — confirmed at country level (r = −0.515, p = 0.0001); the education gradient under the current direction is negative but not significant (pooled z = −0.92).
- **§11 "financial-satisfaction (Q50) U-shaped (age² +1.41, z = +7.3 USA)"** — reproduced: USA age² = +1.41 (z = +7.3) and pooled age² z = +8.35 under the current direction. This age-curvature failure is a property of the Q50 item itself, not of its direction (flipping inverts it to the correct hump sign but destroys the education gradient and P1 — see §4).
- **No committed artifact was modified.** `protocol.yaml`, `scores_*.csv`, `gradients_wvs*.csv`, P1 run profiles, and the Stream C freeze (§8) are untouched.

## 7. Bottom line

1. **No item gets a definitive flip recommendation** — no flipped direction simultaneously makes the country-level correlation positive/significant **and** aligns the demographic gradients.
2. **Definitive non-alignment (construct, not coding):** Q106, Q107, Q176, Q195, Q174 (low-confidence) + Q13, Q81, Q99, Q101, Q103 (bridge) — keep out of the menu or document as non-admissible; their failure is not a polarity problem.
3. **Directions confirmed (do not flip):** Q50, Q177, Q179 — the two admissible non-trust facets are correctly coded.
4. **Ambiguous, defer to Augusto:** Q43 (strong P1 case for flip, no gradient corroboration), Q109 and Q178 (strong gradient case for flip, P1 unresolvable), Q12 and Q14 (bridge).
5. **Stream C gates are immune** — the frozen survivor composite contains only `confidence: clean` trust items.
