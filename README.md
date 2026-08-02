# SCA2_PofW — Synthetic Cultural Agents (phase 2)

**EconLLM Lab** · Arizona State University  
Lab site: [econllm-lab.com](https://www.econllm-lab.com/)

Country-conditioned preference adapters (DPO / QLoRA on Llama-3.1-8B-Instruct) trained from GPS-grounded synthetic preference data, with frozen-adapter out-of-sample evaluation on WVS and AmericasBarometer trust-core surfaces.

## Start here (by role)

| If you need… | Go to |
|---|---|
| **Synthetic data generation** (closed for v1 paper scope) | [`synthetic_generation/`](./synthetic_generation/) · start at [`synthetic_generation/README.md`](./synthetic_generation/README.md) and [`CLI_GUIDE.md`](./synthetic_generation/CLI_GUIDE.md) |
| **Canonical DPO train / cross-eval** (colleague path) | [`DPO_train_test/`](./DPO_train_test/) · run order in its README |
| **Tier-2 OOS evaluation surfaces** (USA/MEX × WVS/AB) | [`data/merged/`](./data/merged/) · start at [`DATASET_GUIDE.md`](./data/merged/DATASET_GUIDE.md) |
| **Package smoke demo** | [`notebooks/demo.ipynb`](./notebooks/demo.ipynb) |
| **Working paper / theory archive** | [`misc/position_paper/`](./misc/position_paper/) · other `misc/*` = theory notes (see [`misc/README.md`](./misc/README.md)) |
| **Historical small-n pilot CSVs** | [`DPO_preliminary_results/`](./DPO_preliminary_results/) — **not** the canonical metrics surface |

## Canonical vs non-canonical

| Surface | Status |
|---|---|
| `synthetic_generation/` | **Canonical** data-gen code + selected outputs |
| `DPO_train_test/` | **Canonical** fine-tune + reward-recovery eval notebooks |
| `data/merged/` | **Canonical** frozen OOS share pack (do not retrain adapters on these) |
| `DPO_preliminary_results/` | **Historical** (e.g. n≈70 pilot). Prefer later n=200 colleague runs / Drive artifacts when quoting metrics |
| `DPO_anchored_pilot_experiment/` | **Removed** from `main` (throwaway pilot scaffolding) |
| Raw `data/Barometer/**/*.dta`, full WVS `.dta`, GPS microdata dirs | **Not in git** (licensed / large). Local only; rebuild merge via `data/merged/_build_merge.py` if you have raw files |

## Quick orientation

```
SCA2_PofW/
├── synthetic_generation/     # GPS → synthetic preference triplets
├── DPO_train_test/           # preprocess → DPO train → cross-country eval
├── data/merged/              # WVS + AB evaluation parquets + guides
├── data/GPS, data/WVS/       # docs/codebooks; raw microdata gitignored
├── notebooks/demo.ipynb      # thin import + cost-estimate demo
├── misc/                     # position paper + DPO–BT theory archive
├── DPO_preliminary_results/  # old pilot CSVs / notebooks
├── SCA2_ProjectProposal.pdf
└── SCA2_Main_draft.pdf
```

### OOS evaluation rules (short)

1. Evaluate **frozen** USA/MEX adapters — no per-survey retrain.  
2. Primary OOS construct coverage is documented in `data/merged/CONSTRUCT_MAP.md` (`clean` / `bridge` / `stretch`).  
3. AmericasBarometer in the share pack is **2012–2019 trust-core only**.  
4. Do **not** row-stack WVS with AB. GPS is identification / in-sample, not in the merge.

### DPO train/eval (short)

See `DPO_train_test/README.md`. Typical order: preprocessing → train → cross evaluation. Paths in notebooks default to Google Drive Colab layouts — update before running.

## What is intentionally not here

- Trained adapter weights (Drive / HF private)  
- Raw LAPOP/AmericasBarometer `.dta` and full WVS microdata  
- Local venvs, editor config, agent indexes  

## License

See [`LICENSE`](./LICENSE). Survey microdata remain under their original distributor terms even when derived parquets are shared for lab evaluation.
