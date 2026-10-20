# WB1-V independent verification (task t_005b33de)

Verifier: profile `verifier`, model `claude-sonnet-5-5` (provider anthropic). Producer was gpt-6.1-sol / openai-codex.
Branch `Adapter-Brain-Vizualization`, base HEAD `e5fea0b`. Date 2026-10-19 (MST). Nothing deployed, pushed or edited in producer files.
Evidence: `workbench/viewer/screens/sca2/verified/` (screenshots, `browser-evidence.json`, `featured-evidence.json`, `logs/`, `scripts/`).
Absolute local paths in copied logs/scripts are replaced by `<WORKTREE>`, `<MAIN>`, `<INPUTS>`, `<SCRATCH>`, `<HOME>`.

## VERDICT: PASS for the WB1 production bundle, with two deploy preconditions (P1, P2) and five non-blocking findings (F1-F5)

No requirement in the acceptance list failed on the artifact. P1 and P2 are not defects of the bundle. They are state-of-the-tree facts the deploy card must resolve before it runs. If the PM reads P1 or P2 as blocking, treat this verdict as BLOCK until they are closed.

## Deploy preconditions (not bundle defects)

P1. Full workbench suite is NOT green in the shared tree right now, because of a different card's untracked work.
  - Run 1: `pytest workbench/tests -q` exit 2, collection error: `workbench/analysis/w3_mechanisms.py:344` SyntaxError (f-string), imported by untracked `workbench/tests/test_w3_mechanisms.py:12` (`logs/fullsuite_run1_collection_error.log`).
  - Run 2, minutes later after W3 edited the file: exit 1, `8 failed, 176 passed, 4 skipped`. All 8 failures are in `test_w3_mechanisms.py` (`logs/fullsuite_run2_8_w3_failures.log`).
  - Same suite with that one file ignored: exit 0, `176 passed, 4 skipped, 3 warnings in 90.69s` (`logs/suite_w3_file_ignored.log`). This equals the producer's 176/4.
  - Neither file is part of WB1 (`git status`: `?? workbench/analysis/`, `?? workbench/tests/test_w3_mechanisms.py`). Re-run the full suite at deploy time, ideally from a committed tree.

P2. The WB1 repair is staged but NOT committed.
  - `git log --oneline -3 -- workbench/scripts/build_deploy_bundle.py workbench/viewer/public/sca2/index.html` prints nothing. HEAD is still `e5fea0b`. `git diff --cached --stat`: 42 files, 6683 insertions. Producer handoff says "explicit-file commit"; `WB1_ACCEPTANCE.md:81` says "this repair commit"; no such commit exists.
  - The bundle is reproducible (see below), so committing will not change it unless sources change. Deploy should still build from a commit, not from an index state.

## What was verified (all commands read their own exit codes, no pipes)

| Gate | Command / method | Result |
|---|---|---|
| Clean real build, <=1.5 GB | `uv run --project workbench python workbench/scripts/build_deploy_bundle.py --out <SCRATCH>/bundle/deploy_bundle.tar.gz` (rebuilds `viewer/dist` via `npm run build`, no stale fallback) | exit 0. 94 files, 572,239,120 payload bytes, 456,958,521 compressed bytes. Both < 1,500,000,000. |
| Manifest hashes | `scripts/check_bundle.py`: extract archive, recompute sha256+size of every manifest file | exit 0. 94/94 match, 0 extra, 0 missing, payload equals manifest, archive sha256 equals manifest. All tar members regular files, no `..` or absolute names. |
| Reproducibility | Compared producer's `workbench/dist/deploy_bundle.tar.manifest.json` with mine | Per-file (sha256, bytes) maps identical for all 94 files. Producer archive sha `90fa89ab...` re-hashes to its manifest. Only gzip framing differs (my archive sha `9b7dd396...`). |
| Closure | Same script, walks `exports/index.json` (25 runs, 17 pairs, 14 models) | 0 missing. Every run/pair JSON has its `.bin`; every array within bin bounds; every pair's two runs and both models present. Index `model`/`a`/`b` identities match the capture JSON. |
| Production static serve | Extracted tree served by `python3 -m http.server --bind 127.0.0.1` (no Vite). `/nonexistent` returns a real 404 (no SPA fallback). | Root, `/sca2/index.html`, assets and exports all load. |
| Focused tests | `pytest test_sca2_story_data.py test_deploy_bundle.py -q` | exit 0, 27 passed (`logs/focused_tests.log`). |
| `npm run build` (tsc + Vite) | `npm --prefix workbench/viewer run build` | exit 0 (existing >500 kB chunk advisory only). |
| Full suite | see P1 | exit 1 as run; 176 passed + 8 W3 failures; exit 0 with W3 file ignored. |
| Browser sweep | `scripts/verify.mjs` (my own puppeteer-core harness, system Chrome, both 1440x860 and 1700x1000) | exit 0. 135 checks, 0 failed. 0 pageerrors, 0 requestfailed. 314 responses: 310 normal-path all 200/304; the 4 non-2xx/4 console errors come only from the deliberate failure injections below (`browser-evidence.json`). |
| WebGL | `scripts/gl.mjs` on `?tab=a` | exit 0, `__ready` true, context not lost, 0 console errors. A new leak test was not required: `git diff HEAD --stat -- workbench/viewer/src` shows only `landing.ts` (1 line) changed, no scene/rebuild code. |

