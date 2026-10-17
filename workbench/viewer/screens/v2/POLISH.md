# Workbench v2 polish (card t_20471cca): progress log

1. Ladder kind label: DONE (code). `src/tab-c.ts` prompt(): a `.seglab` line above the open
   `question` part, "Scenario" when `manifest.item.kind == "bank"` (via `isBank`), else "Survey question";
   its title names the exported segment label. Style `.seglab` in `src/style.css`.
2. Merged gaps named: DONE (code). `src/scene.ts` layoutX(): a merged gap keeps the first word of each
   non-marker part it hides, so the label reads "system + persona · 4 parts" (markers-only merges read
   "message markers · k parts"). `Gap` gains `name` and `k`; the token-strip sprite draws "⋯ name" over
   "k parts · n tok". The Σ-arc label and the tab-A inspector note use `label`. The ladder's pills and
   the prompt map draw one band/pill per segment, so they have no merge to name.
3. Tab badge: DONE (code). Same `.badge.data` component as the landing, first in each tab's `.strip`
   (`tab-a.ts`, `tab-b.ts`, `tab-c.ts`): "real data · drawn from the exports". `.strip .badge` margin rule.
4. Prompt-map band labels: DONE (code). `src/tab-a.ts` drawMini() uses `fitWords()` (end of file): the
   longest word prefix that fits the band, with "…"; a `mc.onmousemove` sets the canvas `title` to the
   full label, token count and the click action of the band under the cursor.
6. Landing hero: DONE (code). `src/landing.ts`: axis "after this many layers (0 = …, L = …)"; caption
   "after that many layers"; story "A and B differ most in what layer 23 adds to the margin (the step
   from 23 to 24 on this axis): …". No italic l is left.
7. Inspector gold cells: DONE (code). `src/common.ts` cell(): "‖Δ‖ " prefix (`.lenp`, dimmer) before the
   length in `how === "len"` cells.
5. Tab A framing: DONE (code + screenshots). `src/tab-a.ts` preset(): the fit now bounds the projected
   box's extent (box top raised 5 -> 6.5 for the end labels), keeps a right strip of ~70 px for the
   centred end labels, then pans camera+target (4 iterations) so the box is centred in the remaining
   area; applies to every preset. `src/scene.ts` addMarginRibbon(): "margin …", "clamped …" and
   "h^l·w per layer" are centred over the line's last point (align 0.5) instead of starting to its
   right; the caption sits above the margin label. Positions only; no value or binding changed.
   Checked by eye: polish/pre-a-side-1440.png (before: labels cut at both panels' right edges) vs
   polish/a-side-1440.png and polish/a-side-1700.png (after: both labels inside, grid centred).

## Acceptance (run 2026-10-17, this card)
- `npx tsc --noEmit -p .` -> exit 0 (`polish/tsc.txt`).
- `node leak_end_on_a.mjs` (from `$TMPDIR/pp`) -> exit 0; start {74 geometries, 130 textures} = end
  {74, 130}, flat true, page_errors [] (`polish/leak_end_on_a.json`).
- `node sweep.mjs <abs>/workbench/exports/index.json` -> exit 0; 16 pairs, 64 loads, 0 failures,
  0 console errors, pass true (`polish/sweep.json`).
- Screenshots (`polish/`, made with `screens/v2/shoot.mjs`, 0 console errors each):
  c-bank-1440/1700 (SCENARIO label, badge, ‖Δ‖ cells), a-side-1440 + a-side-1700 (framing), pre-a-side-1440
  (before), a-single-1700, a-pinned-gaps-1700 (Σ arc "system + persona · 4 parts", inspector note),
  landing-1440/1700 (hero axis and caption).

## Seen, not touched (outside this card)
- Tab C at 1440: under the ladder the "embedding" column labels overlap the "✓ All cells + embedding = …"
  sums of the neighbouring panel (c-bank-1440.png, bottom of the ladder). This card did not touch the
  ladder SVG layout; the older c-1440.png is cut off above that row, so "pre-existing" is inferred, not seen.
- Tab A, B panel: the HTML "margin if read off at each layer" inset sits close to the object's front-right
  corner at 1700 (no overlap seen).
