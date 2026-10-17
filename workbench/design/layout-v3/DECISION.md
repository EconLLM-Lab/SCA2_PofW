# DECISION: workbench v3 (card t_b31e4996)

## Recommendation

**Adopt one frame and one disclosure grammar for every view, and show one face of each object at a time.**
- **The frame (object 1).** Two lines hold the tabs, the A and B slots, the item and a check pill. They replace the top bar, the model line, the real-data banner and the checks card.
- **The answer strip (object 2).** One sentence and two bars replace the answer card. The full card is one click or the `A` key away.
- **The view's own objects.** Each view adds 3 to 5 of its own. A ladder or map shows **B − A by default**. A and B sit in a segmented switch in the same header, not in two more panels.
- **The inspector becomes a drawer.** Nothing is pinned at rest. The five largest changes get gold rings instead of a table.

Port the ladder first, for the same reason as in v2: it is SVG, so it is the cheapest. Then port the frame and the answer strip, which all three tabs share. Then the matrix and the object.

Decide by looking. Every view is in `shots/` at 1440 and at 1700. The gold numbers and the bottom-left caption are the count overlay, not part of the design.

| View | v2 at rest | v3 at rest | Shot |
|---|---|---|---|
| Landing, first screen | 9 | **5** | `landing-*.png` |
| Landing, one section | 4–6 | **5** | `landing-s2-*.png` |
| Ladder | 20 | **5** | `ladder-*.png` |
| Ladder, head pinned | (20; v2 is already pinned) | **6** | `ladder-pinned-*.png` |
| Matrix | 18 | **5** | `matrix-*.png` |
| 3D object | 17 | **7** | `object-*.png` |
| Ladder with a failed check (simulated, `?fail=1`) | – | **6** | `ladder-fail-*.png` |
| 8B ladder, 32 × 33 (illustration) | – | 5 | `scale-ladder-*.png` |
| Picking B from 43 models (illustration) | – | 2 (pop-over open) | `scale-picker-*.png` |
| Cohort: one base vs 42 adapters (illustration) | – | 4 | `scale-cohort-*.png` |

The v3 counts are read from the DOM by `shoot.mjs`: it counts the `[data-obj]` elements visible at rest. They are printed in `shots/report.txt`, together with an interaction self-test of the ladder: pin by click, Esc to unpin, switch face. The v2 counts are by eye, from INVENTORY.md.

## Trade-offs

- **One face at a time loses the instant A | B | B − A glance.**
  - **What is lost:** v2 put three ladders side by side, and each sum could be checked by eye against its own margin. v3 needs one switch press per face.
  - **What softens it:**
    - The margin column always draws both A and B.
    - The check line under the ladder re-sums whichever face is shown.
    - The drawer gives A, B and the change for the pinned cell.
  - **If readers compare A with B more than they read the change,** make A and B the default.
  - **Room:** the grid has room for two ladders at 135M. It does not at 8B, where two ladders of 33 columns take about 1,000 px at 15 px cells, before the prompt.
- **The answer card is behind a click.** The margin's definition (log-odds of 1 vs 4) is no longer on screen at rest. The strip says "pushes toward “A great deal”", and the definition is under `?` and `A`. A first-time reader loses it; a returning reader gains the room. If this worries Augusto, the landing can teach the margin once, since every workbench link starts there.
- **Find (`/`) and the other keys are invisible.** Keyboard disclosure only helps people who know the keys exist, so the `?` in each header must list them.
- **The 3D object in this mockup is an isometric SVG stand-in.** It uses the same `resid_norm` and the same collapsed segments. It shows the layout (two scenes, the inset, the minimap) but not the three.js rendering. The port keeps the real scene.
- **The matrix's B − A map is mostly bright.** `d_resid_norm` grows with depth almost everywhere, so even on a linear p99 scale the top third saturates. That is a true reading: the change builds up through the layers. But it makes the running state a weak answer to "where did the change happen?". The attention-write and MLP-write quantities are more local. Before the port, check whether `attn` makes a better default quantity for the matrix.

## Is 7 ± 2 the right premise everywhere?

