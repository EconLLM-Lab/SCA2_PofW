# H1 Hub upload: phase-1 cohort exports + frozen T4 instrument + evidence → private artifacts dataset (self-verifying)

Card `t_54c5b1df`, board sca2-paper-b, assignee `sca`, status at export: done
Created 2026-10-19 07:53 MST. Exported 2026-10-19 by the CP assembly card as a dated record, not status.

## Body

Upload the phase-1 workbench cohort artifacts to the PRIVATE dataset `Bonorinoa/SCA2-paper-b-artifacts` (repo_type=dataset) using your own huggingface-hub skill/token. The PM shell is not HF-logged-in and must not read your .env, which is why this is yours. No Colab, no GPU, 0 CU.

Root (worktree): /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.worktrees/adapter-brain-vizualization  (branch Adapter-Brain-Vizualization, pushed at 692d611; git is clean, do NOT commit or modify tracked files)
Python: `env -u PYTHONPATH uv run --project workbench --with huggingface_hub python ...` (PYTHONPATH shadows venvs).

## Exact mapping (repo prefix `workbench_cohort/phase1_nf4_t4/`)
| local (relative to root) | repo path | approx |
|---|---|---|
| workbench/exports/phase1_nf4_t4/ EXCLUDING `queue.lock` and `.index-staging/` | workbench_cohort/phase1_nf4_t4/exports/ | 23 GB, ~9.8k files |
| workbench/plans/gpu_cohort/frozen_nf4_t4/ (all files, incl. *.safetensors) | workbench_cohort/phase1_nf4_t4/nf4/ | 3.4 GB, 228 files |
| workbench/plans/gpu_cohort/benchmark/ (all files) | workbench_cohort/phase1_nf4_t4/evidence/benchmark/ | 380 MB |
| workbench/plans/gpu_cohort/c1/ EXCLUDING any `parts/` dir and `*.tar`/`*.tar.gz` (redundant shards of nf4/) | workbench_cohort/phase1_nf4_t4/evidence/c1/ | small |
| a new file with one line `692d611` | workbench_cohort/phase1_nf4_t4/GIT_COMMIT.txt | |

Suggested method: build a staging tree of SYMLINKS (not copies, disk matters) under ~/.hermes/cache/scratch/h1_stage/ mirroring the repo paths, then `HfApi().upload_large_folder(repo_id=..., repo_type="dataset", folder_path=stage)` (resumable). Verify symlinks are followed; if not, use hardlinks (same volume).

## Run it DETACHED and self-verifying
The upload may take hours. Write ONE script (keep it in ~/.hermes/cache/scratch/h1_upload.py) that: (1) uploads; (2) then lists the remote prefix recursively (`list_repo_tree(..., recursive=True, expand=True)`) and checks, for EVERY local file in the mapping: present remotely, same size, and for LFS files remote `lfs.sha256` == local sha256 (non-LFS: size + download-free check of blob is fine, or hash via hf_hub_download for files <1 MB); (3) writes the receipt JSON to `workbench/exports/phase1_nf4_t4_hub_receipt.json` (gitignored path) with: repo, head commit sha after upload, counts local/remote per subtree, bytes, n_mismatch, list of mismatches (max 50), started/finished timestamps, `pass` boolean. Launch with `nohup caffeinate -i ... > ~/.hermes/cache/scratch/h1_upload.log 2>&1 &`.

Poll with long sleeps (terminal calls up to ~9 min). If it finishes within your turn budget, report the receipt. If not, `kanban_complete` with pid, log path and receipt path, stating explicitly that upload is IN PROGRESS (do not claim success).

## Fences
- Never print, echo, log or write the token anywhere; never pass it on a command line. Do not read other profiles' .env.
- Writes ONLY under `workbench_cohort/phase1_nf4_t4/` in that dataset. No deletes. Never touch `Bonorinoa/SCA2-paper-b-adapters`. Do not change repo visibility.
- Content is model internals + public item text only (PM checked: 0 respondent/population fields, 0 absolute paths in export manifests). Do not add anything from `data/`.
- Do not delete local files (PM decides local cleanup after verification).

## Handoff (five fields)
what was uploaded (counts/bytes per subtree) · remote commit sha + URL `https://huggingface.co/datasets/Bonorinoa/SCA2-paper-b-artifacts/tree/main/workbench_cohort/phase1_nf4_t4` · receipt path + pass/fail · anything excluded or failed · time taken.

## Runs

- run 48 sca: done/completed  H1 upload COMPLETE and self-verified (pass=true, 0 mismatches). 8,628 files / 28.56 GB under workbench_cohort/phase1_nf4_t4/ in private dataset Bonorinoa/SCA2-paper-b-artifacts; head e1687cf03d6833227c6e9b746ad45a9d59b7c140. Receipt: workbench/exports/phase1_nf4_t4_hub_receipt.json. ~56 min.

## Comments

