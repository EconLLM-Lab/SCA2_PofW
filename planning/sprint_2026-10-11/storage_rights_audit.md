# SCA2 Paper B — human data storage-rights audit and proposed HF-first layout

**Date:** 2026-10-11 · Hermes (SCA profile) · read-only audit; no uploads, repo edits, deletions, or code changes performed.
**Scope:** storage/redistribution rights for the human survey data backing Paper B (GPS ∩ WVS7, 42 countries), and a Hub-first data layout that respects them.
**Companion docs:** `TWO_PAPER_CLAIM_LOCK.md` (claims), `PAPER_B_PROTOCOL_DRAFT.md` (frozen run protocol, 2026-10-09).
**Method:** local file inventory via Python (aggregates only; no respondent rows dumped) + primary-source terms fetched 2026-10-11. Claims from local file inspection carry no citation; external claims carry ledger citations below.

## TL;DR — concrete recommendation

1. **Keep raw human microdata local-only.** WVS Wave 7 respondent data is non-redistributable [1][2]; GPS data "must not be transferred to third parties without prior approval" [6]. The repo already enforces this with `.gitignore` (verified via `git check-ignore -v`) and its own README statement that the 42 parquets are "licensed respondent extracts… not redistributed in git."
2. **HF-first for everything that is not human microdata.** The existing private, gated `Bonorinoa/SCA2-paper-b-adapters` (42 adapters) is the correct pattern — extend it with two new repos: `SCA2-paper-b-synthetic-bank` (private initially) and `SCA2-paper-b-manifests` (tiny, revision-pinned). No respondent rows in any Hub repo.
3. **Remove Google Drive from the Paper B critical path** (frozen protocol §5 currently routes the ref cache and eval CSVs to Drive; the runbook makes Drive the only durable state). Redirect durable artifacts to the HF repos; preserve all historical Drive copies as-is — they are provenance, not clutter.
4. **Private HF is third-party hosting, not a safe harbor:** HF's ToS makes you "solely responsible for the Content you post" and requires that you have "the right to do so" [8]. Public download ≠ redistribution permission.

## 1. Primary-source terms

### 1.1 World Values Survey

WVS Data Download documentation: "When downloading files and result reports you will be asked to **register** at no charge and agree with the WVS non-redistribution data use license." [2]

