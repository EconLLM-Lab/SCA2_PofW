# Presenter's notes — 16 September 2026

Read these paragraphs out loud if you are tired. Skip anything in `[brackets]`. Appendix is slides 21–24; do not walk it unless asked.

**Time.** About 20 minutes of talking, then discussion. You do not need 30. If you are late: skip 8, do not read the equation on 9, skip 17, go 16 → 18.

**Expansions, once.** GPS = Global Preferences Survey (Falk et al. 2018). WVS = World Values Survey Wave 7. DPO = Direct Preference Optimization. QLoRA = quantized low-rank adapters on Llama 3.1 8B Instruct.

**Do not say.** We recovered culture. We identified a GPS coordinate. We wiped the model's priors. We showed pre-piloting saves money. The assignment permutation is a sign-retrain. Zero Spearman means different constructs.

---

## Crib sheet

| Thing | Number |
|---|---|
| Countries / distinct sign profiles | 16 / 13 |
| Shared pair bank | 658 (train 526, holdout 132) |
| Twins | MEX=RUS, IND=GRC, IDN=EGY |
| USA labels | 658/658 chosen A |
| Mexico labels | 658/658 chosen B |
| Argentina labels | 328 A, 330 B |
| Selector vs sign (USA/MEX) | 1,314 / 1,316 (99.85%) |
| DPO | β = 0.1, rank 16, one epoch |
| Encoding | recovery 0.942, accuracy 0.819, 2,112 cells |
| Trust adapter–GPS | **0.80** [0.55, 0.93] |
| Trust persona–GPS | −0.07 [−0.55, 0.45] |
| Trust adapter−persona | 0.87 [0.22, 1.36] |
| Trust adapter–human | 0.33 [−0.23, 0.74] |
| Trust human–GPS | 0.39 [−0.18, 0.79] |
| Q57 human–GPS (this panel) | 0.15 |
| Risk adapter–human | 0, interval [−0.48, 0.51] |
| Patience human–GPS | Q43 −0.56; Q50 +0.62 |
| 2×2 trust–GPS / TVD | adapter uncond. 0.80 / 0.480; persona base −0.07 / 0.369 |
| Assignment placebo | p = 0.002, adapters **not** refit |
| Egypt robustness | adapter–GPS trust 0.79–0.81 |
| Eval surface | 23 items, 368 country–item TVD cells |

---

## 1. Title

Thank you for coming. This is a working-paper discussion. I am Augusto, with Kseniia Biriukova and Monica Capra.

The question on the slide is the one to keep in view: can a sign-labeled adapter score a new survey item? I will go background, problems and scope, questions, methods from the anchors through fitting, evaluation and results, then what I think the contributions are, then what we should run before a journal version. I want criticism, including from people who have not been living inside this.

---

## 2. Background

SCA 1.0 used cultural descriptions and persona-style prompting. We compared synthetic play to published tables from small-scale society experiments. That is the Henrich-style table comparison. It is **not** the data in this paper.

This draft changes the supplied information. Public GPS country scores become **sign labels** on a **shared** synthetic pair bank. We fit one joint adapter per country. Evaluation prompts omit country names.

The lineage is simulation, then an inspectable construction. I cannot claim we have identified a preference parameter.

---

## 3. How much can simulation do on its own?

This is the anxiety. How far can we get with simulation alone.

Human observations remain necessary. The live question is how many, and for what. Prompted synthetic respondents mix what we typed with what the model already associates with a country name. That is fine for exploration. It is a weak basis for claiming that an item tracks a preference across populations.

A human pilot is still the measurement step. This instrument is a cheap preliminary readout. Whether it helps item selection is untested.

---

## 4. Problems documented, and the scope of this draft

Problems we are answering: too many free knobs at prompt time; construct validity hard to audit; most uses are about **groups** while LLM-generated microdata are poorly understood; human microdata are expensive; persona prompts invite stereotyping.

**Scope of this draft:** synthetic comparisons; population-moment anchors; one DPO adapter per group with QLoRA, as a regularized Bradley–Terry pairwise choice fit.

