# WB8 candidate: Workbench v1.6 candidate (CP26-E1)

Not deployed, not pushed. Built from `Adapter-Brain-Vizualization` at `4984189` (parent `a291f3b`, the source of deployed v1.5 `890ead3` plus docs).
Route: claude-sonnet-5-5 (anthropic) via the kanban worker.

## Commits (explicit paths only)

| sha | what |
|---|---|
| `7534529` | `viewer/src/landing.ts` footer: "Paper B, the journal version in preparation, evaluates the method as a scoring instrument on a 42-country cohort; this workbench is its companion." New `tests/test_landing_wording.py` (3 tests: new sentence present, no "extends the method / sequel / follow-up study / Paper B builds on" in `viewer/src/*.ts`, arXiv:2610.06562 kept). |
| `bf5ab17` | `scripts/build_deploy_bundle.py`: new `resolve_scratch()`; order `--scratch` > `$SCA2_BUNDLE_SCRATCH` > `<workbench>/dist/.bundle-scratch`; always `.expanduser().resolve()` (symlinked scratch resolved). Module constant `SCRATCH` and its `~/.hermes/cache/scratch/wb-bundle` default removed. Two new tests in `tests/test_deploy_bundle.py` (resolution order + symlink; `--scratch` honoured and stage cleaned). The fixture now stages in `tempfile.gettempdir()` instead of the builder constant. |
| `4984189` | `workbench/.gitignore`: anchored `/viewer/screens/sca2/{verified,wb3v,wb31v,wb4v}/` and `/analysis/out/w3v_*`. Nothing deleted; the 10 PNGs already tracked under `viewer/screens/sca2/` are unaffected. |

## Wording grep

Searched `viewer/src`, `viewer/public/sca2/index.html`, `viewer/README.md`, `viewer/index.html`, `deploy/SPACE_README.md`, `README.md`, `scripts/build_sca2_data.py` (story JSON builder), `src/sca2_workbench/*.py` for "extend", "sequel", "follow-up", "builds on", "companion", "earlier study", "preprint". The only hit about Paper B was `landing.ts:95`. The other `extends` hits are TypeScript generics. arXiv:2610.06562 citations (`common.ts:345`, `landing.ts:33`, `landing.ts:95`) are unchanged.

## Bundle

- Path: `workbench/dist/wb8_candidate/deploy_bundle.tar.gz` (gitignored copy). Build output: `~/.hermes/profiles/engineer/cache/scratch/wb8/` (scratch is pruned after 24 h idle).
- Command: `env -u PYTHONPATH HF_TOKEN= uv run python scripts/build_deploy_bundle.py --out $S/deploy_bundle.tar.gz --scratch $S/stage --human-reference human_ref/human_reference.json` -> exit 0.
- Payload 949,437,055 B (cap 950,000,000; headroom 562,825 B); archive 758,361,300 B; archive sha256 `2fabb433bf063795a8d9f3f9952c5049291619decd3268609fe4126de3923eab` (differs from v1.5 `a94e5373…` because of the changed JS and tar mtimes).
- Manifest: 376 files; sha256 of `deploy_bundle.tar.manifest.json` = `3d415b938684bb82f4e6551f04e7bb9d86fc9ebc5cc0963f6820a22083891588`. (v1.5 reference manifest `workbench/dist/deploy_bundle.tar.manifest.json` = `acabaae353d669913e1e673ece8f245aea82dec43e58189417291a3a308547e1`; its `archive_sha256` `a94e5373…` equals the value recorded in README for the deployed v1.5.)
- Archive closure: 376 archive files = 376 manifest files, 0 hash mismatches.

## Difference from v1.5 (per-file sha256 + bytes, manifest vs manifest)

374 of 376 files byte-identical, including `sca2/sca2_data.json`, `sca2/index.html`, `exports/index.json` and every file under `exports/`. Blocks `human_reference`, `selection_rule`, `source_indexes`, `story_sources` equal.

| file | change | why |
|---|---|---|
| `assets/index-ElQYjXeR.js` -> `assets/index-BaJ78cEn.js` | 749,934 -> 749,997 B (+63) | the footer sentence is 63 characters longer ("…the journal version in preparation, evaluates … as a scoring instrument on" vs "extends … to") |
| `index.html` | 1,594 B both | references the new hashed JS file name |
| manifest `q57.budget_left_bytes` | 562,888 -> 562,825 | the same +63 B |
| manifest `archive_*`, `payload_bytes` | +250 / +63 | consequence |

`scripts/check_bundle_identity.py` against the v1.4 baseline: exit 0, 143 checked, 138 identical, the same 5 allowed changes, 0 violations.

## Tests and checks

- `env -u PYTHONPATH uv run python -m pytest tests -q`: exit 0, 206 passed, 4 skipped. Focused (deploy bundle, light, wording, story data, human reference): exit 0, 57 passed.
- `npm run check` (`tsc --noEmit`): exit 0. `npm run build`: exit 0.
- Static serve of the unpacked archive (`python3 -m http.server --bind 127.0.0.1 5871`, server stopped afterwards), Chrome headless 1440x860: footer text shows the new sentence, no "extends the method" anywhere in the body text, 0 console/page errors, no horizontal overflow (scrollWidth 1440), footer bottom at 859.7 of 860 px (unchanged layout; the footer is the last block, scrolled into view).
- Screenshot: `workbench/plans/wb8_shots/landing-footer-1440x860.png` (committed with this file).

## For Augusto / verifier

1. **`verified/` was not committed.** Its files are dated 2026-10-19 and are the WB1 evidence (94-file, 457 MB bundle; `plans/WB1_VERIFICATION.md`), not the shipped v1.5 release. The card said commit only if they document the shipped release. The same holds for `wb3v`, `wb31v`, `wb4v`, which tracked docs `WB1/WB3/WB3_1/WB4_VERIFICATION.md` cite as evidence: those citations now point at local-only folders. Say if you want any of them committed (PNGs need `git add -f` or a `.gitignore` exception).
2. **N3 was half done.** WB4 already made `SCRATCH` overridable by `SCA2_BUNDLE_SCRATCH` and resolved. What remained was the home-path default and the missing test; both are now fixed.
3. **Footer label.** The footer still says "(Paper A: arXiv:2610.06562)". With Paper B described as the journal version, "Paper A" for the preprint may read as a second paper. Left as written because the card says to keep the citations; wording is your call.
4. **W3b files untouched.** `git status` after the work shows only the W3b set (`run_w3b.py` modified, `W3b_*`, `_discarded_W3/`, `plot_w3b.py`, `w3b/tests/`) as uncommitted.
5. No push, no deploy, no `data/` access, `HF_TOKEN` passed empty and never printed.
