# WB4 acceptance: landing page on the Paper B model, Cohort labels, safe failure path

Producer: orchestrator (`default`, Claude). Independent check: WB4-V (Codex, a different model family).
Built from the working tree on top of `eb9d929`. Nothing was deployed before WB4-V.

## Why

After the Space went public (2026-10-20), a walkthrough found four problems:

1. The landing page and the workbench default taught with SmolLM2-135M (30 layers, 576 numbers per token, 9 heads,
   a USA DPO LoRA from the development stage). None of the Paper B adapters appeared until the selectors changed.
2. Cohort clipped every row label at the same prefix, so an adapter and a sign prompt could not be told apart, and
   the title called all four rows "adapters".
3. When a pair failed to load, the selectors showed the new pair while the panels kept the old pair's numbers. This
   was reproduced on the live Space: "Llama + CAN, wvs_Q43" was shown over SmolLM `wvs_Q81` data.
4. The Space opened on the workbench landing page, not on the Paper B story.

## What changed

- `viewer/src/main.ts`:
  - `DEFAULT` is now the Paper B base against the CAN cohort-1 adapter on `wvs_Q43`. `TEACHING` keeps the SmolLM pair.
  - While a pair loads, the old figures are greyed out and inert.
  - A failed load clears the page and shows one error panel, so no figure from another pair stays on screen.
  - Only the newest route may draw or report an error (`routeSeq`).
- `viewer/src/landing.ts`:
  - The model sizes (4,096 / 32 heads / 14,336 MLP units / 32 layers), the term counts (1,024 head terms, 458,752
    neuron terms) and the adapter description (country, LoRA rank, attention-only) are read from the run manifest.
    None are typed in.
  - The page states which model it shows, and links to the teaching example and back.
  - "Read the Paper B story" is a hero button.
  - The checks paragraph no longer claims SmolLM's 1e-10 tolerance for every run; it points to the table.
  - There are four view cards, including Cohort, with v4 thumbnails of the new default.
  - The Limits section is model-specific: a CPU re-run for the Paper B model, and the 135M stand-in for SmolLM. The
    arXiv references are unchanged; that is Augusto's call.
- `viewer/src/tab-k.ts`:
  - Rows are named "CAN adapter · signs 111111" and "sign prompt 111111 = CAN's signs". The full label shows on hover.
    Signs come from the bundled `sca2/sca2_data.json`, and rows still draw without it.
  - The title counts adapters and sign prompts separately.
  - The d_margin bars carry their values.
  - A one-paragraph legend explains weights vs words.
- `viewer/public/sca2/index.html`: the nav adds "How the workbench works" and "Cohort: weights vs words".
- `scripts/build_deploy_bundle.py`:
  - `DEFAULT` and `TEACHING` each resolve to the single export folder that holds them. Zero or two homes fail closed.
  - The images are now v4 thumbnails plus the v3 Cohort illustration.
  - `SCRATCH` is overridable (`SCA2_BUNDLE_SCRATCH`) and resolved. This fixes WB1-V F4, WB3-V N3 and WB3.1-V N3.
- `tests/test_deploy_bundle.py`: the fixture uses an adapter-folder `DEFAULT` plus `TEACHING`, with two new tests:
  pin resolution, and an unresolvable pin failing closed.
- Space `README.md` (deploy-time, not in git): `app_file: sca2/index.html`, so the Space opens on the story page.

## Evidence

- `npx tsc --noEmit`: exit 0.
- Workbench suite (`env -u PYTHONPATH HF_TOKEN= uv run --project workbench pytest workbench/tests -q`):
  183 passed, 4 skipped.
- `build_deploy_bundle.py`: 143 files, payload 918,429,543 bytes (cap 950,000,000), archive sha256
  `e6102a8380c31fffdbf8ae00ad5e77d6cce866d854c50ccaa2e75566c7a1daf4`.
- `verify_bundle.py` into a fresh directory: pass. 143 files, 37 runs, 29 pairs, 66 capture manifests.
- Browser pass on the verified extraction (Playwright, 1440x860):
  - All four tabs reach `__ready === true` on the new default.
  - The landing renders the Llama sizes, and the teaching link renders the SmolLM copy.
  - The story page shows the C9 step and takeaway.
  - All 28 featured story links reach ready with no failed request.
  - An injected HTTP 401 on the IRN pair yields only the error panel. The only console errors are those injected 401s.
- Cohort on the default: CAN adapter +14.6, IRN adapter +6.72, sign prompt 111111 (= CAN's signs) +0.742, sign
  prompt 110111 (= IRN's signs) +0.266.

The thumbnails are in `viewer/screens/v4/` (gitignored like v3); the review shots are in the PM's scratch.