**Application:** transport between GPS anchors and WVS item text, against a country-named prompt. Keep this in mind: can the adapters score new survey items?

[If someone asks novelty: CultureLLM, Cao, SubPOP, Jung and Kim already do cultural fine-tuning or DPO. We are not claiming first. The narrower object is economic-preference **signs**, a **shared** bank, adapters, scoring on a **separate** instrument without naming the country.]

---

## 5. Main research questions

Three questions this draft can speak to.

**1 Construction.** Can we write an inspectable map from declared aggregate signs, through a shared pair bank, to a fitted scoring policy?

**2 Transport.** On held-out WVS text, with no country name, do those policies retain GPS country order?

**3 Agreement.** Do they match WVS country orderings, and does that depend on the proposed item map?

[If someone asks about compiler identification: that is whether differences across policies are a function of the assigned sign vector alone. It needs a second bank or a sign-retrain. It is not a claim of this draft.]

---

## 6. From anchors to a synthetic dataset

Let \(z\) be six population moments: trust, risk, patience, altruism, positive reciprocity, negative reciprocity. A labeling map sends \(z\) to a dataset of scenarios and two opposing responses. The plus text is written to load high on a target facet; the minus text to load low. Those loadings are **generator judgments**, not lab manipulations.

This application cares about country **order**, so production uses only the **sign** of each coordinate. Chosen is A if that coordinate is at least zero, B otherwise.

Magnitudes are not wasted. They are the GPS **ranking** in the Spearman. They do not weight the DPO pairs. An intensity-weighted protocol would be a different paper.

---

## 7. A sign profile is the construction unit — **pause**

Argentina is minus, plus, minus, plus, plus, minus, in the order trust, risk, patience, altruism, posrecip, negrecip.

The United States is non-negative on all six, so **every** pair is chosen A. Mexico is negative on all six, so **every** pair is chosen B. That is a global polarity flip of the **same** 658 scenarios. It is not six independent trait contrasts.

Sixteen countries, thirteen distinct sign profiles. Twins share a labeling problem: Mexico with Russia, India with Greece, Indonesia with Egypt.

**Pause:** How should we use the twins as a robustness check?

[If quiet: if two adapters with the same signs diverge on WVS, the policy is not a function of the sign vector alone. Unrun. That is open question 3.]

---

## 8. We replaced an LLM selector with the sign rule

[Skip if you are already long.]

The teacher and generator still write the shared A/B bank. An early path asked a second model to pick A or B given a prose profile. That selector was **told** that sign sets the direction. On USA–Mexico it matched the sign rule on 1,314 of 1,316 labels. Two misses: Mexico patience at \(z = -0.11\).

We stopped paying a model to re-implement a declared rule with noise. Cost of the 76-country relabel dropping to zero was a side effect. Profile prose is unused in production. The 16 adapters train on \(\mathrm{sign}(z)\) only.

---

## 9. DPO fits the labeled contests

[Do not read the equation unless someone asks. Say the English.]

The loss raises the **chosen** text over the **rejected** text, **relative to Llama**. There is an extra constant that depends only on the scenario. It cancels in a pairwise contest. DPO never sees “how good is this scenario.” It sees “how much more does this policy like A than B, compared with the base model.”

That probability is **not** the chance of generating the whole paragraph. That number is tiny. It is **not** the WVS code softmax. It is: if you put these two texts on the table, what is the logistic probability that chosen wins.

USA: 658 of 658 chosen A. Mexico: all B. The loss pushes that contest probability toward 1 as a **global polarity**. Argentina is mixed: 328 A and 330 B, by target dimension. One joint adapter has to implement that patchwork. Prefer A on risk/altruism/posrecip slices; prefer B on trust/patience/negrecip slices.

[If they ask “feature or bug?”: feature of a six-sign compiler. Bug if you read the trust bar as an isolated trust-bit effect.]

---

## 10. We fit the whole bank jointly

All six signs enter the same QLoRA. A movement on trust items is not an isolated trust-bit effect. Countries that differ on GPS trust also differ on other signs. Pairs load off-target facets.

