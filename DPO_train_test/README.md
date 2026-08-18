# DPO train / test (canonical)

Country-specific QLoRA DPO adapters on **Llama-3.1-8B-Instruct**, plus cross-country reward-recovery evaluation.

NOTE: For a base run, refer to the notebooks in the folder. This version does not require preprocessing and only needs data preparation.

NOTE2: For evaluation, select the countries carefully: running all combinations of countries will be long and unnecessary.

## Run order

1. **Preprocessing (CPU OK):** `preprocessing_without_gpu_multi_country.ipynb`  
2. **Train data prep:** `DPO_train_data_preparation_multi_country.ipynb`  
3. **Training (GPU):** `DPO_train.ipynb`  
4. **Cross evaluation (GPU):** `DPO_evaluation_cross_evaluation.ipynb`

## Inputs

- Synthetic preference files (`D_syn` / triplets) from [`../synthetic_generation/`](../synthetic_generation/)
- Extended answer options / variants: `generated_response_variants_3.csv` (in this folder)

Before running, **update Drive/local paths** inside the notebooks (defaults assume Colab + Google Drive layouts under `/content/drive/MyDrive/DPO/`).

## Notes for collaborators

- This directory is the **canonical** fine-tuning path for the paper.
- Frozen adapters are evaluated OOS on [`DPO_eval_WVS/`](../DPO_eval_WVS/) (Wave-7 WVS option-likelihood scoring) and on [`../data/merged/`](../data/merged/) — **no retrain** on WVS/AB.
- Adapter loading pattern (base + PEFT) is demonstrated in the last cell of `DPO_evaluation_cross_evaluation.ipynb` and in [`../notebooks/adapter_usage_demo.ipynb`](../notebooks/adapter_usage_demo.ipynb).
- Training is ~hours per country on a single Colab-class GPU; full cross-eval is longer. See notebook comments for `max_examples` smoke settings.