Integrated EVS/WVS Conditions of Use (retrieved verbatim from the WVSA site's Conditions-of-Use panel; the text is JS-rendered and not visible to plain curl): the data "are available without restrictions, provided that 1. They are used for non-profit purposes 2. **Data files are not redistributed** 3. Correct citations are provided wherever results based on the data are published." The panel also states "only anonymous data are available to users," with confidentiality checked by national teams before deposit. [1]

### 1.2 Global Preferences Survey

GPS downloads page: "Our data can be accessed for further research. Please select the relevant datasets, questionnaires or supplementary material and accept the citation agreement. **Please note that these data must not be transferred to third parties without prior approval.**" The page stamps the material CC BY-NC-SA 4.0 and mandates citing Falk et al. (2018, QJE) and Falk et al. (2016, IZA DP 9674). [6] The GPS FAQ: "Is it legal to use the data and questionnaires for commercial purposes? **No.** All materials provided may only be used for non-profit and academic purposes." The individual-level dataset "contains a personal identifier which allows you to link this data with the Gallup World Poll 2012." [9]

Note the tension: a CC BY-NC-SA button next to a no-transfer clause. ShareAlike licensing and the contractual no-transfer restriction coexist; the stricter clause governs practical handling.

### 1.3 Hugging Face

HF Terms of Service ("Your Content"): "You are **solely responsible for the Content you post** … You represent and warrant that you have ownership, control, and responsibility for the Content you post or otherwise make available on our Website … and otherwise have the right to do so." [8] A private repo restricts *visibility*, not the uploader's obligation to hold redistribution rights. HF storage-limits doc distinguishes plan tables (Free = 100 GB private; PRO = 1 TB + pay-as-you-go at $18/TB/mo) and states public free storage is best-effort. [3]

### 1.4 Not verified this audit

- LAPOP AmericasBarometer terms (the repo's own `data/merged/DATASET_GUIDE.md` warns its terms "typically prohibit redistributing raw third-party data dumps"). **[unverified]**
- Meta Llama-3.1-8B-Instruct community-license obligations for distributing derivative QLoRA adapters (the runbook already requires `HF_TOKEN` and the existing adapters repo is gated). **[unverified]**

## 2. Local inventory (verified 2026-10-11, `SCA2_PofW`)

### 2.1 Raw human microdata — keep LOCAL-ONLY

| Asset | Path | Size | sha256 (16-hex prefix) |
|---|---|---|---|
| WVS7 full microdata | `data/WVS/WVS_wave7.dta` | 189.5 MB | `9e03bbf290e6aaae` |
| GPS individual-level (personal identifiers) | `data/GPS/GPS_dataset_individual_level/{individual_new,individual_v11_new}.dta` | 12.0 + 11.9 MB | — |
| GPS country-level aggregates | `data/GPS/GPS_dataset_country_level/{country_gps,country_v11}.dta` | 0.08 + 0.03 MB | `d9282968fc0feb5a` (country_gps) |
| 42× WVS7 respondent-extract parquets | `data/wvs_eval_full/*.parquet` | 2.5 MB total | `89b7e9147802e424` (USA) |
| Phase-2 raw WVS eval surfaces | `data/phase2/raw/wvs/{co2_8,ksenias_base8,persona_*}` | 311.9 MB | — |
| Merged surfaces (WVS + LAPOP) | `data/merged/*.parquet` | 0.5 MB | — |
| WVS documentation PDFs | `data/WVS/{Codebook,MasterQuestionnaire}.pdf` | 4.4 MB | — |

Coverage: `data/wvs_eval_full/_manifest.json` confirms exactly the 42-country GPS ∩ WVS7 intersection named in the frozen protocol §2; per-country parquets ~1.2–2.6k respondent rows each, columns = WVS meta + demographics + evaluation items (Q57, Q59, Q61, Q62, …). All of the above are git-ignored (verified). Derivatives inherit the source licenses: WVS-derived parquets inherit non-redistribution [1][2]; GPS aggregates inherit the no-transfer clause [6].

### 2.2 Model artifacts — Hub-eligible

- `data/phase2/adapters/` — 16 Paper A QLoRA adapters (~2.6 GB local, two checkpoints each; already HF-hosted at gated `Bonorinoa/SCA2-phase2-adapters`, commit `03c43dfd…`).
- `Bonorinoa/SCA2-paper-b-adapters` — the 42 Paper B adapters (unauthenticated API probe returns HTTP 401 ⇒ exists, private/gated). Repo HEAD `38ed2ee` (2026-10-10): "upload each adapter to the HF Hub (durable artifact bus, independent of the Drive FUSE)".

### 2.3 Synthetic bank — sign-off gate before Hub

`synthetic_generation/outputs/gps_sign_relabel_all/` — 78 × `D_syn_<CC>.jsonl` (122.8 MB), 658 shared pairs × 76 countries, `run_id=gps_sign_relabel_all_20260816_004545Z`, `labeling_rule=deterministic_sign`. **NOT git-ignored — currently tracked in git.** Verified frozen-protocol gates on 2026-10-09 (protocol §3): identical prompts/labels/order across cohort files, zero sign-rule mismatches, no WVS outcomes and no country names in training text. The scenario text paraphrases the GPS battery, so per §1.2 the conservative posture is: private initially; public only after PI sign-off that the bank is sufficiently transformed from the source instrument.

### 2.4 Current Drive footprint (historical, preserve)

- `MyDrive/SCA2_phase2/` — canonical per `data/phase2/MANIFEST.md`; Drive copies purged 2026-08-19 to stay under a ~20 GiB personal quota, "sources remain intact."
- Pinned historical zip `drive.google.com/uc?export=download&id=1lIAx0ueSpgaZPmAzNbFSD31ddGQH7Nqo` in `README.md`, `replication/README.md`, and `analysis/phase2/reproduce_tables.py` (`SCA2_EVAL_URL`).
- Frozen protocol §5 and `paper_b/RUNBOOK.md` still route new durable state (ref cache, eval CSVs, pilot artifacts) to Drive — the dependency this audit recommends removing going forward.

## 3. Artifact taxonomy → storage posture

| Class | Examples | Rights basis | Posture |
|---|---|---|---|
| Raw human microdata | `WVS_wave7.dta`, GPS `.dta`, 42 wvs_eval_full parquets, `phase2/raw/wvs/` | WVS non-redistribution [1][2]; GPS no-transfer [6] | Local-only; never to Hub without written permission; rebuildable from source by anyone with access |
| Aggregate derivatives | `country_gps.dta`, `survey_metrics_by_gps_dimension*.csv` | GPS no-transfer applies to "these data" [6] | Local-only; Hub only with prior briq approval — do not assume aggregates are exempt |
| Survey question text | `data/GPS/*.pdf` questionnaires, `data/WVS/{Codebook,MasterQuestionnaire}.pdf` | CC BY-NC-SA + citations [6]; WVS registration basis [2] | Local-only; not for Hub without approval |
| Synthetic bank | `D_syn_*.jsonl` | Own generation run; paraphrases GPS battery | Private HF repo initially; public only after PI sign-off |
| Adapters (QLoRA) | `data/phase2/adapters/`, paper-b adapters | Own artifacts on gated Llama base | Private, gated HF repos (existing pattern) |
| Manifests / hashes / provenance | `_manifest.json`, `replication/HASHES.md`, run manifests | Own artifacts | Tiny private HF repo; revision-pinned |

## 4. Proposed HF-first Paper B layout

| Repo | Visibility | Contents | Status |
|---|---|---|---|
| `Bonorinoa/SCA2-paper-b-adapters` | private, gated | 42 QLoRA adapters, `adapters/<CC>/` | exists (HTTP 401 probe) |
| `Bonorinoa/SCA2-paper-b-synthetic-bank` | private initially | 78 `D_syn_*.jsonl` (or one merged jsonl, 122.8 MB) + `gps_z_vectors.json` + `manifest.json` + bank sha256 | proposed; upload gated on PI sign-off |
| `Bonorinoa/SCA2-paper-b-manifests` | private | `_manifest.json` (42-country list, item map, per-file sha256), adapter commit SHAs, bank hash, config hash, git SHA, per-run provenance | proposed |

**Revision pinning.** Every manifest entry records: artifact class, source URL + retrieval date, source sha256, generated-artifact sha256, HF revision SHA, builder script + git SHA. Raw human data appears in manifests as **hashes only**, never as rows.

**Why separate repos.** Independent licensing lifecycles: the adapters and manifests are publishable once Paper B lands; the bank may stay private indefinitely pending the GPS question-text judgment; nothing in one repo's history can tangle another's. HF storage headroom is ample for this footprint (~2.7 GB total) on any plan [3] — but verify the *actual* account quota in Billing settings at upload time; never infer it from the generic plan table.

## 5. Risk register

- **R1 — GPS question-text PDFs are tracked in git.** `data/GPS/*.pdf` (incl. `GPS_Falk_QJE.pdf`) are git-tracked (`git ls-files` verified). If the remote is public, these are publicly exposed without the download-page's citation agreement context. Mitigation: verify remote visibility; if public, untrack (keep local), or obtain briq approval. Not fixed here (no repo edits allowed).
- **R2 — Drive quota fragility.** Drive copies already purged once (2026-08-19) under a ~20 GiB quota; pinned zip links can break on quota or sharing changes. Mitigation: HF manifests repo as the durable machine-readable record; keep historical Drive links as-is.
- **R3 — Frozen-protocol wording.** Protocol §5 says the ref cache is "stored on Drive"; §7 routes eval CSVs to Drive. Revising the *run* protocol (claims lock untouched) is required for the HF-first layout; flag for the next dated amendment rather than editing silently.
- **R4 — Bank licensing judgment.** Paraphrase sufficiency vs the GPS instrument is a PI call, not settled by license text [6][unverified].
- **R5 — Llama gating.** Keep both adapters repos gated; `HF_TOKEN` requirement already in the runbook [unverified — Meta license text not pulled].

## 6. Immediate actions (none taken — audit is read-only)

1. Verify `SCA2_PofW` git remote visibility; untrack GPS PDFs if public.
2. On PI sign-off for the bank: create the two new repos per §4 and update the runbook's durable-state line.
3. At the next protocol amendment: replace "stored on Drive" with the HF manifests repo; Drive = historical mirror.
4. If aggregates or the bank are ever shared beyond the local machine, contact briq first (per the FAQ's approval requirement) [9].

## 7. Licensing unknowns

- WVS Wave 7-specific license text (vs the Integrated 1981–2014 conditions quoted) sits behind the interactive download flow — requires a real registration event to read.
- GPS "prior approval" procedure — FAQ gives only a mailbox; no documented process.
- LAPOP AmericasBarometer terms — not retrieved. **[unverified]**
- Meta Llama community license terms for derivative adapter hosting — not pulled. **[unverified]**
- Synthetic bank's transformation distance from the GPS instrument — PI judgment. **[unverified]**
- Actual HF account quota — check Billing settings at upload time [3].

## Sources

[1] https://www.worldvaluessurvey.org/WVSDocumentationWVL.jsp — WVS Longitudinal files — terms
[2] https://www.worldvaluessurvey.org/WVSContents.jsp?CMSID=Documentation — WVS Wave documentation (registration + non-redistribution license)
[3] https://huggingface.co/docs/hub/en/storage-limits — HF Hub storage limits
[6] https://gps.econ.uni-bonn.de/downloads — GPS downloads
[8] https://huggingface.co/terms-of-service — Hugging Face Terms of Service
[9] https://gps.econ.uni-bonn.de/faq — GPS FAQ (non-commercial, citations, approval)
