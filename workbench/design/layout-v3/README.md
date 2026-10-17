# layout-v3 · decluttered workbench (card t_b31e4996)

Read in order: INVENTORY.md (v2 at rest, verdict per object) → SYSTEM.md (grid, frame, disclosure, type, colour) → DECISION.md.

Run: `../layout-v2/serve.sh` (serves workbench/ on :5181), then open
`http://127.0.0.1:5181/design/layout-v3/v3.html?view=ladder` — views: landing, landing-s2, ladder (`&pin=23,0`, `&face=a|b|d`, `&fail=1`),
matrix (`&qty=resid|attn|mlp`), object, scale-ladder, scale-picker, scale-cohort. `&item=bank_USA_00023ac74dac` switches the item; `&count=0` hides the count overlay.

Shots: `cp shoot.mjs $TMPDIR/pp/ && (cd $TMPDIR/pp && node shoot.mjs <abs>/shots)` → shots/*-{1440,1700}.png + report.txt (exit 0 = no errors, every view ≤ 9 objects, self-test passed).

Bindings: v3.js reuses `loadBundle` from ../layout-v2/common.js. Frame pill: run/pair `conservation`; answer strip: `readout.margin`, `readout.probs`, pair `d_margin`;
ladder: `head_attr`, `mlp_attr`, `readout.embed_attr` / pair `d_head_attr`, `d_mlp_attr`, `d_embed_attr`; margin column: `running_margin`; drawer: `head_attr`, `head_norm`, `attn_topk_mass`, `attn_topk_idx/_val`, pair `d_head_attr`, `d_head_norm`, `d_weight_head`;
matrix: `resid_norm|attn_norm|mlp_norm` / pair `d_*`; object + minimap: `resid_norm`, `segments`; landing: `running_margin`, pair `d_attn_attr + d_mlp_attr`. Scale views: seeded `fake()`, badged.
