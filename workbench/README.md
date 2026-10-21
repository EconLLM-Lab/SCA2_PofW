# SCA2 workbench

The workbench is a viewer and capture toolchain for the Synthetic Cultural Agents project (EconLLM Lab, phase 2).
It lives on the branch `Adapter-Brain-Vizualization`, separate from the Paper B code branch `feat/paper-b-cohort`
(that branch's root README points here, and this branch's root README points back).

Reading direction is one way. The workbench reads Paper B artifacts (model-only scores, sign profiles, adapters'
captures). Paper B claims never depend on a workbench result, and workbench compute is never counted as Paper B's.
Decision recorded 2026-10-19 in `planning/DECISIONS.md` on `feat/paper-b-cohort`.

## What it shows

Five steps on one story page (`viewer/public/sca2/index.html`): signs to profiles to countries; country scores by
route; own-bit direction and behavioral cross-talk; C9 label recovery against the four-cell TVD audit; and saved
adapter/sign-prompt forward passes, with click-through to the tensor viewer. Marks come from banked sources.

- A 42 country by 7 surface heatmap over four routes (cohort-1 adapters, bank-2 adapters, sign prompt, country-named
  persona), grouped by six-sign profile. The values are the model-only scores banked in the artifacts dataset.
- A 6-bit by 7-surface factorial matrix, and the cross-talk view (a behavioral decomposition, not a neural mechanism).
- The C9 aggregate four-cell TVD means and profile-block contrasts, beside model-only synthetic-label recovery and
  per-country recovery/accuracy dots. It carries no per-country TVD, human means or respondent distributions.
- The tensor viewer (`?tab=c` ladder, `?tab=b` matrix, `?tab=a` 3D object) over float64 captures of the residual stream,
  per-head and MLP writes, and direct logit attribution. Featured adapter and sign-prompt links share the same items.
  The contract is `spec/export_contract.md`.

## Run

```bash
cd workbench
PYTHONPATH=src uv run python -m sca2_workbench.export --pair smol_base smol_inst   # captures; exports/ is gitignored
cd .. && env -u PYTHONPATH HF_TOKEN= uv run --project workbench pytest workbench/tests -q
cd workbench/viewer && npm install && npx vite                                     # http://127.0.0.1:5178
```

The story page is `/sca2/index.html`; the root page links to it. Viewer details: `viewer/README.md`.

## Rebuild the deploy bundle

```bash
# from the worktree root; each step exits non-zero on failure
env -u PYTHONPATH HF_TOKEN= uv run --project workbench --with pandas python workbench/scripts/build_sca2_data.py
env -u PYTHONPATH HF_TOKEN= uv run --project workbench python workbench/scripts/build_deploy_bundle.py
env -u PYTHONPATH HF_TOKEN= uv run --project workbench python workbench/viewer/screens/sca2/verify_bundle.py \
    workbench/dist/deploy_bundle.tar.gz <fresh-scratch-dir> --report workbench/viewer/screens/sca2/bundle-check.json
```

`build_sca2_data.py` writes the story JSON from Paper B's banked inputs, selecting C9 rows by exact claim id and
keeping source digests and logical input paths. `build_deploy_bundle.py` runs a fresh `npm run build`, copies an allowlisted static site and a closed set of
capture files, and fails when either the archive or the payload exceeds 950,000,000 bytes. To stay below the Space's
1 GB storage ceiling, it keeps every featured adapter pair but only the largest saved-margin prompt pair per sign bit. It writes
`dist/deploy_bundle.tar.gz` and a sidecar `dist/deploy_bundle.tar.manifest.json` that hashes each shipped file.
`verify_bundle.py` recomputes every hash and the dependency closure. The record of the last verified build is
`plans/WB4_ACCEPTANCE.md` (producer) and `plans/WB4_VERIFICATION.md` (independent verifier): 143 files, about 918.4 MB
of payload, built from `d8a232d`. Two later commits change only `index.html`, the CSS and the checks-table wording
(`1c2a2dd`, `c52480d`). Earlier records: WB1 (94 files, `e86d4c2`), WB3 (158 files, `2309ab0`) and WB3.1 (142 files,
`67200ce`).

## Deployment

Public static Hugging Face Space `EconLLM/sca2-workbench`
(https://huggingface.co/spaces/EconLLM/sca2-workbench). It was made public by Augusto on 2026-10-20.

The current deploy is v1.2.1, 2026-10-21, from `c52480d`:
- all 143 manifest files are on the Space, with 0 sha256 or size mismatches (checked file by file after upload);
- stage RUNNING;
- storage 0.916 GB.

Earlier deploys:
- WB2 on 2026-10-19 from `e86d4c2` (receipt `plans/WB2_DEPLOY_RECEIPT.json`);
- v1 on 2026-10-20 from `2309ab0`;
- v1.1 on 2026-10-20 from `67200ce`.

Two Hub pitfalls:
- **The 1 GB cap counts every LFS object in the Space's history, not just the current files.** When an upload is
  refused, squash the history (`HfApi.super_squash_history`), then `permanently_delete_lfs_files` for objects the
  current tree no longer references. On 2026-10-21 this freed 0.135 GB.
- **Do not set `app_file` in the Space README.** For a static Space it re-roots the site at that file's folder, so
  `/sca2/index.html` returns 404 and `/exports` breaks.

Keep the payload at 0.95 GB or less. Deploy from this worktree's `dist/deploy_bundle.tar.gz`: the bundle includes
gitignored files, so a fresh clone cannot rebuild it. Augusto invites co-authors and grants access. A static Space has no live
inference.

## Data policy

The bundle carries precomputed captures and model-only scores. It carries no human respondent rows, no country-level
human means or distributions, no adapter or base-model weights, no tokenizer and no inference runtime. GPS signs and
public survey item text are not licensed human responses. Privacy is checked structurally (an allowlist of story fields
in `tests/test_sca2_story_data.py`), not by a banned-substring search. Live adapter chat is deferred to its own card with
a cost and data-rights check. The Space went public on 2026-10-20, ahead of co-author review; the data-rights check for that is open in the main repo STATUS.

## Status of the audit

`AUDIT.md` section 17 records W2 (prompt-route capture), W3 (mechanisms), WB1 (story and bundle) and WB2 (deployment)
with their verifier outcomes. Read it before quoting any workbench result.
