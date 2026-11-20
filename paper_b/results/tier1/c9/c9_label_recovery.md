# C9-4 B: held-out synthetic-label recovery, 42 cohort-1 adapters (DESCRIPTIVE / NOT PREREGISTERED (construction check))

Run `label-recovery-cohort1-v1-20261019`: 42 countries x 132 held-out training-scenario pairs (shared split TRAIN_FRAC=0.80, SEED=42). Cohort means are country-equal; 26 sign profiles in the profile-block bootstrap (2000 draws).

| Quantity | Mean | Profile-block 95% | Country 95% |
|---|---|---|---|
| Recovery (adapter margin > base margin) | 0.940 | [0.926, 0.952] | [0.930, 0.949] |
| Accuracy (adapter margin > 0) | 0.816 | [0.771, 0.856] | [0.786, 0.848] |
| Base accuracy (base margin > 0) | 0.489 | [0.471, 0.506] | [0.476, 0.501] |
| Mean margin shift, nats | 40.282 | [28.246, 54.063] | [32.612, 49.526] |

Reading: recovery and accuracy say whether training installed each country's synthetic labels on scenarios it never saw. They are construction checks; they say nothing about whether the labels order countries like GPS. The preprint reported 0.942 / 0.819 on its 16 development countries with different (preprint) adapters and banks; that is context, not a replication target, and is not re-computed here.

Per-country values and Wilson intervals (pair sampling for one fixed adapter; pairs are shared across countries) are in the CSV/JSON.

Inputs:

- logps: hub:Bonorinoa/SCA2-paper-b-artifacts/runs/label-recovery-cohort1-v1-20261019/logps/ (42 files, sha256 c31640a78d7f4831)
- producer: paper_b/colab/vm_c9_label_recovery.py (gates in runs/<run>/gates.json)
