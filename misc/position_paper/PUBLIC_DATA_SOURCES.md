# What can be made public (and what cannot)

The replication path for this paper is **not** "make the whole Drive folder public."

## Publish (our artifacts)

| Object | Where it lives now | Public home |
|---|---|---|
| 16-country option-probability CSVs (~80 MB) | local `data/phase2/raw/wvs/` (gitignored); partial copy on `sca2drive:SCA2_phase2/eval/wvs/` | a **dedicated** public Drive folder *or* a Hugging Face dataset, hashed in `reproduce_tables.py` |
| Persona + adapter-persona CSVs | same | same folder |
| Derived analysis tables | already in git (`analysis/phase2/outputs/`) | git |
| Adapter weights (~7.6 GB) | private HF `Bonorinoa/SCA2-phase2-adapters` (HTTP 401) | flip that repo to **public** when you are ready; needed only to score *new* batteries |

## Do not publish

| Object | Why |
|---|---|
| WVS Wave 7 `.dta` / country parquets | WVSA license; paper already says we do not redistribute |
| GPS microdata / `country_gps.dta` if the license forbids it | obtain from Falk et al. |
| Anything else sitting next to those files in a mixed Drive folder | a public share of `MyDrive/SCA2_phase2` as a whole is unsafe until you have listed every file |

## Recommended layout

1. Create `sca2drive:SCA2_phase2/public_eval/` containing **only** the option-probability CSVs and population *aggregates* we computed (not respondent-level files).
2. Share that folder as "anyone with the link."
3. Set `SCA2_EVAL_REMOTE=sca2drive:SCA2_phase2/public_eval` (or zip it and set `SCA2_EVAL_URL`).
4. Flip the HF adapter repo public when the team agrees.
5. Ship `analysis/phase2/reproduce_tables.py` in the git repo.

A Zenodo DOI is still better for a journal (immutable). Drive+HF is enough for the arXiv working paper if the script pins names and we record md5s.
