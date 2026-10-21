# WB3-V independent verification (task t_7c6f0653)

Verifier: profile `verifier`, model `claude-sonnet-5-5` (provider anthropic). Producer: `gpt-5.6-sol` / openai-codex (session 20261020_180933_a20768). Different family.
Branch `Adapter-Brain-Vizualization`, verified head `2309ab0fa17a10c1766c5d29a19bdd0469525cf8` (WB3 code commit `4f9af2b`). Date 2026-10-20 (MST). Nothing deployed, committed, pushed, or edited in producer files.
Evidence: `workbench/viewer/screens/sca2/wb3v/` (scripts, logs, `wb3v-browser.json`, `c9_check.json`, `parity_text.json`, screenshots). Absolute paths in copies are replaced by `<SCRATCH>`, `<MAIN>`, `<HOME>`.

## OVERALL: PASS (with 3 non-blocking notes, N1-N3)

Every item in the acceptance list passes. Nothing in the bundle fails a privacy, number, or label check. The notes are for the PM and Augusto, not defects that stop the deploy.

## Card instruction that I did not follow, on purpose

The card says to confirm the label "descriptive; C9-4 audit pending". The engineer's comment (PM update) supersedes it: the C9-4 cross-family audit (t_b4030219, my own earlier ACCEPT) cleared both experiments. I checked the shipped label against that, not the stale text. The shipped label is exactly `descriptive, not preregistered; cross-family audited`. The stale string "audit pending" / "C9-4 audit" appears nowhere in the story HTML (checked at both viewports). The label-recovery panel is marked "Construction check on held-out synthetic pairs; not a respondent-agreement test", as the comment requires.

## Result table (all exits read directly, no pipes)

| # | Gate | Command / method | Result |
|---|---|---|---|
| 1 | Clean rebuild from the committed head | `git archive HEAD workbench` into a fresh scratch dir; APFS-cloned `exports/` and `node_modules/` (gitignored); copied the 4 gitignored PNGs (`screens/v3/*`); one-line scratch-only patch of `SCRATCH` in `build_deploy_bundle.py` (see N3); `env -u PYTHONPATH HF_TOKEN= uv run --project workbench python workbench/scripts/build_deploy_bundle.py --out <SCRATCH>/out/deploy_bundle.tar.gz` | exit 0. 158 files, 1,053,474,200 payload bytes, 840,187,770 compressed bytes (`logs/build.log`) |
| 2 | Manifest compare | `scripts/cmp_manifest.py` producer sidecar vs mine | exit 0. 158 vs 158 files, 0 only-in-either, **0 per-file (sha256, bytes) mismatches**, payload equal. Only the gzip framing differs (archive sha producer `ef2528a0...`, mine `876ea15a...`), same as WB1-V |
| 3 | Own closure/hash check | `scripts/check_bundle.py` on my archive | exit 0. 158/158 hashes match, 0 extra, 0 missing, archive sha equals manifest, 41 runs, 33 pairs, 24 models, closure missing = [], all tar members regular files, no `..` or absolute names |
| 4 | Payload < 1.5 GB | manifest | Payload 1,053,474,200 and archive 840,187,770 are both < 1,500,000,000 (70% and 56% of the limit) |
| 5 | Byte identity to live sources | sha256 of all 74 capture JSONs and their `.bin` vs `workbench/exports/` in the live tree | 0 differences. No file under `exports/phase1_promptroute_nf4_t4`, `exports/phase1_nf4_t4` or `exports/index.json` is newer than `W2_VERIFICATION.md`, so the W2-V hashes still describe these bytes |
| 6 | Story data regenerated | `.venv/bin/python <SCRATCH>/workbench/scripts/build_sca2_data.py` run from the main repo | exit 0. Output is **byte-identical** to the committed `sca2_data.json`. Source digests in the JSON equal today's files (`NUMBERS_TABLE.csv` `71ee7c8c...`, `c9_label_recovery.csv` `1e0bcfb6...`) |
| 7 | Routes and console | `scripts/wb3v_browser.mjs` (my own harness; system Chrome; plain `http.server`, `/nonexistent` returns 404, no SPA fallback), both 1440x860 and 1700x1000 | exit 0. 56 checks, 0 failed. **0 console errors/warnings, 0 pageerrors, 0 requestfailed, 0 non-200/304 responses (434 responses)** |
| 8 | Routes covered | same | `/`, `/sca2/index.html` (both sizes, all 6 cohort/cross-talk route selectors switched), tabs a/b/c/k at both sizes, and all **32 featured links** (16 adapter + 16 sign-prompt): each lands on A = base, B = the link's model, the link's item, tab Ladder, no failbar, with at least one run/pair JSON and one `.bin` request all 200/304 |
| 9 | C9 numbers vs NUMBERS_TABLE by claim_id | `scripts/c9_check.py` on the **rendered DOM** (`wb3v-browser.json`) vs `NUMBERS_TABLE.csv` (main repo) | exit 0. 324 checks, 0 failures: 3 summaries, 4 TVD cells, 6 contrasts with intervals compared as printed text at 3 decimals (e.g. `0.045 [0.006, 0.093]`) and as exact `data-value` floats, at both viewports; 84 country dots vs `c9_label_recovery.csv` (exact); 14 C9 claim records in the JSON equal the table (value, ci_low, ci_high); the 30-entry `claims` block also equals the table. No duplicate claim ids in the table |
| 10 | Label | DOM `#c9 .audit-label` | Equals `descriptive, not preregistered; cross-family audited` at both viewports; no "audit pending" anywhere |
| 11 | Privacy: structural | recursive key scan of all 76 bundle JSON files | No key containing `human`, `respondent`, `population`, `wvs_mean`, `country_mean`. Story keys are only the 4 `tvd_cells` (country-equal aggregate cell means). The C9 country array is exactly `{cc, recovery, accuracy}` x 42. The only `prob`/`distribution` keys are model option probabilities and parity fields inside run/pair captures |
| 12 | Privacy: text | grep of built JS, CSS, root HTML, story HTML, story JSON | Built JS and root `index.html`: 0 hits for human/respondent/tvd. `sca2/index.html` and the JSON mention these words only in the disclaimer "no respondent rows, country-level TVD, human means or distributions", in CSS class names, and in the panel heading "Mean TVD to respondent distributions" (an aggregate, not a distribution). Only other "human" hit is the survey wording "humanitarian" in item text |
| 13 | No per-country TVD | `c9_tvd.csv` has only `cell` and `contrast` rows (no country rows); the bundle ships 4 cells + 6 contrasts | Nothing per-country for TVD exists to leak, and none is shipped |
| 14 | Sign-prompt profile mapping | all 16 prompt-route links | Each model key ends `_sp<bits>` equal to the six GPS sign bits of the linked country (0 mismatches); run label reads "+ sign prompt <bits>"; one `source_digest` family `843a4cf0`, which W2-V checked |
| 15 | W2-V gate | `workbench/plans/W2_VERIFICATION.md` | PASS-WITH-NOTES (not BLOCK), so the prompt-route captures may ship |
| 16 | Workbench suite | `env -u PYTHONPATH HF_TOKEN= PYTHONDONTWRITEBYTECODE=1 uv run --project workbench pytest workbench/tests -q -p no:cacheprovider` in the live tree at `2309ab0`; `git status --short` hash identical before and after | exit 0. **178 passed, 4 skipped, 3 warnings** in 23.6 s. This equals the producer's number. The only tracked modification in the tree is `workbench/analysis/w3b/run_w3b.py`, outside `workbench/tests` |
| 17 | Visual | vision read of my own `c9-1440.png`, `featured-1700.png` | Badge visible and legible; both C9 panels legible, no clipping or overlap; numbers read from the image equal the DOM values (0.940 / 0.816 / 0.489; 0.470 / 0.365 / 0.515 / 0.420); "Direct route Δ unavailable" notice visible. Page does not overflow horizontally (`scrollWidth <= innerWidth` at both sizes) |

