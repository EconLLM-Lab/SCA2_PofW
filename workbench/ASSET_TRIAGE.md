# Asset Triage — SCA2 Adapter-Brain Visualization Workbench

## 1. Readable — Local files the workbench may read

| Path | Description | Verified |
|------|-------------|----------|
| `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.worktrees/adapter-brain-vizualization/` | Workspace root — source code, configs, docs | ✓ |
| `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.worktrees/adapter-brain-vizualization/data/wvs_eval_full/` | Guides & manifests: `README.md`, `_build_wvs_eval_full.py`, `_manifest.json` | ✓ |
| `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.worktrees/adapter-brain-vizualization/data/merged/` | Guides & manifests: `01_merge_quality_and_usage.ipynb`, `CONSTRUCT_MAP.md`, `DATASET_GUIDE.md`, `README.md`, `_build_merge.py`, `_manifest.json` | ✓ |
| `~/.cache/huggingface/hub/models--meta-llama--Llama-3.1-8B-Instruct/` | Cached Llama-3.1-8B-Instruct model (blobs, refs, snapshots) | ✓ |

**Note:** The workbench may read any file under the workspace root and the cached Llama-3.1-8B-Instruct model. It may NOT read the Paper B dataset caches (see §3).

---

## 2. Absent — Files not present locally

| Expected | Status | Verified |
|----------|--------|----------|
| Parquet files in `data/wvs_eval_full/` | **Absent** — directory contains only guides/manifests | ✓ |
| Parquet files in `data/merged/` | **Absent** — directory contains only guides/manifests | ✓ |
| Hugging Face cache for `Bonorinoa/SCA2-phase2-adapters` (commit `03c43dfd27c9535283feb78ffa727da3bfa1b966`) | **Absent** — no `models--Bonorinoa--SCA2-phase2-adapters` under `~/.cache/huggingface/hub/` | ✓ |
| `gpt2` model cache | **Absent** | ✓ |
| `HuggingFaceTB/SmolLM2-360M-Instruct` cache | **Absent** | ✓ |
| `meta-llama/Llama-3.2-1B-Instruct` cache | **Absent** | ✓ |

---

## 3. Licensed — Files that must stay on this machine

| Path | License / Restriction | Verified |
|------|----------------------|----------|
| `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.worktrees/adapter-brain-vizualization/data/` | **Licensed, local-only, non-redistributable microdata** (WVS/GPS microdata). Per task LOCKS: "Do not copy it into workbench/, a frontend bundle, or git. Do not send it to an API. No push, tag, or publish." | ✓ |
| `~/.cache/huggingface/hub/datasets--Bonorinoa--SCA2-paper-b-adapters/` | Paper B adapter dataset — derived from licensed microdata | ✓ |
| `~/.cache/huggingface/hub/datasets--Bonorinoa--SCA2-paper-b-artifacts/` | Paper B artifacts — derived from licensed microdata | ✓ |

**Ruling:** No file under `data/` or the Paper B dataset caches may leave this machine. No license clause permitting export was found.

---

## 4. Download Command (not run) — Phase-2 adapters

The phase-2 adapter repo `Bonorinoa/SCA2-phase2-adapters` at commit `03c43dfd27c9535283feb78ffa727da3bfa1b966` requires a Hugging Face account and gate acceptance (per repo README). The user owns the namespace (`Bonorinoa`), so gate acceptance is satisfied. A local download that does not redistribute weights is allowed.

**Exact command (do not run):**
```bash
huggingface-cli download Bonorinoa/SCA2-phase2-adapters \
  --revision 03c43dfd27c9535283feb78ffa727da3bfa1b966 \
  --local-dir ./phase2-adapters
```

**Conditions:** Run only from this machine. Do not copy the downloaded adapters off-machine. Do not commit to git.

---

## 5. Model-Load Ruling — Llama-3.1-8B-Instruct on 24 GB

**Machine memory:** `sysctl hw.memsize` = 25,769,803,776 bytes = **24 GB** unified memory (PM claim: 24 GB; user text said 20 GB — discrepancy noted).

**Model footprint (Llama-3.1-8B-Instruct):**
- FP16/BF16 weights: ~16 GB
- KV cache (2048 ctx, batch 1): ~2–4 GB
- Activation overhead + OS: ~2–3 GB
- **Total: ~20–23 GB**

**Risk assessment:**
- **Feasible with headroom ~1–4 GB** if running only the model + minimal Python overhead.
- **Risk: OOM** if other processes (browser, IDE, OS) consume >1–2 GB, or if batch size / context length increases.
- **Mitigation:** Use 8-bit quantization (~8 GB weights) or 4-bit (~4 GB) for comfortable headroom. At full precision, load is borderline; monitor `memory_pressure` and be prepared to offload.

**Verdict:** A later slice MAY load the cached Llama-3.1-8B-Instruct, but only with quantization (8-bit or 4-bit) or strict single-sequence inference. Full-precision load carries non-trivial OOM risk on 24 GB unified memory.

---

## 6. Colab Tensor Transfer Ruling

**Question:** May a later slice send tensors to Google Colab Pro?

**Ruling: NO — not for tensors derived from licensed microdata.**

**Reasoning:**
- The `data/` directory holds licensed, local-only, non-redistributable microdata (WVS/GPS). The task LOCKS explicitly prohibit sending it to an API.
- No license clause was found that permits export of this microdata or derived tensors.
- Tensors computed **from** the licensed microdata (e.g., embeddings, activations, attributions on WVS items) inherit the same restriction.
- Only tensors derived **exclusively** from public models (e.g., base Llama-3.1-8B-Instruct forward passes on synthetic/public prompts with no licensed microdata) could theoretically be sent, but this workbench's purpose is SCA2/WVS evaluation, which requires the licensed microdata.

**Conclusion:** No tensor transfer to Colab is permitted for this workbench. All computation on licensed microdata must remain on this machine.

---

## PM Claim Verification Summary

| # | Claim | Status |
|---|-------|--------|
| 1 | `data/wvs_eval_full` and `data/merged` contain guides/manifests; no parquet files | **Reproduced** |
| 2 | Phase-2 adapter repo is `Bonorinoa/SCA2-phase2-adapters` at commit `03c43dfd...`; requires HF account/gate; no local hub cache | **Reproduced** |
| 3 | Paper B dataset caches exist at `datasets--Bonorinoa--SCA2-paper-b-adapters` and `datasets--Bonorinoa--SCA2-paper-b-artifacts` | **Reproduced** |
| 4 | `models--meta-llama--Llama-3.1-8B-Instruct` cache exists; no `gpt2`, `SmolLM2`, or `Llama-3.2-1B` caches | **Reproduced** |
| 5 | `sysctl hw.memsize` = 25,769,803,776 bytes (24 GB); user text said 20 GB | **Reproduced** (24 GB confirmed; user text discrepancy noted) |

---

**Model/Provider from run log:** `nvidia/nemotron-3-ultra-550b-a55b:free` via `openrouter`