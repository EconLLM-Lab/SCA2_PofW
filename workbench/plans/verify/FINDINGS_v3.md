# Verifier findings — workbench v3 port (t_9799f1a1)

Independent falsification. Route: `deepseek/deepseek-v4.1-flash` on `openrouter` (the card's pin).
Artifact root: `workbench/` at the current worktree HEAD
(`/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.worktrees/adapter-brain-vizualization`).
Fence: read-only except `$TMPDIR` and `plans/verify/`. `data/` was not read. No git.

Own tools (no viewer code, no producer script, no `common.ts` decoding imported):

- `plans/verify/compare_v3.py` + `plans/verify/reader.py` — my own reader over `workbench/exports`
  (manifest offsets + `struct`, per `spec/export_contract.md`), compared against raw strings and raw
  SVG fills the browser showed. 1314 checks, 0 failures, exit 0.
- `$TMPDIR/pp/v3obs.mjs` → `v3obs.json` (observations), `$TMPDIR/pp/probe_overlap.mjs` →
  `overlap.json`, `$TMPDIR/pp/probe_obj3.mjs`, `$TMPDIR/pp/probe_fail.mjs`, `$TMPDIR/pp/copysweep.mjs`.
- Producer scripts re-run **verbatim** (copied into `$TMPDIR/pp`, which holds `puppeteer-core`):
  `screens/v3/sweep.mjs`, `screens/v2/leak_end_on_a.mjs`, `screens/v2/webgl_leak_check.mjs`.

The Vite dev server was **down** when I started (the producer's process had exited). I restarted the
documented one (`npx vite --host 127.0.0.1 --port 5178 --strictPort` from `workbench/viewer`) and left
it running; no source file was touched.

---

## Check 1 — bindings (own reader over the served exports) → PASS

```
$ cd <repo root> && env -u PYTHONPATH python3 workbench/plans/verify/compare_v3.py
reader: L=30 H=9 T=152 ro=151 | A margin 1.058629  B margin 2.920371  d_margin 1.861742
  ladder fills face d: 301 cells, 0 mismatched (vmax 0.8939)
  ladder fills face a: 301 cells, 0 mismatched (vmax 0.7006)
  ladder fills face b: 301 cells, 0 mismatched (vmax 0.4034)
  matrix attn  tooltips parsed: 54  distinct cells: 54
  matrix resid tooltips parsed: 4  distinct cells: 4
  matrix mlp   tooltips parsed: 4  distinct cells: 4
  object a_delta numbers parsed from tooltips: 55  (hovers: 16)
  object a_side  numbers parsed from tooltips: 78  (hovers: 16)
=== checks: 1314   failures: 0 ===
EXIT=0
```

**Ladder (tab c).** Default face is `B − A` (`face_default = "d"`, `tab-c.ts:45`). Six hovers (heads
`17,3`; `4,0`; `0,8`; `29,2`; `12,4` and MLP `25`) each bound 3 numbers to `head_attr`/`mlp_attr` of A
and B and `d_head_attr`/`d_mlp_attr` of the pair, e.g.

```
head 3 · layer 17   A −0.01169   B −0.01236   B − A −6.639e-4 (pair export)
```

**The three faces are bound by the drawn marks, not only by tooltips.** Every `rect.cell` fill was
re-derived from my own arrays as `mix("#3a3a3e", blue/orange, sqrt(min(1,|v|/vmax)))` with `vmax`
recomputed over the drawn grid (embedding row included): **903/903 cells match within ±1/255** across
the default `B − A` face, the A face and the B face. The footer's `±` value is that same `vmax`
(`±0.89` / `±0.70` / `±0.40`). The re-sum line binds on every face:

| face | drawn re-sum | my Σ | drawn target | my target |
|---|---|---|---|---|
| B − A | 1.8617 | 1.8617 | 1.8617 | `d_margin` = 1.861742 |
| A | 1.0586 | 1.0586 | 1.0586 | A `readout.margin` = 1.058629 |
| B | 2.9204 | 2.9204 | 2.9204 | B `readout.margin` = 2.920371 |

**The drawer (pin `sel=17,3`).** All ten numbers equal my reader: `Write size ‖o‖` 2.476 / 2.498 /
`‖Δ‖ 0.1513` (`head_norm` A,B and `d_head_norm`), `Push (DLA)` −0.01169 / −0.01236 / −6.64e-4
(`head_attr` and `d_head_attr`, upright = from the pair export), `Top-16 coverage` 0.9999 / 0.9999 /
+1.29e-5 (A,B from `attn_topk_mass`, the change a browser difference shown italic).

**Matrix (tab b).** Default quantity is **`attn`** and the default face is `d`
(`qty_on = "attn"`, `face_on = "d"`). 54 distinct cells bound on the default quantity (A `attn_norm`,
B `attn_norm`, `d_attn_norm` — all three per cell), plus 4 on `resid` and 4 on `mlp`; the tooltip names
its own `(layer, token)`, so nothing is assumed. Footer clip value and max re-derived from the pair
tensor: `0 → 22.1 (99th percentile…) · max 49.5 · pair d_attn_norm` (my p99 22.11, my max 49.47;
`resid` and `mlp` footers likewise). Drawer at `pin=15,89`: `Attention write ‖a‖` 43.62 / 42.39 /
`‖Δ‖ 7.288` and all nine per-head `d_head_norm` rows.

**Object (tab a).** Default view is `A | ‖B − A‖` (`view_on = "delta"`, labels
`A · SmolLM2-135M-Instruct` and `‖B − A‖ · the change, B = …`). 55 numbers bound in the delta view and
78 in the `A | B` view: `||o^l_{h,t}||` per panel against that panel's `head_norm`, `||o_B - o_A||`
against `d_head_norm`, `DLA to margin` against `head_attr`, and the top-16 row's first weight and key
index against `attn_topk_val` / `attn_topk_idx`. The pin drawer (`sel=23,0,57`) binds `Write size ‖o‖`
13.90 / 17.63 / `‖Δ‖ 4.600` to `head_norm` and `d_head_norm`.

**Cohort (tab k). — no marks exist, by design (request note, not a finding).** See "Request notes".

---

## Check 2 — the never-hide rules → PASS

**Banner.** With `?fail=dla_gap` on tabs c, b and a the banner is present, visible and red
(`role="alert"`, colour `rgb(255,214,211)` on `rgb(42,19,18)`, border `rgb(255,95,86)`), carries **no
button** (it cannot be dismissed) and reads:

```
✗ 1 check failed · A dla_gap = 0.031 ≥ 0.01 (simulated with ?fail · not data). The parts below do not
add up for A; do not read them as measurements until the export is fixed.
```

That is the check, its value, its threshold and the word "simulated" (`common.ts:202`, `main.ts:100`).

**No green ✓ for the affected numbers.** A DOM walk over every visible leaf element found
**0 elements containing "✓"** on c, b and a with `?fail` (2 visible marks, both "✗"). The status pill
reads `✗ 1 of 7`; the ladder's re-sum line flips to `class="sumline bad"` and repeats the check; the
ladder gets `tainted`, and the face buttons read `a:bad`, `b`, `d:bad` — the failing check is A's, so
A's face and the `B − A` face go red and B's face does not (`common.ts:201`). The status button's
`title` (a tooltip) lists all seven checks with `✓`/`✗`, and the affected one reads `✗`.

**Re-sum line, sign convention, clip value at rest.** Ladder footer, always drawn: `orange: toward “4”
(None at all) · blue: toward “1” (A great deal) · ±0.89, square-root scale` and the re-sum line. Matrix
footer, always drawn: the p99 clip and the max (both re-derived above). Object scene bar: the encoding
key.

**Clamped run says so in the frame.** Ladder with `clamp=1`: `#clampchip` visible ("clamped run"),
hidden again at rest; the re-sum line switches to `d_margin_clamped` (bound numerically). Object tab,
`view=side`, `clamp=1`: same chip. One deviation, see nit 1.

**Cohort shows no unbadged placeholder data.** The tab's only figure is `<img
src="/screens/v3/cohort-illustration.png">` (naturalWidth 560, so it loads) carrying the badge
`illustration · not data`, with a frame badge `no data yet · illustration` (`tab-k.ts:31`, `main.ts:87`),
and the body text is prose plus the honest count ("`index.json` lists 2 adapters"). No numbers.

---

## Check 3 — the object budget → PASS, and my count equals the producer's

Counted myself as visible `[data-obj]` elements at rest at 1600×950 (frame elements counted as a reader
sees them: `title-tabs`, `pickers`, `status` = the approved 3):

| tab | my count | objects | producer `report.txt` |
|---|---|---|---|
| Ladder | **7** | title-tabs, status, pickers, answer, prompt, ladder, margin | 7 |
| Matrix | **6** | title-tabs, status, pickers, answer, map, margin | 6 |
| Object | **9** | title-tabs, status, pickers, answer, scenebar, sceneA, sceneB, inset, minimap | 9 |
| Cohort | **6** | title-tabs, status, pickers, answer, cohort-empty, illustration | 6 |
| landing (first screen) | **5** | nav, h1, lede, cta, hero | 5 |

Every count is ≤ 9 and matches the producer's line for line. The only visible elements without a
`data-obj` are layout wrappers (`#work`, `.a-col`, `#stage`), not things a reader sees; every visible
`data-obj` on the pinned views is still an at-rest object (drawer excepted).

---

## Check 4 — the drawer covers nothing → PASS

`$TMPDIR/pp/probe_overlap.mjs` pins on four scenarios and, after a **2.5 s settle**, intersects the
drawer's bounding box with every visible at-rest object:

```
LADDER pin(17,3)                 overlaps: []   chartW 220 -> 220
MATRIX pin(canvas)               overlaps: []   chartW 200 -> 200
OBJECT pin via URL sel=23,0,57   overlaps: []   (9 at-rest objects, all visible)
OBJECT pin by click              overlaps: []   (9 at-rest objects, all visible)
```

The margin-by-layer chart keeps its width on both tabs, and nothing disappears: the pinned views list
the same objects as the at-rest views plus the drawer. `compare_v3.py` re-checks these as
`overlap-LADDER/MATRIX/OBJECT` (0 failures).

---

## Check 5 — robustness → PASS

```
$ cd workbench/viewer && npx tsc --noEmit
TSC_EXIT=0

$ cd $TMPDIR/pp && node leak_end_on_a.mjs
{"steps":80,"start":{"geometries":10,"textures":122,"lost":false},
 "end":{"geometries":10,"textures":122,"lost":false},"flat":true,"page_errors":[]}
LEAK_END_EXIT=0

$ cd $TMPDIR/pp && node webgl_leak_check.mjs "http://127.0.0.1:5178/?tab=a" 42 \
    "hscale,color,click:[data-tab=k],click:[data-tab=c],click:[data-tab=b],click:[data-tab=a]"
{"url":"http://127.0.0.1:5178/?tab=a","rebuilds":42,"before":{"geometries":10,"textures":122},
 "after":{"geometries":10,"textures":122},"context_lost":false,"page_errors":[],"pass":true}
WEBGL_EXIT=0

$ cd $TMPDIR/pp && node sweep3.mjs <abs>/workbench/exports/index.json
{"pairs":16,"loads":80,"failures":0,"console_errors":0,"bad":[],"pass":true}
SWEEP_EXIT=0
```

The leak run is 42 rebuilds (≥ 30) that switch tabs across **all four** tabs and start and end on tab a
(the only view with a WebGL context); flat at 10 geometries / 122 textures. The sweep covers the 16
pairs of `index.json` × 5 surfaces (landing, c, b, a, k) = 80 loads, 0 console errors.

---

## Check 6 — copy → PASS with one request note

**Eq. 6 is cited to the SCA2 paper, not to Paper B.** `common.ts:227`, `common.ts:258` and
`landing.ts:46` all read "Eq. 6 of the SCA2 paper (arXiv:2610.06562)". No string cites Eq. 6 to Paper B;
the only "Paper B" on screen is the landing footer ("Paper A: arXiv:2610.06562 … Paper B extends the
method to a 42-country cohort; this workbench is its companion").

**No claim that training used survey answers.** The only two sentences that mention survey responses
are negations: "Not survey responses." (`common.ts:238`) and "It was not trained on survey responses."
(`common.ts:280`); the training data is named as made-up scenarios plus the GPS direction. A grep for
"trained on survey / training used survey / trained with survey" over `viewer/src` returns nothing.

**"logit" — 0 occurrences in the visible text of all four tabs at rest** (`copysweep.mjs`: ladder,
matrix, object, cohort each `logitCount: 0`; the only DOM hit is the check-key name
`hf64_logits_max_rel_gap` inside the status button's `title`, a tooltip). It survives in the visible
text of the **landing** (3: "multinomial logit", "Direct logit attribution", "logit index") and of the
**eq6 / terms pop-ups** (2 and 4). Every one of those strings is prescribed by the copy deck the card
names (`COPY.md` L19 "multinomial logit", L21 "Direct logit attribution … logit index", G02 glossary
"logit" whose home the deck itself gives as "tooltip, pop-up (P01)", P05/G09, P06). See request note 2.

---

## Nits and observations (no block)

1. **Object tab, `view=delta`, `clamp=1`: the frame chip stays hidden although the A scene does draw the
   clamped run.** `tab-a.ts:117` is `ctx.mode(clamp && view !== "delta")`, while `tab-a.ts:130` passes
   `delta ? false : clamp` to the A panel — so in the delta view the A scene is clamped and the chip is
   suppressed. The reader is still told at rest: the scene bar's key ends "· clamped run"
   (`tab-a.ts:164`, observed). Rule 4's letter ("the frame shows it") is met by the scene bar rather
   than by the frame's chip on this one view; worth a PM ruling, not a defect in the numbers.
2. **Pinning on the object tab re-flows slowly.** Measured 900 ms after a click, `#sceneA`/`#sceneB`
   still carried their pre-pin inline `left`/`width` (a 340 × 539 px overlap with the drawer); by
   1200–2500 ms they are correct (0 overlap, buffer 868 × 539). Cosmetic transient on a swiftshader
   headless run; the settled state is what check 4 measures.
3. The status button's tooltip lists the six unaffected checks with `✓` while the banner is red. The
   affected check reads `✗` there, so the marks are consistent; the card's "DOM search" is about
   visible text, where there are none.
4. Interpretation risk on check 3: I read the approved rule's "title + tabs" as **one** frame item
   (card `t_3dbac0bc`, item 4). Read as two, the object tab would be 10. The approved wording is
   explicit, so I counted 3 frame items.

## Request notes (not findings)

1. **Check 1's "at least 3 marks in each of the 4 tabs" cannot hold on the Cohort tab.** `index.json`
   holds 16 pairs; the largest number of pairs sharing a base and an item is **2** (4 pairs of 1, 6 of
   2 — computed from the index), and `tab-k.ts:12,23` requires ≥ 3 adapters before it draws the real
   map. The parent card (`t_0729b553`, item 3) mandates exactly this empty state for today's exports,
   so the criterion is unsatisfiable by design. I verified the tab's own requirements instead (honest
   empty state, one badged illustration, no data).
2. **Check 6's "no 'logit' outside tooltips" conflicts with `COPY.md`**, which the same card names as
   the copy rule and which puts "logit" in the landing's §2/§3 text and in the glossary/eq6 pop-ups.
   As shipped, no workbench tab says "logit" at rest; only the landing and the pop-ups do, in the
   deck's own wording. Narrowing the rule to "at rest, on the tabs" would make it hold exactly.
