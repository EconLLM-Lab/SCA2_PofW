# layout-v2: landing page + three workbench layouts (sketches)

These are throwaway HTML sketches for choosing a direction. They are not the viewer. The chosen layout gets ported into `workbench/viewer/src/` in a later card. Nothing in `viewer/src/` or any Python was touched.

## Run

```sh
workbench/design/layout-v2/serve.sh          # http://127.0.0.1:5181/design/layout-v2/landing.html
workbench/design/layout-v2/shoot-all.sh      # re-shoots every PNG in shots/ (serve.sh must be running)
```

`serve.sh` serves `workbench/`, so the pages read the real exports from `../../exports/` and three.js from `../../viewer/node_modules/three`. There is no CDN and no build step. Data: pair `smol_inst | smol_inst_usa_e3`, item `wvs_Q81` (152 tokens). `?a=&b=&item=` selects another pair or item.

| File | What it is |
|---|---|
| `landing.html` | The science and method in plain language. Each figure is badged either "real data" (drawn from the exports in the browser) or "illustration · not data". |
| `variant-a.html` | **The object, tamed.** The 3D viewer with collapsed segments, a prompt map, token search, camera presets, a synced A/B/Δ inspector, and a list of the largest changes. |
| `variant-b.html` | **The matrix.** Layer × token heatmaps for A, B and ‖B−A‖, with one shared crosshair. Boilerplate is squeezed to 2 px per token, not dropped. Below the maps are charts of the readout column. |
| `variant-c.html` | **The readout ladder.** Every head and MLP at t* for A, B and B−A. Each group adds up to its margin. The prompt is shown as text and shaded by where the selected head looks. |
| `common.js` | Shared code: export decoding (a port of `viewer/src/data.ts`), prompt segments, the A/B/Δ inspector, the readout card, the learn-more texts and the base CSS. |
| `DECISION.md` | The recommendation. |
| `shots/` | Screenshots at 1700×1000 and 1440×860, plus `landing-full.png` and `learn-more-popup.png`. |

URL state for screenshots: A takes `view=single|side|delta`, `cam=readout|overview|top|front`, `q=`, `fly=t`, `sel=l,h,t` and `still=1`. B takes `qty=resid|attn|mlp`, `pin=l,t`, `hl=l` and `fold=0`. C takes `sel=l,h`, `shade=a|b|d` and `clamp=1`. All three take `learn=<key>` to open a pop-up.

## Bindings (each mark → named export array)

The same rule applies as in the viewer: each mark is one entry of one array. Any number computed in the browser is labelled as computed on the page.

| Mark | Array | Notes |
|---|---|---|
| A: head sliver, MLP block, residual bar | `head_norm`, `mlp_norm`, `resid_norm`; Δ panel: `d_head_norm`, `d_mlp_norm`, `d_resid_norm` | Same instance layout as `viewer/src/scene.ts`. Only x changes: open tokens are packed together. |
| A: readout-column colour | `head_attr`, `mlp_attr` | Same `diverging()` as the viewer |
| A: attention arcs | `attn_topk_idx`, `attn_topk_val` | Arcs to collapsed tokens are not drawn. |
| A: margin polyline | `running_margin` | |
| A: collapsed segment | none | A gap with a label. It draws no geometry. |
| A: prompt map | `resid_norm` (A), or `d_resid_norm` in Δ view | Log colour, clipped at the 99th percentile; the caption says so. |
| A: "largest changes" list | `d_head_norm[:, :, t*]` | |
| B: heatmap cells | `resid_norm` / `attn_norm` / `mlp_norm`, and their `d_*` arrays | One cell = [l, t]. The colour ramp is clipped at p99, as stated. |
| B: per-head bars in the inspector | `head_norm` (A, B), `d_head_norm` | |
| B: margin chart | `running_margin`, `running_margin_clamped` | |
| B: DLA chart | `attn_attr`, `mlp_attr` | |
| C: ladder cells A, B | `head_attr`, `mlp_attr` (or the `*_clamped` arrays), `readout.embed_attr` | |
| C: ladder cells B − A | the same arrays, B minus A | **Computed in the browser.** The page labels it, and the green Σ line checks that it sums to `d_margin`. |
| C: prompt shading | `attn_topk_val` of the selected head at t* | A pill shows the sum over its tokens, labelled Σ. |
| C: margin by layer | `running_margin` (or `_clamped`) | |
| Inspector, everywhere | `compareRows()` in `common.js` | ‖B−A‖ comes from the pair export. The italic B−A is a browser difference. |
| Landing, hero | `running_margin` A, B | The caption text is computed from the arrays (`story()`), not written by hand. |
| Landing, heatmap | `resid_norm` A | |
| Landing, Δ DLA bars | `attn_attr`, `mlp_attr`, B − A | The caption checks the bars against `d_margin`. |
| Landing, transformer schematic | none | Badged "illustration · not data". |

Prompt segments come from a browser heuristic over token text, in `segments()` in `common.js`. This is not an export field. See DECISION.md.
