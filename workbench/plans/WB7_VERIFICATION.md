# WB7-V verification: the v1.5 candidate (Q57 at panel scale, human layer, how-to-read pop-ups, many-option headline)

Card t_ab5d175a. Verifier route: z-ai/glm-5.3 via openrouter (GLM; cross-family to all four producers:
DeepSeek WB7-Q, Claude WB7-W/H/I). Verified at HEAD 6238102 (branch Adapter-Brain-Vizualization);
`git diff --stat 0bc4772..6238102` touches only `workbench/plans/WB7I_ACCEPTANCE.md`, so the code verified
is exactly the code WB7-I built. The worktree's uncommitted `workbench/analysis/` WIP was left untouched.

Scope per the PM's two comments: the deploy candidate is WB7-I's `dist/` build WITH the human layer
(augusto confirmed "ship human layer"); the panel-off build is not deployed and got the reduced check.
`data/` was never opened; no respondent row was read or recomputed. WB7-I's ASU recompute is cited, not rerun.

## Verdict

- **Deploy candidate (with human layer): PASS-WITH-NOTES** (8 notes, no blocker; note N1 requires a
  story-page prose edit at or before deploy — a words fix, not a data or viewer-code fix).
- **Panel-off build: PASS** (verify_bundle exit 0, 375 files, 949,428,139 B, human cells null,
  `check_human_numbers.mjs` mode off: 129 checks, 0 failed).

## Check 1 — rebuild, identity, size (all exit codes read directly)

| Command | Exit | Result |
|---|---|---|
| `shasum -a 256 dist/deploy_bundle.tar.gz` | 0 | `d46cc98436a7a4da483cecd8bc250218977f70e1be64fe2f73b29146a6057481` — equals WB7-I's declared archive sha256 exactly |
| `env -u PYTHONPATH HF_TOKEN= uv run python scripts/build_deploy_bundle.py --out $S/on/deploy_bundle.tar.gz --human-reference human_ref/human_reference.json` | 0 | 376 files, payload 949,436,898 B (cap 950,000,000; headroom 563,102 B), "Q57: 68 comparators; full 4, light 40, pairs only 24" |
| Per-file sha256+bytes, my manifest vs `dist/deploy_bundle.tar.manifest.json` | 0 | **376/376 identical, 0 differing, 0 only-in-one.** Payload bytes equal. `human_reference` (7 items / 56 cells), `selection_rule` and `q57` manifest blocks byte-equal. (My archive's own sha256 differs — `55a94bed…` — because tar.gz embeds mtimes; per-file payload identity is the criterion, and the producer's archive matches its own declared sha.) |
| `viewer/screens/sca2/verify_bundle.py $S/on/deploy_bundle.tar.gz $S/on/extracted --report` | 0 | `pass: true`, `human_reference_cells: 56` |
| `scripts/check_bundle_identity.py $S/on/...manifest.json` | 0 | 143 checked, 138 identical, the same 5 allowed changes (`assets/index-BlZYX-aA.css`, `assets/index-CCjLwD0I.js`, `exports/index.json`, `index.html`, `sca2/index.html`), **0 violations** |
| Panel-off rebuild (no flag) + verify + identity | 0 | 375 files, 949,428,139 B, `human_reference_cells: null`, identity 0 violations — all four numbers equal WB7-I's off-build table |

Q57 data equals source, byte for byte (independent GLM re-run of the WB7-Q round-3 check, my script
`cmp_manifests.py` / `data_checks.py` over all 68 comparators): 40 light runs keep exactly the source arrays
minus the 8 dropped (`light_drop`), every kept array's bytes equal the source slice; 24 numbers-only runs
ship `arrays: {}` and `bin: null`; the 4 full comparators and the base run are complete and identical; all
64 new pairs ship without `d_head_norm`, every shipped array byte-equal; **every non-array field of all
137 run/pair JSONs equals its source export** (0 problems). `exports/index.json` vs v1.4 is purely
additive: +64 Q57 runs, +64 Q57 pairs, +49 model ids, **0 v1.4 entries changed or removed**.

## Check 2 — tests

`env -u PYTHONPATH HF_TOKEN= uv run --project . pytest tests -q -p no:cacheprovider` → **201 passed,
4 skipped, exit 0**. `npx tsc --noEmit` (viewer/) → **exit 0**. Both equal WB7-I.

