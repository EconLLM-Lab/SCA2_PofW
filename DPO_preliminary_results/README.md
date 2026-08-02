# DPO preliminary results (historical)

Small-n pilot artifacts from an earlier training/eval pass.

| File | Role |
|------|------|
| `DPO_train_eval (1).ipynb` | Older combined train/eval notebook |
| `Results_EDA.ipynb` | Notes on pilot CSVs |
| `reward_recovery_*.csv` | Pilot reward-recovery tables (**n ≈ 70**) |

## Important

- **Not the canonical metrics surface.** Preference accuracies here (~0.97 own-country) are inflated relative to the later **n = 200** cross-eval runs.
- **Canonical train/eval code:** [`../DPO_train_test/`](../DPO_train_test/).
- When quoting results externally, tag sample size and source path/date; prefer the colleague n=200 summary over these CSVs.