## Data gates (own readers, not the producer's)

- `scripts/check_data.py` exit 0:
  - All 8 `sources[]` sha256 digests match the files on disk (4 paper_b_inputs CSVs, GPS JSON, NUMBERS_TABLE, 2 mtmm cell CSVs).
  - Bundle `sca2/sca2_data.json` is byte-identical to the worktree copy.
  - GPS signs: I recomputed `sign(z) >= 0` from the raw GPS JSON myself; 42 countries, 0 bit/profile mismatches; 26 profiles; 42 members.
  - Cross-talk: 42 cells per route compared with `mtmm_*_cells.csv` (beta, se, own flag): 0 mismatches; 42 distinct betas per route (not a repeated-value matrix); 7 own cells; own-cell positives 7/7 adapter, 4/7 sign-prompt (wrong-signed 0 and 3, equal to claims `FX_adapter64_own_effects_wrong_signed` = 0 and `FX_signprompt64_own_effects_wrong_signed` = 3).
  - Claims: all 30 claim IDs exist in NUMBERS_TABLE with equal values. Every claim attached to a cell has the correct route prefix (`FX_adapter64_*` only on the adapter route, `FX_signprompt64_*` only on sign-prompt) and equals that cell's beta to 1e-12.
- `scripts/check_scores.py` exit 0 (uses the paper_b library `unit_composites`, so it checks the data against the library, not an independent reimplementation of `e_recode`): 1,176 cells (4 routes x 42 x 7), max abs difference 0. Bank-2 and sign-prompt are exactly constant within a profile (max within-profile range 0). Cohort-1 and persona are not (0.351 and 3.252), so the "by construction" label is correctly limited to the two profile-mapped routes.
- Browser DOM vs JSON: 294 displayed cells per cohort route (4 routes) and 42 per cross-talk route (2 routes) equal `toFixed(3)` of the JSON value; row sign strings and profile titles correct; per-surface headers show a range equal to the min/max over all four routes (shared scale); cell hue sign agrees with position on that scale; cross-talk legend states symmetric +-1.780 shared by both routes; claim IDs appear in tooltips of the right cells; 7 `.own` outlines at exactly (bit == surface prefix), including both patience surfaces.
- Featured links: 8 entries, 16 links. For each link I loaded the production URL and read the viewer: A = base Llama, B = `+ <CC> LoRA`, prompt = the entry's item, tab Ladder, no failure banner, run and pair `.bin` and JSON requests all 200 (`featured-evidence.json`). I checked the 8 (X, Y) pairs differ in exactly the named bit (X bit 0, Y bit 1). I recomputed the selection rule from the 966 source pair exports: the chosen pair is the arg-max of |d_margin(Y) - d_margin(X)| in all 8 entries. The page says plainly that "Two-country Δ unavailable" and every link text is `base → CC`, never X → Y. This is honest: it makes no X→Y claim.
- Units: surfaces and betas are labelled "frozen-recode composite units"; no percent or unbounded ratio is shown; no `Var(cross)/Var(full)`.

## Scientific-label gate (text checked in the rendered DOM at both viewports)

Present: "on average" with "does not guarantee every matched flip has that sign" (index.html:54); "behavioral cross-talk, not a neural mechanism or causal component attribution" (:57); "constant within a profile by construction ... not evidence of quality, trust specificity, or an anchor bottleneck" (:52); "especially after an underpowered null" (:57); "Two-country Δ unavailable" (:60); "no WVS human responses, country means or model–human joins"; "not a live model". Absent: Var(cross) ratio, causal/mechanism assertions, deployment claims, "no anchor bottleneck" assertions. The step-2 sentence reads 7/7 adapter and 4/7 sign-prompt positive, which matches 0/7 and 3/7 wrong-signed.

## Privacy gate (structural, not banned-substring only)

