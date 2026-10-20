# WB1-R producer acceptance record

Task: `t_313d3c22`. Branch: `Adapter-Brain-Vizualization`.

Status: producer checks PASS, including the fresh full Python suite (176 passed, 4 skipped). Independent acceptance `t_005b33de` has not run; this is not a deployment authorization. Nothing deployed or pushed.

## Repair delivered

- `workbench/scripts/build_deploy_bundle.py`: replaces the broken skeleton with a fresh `npm run build`, an allowlisted static site, and a curated, closed export index. Missing dependencies, symlinks, unsafe paths, inconsistent capture identities, array bounds and either size limit fail closed. The sidecar manifest hashes every shipped file; it is intentionally outside the archive (no impossible self-hash).
- `workbench/scripts/build_sca2_data.py`: preserves source digests while replacing private absolute input paths with logical `paper_b_inputs/<basename>` identifiers. Scores and capture files are not altered.
- `workbench/viewer/public/sca2/index.html`: self-contained production CSS; 42-country × 7-surface heatmap grouped by six-sign profile, four route choices; real 6-bit × 7-surface factorial matrix with two route choices and seven own-cell outlines. Each cohort surface shares its range across all four routes; cross-talk shares a symmetric range across both routes. Neither scale clips.
- All story-to-viewer links use `/?tab=...`. Featured X/Y entries expose two explicitly labelled base-to-country links. An at-rest notice says two-country Δ is unavailable. No X→Y result is claimed and no norms are subtracted.
- `workbench/viewer/src/landing.ts`: one navigation link makes the story discoverable from the existing root entry page. Tensor rendering and WebGL scene rebuilds were not changed.
- The story now distinguishes average factorial direction from individual flips, behavioral cross-talk from a neural mechanism, and within-profile constancy by construction from measurement quality. It removes the old deadline/deploy alert and unsupported size/deployment assertions. Counts/values are derived from the JSON, not transcribed into HTML.

## Real archive and closure

Archive: `workbench/dist/deploy_bundle.tar.gz`.
Sidecar: `workbench/dist/deploy_bundle.tar.manifest.json`.

| Measured property | Value |
|---|---:|
| Compressed archive bytes | 456,958,356 |
| Uncompressed payload bytes | 572,239,120 |
| Enforced upper bound, each | 1,500,000,000 |
| Shipped regular files | 94 |
| Offered run manifests / binaries | 25 / 25 |
| Offered pair manifests / binaries | 17 / 17 |

Archive SHA-256: `90fa89abf949d1f9cd0772bbfb5da33405bea2143dec598b0263d9e4651cbccf`.

Selection: existing Smol default A/B/item, the story's default country unit, and base-versus-both-countries for every featured entry. Only these runs/pairs/models are offered in `/exports/index.json`. The original 989-run index is not shipped. All selected capture JSONs/binaries are byte-identical copies, retain capture@1.1 and source digests, and live at the paths the existing reader requests. Root thumbnails are copied through an explicit four-image allowlist. No tokenizer, embeddings, model/adaptor weights or inference runtime is copied.

`viewer/screens/sca2/verify_bundle.py` independently recomputes the archive hash, every member hash/size and dependency closure, checks frozen array names/bounds, rejects private metadata paths, and extracts only verified regular files into a new directory. Receipt: `viewer/screens/sca2/bundle-check.json`. The payload schema tests additionally restrict story fields; privacy is not inferred from a banned-substring search. GPS signs and public survey item text are distinct from licensed human responses. No human response/country-outcome payloads were read or added by this repair.

## Commands and captured exits

Run from the worktree root. Each exit was captured directly from the command, never from a pipe.

| Command / check | Exit | Result |
|---|---:|---|
| `env -u PYTHONPATH HF_TOKEN= uv run --project workbench pytest workbench/tests/test_sca2_story_data.py workbench/tests/test_deploy_bundle.py -q` | 0 | 27 passed |
| `npm --prefix workbench/viewer run build` | 0 | TypeScript + Vite production build; existing >500 kB chunk-size advisory, not a build failure |
| `env -u PYTHONPATH HF_TOKEN= uv run --project workbench python workbench/scripts/build_deploy_bundle.py` | 0 | Fresh real archive; sizes above |
| `env -u PYTHONPATH HF_TOKEN= uv run --project workbench python workbench/viewer/screens/sca2/verify_bundle.py workbench/dist/deploy_bundle.tar.gz <fresh-scratch-dir> --report workbench/viewer/screens/sca2/bundle-check.json` | 0 | All 94 members + closure verified and extracted |
| `BROWSER_TOOLS=<scratch>/browser-tools node workbench/viewer/screens/sca2/acceptance.mjs http://127.0.0.1:5192 workbench/viewer/screens/sca2` | 0 | Production-static browser sweep |
| `env -u PYTHONPATH HF_TOKEN= uv run --project workbench pytest workbench/tests -q` | 0 | Final fresh shared-tree run: 176 passed, 4 skipped, 3 expected loader warnings in 82.54 s |

The extracted final archive was served with plain `python3 -m http.server`, bound to localhost. No Vite server or middleware was used. `BROWSER_TOOLS` points to a scratch-only installation of `puppeteer-core`; `CHROME_PATH` can override the system Chrome location. The browser harness resolves these without adding an application dependency.

