# SCA2_PofW — Synthetic Cultural Agents 2.0

**EconLLM Lab**  
Lab site: [econllm-lab.com](https://www.econllm-lab.com/)  
Codebase: [github.com/EconLLM-Lab/SCA2_PofW](https://github.com/EconLLM-Lab/SCA2_PofW)

Country-conditioned preference adapters (DPO / QLoRA on Llama-3.1-8B-Instruct) trained from GPS-grounded synthetic preference data, with frozen-adapter out-of-sample evaluation on World Values Survey (WVS Wave 7) and AmericasBarometer trust-core surfaces.

---

## Start Here (by role)

| If you need… | Go to |
|---|---|
| **Synthetic data generation** | [`synthetic_generation/`](./synthetic_generation/) · start at [`synthetic_generation/README.md`](./synthetic_generation/README.md) and [`CLI_GUIDE.md`](./synthetic_generation/CLI_GUIDE.md) |
| **Canonical DPO training pipeline** | [`DPO_train_test/`](./DPO_train_test/) · run order in its README |
| **Canonical WVS OOS evaluation surface** | [`DPO_eval_WVS/`](./DPO_eval_WVS/) · evaluation scripts, result tables, and [`DPO_eval_WVS/README.md`](./DPO_eval_WVS/README.md) |
| **Tier-2 OOS evaluation share pack** | [`data/merged/`](./data/merged/) · start at [`DATASET_GUIDE.md`](./data/merged/DATASET_GUIDE.md) |
| **Position paper & theoretical framework** | [`misc/position_paper/`](./misc/position_paper/) · LaTeX source, compiled PDF, and theory notes |
| **Package smoke demo** | [`notebooks/demo.ipynb`](./notebooks/demo.ipynb) |

---

## Repository Structure

```
SCA2_PofW/
├── synthetic_generation/     # GPS → synthetic preference triplets (q, y_w, y_l)
├── DPO_train_test/           # Preprocessing → DPO QLoRA fine-tuning → cross-eval
├── DPO_eval_WVS/             # Canonical Wave 7 WVS OOS evaluation surface & metrics
│   ├── eval_results_wvs_wave7/  # Summary CSVs, bootstrap CIs, calibration, and question metrics
│   └── question_map_wvs_edited.csv  # 35 unseen WVS items mapped to 6 GPS preference dimensions
├── data/merged/              # WVS + AmericasBarometer evaluation parquets + guides
├── data/GPS, data/WVS/       # Codebooks & metadata (raw microdata gitignored)
├── misc/                     # Position paper latex source (`position_paper/`) & DPO–BT theory archive
├── notebooks/demo.ipynb      # Package smoke demo
├── SCA2_ProjectProposal.pdf
└── SCA2_Main_draft.pdf
```

---

## Canonical Surface Summary

| Surface | Status | Purpose |
|---|---|---|
| `synthetic_generation/` | **Canonical** | Generator & scorer for GPS-grounded preference pairs |
| `DPO_train_test/` | **Canonical** | QLoRA fine-tuning pipeline (`Llama-3.1-8B-Instruct`) |
| `DPO_eval_WVS/` | **Canonical** | OOS evaluation on 35 unseen WVS Wave 7 items across 6 GPS dimensions |
| `data/merged/` | **Canonical** | Frozen OOS parquets (USA/MEX × WVS/AB) |
| `DPO_preliminary_results/` | **Removed** | Legacy pilot CSVs (superseded by `DPO_eval_WVS/eval_results_wvs_wave7/`) |

---

## Empirical Findings (WVS Wave 7 OOS Evaluation)

Evaluated on 35 unseen Wave 7 WVS questions mapped to 6 Global Preferences Survey (GPS) dimensions with `PROMPT_COUNTRY_CONDITIONING = False`:

| Evaluation Setup | Model / Adapter | Total Variation Dist. (TVD) ↓ | Jensen-Shannon Div. (JSD) ↓ | Specificity (% Matched > Cross) |
|---|---|---|---|---|
| **Mexico Data (MEX WVS)** | Base Model (`Llama-3.1-8B`) | 0.5211 | 0.2165 | — |
| **Mexico Data (MEX WVS)** | **MEX Adapter (Matched)** | **0.4882** | **0.2010** | **97.1%** |
| **Mexico Data (MEX WVS)** | USA Adapter (Cross) | 0.6377 | 0.2965 | — |
| **USA Data (USA WVS)** | **Base Model (`Llama-3.1-8B`)** | **0.3958** | **0.1439** | — |
| **USA Data (USA WVS)** | MEX Adapter (Cross) | 0.3888 | 0.1405 | — |
| **USA Data (USA WVS)** | USA Adapter (Matched) | 0.5258 | 0.2246 | 11.4% |

### Key Takeaways:
1. **Mexico Specificity Success:** The matched MEX adapter significantly outperforms the cross USA adapter on 97.1% of MEX questions ($\Delta \text{TVD} = 0.1495, \text{95% CI}: [0.0964, 0.2152]$).
2. **USA Adapter Asymmetry:** The USA adapter degrades performance relative to the base model on US data due to over-correction on an already US-biased base pretraining prior.
3. **Under-Dispersion:** Option log-probability softmax scoring concentrates probability mass on modal options, leading to systematic population under-dispersion (dispersion bias $-1.15$ to $-1.63$).

---

## Scope & Reliable Applications

### Reliable Applications (What the methodology CAN do):
* **Implicit Preference Internalization:** Bakes country-specific behavioral priors directly into weights without explicit country prompts (`PROMPT_COUNTRY_CONDITIONING = False`).
* **Non-WEIRD Latent Trait Alignment:** Reliably shifts option choice probabilities toward empirical population distributions for populations under-represented in pretraining (e.g., Mexico).
* **Relative Comparative Statics:** Suitable for evaluating ordinal shifts in preference traits (e.g., Altruism TVD dropping from $0.450 \rightarrow 0.152$ on MEX data).
* **Latent Option Probing:** Clean, zero-shot option log-likelihood scoring on structured questionnaires without generation noise.

### Unreliable Applications (What it CANNOT do yet):
* **Absolute Population Polling / Headcount Forecasting:** Cannot predict exact percentage response shares due to structural under-dispersion.
* **USA Adapter Deployment:** USA DPO adapter should not be deployed as an "improved American persona" as fine-tuning degrades the base model's existing prior.
* **Free-Form Generative Persona Chat:** Current evaluation validates structured choice probability distributions, not open-ended conversational roleplay.

---

## License

See [`LICENSE`](./LICENSE). Survey microdata remain under original distributor terms even when derived parquets are shared for lab evaluation.
