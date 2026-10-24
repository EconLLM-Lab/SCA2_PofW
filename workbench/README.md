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

**v1.6 deploy**, 2026-10-24, from `4984189` (Space commit `77e3e612`). It changes one sentence: the landing footer now
says that Paper B is the journal version in preparation, evaluating the method as a scoring instrument on a 42-country
cohort; the arXiv:2610.06562 citation is kept. Every data file, including `sca2/sca2_data.json` and all of `exports/`,
is byte-identical to v1.5; only the JS asset (+63 B) and `index.html` differ. Records: `plans/WB8_CANDIDATE.md` (E1),
`plans/WB8_VERIFICATION.md` (`t_3a5c9a4c`, GLM cross-family): PASS-WITH-NOTES, notes not about data; deploy record
`plans/WB8_DEPLOY.md` (`t_5066d83f`).
- All 376 manifest files are on the Space (378 with `README.md` and `.gitattributes`), with 0 missing and 0 sha256 or
  size mismatches (173 LFS files by `lfs.sha256`; 203 small files re-downloaded and hashed). Archive sha256
  `2fabb433...`; payload 949,437,055 B. Stage RUNNING; private False; storage 0.944 GB; no `app_file`.
- Live, in three fresh Chromium contexts: the cold landing page is ready in 2.3 to 3.0 s, shows the new footer
  sentence, and logs 0 console errors, page errors or failed requests. `/sca2/index.html` and `/exports/index.json`
  return 200.