Mostly yes. Two caveats, put on record here rather than worked around:
1. **The matrix and the ladder each count as one object, but neither is simple.** A 31 × 152 map or a 30 × 10 ladder holds hundreds of comparable marks. Miller's limit is about chunks held in working memory, not marks scanned in a chart. Counting each as "1" is right for the layout. It says nothing about whether the chart reads well. That depends on its own key and scale, which v3 keeps in the object's footer.
2. **The landing and the picker sit below the 5–9 band (5 and 2).** That is on purpose: a landing should have one job, and a pop-over takes over the screen. I would not add objects to reach a quota.

## Personal taste, kept separate

- **Taste.**
  - I like v3's quiet frame, and the ladder's single face with gold rings. It reads like a well-set table.
  - I miss v2's three ladders side by side as a picture. They were the workbench's most "engineering tool" moment.
- **Fit to the audience** (quantitative social scientists on a first visit). One face plus a sentence fits better. These readers need "what changed, and does it add up?" before they need each model's decomposition. The check line keeps the "does it add up" promise on every face.

## What disclosure must never hide (rules for the port)

1. **A failed check is always visible at rest.** The pill turns into a red banner under the frame. The banner cannot be dismissed, and it names the check, its value and its threshold. See `ladder-fail-*.png`, simulated with `?fail=1`; the banner says it is simulated.
2. **The re-sum line under every ladder and map face stays at rest.** "✓ cells + embedding = margin" never moves into a drawer.
3. **The sign convention stays at rest.** The ladder footer names both answers ("toward “None at all” · toward “A great deal”"). Blue and orange mean nothing without it.
4. **When the clamped run is on, the frame shows it,** not only the pressed button. A reader must not mistake clamped numbers for the normal run. (Not mocked up; this is a rule for the port.)
5. **When the colour scale clips, the clip value is shown at rest.** The matrix footer prints the p99 value and the maximum.
6. **The "illustration · not data" badge sits in the frame,** not only on the figure. A screenshot of any part of a placeholder view then still carries it.
7. **A number computed in the browser keeps its marking** (italic, or "browser") in the tooltip and in the drawer too.
8. **Collapsed template text keeps its Σ attention on the collapsed line while a head is pinned** ("⋯ template text · … · Σ attention 0.10"). Without it, a head that reads the system prompt looks as if it reads nothing.

## The scale check (8B, 43 models)

- **The ladder at 32 × 33** (`scale-ladder-*.png`, illustration).
  - It fits: cells are about 15 px at 1440 and 18 px at 1700, measured from the SVG.
  - It is limited by height, not width.
  - Heads are grouped into the 8 KV groups of 4, with 3 px gaps, so "head 13" reads as group 3, position 1.
  - The prompt narrows from 4 to 3 grid columns, and the margin column is unchanged.
  - The one-face rule is what makes this fit. Three faces would not.
- **Picking A and B from 43 models** (`scale-picker-*.png`, illustration).
  - Two slots replace one select of pre-made pairs. 43 × 42 = 1,806 ordered pairs cannot fit in a select.
  - Each slot opens a searchable pop-over: the base on top, then the 42 adapters in a 7 × 6 grid, with ↑ ↓ ⏎ on the keyboard.
  - Each chip carries that adapter's d_margin on the current item, so the menu doubles as a sort.
  - The country list in the mockup is a placeholder. The real menu comes from `index.json → models`.
- **The cohort overview** (`scale-cohort-*.png`, illustration).
  - It is a fourth tab, "Cohort", where slot B reads "all 42 country adapters".
  - It shows a 42 × 32 map of the change in push by layer, with the rows sorted by d_margin, and a d_margin bar column beside it. The map will later bind to the pair arrays `d_attn_attr + d_mlp_attr` for each (base, adapter).
  - Clicking a row opens that adapter as B in the ladder.
  - It fits the same frame with 4 objects.

## Not done, or still open

- These are mockups only. `viewer/src` and the Python were not edited, `data/` was not read, and nothing was committed.
- **Not mocked up** (all three reuse components that are already shown):
  - the answer-card pop-over;
  - the learn-more modal;
  - the matrix and the object with a cell pinned. Their drawer is the same component as the ladder's.
- The 3D object is an SVG stand-in, not three.js (see the trade-offs).
- The scale views use seeded placeholders (`fake()` in `v3.js`). They are badged in the frame and on the figure.
- **Left to Augusto:**
  - the default face (B − A, or A and B);
  - whether "Cohort" becomes a tab;
  - the matrix's default quantity.