## Check 3 — number parity vs v1.4 (33 parity URLs)

Own sweep (puppeteer-core, both trees self-served, DOM text walk over #app text nodes skipping
SELECT/OPTION — rendering-independent — token regex `[-+−]?\d[\d,.]*%?`):
33/33 URLs, `__ready` true on both sides, **0 console or page errors** on the new side.

- 2 URLs byte-identical in tokens: the two sign-prompt Q57 pages (no country, no survey cell) — matches WB7-I.
- 30 URLs have only-new tokens, no old-side-only tokens. Every added token class traces to a named change:
  the many-option headline (WB7-W: e.g. `5.6`/`6.2`/`40%`/`85%` on Q176 USA; `0.63`/`15.20`/`91%`/`66%` on
  Q43), the Q57 rows and picker count `68` (WB7-Q), the human panel (WB7-H: survey shares, means, gaps,
  `n` with thousands separators, `WVS-7` legend), the attribution citations (WB7-I: years, `133`/`1645`/`1692`,
  `9674`, `10.14281`, `3.1`, `4.0`, `2017`–`2022`).
- 1 URL (`/?tab=k`) has old-side-only tokens: `4`, `110111`×1, `111111`×1, `91%`×2, `50.2%`, `84%`. All traced
  to the WB7-Q Cohort rebuild (accepted with its own parity table in WB7-Q round 3, re-checked there row by
  row): the picker count for Q57 changed 4→68, the six-bit code moved from row label to block header, and
  the modal-answer line is deduped per block ("Most likely answer in every row"), which drops the modal
  percentages 91%/50.2%/84% from those rows. The dumbbell percentages (5.8%→66%, 5.8%→49.8%, 5.8%→11%)
  and log-odds (+14.6, +6.72, +0.266) are unchanged on both sides. This is the one letter-violation of the
  WB7-W allow-list rule, exactly as WB7-I disclosed; the underlying data did not change. See note N3.

**Q176 recompute** (card item): from `exports/index.json` probs, codes 1–10, Σ code·P:
A base 5.5918 → 5.6; B USA 6.1550 → 6.2; probs sum to 1.000000 over the ten codes; modal answers
A "5" (39.7% → shown 40%) → B "6" (84.7% → shown 85%). Matches the on-screen headline
"Average answer on the 1–10 scale: A 5.6 → B 6.2" and "Most likely answer" line, and the allow-list values.
The old "+9.83 headline" misreading is gone: the headline now leads with the expected answer.

## Check 4 — Q57 at panel scale

Own script (`q57cohort3.mjs`), Cohort `?tab=k&item=wvs_Q57`, default 42 adapter rows, "All comparators" 68
rows; every row's aria-label rowTip and DOM parsed:

- **Percentages + log-odds**: all 68 rows match `index.json` probs and pair `d_margin` under the exact
  display functions (`pct()`: <0.1%, >99.9%, 1 decimal under 10; `change()`: 3 significant digits). 0 mismatches.
- **Matched pairs vs `sca2_data.json`**: all 42 adapter rows sit in the block whose aria-label equals the
  country's `countries[].bits` (0 mismatches; 26 blocks). Layer map 70 rows, horizontal overflow 0.
- **Human elements on rows**: survey share in the rowTip and the pink tick's `left:%` equal
  `human_reference.json` shares for all 42 adapter rows; all 26 sign-prompt rows have no tick, no survey text
  ("–" in the closer column); the 24 numbers-only rows carry the "Cohort only" tag and no Ladder link.
  Marker text (direction + both gaps) recomputed independently for all 42 cells: 0 mismatches.
