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

# WB6-K2: fixes for the 15 review findings

Same branch (`wb6-cohort`), same fence. Edited: `viewer/src/tab-k.ts`, `viewer/src/cohort-model.ts`, the `.tab-k` rules in `viewer/src/style.css`, this file. No new claim was added.

## What changed, by finding
1. Model output is never "say" or "share": "The base model gives “Good thing” a 5.8% probability on …"; row tooltips read "the model gives … a 66% probability".
2. "Across the 4 comparators it ranges from 5.6% to 66%."
3. One name, **base model**, on the whole tab (legend, axis, glossary, map note, empty state). "A comparator is an adapter or sign prompt compared with the base model." appears once under the headline (and as a glossary entry).
4. The base model is a white bar, the comparator a filled dot. A chevron sits just beyond the comparator, on the side the probability moved to, so a direction shows when the markers overlap (CAN sign prompt 5.8% → 5.6%: bar, dot, left chevron). The line between them is drawn for any change.
5. Layout: tracks, tick labels and gridlines share one column (measured: tick-centre minus track offset = 0 px for 0/25/50/75/100%; axis and track edges differ by 0 px); the matched-pair bracket lives in a gutter that every row has, so the groups no longer shift the columns; rule, head card, groups, rows and map end at the same right edge (1252 px at 1440, 1216 px at 1280); "100%" is 17 px from the "base model → comparator" header; "Most likely answer" wraps (no ellipsis anywhere on the tab); the footer sentence of every pair sits inside its block (-8 px from the block bottom).
6. Legend: a white bar and a teal dot with plain words, not ring/disc controls.
7. Near tie: when the runner-up rounds to the same figure, both get more decimals (Q43 Iran prompt: "Don't mind (50.2%)" next to "Good thing 49.8%").
8. Gold (`--delta`) is used only for the log-odds change. Notes, footers and the bracket are neutral.
9. The sort button reads "Size of change (log-odds)". The note is one general sentence: "Log-odds compare only “A” and “B”, so they can move differently from one answer's percentage."
10. Sign-prompt rows carry their signs and match: "Sign prompt 101111 = China's signs" (map) and "Sign prompt / = China's signs" plus the dots and code (answer view). The match is the country adapter on the same question with the same six signs; with none, the row says "weights unchanged".
11. The map is grouped in the same blocks as the answer view (bracket, background, gap).
12. Legend: gradient bar with end labels −6.24, 0, +6.24 and the unit "log-odds"; "Dark: about zero"; the square-root scale in plain words; "nothing is clipped" removed; `text-wrap: pretty`.
13. Axis ticks 0, 5, …, 30 and 31 with faint gridlines; "← reads the question … writes the answer →" under the axis.
14. Map rows: pointer cursor, hover/focus background, a left accent bar, a chevron (›) at the row end, the focus ring is kept; the survey question is shown above the map.
15. Small labels use `--k-mut` #b3b3b3. A script computed contrast for every text node on the tab (opacity and background composited): lowest ratio 5.5:1 (the row chevron), 0 nodes under 4.5:1, on all 5 questions at both sizes. Count badges no longer use opacity.

## Checks (final source)
- `cd workbench/viewer && npx tsc --noEmit -p .`: exit 0.
- `env -u PYTHONPATH uv run pytest tests -q`: 183 passed, 4 skipped, exit 0.
- Bundle build (`build_deploy_bundle.py --workbench <scratch copy>`): exit 0, 143 files, 733,523,823 bytes compressed. `verify_bundle.py`: exit 0, `pass: true` (`~/.hermes/cache/scratch/wb6k2/verify-report.json`, archive sha256 ad07c3bf…225264e).
- Headless Chromium over the 5 questions, each filter, both sorts, picker clicks, a row Enter, "Open in the Ladder", a map-row click, Q50/Q106, smol empty state, reduced motion; 1440×860 and 1280×720: 0 console errors or warnings, 0 HTTP errors, `__ready === true`.
- Wording scan of the rendered tab (text, tooltips, aria labels, glossary open): "say" appears only inside the quoted survey question; no "share", no "Unchanged".
- Screenshots: `~/.hermes/cache/scratch/wb6/cohort/*-k2.png` (`Q43|Q57|Q81|Q99|Q176` × `-1440|-1280`, plus `-map`, `-rowsend`, `-end`; `Q99-rowhover`, `Q99-rowfocus-map`, `Q99-sizesort`, `Q99-tooltip-cell`, `Q50`).

## Limits
- The viewport shot of a tall page cuts at the pane bottom, as before; the `-rowsend` and `-end` shots show the scrolled state.
- Sign-prompt rows on Q99 look alike in the map; the tab shows that and does not interpret it.
- Frame bar model labels ("LoRA [nf4_dequant, float64]") are in `main.ts`, outside the fence.
