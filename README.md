# SCA2_PofW — Synthetic Cultural Agents from Aggregate Anchors

**EconLLM Lab**
Lab site: [econllm-lab.com](https://www.econllm-lab.com/)
Code: [github.com/EconLLM-Lab/SCA2_PofW](https://github.com/EconLLM-Lab/SCA2_PofW)

A construction protocol for *anchored synthetic choice policies*. Pre-specified aggregate preference moments (Global Preferences Survey country profiles) are mapped into synthetic pairwise choices and written into lightweight adapters. Primary evaluation prompts omit country names. Instantiated on sixteen GPS countries and scored on World Values Survey Wave 7 items.

This repository is the methods archive for a working paper. It is not a packaged product, and it is not a one-click trainer.

---

## Working paper

| Paper | File | Status |
|---|---|---|
| **Synthetic Cultural Agents from Aggregate Anchors** (Gonzalez-Bonorino, Biriukova, Capra) | [`misc/position_paper/position_paper_sca2.pdf`](./misc/position_paper/position_paper_sca2.pdf) | Working-paper draft. Do not treat the USA/MEX pilot as the headline result. |

A construct-validity instrument paper lives in a separate lane (`cvprofiles`). It is not this repo's contribution.

**Replication entry:** [`replication/README.md`](./replication/README.md).

---

## What is public vs local

| Object | Where | Public? |
|---|---|---|
| Code, protocol, committed analysis tables/figures | this GitHub repo | Yes (MIT) |
| Sixteen-country option-probability banks | local `data/phase2/raw/` (gitignored) | **Not yet.** Set `SCA2_EVAL_URL` / `SCA2_EVAL_REMOTE` when a zip is published. |
| Adapter weights | Hugging Face `Bonorinoa/SCA2-phase2-adapters` | **Private.** Optional for table regeneration; required only to score new item text. |
| GPS country/individual files | briq / Falk et al. (2018) | Obtain from the source. Not redistributed. |
| WVS Wave 7 microdata | World Values Survey Association (DOI [10.14281/18241.18](https://doi.org/10.14281/18241.18)) | Obtain from the source. Derived respondent extracts are **not** shipped. Rebuild with `data/wvs_eval_full/_build_wvs_eval_full.py`. |

`analysis/phase2/reproduce_tables.py` regenerates headline tables **if** you already have licensed WVS extracts and the eval banks. Committed CSVs under `analysis/phase2/outputs/` are the frozen numbers in git. The draft's 16×23 trust ρ = 0.80 is a later matched surface than the committed construct table (trust ρ = 0.78). See `replication/ARXIV_GATES.md`.

---

## Start here (by role)

| If you need… | Go to |
|---|---|
| **Reproduce committed tables** (no GPU) | [`replication/`](./replication/) |
| **Protocol / sign-labeling CLI** | [`sca2/README.md`](./sca2/README.md), [`protocols/`](./protocols/) |
| **Synthetic pair generation** | [`synthetic_generation/`](./synthetic_generation/) |
| **Historical DPO notebooks** | [`DPO_train_test/`](./DPO_train_test/) — Colab-class T4 jobs, not a free-tier 16-adapter run |
| **WVS scoring notebooks** | [`DPO_eval_WVS/`](./DPO_eval_WVS/) |
| **Working paper** | [`misc/position_paper/`](./misc/position_paper/) |

The `sca2` CLI audits a frozen protocol. `train` / `eval` / `generate --materialize` refuse execution by design.

---

## Design in one paragraph

Country-specific information enters as GPS `sign(z)` labels on a **shared** scenario bank. Magnitudes in the anonymized profile do not change those labels. Sixteen geographic units instantiate thirteen distinct sign profiles (Mexico with Russia, India with Greece, Indonesia with Egypt). Evaluation prompts omit country tokens; that closes a prompting channel, not pretrained associations. Pairwise DPO identifies an ordering. It does not identify population marginals. Phi-4 pair scores are an unused diagnostic (contamination is not a training gate).

Egypt was not asked WVS Q69–Q71 (police, courts, government). Great Britain was not asked Q174. The strict 23-item rectangle drops those four items everywhere. Q69 is the strongest human–GPS trust item on the 42-country map; report it on the 15-country subset rather than deleting it from the scientific story.

---

## Scope

Reliable uses, when the tests support them: scoring new item text against a declared anchor; mapping where two batteries share a construct; fixed-policy proximity to survey distributions.

Unreliable uses: speaking for individuals; recovering response-distribution shape; causal or policy counterfactuals; treating adapters as national cultures.

---

## License

See [`LICENSE`](./LICENSE). Survey microdata remain under original distributor terms.