What we **can** report is dimension-specific **transport**: on a named WVS map, do policy country ranks track that GPS \(z\). What we **cannot** report is a ceteris paribus effect of one coordinate. That would need per-dimension adapters, or a sign-retrain that flips only trust.

We kept Llama 3.1 8B because prompted survey simulation is known to be weak there. The test is whether a weight-embedded sign rule survives where a country name in the prompt is a poor instrument.

---

## 11. Evaluation surface

Sixteen countries, twenty-three single-choice WVS items, same recodes and aggregation across arms. Egypt was not asked Q69–Q71; Britain was not asked Q174; those items are out **everywhere**. Patience is two items we refuse to pool.

Readout: teacher-forced log probability of each **option code**, leading space included, softmax over the supplied codes only. No sampled answer. No country name in the primary prompt.

That softmax is a scoring convention. Its spread is not how dispersed people are.

---

## 12. Three questions, one matched panel

**Gold line**, adapter to GPS: **retention**. Does the policy keep GPS country order on new text.

**Left**, humans to GPS: **coherence** of this WVS map with GPS.

**Bottom**, adapter to humans: **agreement** with people.

A country-named persona is a comparator. It does **not** receive the sign vector. Naming Argentina is a different information set.

Held-out synthetic pairs ask a prior question: did fitting recover the labels we imposed.

Two of these correlations being large does not prove a shared construct.

---

## 13. Fitting recovers the imposed labels — **pause**

Relative-reward recovery **0.942**: the chosen-versus-rejected margin improved over Llama. Raw choice accuracy **0.819**: the adapter itself ranks chosen above rejected. 2,112 held-out country–pair cells. Russia has a different 132-pair holdout that overlaps 26 prompts, so pooled precision is a little flattering.

This supports recovery of **synthetic** contrasts. It does not measure prediction of human choices.

**Pause:** What independent test would make this more than a training metric?

[If quiet: a new bank with the same sign rule, or human pairwise judgments.]

---

## 14. Anchor retention and human agreement differ — **pause**

This is Figure 2. Four series, different questions. GPS is the survey, not a model.

Look at trust on the left. Adapter–GPS is high. Human agreement is much weaker. On risk, adapter–human has **height zero**. That is a sample Spearman of exactly zero, not missing data. Patience is omitted here because the two items disagree; they are on the next slide.

Whiskers are 95 percent **country** bootstrap, 2,000 draws. They omit respondent sampling, GPS measurement error, and training seeds.

**Pause:** Which association should carry the paper's main empirical claim?

[My answer: adapter–GPS on trust, as order-retention, with human agreement unresolved.]

---

## 15. Trust retains GPS order; human agreement is uncertain — **pause**

Adapter–GPS **0.80**, interval 0.55 to 0.93. Persona–GPS **minus 0.07**. Paired difference **0.87**, interval 0.22 to 1.36. On this panel the unconditioned adapter retains GPS trust ordering. The country-named prompt does not.

Adapter–human **0.33**, interval minus 0.23 to 0.74. That includes zero. Human agreement is unresolved. I will not interpret 0.80 times 0.39 as a mechanism for 0.33.

We shuffled GPS trust \(z\) across **frozen** adapter scores, without refitting. One-sided **p = 0.002**. That is an **assignment** placebo. Probabilities did not move. It is **not** a sign-retrain.

**Pause:** Is order-retention on this trust map enough for the contribution?

---

## 16. A zero on risk does not settle the construct — **pause**

Sixteen countries. Adapter–human risk Spearman is 0. The interval is **minus 0.48 to plus 0.51**. We have not shown the population correlation is near zero.

Even a true zero **rank covariance of these country scores** would not be independence of the response distributions, and it would not be discriminant validity. Discriminant validity is a **pattern**. One zero on one messy map can be a bad item, GPS noise, ecology, or a policy that does not track people.

Patience: Q43, less importance of work, human–GPS **minus 0.56**. Q50, financial satisfaction, **plus 0.62**. We kept the original coding. We did not flip after seeing the sign. We do not treat their average as a validated patience measure.

**Pause:** What evidence would separate a bad map from a policy that does not track people?

---

