# SCA2_PofW — Synthetic Cultural Agents from Aggregate Anchors

**EconLLM Lab**  
Lab site: [econllm-lab.com](https://www.econllm-lab.com/)  
Codebase: [github.com/EconLLM-Lab/SCA2_PofW](https://github.com/EconLLM-Lab/SCA2_PofW)

A falsifiable construction protocol for population-level choice policies. The pipeline renders declared aggregate anchors — country-level Global Preference Survey (GPS) scores — into synthetic preference data, fits country-specific adapters (DPO / QLoRA on Llama-3.1-8B-Instruct), and evaluates the induced policies against independent human survey distributions. Country labels are excluded from primary inference prompts (`PROMPT_COUNTRY_CONDITIONING = False`): culture enters through the training signal, not through prompt retrieval.

The protocol's scientific value is empirical, not assumed: the working paper specifies five rejection points — anchor transmission, policy encoding, anchor relevance (permuted-anchor placebo), external transport to independent human evidence, and operator robustness.

---

## Working papers

| Paper | File | Status |
|---|---|---|
| **Synthetic Cultural Agents from Aggregate Anchors: A Falsifiable Protocol for Constructing Population-Level Choice Policies** (Gonzalez-Bonorino, Biriukova, Capra) — the methods paper for this codebase: aggregate-anchor construction protocol, scope boundary, five rejection points, predeclared multi-country design, USA/MEX pilot diagnostic (Appendix A), and an independent adversarial audit of the generation pipeline (Appendix B) | [`misc/position_paper/position_paper_sca2.pdf`](./misc/position_paper/position_paper_sca2.pdf) (LaTeX: [`position_paper_sca2.tex`](./misc/position_paper/position_paper_sca2.tex)) | Working-paper draft (methods-first; results shells pending the scaled experiment) |
| Construct-validity instrument paper (validation lane, separate from this generation pipeline) | [`misc/position_paper/position_paper_cvprofiles.pdf`](./misc/position_paper/position_paper_cvprofiles.pdf) (LaTeX: [`position_paper_cvprofiles.tex`](./misc/position_paper/position_paper_cvprofiles.tex)) | Working-paper draft |

---

## Start Here (by role)

| If you need… | Go to |
|---|---|
| **Synthetic data generation** | [`synthetic_generation/`](./synthetic_generation/) · start at [`synthetic_generation/README.md`](./synthetic_generation/README.md) and [`CLI_GUIDE.md`](./synthetic_generation/CLI_GUIDE.md) |
| **Canonical DPO training pipeline** | [`DPO_train_test/`](./DPO_train_test/) · run order in its README |
| **Adapter usage demo** (load + score + reward recovery) | [`notebooks/adapter_usage_demo.ipynb`](./notebooks/adapter_usage_demo.ipynb) |
| **Canonical WVS OOS evaluation surface** | [`DPO_eval_WVS/`](./DPO_eval_WVS/) · evaluation scripts, result tables, and [`DPO_eval_WVS/README.md`](./DPO_eval_WVS/README.md) |
| **Tier-2 OOS evaluation share pack** | [`data/merged/`](./data/merged/) · start at [`DATASET_GUIDE.md`](./data/merged/DATASET_GUIDE.md) |
| **Working papers & theoretical framework** | [`misc/position_paper/`](./misc/position_paper/) · see the table above |
| **Package smoke demo** | [`notebooks/demo.ipynb`](./notebooks/demo.ipynb) |

---

## Repository Structure

```
SCA2_PofW/
├── synthetic_generation/     # GPS anchors → synthetic preference triplets (q, y_w, y_l) + scoring/QC
├── DPO_train_test/           # Preprocessing → DPO QLoRA fine-tuning → cross-eval
├── DPO_eval_WVS/             # Canonical Wave 7 WVS OOS evaluation surface & metrics
│   ├── eval_results_wvs_wave7/  # Summary CSVs, bootstrap CIs, calibration, and question metrics
│   └── question_map_wvs_edited.csv  # 35 unseen WVS items (30 mapped to 6 GPS dimensions, 5 demographics)
├── data/merged/              # WVS + AmericasBarometer evaluation parquets + guides
├── data/GPS, data/WVS/       # Codebooks & metadata (raw microdata gitignored)
├── misc/position_paper/      # Working papers (SCA protocol paper + cvprofiles validation paper)
├── notebooks/demo.ipynb      # Package smoke demo
├── SCA2_ProjectProposal.pdf
└── SCA2_Main_draft.pdf
```

---

## Canonical Surface Summary

| Surface | Status | Purpose |
|---|---|---|
| `synthetic_generation/` | **Canonical** | Anchor rendering, synthetic-pair generation, scoring & QC for GPS-grounded preference pairs |
| `DPO_train_test/` | **Canonical** | QLoRA fine-tuning pipeline (`Llama-3.1-8B-Instruct`) |
| `DPO_eval_WVS/` | **Canonical** | OOS evaluation on 35 unseen WVS Wave 7 items (30 mapped to 6 GPS dimensions, 5 demographics) |
| `data/merged/` | **Canonical** | Frozen OOS parquets (USA/MEX × WVS/AB) |
| `misc/position_paper/` | **Canonical** | Working papers (SCA protocol + cvprofiles validation) |
| `DPO_preliminary_results/` | **Removed** | Legacy pilot CSVs (superseded by `DPO_eval_WVS/eval_results_wvs_wave7/`) |
| `sca2_validity/` | **Removed** | Construct-validity prototypes (orthogonal to this pipeline; superseded by the cvprofiles paper lane) |

---

## Pilot Evaluation (USA/MEX — proof of concept, not country-specificity evidence)

Evaluated on 35 unseen Wave 7 WVS items (30 mapped to 6 Global Preferences Survey (GPS) dimensions, 5 demographics) with `PROMPT_COUNTRY_CONDITIONING = False`:

| Evaluation Setup | Model / Adapter | Total Variation Dist. (TVD) ↓ | Jensen-Shannon Div. (JSD) ↓ | Matched vs Cross (% Matched Better) |
|---|---|---|---|---|
| **Mexico Data (MEX WVS)** | Base Model (`Llama-3.1-8B`) | 0.5211 | 0.2165 | — |
| **Mexico Data (MEX WVS)** | **MEX Adapter (Matched)** | **0.4882** | **0.2010** | **97.1%** |
| **Mexico Data (MEX WVS)** | USA Adapter (Cross) | 0.6377 | 0.2965 | — |
| **USA Data (USA WVS)** | **Base Model (`Llama-3.1-8B`)** | **0.3958** | **0.1439** | — |
| **USA Data (USA WVS)** | MEX Adapter (Cross) | 0.3888 | 0.1405 | — |
| **USA Data (USA WVS)** | USA Adapter (Matched) | 0.5258 | 0.2246 | 11.4% |

### Key Takeaways:
1. **MEX adapter distributional alignment:** On MEX WVS items, the MEX adapter's fixed predicted response distribution lies closer to Mexico's observed response distribution than the USA adapter's on 97.1% of questions ($\Delta \text{TVD} = 0.1495$, 95% CI: [0.0964, 0.2152]).
2. **USA adapter degradation:** The USA adapter degrades fidelity to WVS response distributions relative to the base model on **both** eval countries (TVD 0.526 vs 0.396 on USA data; also worse on MEX data). Mechanism (e.g., anchor–pretraining-prior collision vs. overfit to synthetic scenario format) is not identified by this design.
3. **Under-dispersion:** Option log-probability softmax scoring concentrates probability mass on modal options, leading to systematic population under-dispersion (dispersion bias $-1.15$ to $-1.63$).

> **Design note (interpretation boundary):** with unconditioned prompts, all models emit identical option probabilities across eval countries (the `_on_USA` and `_on_MEX` files differ only in the `eval_country` label). "Matched vs cross" therefore compares each adapter's single **fixed** distribution against each country's observed response distribution. It does **not** demonstrate that an adapter conditions on or "knows" its target country at inference time. The two-country pilot cannot establish country-specificity; the working paper's predeclared design (§6) addresses this with a restricted permutation distribution, an operator-sensitivity panel, and a planned 10–15-country panel. These pilot numbers are reproduced and discussed in Appendix A of the working paper.

---

## Scope & Reliable Applications

The working paper (§8) draws the boundary precisely; a summary:

### Reliable applications (when the predeclared tests support them):
* **Exploratory measurement and hypothesis generation:** constructing candidate policy measures from declared aggregate anchors.
* **Survey-item and benchmark design:** generating plausible scenario/response material conditioned on population-level profiles.
* **Fixed-policy proximity evaluation:** measuring how close an adapter's fixed output distribution lies to independent human response distributions (no country-conditioned inference claims).
* **Ordinal comparative statics:** evaluating ordinal shifts in preference traits across adapters.
* **Latent option probing:** clean, zero-shot option log-likelihood scoring on structured questionnaires without generation noise.

### Unreliable applications:
* **Individual or subgroup representation:** aggregate anchors do not identify individual preferences or within-country heterogeneity; no individual is claimed to be represented.
* **Full preference-distribution recovery:** structural under-dispersion bounds distributional-shape claims.
* **Causal or structural inference / counterfactuals:** requires a separate measurement and identification argument.
* **Absolute polling / headcount forecasting:** cannot predict exact percentage response shares.
* **USA adapter deployment as an "improved American persona":** fine-tuning degrades the base model's existing prior.
* **Free-form generative persona chat:** current evaluation validates structured choice probability distributions, not open-ended roleplay.

---

## License

See [`LICENSE`](./LICENSE). Survey microdata remain under original distributor terms even when derived parquets are shared for lab evaluation.