Scratch checkout cannot run the full suite: it fails with 23 failed/27 errors from missing main-repo paths (`DPO_eval_WVS/`, `synthetic_generation/`) and gitignored `models/` (`logs/suite_scratch.log`). That is a property of the scratch layout, not a finding. The suite was run in the live tree at the verified head.

## Notes (non-blocking; each with evidence)

N1. Parity wording, W2-V rule N1. The story page makes no archive-parity claim, and the text "within 4 ulp" appears nowhere in the rendered story page (checked). But the pre-existing tensor viewer prints a header on every run, including the shipped prompt-route runs: `archive X ulp (≤4; report-only)` with a tooltip "≤4 archived-fp16 ulp, report-only" (`viewer/src/common.ts:416-417`). For all 16 sign-prompt featured runs the value shown is at most 3.9 ulp, so the label is true there (`parity_text.json`). On 8 of the 16 adapter featured runs (already deployed under WB2) it shows more than 4: GRC 4.6, NGA 5.4, IRN 4.5 and 6.0, USA 4.9, 6.3 and 8.8, PHL 4.7, printed next to "≤4; report-only". That is a declared tolerance beside a value that exceeds it. It is the same non-fatal behaviour W2-V accepted, but it is the kind of "4 ulp" text rule N1 warns about. Decision for Augusto: leave, or change the label to the observed gap. Not made here.

N2. Featured-table header text alignment (repeat of WB1-V F1, unfixed). `th` is `text-align:right`, body cells are `left` in columns 2-6 (`<SCRATCH>` DOM measure, `logs/align.log`). Column boxes align (same left edge), so the producer's "columns aligned" is true for boxes; the header text sits at the right of its column over left-aligned links. Cosmetic.

N3. `build_deploy_bundle.py:23` still hard-codes `~/.hermes/profiles/engineer/cache/scratch/wb1` (WB1-V F4, unfixed). I ran a scratch copy with that one line changed to a verifier scratch path (`logs/scratch_patch.diff`); every other byte of the script is the committed one and the output manifest matches the producer's, so the change does not affect the result. The committed script will write temp files under the engineer profile whoever runs it.

Also recorded, not findings: the producer's sidecar archive sha differs from mine only because of gzip framing; the deploy bundle includes 4 gitignored PNGs (`screens/v3/*`) that a pure clone cannot rebuild, so the PM must deploy from this worktree or an equivalent, not from a fresh clone.

## Not verified / limits

- `.bin` arrays were not decoded for hidden encodings; only manifests, names, sizes and bounds were checked (same limit as WB1-V).
- Chrome only, no Safari/Firefox, no mobile viewport.
- Per-country model option probabilities are inside the run captures by design (model outputs, not respondent data); I did not check them against any human data because none is in scope.
- The deployed Space was not touched or compared; WB2 receipt `built_from_commit e86d4c2` is the prior deploy.

## Route

Verifier ran on `claude-sonnet-5-5` via anthropic (session header). The profile note's codex routing was not what this run used. Independence: not the Codex producer.