## 17. Order and shape need not favor the same configuration

[Skip if you are past 18 minutes.]

Same 23 items. Unconditioned adapter: trust–GPS **0.80**, mean TVD **0.480**. Country-named base: **minus 0.07** and TVD **0.369**. The configuration that keeps GPS order is **farthest** from human response distributions.

This is why we refuse to collapse the paper into “the adapter wins” or “prompting wins.” Better depends on the metric.

On risk, adding a country name changes adapter–GPS from 0.57 to **minus 0.26**. These cells are configuration sensitivity. Adding a country name changes **information and route**. We have not given the prompt the same signs the adapter received.

---

## 18. Main contributions of this draft

After the evidence, three contributions.

**1** An inspectable construction: public GPS signs label a shared pair bank; one joint QLoRA-DPO adapter; country-unconditioned scoring.

**2** An evaluation that keeps recovery, GPS-order transport, and human agreement as **separate** targets, with a persona comparator on the same items.

**3** On this trust map, unconditioned adapters retain GPS country order more strongly than naming the country. Human ranks and distributional closeness remain unresolved and **metric-dependent**.

The object is a scoring instrument for group-level item screening. Independent human validation is still required. We have not identified \(z\), a single coordinate, or culture.

---

## 19. Open questions before a journal version — **pause**

What we would run next, **in this order**. No new human labels.

**1** Second scenario bank, same GPS signs, refit two adapters. One all-positive, one mixed or all-negative, is already informative. If WVS orderings die when the bank changes, the object is bank-specific.

**2** Sign-retrain. Permute the sixteen sign vectors, relabel, **refit**. The permutation in the draft does not refit.

**3** Twin-profile exchangeability on held-out WVS. Mexico versus Russia.

More countries on **this** bank is later. A blinded human item-screening study is a **use-test**.

**Pause:** If we can only run one of these before submission, which one?

[If quiet: I would run the second bank first.]

---

## 20. What would you need to see before using this?

I am going to stop.

We can inspect the labeling rule and observe trust-order transfer on this panel. Human agreement and practical pre-pilot value remain unresolved.

I would like people who have not been in the lab first.

Which part of the construction is least credible?

What evidence would change your view of the proposed use?

Which extension should we run first?

---

# Appendix — only if asked

“I parked four appendix slides. Tell me which one you want.”

## 21. Complete pair

Look at whether A and B differ only on positive reciprocity. I think they also differ on time pressure and duty. Mixed-trait bank. Sign labels are still well-defined.

## 22. WVS map

Candidate bridges. Q57 human–GPS in this panel is **0.15**. The trust composite is doing work, and it mixes interpersonal and institutional items.

## 23. Code scoring

Leading space, softmax over supplied codes. Scoring convention. Not the DPO contest probability.

## 24. Uncertainty

Country bootstrap only. Egypt stays. Restoring Q69–Q71 on the other fifteen leaves adapter–GPS trust **0.79 to 0.81**. Human–GPS moves more. Mixed-trait bank. Public replay still needs pinned checkpoints.

---

# If you get lost

> We write GPS signs into adapter weights through a shared synthetic bank, then score new survey text without naming the country. Trust order transfers. Agreement with people is open. The next scientific step is a second bank or a sign-retrain.

Then go to slide 20.

# If someone over-reads

| They say | You say |
|---|---|
| You recovered Argentine culture. | We fitted a policy to a sign vector. |
| You removed the model's priors. | We removed the country name from the evaluation prompt. |
| Zero means different constructs. | Sixteen countries, interval from −0.48 to 0.51. Zero rank covariance on this map. |
| You showed pre-piloting works. | We proposed that use. Unrun. |
| The permutation shows signs caused WVS order. | Adapters were not refit. That test is still to run. |
| Weights keep direction, prompts keep shape. | On risk the persona prompt **destroys** adapter–GPS. Not a law. |
| Why not just prompt? | Persona–GPS trust is −0.07 on the same items. TVD is a different metric. |
| Is mixed-profile labeling a bug? | It is the six-sign compiler. It is a bug only if we sell the trust bar as an isolated effect. |
