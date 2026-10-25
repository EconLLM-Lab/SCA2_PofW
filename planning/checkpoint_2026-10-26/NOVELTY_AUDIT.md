VERDICT: partly novel — what is new is the instrument: six declared country-level GPS signs, compiled into adapters and scored on new item text with the group never named, under a preregistered retrospective screen. Distribution-matching fine-tuning, country-persona prompting, use in survey design, a measurement-instrument framing and cross-dimension "entanglement" are all published already and must be cited, not claimed.

# CP26-N1 Novelty audit: LM evaluation as social-science measurement

Card t_aca427d2 · written 2026-10-24 by @sca · read-only audit, this file only, not committed.
Positioning audited: option A (preregistered evaluation of a measurement instrument; holds / must-say / fails / order versus distribution / untested), as set out in the card's rules block.

**Method.** I ran about 25 web searches (silicon samples, OpinionQA/GlobalOpinionQA follow-ups, fine-tuned survey-response models, country personas, cultural fine-tuning and adapters, activation steering, construct validity, LLM pretesting, the GPS with LLMs, order versus distribution). I opened every source cited below (abstract page, OpenReview, PMLR, publisher page or PDF). I registered each source in a grounded-citations ledger at the time I retrieved it. The Sources block at the end is rendered from that ledger. The manuscript side comes from `git show paper/paper-b-draft:misc/paper_b/{references.bib,abstract,introduction,background,instrument,discussion,conclusion}.tex`. I did not open `data/` and did not touch the manuscript.

**Premise flags.** (a) The card names a `scientific-paper-strategy` skill, but that skill does not exist on this profile (`skill_view` returned "not found"). I followed `grounded-citations`, plus a manual novelty-audit procedure: closest-work table, then claim-by-claim pre-emption check, then wording ladder. (b) The Oxford Academic page for Tao et al. (PNAS Nexus) blocked extraction, so I opened the arXiv version instead.[22] (c) Coverage limit: there was no Scopus or Google Scholar crawl, and work published under different vocabulary may have been missed. 2026 arXiv postings were searched explicitly.

---

## 1. Has anyone compiled declared group-level benchmark signs into adapters and scored new item text with them?

**Answer: no.** I found no published work that does this. The searches looked for: (i) a training signal made only of the *signs of published country-level benchmark scores*, with no human response distributions or survey answers; (ii) one adapter per sign profile, fitted by a pairwise preference objective; and (iii) evaluation as an instrument that scores *new item text* with the group unnamed. Each element on its own has close neighbours.

**The three closest works:**

| # | Work | What it does | How Paper B differs |
|---|---|---|---|
| 1 | Cao et al., NAACL 2025 (already in `references.bib` as `cao2025`) | Fine-tunes LLMs on first-token probabilities to match country-level response *distributions* from two global cultural surveys. Tests on unseen questions, countries and a whole unseen survey, and calls itself "the first to specialize LLMs for the task of simulating survey response distributions".[1] | Their training target is the human answer distributions, so the human survey sits inside the training signal. Paper B trains on synthetic pairs labelled by six declared GPS signs. Its target is the *order of countries* on new items, and the human survey is read only afterwards as a retrospective criterion. |
| 2 | Suh et al., ACL 2025, SubPOP (already in bib as `suh2025`) | Fine-tunes on 3,362 questions and 70K subpopulation–response pairs. The motivation is "predicting survey responses in advance during the early stages of survey design". Reports generalization to unseen surveys and subpopulations.[2] | SubPOP already claims the survey-design motivation. It is a single model trained on human response distributions, with the subpopulation named in the input. Paper B builds per-profile adapters from aggregate signs and never names the group at evaluation. |
| 3 | Li et al., CultureLLM, NeurIPS 2024 (not in bib) | Fine-tunes culture-specific LLMs (9 cultures) from 50 WVS seed items plus semantic augmentation.[3] A 2026 follow-up keeps each culture in a separate adapter with a router (CultureManager, ACL 2026).[4] | These are per-culture fine-tuned models or adapters, and they are the closest *architecture*. Their training data are WVS item answers and web-grounded cultural text, though, and the goal is downstream-task performance. They do not compile declared benchmark signs, and they are not evaluated as an item-scoring instrument against a held-out survey. |

Other neighbours to cite where relevant:

- Chen, Wang, Wang and Bhatia (Nat. Hum. Behav., 12 Oct 2026) use the *same anchor*. They ran "a virtual Global Preference Survey" across 74 countries and 20 LLM configurations, all by prompting, and conclude that simulated responses are "not yet reliable proxies for cross-national representative surveys".[8] A referee will expect this paper in the GPS discussion. It uses individual-level prompting, with no adapters and no new item text.
- Group Preference Optimization fits groups' preferences few-shot with an added module.[7] Theory-driven SFT installs explicit utility specifications into agents.[6] Both "compile declared preferences into weights", but neither works from group-level benchmark signs or evaluates items.
- Dang & Masud steer cultural values with activations, and report "latent entanglement, where interventions along one cultural dimension induce shifts along another".[5] See answer 3: this pre-empts any claim that entanglement is a new finding.

**Implication for M1.** Paper B may say *what* it studies: an instrument compiled from declared signs, scored on new item text, with the group unnamed. It must cite [1][2] and CultureLLM[3] as the distribution-trained and per-culture-trained alternatives. It may not claim to be first to fine-tune for survey simulation[1], or first to aim LLM survey models at survey design.[2]

---

## 2. Is the "order of groups versus answer distributions" contrast reported elsewhere?

**Answer: the general separation is published. Paper B's specific crossing is not, as far as I found.** The crossing is: sign-compiled adapters keep the anchor's order on trust but sit farther from WVS answer distributions than the base model, while a country-named prompt sits closer on distributions but has no trust order. Treat it as a descriptive result (C9 rows, not preregistered) that sits inside a known distinction.

What is already published:

- **Order or level and distribution are different evaluation targets.** Population Fidelity separates "group-level accuracy, the amount of between-group variation, and the structure of that variation". It finds that cultural fine-tuning "can improve alignment with the survey center without improving the representation of within-population differences, a distinction that measures of aggregate agreement do not capture".[10] Meister et al. separate describing a distribution from simulating one.[23]
- **Naming the country, in the ESS.** Wang (Sep 2026) finds that adding the country name to a backstory "raises the median per-item correlation between simulated and observed country means from -0.03 to 0.52". The paper concludes that silicon sampling "can thus support exploratory country-ranking comparison … It does not support individual or distributional inference."[9] **This runs opposite to Paper B on order.** There, naming the country *does* buy the ranking. M1 must not generalize `PX_persona_trust_rho` beyond GPS trust on these surfaces. It should cite [9] as a case where country naming recovers country rankings on different items and a different survey.
- **Country cues move distributions, partly.** Durmus et al. report that prompting for a country's perspective makes responses "more similar to the opinions of the prompted populations" (with stereotype risk).[14] Tao et al. report that cultural prompting improves alignment for 71–81% of countries.[22] Wedgwood et al. (2026) find that "not all shifts move toward matched human response distributions" and that "institutional trust and democracy-related questions remain difficult".[11] That is consistent with Paper B's persona arm failing on the trust order.
- **Survey fine-tuning and dispersion.** Ziaei (2026) reports "consensus collapse": fine-tuning on WVS (SFT/DPO/GRPO) compresses within-group spread.[12] This touches `C9_TVD_adapter_minus_base_profile_block`. It is also the "fine-tuning drives agents away from humans" story that is **forbidden framing C**, so cite it as related evidence on distributions and do not adopt its thesis.
- Chen et al. find that removing country labels weakens alignment less than removing demographics, which suggests the country label carries limited information.[8]

**What remains Paper B's own.** These are one fixed instrument family and one anchor. Training on the anchor's signs gives the anchor's order (trust only) and loses distributional closeness. The named-group prompt shows the reverse pattern. The paper must also say that the sign *prompt* keeps the order too (`PX_signprompt_trust_rho`, `SP_D_own` unresolved), so the order belongs to the signs, not to the weights. **Safe wording:** "a descriptive contrast between two questions: whether the instrument keeps the anchor's order of countries, and whether it reproduces respondents' answer distributions", citing [10][9]. Avoid "we show for the first time" and "the persona matches respondents".

---

## 3. Framing words: safe, hedge, taken

The manuscript grep (`first|novel|we introduce|we propose|to our knowledge|entangle*|measurement instrument|scoring instrument|pretest*|pre-pilot*`) found **no** "first", "novel", "we introduce", "we propose" or "to our knowledge" in the abstract, introduction, discussion or conclusion. The current draft is already clean on the strong words. The flags below are for M1's rewrite and for three existing phrases.

