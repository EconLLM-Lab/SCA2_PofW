# WB6-K acceptance: Cohort tab for social scientists

Branch `wb6-cohort` (from `e9b5fda`). Files changed: `viewer/src/tab-k.ts`, new `viewer/src/cohort-model.ts`, rules scoped under `.tab-k` in `viewer/src/style.css`, this file. Nothing else was edited.

## What changed
- Headline column: per comparator, the base model's probability of the answer `item.j_plus` against the comparator's (from `index.runs[].probs`, shown as percentages), as a dumbbell on a fixed 0 to 100% axis. A second line gives the most likely answer for base and comparator (needed on the 10-point questions, where one answer has a tiny share).
- Question picker: the 5 questions with 3 or more comparators on the base (Q43, Q57, Q81, Q99, Q176), by short wording; the full text and id are shown below and in the tooltip. A click goes through the app's `data-go` navigation with a `b` that has a pair on that question (the current `b` when it has one). Q50 and Q106 (2 comparators each) are named in a plain note with Ladder links; opening them draws the saved answers plus a "too few to compare" note and no layer map.
- Filters (both / country adapters / sign prompts) and order (matched pairs / size of change), kept in the URL keys `show` and `sort`. Matched pairs: adapter and sign prompt with the same six signs share a bracketed block with one computed sentence, e.g. "Same six signs: in the weights (Canada adapter) the log-odds of “Good thing” over “Bad thing” move +14.6; in words (sign prompt 111111) +0.742."
- Layer heatmap kept (attention + MLP block per layer, square-root diverging blue/orange scale), now under "Where in the model the change happens" with plain legend. Hover or focus: plain tooltip with the number. Click or Enter on a row, or its "Open in the Ladder →" link: `?tab=c` for that pair.
- Plain words: country names instead of ISO codes, no "LoRA", "margin", "d_margin", "DLA" on screen except as "technical name" lines inside "What do these words mean?".
- Accessibility: rows and controls focusable (`aria-pressed`, `aria-label` per row), focus ring, `prefers-reduced-motion` rule (verified `transition-duration: 0s`), 1280×720 readable.
- Kept: `id="answer"`, `data-obj` hooks (`answer`, `cohort`, `cohort-legend`, `dmargin`, new ones), `window.__ready`, `ctx.ready()`. Empty state for bases with no question of 3+ comparators is kept (smol checked).

## Checks (all run on the final source)
- `cd workbench/viewer && npx tsc --noEmit -p .`: exit 0.
- `pytest tests -q`: 183 passed, 4 skipped, exit 0.
- Bundle build: exit 0, 143 files, 732,638,050 bytes compressed. `verify_bundle.py`: `pass: true` (report `~/.hermes/cache/scratch/wb6k/verify-report.json`).
- Headless Chromium on the verified extraction (`python3 -m http.server`): 5 questions, each filter, both sorts, picker clicks, Enter on a row, "Open in the Ladder" link, heatmap row click, Q50/Q106, smol empty state, at 1440×860 and 1280×720: 0 console errors/warnings, 0 failed requests, `__ready === true` every time.
- Screenshots: `~/.hermes/cache/scratch/wb6/cohort/` (`Q43|Q57|Q81|Q99|Q176` `-1440.png`, `-1280.png`, `-map.png`; `Q99-sizesort-1440.png`, `Q99-tooltip-cell-1280.png`, `Q99-rowfocus-*.png`, `Q50-*.png`). I looked at them.

## Build note
The builder rejects symlinked `exports/` and needs gitignored `viewer/screens/v2|v3|v4/*.png`. I built from a scratch copy (hard-linked exports, copied screenshots, my `src/`) with `--workbench`. The PNGs copied into the worktree are gitignored and not committed.

## Known limits and items outside the fence
- The frame bar (main.ts) still shows model labels with "LoRA [nf4_dequant, float64]". Not editable here.
- On Q57 and the 10-point questions the "Most likely answer" line truncates with an ellipsis at some widths; the row tooltip has the full numbers.
- On the 10-point questions the log-odds compare only the two ends, so a positive change can sit beside a falling share of that answer; the tab says so.
- Sign prompts sit in the same row list as adapters; the sentence compares each only with the base. No claim that a model represents a country.
