# PROGRESS (card t_b31e4996)

- [x] 1 · INVENTORY.md — v2 at rest: landing 9, ladder 20, matrix 18, object 17.
- [x] 2 · SYSTEM.md — 1240 px frame, 64 px minimum margins, 12 cols / 32 px gutters, 4 type sizes, 8 colours with one meaning each, 4 disclosure layers.
- [x] 5 · DECISION.md — draft recommendation (one face per object, B − A default, nothing pinned at rest).
- [x] 3 · Mockups — `v3.html` + `v3.js` + `v3.css` (served by ../layout-v2/serve.sh), bound to the real exports for smol_inst | smol_inst_usa_e3 · wvs_Q81. Landing 5, section 5, ladder 5, pinned 6, matrix 5, object 7 (DOM counts in shots/report.txt). Interaction self-test passes (pin, Esc, face switch).
- [x] 4 · Scale — scale-ladder (32 × 33, 1056 cells, ~15/18 px at 1440/1700), scale-picker (43 models, two slots), scale-cohort (42 × 32). All badged "illustration · not data".
- [x] 5 · DECISION.md final.
- Not done: answer-card pop-over, learn-more modal, pinned states of matrix/object; none for the bank item: ladder-bank and matrix-bank shots exist.
- Final verification: `cp shoot.mjs $TMPDIR/pp/ && (cd $TMPDIR/pp && node shoot.mjs <abs>/shots > <abs>/shots/report.txt)` → exit 0; 24 shots (12 views × 2 sizes), no console errors, all ≤ 9 objects, self-test {rest, pinned, unpinned, faceA} all true. Bank item: long option labels truncated in the strip (full text in title), prompt column scrolls with a fade.