- **Light comparator**: `?tab=a` on USA (light): the exact `.notshipped` sentence
  ("The public workbench ships the full 3D capture only for the featured pairs. This comparator has the
  Ladder, Matrix and Cohort views."), 0 canvases, `__ready` true, 0 console errors. Network: the only bin
  requests are the slim pair bin `bytes=0-76559` and the light run bin `bytes=0-617623` (whole files —
  the light bin contains no heavy array); **no request touches any heavy array** (base-bin heavy ranges
  from the run JSON checked against every logged range; no base-bin request at all on this tab).
- **Ladder head pin on a light comparator** (WB7-Q F1 crash path, re-tested since common.ts changed):
  clicking a `.cell` in `#lad` on USA Q57 sets `sel=0,-1`, the drawer pins and fills ("MLP block ·
  layer 0 … pinned"), no error panel, 0 console/page errors — no regression (the Ladder is SVG, not
  canvas; my first probe looked for the wrong element and found nothing — the sweep above is the real check).

## Check 5 — human layer (deploy gate)

- **Screen numbers vs the shipped aggregate**: `node scripts_verify/check_human_numbers.mjs $S/on/extracted
  on …` → **656 checks, 600 passed**. Every numeric check passed: Ladder headline numbers, every cell of the
  all-answers tables, Cohort tick positions, yes/no markers vs a fresh index.json computation, row tooltips,
  legend, sort, column header. The 56 non-passing checks are all the same stale expectation: the script
  asserts the marker equals the bare pre-PM-edit sentence, while the PM's binding E5.3 edit makes the marker
  carry both gaps. I recomputed every one of the 56 markers independently from `index.json` probs +
  `human_reference.json` (same fixed rule, same rounding): **56/56 exact matches** of direction, both gap
  numbers and wording, and the script's own expected direction agreed with the marker in every line.
  The checker's expectation is stale, the artifact is right. See note N2.
- **Aggregate only, no microdata**: the bundle ships exactly one `exports/human_reference.json`
  (9,620 B class, gitignored at source, never committed); schema `sca2-workbench/human-reference@1`;
  56 cells (Q57×42, Q99×4, Q106/Q176/Q43/Q50/Q81×2), cell keys limited to `n, shares, top, mean,
  mean_present, ordered`; **no cell has n < 100 (min n = 952, ARG)**; `dropped_cells: []`,
  `dropped_items: {}`; no respondent row exists anywhere in the bundle (verify_bundle schema check + my
  walk). `data/` was never opened by me.
- **Wording**: rendered human text uses "chose", "respondents", "descriptive"; the model "gives a
  probability"; ties read "as far from the survey as the base model"; missing data reads "no survey data".
  Banned words on the human elements: none ("accuracy" appears once, negated: groundTruth pop-up
  "Not an accuracy test" — that sentence exists to make the rule, see note N8). No TVD, Spearman or total
  variation anywhere in the human layer; the groundTruth TVD bullet WB7-H flagged is gone.
- **Sign-prompt rows**: no human tick, "–" in the closer column (all 26, check 4 above).
- **Attribution** (PM's list): all lines present in all three required places —
  `deploy/SPACE_README.md`, the landing footer (`viewer/src/landing.ts`, rendered on `/`), and the
  story-page footer (`viewer/public/sca2/index.html`, shipped as `sca2/index.html`):
  WVS-7 citation (Haerpfer et al. 2020, Round Seven – Country-Pooled Datafile, JD Systems Institute &
  WVSA Secretariat, doi.org/10.14281/18241.1) with the "Wave 7 (2017–2022), worldvaluessurvey.org" source
  line; both GPS citations (Falk et al. 2018 QJE 133(4) 1645–1692; Falk et al. 2016 IZA DP No. 9674) plus
  the CC BY-NC-SA 4.0 notice and "No GPS values are shipped"; "Built with Llama" with the Llama 3.1
  Community License line. (Line wraps differ between the three files; content is word-for-word.)
- **Panel-off build**: `check_human_numbers.mjs … off` → **129 checks, 0 failed, PASS** — no human element
  anywhere, no console/page error, the only failed request is the missing file itself.
- **Aggregate correctness**: rests on WB7-I's independent recompute on the ASU seat (56 cells, 0
  mismatches vs the local WVS-7 .dta, weights W_WEIGHT), which I cite and did not repeat (same-family
  limitation, see N7).

## Check 6 — pop-ups vs what the views draw

- **Clamped run**: the pop-up text matches the capture code exactly. `stream_capture.py:266-268`:
  `q3 = (g < -eps_q3) & (u < -eps_q3)` with `EPS_Q3 = 0.05` (llama_capture.py:38), and in the clamped run
  `c = c_raw.masked_fill(q3, 0.0)` — gate and up both below −0.05, outputs zeroed in every layer and token.
  The `q3_count` tooltip, the `clamp` pop-up, the `mlp` pop-up and both GLOSSARY entries agree with this and
  with each other.
- **Ladder (howto-c)**: cells per head/MLP at t*, rows = layers with the emb row and wide MLP cell, DLA unit,
  blue/orange/grey with the key under the chart, A/B/Change faces with Change default, gold rings for the
  five largest, click-to-pin drawer, "all cells + embedding term = total ✓" line, grey/teal log-odds-by-layer
  with the top dot, prompt shading from stored top-16 attention, clamped button (key C) — all match what
  tab-c draws (SVG `#lad`/`#mc`, `.cell[data-l][data-h]`, `#clamp`).
- **Matrix (howto-b)**: "linear from 0, clipped at the 99th percentile, footer prints the clip value and
  the maximum" — matches tab-b.ts (p99 linear scale; footer prints clip + max verbatim). The log-scale legend
  belongs to the 3D prompt map, and howto-a correctly calls that one logarithmic. White t* frame, 2 px
  template columns, hover A/B/‖B−A‖ — match.
- **3D object (howto-a)**: log heights shared by A and B, gold change scale on its own, camera buttons,
  log-clipped prompt map — match (notshipped guard sentence on light comparators checked in check 4).
- **Cohort (howto-k)**: row arrow base→comparator on 0–100%, log-odds column, matched-pair sentences,
  layer map — accurate. It does not mention the new survey tick/column/sort (see note N5).
- **groundTruth**: states the rule actually on screen (one marker, both gaps, two-answer share rule,
  3+-answer mean rule, unordered items without a mean use the share), sign prompts have no reference,
  "about 100%" (rounding), "no survey data", "Not an accuracy test". Matches human.ts exactly.
- **Claim lock**: no pop-up text makes or strengthens any Paper A/B claim; no paper number appears that is
  not already on the v1.4 pages; the human layer carries no Paper B statistic. Nothing contradicts
  `planning/TWO_PAPER_CLAIM_LOCK.md`.

## Check 7 — errors and the failure path

Across every page I opened (33 parity URLs × 2 sides, 68-row Cohort, all Ladder human pages via the
656-check run, tab=a guards, panel-off 129-check run, the pop-up sweep): **0 console errors, 0 page
errors**.

**A 500 on a heavy range never showed a wrong number** (`final_sweep.mjs`): with a fault server returning
HTTP 500 for every range at or after the `attn_topk_idx` offset of the full BGD run bin, `?tab=a` on BGD
Q57 still rendered with `__ready: true`, no error panel, 0 console/page errors, and its answer strip showed
exactly the run's own readout numbers (change −10.1 = `d_margin` −10.08 rounded; A −1.03, B −11.11,
P("1") 0.26 → 0.00, "✓ matches the archived Paper B run") — all read from the run JSON, none derived from
the failed heavy fetch, and none wrong. The pop-up sweep also confirmed on the live pages: every pop-up
opens (howto-c, groundTruth, clamp, answer details, howto-b, howto-a) with the expected heading and the
key claims; groundTruth contains no TVD/Spearman/validation; clamp names −0.05, the zeroed outputs and
`q3_count`; the Matrix footer prints "0 → 7.24 (99th percentile, linear; brighter cells are clipped) ·
max 13.8", matching howto-b's "linear from 0 … footer prints the clip value and the maximum"; the full BGD
3D draws 2 canvases with no notshipped guard, while light comparators show the guard sentence and 0 canvases.