**Safe (use freely):**
- "we evaluate", "we locate where … holds and where it fails", "we report", "we study one such instrument", "we build" or "we construct".
- "preregistered", "retrospective" (say it first), "descriptive" (for C9).
- "sign-compiled adapters", "declared country-level benchmarks", "with the group unnamed".
- "we specify and register a screen of new items". I found no other preregistered item-screening protocol for LLM survey instruments. Say what the protocol does without claiming priority.

**Needs a hedge or a citation next to it:**
- **"scoring instrument for new item text"** (abstract, intro ¶4, discussion, conclusion). Keep it, but say immediately that the novelty lies in the *training signal* (six declared signs, no human answers) and the unnamed group. Generalization to unseen questions is established for distribution-trained models.[1][2]
- **"measurement instrument" or the "evaluation as measurement" framing.** Wallach et al. argue that "evaluating GenAI systems is a social science measurement challenge".[16] Desai, Card and Jacobs audit LLMs "as measurement instruments" in flagship social-science journals.[18] TS2E builds a total-survey-error framework for simulated survey responses.[19] Bean et al. review construct validity across 445 benchmarks.[17] Use the framing with [16][18] cited, as the lens the paper adopts, not as a contribution.
- **"A diagnostic of entanglement"** (contribution 3 and discussion). Entanglement across cultural dimensions under intervention is already reported, for activation steering.[5] Rephrase as "we use the full factorial of sign profiles to measure how far the declared dimensions move each other's surfaces in trained adapters and under a sign prompt" and cite [5]. The factorial design is the contribution; the existence of entanglement is not.
- **"rarely tested as screening instruments"** (abstract). This is defensible. LLM pretesting work tests *flaw detection* in question wording, not whether items separate countries.[20][21] Keep "rarely", cite [20], and never write "never".
- **"cheap first reading of survey items" or a survey-design motivation.** SubPOP states the same motive,[2] and Sturgis et al. report LLM question testing "orders of magnitude faster and cheaper than human pretesting".[20] Cite both. Do not let this slide into option B ("a tool for pre-piloting").

**Taken (do not claim):**
- "first to fine-tune / specialize LLMs to simulate survey response distributions" (claimed by [1]).
- "LLM survey models for survey design / predicting responses before fielding" ([2]).
- "LLMs as measurement instruments" or "evaluation is measurement" as a new idea ([16][18]).
- "country prompts shift answers toward that country" ([14][22]); "country label buys country ranking" ([9]).
- "dimensions are entangled / coupled" as a discovery ([5]).
- "fine-tuning erases or compresses human variance" ([12]). This is also forbidden framing C.
- "between-group order and distributional fidelity are distinct" as a conceptual point ([10]).
- "we introduce synthetic cultural agents". Avoid it as well. The construction appears in the arXiv preprint, which the manuscript may not cite, so "we introduce" invites a referee to find the preprint. Use "we study" / "we build" / "the development stage of this study".

---

## 4. Up to eight references the introduction should cite and does not

Checked against `paper/paper-b-draft:misc/paper_b/references.bib` (31 entries). The bib already has argyle2023, bisbee2024, boelaert2025, wang2025, cao2025, suh2025, krsteski2026, kozlowski2025, lyman2025, broska2025, buskirk2026, ludwig2026 and dalloul2026. **None of the eight below is in it.** Each entry was built from the page I opened. Keys avoid the existing `wang2025`.

Priority order and where each goes in the introduction:
1. `santurkar2023` and 2. `durmus2024`: the canonical LM-versus-opinion-poll frameworks; GlobalOpinionQA is the cross-national, country-prompted one.[26][27]
3. `dominguezolmedo2024`: survey responses governed by ordering and labelling biases, trending to uniform. This is the measurement-artefact critique that motivates prompts with no country and fixed scoring.[15]
4. `chen2026`: the same anchor (GPS), 74 countries, prompting, "weak proxies". A referee will ask for it.[8]
5. `wallach2025`: the measurement framing the positioning adopts.[16]
6. `wangc2026`: country naming recovers the ranking on the ESS but supports no distributional inference. It is the necessary foil for the order-versus-distribution contrast.[9]
7. `dasilva2026`: center accuracy versus between-group variation versus structure.[10]
8. `dangmasud2026`: prior evidence of entanglement across cultural dimensions.[5]

