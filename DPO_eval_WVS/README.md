# DPO Adapter Evaluation on Unseen WVS Survey Questions

This repository contains the evaluation pipeline for assessing the base Llama model and country-specific DPO+QLoRA adapters against empirical population response distributions. The evaluation is performed on unseen World Values Survey (WVS) questions. 

**Important Note on Adapters:** The adapter files must be loaded separately. They were trained in the previous step, and the corresponding training pipeline is stored in the `DPO_train_test` folder.

**Evaluation Notes:** The scoring notebook has the basic metrics, while a more comprehensive and graphical analysis is stored in a separate notebook.

You need to change the file pathways to where the adapters and eval data is stored on your computer/Drive.

---

## Overview

The primary goal of this evaluation is to test whether the country-specific behavior stems from the adapter itself rather than explicit country conditioning in the prompt. For every survey question, the model is scored on all valid response codes, and the option log-probabilities are normalized into a response distribution. 

The notebook produces the following cross-comparisons:
* Base model on USA data
* Base model on MEX data
* USA adapter on USA data
* USA adapter on MEX data
* MEX adapter on USA data
* MEX adapter on MEX data

---

## Evaluation Metrics

The generated response distributions are compared against weighted population distributions using several statistical metrics:
* Total variation distance
* Jensen-Shannon divergence
* Brier score
* Cross-entropy
* Wasserstein distance (for ordered response scales)
* Moment errors (for ordered response scales)

---

## Configuration Details

* **Base Model:** `meta-llama/Llama-3.1-8B-Instruct`
* **Country Conditioning:** By default, the country is **not** named in the prompt (`PROMPT_COUNTRY_CONDITIONING = False`) to ensure observed behaviors are learned by the adapter. You can set this to `True` to run an alternative country-conditioned test.
* **Survey Weights:** The evaluation uses survey weights by default (`USE_SURVEY_WEIGHTS = True`) based on the provided parquet files. 
* **Numeric-Open Questions:** The pipeline evaluates numeric-open questions (like age and birth year) over the union of observed valid integer responses in the population files.

---

## Dependencies

To run this evaluation, ensure you have the following packages installed:
* `transformers>=4.41.0`
* `accelerate>=0.30.0`
* `peft>=0.11.1`
* `bitsandbytes>=0.46.1`
* `safetensors>=0.4.3`
* `pyarrow>=15.0.0`
* `scipy>=1.10.0`
* `matplotlib>=3.7.0`

You will also need to authenticate with Hugging Face using a valid access token to download the base Llama-3.1 model.