## Limits of this verification (same-family note, per the PM)

WB7-Q's own verifier ran on Claude — the same family as the WB7-W/H/I producers — so its viewer-side
judgment calls were same-family. I re-ran, cross-family and independently, everything that is deterministic:
rebuild byte identity, per-file manifest identity, source-slice identity for all 68 comparators (incl. the
1112-array equivalent), v1.4 identity, parity tokens, Cohort row numbers, tick/marker recomputation, the F1
pin path, the light-run network guard, tests and tsc. What I could not independently verify: (a) the
correctness of `human_reference.json` against WVS microdata — that is WB7-I's ASU recompute (56 cells,
0 mismatches), cited; (b) anything about the live Hub deployment (not deployed yet; WB7-D's card).

## Notes (non-blocking unless marked)

- **N1 (edit before or with deploy).** The story page's intro (viewer/public/sca2/index.html:64) still
  says "It has no respondent rows, no country-level TVD …, and no human means or distributions." The
  with-human build now shows WVS-7 shares and means, so the last clause is false on the shipped site. My
  decision (the card left this to WB7-V): **the sentence needs an edit** — e.g. "no respondent rows, no
  country-level TVD; survey figures are country-level WVS-7 aggregates only." Prose only; a words edit for
  WB7-D or a follow-up card, not a viewer-code change, and not a data problem. The same stale clause is in
  the `label` field of `sca2_data.json` ("no respondent rows, country-level TVD, human means or
  distributions"), which is generated by `build_sca2_data.py` in the main repo.
- **N2.** `scripts_verify/check_human_numbers.mjs` line 86 still asserts the bare pre-edit marker string;
  with the PM's E5.3 both-gaps marker its "on" mode reports 56 fails that are all wording, not numbers.
  The next words/build wave should update the expectation to `markerText()` semantics. The shipped marker
  is correct (56/56 independently recomputed).
- **N3.** The WB7-W parity allow-list's rule "tokens only in OLD must be empty on every URL" is violated on
  exactly one URL (`/?tab=k`) by the earlier, separately accepted WB7-Q Cohort redesign; WB7-I disclosed
  this and my sweep traces every such token (see check 3). No data token changed anywhere.
- **N4.** NGA on Q106 shows the marker "closer to the survey than the base model (2.1 vs 2.1 points from
  the survey mean on the answer scale)": the true gaps are 2.08 vs 2.10, both round to 2.1, so the display
  reads as a tie while the direction comes from the unrounded values (human.ts compares unrounded, prints
  one decimal). Correct but cosmetically ambiguous; a one-decimal-more display would fix it.
- **N5.** `howto-k` (WB7-W, written before the human merge) does not mention the Cohort's new pink survey
  tick, the "closer to survey than base?" column or the "Closer to the survey" sort; those are covered by
  the axis title ("… share of respondents who chose it (pink)"), the column-header rule tooltip and the
  groundTruth pop-up. A sentence in howto-k would close the gap.
- **N6.** WB7-H's acceptance says the smallest cell has n = 931; the shipped aggregate's smallest cell is
  n = 952 (ARG). The acceptance prose describes WB7-H's own earlier build; the shipped file is the one
  WB7-I recomputed at 0 mismatches and the one every screen number matches. No cell is below 100 either way.
- **N7.** Same-family limits, as above: WB7-Q's viewer verification was Claude-on-Claude; the WVS
  microdata recompute is WB7-I's (cited, not repeated by GLM; `data/` untouched).
- **N8.** The groundTruth pop-up contains "Not an accuracy test". The card's wording rule ("never accuracy
  or validation") is satisfied in substance — the word appears only in explicit negation, which serves the
  rule's purpose — but a strict reading would drop the noun; flagging for the PM, no action required.

## Reproduce

```
cd workbench
S=$HERMES_KANBAN_WORKSPACE/wb7v
env -u PYTHONPATH HF_TOKEN= uv run python scripts/build_deploy_bundle.py --out $S/on/deploy_bundle.tar.gz --human-reference human_ref/human_reference.json   # exit 0
python3 $S/cmp_manifests.py        # 376/376 identical vs dist manifest, exit 0
env -u PYTHONPATH uv run python viewer/screens/sca2/verify_bundle.py $S/on/deploy_bundle.tar.gz $S/on/extracted --report $S/on/verify-report.json   # exit 0, 56 cells
env -u PYTHONPATH uv run python scripts/check_bundle_identity.py $S/on/deploy_bundle.tar.manifest.json   # exit 0, 0 violations
python3 $S/data_checks.py          # exit 0: 137 run/pair JSONs equal source; index.json additive-only; Q176 5.6->6.2; human file 56 cells, min n 952
python3 $S/marker_check.py         # exit 0: 56/56 markers recomputed exactly
node scripts_verify/check_human_numbers.mjs $S/on/extracted on $S/shots_on $S/on/extracted/exports/human_reference.json   # 656 checks; 600 pass, 56 stale-expectation fails (N2)
node scripts_verify/check_human_numbers.mjs $S/off/extracted off $S/shots_off   # 129 checks, 0 failed
node $S/parity.mjs && python3 $S/parity_analyse.py    # 33 URLs, 0 errors, diffs traced
node $S/q57cohort3.mjs             # 68/68 rows vs exports + human file + sca2 bits, 0 problems
node $S/final_sweep.mjs            # pop-ups, pin, 500-path (below)
env -u PYTHONPATH HF_TOKEN= uv run --project . pytest tests -q -p no:cacheprovider   # 201 passed, 4 skipped
cd viewer && npx tsc --noEmit      # exit 0
```

Scratch: $HERMES_KANBAN_WORKSPACE/wb7v/ (scripts above; `on/` and `off/` builds and extracts;
parity_result.json; q57cohort3.out; human_on/off.log). Not deployed, not pushed, no viewer code edited.

## Re-check (retry run 141, 2026-10-21, same route z-ai/glm-5.3)

Run 140 wrote this report but exited on a protocol violation before completing the card
(no terminal kanban call). Run 141 re-ran every load-bearing deterministic check and
read every exit code directly; all results equal the run-140 evidence above:

- `shasum -a 256 dist/deploy_bundle.tar.gz` → exit 0, `d46cc984…a6057481` — equals WB7-I's declared archive sha256.
- `python3 $S/cmp_manifests.py` → exit 0: my rebuild vs `dist/deploy_bundle.tar.manifest.json` **376/376 identical, 0 differing, 0 only-in-one**, payload 949,436,898 B both sides; `human_reference`, `selection_rule` and `q57` manifest blocks equal.
- `python3 $S/data_checks.py` → exit 0, `PROBLEMS: 0`; Q176 A base 5.5918 → 5.6 (modal 5, 39.7%), B USA 6.1550 → 6.2 (modal 6, 84.7%), probs sum 1.0; human file 56 cells, min n 952, no unexpected keys.
- `python3 $S/marker_check.py` → exit 0: all 56 checker-FAIL markers independently recomputed, **56/56 exact**, checker-expected direction consistent in every line (N2 stands: stale expectation, artifact right).
- `env -u PYTHONPATH HF_TOKEN= uv run --project . pytest tests -q -p no:cacheprovider` → **201 passed, 4 skipped**, exit 0; `cd viewer && npx tsc --noEmit` → **exit 0**.
- `node $S/final_sweep.mjs` → exit 0: pin path ok (`sel=0,-1`, drawer pinned, no error panel); groundTruth open, **no TVD/Spearman/validation**, "Not an accuracy test", both-gaps rule; clamp names −0.05, zeroed outputs, `q3_count`; answer details open (purple tick, clamped link); Matrix footer `0 → 7.24 (99th percentile, linear …) · max 13.8`; full-BGD 3D 2 canvases, no guard sentence; **500-on-heavy**: `__ready: true`, no error panel, strip `−10.1 / A −1.03 / B −11.11 / P("1") 0.26 → 0.00` — each equal to the run/pair readout JSONs (BGD `readout.margin` −11.112; pair change −10.08), none from the failed heavy fetch; **0 console/page errors**.
- Attribution re-grep: "Built with Llama", WVS-7 doi `10.14281`, GPS `9674` and `CC BY-NC-SA` present in all three required files (`deploy/SPACE_README.md`, `viewer/src/landing.ts`, `viewer/public/sca2/index.html`).
- Parity re-read of `parity_analysis.out`: 33/33 URLs `errs=0`, old-side-only tokens on exactly **1** URL (`/?tab=k`, the accepted WB7-Q redesign), `__ready` True 33/33 on both sides.
- Clamp code citation re-read: `src/sca2_workbench/stream_capture.py:266-268` `q3 = (g < -eps_q3) & (u < -eps_q3)`, `c = c_raw.masked_fill(q3, 0.0)`; `src/sca2_workbench/llama_capture.py:38` `EPS_Q3 = 0.05` — matches the pop-up text.

Verdict unchanged: deploy candidate (with human layer) **PASS-WITH-NOTES** (N1..N8, no
blocker; N1 is the story-page prose edit for WB7-D), panel-off build **PASS**.
