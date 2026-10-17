# Viewer: SCA2 workbench (landing + ladder | matrix | 3D object)

The viewer has two views. **Individual network** shows one model. **Side by side** shows A next to either B or ‖B − A‖. Both use one shared camera.

## Run

```bash
cd workbench
# 1. captures (float64, CPU, about 1 min per pair; writes exports/, gitignored)
PYTHONPATH=src uv run python -m sca2_workbench.export --pair smol_base smol_inst
PYTHONPATH=src uv run python -m sca2_workbench.export --pair smol_inst smol_inst_usa_e1 \
  --items wvs_Q57 wvs_Q43 wvs_Q81 bank_USA_00023ac74dac bank_USA_7232414df567 bank_USA_f48d3d37c50e
# 2. contract tests
cd .. && env -u PYTHONPATH uv run --project workbench pytest workbench/tests -q
# 3. viewer
cd workbench/viewer && npm install && npx vite      # http://127.0.0.1:5178
```

Routes: `/` landing, `?tab=c` ladder (default), `?tab=b` matrix, `?tab=a` 3D object. The URL holds each tab's whole state (keys in `screens/v2/NOTES.md`); shared keys `a`, `b`, `item`, `learn`.

## What each mark is

The full contract is `../spec/export_contract.md`.

- **X** is token position, left to right. **Z** is layer, with L0 nearest the viewer. **Y** is magnitude.
- **Residual bar** before each layer: ‖h^l_t‖.
- **Nine head slivers**: ‖o^l_{h,t}‖.
- **MLP block**: ‖m^l_t‖.
- **Readout column** (blue outline): heads and MLP blocks are coloured by DLA to the margin. Blue means toward j₊, orange toward j₋.
- **Polyline** beside the readout: h^l_{t*}·w per layer. Its last point is the margin.
- **Clicking a head** draws its attention arcs from the stored top-16 keys in every panel. Arc radius and opacity follow A[q, k].
- **Heights** use one scale per quantity, shared by A and B. Log or linear is selectable, and the exact formula is printed in the legend. In Δ mode the right panel has its own Δ scale, and its colour uses the same mapping as its height.

## Conservation bar

The bar shows the Python checks for every pass. It also shows one check recomputed in the browser: ΣDLA (embedding + heads + neurons) against the margin, using the float32 arrays that are drawn.

## Not built yet

These are out of scope for this slice:
- the 2D phase-plane view (View 2)
- the cross-country overlap curve (View 3)
- live steering (View 4)
- live re-runs of the clamp (the clamped pass is precomputed)

## Bindings (mark -> named export array), contract `sca2-workbench/capture@1.1`

*Browser* = computed on the page, and labelled so on screen (italic in the inspector).

| Tab | Mark | Export field |
|---|---|---|
| all | prompt parts (pills, bands, gaps, minimap) | run `segments` (@1.1); @1 fallback: one labelled span |
| all | answer card | run `readout.probs`, `readout.probs_clamped`, `readout.margin`; pair `d_probs`, `d_margin` |
| all | status line, checks pop-up | run `conservation.*`; pair `conservation.*`; *browser* re-sum `clientCheck` |
| all | inspector sizes, gold change | run `head_norm`/`mlp_norm`/`resid_norm`/`attn_norm`; pair `d_*_norm` |
| all | inspector push on the margin + change | run `head_attr`, `mlp_attr` (`_clamped`); pair `d_head_attr`, `d_mlp_attr` (`_clamped`); *browser* for @1 |
| all | top-16 covered, Q-III count, margin-if-read-off | run `attn_topk_mass`, `q3_count`, `running_margin`; their change is *browser* |
| all | weights moved | pair `d_weight_head`, `d_weight_mlp` |
| C | ladder A, B | run `head_attr`, `mlp_attr`, `readout.embed_attr` (or `_clamped`) |
| C | ladder B − A | pair `d_head_attr`, `d_mlp_attr`, `d_embed_attr` (or `_clamped`) |
| C | check line | *browser* sum of cells vs run `readout.margin` / pair `d_margin(_clamped)` |
| C | margin by layer | run `running_margin(_clamped)` |
| C | prompt shading, pill totals | run `attn_topk_idx/_val` at t*; B − A and totals *browser* |
| C | largest changes table | pair `d_head_attr`, `d_mlp_attr` |
| B | maps A, B; change map | run `resid_norm`/`attn_norm`/`mlp_norm`; pair `d_resid_norm`/`d_attn_norm`/`d_mlp_norm` |
| B | margin chart; DLA chart; nine-head bars | run `running_margin(_clamped)`; run `attn_attr`, `mlp_attr`; run `head_norm` + pair `d_head_norm` |
| A | blocks, answer column colour, Q-III | as before: `resid_norm`, `head_norm`, `mlp_norm` (Δ: `d_*_norm`); `head_attr`/`mlp_attr`; `q3_count` |
| A | arcs; Σ arc to a collapsed gap | run `attn_topk_idx/_val`; Σ is a *browser* sum |
| A | margin line + end numbers; inset | run `running_margin(_clamped)` |
| A | largest-changes list; prompt map | pair `d_head_norm` at t*; run `resid_norm` (or pair `d_resid_norm`) |
| landing | hero; heatmap; probabilities; change by layer | run `running_margin`; `resid_norm` + `segments`; `readout.probs(_clamped)`; pair `d_attn_attr`, `d_mlp_attr`, `d_embed_attr` |
| landing | question text | run `tokens` of the `question` segment |
