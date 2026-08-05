# SCA2 Evaluation & Validity Audit — Honest-Reporting Review

**Status:** AUDIT DRAFT (2026-08-05) — for Augusto's review before any paper use.
**Scope:** committed `DPO_eval_WVS/` results + untracked `sca2_validity/` + Stream A/B work in `demographic_gradient_protocol.md`.
**Method:** re-verified all headline numbers against committed CSVs; audited causal wording; checked reproducibility hashes; bootstrapped key contrasts. No new inference was run.
**Ownership:** Augusto owns every interpretation and claim; this document only reports what the data and design do and do not support.

---

## 1. Verdict summary

| Area | Verdict |
|---|---|
| Headline numbers (97.1%, 11.4%, TVD/JSD table, dispersion range) | ✅ **All accurate transcriptions** of committed CSVs |
| "35 unseen WVS questions mapped to 6 GPS dimensions" (README root + DPO README) | ⚠️ **Misleading**: only 30 questions have GPS mappings; 5 are demographic items (Q260/Q261/Q262/Q275/Q288) |
| "because Llama-3.1-8B already carries a heavy US pretraining prior" (DPO README) | ⚠️ **Not testable from this design** — wording overstates mechanism |
| "Mexico Specificity Success" framing | ⚠️ **Overstated** — see §4; "matched vs cross" ≠ evidence of country-conditioned behavior |
| Reproducibility of validity layer | ✅ protocol/scores/network hashes all match committed inputs |
| Gender-gap contrast (Q57 vs composite) | ✅ robust under bootstrap (P = 0.999) |

---

## 2. Number verification (all re-computed from committed CSVs)

| Claim | Committed value | Re-verified |
|---|---|---|
| MEX matched-beats-cross on 97.1% of questions | 0.971429 | ✅ 34/35 questions |
| USA matched-beats-cross on 11.4% | 0.114286 | ✅ 4/35 questions |
| ΔTVD MEX = 0.1495 [0.0964, 0.2152] | summary CSV | ✅ exact |
| MEX matched TVD 0.4882; USA cross 0.6377; USA matched 0.5258; base USA 0.3958 | README table | ✅ exact |
| Dispersion bias −1.15 to −1.63 | README | ✅ committed range: −1.634 to −1.155 |
| USA adapter degrades vs base (TVD) | −0.130 (USA), −0.117 (MEX) | ✅ both cells |
| MEX adapter vs base | +0.033 (MEX), +0.007 (USA) | ✅ both cells (USA cell ≈ 0, CI crosses 0) |

**Reproducibility hashes** (validity layer): protocol hash `7a4a42bd…` recomputes identical from `prep/protocol.yaml`; run `profile.json` protocol/scores/network hashes match committed inputs exactly.

---

## 3. Finding A — "35 mapped questions" is wrong; it's 30 + 5 demographics

Committed truth (`question_map_wvs_edited.csv`): 35 questions total, **30 with GPS-dimension mappings** (trust 12, patience 4, risktaking 4, negrecip 4, posrecip 3, altruism 3), **5 unmapped** — Q260 (sex), Q261 (birth year), Q262 (age), Q275 (education), Q288 (income).

Both READMEs say "35 unseen WVS questions mapped to 6 GPS preference dimensions." The 5 demographic items are in the eval but have no `gps_dimension` (they appear under `Unspecified` in the by-dimension tables).

**Fix:** say "35 unseen WVS Wave 7 items (30 mapped to the six GPS dimensions, 5 demographics)".

---

## 4. Finding B — the specificity framing overstates what the design can show

The most important audit result, combining three facts:

1. **Model probabilities are identical across eval countries** (verified: for each model, `model_option_probabilities_<m>_on_USA.csv` and `_on_MEX.csv` differ only in the `eval_country` label; every probability matches to 0.0). This follows from `PROMPT_COUNTRY_CONDITIONING = False` — prompts never name a country.
2. Therefore "matched vs cross" differences come **entirely from the population distributions** (USA vs MEX WVS responses), not from the model producing country-specific answers.
3. The committed tables are internally consistent with this: the same model scores differently against USA vs MEX *because the target distribution differs*, not because its output changed.

**What the numbers honestly support:**

- "The MEX adapter's fixed output distribution is closer to Mexico's actual WVS responses than the USA adapter's is (97.1% of items)." ✅
- "The USA adapter's fixed output distribution is closer to Mexico's responses than to the US's own responses" — i.e., the USA adapter shifted *away* from USA WVS response patterns (TVD 0.526 vs base 0.396). ✅
- "The MEX adapter's distribution is closer to MEX responses than the base model's (TVD 0.488 vs 0.521), and approximately neutral on USA responses (+0.007, CI crosses 0)." ✅

**What the wording "Mexico specificity success" implies but the design cannot show:**