- Story payload allowlist: country objects have exactly `{bits, cc, unit}`; cells `{beta,bit,claims,own,se,surface,t,t_lenth}`; export `{base,country_key,default_units,j_minus,j_plus,src}`; route `{desc,name,scores,unit_of_score,within}`. None of the 456 continuous GPS z values (rounded to 6 d.p.) appears anywhere in the story JSON. Only the six sign bits are kept.
- Walked every JSON string in the bundle (index, 25 runs, 17 pairs, story): no `/Users`, `/home`, `~/`, `file://`, Windows drive, `.hermes`, `Desktop`, `Github_Repositories`, no user/host names, no token or key patterns. Model `adapter` fields are logical (`adapters/BGD`). Provenance contains instrument file digests and package versions only.
- Array names in `.bin` manifests are all activation/DLA/readout quantities (max array 13.8 MB top-k values); no model or adapter weight tensor, tokenizer or embedding matrix shipped. Static file extensions are only `.bin .css .html .js .json .png`.
- Run manifests carry the public WVS item wording and answer labels (`item.labels`, prompt tokens). These are survey instrument text, distinct from licensed respondent data; no respondent rows, country-level human means, distributions or model-human joins found.
- Not covered: I did not read the `.bin` arrays for hidden encodings (they are float/uint arrays under the frozen contract names).

## Failure and empty states (injected in the browser, `browser-evidence.json`)

| Injection | Observed |
|---|---|
| `sca2_data.json` 404 | `role=alert` "Story data unavailable. HTTP 404", no tables (`fail-story-404.png`) |
| zero countries | "Missing or empty story data", no fabricated table (`empty-story.png`) |
| a null score | "Non-finite model score" error, no NaN heat map |
| missing cross-talk cell | error "Missing cross-talk cell" shown; cohort table not partially rendered over a wrong matrix (`fail-missing-cell.png`) |
| viewer pair `.bin` 404 | red "Error: pair__...bin: HTTP 404" text; no stale data (`fail-viewer-bin404.png`) |
| unknown country pair | "Error: run__..._zzz__wvs_Q81.json: HTTP 404" |

## Visual / layout verdict (vision tool on 1440x860 and 1700x1000; page is a scrolling editorial story, not a one-screen dashboard)

- Legible: all heat-map and matrix numerals, own-cell outlines, headings and the four-step order. No page horizontal overflow, no clipped table cells (DOM `scrollWidth` checks) at either size. Root, ladder, matrix, object and cohort tabs load without a failure banner at both sizes.
- Weak but not failing: neutral mid-ramp colour blends into the card background, small values (|beta| < 0.1) look alike; ramp legend has no ticks; the 10-px range and sign-bit labels are small.

## Findings (all non-blocking; each with evidence)

F1. Featured-table headers are misaligned. `viewer/public/sca2/index.html:13` sets `th{text-align:right}` and `.links td{text-align:left}` with no `.links th` rule. Measured at 1440: header cells 2-5 `text-align: right`, body cells 2-5 `left`; the "X / Y" header sits ~200 px right of its data. Cosmetic, content correct.
F2. Profile grouping is only implied. Rows are sorted by profile (`index.html:34`) and the six sign bits are printed under each country code, but there is no group separator, band or profile label (`index.html:63-70`). For bank-2 and sign-prompt the repeated rows show the collapse, but a reader needs the 10-px bit strings to see the groups. Original WB1 item (b) says the collapse must be visible. I judge it partly met; recommend a group border before the co-author session.
F3. The inner table scroller clips a row at its boundary (`.scroll{max-height:472px}`, index.html:13); at 1440 9 of 42 rows are fully visible and the scrollbar is 2 px wide, so a half row looks like a defect. All 42 rows are reachable (checked).
F4. `build_deploy_bundle.py:23` hard-codes `SCRATCH = ~/.hermes/profiles/engineer/cache/scratch/wb1`, so my verifier run wrote its build temp dir under the engineer profile's scratch (cleaned on exit). Non-portable and crosses profile boundaries; it should take a tempdir or an argument.
F5. Pre-existing viewer behaviors, not introduced by WB1: an unavailable capture renders a bare small red line at top-left (no frame), and `viewer/src/main.ts:59` silently replaces an item that the pair does not offer with the pair's first item. All story links name items that exist, so no story link is affected. `running_margin_clamped` is emitted in manifests but absent from `spec/export_contract.md` (contract/code drift; the other topk arrays are documented at line 56).
Also: `WB1_ACCEPTANCE.md:51` cites a profile-specific scratch path in prose (not shipped in the bundle).

## Not verified / limits

- Composite scores were checked against the paper_b library on the same inputs, not re-derived from raw logprobs with an independent `e_recode`.
- The 8 featured claims of "largest |d_margin| gap" are verified on the 966 local source exports, which are not in the bundle.
- WebGL leak test (`webgl_leak_check.mjs`) not run, since no scene code changed; only a load/context check.
- No Safari/Firefox; Chrome only. No mobile viewport.

## Route

Verifier ran on `claude-sonnet-5-5` / anthropic (session model); the profile note's codex routing was not what this run used. Independence: different family from the gpt-6.1-sol producer.