```bibtex
@inproceedings{santurkar2023,
  title     = {Whose Opinions Do Language Models Reflect?},
  author    = {Santurkar, Shibani and Durmus, Esin and Ladhak, Faisal and Lee, Cinoo and Liang, Percy and Hashimoto, Tatsunori},
  booktitle = {Proceedings of the 40th International Conference on Machine Learning},
  series    = {Proceedings of Machine Learning Research},
  volume    = {202},
  pages     = {29971--30004},
  year      = {2023},
  url       = {https://proceedings.mlr.press/v202/santurkar23a.html}
}

@inproceedings{durmus2024,
  title     = {Towards Measuring the Representation of Subjective Global Opinions in Language Models},
  author    = {Durmus, Esin and Nguyen, Karina and Liao, Thomas I. and Schiefer, Nicholas and Askell, Amanda and Bakhtin, Anton and Chen, Carol and Hatfield-Dodds, Zac and Hernandez, Danny and Joseph, Nicholas and Lovitt, Liane and McCandlish, Sam and Sikder, Orowa and Tamkin, Alex and Thamkul, Janel and Kaplan, Jared and Clark, Jack and Ganguli, Deep},
  booktitle = {First Conference on Language Modeling (COLM)},
  year      = {2024},
  url       = {https://openreview.net/forum?id=zl16jLb91v},
  eprint    = {2306.16388},
  archivePrefix = {arXiv}
}

@inproceedings{dominguezolmedo2024,
  title     = {Questioning the Survey Responses of Large Language Models},
  author    = {Dominguez-Olmedo, Ricardo and Hardt, Moritz and Mendler-D{\"u}nner, Celestine},
  booktitle = {Advances in Neural Information Processing Systems},
  volume    = {37},
  year      = {2024},
  eprint    = {2306.07951},
  archivePrefix = {arXiv},
  url       = {https://arxiv.org/abs/2306.07951}
}

@article{chen2026,
  title   = {Simulated Responses from Large Language Models Are Weak Proxies for Human Economic Preferences across 74 Countries},
  author  = {Chen, Fadong and Wang, Qijun and Wang, Lei and Bhatia, Sudeep},
  journal = {Nature Human Behaviour},
  year    = {2026},
  doi     = {10.1038/s41562-026-02611-4},
  url     = {https://doi.org/10.1038/s41562-026-02611-4}
}

@inproceedings{wallach2025,
  title     = {Position: Evaluating Generative {AI} Systems Is a Social Science Measurement Challenge},
  author    = {Wallach, Hanna and Desai, Meera and Cooper, A. Feder and Wang, Angelina and Atalla, Chad and Barocas, Solon and Blodgett, Su Lin and Chouldechova, Alexandra and Corvi, Emily and Dow, P. Alex and Garcia-Gathright, Jean and Olteanu, Alexandra and Pangakis, Nicholas and Reed, Stefanie and Sheng, Emily and Vann, Dan and Vaughan, Jennifer Wortman and Vogel, Matthew and Washington, Hannah and Jacobs, Abigail Z.},
  booktitle = {Proceedings of the 42nd International Conference on Machine Learning (Position Paper Track)},
  year      = {2025},
  url       = {https://openreview.net/forum?id=1ZC4RNjqzU}
}

@misc{wangc2026,
  title         = {Silicon Sampling Answers with Country-Level Assumptions, Not Individual Attitudes: Cross-National Evidence from the {E}uropean {S}ocial {S}urvey},
  author        = {Wang, Chuyao},
  year          = {2026},
  eprint        = {2609.16395},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CY},
  url           = {https://arxiv.org/abs/2609.16395}
}

@misc{dasilva2026,
  title         = {Population Fidelity: Evaluating Population Representativeness in {LLMs}},
  author        = {da Silva, Neemias B. and Lukk, Martin and Sutani, Ali and Moturu, Abhishek and Yang, Harris and Silver, Daniel and Ratto, Matt and Silva, Thiago H.},
  year          = {2026},
  eprint        = {2609.36253},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CL},
  url           = {https://arxiv.org/abs/2609.36253}
}

@misc{dangmasud2026,
  title         = {Cultural Value Alignment via Latent Activation Steering in Large Language Models},
  author        = {Dang, Trung Duc Anh and Masud, Sarah},
  year          = {2026},
  eprint        = {2605.26365},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CL},
  note          = {ACL 2026 Student Research Workshop (non-archival track)},
  url           = {https://arxiv.org/abs/2605.26365}
}
```

