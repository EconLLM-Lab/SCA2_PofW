# Verifier findings — workbench v2 (t_ebb2173c)

Independent falsification. Route: deepseek/deepseek-v4.1-flash on openrouter (card pin).
Artifact root: `workbench/`. Fence: read-only except `plans/verify/` and `$TMPDIR`.
Scripts: `plans/verify/reader.py` (own reader: manifest offsets + struct, no viewer/common.js
decoding), `check1.py`, `check1d.py`, `check1f.py`, `compare_bindings.py`, `recompute.py` (PM's).

---

## Check 1 — exporter@1.1, segments, d_*_attr  → NO BLOCKER

**1.1 Tests, at the reported count.** PASS.
```
$ cd <repo root> && env -u PYTHONPATH uv run --project workbench pytest workbench/tests -q
38 passed, 1 warning in 12.57s
EXIT=0
```
Reported count is `AUDIT.md:324` "38 passed in 6.95s" (baseline `AUDIT.md:320` "24 passed").
Re-run: 38 passed, exit 0. Matches.

**1.2 `segments` covers `[0, T)` exactly once, in order, every run.** PASS.
```
$ env -u PYTHONPATH python3 plans/verify/check1.py
1b segments coverage failures: 0
1b distinct kind sequences (count):
  22  ('template','system','template','instruction','question','instruction','options',
       'instruction','answer_cue','template','readout')
EXIT1=0
```
All 22 runs carry the 11-segment list `spec/export_contract.md:44` mandates, same order, no gap,
no overlap, last `b` == T, and `len(tokens) == T` on each.

**1.3 Three items decoded; kinds are true.** PASS. `check1.py` 1c output, cross-checked against the
source records (read-only, not `data/`):

| item | segment | tokens | truth |
|---|---|---|---|
| `bank_USA_00023ac74dac` | `question` [55,147) | "Question:\nA fellow student tutored me for free before a critical exam, …" | = `D_syn_USA.jsonl` `prompt` verbatim; span 92 tokens = `spec/export_contract.md:45` |
| " | `options` [158,283) | "1: I'll set aside time to carefully review their work this evening. … 2: I'll let them know I can only do a quick scan tomorrow morning. …" | = `chosen`(1) + `rejected`(2); `chosen_first = sha256(triplet_id)%2==0 = True` (`items.py:134-136`) |
| `bank_USA_7232414df567` | `options` [110,207) | "1: I'll pass on the high-paying project. …" (the *rejected* text) | hash gives `chosen_first=False`, so option 1 = rejected — follows the data, not a hard-coded order |
| `wvs_Q57` | `question` [55,85) / `options` [96,113) | "…most people can be trusted or …" / "1: Most people can be trusted\n2: Need to be very careful" | question is the stem, options are the option lines |

**1.4 Σ d_* + d_embed = d_margin, and d_head_attr = B.head_attr − A.head_attr.** PASS.
```
$ env -u PYTHONPATH python3 plans/verify/check1d.py
pairs: 16
  worst g32    = 7.431157e-08   (Σ stored float32 d_head/d_mlp + float64 d_embed − d_margin)
  worst g32c   = 7.237936e-08   (same, clamped)
  worst attn   = 3.696914e-08   (|Σ_h d_head_attr − d_attn_attr|)
  worst dh     = 1.192093e-07   (|d_head_attr − f32(f32(B)−f32(A))|, ≈1 ulp of f32)
  worst dm     = 5.960464e-08   (same for d_mlp_attr)
fails: []
```
All < 1e-6. The worst float32 gate, 7.43e-8, reproduces `spec/export_contract.md:120`
("worst value is 7.4e-8") from the files, independently.
`d_head_attr` is a float64 difference stored as float32, so a ≤1-ulp disagreement with the
difference of the two float32 run arrays is expected and is what `worst dh` shows.

**1.5 Margins unchanged vs the pre-@1.1 export.** PASS. The engineer's copy is
`$TMPDIR/exports_old/` (38 json = 16 pairs + 22 runs), timestamped 2026-10-16 22:22.
```
$ env -u PYTHONPATH python3 plans/verify/check1f.py
old files: 38
arrays compared byte-for-byte: 536
missing files/arrays: []
scalar mismatches: 0
array mismatches: 0
worst margin difference over all old/new files: 0.000e+00
new-only files (added after the re-export): []
```
i.e. every `readout` scalar (margin, margin_clamped, probs, embed_attr, rho_final), every
`d_margin`/`d_probs`, and **536 arrays are byte-identical** across the re-export — which is
`spec/export_contract.md:136` ("every @1 array is byte-identical and every margin is
bit-identical") checked against the files.

**1.6 Recompute one run through `llama_capture`.** PASS (3 runs, not 1).
```
$ cd workbench && env -u PYTHONPATH uv run --project . python plans/verify/recompute.py
smol_base        bank_USA_00023ac74dac  recomputed 0.732743594800191 stored 0.732743594800191 diff=0.00e+00
                 margin_c 0.996084042750 vs 0.996084042750  eq6=1.53e-07  pass=True resid=4.9e-12 dla=1.8e-14 hf64=5.6e-15
                 old(@1) margin 0.732743594800191 diff=0.00e+00
smol_inst        wvs_Q57                 recomputed 0.755343095951627 stored 0.755343095951627 diff=0.00e+00
                 old(@1) margin 0.755343095951627 diff=0.00e+00
smol_inst_usa_e1 bank_USA_00023ac74dac  recomputed 1.133295023729218 stored 1.133295023729218 diff=0.00e+00
                 old(@1) margin 1.133295023729218 diff=0.00e+00
EXIT=0
```
Bit-identical to both the shipped run files and the @1 copies.

**Nit, not a finding:** `bank.py` (`build_user_prompt`, "the DPO training prompt") is dead code for
the export: `items.py:76-87,140` builds bank items with `survey_prompt_v1`. Harmless, but two
prompt builders in the tree invite a mis-read of what the bank item actually is.

---

## Check 2 — viewer bindings (own reader over the served exports; no viewer code imported) → NO BLOCKER

Scripts: `$TMPDIR/pp/bindings.mjs` (tabs C, B, A), `$TMPDIR/pp/bindings2.mjs` (pinned head at t*,
the "largest changes" list, the attention card). Run against `http://127.0.0.1:5178` (the viewer's own
Vite dev server, which serves `workbench/exports` at `/exports`). Driver: Chrome via puppeteer-core,
headless, `--use-angle=swiftshader`.

**2.1 Tab C, the ladder.** URL `?tab=c&a=smol_inst&b=smol_inst_usa_e3&item=wvs_Q81&sel=none`;
three marks in each of the three panels, read from the SVG `<title>` of the `rect.cell`
(`viewer/src/tab-c.ts:76`) and compared with `head_attr`, `mlp_attr`, `d_head_attr`
(`run__smol_inst__wvs_Q81`, `run__smol_inst_usa_e3__wvs_Q81`, `pair__...`):

```
ok C ladder g0 head 3 l17: shown=−0.01169 mine=−0.01169   (panel A, head_attr)
ok C ladder g1 head 3 l17: shown=−0.01236 mine=−0.01236   (panel B)
ok C ladder g2 head 3 l17: shown=−6.639e-4 mine=−6.639e-4 (panel B − A, d_head_attr)
ok C ladder g0 head 0 l4 : shown=−0.006928 mine=−0.006928
ok C ladder g1 head 0 l4 : shown=−0.006726 mine=−0.006726
ok C ladder g2 head 0 l4 : shown=+2.021e-4 mine=+2.021e-4
ok C ladder g0 MLP  l25  : shown=−0.1569  mine=−0.1569
ok C ladder g1 MLP  l25  : shown=−0.08833 mine=−0.08833
ok C ladder g2 MLP  l25  : shown=+0.06857 mine=+0.06857
ok C ladder cells count  : shown=903 mine=903
ok C Δ cell cites the pair export: shown=true (title says “from the pair export (d_head_attr, d_mlp_attr)”)
ok C A/B cell does not: shown=false
```
The three drawn per-panel balances are the sums of **my own** float32 arrays plus the embedding scalar:
```
ok C ladder drawn panel-A sum: shown=1.059 mine=1.059   (Σ head_attr + mlp_attr + embed_A)
ok C ladder drawn panel-B sum: shown=2.920 mine=2.920
ok C ladder drawn panel-D sum: shown=1.862 mine=1.862   (Σ d_head_attr + d_mlp_attr + d_embed)
```
(1.862 is `d_margin`; cf. `exports/index.json` for this pair.)

**2.2 Tab B, the matrix.** Cell read back through the inspector card, which the hover handler fills
(`viewer/src/tab-b.ts:101-110`); layer and token are taken from the card itself, not assumed:
```
ok B matrix map0 A ‖h‖  (l20,t26): shown=254.5 mine=254.5   (resid_norm)
ok B matrix map0 B ‖h‖  (l20,t26): shown=251.7 mine=251.7
ok B matrix map0 Δ ‖h_B−h_A‖ (l20,t26): shown=14.82 mine=14.82   (d_resid_norm)
ok B matrix map0 A/B/Δ   (l14,t26): shown=174.1/171.9/11.53 mine=174.1/171.9/11.53
```
The third planned hover (the Δ map) landed on no cell — **my** coordinate, not a page fault: the page
stayed clean (`page_errors: []`). The Δ side of the matrix is covered instead by the attention card
below, which draws `d_attn_norm` and all nine `d_head_norm` rows for a pinned cell
(`?tab=b&qty=attn&pin=25,30`):
```
ok B card A ‖a‖: 73.88   B ‖a‖: 71.85   Δ ‖a_B−a_A‖: 7.287
ok B card head h0..h8 Δ ‖o_B−o_A‖: 1.05, 0.614, 0.831, 2.57, 3.47, 2.97, 3.72, 1.75, 3.54  (all nine match)
```

**2.3 Tab A, the 3D object (head slivers).** Hovered a grid of points and parsed the tooltip
(`#tip`, filled by `viewer/src/tab-a.ts:290-305`); the hit's layer/head/token come from the tooltip's
first line, so nothing is assumed:
```
side view (A next to B):  ok A ‖o‖ 8.027/6.744/8.072/8.936, B ‖o‖ 8.665/6.797/7.626/8.743  (head_norm, 4 seams)
delta view (A + ‖B − A‖): ok ‖o_B−o_A‖ 1.259/0.5534/1.239/0.5431, A ‖o‖ 8.027/6.744/8.072/8.936
```
Both views bind, at four different (layer, head, token) marks each — more than the three asked for.

**2.4 Tab A, the pinned head at t\*.** `?tab=a&view=side&sel=29,2,151`; the inspector card
(`common.ts:151 inspectorHTML`) must tie A, B and Δ for the same head:
```
ok A inspector heading: Head 2 · layer 29        ok token line is t*: true
ok A ‖o‖ 56.50   B ‖o‖ 67.91   Δ ‖o_B−o_A‖ 23.20 (gold, from d_head_norm)
ok A DLA −5.952e-5  B DLA 0.04582  Δ DLA +0.0459  (signed, from d_head_attr; 0.04582−(−5.952e-5)=0.04588→+0.0459)
ok A covered 0.8935 / 0.9443 (attn_topk_mass)
ok A bigd rows 0-5: “layer 23 · head 0” 26.6, “29 · 2” 23.2, “24 · 4” 21.1, “23 · 2” 16.1, “29 · 1” 15.6, “29 · 0” 14.9
   = the top six of d_head_norm[·,·,t*] from my reader, in my order
```
`page_errors: []` throughout both scripts.

**Nit (not a finding):** in the first run the "largest changes" numbers all read `26.6` because my own
selector grabbed the first `.num` in the card (`tab-a.ts:172` emits the row, the bar and the number as
three siblings). With the correct selector each row binds. No app defect.

---

## Check 3 — no silent drops in tab A → PASS (one nit)

Chosen head: the (l,h) whose stored top-16 mass at t\* lands most on a **collapsed** segment, found
from my own reader over `attn_topk_idx/attn_topk_val` → layer 18, head 8, Σ = 1.00, all of it on
tokens [0,3) (`system turn opens`).

```
$ ?tab=a&a=smol_inst&b=smol_inst_usa_e3&item=wvs_Q81&sel=18,8,151
#insp .note = "Attention to collapsed parts (one Σ arc each, model A): 4 parts Σ 1.00"
ok A collapsed Σ value: shown=1.00 mine=1.00
$ ?tab=c&...&sel=18,8
#ptext pills = ["‹system message starts · 3 tokens · total attention 1.00›", "‹system instructions · 16 tokens›", …]
ok C collapsed pills declare total attention: ["‹system message starts · 3 tokens · total attention 1.00›"]
```
So the collapsed segment that holds the head's top-16 key is declared on screen, in both tabs, and the
number equals my own sum of the stored weights (1.00 = 1.00 + 0.00 + 0.00 over the three collapsed
segments the key lands in). In 3D the same value is drawn as one arc to the gap with an on-canvas
sprite `Σ 1.00 → 4 parts (collapsed)` (`viewer/src/scene.ts:310-315`).

**Nit (fix-later):** adjacent collapsed segments are merged into one gap and the gap is relabelled
`${n} parts` (`viewer/src/scene.ts:89`), so the 3D arc and the inspector note say "4 parts" where the
ladder pill names the part ("system message starts"). The number is right; naming the merged run
("system + persona, 4 parts") would read better. Not a drop, not a blocker.

---

## Check 5 — copy integrity against COPY.md, the PM rulings and the spec → NO BLOCKER

Sources compared: `design/layout-v2/COPY.md` (incl. the "PM rulings" block at the top),
`spec/export_contract.md`, `spec/conservation.md`, and the shipped strings in `viewer/src/*.ts`.
Scripts: greps + `$TMPDIR/pp/bindings3.mjs` and `$TMPDIR/pp/bindings4.mjs` (rendered text, read from
the DOM in the running app).

**G12 (float64 must not be called "decimal") — PASS.**
```
$ grep -rn -i "decimal" workbench/viewer/src        → (no match)
ok  G12: float64 gloss is the PM text and never says “decimal”
    rendered: "64-bit binary floating-point arithmetic, about 16 significant digits. R's default
    numeric type. Most language-model runs use 16 or 32 bits."          (common.ts:203, locale 4)
```
The only "decimal" left in the tree is `design/layout-v2/COPY.md:327`, in the table's "current"
(wrong) column — the ruling above it says "(It is not decimal.)".

**G13/G16 (never "trained on survey answers") — PASS.**
Rendered, default pair, `?learn=models`:
```
ok  only “survey responses” sentence is the negation:
    "The adapter was trained with DPO on made-up everyday scenarios, preferring the answer that
     matches the USA's direction on the Global Preferences Survey (e.g. more trusting, more
     patient). It was not trained on survey responses."                    (common.ts:248)
ok  training data named as made-up scenarios + GPS direction
```
Same wording in the DPO glossary entry (`common.ts:206`, "…Not survey responses.") and in landing §2
(`viewer/src/landing.ts:51`, "trained with DPO on made-up everyday scenarios, preferring … GPS").
For a pair with no adapter (`smol_base|smol_inst`) the DPO sentence is **absent** rather than wrong:
```
ok  no adapter ⇒ no DPO training-data sentence
    "…A is SmolLM2-135M (pretrained base). B is SmolLM2-135M-Instruct. For every layer and token, …"
```
No string anywhere claims training on survey answers/responses.

**K2 (story() sign wording) — PASS.** `viewer/src/landing.ts:112` renders
`Overall, B's margin ends ${abs} higher/lower than A's: further toward / less toward “${label_plus}”`,
branching on the sign of `d_margin` (no "−0.123 higher" left). Confirmable on screen: for the default
pair `d_margin = +1.86` the caption reads "higher … further toward"; for `smol_base|smol_inst`
`d_margin = −2.26` it must read "lower … less toward" (same template, sign branch).

**K10 (no hard-coded question text) — PASS.** `common.ts:59 questionText()` slices the exported
`question` segment. Rendered hero captions, from the DOM:
```
bank_USA_00023ac74dac → 'Scenario: "A fellow student tutored me for free before a critical exam, …'
                        = the export's question-segment tokens, and no Q81 wording anywhere
wvs_Q57               → 'WVS Q57: "Generally speaking, would you say that most people can be trusted …'
```

**K11 (no hard-coded pair labels; labels from the registry) — PASS.**
```
default pair #who  : "A: SmolLM2-135M-Instruct (original) · B: Instruct + USA DPO LoRA (3 epochs) (fine-tuned) · wvs_Q81"
smol_base|smol_inst: "A: SmolLM2-135M (pretrained base) · B: SmolLM2-135M-Instruct · bank_USA_00023ac74dac"
hero SVG labels    : registry labels; no “original/fine-tuned” for the non-adapter pair (roleOf, common.ts:56)
```

**K24 ("scenario" for bank items) — PASS where the copy says it, one gap flagged.**
```
export manifest  : bank question segment = {"a":55,"b":147,"kind":"question","label":"scenario"}
landing hero      : prefix "Scenario:" (bank) vs "WVS Q57" (WVS) — verified both
?learn=segments   : "…the scenario, the options, the answer cue…" (bank) vs "…the question, …" (WVS)
?learn=models     : "The prompt, the scenario and the answer position are the same for both."
```
Refutes the PM's logged "bank items are not marked as 'scenario' in the UI" for the landing and the
pop-ups, and for tab B, which draws every segment's label (from `manifest.segments`) in its band
(`viewer/src/tab-b.ts:87`). **But in the ladder the word is not visible:** the question part is open by
default, open parts are drawn as plain token text with no label (`viewer/src/tab-c.ts:135-141`), so the
only naming a reader gets there is the item id in the answer card ("The model's answer ·
bank_USA_00023ac74dac"). Pills observed for the bank item are template/system/instruction only.
→ fix-later, not a blocker.

**Technically wrong glosses the card asked about — none found.**
```
ok  DLA is not called causal: "Direct effect only … A large DLA does not show that the part causes the
    answer; that needs ablation or patching." (landing.ts:74); the DLA pop-up adds "direct effect only"
ok  ‖B − A‖ is not a difference of norms: "It is not the difference of two lengths: ‖B − A‖ is not
    ‖B‖ − ‖A‖. It is never negative …" (common.ts:244, rendered)
ok  B − A is named as a signed difference of two numbers, attributed to d_head_attr/d_mlp_attr
    (said to be from the pair export; other signed changes "computed on this page, shown in italics")
ok  K1 qualifier kept: "(relative) once the reference's own 32-bit rounding steps are switched off"
ok  K5: "a test checks this; each export also records the gap" is the wording shipped (common.ts:226)
```

**Badges — PASS on the landing, absent (by design) in the tabs.**
```
ok  landing: every figure carries a badge  {"data":5,"ill":1,"figs":6}
grep -rn "real data" viewer/src → landing.ts only (lines 25, 36, 38, 54, 55, 57, 81)
```
COPY.md specifies badges for the landing figures only (L06, L16, L17, L24, L25, L26 — all shipped,
one `illustration · not data` for the schematic). No tab draws an illustration, and none of the C/M/O
string tables asks for a badge. Nit for the next pass: a reader of the tabs alone never sees the
"real data" statement that the landing footer makes.

**Bonus bindings (already in check 2 but they are copy claims too).**
```
ok  the pair gate drawn in the conservation pop-up "6.1e-9 · clamped 2.1e-9" equals my own sum of the
    stored float32 arrays: Σ d_head_attr + Σ d_mlp_attr + d_embed_attr − d_margin = 6.1388643057824765e-09
    = manifest conservation.d_attr_gap_float32 (same double), clamped 2.1005835404430684e-09
ok  ladder with clamp=1 draws the clamped attribution: layer 17 · head 3 → −0.002773 = d_head_attr_clamped,
    and its title cites "from the pair export (d_head_attr_clamped, d_mlp_attr_clamped)"
ok  the ladder Change column IS labelled per row in the shipped inspector: rows are
    ["Write size ‖o‖", 56.50, 67.91, 23.20] and ["Push on the margin (DLA)", −5.952e-5, 0.04582, +0.0459],
    each cell carries a title naming its array, and CHANGE_FOOT says gold = length, signed = B − A.
    → the PM's logged "Change column … with no row label" is REFUTED as shipped (common.ts:146).
```

Two assertions in my first copy pass failed for my own reasons and are **withdrawn**: (i) a pill reading
"scenario"/"WVS question" was expected for an open segment — open segments are inline text, not pills;
(ii) two regexes missed the U+2212 minus and the scientific-notation values. Re-run in
`bindings4.mjs`: 14/15 ok, the one failure being that extraction regex again (the drawn value 6.1e-9 is
the one my reader computes).

---

## Check 4 — robustness (tsc, leak, sweep) → NO BLOCKER

Re-run from the repo root, no pipes on the exit codes I report. The PM's scripts were **copied
verbatim** into `$TMPDIR/pp/` (that folder is the one with `puppeteer-core`; ESM ignores
`NODE_PATH`, which is why the copies, not edits, are needed).

**4.1 `tsc`.** PASS.
```
$ cd workbench/viewer && npx tsc --noEmit    → exit 0     (TSC_EXIT=0)
```

**4.2 Leak check, ≥30 rebuilds with tab switches.** PASS, twice.
```
$ node webgl_leak_check.mjs "http://127.0.0.1:5178/?tab=a" 40 \
      "hscale,color,click:[data-tab=c],click:[data-tab=a]"
{"url":"http://127.0.0.1:5178/?tab=a","rebuilds":40,"before":{"geometries":74,"textures":130},
 "after":{"geometries":74,"textures":130},"context_lost":false,"page_errors":[],"pass":true}
exit 0
```
That is the card's named script (`~/.hermes/skills/mlops/interpretability-visual-workbench/scripts/
webgl_leak_check.mjs`), driven with 40 rebuilds that include two tab switches per cycle and start and
end on tab A (the only view that holds a WebGL context). Flat at 74 geometries / 130 textures.
The PM's stronger run reproduces bit-for-bit:
```
$ node leak_end_on_a.mjs
{"steps":80,"start":{"geometries":74,"textures":130,"lost":false},
 "end":{"geometries":74,"textures":130,"lost":false},"flat":true,"page_errors":[]}
exit 0
```

**4.3 All-items × all-tabs sweep for console errors.** PASS.
```
$ node sweep.mjs <abs>/workbench/exports/index.json
{"pairs":16,"loads":64,"failures":0,"console_errors":0,"bad":[],"pass":true}   exit 0
```
Coverage checked against the files rather than the report: `index.json` lists 16 pairs and 22 runs;
the 16 `(a,b,item)` triples in `index.pairs` are exactly the 16 `pair__*.json` on disk (no item missing
from the index, no file missing from the index), and the sweep loads each triple's item in all four
surfaces (landing, c, b, a) = 64 loads.

---

## The PM's logged known issues — confirmed or refuted

1. **"the ladder inspector's Change column mixes ‖B−A‖ and signed B−A with no row label" → REFUTED.**
   As shipped, each row of the card carries its own label and the two kinds of change are separated by
   label and by a legend: rows read `["Write size ‖o‖", 56.50, 67.91, 23.20]` (gold, a length from
   `d_head_norm`) and `["Push on the margin (DLA)", −5.952e-5, 0.04582, +0.0459]` (signed, from
   `d_head_attr`); every change cell has a `title` naming its array, and `CHANGE_FOOT`
   (`common.ts:146`) states "gold = … a length, never negative, exact, from the pair export … signed =
   B − A …, upright from the export, italic computed on this page". The `26.56` the PM saw is the
   tab-A "largest changes" bar list, which states its own meaning in its foot ("Each bar is
   ‖o_B − o_A‖ at the answer position (d_head_norm)").
2. **"bank items are not marked 'scenario' in the UI" → PARTLY CONFIRMED.** Refuted for the landing
   (hero prefix `Scenario:`), the `segments` and `models` pop-ups, and the exporter's own label
   (`manifest.segments` question label is `scenario` for `bank_USA_00023ac74dac`); confirmed for the
   ladder, where the question part is open by default so no label is drawn at all and the only naming
   is the item id in the answer card. fix-later.
3. **"tab A: margin labels clipped at the right edge; grid framed low; ‖B − A‖ glyphs read as
   IIB − All" → NOT REPRODUCED as a DOM/SVG defect.** A probe of every `<svg>` `text` box against its
   host, at 1440 and 1700, in all three tabs and the landing, found **zero** overflowing texts
   (`clip.mjs`: `{"c":[],"b":[],"a":[],"landing":[]}`; `page_errors: []`). The ‖B − A‖ glyphs render as
   proper double bars in the shipped screenshot `viewer/screens/v2/a-side-1440.png` (read, not
   measured). Two of the three claims are about canvas-drawn labels (the prompt-map band label, which
   is clipped to its own band by design once the band is short, and the right-edge 3D annotations),
   which no DOM probe can measure — reported, not resolved. Nit/fix-later for the next visual pass.
4. Minor wraps/truncations are outside what I can measure from the DOM; not a finding.

---

## VERDICT: **ACCEPT** — no blockers. Five fix-later/nit items, one request-error note.

The artifact is `workbench/` at the current worktree HEAD; the acceptance criterion is the five checks
in the card body. All five hold, re-derived from the files rather than from the producer's reports:
the exporter's tests (38, exit 0), the segment cover (22/22 runs, 11 segments each), the three decoded
items against their source records, the two conservation gates (worst 7.43e-8 float32, worst 1.19e-7
one-ulp), margins and 536 arrays bit-identical across the re-export plus three re-computed runs,
mark-to-array bindings in all three tabs (≥3 marks per tab, both A|B and Δ), the no-silent-drops
declaration, tsc 0, the leak check flat over 40 and 80 rebuilds, the 64-load sweep with 0 console
errors, and the copy against the PM rulings.

Fix-later, in the order I would take them:
1. ladder: name the merged collapsed gap ("4 parts" → "system + persona, 4 parts") — `scene.ts:89`;
2. ladder: the bank item's question part is open by default, so the word "scenario" never appears in
   that tab — `tab-c.ts:135-141`; the landing and the pop-ups already do it;
3. tabs carry no `real data` badge; only the landing does (matches COPY.md, but a tab-only reader
   never sees it) — `landing.ts` vs `tab-*.ts`;
4. prompt-map band labels are clipped to their band and can truncate mid-word — `tab-a.ts:342-347`;
5. the right-edge 3D annotations could not be measured; whoever does the visual pass should check them
   with eyes on a screenshot at 1440.

Nits: `bank.py`'s `build_user_prompt` is dead code for the export (`items.py:140` uses
`survey_prompt_v1`); `COPY.md:327` still carries "float64 = 64-bit decimal arithmetic" in its
"current" column, which is the text G12 bans.

Request-error note (not a finding): nothing under test is missing for a verdict; but the exhaustive
"every figure has a badge" reading of check 5 is only defined for the landing, because COPY.md
specifies no badge in the C/M/O string tables.

Reproduce with: `env -u PYTHONPATH uv run --project workbench pytest workbench/tests -q`;
`python3 plans/verify/check1.py`; `check1d.py`; `check1f.py`;
`recompute.py` (loads the models); and, with the viewer served on 127.0.0.1:5178 and
`puppeteer-core` on the module path, `$TMPDIR/pp/bindings.mjs|bindings2.mjs|bindings3.mjs|bindings4.mjs|k2.mjs`,
`$TMPDIR/pp/sweep.mjs <abs>/workbench/exports/index.json`, `$TMPDIR/pp/leak_end_on_a.mjs`,
`$TMPDIR/pp/webgl_leak_check.mjs "http://127.0.0.1:5178/?tab=a" 40 "hscale,color,click:[data-tab=c],click:[data-tab=a]"`.

Route: `deepseek/deepseek-v4.1-flash` on `openrouter` (the card's `model_override`).