Previous deploy, v1.5, 2026-10-21, from `890ead3`. It adds the clamped-run and how-to-read text (WB7-W), Q57 across all 42 adapters and 26 sign
prompts in the Cohort tab (WB7-Q), a many-option headline for 10-point items, and a **human reference panel**: country-level
World Values Survey wave 7 shares, rounded to whole percent, as a descriptive reference (WB7-H, 56 cells; no respondent rows). Records:
`plans/WB7_PLAN.md`, `WB7H_ACCEPTANCE.md`, `WB7I_ACCEPTANCE.md`, `WB7_DATA_RIGHTS.md` (WB7-R: permitted with attribution) and
`WB7_VERIFICATION.md` (`t_ab5d175a`, GLM cross-family): PASS-WITH-NOTES, with N1 (the story intro still said "no human means or
distributions") fixed before deploy. Augusto confirmed the WB7-R ruling in writing on 2026-10-21 ("ship human layer").
- All 376 manifest files are on the Space (377 with its README, plus `.gitattributes`), with 0 sha256 or size mismatches (203 small non-LFS files
  re-downloaded and hashed). Stage RUNNING; private False; storage 0.949 GB. Archive sha256 `a94e5373...`; payload 949,436,992 B. The v1.4 identity check
  holds: 138 of 143 files identical, the 5 changed files are on the allowed list (two assets, `exports/index.json`, `index.html`, `sca2/index.html`).
- Live, in a fresh Chromium: the cold landing page opens in 3.6 s, with the card showing "Downloading saved model data · 0.3 of 5.7 MB · 5%".
  Reloads and the Matrix open in 0.5 s; the Ladder in 1.8 s; Cohort in 1.6 s; Cohort Q57 (68 comparators) in 8.9 s cold and 0.8 s again. Q57 China
  Ladder: log-odds change +5.33 (A -1.03, B 4.30; P("1") 0.26 to 0.99), human panel shows 64% for "Most people can be trusted". Q176 USA
  headline: average answer 5.6 to 6.2, most likely answer "5" (40%) to "6" (85%); human panel mode "5" (19%), mean 5.5. 0 console errors; `/sca2/index.html` returns 200.
  One earlier run of the check timed out waiting on a page for 400 s and was not reproduced in three later runs; treat a cold Cohort Q57 as seconds, not as guaranteed.
- Attribution on the Space: the WVS-7 citation, both GPS citations with the CC BY-NC-SA 4.0 notice, and "Built with Llama" with the license line, in the Space README and in both footers.
- The human file `human_ref/human_reference.json` is gitignored and never committed; the build takes it with `--human-reference`.

Previous deploy, v1.4, 2026-10-21, from `7b3a563`. It has a loading card with real download progress, an
interactive Cohort tab, plain language for social scientists, pop-up model sizes read from the manifest, and a plain
frame. Records: `plans/WB6L_ACCEPTANCE.md`, `WB6P_ACCEPTANCE.md`, `WB6K_ACCEPTANCE.md`; verifier `plans/WB6_VERIFICATION.md`
(`t_fb8b00a6`, DeepSeek): PASS-WITH-NOTES, with F1 and N5 fixed before deploy.
- All 143 manifest files are on the Space, with 0 sha256 or size mismatches. Stage RUNNING; storage 0.916 GB. The Space
  README comes from `deploy/SPACE_README.md`.
- Live, in a fresh Chromium: the cold landing page opens in 2.6 s, with the card showing "3.1 of 5.7 MB · 55%". Reloads,
  the Ladder and the Matrix open in 0.5 s; Cohort in 1.3 s; Cohort Q99 (8 comparators) in 3.3 s. 0 console errors.

Earlier deploys:
- WB2 on 2026-10-19 from `e86d4c2` (receipt `plans/WB2_DEPLOY_RECEIPT.json`);
- v1 on 2026-10-20 from `2309ab0`;
- v1.1 on 2026-10-20 from `67200ce`;
- v1.2 to v1.2.2 on 2026-10-21 from `1c2a2dd`, `c52480d` and `3c68a82` (whole-file fetches, uncacheable);
- v1.3 on 2026-10-21 from `fa04992` (range fetch and browser cache; WB5-V PASS).

Three Hub pitfalls:
- **The 1 GB cap counts every LFS object in the Space's history, not just the current files.** When an upload is
  refused, squash the history (`HfApi.super_squash_history`), then `permanently_delete_lfs_files` for objects the
  current tree no longer references. On 2026-10-21 this freed 0.135 GB.
- **Do not set `app_file` in the Space README.** For a static Space it re-roots the site at that file's folder, so
  `/sca2/index.html` returns 404 and `/exports` breaks.

- **The Hub serves LFS and xet files uncacheable.** Each file is a 302 redirect with `cache-control: no-store` to a
  freshly signed CDN URL, so the browser's HTTP cache never helps. The viewer therefore fetches byte ranges (the CDN
  returns 206 with a readable `Content-Range`) and keeps them in the Cache API itself.

Keep the payload at 0.95 GB or less. Deploy from this worktree's `dist/deploy_bundle.tar.gz`: the bundle includes
gitignored files, so a fresh clone cannot rebuild it. Augusto invites co-authors and grants access. A static Space has no live
inference.

## Data policy

The bundle carries precomputed captures, model-only scores and one human reference file: country-level World Values Survey wave 7 answer
shares (`exports/human_reference.json`, 56 country-question cells, rounded to whole percent, with n and the source). It carries no respondent
rows, no microdata, no adapter or base-model weights, no tokenizer and no inference runtime. WB7-R (`plans/WB7_DATA_RIGHTS.md`) ruled the
WVS wording, the binary GPS signs, the WVS aggregates and the Llama outputs "permitted with attribution"; Augusto confirmed in writing on
2026-10-21. Privacy is checked structurally (an allowlist of story fields in `tests/test_sca2_story_data.py`), not by a banned-substring
search. Live adapter chat is deferred to its own card with a cost and data-rights check. The Space went public on 2026-10-20, ahead of
co-author review. Augusto sends the courtesy emails to the WVSA Secretariat and the GPS team himself.

## Status of the audit

`AUDIT.md` section 17 records W2 (prompt-route capture), W3 (mechanisms), WB1 (story and bundle) and WB2 (deployment)
with their verifier outcomes. Read it before quoting any workbench result.
