# WB3 producer acceptance record

Task: `t_490878ba`. Branch: `Adapter-Brain-Vizualization`.

Status: PASS for producer checks. Implementation commit: `4f9af2b`. Nothing was deployed or pushed. Independent verification remains on `t_7c6f0653`.

## Delivered

- `scripts/build_sca2_data.py` now selects the four country-equal TVD cell means, all six requested profile-block contrasts, and four profile-block label-recovery summaries from `NUMBERS_TABLE.csv` by exact claim id. It reads only country, recovery and accuracy from `c9_label_recovery.csv` for the 42 model-only country dots. Both source files retain logical paths and SHA-256 digests.
- `viewer/public/sca2/index.html` adds step 4, “Does learning the labels mean behaving like the respondents?” The left panel shows held-out synthetic-label recovery as an explicit construction check; the right shows the 2×2 TVD cells and profile-block intervals. The caption is “Label fidelity is not agreement with respondents.” All displayed numerical values are rendered from `sca2_data.json`; none is typed into the page.
- The current audit label is `descriptive, not preregistered; cross-family audited`, per the PM update after the cross-family C9-4 audit accepted both experiments.
- Each of the eight existing featured adapter rows now offers the matching W2 sign-prompt route on the same item and sign profile. The page makes no archived-parity claim. Per W2-V note N1, any future such claim must say “within about 0.11 nats of the archived run”, never “within 4 ulp”.
- `build_deploy_bundle.py` includes the exact adapter and prompt-route closure, deduplicates shared base runs, and still fails closed on conflicting metadata or bytes.
- Tests structurally reject extra human fields, per-country TVD, and typed C9 headline values. The browser sweep checks every displayed C9 point/value/interval against JSON and opens all 32 featured adapter/sign-prompt links through successful run and pair binary requests.

## Data and privacy checks

A separate read-back compared all 14 shipped C9 claim records with `NUMBERS_TABLE.csv` as Python round-trip floats: 0 mismatches. The C9 country array has 42 rows and exactly the fields `{cc, recovery, accuracy}`. Recursive key inspection found 0 `human_mean`, `human_distribution`, or `population_prob` paths. No country-level TVD, respondent row, human mean, or human distribution is shipped.

Source digests in the generated JSON:

- `NUMBERS_TABLE.csv`: `71ee7c8c68eb856bf7215165dd836aef7cc3f67993a6523790cee4b22ce186a4`
- `c9_label_recovery.csv`: `1e0bcfb6ec14f0c83e879c0ca15a8ddd77ec2683d84b0b66f47fca15a55b221f`

## Bundle

- Archive: `workbench/dist/deploy_bundle.tar.gz`
- Sidecar: `workbench/dist/deploy_bundle.tar.manifest.json`
- Verification receipt: `workbench/viewer/screens/sca2/bundle-check-wb3.json`
- Compressed bytes: `840,187,125`
- Uncompressed payload bytes: `1,053,474,200`
- Limit: `1,500,000,000` bytes for each measure
- Archive SHA-256: `ef2528a0aa4541a987cca6d69a6fafef073c87dbf53a16cd1de8d354bfb6da2f`
- Closure: 158 files; 41 runs; 33 pairs; 74 capture manifests
- Deploy status: NOT DEPLOYED

`verify_bundle.py` rebuilt every member hash and size, checked archive and payload limits, capture identity, binary bounds, allowed array names and exact dependency closure, then extracted only verified regular files into a fresh engineer scratch directory. Result: PASS.

## Browser and screenshots

Production-static browser sweep: PASS. It recorded 40 checks, 459 HTTP 200/304 responses, 0 non-success responses, 0 console errors and 0 page errors.

Numerical DOM checks:

- Cohort heat maps: 294 cells × 4 routes = 1,176 values
- Cross-talk: 42 cells × 2 routes = 84 values
- C9: 3 summary values, 84 country dots, 4 TVD cells, and 6 profile-block contrasts
- Featured captures: 32 links (16 adapter, 16 sign-prompt), each with successful run and pair binary requests

Screenshots are under `workbench/viewer/screens/sca2/wb3/`. The required views are:

- `c9-1440.png` and `c9-1700.png`
- `story-1440.png` and `story-1700.png`
- `featured-1440.png` and `featured-1700.png`

The suffixes correspond to 1440×860 and 1700×1000 viewports. The complete 33-file sweep also covers root, ladder, matrix, object, empty cohort, all four cohort routes and both cross-talk routes. Final visual inspection found the audited badge and construction-check note visible, both C9 panels legible, adapter/sign-prompt columns aligned, and no clipping or overlap.

## Commands and captured exits

Each exit was captured directly, never through a pipe.

| Command / check | Exit | Result |
|---|---:|---|
| Initial focused RED: `env -u PYTHONPATH HF_TOKEN= uv run --project workbench pytest workbench/tests/test_sca2_story_data.py workbench/tests/test_deploy_bundle.py -q` | 1 | 5 expected failures: absent C9 block, absent prompt fields/closure |
| `env -u PYTHONPATH HF_TOKEN= uv run --project workbench --with pandas python workbench/scripts/build_sca2_data.py` | 0 | 107,760-byte JSON; 42 countries; 26 profiles; 9 source digests |
| Focused tests, same two files | 0 | 29 passed |
| `env -u PYTHONPATH HF_TOKEN= uv run --project workbench python workbench/scripts/build_deploy_bundle.py` | 0 | Fresh bundle; sizes and hash above |
| `env -u PYTHONPATH HF_TOKEN= uv run --project workbench python workbench/viewer/screens/sca2/verify_bundle.py workbench/dist/deploy_bundle.tar.gz <fresh-scratch> --report workbench/viewer/screens/sca2/bundle-check-wb3.json` | 0 | PASS; 158-file closure |
| `BROWSER_TOOLS=<engineer-scratch>/browser-tools node workbench/viewer/screens/sca2/acceptance.mjs http://127.0.0.1:5194 workbench/viewer/screens/sca2/wb3` | 0 | 40 checks; 459 successful responses; no browser errors |
| C9 claim/source/privacy read-back script | 0 | 14/14 claim records exact; 42 country rows; 0 forbidden key paths |
| `env -u PYTHONPATH HF_TOKEN= uv run --project workbench pytest workbench/tests -q` | 0 | 178 passed, 4 skipped, 3 expected loader warnings |
| `git diff --check` | 0 | No whitespace errors |

The first documented rebuild attempt without `--with pandas` exited 1 because pandas is intentionally absent from the workbench runtime dependencies. The README now uses uv’s explicit transient `--with pandas` build dependency; no runtime package was added.

## Boundaries and existing tree state

- No edits were made under `workbench/analysis/w3b/` or `workbench/exports/`.
- Existing W3/W3b modified and untracked files, the verifier-owned `workbench/plans/W2_VERIFICATION.md`, and `viewer/screens/sca2/verified/` were not staged or adopted.
- No deployment, upload, push, model inference, or weight copy occurred.

## Model route

The engineer session run log (`state.db`, session `20261020_180933_a20768`) records model `gpt-5.6-sol`, billing/provider route `openai-codex`, reasoning effort `high`.
