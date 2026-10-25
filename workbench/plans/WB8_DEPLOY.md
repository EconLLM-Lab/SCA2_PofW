# WB8 deploy: Workbench v1.6 to the public Space (CP26-ED)

Card `t_5066d83f`, route claude-opus-5-5 (anthropic) via the kanban worker. Date 2026-10-24.

## Step 1 · Precondition

- `plans/WB8_VERIFICATION.md` line 1: `VERDICT: PASS-WITH-NOTES` (card `t_3a5c9a4c`, GLM cross-family). Its five notes are
  headed "non-blocking, none about data": the "Paper A" footer label, a PNG-count slip in the candidate record, untracked
  build inputs, footer only on the landing view, iteration folders local-only. None concerns shipped data -> deploy.
- Candidate: built from `4984189` (`WB8_CANDIDATE.md`); the worktree HEAD `e7bf22d` adds only the candidate record and a
  screenshot (`git diff --stat 4984189 e7bf22d`: 2 files under `plans/`).

## Step 2 · Bundle identity (local)

- `shasum -a 256 dist/wb8_candidate/deploy_bundle.tar.gz` = `2fabb433bf063795a8d9f3f9952c5049291619decd3268609fe4126de3923eab` (equals the record).
- manifest sha256 = `3d415b938684bb82f4e6551f04e7bb9d86fc9ebc5cc0963f6820a22083891588` (equals the record).
- Extracted to scratch `wb8d/site`: 376 files.

## Step 3 · Space before upload

- `space_info`: sha `6e4d2730` (v1.5 from `890ead3`), private False, stage RUNNING, `used_storage` 944,144,988 B, no `app_file`.
- The live v1.5 `README.md` body equals the tracked `deploy/SPACE_README.md` except the `Build:` line, so the tracked card was used.

## Step 4 · Upload

- Space README = `deploy/SPACE_README.md` with `{COMMIT}`=`4984189`, `{FILES}`=376, `{ARCHIVE}`=`2fabb433bf06`; front matter
  `sdk: static`, no `app_file` (grep count 0).
- `HfApi.upload_folder(repo_type="space", folder_path=<scratch>/site, delete_patterns=["*", "!README.md", "!.gitattributes"])`,
  message "v1.6 from 4984189 (Paper B journal-version footer; WB8-V t_3a5c9a4c PASS-WITH-NOTES)" -> Space commit
  **`77e3e612e5608ccd0605b4c558475350839ea4f1`**, 4.5 s (unchanged LFS objects deduplicated by the Hub).
- Token read from the profile `.env` inside the script; never printed.

## Step 5 · File-by-file check (Space vs manifest `3d415b93…`)

| check | result |
|---|---|
| manifest files | 376 |
| Space files | 378 = 376 + `README.md` + `.gitattributes` |
| missing | 0 |
| extras | `.gitattributes`, `README.md` only |
| size mismatches | 0 |
| sha256 mismatches | 0 (173 LFS files by `lfs.sha256`; 203 small files re-downloaded with `force_download=True` and hashed) |
| stage / private | RUNNING / False |
| `used_storage` | 944,144,988 B (0.944 GB ≤ 0.95 GB). Reported value unchanged from before the upload; the only new object is the 750 KB JS (non-LFS), and the Hub may refresh this figure late. |
| `app_file` | None |

## Step 6 · Live checks (static host `https://econllm-sca2-workbench.static.hf.space`)

- curl: `/` -> 302 to `/index.html`, which references `assets/index-BaJ78cEn.js` (the v1.6 asset); `/sca2/index.html` 200;
  `/exports/index.json` 200; `/assets/index-BaJ78cEn.js` 200 (749,997 B, contains the new sentence); old v1.5 asset
  `/assets/index-ElQYjXeR.js` 404 (deleted by `delete_patterns`).
- Fresh Chromium (Playwright, headless, 1440x860), three separate new contexts, cache-busting query, timer from `goto`
  (wait `commit`) until the footer exists, the hero SVG has content and no loading card is visible:

| run | cold landing ready | new footer sentence | "extends the method" absent | arXiv:2610.06562 kept | console errors / page errors / failed requests |
|---|---|---|---|---|---|
| 1 | 2.99 s | yes | yes | yes | 0 / 0 / 0 |
| 2 | 2.32 s | yes | yes | yes | 0 / 0 / 0 |
| 3 | 2.72 s | yes | yes | yes | 0 / 0 / 0 |

  Footer sentence checked verbatim: "Paper B, the journal version in preparation, evaluates the method as a scoring
  instrument on a 42-country cohort; this workbench is its companion." Console warnings were not counted.
- Not re-checked live: the Ladder, Matrix and Cohort tabs (all data files are byte-identical to v1.5, which was checked
  live on 2026-10-21; the verifier loaded Ladder and Cohort from this exact bundle with 0 errors).

## Step 7 · README

- `workbench/README.md` gains a "v1.6 deploy" paragraph under Deployment; committed by explicit path only. Branch not pushed.

## Open for Augusto

1. The footer still says "(Paper A: arXiv:2610.06562)" (verifier note 1). It is live as written.
2. `plans/WB8_VERIFICATION.md` and this file are left uncommitted (the card allows committing only the README); the README
   cites both.
3. `data/` never opened. Rollback: the v1.5 tree is Space commit `6e4d2730`; re-uploading `dist/deploy_bundle.tar.gz`
   (archive `a94e5373…`) the same way restores it.
- Commit: `2dded0f` (workbench/README.md only), not pushed.
