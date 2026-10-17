# INVENTORY: what the shipped v2 shows at rest (card t_b31e4996)

Counted from `viewer/screens/v2/final/{landing,c-q81,b,a-side}.png` (1700 x 1000, default pair
`smol_inst | smol_inst_usa_e3`, item `wvs_Q81`). An object is a chunk a reader parses on its own
(the card's definition). A grouped toolbar counts as 1. Text inside a card does not count. Small
"learn more" / "what is X?" buttons that sit inside a panel header are counted once per view as a
scattered object, because the eye has to find each one.

Verdicts: **keep** · **merge → X** · **on demand (trigger)** · **drop (reason)**.

## Ladder (tab C): 20 objects at rest → 5 in v3 (6 with a head pinned)

| # | Object (v2) | Verdict |
|---|---|---|
| 1 | Top bar: brand + three tabs + pair select + prompt select + About | **merge → frame** (one line, object 1) |
| 2 | Model line "A: … · B: … · wvs_Q81 · who are A and B?" | **merge → frame** (the pair picker *is* the model line) |
| 3 | Real-data banner + one-sentence explainer + "How to read this" | **drop** banner on tabs (the frame says "real data" once, as a word in the item chip); explainer → **on demand** (`?` key / "how to read" in the frame) |
| 4 | Control group: model run normal / Quadrant III clamped + "what's this?" | **on demand** (mode switch inside the ladder header; key `C`) |
| 5 | Control group: shade the prompt by A / B / B − A | **drop** as a control: shading follows the ladder's own A / B / B − A switch |
| 6 | Find box | **on demand** (`/` key; Cmd-F already works on the prompt text) |
| 7 | Prompt panel header + "what are these grey pills?" | **merge → prompt** (header is the panel's own label) |
| 8 | Five template pills, each with Σ attention | **merge → one line** "⋯ template text · 6 parts" inside the prompt; expand on click |
| 9 | "Survey question" label + question text + options | **keep** (the prompt object) |
| 10 | Attention-weight colour key (bottom left) | **on demand** (appears only when a head is pinned, because shading only exists then) |
| 11 | "Largest changes in push on the margin" table | **merge → ladder** (the five largest B − A cells get a gold corner tick; the table opens in the pin drawer) |
| 12 | Ladder A | **mode switch** (A / B / B − A segmented control; default B − A) |
| 13 | Ladder B | **mode switch** (same) |
| 14 | Ladder B − A | **keep** (default face of the one ladder) |
| 15 | Margin-by-layer chart | **keep** (shares the ladder's layer rows; A and B as two lines) |
| 16 | Three green check lines under the ladders | **merge → ladder footer** (one line for the face shown; red and promoted to the frame if any fails) |
| 17 | Push colour key | **merge → ladder footer** (same line as the check) |
| 18 | Answer card (margin definition, codes, A/B probability bars, change, purple tick) | **merge → answer strip** (one sentence + two mini bars at rest; full card on click / key `A`) |
| 19 | "The parts add up" checks card | **merge → frame status pill** "✓ 7 checks" at rest; **always expanded at rest when a check fails** |
| 20 | Inspector, pinned by default (head 0 · layer 23), with its 16-row attention list | **on demand**: hover = tooltip at the cursor; click = pin drawer. **Nothing is pinned at rest** (v2 pinned the largest change "as a starting point"; v3 marks it with a gold ring instead) |
| (+) | Six scattered "learn more / what is …" buttons | **merge → one `?` in each object's header**, plus the `L` key for the learn-more pop-up |

## Matrix (tab B): 18 objects at rest → 5 in v3

| # | Object (v2) | Verdict |
|---|---|---|
| 1 | Top bar | **merge → frame** |
| 2 | Model line | **merge → frame** |
| 3 | Real-data banner + explainer + "What is the size of a vector?" | **drop** banner; explainer **on demand** (`?`) |
| 4 | Quantity switch (running state / attention write / MLP write) | **keep** as the map's header control (with fold, object 3) |
| 5 | Find box | **on demand** (`/`) |
| 6 | "Template text: squeezed" toggle | **merge → toolbar** (object 3) |
| 7 | Map A + its caption row ("Rows: layers… Colour: one log scale…") | **mode switch** (A / B / B − A on the one map; default B − A) |
| 8 | Colour ramp for A and B | **merge → map footer** (one key for the face shown) |
| 9 | Map B + caption row | **mode switch** (same) |
| 10 | Map B − A (gold) + caption row | **keep** (default face) |
| 11 | Gold ramp + p99 caption | **merge → map footer** |
| 12 | Margin-if-read-off chart | **keep**, re-cut as a narrow column on the map's right edge sharing its layer rows (object 5) |
| 13 | Push-by-layer chart | **on demand** (it is the ladder's information; the ladder tab owns it; key `2` jumps there) |
| 14 | Answer card | **merge → answer strip** |
| 15 | Checks card | **merge → frame status pill** |
| 16 | "Compare A and B for one cell" placeholder card | **drop** (it is an empty-state instruction; the hover tooltip teaches the same thing) |
| 17 | Token axis labels under the change map | **merge → map** (labels only for open parts; template parts get one band label) |
| 18 | Scattered "learn more / how are colours scaled? / what is ‖B−A‖?" | **merge → one `?` per object** |

## 3D object (tab A, side by side): 17 objects at rest → 7 in v3

| # | Object (v2) | Verdict |
|---|---|---|
| 1 | Top bar | **merge → frame** |
| 2 | Model line | **merge → frame** |
| 3 | Toolbar 1: show (A only / A next to B / A next to the change) | **keep** as the scene header (object 3), with the camera presets |
| 4 | Toolbar 1: camera presets (answer position / whole object / from above / layer stack) | **merge → scene header**, presets also on keys `1`–`4` |
| 5 | Toolbar 1: find box + "show all template text" + height (log) | find **on demand** (`/`); "show all" **on demand** (minimap click); height **drop** at rest (log is the default; linear stays in the `?` pop-up) |
| 6 | Toolbar 2: colour select + clamped-run checkbox | **on demand** (key `C` for clamped; colour select → inside the `?` pop-up) |
| 7 | Real-data banner + long explainer | **drop** banner; explainer → axis key (object 7) + `?` |
| 8 | Panel label A | **merge → scene A** |
| 9 | Scene A | **keep** |
| 10 | Panel label B | **merge → scene B** |
| 11 | Scene B | **keep** |
| 12 | "Margin if read off" inset | **keep**, moved out of scene B into the gutter between the two scenes (object 6), A and B lines |
| 13 | Answer card | **merge → answer strip** |
| 14 | Checks card | **merge → frame status pill** |
| 15 | "Compare A and B for one block" placeholder card | **drop** (empty-state instruction; tooltip teaches it) |
| 16 | "Heads whose write changed most" list | **on demand** (drawer, key `D`; the top five also get gold rings in the scene) |
| 17 | Prompt map caption + prompt map strip (bands + heatmap + bracket) | **keep** as one object (minimap, object 5), caption **drop** (its band labels say it) |

## Landing: 9 objects in the first screen (already near the budget) → 5

| # | Object (v2) | Verdict |
|---|---|---|
| 1 | Nav bar (brand + six links + "Open the workbench") | **keep**, trimmed to brand + 3 links + open |
| 2 | Headline | **keep** |
| 3 | Lede paragraph | **keep** |
| 4 | Small print (audience + SCA2 + arXiv) | **merge → lede** (one muted line under it) |
| 5 | Two buttons | **keep** as one group |
| 6 | Hero chart card: badge | **merge → hero chart** |
| 7 | Hero chart | **keep** |
| 8 | Hero long caption (question text + story, ~90 words) | **on demand**: one line at rest ("B ends 1.86 higher than A"), full story under "read the story" |
| 9 | The top of section 1, already visible below the fold line | **drop from the first screen** (the hero takes the first 860 px; section 1 starts below) |

Landing sections (scrolled) have 4–6 objects each in v2 and are not cluttered; v3 keeps them, with
the number / title / text / one figure rhythm, and moves the six-row conservation table behind
"show all checks" (already done in the port).

## Totals

| View | v2 at rest | v3 at rest |
|---|---|---|
| Landing, first screen | 9 | 5 |
| Ladder | 20 (+ scattered help) | 5 (6 with a head pinned) |
| Matrix | 18 | 5 |
| 3D object (side by side) | 17 | 7 |

The PM's estimate of 15–25 per tab holds: 17–20. The v3 numbers are measured from the mockups (`shots/report.txt`, DOM count of `[data-obj]`); v2 numbers are counted by eye from the screenshots.
