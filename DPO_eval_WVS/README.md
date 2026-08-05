# DPO Adapter Evaluation on Unseen WVS Survey Questions

**Canonical Out-of-Sample (OOS) Evaluation Surface**  
**EconLLM Lab** · [`github.com/EconLLM-Lab/SCA2_PofW`](https://github.com/EconLLM-Lab/SCA2_PofW)

This folder contains the canonical evaluation pipeline and empirical results for assessing the base Llama model (`meta-llama/Llama-3.1-8B-Instruct`) and country-specific DPO+QLoRA adapters (`USA_adapter` and `MEX_adapter`) against empirical population response distributions from Wave 7 of the World Values Survey (WVS).

---

## Folder Structure

```
DPO_eval_WVS/
├── DPO_survey_distribution_evaluation.ipynb  # Primary scoring notebook: log-prob extraction & distribution metrics
├── GPS_vs_WVS_evaluation_analysis.ipynb      # Statistical analysis, bootstrap CIs, specificity & visualization
├── question_map_wvs_edited.csv               # 35 unseen WVS questions mapped to 6 GPS preference dimensions
├── README.md                                 # This documentation file
└── eval_results_wvs_wave7/                   # Canonical result tables & summary CSVs
    ├── survey_question_metrics_all_models.csv
    ├── survey_adapter_improvement_vs_base_summary.csv
    ├── survey_matched_vs_cross_specificity_summary.csv
    ├── survey_probability_calibration_ece.csv
    ├── survey_signed_moment_and_top_option_summary.csv
    ├── survey_metrics_by_gps_dimension_wide.csv
    └── survey_metric_bootstrap_summary.csv
```

---

## Methodology & Option-Likelihood Scoring

Unlike open-ended text generation, this evaluation assesses LLMs as **population option-probability simulators**:
1. **Unconditioned Prompting (`PROMPT_COUNTRY_CONDITIONING = False`):** To ensure observed behavioral differences originate from learned adapter weights rather than prompt tokens, country names (e.g., "in Mexico") are omitted from prompts.
2. **Log-Likelihood Extraction:** For every question, the model computes log-probabilities for all valid response codes (e.g., 1–10 scale, Yes/No, 4-point Likert).
3. **Softmax Normalization:** Option log-probabilities are normalized into a predicted discrete choice distribution $\hat{P} = (\hat{p}_1, \dots, \hat{p}_K)$.
4. **Weighted Benchmark Comparison:** $\hat{P}$ is compared against survey-weighted population distributions $P_{\text{WVS}}$ using:
   * Total Variation Distance (TVD)
   * Jensen-Shannon Divergence (JSD)
   * Brier Score & Cross-Entropy
   * Wasserstein Distance & Moment Errors (Mean/Std Error for ordered scales)
   * Expected Calibration Error (ECE) & Dispersion Bias

### $2 \times 2$ Experimental Design Matrix:
* Base Model on USA WVS & Base Model on MEX WVS
* USA Adapter on USA WVS (Matched) & USA Adapter on MEX WVS (Cross)
* MEX Adapter on MEX WVS (Matched) & MEX Adapter on USA WVS (Cross)

---

## Summary of Empirical Findings

| Evaluation Target | Model / Adapter | TVD ↓ | JSD ↓ | ECE ↓ | Specificity (% Matched > Cross) |
|---|---|---|---|---|---|
| **MEX WVS Data** | Base Model (`Llama-3.1-8B`) | 0.5211 | 0.2165 | 0.0919 | — |
| **MEX WVS Data** | **MEX Adapter (Matched)** | **0.4882** | **0.2010** | 0.0967 | **97.1%** |
| **MEX WVS Data** | USA Adapter (Cross) | 0.6377 | 0.2965 | 0.1220 | — |
| **USA WVS Data** | **Base Model (`Llama-3.1-8B`)** | **0.3958** | **0.1439** | **0.0654** | — |
| **USA WVS Data** | MEX Adapter (Cross) | 0.3888 | 0.1405 | 0.0719 | — |
| **USA WVS Data** | USA Adapter (Matched) | 0.5258 | 0.2246 | 0.0958 | 11.4% |

### Key Takeaways:
1. **Strong Mexico Specificity:** On MEX WVS items, the matched MEX adapter outperforms the cross USA adapter on 97.1% of questions ($\Delta \text{TVD} = 0.1495$, $\text{95% CI}: [0.0964, 0.2152]$).
2. **Pretraining Prior Collision on USA:** Fine-tuning on synthetic US pairs degrades performance relative to the base model (TVD $0.3958 \rightarrow 0.5258$) because Llama-3.1-8B already carries a heavy US pretraining prior.
3. **Under-Dispersion:** Softmax option scoring exhibits structural over-confidence, under-estimating real human variance (dispersion bias $-1.15$ to $-1.63$).

---

## Dependencies

* `transformers>=4.41.0`
* `accelerate>=0.30.0`
* `peft>=0.11.1`
* `bitsandbytes>=0.46.1`
* `pyarrow>=15.0.0`
* `scipy>=1.10.0`
* `matplotlib>=3.7.0`
