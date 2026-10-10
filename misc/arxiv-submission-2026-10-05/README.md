# arXiv submission package — Synthetic Cultural Agents from Aggregate Anchors

| Field | Value |
|---|---|
| Live paper | https://arxiv.org/abs/2610.06562 |
| Version | v1 — submitted 2026-10-05, 15:48 UTC |
| Subjects | econ.GN; cs.CL |
| Pages | 20 ("Working paper — September 2026") |
| DOI | 10.48550/arXiv.2610.06562 (DataCite, pending registration) |
| License | arXiv.org perpetual non-exclusive license (confirmed on the abs page 2026-10-09) |
| Source commit | `5664026` — tagged `arxiv-2610.06562-v1` |

## Contents

- `sca2-arxiv-source.zip` — the exact source bundle uploaded to arXiv.
- `sca2-arxiv-preview.pdf` — compiled preview of the uploaded source.
- The unpacked TeX source (the same files the zip contains): `main.tex`, the section
  files, `references.bib`, `tables/`, `figures/`.

## Provenance notes

- The correlation tables in the paper are reprinted from the committed
  `analysis/phase2/outputs/paper_a/country_item_scores.csv` (two-wave file,
  2026-09-25; see `replication/HASHES.md`). The Drive zip linked in the paper
  (17 September 2026) is *not* the source of the reported trust correlation.
- Adapter weights: https://huggingface.co/Bonorinoa/SCA2-phase2-adapters
  (gated; commit `03c43dfd27c9535283feb78ffa727da3bfa1b966`).
- This folder is the upload-time provenance record; it is not the live paper
  source. Post-arXiv edits live in the normal repository tree.