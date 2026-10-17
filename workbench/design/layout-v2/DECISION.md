# DECISION: workbench layout v2

**Recommendation: make variant C, the readout ladder, the default workbench. Keep B, the matrix, as a second tab. Keep the 3D object (variant A) as a third tab, with A's navigation fixes ported into it.** Port C first. It is 2D SVG with no three.js, so it is the cheapest of the three to port and the least likely to break.

Decide by looking:
- **C:** `shots/variant-c-1700.png`, `shots/variant-c-delta-clamped-1700.png`
- **B:** `shots/variant-b-1700.png`, `shots/variant-b-resid-1440.png`
- **A:** `shots/variant-a-1700.png`, `shots/variant-a-search-1440.png`, `shots/variant-a-delta-overview-1700.png`
- **Landing page:** `shots/landing-full.png`
- **Pop-up:** `shots/learn-more-popup.png`

## The premise, challenged (please rule on this, Augusto)

The brief asks how to navigate a 152–306-token object. I think the object is the wrong default for this audience, not just hard to navigate.

1. **The estimand lives in one column.** Eq. 6, the margin, DLA and every conservation check are all read at t*. That is 1 of 152 token positions. A survey researcher's first question is "which parts of the model decided the answer, and what did the fine-tune change?" The ladder answers it in one screen, and it does so as an additive decomposition that visibly sums to the margin (the green Σ line under each group). The other 151 columns hold norms of vectors whose direction toward the answer is never shown. A tall block means "large write", not "pushes the answer".
2. **Even when tamed, the object is a carpet.** Collapsing the boilerplate cuts the scene from 152 to about 75 token columns. The overview preset still looks like the top of a rug (`variant-a-delta-overview-1700.png`). Height in perspective cannot be compared across a 75 × 30 grid. A heatmap (B) shows the same arrays with every cell visible and comparable.
3. **Tokens matter as sources of attention, not as an axis.** In C the prompt is shown as text. A reader finds a token with Cmd-F, not with an orbit control, and sees it light up when a head reads it. That is the token navigation the feedback asked for, and it needs no camera.

So I would not keep "all 306 tokens in 3D" as the landing state of the tool. This is a scope call that belongs to you: the 3D view was the original brief's centrepiece.

## Trade-offs

| | C · ladder | B · matrix | A · object |
|---|---|---|---|
| Answers "what decided the answer?" | directly; sums to the margin | indirectly (the charts below the maps) | only at the readout column, after orbiting |
| Answers "where did the fine-tune act?" | at t* only | every token × layer, A/B/Δ aligned | every token × layer, but hard to compare |
| Finding a token | read it; Cmd-F; find box | find box; segment bands | find box flies the camera; prompt map |
| Long prompt (306 tokens) | text wraps; template collapsed into pills | 2 px per squeezed token; still fits | still long once segments are opened |
| Side-by-side sync beyond the camera | A/B/B−A ladders share hover and pin; prompt shading switches A/B/B−A for the same head; Σ check per group | one crosshair across three maps; hovering a chart layer lights the row in all maps; per-head A/B/Δ bars | synced inspector; arcs in both panels; Δ prompt map; "largest changes" list |
| Shows the clamped pass | yes (toggle; the ladder and the sums switch) | dashed lines in the margin chart | no (the viewer has it) |
| Geometric reading | weak | medium | strong |
| Cost to port | low (SVG) | low (canvas) | medium (three.js; existing code) |

**Fit to the audience (quantitative social scientists).** C fits best. It is a decomposition table with a total, a sign convention and a check that it adds up: the form they already trust. B is the natural second step ("where in the prompt and the depth"). A serves the "anyone curious" reader and the geometric reading the brief asks for. It suits the landing mood better than daily analysis.

**My personal taste, kept separate.** I find A the most beautiful, and the minimap with its view bracket is the nicest single interaction of the three. I like B's density. If I were choosing for myself, I would be tempted to lead with A. I am recommending against that because the screenshots show it answering the audience's question least directly.

## What each variant does about the three pieces of feedback

- **(a) Long prompt.**
  - A collapses template and boilerplate segments into labelled gaps that draw no geometry. Adjacent collapsed segments merge into one gap. A also has a prompt map (a real `resid_norm` heatmap of all tokens) with a bracket showing the tokens in view, a find box that opens the segment and flies to the token, and presets (readout / overview / top-down / layer stack).
  - B squeezes boilerplate to 2 px per token, so every token keeps a column.
  - C turns the prompt into text with pills.
- **(b) Dynamic right panel.** Static text is down to one readout card and a single conservation line. The legend, the formulas, the conservation table and the definitions moved into learn-more pop-ups (`common.js → learnText`). These are filled with live numbers. The inspector follows hover and pins on click.
- **(c) Sync.** Every inspector shows A, B and the exact ‖B−A‖ side by side. B−A of two run arrays is shown in italics and labelled as a browser difference. Each variant's own sync features are in the table above.

## Weak spots found while building (fix in the port, or decide)

1. **The segments are a browser heuristic.** `segments()` splits on chat-template markers and blank lines. It opens a paragraph by default if the paragraph contains one of the item's option labels. That works for WVS Q81. It fails for `bank_USA_00023ac74dac`: the 92-token scenario paragraph stays collapsed by default, because it contains no option label. I checked this through the DOM: 11 pills, and the scenario is one of them. The exporter knows the template, so it should emit `segments: [{a, b, kind, label}]` in the run manifest. That is a Python and contract change, outside this card's fence. **Suggested follow-up card for the engineer.**
2. **B − A of DLA is computed in the browser** (C's third ladder, landing Δ bars). It is exact arithmetic on the exported float32 arrays, and each sum is checked against `d_margin` on screen (it agrees to 4 decimals). If you want it in the contract, add `d_head_attr` and `d_mlp_attr` to the pair export.
3. **In A, arcs to collapsed tokens are dropped silently.** For L23 h0 the top key is in the options segment, which is open. A head that reads the system prompt would show no arc. C does not have this problem: pills show Σ attention, for example "Σ 0.04" on the system-turn pill.
4. **Colour ramps in the heatmaps clip at the 99th percentile** because one sink token flattens everything else. The captions say so, but a reader could still miss it.
5. **The landing page uses no viewer screenshots.** Its "real data" figures are drawn live from the exports. The three thumbnails in section 3 are this folder's screenshots. They are real renders, but of sketches.

## Not done

- No viewer source or Python was edited, and nothing was committed.
- `data/` was not read.
- Only one pair and one item were checked visually. The other exports load through `?a=&b=&item=` but were not reviewed.
