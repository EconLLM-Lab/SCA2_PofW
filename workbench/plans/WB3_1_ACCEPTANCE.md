# WB3.1 producer acceptance record

Task: `t_04ac8789`. Branch: `Adapter-Brain-Vizualization`.

Status: PASS for producer checks. Nothing was deployed or pushed. Independent verification is the dependent task `t_42d33a08`.

## Delivered

The C9 step in `viewer/public/sca2/index.html` keeps the dark theme and the badge `descriptive, not preregistered; cross-family audited`, while making the interpretation readable from the main slide rather than its footnotes:

- The panel headings now state `higher = better` for label recovery and `lower = closer to respondents` for TVD.
- The takeaway `Label fidelity is not agreement with respondents.` is a callout directly beneath the step title.
- The TVD cells are arranged under `no persona / persona` columns and `no adapter / adapter` rows. The largest cell is identified from JSON at render time and receives a quiet blue-grey emphasis; under the current data this is Adapter, 0.515.
- Both country strips use the same 0–1 scale. A dashed chance guide is fixed at the shared midpoint and labelled `chance`; each strip has a mean marker sourced from the corresponding JSON summary. `Base accuracy` remains labelled `at chance`, because the JSON has no separate 0.50 design-constant field.
- The six contrast rows are now a compact forest plot. Every row has a point, profile-block 95% interval, vertical zero line, and a quiet blue/grey distinction for intervals that exclude/cross zero. Its compact value column and hover title both come from the same JSON values. The note reads `95% profile-block bootstrap over the 26 sign profiles` and defines interaction inline as `(adapter + persona − persona) − (adapter − base)`.
- Secondary C9 labels are larger and brighter for projection. The construction-check caption is one normal line, with no orphaned `test.` fragment.

The source `viewer/public/sca2/sca2_data.json` remains byte-identical to WB3 at `2309ab0` (SHA-256 `16068182617aa623bc10d3fceaae6373f1ec32311b4f24ed2ccee47dbc058584`). It was not trimmed or regenerated into a new data surface. C9, heat-map, factorial, country-strip, and featured-row data are unchanged.

## Hugging Face 1 GB storage constraint

The operator reported that the v1 upload encountered the Space's 1 GB storage ceiling. The builder now enforces a conservative decimal cap of 950,000,000 bytes for both uncompressed payload and compressed archive.

The story keeps all eight featured adapter country pairs. Prompt-route captures are included only for the featured row with the largest saved adapter-margin difference within each sign bit. This retains one complete X/Y adapter/sign-prompt comparison for each of the six bits. At runtime the featured table reads the curated capture index: included prompt captures become links; omitted ones are labelled `omitted from compact bundle`, so the page never offers a dead link.

Prompt rows retained:

| Bit | Surface / item | X → Y | Saved margin difference |
|---|---|---|---:|
| trust | trust / `wvs_Q57` | BGD → CHN | 15.416054 |
| risktaking | altruism / `wvs_Q99` | CHN → USA | 18.490671 |
| patience | patience:Q43 / `wvs_Q43` | IRN → CAN | 7.842616 |
| altruism | altruism / `wvs_Q99` | THA → EGY | 2.814565 |
| posrecip | posrecip / `wvs_Q81` | GBR → USA | 16.706905 |
| negrecip | negrecip / `wvs_Q176` | PHL → USA | 4.315283 |

Dropped duplicate prompt-route units (adapter captures and story rows remain):

| Duplicate bit | Surface / item | Dropped X/Y units | Prompt models | Saved margin difference | Kept alternative |
|---|---|---|---|---:|---|
| risktaking | risktaking / `wvs_Q106` | GRC / NGA | `llama31_8b_nf4_dequant_float64_cpu_843a4cf0_46079e27_base_sp000001`; `llama31_8b_nf4_dequant_float64_cpu_843a4cf0_46079e27_base_sp010001` | 3.163522 | CHN / USA on `wvs_Q99`, 18.490671 |
| patience | patience:Q50 / `wvs_Q50` | IRN / USA | `llama31_8b_nf4_dequant_float64_cpu_843a4cf0_46079e27_base_sp110111`; `llama31_8b_nf4_dequant_float64_cpu_843a4cf0_46079e27_base_sp111111` | 2.613164 | IRN / CAN on `wvs_Q43`, 7.842616 |

The manifest records both retained and dropped feature rows, including the source-derived margin differences. No capture source was edited.

## Bundle

- Archive: `workbench/dist/deploy_bundle.tar.gz`
- Sidecar: `workbench/dist/deploy_bundle.tar.manifest.json`
- Verification receipt: `workbench/viewer/screens/sca2/bundle-check-wb3_1.json`
- Target maximum: 950,000,000 bytes
- Uncompressed payload: 918,377,325 bytes (96.67% of cap; 31,622,675 bytes headroom)
- Compressed archive: 732,597,827 bytes
- Archive SHA-256: `f1af02176f86b1f4b51fb0a183dedd85d68dc3b1b5eacb90c31a3c471ed3d1e9`
- Closure: 142 files; 37 runs; 29 pairs; 66 capture manifests
- Payload reduction from WB3: 135,096,875 bytes (12.82%)
- Deploy status: NOT DEPLOYED