- That the adapter *conditions on* or *knows* its target country at inference. It cannot: no country token is ever shown, and its outputs are identical across eval countries.
- That matched-vs-cross measures adapter country-specificity. It measures, instead, which adapter's **single fixed** distribution happens to sit closer to each country's observed response pattern.

**Fix for the paper:** replace "specificity" language with "distributional alignment" or "fixed-output proximity":
> "On Mexico's WVS items, the MEX adapter's predicted response distribution lies closer to Mexico's observed response distribution than the USA adapter's does (97.1% of items, ΔTVD 0.15). The USA adapter, by contrast, sits farther from US responses than the base model — its fine-tuning shifted its WVS-style responses away from US response patterns."

This keeps every number, drops the untestable mechanism.

---

## 5. Finding C — "because Llama already carries a heavy US pretraining prior" is not established

The DPO README says the USA adapter degrades "because Llama-3.1-8B already carries a heavy US pretraining prior." This is a plausible story, but the design cannot test it:

- The committed data show the **USA adapter degrades on BOTH eval countries** (−0.130 USA, −0.117 MEX) — not just where a "US prior" would bite hardest.
- A "prior collision" account would predict the degradation concentrated on US data; the data show a general shift away from WVS-style response distributions.
- Competing explanations (adapter overfitting to the synthetic scenario format, distribution shift in option-scoring, insufficient US-pair diversity) are equally consistent.

**Fix:** report the degradation as a measured fact (both cells negative, CIs excluding 0), and list mechanism candidates as *unresolved*, not as the explanation. The `sca2_validity` adapter pilot exists precisely to test whether the adapters encode country structure — that is the right place for the mechanism question, and Stream C (persona gradients) is the designed test.

---

## 6. Finding D — validity layer is reproducible; Stream A/B results hold up

- **Hashes:** protocol/scores/network all match committed inputs (verified above).
- **Stream A (GPS benchmark):** pooled gender/cognitive coefficients match Falk et al. 2018 Table 5 signs on all six dimensions; gender coding (1 = female) confirmed against the published table.
- **Stream B (WVS gradients):** education gradient reproduced for trust facets + patience-financial + negrecip-justifiability; gender gradient largely fails (Q57/out-group negative where GPS is positive); age-shape catches Q50-as-patience (U vs hump).
- **Gender-gap extension (Stream B §12):** the Q57-vs-composite contrast is **robust**: country-cluster bootstrap (2000 reps) gives Q57 r = +0.005, 95% CI [−0.35, +0.33]; composite r = +0.568, 95% CI [+0.40, +0.70]; P(composite > Q57) = 0.999. The claim "single-item Q57 has no demographic-structure alignment with GPS trust; the composite does" survives resampling.
- **Caveat (honest):** institution trust's gender-gap correlation is weaker (r = +0.276, CI [−0.03, +0.52]) — treat it as suggestive, not established.

---

## 7. Recommendations — disposition (2026-08-05)

| # | Recommendation | Status |
|---|---|---|
| 1 | Fix "35 mapped" → "30 mapped + 5 demographics" (root README, DPO README) | ✅ **Done** — 4 occurrences updated |
| 2 | Rewrite causal/specificity claims (root README findings + scope, DPO README takeaways) | ✅ **Done** — "specificity" → "distributional alignment"; "because pretraining prior" → mechanism-unidentified wording; table column renamed "Matched vs Cross (% Matched Better)" |
| 3 | Add design-limitation note to DPO README | ✅ **Done** — blockquote added to both READMEs |
| 4 | Keep validity layer as construct-validity home | ✅ no change needed (already honest) |
| 5 | Freeze Stream C gates | ✅ **Done 2026-08-05** — §8 rewritten as FROZEN pre-registration: survivor composite = WVS-side reference (not Q57); education + institution-trust gender = confirmatory channels; trust-general gender NOT a gate; persona grid/repetitions/sign-agreement metric fixed. |
| 6 | Cell-mean design | ✅ **Done 2026-08-05** — trust only (confirmatory): composite survives within-country demeaning (pooled r = +0.334, CI [+0.234, +0.415], P(>Q57) = 0.999); Q57 does not (r = +0.087, CI crosses 0). See protocol §13. Other dimensions exploratory pending direction fixes. |

**Note:** the committed CSV `survey_matched_vs_cross_specificity_summary.csv` keeps its name (renaming a tracked artifact is a separate decision); its *content* and the READMEs that cite it now use aligned wording.

---

## 8. What was NOT audited (open)

- The synthetic generation pipeline (`synthetic_generation/`) and DPO training (`DPO_train_test/`) — outside the validity/eval scope of this audit.
- AmericasBarometer eval surfaces (not in `DPO_eval_WVS`; separate tier-2 workflow).
- Persona-inference (Stream C) — intentionally not run (no new inference per instruction).
