# SCA2 Phase-2 — Unified Results (canonical store)

**Canonical location:** `MyDrive/SCA2_phase2/` on Google Drive (agonz439@asu.edu)
**Local mirror:** `SCA2_PofW/data/phase2/` (this folder)

The phase-2 adapter evaluation unifies **Ksennia's base-8 run** and **our CO2-8 run**
into one 16-adapter bank, with two evaluation families:

- **GPS reward recovery** (`eval/gps/`) — held-out DPO pairs from the GPS-battery items; accuracy, implied-reward deltas, per-dimension breakdowns, plus generated answers.
- **WVS Wave-7 OOS distributional eval** (`eval/wvs/`) — option-likelihood scoring of the adapters against survey-weighted population distributions (TVD, JSD, Brier, cross-entropy, Wasserstein, ECE, moment/dispersion diagnostics), matched-only for base8/co2_8, full 2×2 for USA/MEX.

Adapters (`adapters/`, 16 × QLoRA on Llama-3.1-8B-Instruct) are Drive-only — they never enter git.

**Start here:**
- `MANIFEST.md` — provenance, schemas, sync commands, warnings.
- Repo `DPO_train_test/CO2_run/CO2_RUN.md` — CO2 training/eval record.
- Repo `DPO_eval_WVS/README.md` — canonical evaluation methodology.

Analysis scripts and unified datasets land in repo `analysis/phase2/`.
