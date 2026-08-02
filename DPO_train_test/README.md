# DPO train / test (canonical)

Country-specific QLoRA DPO adapters on **Llama-3.1-8B-Instruct**, plus cross-country reward-recovery evaluation.

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
- Do **not** confuse with [`../DPO_preliminary_results/`](../DPO_preliminary_results/) (historical n≈70 pilot CSVs).
- Frozen adapters are evaluated OOS on [`../data/merged/`](../data/merged/) — **no retrain** on WVS/AB.
- Training is ~hours per country on a single Colab-class GPU; full cross-eval is longer. See notebook comments for `max_examples` smoke settings.