Raw stdout/stderr logs are in `~/.hermes/profiles/engineer/cache/scratch/wb1/`: `story-red.log`, `schema-red.log`, `browser-red-snapshot.log`, `group-red.log`, `entry-red.log`, `focused-final.log`, `bundle-final.log`, `bundle-check.log`, `npm-final.log`, `all-tests-final.log` (intermediate W2 failures), `all-tests-latest.log` (final PASS), `browser-final.log`. Browser and archive receipts are checked into the screenshot/evidence directory without private local paths.

## Regression evidence and limits of its chronology

- Original story tests: exit 1 (the substring privacy check rejected a provenance filename). Replaced by an exact-field payload allowlist, with negative injections at root/country/route/cell levels; positive source metadata may legitimately name `gps_z_vectors.json`.
- Bundle unit tests first exercised the skeleton: exit 1. The repaired builder's 15 tests cover real synthetic test archives, closure/identity, missing run/pair/bin/image, unsafe/absolute paths, symlinks, npm failure, bounds, stale-output exclusion and actual payload/compressed size limits. Test fixtures are not shipped as measurements.
- The first browser attempt could not import `puppeteer-core`; this was a setup failure, not a valid RED. After installing it in scratch, the exact originally-read HTML was recovered from this run's stored tool result into a scratch-only historical snapshot. That snapshot produces exit 1: missing production CSS and a real JS syntax error (`Unexpected identifier 'cid'`), and no rendered heatmaps. This historical rerun occurred after the page rewrite; it is not claimed as strict pre-implementation browser TDD for each individual original UI defect.
- Additional profile-grouping and root-navigation regressions were demonstrated RED before their fixes, then included in the final GREEN browser/test runs.

## Browser/data evidence

`viewer/screens/sca2/browser-report.json` records 299 responses and the checks. Final normal-path responses are HTTP 200/304; zero 404s, console errors or page errors were recorded. Thirty viewport screenshots are saved.

The sweep checks every rendered numerical cell against the saved JSON: 294 cohort cells for each of four routes and 42 factorial cells for each of two routes, including exact unrounded DOM values, printed three-decimal values, shared surface scales, profile order and own-cell flags. It verifies all country rows are reachable in the table scroller. It opens all 16 featured links, checks exact A/B/item selection, and requires successful run and pair binary requests rather than only a loaded shell. It also loads the root, ladder, matrix, object and existing cohort empty state at both requested viewport sizes. Test-only intercepted responses exercise a failed capture's persistent red banner and an empty story's explicit unavailable state without modifying shipped captures.

Screenshots: `workbench/viewer/screens/sca2/`, at 1440×860 and 1700×1000. Filenames include `story-*`, `root-*`, `cohort-{cohort1,bank2,signprompt,persona}-*`, `crosstalk-{adapter,signprompt}-*`, `featured-*`, and existing tensor tabs. Final vision inspection found legible numerals, distinct matrix values, all own outlines, clear base-to-country links, and no horizontal clipping/overlapping headings. The cohort's 42 rows deliberately use an inner scroller with sticky headers; a partially visible next row at the scroll boundary is not omitted data. At 1700 the small ranges are best inspected at native resolution rather than a downsampled preview. This is a vertically scrolling editorial story, not a one-screen dashboard.

Existing/fixed boundaries:

- Two-country signed DLA/margin comparison is explicitly unavailable, not silently substituted with base→Y.
- Root remains the small-model method introduction; its new story navigation leads to the SCA2 cohort/factorial display. Existing root teaching copy is not rewritten into new Llama findings.
- The new cohort-score heatmap is on `/sca2/index.html`; the existing tensor-cohort tab is a different layer-attribution view. Some curated item/base selections have fewer than three adapters and correctly retain that tab's existing empty state.
- Only curated exports are offered; this is not a bundle of all phase-1 captures. No prompt-route captures from W2 are shipped.
- No WebGL scene/rebuild code changed, so a new leak test was not required; existing object rendering was exercised in the production sweep.
- Source GPS continuous values remain outside the delivered data. Only six sign bits are kept.

## Acceptance gate and coordination

Intermediate full-suite runs failed exclusively in W2-owned `test_prompt_route.py`. The PM instructed exclusive W2 ownership and re-routed that same card. This repair did not edit/stage any W2 files. After W2's concurrent fixes, a fresh complete run returned exit 0: 176 passed, 4 skipped, 3 warnings. W2 was notified of that measured result. The required producer full-suite gate is now closed; independent verification remains pending.

`hotspot`: `workbench/src/sca2_workbench/cohort.py`, `workbench/src/sca2_workbench/stream_export.py`, `workbench/plans/gpu_cohort/runner/mac_queue.py` — shared-tree suite observed W2 in-progress code during intermediate runs. Do not fold those files into this repair commit.

Deployment card `t_1067ab75` was notified and its state was read back: it now depends on independent acceptance `t_005b33de` and is waiting. Completing repair alone is not authorization to deploy. No deploy was performed.

## Actual model route

Model `gpt-6.1-sol`, provider `openai-codex`, session `20261019_165212_cf0f6c`, verified in the engineer run log (turn-context entry at 2026-10-19 16:52:15 MST). The short bundle implementation subtask used the same route. No provider/profile configuration was changed.
