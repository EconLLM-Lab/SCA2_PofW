# SCA2 Phase-2 Unified Results — MANIFEST (canonical store)

**Location:** `MyDrive/SCA2_phase2/` (Google Drive, agonz439@asu.edu) · mirrored locally at `SCA2_PofW/data/phase2/`
**Created:** 2026-08-19 · **By:** EconLLM Lab (SCA2 phase-2 unification session)
**Sync tool:** rclone remotes — `sca2drive` (own Drive), `ksenias_gps` / `ksenias_wvs` / `ksenias_adapters` (Ksennia's shared folders, mounted by folder ID)

This is the single canonical home for the 16-adapter bank and both evaluation families (GPS reward recovery + WVS OOS distributional eval). Git stores code, small summaries, and manifests only — adapters and raw eval outputs live here.

---

## Layout

```
SCA2_phase2/
├── README.md                    ← this project readme
├── MANIFEST.md                  ← this file (provenance + schema + sync)
├── adapters/                    ← (REMOVED 2026-08-19 — adapters moved to HuggingFace Hub)
├── docs/
│   └── CO2_run/                 ← CO2 run record: CO2_RUN.md, eval summary,
│                                   profile-screen scripts, WVS exec report + PNGs
├── analysis/                    ← unified analysis layer (scripts + outputs + figures)
│   ├── 01..11_*.py              ← full pipeline (build → heatmaps → twins → temp → dev)
│   ├── outputs/                 ← all CSVs/parquets + 10 figures
│   └── README.md                ← analysis README with headline results
└── eval/
    ├── gps/                     ← DPO reward recovery on GPS-battery held-out pairs
    │   ├── ksenias_base8/       ← row-level + summaries (incl. cross-country pairs)
    │   └── co2_8/               ← row-level (self-mode) + all_adapters
    └── wvs/                     ← WVS Wave-7 OOS distributional eval (TVD/JSD/Brier/CE/Wasserstein/ECE)
        ├── ksenias_base8/       ← matched-only, 8 countries
        ├── co2_8/               ← matched-only, 8 countries
        └── usamex_canonical/    ← full 2×2 matched+cross (from repo DPO_eval_WVS)
```

## Adapters live on HuggingFace Hub (decision 2026-08-19)

**`Bonorinoa/SCA2-phase2-adapters`** (private model repo) — 16 QLoRA adapters:

| Subfolder | Countries | Files |
|---|---|---|
| `base8/` | CHN JPN GBR USA MEX ARG DEU RUS (Ksennia) | 274 |
| `co2_8/` | IND IDN NGA EGY TUR NLD BRA GRC (EconLLM) | 230 |

Local working copy: `SCA2_PofW/data/phase2/adapters/` (7.6 GB — gitignored, keep as backup).
Drive copies were purged (2026-08-19) to stay under the ~20 GiB personal quota; sources remain intact
(Ksennia's shared folder `1IopTI6n9xMMNihsoRu-8B_DGQ-qX-3hs` + `MyDrive/DPO_CO2/dpo_qlora_adapters/`).
Load with `PeftModel.from_pretrained(base, "Bonorinoa/SCA2-phase2-adapters", subfolder="co2_8/BRA")`.

## Provenance

| Canonical path | Source | Objects | Size | Copied |
|---|---|---|---|---|
| `eval/gps/ksenias_base8/` | Shared folder `1GppMTKt3ZX6hgez4zby3Wzl_mFRO8Ncr` ("eval_results", Ksennia) | 28 | 5.0 MB | 2026-08-19 |
| `eval/wvs/ksenias_base8/` | Shared folder `16skQIR7m6YjINxlH1Ma9wXa1rkC-5eN7` ("eval_results_wvs_wave7_new", Ksennia) | 76 | 49.8 MB | 2026-08-19 |
| `eval/gps/co2_8/` | `MyDrive/DPO_CO2/eval_results/` (EconLLM CO2 run) | 18 | 4.9 MB | 2026-08-19 |
| `eval/wvs/co2_8/` | `MyDrive/DPO_CO2/eval_results_wvs_wave7/` (EconLLM CO2 run) | 237 | 223.6 MB | 2026-08-19 |
| `eval/wvs/usamex_canonical/` | repo `DPO_eval_WVS/eval_results_wvs_wave7/` | 45 | 18 MB | 2026-08-19 (upload pending) |
| `docs/CO2_run/` | repo `DPO_train_test/CO2_run/` (CO2_RUN.md, eval summary, scripts, WVS docx/PNG) | 17 | 19.5 MB | 2026-08-19 |
| `analysis/` | repo `analysis/phase2/` (11 scripts + outputs + 10 figures + README) | 65 | 7.6 MB | 2026-08-19 |
| `adapters/base8/` | Shared folder `1IopTI6n9xMMNihsoRu-8B_DGQ-qX-3hs` ("dpo_qlora_adapters", Ksennia) | 274 | 4.23 GB | 2026-08-19 |
| `adapters/co2_8/` | `MyDrive/DPO_CO2/dpo_qlora_adapters/` (EconLLM CO2 run) | 230 | 3.34 GB | 2026-08-19 |

Ksennia's folders are **copied, never moved** — her originals remain untouched in Shared with me.

## Adapter bank (16 adapters, 13 distinct sign-vector profiles)

| Bank | Countries | Owner | Run doc |
|---|---|---|---|
| base8 | CHN JPN GBR USA MEX ARG DEU RUS | Ksennia | `DPO_train_test/Base_run/` (fork hashes in `CO2_RUN.md`) |
| co2_8 | IND IDN NGA EGY TUR NLD BRA GRC | EconLLM | `DPO_train_test/CO2_run/CO2_RUN.md` (branch `feat/co2-adapters`) |

- Base model `meta-llama/Llama-3.1-8B-Instruct`; DPO + QLoRA (r=16, α=32, β=0.1, 1 epoch, 526 train / 132 eval shared split; `PROMPT_COUNTRY_CONDITIONING=False`). Hyperparameters identical across banks.
- Production bank: 658 D_syn pairs (G = sign(z)); **not** the QC-599 subset.
- Label-identical profile pairs within the 16 — **verified from `country_gps.dta` (2026-08-19, `analysis/phase2/03_sign_vector_profiles.py`)**: MEX==RUS, EGY==IDN, GRC==IND ⇒ **13 distinct sign-vector profiles** (not 14; base-8 alone has 7, not 6 — Ksennia's "6 unique" from the meeting notes is not supported by GPS sign vectors; it likely reflects eval-behavioral similarity). These are sign-vector classes, NOT a cultural taxonomy.

## Data-format notes (for the unified analysis build)

- **GPS reward-recovery row schema** (both banks): `model, eval_country, country, item_id, gps_dimension, prompt, chosen, rejected, generated_answer, ref_chosen_logp, ref_rejected_logp, adapter_chosen_logp, adapter_rejected_logp, ref_margin, adapter_margin, dpo_reward_delta, dpo_pref_prob, dpo_prefers_chosen`.
- **Base-8 GPS source of truth = `reward_recovery_<CC>_adapter_on_<CC>.csv`** (ISO3, 132 rows incl. header = shared 526/132 eval split, self-mode). `<CC>_adapter.csv` is byte-identical (verified md5 for CHN/MEX/USA) — dedupe.
- **Stale/legacy artifacts in Ksenia's GPS folder (do NOT use):** `reward_recovery_adapter_summary.csv` + `dimension_summary.csv` use pilot-era `Mexico_adapter`/`US_adapter` naming with a 70-row eval set; `reward_recovery_all_adapters.csv` contains RUS rows only; `*_1.csv` are older duplicates. **Cross-eval (adapter i on country j) exists ONLY for USA↔MEX** (pilot 2×2, summary level only) — recompute per-dimension metrics from the ISO3 row files instead.
- **WVS eval designs (verified from the CSVs):** `usamex_canonical` = full 2×2 (base, USA_adapter, MEX_adapter × {USA, MEX}, 35 items/cell); `ksenias_base8` = **matched-only** (8 adapters on own country) + base×8 (its `survey_matched_vs_cross_*.csv` shells are EMPTY); `co2_8` = **FULL 8×8 cross grid** (277 matched + 1939 cross + 277 base rows; EGY eval has 32 items, others 35). The CO2 cross grid is the workhorse for matched-vs-cross analysis on the WVS surface.
- `population_response_distributions.csv`: identical schema across all runs (`eval_country, question_id, ..., population_prob, weight_column`).
- **Aux data (repo, tracked):** `data/phase2/aux/wdi.csv` — World Bank WDI `NY.GDP.PCAP.PP.KD` (PPP, constant 2017 US$), 2015–2019, all countries (from the cvprofiles lane cache). Used by `analysis/phase2/10_development_restrictions.py` and `11_twin_gdp.py`; scripts fall back to the cvprofiles cache if the local copy is missing. Education control is Q275 (WVS ISCED) computed from the local parquets — no fetch needed.
- **Session-2 analysis outputs (2026-08-19, in `analysis/outputs/`):** `twin_gps_clusters.csv`, `twin_wvs_cfst.csv`, `twin_adapter_cfst.csv`, `twin_adapter_itemdiff.csv`, `trust_class_bridge.csv`, `eval_08_summary.json` (twins + trust classes); `temp_scale_{pooled,by_family,by_country,Tstar,cfst_rank,base_reference}.csv` (temperature sweep); `development_restrictions.csv` + `development_{human,adapter}_by_country.csv` + `twin_gdp_pairs.csv` (development tests).
- Adapter folder naming: base8 uses `US/` (not `USA/`); co2_8 uses ISO3.
- WVS question map: repo `DPO_eval_WVS/question_map_wvs_edited.csv` — 35 unseen items (30 mapped to 6 GPS dims + 5 demographics). Q12–Q14 thrift/perseverance (patience), Q57/Q106/Q107/Q109/Q174/Q176/Q177/Q178/Q179/Q195 trust-family mapping per the direction audit (`llm-construct-validity` skill).
- CO2 generated answers show style+direction shifts (e.g. GRC/IND adapters generate refusal-styled text on positive-reciprocity items) — qualitative mechanism evidence, not just numbers.

## Sync procedure

```bash
# Pull Ksennia's eval folders to local mirror (repo data/phase2/raw/)
rclone copy ksenias_gps: <repo>/data/phase2/raw/gps/ksenias_base8/
rclone copy ksenias_wvs: <repo>/data/phase2/raw/wvs/ksenias_base8/
rclone copy sca2drive:SCA2_phase2/eval/wvs/co2_8 <repo>/data/phase2/raw/wvs/co2_8/

# Push updated canonical eval to Drive
rclone copy <repo>/data/phase2/raw/wvs/usamex_canonical/ sca2drive:SCA2_phase2/eval/wvs/usamex_canonical/
```

- rclone config: `~/.config/rclone/rclone.conf` (refresh token auto-renews).
- Same-account copies are server-side (`--drive-server-side-across-configs` when crossing remote names).

## Warnings

1. **rclone shared client_id is being retired during 2026** — plan a custom client_id (Google Cloud project) before then; the token in this manifest's remotes was minted 2026-08-19.
2. **agonz439's Drive has a personal cap of ~20 GiB** (`rclone about`'s pool numbers are the university quota, NOT yours). Observed: `storageQuotaExceeded` at 19.5 GiB used (2026-08-19). Budget Colab outputs accordingly; trash counts against quota — empty it periodically (`rclone cleanup sca2drive:` — destroys trashed files permanently).
3. Local mirror is a *working copy* — Drive is canonical for eval; HF is canonical for adapters.
4. Adapters: HF private repo `Bonorinoa/SCA2-phase2-adapters` is the canonical home; local `data/phase2/adapters/` (7.6 GB) is the backup. Do not delete both.
