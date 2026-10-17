# Workbench v2 port: notes (card t_0fc4d4f8)

Routes: `/` landing · `?tab=c` ladder (default, "Open the workbench") · `?tab=b` matrix · `?tab=a` 3D object.
Shared URL keys: `a`, `b`, `item`, `learn`. Per-tab keys: C `clamp, shade, sel=l,h (h=-1 MLP; sel=none), q` ·
B `qty, fold, pin=l,t, hl` · A `view=single|side|delta, single, hscale, color, clamp, sel=l,h,t, cam, q, open=all, fly`.
Legacy keys `pair=a|b` and `view=side&right=delta` are still read.

## Acceptance artefacts (this folder)
- `tsc.txt`: `npx tsc --noEmit -p .` -> exit 0.
- `sweep.json` (`sweep.mjs`): 16 pairs x {landing, c, b, a} = 64 loads, 0 failures, 0 console errors.
- `leak.json`: the skill's `webgl_leak_check.mjs` on tab A, 36 steps incl. tab switches (`click:[data-tab=c|b|a]`), views, clamp, camera preset, "show all": pass true.
  CAVEAT: that script reads memory 150 ms after the last step, which can catch a rebuild before its first render (its after = 0/0).
  So `leak_settled.json` is the same script with a 4 s settle before the final read (`webgl_leak_check_settled.mjs`, one added line): pass true.
  `leak_probe.txt` (`probe.mjs`) reads memory 2.5 s after each step: every return to a state gives the same counts (74 geometries / 130 textures for A|B), and leaving tab A frees all (0/0).
- Screenshots: `{c,b,a-single,a-side,a-delta,c-bank,b-bank,a-bank,popup,popup-checks,landing}-{1700,1440}.png`, `landing-full-1700.png`; `shots-*.json` hold each URL and its console errors.

## COPY.md strings declined or changed (with reason)
- L01 kept as is (PM ruling: wait for Augusto on Q1).
- L04 "toward one country's answers" -> "toward one country's preferences": PM ruling, the adapter was trained on synthetic GPS-signed scenarios, not survey answers. L23/P11/G13/G16 use the PM's gloss; G12 says "binary".
- L04 first clause templated: bank items say "a question about an everyday scenario" (K24).
- L09 "A · original / B · fine-tuned" only when B = A + adapter; otherwise short registry labels (K11). Same for C06/C11.
- L11 story(): PM K2 template, "ends X higher/lower than A's".
- S12 extended: @1.1 exports a SIGNED B − A of the DLA (`d_head_attr` etc.), a third kind of change the copy did not foresee. Gold = ‖B−A‖ (export); upright cream = signed B − A from the export; italic = computed on the page. The footer names all three.
- S16 rows read "0.38 · #122 “4”" (not "token 122"): the two-column list in a 360 px panel truncated the token text.
- S19 applied as a relabel of the exported labels ("turn opens" -> "message starts", "system prompt" -> "system instructions"); readout reads "answer position t*=…".
- C20 says "square-root scale … nothing is clipped" (K20 left to Augusto; stated because the card asks for numeric legends).
- O12 3D gap label is two lines "⋯ label" / "N tokens": the strip holds ~16 rotated characters; "collapsed" is carried by ⋯, the dashed gap line, the minimap and the Σ-arc label.
- P06 adds two rows (browser re-sum; the pair's B − A gate) behind "show all six checks".
- P09 says the parts come from the export (K12 resolved).
- COPY §4.3 colour collision resolved: A = light grey, B = teal for lines and bars; blue/orange only mean the sign of a push.

## Weak spots fixed (DECISION.md + PM audit)
- Segments from `manifest.segments` only (heuristic deleted); @1 files fall back to one labelled span.
- B − A of DLA from pair `d_head_attr/d_mlp_attr/d_embed_attr(_clamped)`, `d_margin(_clamped)`; @1 fallback computed and labelled.
- A: arcs to collapsed tokens summed into one arc per gap, labelled "Σ w → part (collapsed)", also listed in the inspector.
- Colour keys with numbers on C (DLA ±max, no clipping; attention shading) and B (both ramps; p99 clip value and the max printed).
- B: tick per layer; labels every 5/10, the last, and the hovered/pinned layer (gold); maps + charts fit 1000 px; DLA chart labels L0…L29.
- A: presets fit the whole collapsed object by projection (no left crop); right layer labels clear of the answer column; gap labels inside the token strip; margin line numbers at both ends + flat A/B inset chart.
- C: fixed column widths in the inspector; left column filled by the "largest changes" table; default pin = largest |ΔDLA| head, labelled as a starting point.
- PM live fixes kept: `disposeScene` (textures) + `renderLists.dispose()` on every rebuild, context lost/restored with `#glLost`, synced hover + one tooltip, `window.__renderer`, `window.__ready`. One renderer/canvas for the app; leaving tab A disposes all scenes.

## Open issues
- `leak.json` alone is weak evidence (see caveat); use the settled run/probe.
- Tab A tool row wraps to two lines at 1440 px; the pair select truncates long labels.
- Landing thumbnails are this folder's 1700 px screenshots of the default pair.
- K3, K16, K20, Q1, Q2 still with Augusto.
