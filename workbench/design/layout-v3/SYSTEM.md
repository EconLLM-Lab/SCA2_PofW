# SYSTEM: one design system for the v3 workbench (card t_b31e4996)

Rendered in `v3.html` (all views; `?view=…`). Tokens live in `v3.css`.

## 1. Grid

| Token | Value | Why |
|---|---|---|
| Max content width | **1240 px** | At 1440 the frame leaves 100 px each side; at 1700 it leaves 230 px. The screen is not filled because it is there. |
| Outer margin | `max(64px, (100vw − 1240px) / 2)`, never below 64 px | Generous by Augusto's ask. 64 px is the floor at 1366 px laptops. |
| Columns | 12, gutter **32 px** (≈ 74 px per column at 1240) | |
| Vertical rhythm | 8 px base; 48 px between the frame and the work area; 32 px between objects | |
| Work area height | the viewport minus the frame (≈ 120 px) minus a 48 px bottom margin | The workbench views never scroll at rest. The landing scrolls. |

Column use at rest:
- **Ladder:** prompt 4 cols · ladder 6 cols · margin-by-layer 2 cols.
- **Matrix:** map 10 cols · margin column 2 cols.
- **3D object:** scene A 5 cols · margin inset 2 cols · scene B 5 cols; minimap 12 cols below.
- **Drawer (pin):** slides over the rightmost 4 cols, never outside the 1240 px frame. It covers the
  margin column, which the drawer repeats for the pinned row.

## 2. The fixed frame (object 1 on every view)

One block, two lines, identical on every view:

```
SCA2 workbench    Ladder · Matrix · Object               ✓ N checks     ?
A  SmolLM2-135M-Instruct  ▾   vs   B  Instruct + USA DPO LoRA (3 ep.)  ▾      item  wvs_Q81 · confidence: charities ▾
```

- The model pair is two **slots** (A, B), not one select of pre-made pairs. At 43 models a pair
  list has 1,806 entries; two slots scale (see `?view=scale-picker`).
- The **status pill** replaces the checks card and the real-data banner. Green "✓ N checks" at rest, N counted live from every `conservation.thresholds` key of run A, run B and the pair (7 for the default pair).
  **If any check fails it becomes a red banner under the frame (a new object) and cannot be dismissed.**
- `?` opens the learn-more pop-up for the current view (key `L` / `?`).

## 3. The answer strip (object 2 on every workbench view)

One line: `B pushes toward “A great deal” 1.86 more than A   A ▮▮▮ 1.06   B ▮▮▮▮▮▮ 2.92   P(“1”) 0.52 → 0.78`.
Click or key `A` opens the full answer card (codes, four probability bars, the clamped tick) as a
pop-over anchored to the strip. Bound to `readout.margin`, `readout.probs`, pair `d_margin`, `d_probs`.

## 4. Disclosure layers

| Layer | Trigger | What appears | Where |
|---|---|---|---|
| 0 · at rest | none | frame, answer strip, the view's 3–5 own objects | grid |
| 1 · hover | pointer over a mark | a tooltip: A, B, B − A of that mark, 3 rows max | at the cursor, never covering the hovered row |
| 2 · pin | click a mark (Esc to unpin) | the **inspector drawer**: full A / B / change table, the attention list, the weights moved; the prompt shades for that head | right 4 cols, inside the frame |
| 3 · pop-up | `?`, `L`, "how to read" | learn-more text with live numbers; the full answer card; all checks | centred modal, 640 px |
| mode | segmented control / keys | A · B · B − A face of the one ladder / map; clamped run (`C`) | the object's own header |

Keyboard: `1 2 3` tabs, `A` answer card, `C` clamped, `/` find, `Esc` unpin, `?` help, `[ ]` step
the pinned head through the layer.

## 5. Where things go when they are not at rest

| Thing | v2 home | v3 home |
|---|---|---|
| Answer card | right column, always | answer strip at rest; full card as a pop-over (`A`) |
| Checks | right column card + a pop-up | frame pill (passing) → pop-up on click; **red banner at rest when failing** |
| Legends / colour keys | separate rows | the object's own footer line, one line, for the face shown |
| Inspector | right column, pinned by default | hover tooltip; pin drawer. Nothing pinned at rest |
| Largest changes | table / list at rest | gold ring on the top five marks at rest (no new object); full list in the drawer |
| Find | box in the toolbar | `/` opens it in place of the object header |
| Explainers, definitions | banner + scattered buttons | one `?` per object header |

## 6. Type budget: 4 sizes in the workbench (+2 on the landing), 3 families

| Size | Use |
|---|---|
| 11 px mono (tracked caps for labels) | object labels, axis ticks, key and check lines, tooltip |
| 13 px sans / mono | body, drawer table, buttons' text is 11 |
| 15 px serif | the prompt as text (it is read, not scanned) |
| 17 px sans | the answer strip's sentence, drawer title (landing: lede, serif) |
| landing only: 28 px serif, 44 px serif | section titles, headline |

Numbers are always mono. `v3.css` uses exactly these sizes (11, 13, 15, 17, 28, 44).

## 7. Colour budget: one meaning per colour

| Colour | Means | Never means |
|---|---|---|
| warm grey `#cfc8bb` | model **A** (lines, slot chip) | a sign |
| teal `#4fc1a6` | model **B** | a sign |
| blue `#6b9bff` | **pushes toward j₊** (code 1) | a model |
| orange `#ff9a3c` | **pushes toward j₋** (code 4) | a model |
| gold `#ffcf5c` | **change B − A** (size or signed) and the selection ring | anything else |
| purple `#c58bff` | the **clamped run** (Quadrant III) | |
| red `#ff5f56` | **a failed check**, only | errors of the page itself use plain text |
| green `#62c370` | passing check, one place (the pill) | |

The writer's collision (blue = model A and = pushes toward answer 1) is gone: A is grey, B is teal,
and blue/orange only appear on signed pushes. A diverging B − A ladder is still blue/orange (it is a
signed push of the change), with a gold frame that says "this is the change".
