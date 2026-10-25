VERDICT: PASS-WITH-NOTES

# WB8 verification: Workbench v1.6 candidate (CP26-EV)

Independent cross-family check of the E1 candidate record (`WB8_CANDIDATE.md`, produced by claude-sonnet-5-5).
Verifier: GLM (z-ai/glm-5.3 via openrouter, kanban run 146, card t_3a5c9a4c). Date: 2026-10-24/25 (MST).
Candidate head: `e7bf22d` (chain `a291f3b` ← `7534529` ← `bf5ab17` ← `4984189` ← `e7bf22d`, branch `Adapter-Brain-Vizualization`).
Probe: `~/.hermes/profiles/verifier/cache/scratch/wb8v/compare_manifests.py` (scratch — the fence allows only this review file inside the repo).

## 1. Diff scope `a291f3b..e7bf22d` — PASS

`git diff --name-status a291f3b..e7bf22d` (exit 0) touches exactly 7 paths, all in the allowed set:

| change | path | belongs to |
|---|---|---|
| M | `workbench/viewer/src/landing.ts` | wording (footer sentence) |
| A | `workbench/tests/test_landing_wording.py` | wording test |
| M | `workbench/scripts/build_deploy_bundle.py` | bundle builder |
| M | `workbench/tests/test_deploy_bundle.py` | builder tests |
| M | `workbench/.gitignore` | .gitignore (lines 27–32) |
| A | `workbench/plans/WB8_CANDIDATE.md` | candidate record (card E1's own artifact) |
| A | `workbench/plans/wb8_shots/landing-footer-1440x860.png` | curated screenshot |

- No W3b path in any commit: `git log a291f3b..HEAD --name-only | grep -i w3b` → empty, exit 1.
- Uncommitted state is only the W3b set: `M workbench/analysis/w3b/run_w3b.py` + `?? W3b_*`, `?? _discarded_W3/`, `?? plot_w3b.py`, `?? w3b/tests/` — untouched by the candidate.
- `.gitignore` effect: `git ls-files -i -c --exclude-standard workbench` = 62 files, all pre-existing force-adds under older rules (30 at `viewer/screens/sca2/` top level + 32 under `sca2/wb3/`). 0 tracked files match any *new* rule (`verified/`, `wb3v/`, `wb31v/`, `wb4v/`, `w3v_*`). Nothing deleted, nothing silenced.

## 2. Wording — PASS

- `viewer/src/landing.ts:95` footer now reads: "Paper B, the journal version in preparation, evaluates the method as a scoring instrument on a 42-country cohort; this workbench is its companion." — journal version, not extension/sequel.
- My own grep (`extends the method|sequel|follow-?up|builds on|earlier study|preprint`, case-insensitive) over `viewer/src`, `viewer/public/sca2/index.html`, `viewer/README.md`, `viewer/index.html`, `deploy/`, `scripts/build_sca2_data.py`, `src/sca2_workbench/`, root `README.md`: exit 1 (zero hits; the earlier exit-2 was my wrong cwd, paths re-checked). Remaining `extend*` tokens are TypeScript `extends` generics only.
- arXiv:2610.06562 citations remain: `common.ts:345`, `common.ts:445`, `landing.ts:33`, `landing.ts:95`.
- `tests/test_landing_wording.py` (3 tests) passes; screenshot `wb8_shots/landing-footer-1440x860.png` inspected visually — it shows the new footer sentence verbatim and no "extends the method".

## 3. Tests, tsc, rebuild, manifest parity — PASS

Run by me, exit codes captured (not through a pipe):

- Full suite: `env -u PYTHONPATH uv run python -m pytest tests -q` → **206 passed, 4 skipped, exit 0** (31.6 s).
- Focused (deploy bundle ×2, wording, story data, human reference): **57 passed, exit 0**.
- `npm run check` (`tsc --noEmit`): **exit 0**. `npm run build` also exit 0 (inside the bundle build).
- Rebuild from the candidate sha `4984189` (E1's bundle source) into my own scratch (`git archive 4984189` tree + read-only clones of the untracked inputs): `python3 scripts/build_deploy_bundle.py --out … --scratch … --human-reference …` → **exit 0**, 376 files, payload 949,437,055 B, cap headroom 562,825 B. Vite emitted the same asset `assets/index-BaJ78cEn.js`.
- Manifest parity with E1: my `files[]` vs `workbench/dist/wb8_candidate/deploy_bundle.tar.manifest.json` → **376/376 identical (name, bytes, sha256), 0 differences**; all non-file manifest fields identical. Only `archive_bytes`/`archive_sha256` differ (758,361,148 vs E1's 758,361,300 — tar mtime/gzip nondeterminism, expected).
- Re-verified from disk: E1 manifest sha256 `3d415b938684bb82f4e6551f04e7bb9d86fc9ebc5cc0963f6820a22083891588` ✓; v1.5 manifest sha256 `acabaae353d669913e1e673ece8f245aea82dec43e58189417291a3a308547e1` ✓; E1's gitignored bundle copy `wb8_candidate/deploy_bundle.tar.gz` sha256 `2fabb433…23eab` = its manifest `archive_sha256` ✓ (the stored bundle is genuine, not just its manifest).

## 4. Data identity vs the v1.5 deploy manifest — PASS, no BLOCK

Manifest `files[]` diff (mine/E1's vs `workbench/dist/deploy_bundle.tar.manifest.json`, v1.5): the only differences are

| file | v1.5 | v1.6 candidate |
|---|---|---|
| `assets/index-ElQYjXeR.js` → `assets/index-BaJ78cEn.js` | 749,934 B | 749,997 B (+63) |
| `index.html` | 1,594 B (asset ref `ElQYjXeR`) | 1,594 B (asset ref `BaJ78cEn`) |
| manifest field `q57.budget_left_bytes` | 562,888 | 562,825 |

`sca2/sca2_data.json`, `sca2/index.html`, every file under `exports/` (incl. `exports/index.json`, `exports/human_reference.json`), all screens, `source_indexes`, `selection_rule`, `human_reference` and `story_sources` blocks: byte-identical. Payload delta = +63 B exactly. No data file differs → nothing to BLOCK.

## 5. Serve + headless load — PASS

My own rebuild unpacked and served with `python3 -m http.server --bind 127.0.0.1 8513` (server killed after the check). CDP-driven Chromium headless at 1440×860 with a pre-navigation collector (`console.error`, `window` error + resource-error capture, `unhandledrejection`):

- Landing `/`: **0 console/page errors**; title ok; new footer in DOM (sentence at innerText offset 12505); "extends the method" absent (-1); `scrollWidth 1440 == innerWidth 1440` (no horizontal overflow).
- Ladder tab (click `[data-go="c"]`): active tab "Ladder", graphics mounted, "✓ 24 checks pass" self-check visible, **0 errors**.
- Cohort tab (click `[data-tab="k"]`): active tab "Cohort", 3 selects, comparators rendered, **0 errors**.

## Notes (non-blocking, none about data)

1. **E1 flag 3 stands (wording call for Augusto):** the footer still labels the preprint "(Paper A: arXiv:2610.06562)" (`landing.ts:95`). With Paper B now "the journal version", "Paper A" can read as a second paper. Kept because the citations were locked; Augusto decides.
2. **Record inaccuracy in `WB8_CANDIDATE.md:12`:** "the 10 PNGs already tracked under viewer/screens/sca2/" — the actual count is 30 tracked top-level `sca2/` PNGs (62 tracked files under `sca2/` incl. `wb3/`). Functionally irrelevant: no tracked file matches any new ignore rule (verified), so nothing was silenced or deleted.
3. **Reproducibility caveat:** the candidate sha alone cannot rebuild the bundle — `workbench/exports` (41 GB), `viewer/node_modules`, the `v3/v4` screen PNGs and `human_ref/` are untracked local inputs (same pattern as every prior card; scratch pruning noted by E1). I cloned them read-only; the 376/376 identity to E1's manifest proves they equal E1's inputs.
4. **Footer placement:** the footer exists only on the landing view; the workbench tabs unmount it (pre-existing SPA structure, unchanged from v1.5). The ED card's "confirm the new footer" should target the landing page.
5. **E1 flag 1 unchanged:** the `verified/`, `wb3v/`, `wb31v/`, `wb4v/` iteration folders stay local-only; the tracked WB1/WB3/WB3_1/WB4 verification docs cite them. Committing them is Augusto's call (PNGs would need `git add -f` or a `.gitignore` exception).

## What I did not verify

- `data/` was never opened (fence); data identity is asserted through manifest sha256 comparison only.
- `scripts/check_bundle_identity.py` vs the v1.4 baseline was not re-run (not asked by this card; identity vs v1.5 proven directly).
- Console *warnings* were not asserted to be zero (only errors, page errors, resource failures, rejections).
- Nothing deployed, nothing pushed, no commit made (fence); the only repo write is this review file.

## Reproduce (key commands, exit codes)

```
git diff --name-status a291f3b..e7bf22d                     # exit 0 (7 paths, table above)
git log a291f3b..HEAD --name-only | grep -i w3b             # exit 1 (empty)
env -u PYTHONPATH uv run python -m pytest tests -q         # exit 0, 206 passed 4 skipped
cd viewer && npm run check                                  # exit 0
python3 scripts/build_deploy_bundle.py --out … --scratch … # exit 0, 376 files, 949,437,055 B
python3 …/wb8v/compare_manifests.py                         # exit 0 (376/376 vs E1; 3 diffs vs v1.5)
python3 -m http.server --bind 127.0.0.1 8513  (then CDP)   # 0 errors on landing, Ladder, Cohort
```