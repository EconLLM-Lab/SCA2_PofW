# Taste pass: individual + side-by-side views (presentation only)

Screens are 1700x1000 headless Chrome (swiftshader), item wvs_Q81, pair smol_inst | smol_inst_usa_e3, sel=23,0,151.
Re-shoot with `screens/shoot.sh <suffix>`. The sidebar check is `node screens/sidebar-check.mjs <out.png>`, which exits 0 if the sidebar fits the window.
The full source diff is in `screens/taste.diff`.

| before | after |
|---|---|
| individual-before.png | individual-after.png |
| side-values-before.png | side-values-after.png |
| side-delta-before.png | side-delta-after.png |
| sidebar-bottom-before.png (FAIL: sidebar bottom at 941 px in a 913 px window) | sidebar-bottom-after.png (PASS: 913 of 913) |

## Changes (one per line: what, why, binding check)

- Camera FOV 42° -> 30° (`FOV` in scene.ts). Why: a narrower lens foreshortens the far layers less, so L29 is not crushed against L25. Binding: camera only; no geometry changes.
- Default camera, individual view: target `tr-16, 0, -0.41*depth`, offset `(32, 58, 70)`. Why: the readout column now runs up the frame with every layer label, the margin polyline and its value in view, and there is less dead floor at the bottom. Binding: camera only.
- Default camera, side by side: target `tr-8, 0, -0.53*depth`, offset `(16, 72, 104)`. Why: the polyline and its "margin x.xxx" label now fit inside each panel (before, they were at or past the panel edge) and the empty sky is smaller. Binding: camera only. `cam=` in the URL still overrides it.
- Readout outline: 1 px `THREE.Line` -> 2.5 px `Line2` (same five points, same `COLORS.pos`). Why: WebGL ignores `linewidth`, so before it was a hairline. Binding: line weight only. The colour and the column it frames are unchanged.
- Margin polyline: 1 px -> 3 px `Line2`, and the clamped pass stays dashed (`LineMaterial` dashes). The zero line is 1.5 px, and the layer dots have radius 0.07 -> 0.11. Why: before, the polyline was the faintest mark on screen. Binding: the points are still `y0 + running_margin[l]*k` at `z = -l*SZ + 0.78`, with the same k, the same y0, and one dot per layer.
- Margin polyline x offset: `T-1+1.6` -> `T-1+4.2`. Why: it sat on top of the readout outline and collided with the right-hand layer labels. Binding: placement only. Y still encodes the margin and z still encodes the layer, and the polyline still sits beside the readout column, as the legend says.
- Fat-line resolution: `TensorScene.setResolution(w/n, h)` is called from `resize()`. Why: `Line2` needs the viewport size for its pixel width. Binding: none.
- Layer labels: floor planes (2.4x0.9 world units, foreshortened) -> camera-facing sprites with a fixed 12 px on-screen size, `sizeAttenuation:false`. Every 5th label is brighter. The right-hand labels moved to just right of the last token. Why: the far layers were unreadable, and the right-hand labels collided with the polyline. Binding: labels only. Each label still names layer l at z = -l*SZ.
- Text sprites (margin value, "0", caption) now use a fixed on-screen pixel size (`textSprite(..., px, align)`), and the caption is shortened to "h^l·w per layer" and placed under the margin value. Why: the caption sat over L0–L2 and was cut at the panel edge. Binding: labels only.
- Token strip: font 26 -> 32 px bold and #d4d4d4 -> #e6e6e6. The strip is hinged at its edge in front of layer 0 and tipped 0.75 rad toward the viewer. Why: on the floor, at grazing angle, it was the smallest text in the scene. Binding: one slot per token at x = t*SX, as before. The readout token is still blue.
- Head vs MLP separation: the MLP category colour #b8b8b2 -> #a8a49a (sand), and the dim in DLA mode off the readout column goes from 0.55/0.55 to heads 0.62, MLP 0.42. Why: the two dimmed colours had nearly the same luminance, so slivers and blocks merged at a distance. Now the heads are lighter blue-grey and the MLP blocks darker sand. Binding: these are constant category colours that bind to no value. The readout-column DLA colours (blue = toward j+, orange = toward j-, `diverging()`), the Q3 colour, the Δ colour and every height are unchanged. The legend swatch now matches the MLP colour.
- Legend wording: one sentence was added, saying that off the readout column the head and MLP colours are category colours only. Why: the bluish heads could be read as "DLA toward j+". Binding: wording only.
- Layout: body is a flex column and `main` is `flex:1; min-height:0` instead of `height: calc(100% - 45px)`. Why: the toolbar wraps to two rows (73 px), so the last ~28 px of the sidebar were below the window and could not be reached. Binding: CSS only.
- Pair dropdown: `max-width: 520px` -> `none`. Why: "A SmolLM2-135M-Instruct · B Instruct + USA DPO LoRA (3 epochs)" was cut off. Binding: CSS only.
- Panel labels (A / B / ‖B − A‖): 14 px, semibold, darker backing. Why: they were the same weight as the toolbar text and were lost over the blocks. Binding: CSS only.

## Not changed (fence)

The height formula (`height()`), `makeScale` and the shared A/B scale rule, `deltaColor`, `diverging`, the arc tube radius `0.025 + 0.09*A` and the arc opacity `0.45 + 0.55*A`, the instance positions and sizes of every head, MLP and residual mark, and every exported array are unchanged. No marks were added except label sprites that name an existing axis or value. No files outside `workbench/viewer/` were touched. `npx tsc --noEmit -p .` (run in workbench/viewer) exits 0.