`verify_bundle.py` re-read all member hashes and sizes, checked archive and payload caps, capture identity, binary bounds, allowed arrays, and exact dependency closure, then extracted only verified regular files into a fresh engineer scratch directory. Result: PASS.

## Browser, numerical sweep, and screenshots

The production-static bundle was served with plain `python3 -m http.server` from the fresh verified extraction. The browser acceptance harness passed with 36 recorded checks, 422 HTTP 200/304 responses, 0 non-success responses, 0 console errors, and 0 page errors. It opened all 16 adapter links and the 12 retained prompt links; together they cover all six sign bits.

The C9 numerical DOM sweep repeated the WB3-V procedure at both viewports and passed 324/324 checks:

- rendered summary text and exact `data-value` values;
- rendered TVD cell text and exact values;
- forest-plot compact values, interval endpoints, and data attributes;
- 84 country dots at each viewport against `c9_label_recovery.csv`;
- all 14 C9 claim records against `NUMBERS_TABLE.csv`;
- all 42 JSON country rows and their restricted field sets.

The acceptance harness separately checks both mean markers, the forest-plot hover values, the farthest-cell emphasis, factor headers, polarity cue, zero lines, interaction definition, prompt coverage, and zero horizontal overflow.

Required screenshots:

- `workbench/viewer/screens/sca2/wb3_1/c9-1440.png` at 1440×860
- `workbench/viewer/screens/sca2/wb3_1/c9-1700.png` at 1700×1000

The same folder also holds the complete route screenshots, `browser-report.json`, `c9-dom.json`, `c9-check.json`, and the two small audit scripts. Visual inspection of both required images found the takeaway visible without footnotes, both polarity cues in the headings, readable 2×2 factor headers, visible chance/mean markers, a legible forest plot, and no overlap or clipping.

## Commands and captured exits

Every exit was captured directly, never through a pipe.

| Command / check | Exit | Result |
|---|---:|---|
| Initial focused RED: `env -u PYTHONPATH HF_TOKEN= uv run --project workbench pytest workbench/tests/test_sca2_story_data.py workbench/tests/test_deploy_bundle.py -q` | 1 | Two expected failures: projection markup absent; old 1.5 GB cap |
| Focused GREEN, same two files | 0 | 31 passed |
| Pinned-source data rebuild with the current unchanged builder, followed by byte comparison | 0 | Rebuilt 107,760-byte JSON; `cmp` exit 0 against WB3 JSON |
| `env -u PYTHONPATH HF_TOKEN= PYTHONDONTWRITEBYTECODE=1 uv run --project workbench python workbench/scripts/build_deploy_bundle.py` | 0 | 918,377,325-byte payload, 732,597,827-byte archive, 142 files |
| `env -u PYTHONPATH ... verify_bundle.py ... <fresh engineer scratch>/site --report .../bundle-check-wb3_1.json` | 0 | PASS; 142-file closure |
| `BROWSER_TOOLS=<engineer scratch>/browser-tools node workbench/viewer/screens/sca2/acceptance.mjs http://127.0.0.1:5196 workbench/viewer/screens/sca2/wb3_1` | 0 | PASS; 36 checks; 422 successful responses; zero browser errors |
| `c9_dom.mjs` then `c9_check.py` against the verified extraction and number sources | 0 | 324 checks, 0 failures; 14 C9 claim records |
| `env -u PYTHONPATH HF_TOKEN= PYTHONDONTWRITEBYTECODE=1 uv run --project workbench pytest workbench/tests -q -p no:cacheprovider` | 0 | 180 passed, 4 skipped, 3 expected dependency warnings |
| `git diff --exit-code 2309ab0 -- workbench/viewer/public/sca2/sca2_data.json` | 0 | Story JSON byte-identical to WB3 |
| `git diff --check` | 0 | No whitespace errors |

The live main checkout advanced after WB3, so a naive data rebuild changed only the provenance field `main_repo_head`. The final reproducibility probe used the recorded producing main commit `6772a8b` in a detached scratch worktree, current unchanged `build_sca2_data.py`, and the same immutable exports; its output is byte-identical to the committed WB3 JSON. The project source JSON was never left with the later provenance value.

## Boundaries

- No data value, interval, label, heat-map cell, factorial cell, country dot, or featured row was changed.
- No edit was made to `build_sca2_data.py`, any source capture, or `workbench/exports/`.
- Existing W3/W3b modified and untracked files, verifier artifacts, and prior screenshot directories were not staged or adopted.
- No deployment, upload, push, model inference, or weight copy occurred.

## Model route

Producer: `gpt-5.6-sol` via `openai-codex` (Kanban run 94, high reasoning). The dependent verifier task is assigned to a different model family.