Notes on the entries:
- The Wallach entry's "42nd ICML" is inferred from the OpenReview venue label "ICML 2025 Position Paper Track". I did not open a PMLR volume page, so check the volume number before adding a `volume` field.
- Dominguez-Olmedo: the NeurIPS 2024 venue comes from the arXiv comment field. Volume 37 is the NeurIPS 2024 volume.

**Also worth citing outside the introduction (not among the eight, no BibTeX here):**
- CultureLLM[3] and CultureManager[4], in the background, as per-culture adapters.
- Wedgwood et al.,[11] for persona framing and institutional trust.
- Ziaei,[12] for dispersion, while keeping clear of framing C.
- Sturgis, Roberts and Robinson,[20] on LLM pretesting, wherever "pretesting" appears.
- Desai, Card and Jacobs,[18] on validation norms.
- Meister et al.,[23] on distributional alignment.
- Tao et al.,[22] on cultural prompting.

## Sources

[1] https://arxiv.org/abs/2502.07068 — Cao et al. 2025, Specializing LLMs to Simulate Survey Response Distributions for Global Populations
[2] https://arxiv.org/abs/2502.16761 — Suh et al. 2025, Language Model Fine-Tuning on Scaled Survey Data (SubPOP)
[3] https://arxiv.org/abs/2402.10946 — Li et al. 2024, CultureLLM
[4] https://aclanthology.org/2026.acl-long.766v2.pdf — Zhang et al. 2026, Mind the Gap in Cultural Alignment (CultureManager)
[5] https://arxiv.org/abs/2605.26365 — Dang and Masud 2026, Cultural Value Alignment via Latent Activation Steering
[6] https://arxiv.org/abs/2507.20796 — 2025, Aligning LLM Agents with Rational and Moral Preferences (SFT)
[7] https://arxiv.org/abs/2310.11523 — Zhao et al., Group Preference Optimization
[8] https://www.nature.com/articles/s41562-026-02611-4 — Chen, Wang, Wang and Bhatia 2026, Nat Hum Behav, weak proxies across 74 countries
[9] https://arxiv.org/abs/2609.16395 — Wang 2026, Silicon sampling answers with country-level assumptions (ESS)
[10] https://arxiv.org/abs/2609.36253 — da Silva et al. 2026, Population Fidelity
[11] https://arxiv.org/abs/2607.24782 — Wedgwood et al. 2026, Personalization, Personas, and Forecasting in Value Alignment
[12] https://arxiv.org/abs/2609.25760 — Ziaei 2026, The Limits of Simulated Societies (consensus collapse)
[14] https://arxiv.org/abs/2306.16388 — Durmus et al. 2024, GlobalOpinionQA
[15] https://arxiv.org/abs/2306.07951 — Dominguez-Olmedo et al. 2024, Questioning the Survey Responses of LLMs
[16] https://openreview.net/forum?id=1ZC4RNjqzU — Wallach et al. 2025, Evaluating GenAI Systems Is a Social Science Measurement Challenge
[17] https://arxiv.org/abs/2511.04703 — Bean et al. 2025, Measuring what Matters: Construct Validity in LLM Benchmarks
[18] https://arxiv.org/abs/2607.07915 — Desai, Card and Jacobs 2026, Validating LLMs in social science
[19] https://arxiv.org/abs/2609.10280 — 2026, Total Simulated Survey Error (TS2E)
[20] https://surveyfutures.net/wp-content/uploads/2026/04/working-paper-15-llms-for-survey-pretesting.pdf — Sturgis, Roberts and Robinson 2026, LLMs for survey pretesting
[21] https://arxiv.org/abs/2501.05985 — 2025, Exploring LLMs for Automated Generation and Adaptation of Questionnaires
[22] https://arxiv.org/abs/2311.14096 — Tao et al. 2024, Cultural Bias and Cultural Alignment of LLMs
[23] https://arxiv.org/abs/2411.05403 — Meister, Guestrin and Hashimoto 2025, Benchmarking Distributional Alignment
[26] https://proceedings.mlr.press/v202/santurkar23a.html — Santurkar et al. 2023, ICML PMLR page
[27] https://openreview.net/forum?id=zl16jLb91v — Durmus et al. COLM 2024 OpenReview page
