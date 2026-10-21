# WB7-Q acceptance (verifier card t_1ff5826c, parent t_7f9ce31a)

Verdict: **BLOCK** (2 findings, F1 and F2). Everything else passes. The bundle is sound; the viewer has one crash path on light comparators.

Verified at HEAD `f38eaf4` (branch `Adapter-Brain-Vizualization`), design of `dc4555d` and later (PM comment 157: light runs drop the six heavy arrays plus `neuron_attr` and `q3_write_norm`; new Q57 pairs drop `d_head_norm`; v1.4 files byte-identical). I rebuilt from source into a scratch directory; I did not use the producers' `dist/wb7q/` (it was stale per t_5b5a44e2).

Route: claude-sonnet-5-5 via anthropic (the route this session ran on). Not the codex seat named in the profile note, and the same family as the viewer producers (t_1b597436, t_5b5a44e2). The bundle checks below are deterministic scripts, not judgment.

Evidence directory (scratch, pruned after about 24 h): `/private/var/folders/x4/vhxvs_xj31z02hfv4nj85__h0000gn/T/wb7qv/` (build, `extracted/`, logs) and `/Users/bonorinoa/.hermes/profiles/verifier/cache/scratch/wb7qv_shots/` (screenshots, JSON results; scripts `wb7qv_*.mjs` next to it).

## Final bundle size

| Quantity | Value |
|---|---|
| Payload (manifest `payload_bytes`) | **949,395,660 B = 0.9494 GB** (cap 950,000,000; headroom 604,340 B) |
| Files | 375 (v1.4: 143) |
| Archive | 758,361,117 B, sha256 `2543b69b2e63f8b33997ff61e13fb17e9079c7933752af7fd4d8e0d8e8927cfe` |
| On-disk size of the extracted tree | 949,395,660 B, 375 files (equals the manifest) |
| PM's figure | 949,389,455 B, 375 files. Mine is 6,205 B larger: the viewer assets differ (`assets/index-BtHX9Wat.js`, built from HEAD). Both are under the cap. |

## Comparator lists (Q57, 68 comparators)

- **Full (already in v1.4, byte-identical to source):** BGD, CHN, sign prompts `sp001111`, `sp101111` (4).
- **Light runs (40, all adapters):** ARG, AUS, BOL, BRA, CAN, CHL, COL, CZE, DEU, EGY, GBR, GRC, GTM, IDN, IND, IRN, IRQ, JOR, JPN, KAZ, KEN, KOR, MAR, MEX, NGA, NIC, NLD, PAK, PER, PHL, ROU, RUS, SRB, THA, TUR, UKR, USA, VEN, VNM, ZWE. Each light run is 658,679 to 658,798 B (bin plus JSON); total 26,351,037 B.
- **Numbers-only (24, all sign prompts; the cap forced these):** `000000`, `000001`, `000010`, `000110`, `001000`, `001001`, `001101`, `010000`, `010001`, `010010`, `010110`, `011010`, `100000`, `100011`, `100110`, `100111`, `101000`, `110001`, `110110`, `110111`, `111001`, `111101`, `111110`, `111111`. Each has a run JSON (about 41 KB, `arrays: {}`, `bin: null`, no `light` flag) and a slim pair (76,560 B bin).
- **Order:** adapters first, then sign prompts, each in descending |d_margin|. Checked from the pair `d_margin` of every comparator: `allocation_order` equals 42 adapters then 26 sign prompts, both lists sorted descending (USA 24.51 first, 0.089 last). Every adapter fits, so no sign prompt received a light run.

## Item table

| # | Item | Result | Evidence |
|---|---|---|---|
| 1a | Builder and `verify_bundle.py` exit 0 | PASS | `env -u PYTHONPATH HF_TOKEN= uv run python scripts/build_deploy_bundle.py --out <scratch>` exit 0, twice. `viewer/screens/sca2/verify_bundle.py` on the archive: exit 0, `pass: true`, 101 runs, 93 pairs, 68 comparators, 40 light, 24 numbers-only. |
| 1b | Manifest total <= 0.95 GB | PASS | 949,395,660 B. Second independent build: per-file sha256 identical to the first (375 files). |
| 1c | 143 v1.4 files unchanged | PASS | `scripts/check_bundle_identity.py` exit 0: 143 checked, 138 identical, 5 allowed changes (`assets/index-BlZYX-aA.css`, `assets/index-CCjLwD0I.js`, `exports/index.json`, `index.html`, `sca2/index.html`), 0 violations. Independent check against the 13:48 v1.4 manifest `dist/deploy_bundle.tar.manifest.json` (143 files, 918,475,574 B): same 5 differences, and `deploy/v1.4_file_hashes.json` equals that manifest on all 143. The baseline comes from a local manifest, not the live Hub (see N3). |
| 1d | Light runs: `"light": true`, none of the six heavy arrays | PASS | 40 run JSONs with `light: true`; none lists `attn_topk_idx/val/mass`, `g_last`, `u_last`, `c_last`. Per PM comment 157 also: none lists `neuron_attr` or `q3_write_norm`. Array set equals source minus those 8, bin size equals the sum of `nbytes`. |
| 1e | Pairs (as redefined in comment 157) | PASS | 4 full pairs byte-identical to source (json and bin). 64 new pairs: array set equals source minus `d_head_norm`, bin size equals sum of `nbytes`, every non-array field equal to source. |
| 1f | Every kept number equals source, byte for byte | PASS | Script over all 68 comparators: 40 light runs (every array's bytes equal the source slice), 64 slim pairs (every array's bytes equal), 24 numbers-only runs, 4 full runs and pairs identical. Non-array fields of every run and pair JSON equal source. 0 problems. |
| 1g | `selection_rule` updated | **FAIL (F2)** | The string was updated, but it says the light run keeps "every array but the six heavy ones" and ships "its pair in full". The shipped bytes drop 8 arrays from light runs and `d_head_norm` from new pairs. The manifest's own `q57.light_drop` and `q57.new_pairs_drop` are correct. |
| 1h | Cap-forced order recorded | PASS | See comparator lists. Order is adapters first, then sign prompts. |
| 2a | `?tab=a` on a light comparator shows the exact sentence | PASS | Base vs USA (`tab=a`) and the same with `sel=16,3,5`: `.notshipped p` equals "The public workbench ships the full 3D capture only for the featured pairs. This comparator has the Ladder, Matrix and Cohort views." once; `__ready === true`; no canvas, no console or page errors. |
| 2b | Pinned-head attention on a light comparator | **FAIL (F1)** | Works through `tab=a&sel=`. Crashes through the Ladder: see F1. |
| 2c | No error panel, no endless spinner | PASS for `tab=a` and unpinned Ladder and Matrix; FAIL on the Ladder pin path (F1) | `tab=a` (light) and `tab=c`, `tab=b` without a pin: `__ready` true, 0 errors. |
| 2d | No network request for heavy arrays | PASS | `tab=a` on USA: range requests to the base run bin were `0-591887`, `14108688-14142479`, `19647504-21491359`. Overlap against the base's heavy-array byte ranges: none (those ranges hold `resid/attn/mlp/head_norm`, `q3_count`, `q3_write_norm`, `neuron_attr`, `head_attr`, `running_margin`). Light USA bin: one request, `0-617623`. No heavy request for the light B. Control: full BGD `tab=a` requested the heavy ranges and drew a canvas. |
| 3 | B picker optgroups, sorted by `plainName()` | PASS | `#selB` has `Country adapters` (42 options) and `Sign prompts` (26 options, 24 marked "(Cohort only)"), no loose options. Both groups equal their `localeCompare("en", numeric)` sort. See N2 for mixed labels. |
| 4a | Default filter shows 42 adapter rows | PASS | 1440 and 1024 px: 42 rows, pressed filter "Country adapters 42", 26 profile blocks, sort "Matched pairs". |
| 4b | Matched pairs match `countries[].bits` | PASS | All 42 rows sit under the block whose `aria-label` equals the country's `bits` in `sca2_data.json` (0 mismatches). Group membership equals an independent grouping of `sca2_data.json` countries by bits (26 groups, no difference). Spot checks: 111111 = USA, CAN, AUS; 110110 = VEN, KAZ; 001001 = CZE, JPN; 001111 = BGD; 111110 = PHL. All-comparators view: 68 rows in 26 blocks. |
| 4c | Row click opens the Ladder | PASS | USA (light), BGD (full), ZWE (light): each lands on `?tab=c&a=<base>&b=<comparator>&item=wvs_Q57`, tab "Ladder", `__ready` true, no error panel. The 24 numbers-only rows carry no link (stated "Cohort only"). |
| 4d | No jank at 1440 and 1024 px | PASS | Horizontal overflow 0 at both widths; every row 64 px; no long tasks; toggling adapters/all, 10 times: 22 to 125 ms at 1440, 22 to 198 ms at 1024 (software-rendered headless Chrome). Layout shift 0.1125 (1440) and 0.158 (1024) appears on load, but it is the app shell (BODY 162 px to 0), identical on the unchanged Ladder tab; see N4. Screenshots `v_cohort_q57_adapters_{1440,1024}.png`, `v_cohort_q57_all_{1440,1024}.png`. |
| 4e | Cohort numbers equal the exports | PASS | Extra check: all 68 rows' "x% to y%" and log-odds change against `probs` and `d_margin` of the export JSON: 0 mismatches (rounded display). |
| 5 | Wording (WB6) | PASS | Lines added since `eba46f7` in `viewer/src` and `viewer/public`: no "say/says" about model output, no "people say". Rendered text of Cohort, Ladder, Matrix, 3D and numbers-only views scanned: the only hits for "say/people" are the WVS question text itself. Cohort frame label is "Base model"; new strings say "base model". See N5. |
| 6 | Featured link | PASS | `/sca2/` (story page, section 5) renders `#q57-featured` with the exact sentence "Trust (Q57): Bangladesh and China differ in one sign, trust, and move in opposite directions." plus two links. Both open `?tab=c&a=<base>&b=..._bgd|_chn&item=wvs_Q57`, selected B "Llama-3.1-8B + Bangladesh adapter" / "+ China adapter", no errors. Claim check: `d_margin` BGD -10.084, CHN +5.332. The viewer root has no featured list (the links live on the story page; N6). |
| 7a | `workbench/analysis/` untouched | PASS (with note) | `git diff --quiet eba46f7 HEAD -- analysis` exit 0 (no committed change by WB7-Q). `git status` shows `analysis/w3b/run_w3b.py` modified and uncommitted, file mtime Oct 19 19:37, i.e. before WB7-Q; it belongs to the W3b card. |
| 7b | `TERMS`/`GLOSSARY`/pop-up strings in `common.ts` | PASS | `git diff eba46f7..HEAD -U0 -- viewer/src/common.ts`: two hunks only, the two new imports (lines 6 to 7) and the `inspectorHTML` head-attention line (173). `GLOSSARY` and the pop-up text are untouched. |
| - | Suite and types | PASS | `env -u PYTHONPATH HF_TOKEN= uv run --project . pytest tests -q -p no:cacheprovider`: **191 passed, 4 skipped, exit 0**. `npx tsc --noEmit`: exit 0. |

## Blocking findings

**F1. Pinning a head in the Ladder throws on every light comparator (40 of 68).** Item 2 requires pinned-head attention on a light comparator to show the exact sentence, with no error panel.
- Cause: `viewer/src/common.ts:128` (`compareRows`, head branch) calls `p.d_head_norm.get(...)` without a guard. New Q57 pairs ship without `d_head_norm` (comment 157), so `p.d_head_norm` is undefined. The guard that exists in `tab-b.ts:174-178` was not added here. (The producer handoff t_1b597436 tested a synthetic fixture built before the pair lever.)
- Evidence 1: open `/?tab=c&a=llama31_8b_nf4_dequant_float64_cpu_45cc5d4b_46079e27&b=llama31_8b_nf4_dequant_float64_cpu_45cc5d4b_46079e27_arg&item=wvs_Q57&sel=16,3`. `window.__ready` is `"error: TypeError: Cannot read properties of undefined (reading 'get')"`; the page shows the error panel "This pair could not be loaded, so nothing is shown." (`wb7qv_shots/light_arg_tab_c_sel.png`). A shared link with a pinned head breaks.
- Evidence 2: open the Ladder for ARG, USA (`tab=c`, no `sel`), then click any head cell (for example layer 0, head 0). The URL becomes `sel=0,0`, the drawer stays empty, and the page logs an uncaught `TypeError: Cannot read properties of undefined (reading 'get')` (stack `qd` in `assets/index-BtHX9Wat.js`). Same on ARG and USA; the full BGD control opens the drawer normally (`wb7qv_shots/ladder_pin_{arg,usa,bgd}.png`). Hover alone does not throw.
- The `tab=a` path is fine (`sel=16,3,5` shows the sentence).
- Fix (not made, I do not edit code): guard `p.d_head_norm` in `compareRows` and show the `NO_PER_HEAD` sentence; then re-check the Ladder pin on light adapters. Check `scene.ts:179,407` and `tab-a.ts:139` for the same pattern; they sit behind the `tab=a` light guard now.

**F2. The manifest `selection_rule` describes a superseded design.** See item 1g. It must say that light runs drop the six heavy arrays plus `neuron_attr` and `q3_write_norm`, and that new pairs drop `d_head_norm`. Source: `scripts/build_deploy_bundle.py` (the `selection_rule=` string near line 434). Fix and rebuild; the bundle's data does not change.

## Non-blocking notes

- N1. The card body says "pairs in full" and "light = all non-heavy arrays". I verified the dc4555d/comment 157 design instead, as the PM directed. Under the original wording only 1 comparator (USA) fits (a436f21 handoff).
- N2. The B picker mixes names and codes: "ARG adapter", "AUS adapter", "Bangladesh adapter", "BOL adapter" (sorted correctly by displayed name). The Cohort rows show full names (United States, Canada). Cosmetic.
- N3. The v1.4 baseline hashes come from the local 13:48 manifest, not from the live Hub. WB6-V reported 918,475,014 B for a fresh v1.4 rebuild, 560 B different from that manifest, within the allowed files.
- N4. Load-time layout shift is 0.11 (1440) and 0.16 (1024) on every tab, including the unchanged Ladder: the loading card hands over to the app shell (BODY 162 px to 0). Not from WB7-Q.
- N5. "A (base)" is still the label of the A selector on the Ladder, Matrix and 3D tabs (pre-existing v1.4 text); only the Cohort says "Base model". The story links read "base → BGD adapter".
- N6. The viewer root (`landing.ts`) has no featured list. The Q57 entry sits on the story page next to the 14 existing featured rows.
- N7. `dist/wb7q/extracted` is stale relative to HEAD; any later verifier or WB7-I should rebuild or re-extract.

## Reproduce

```
cd workbench
env -u PYTHONPATH HF_TOKEN= uv run python scripts/build_deploy_bundle.py --out $S/deploy_bundle.tar.gz        # exit 0
env -u PYTHONPATH HF_TOKEN= uv run python viewer/screens/sca2/verify_bundle.py $S/deploy_bundle.tar.gz $S/extracted --report $S/verify-report.json   # exit 0
env -u PYTHONPATH uv run python scripts/check_bundle_identity.py $S/deploy_bundle.tar.manifest.json              # exit 0
env -u PYTHONPATH HF_TOKEN= uv run --project . pytest tests -q -p no:cacheprovider                              # 191 passed, 4 skipped, exit 0
cd viewer && npx tsc --noEmit                                                                                    # exit 0
```

Browser checks: headless Chrome through puppeteer-core against `extracted/` served with `~/.hermes/cache/scratch/rangesrv/srv.py` on port 8851 (stopped afterwards, `lsof -i :8851` empty).

---

# Round 2 re-check at `7f96ffa` (narrow: F1, F2, N2 only)

**Verdict: PASS-WITH-NOTES. F1 and F2 are closed; N2 is closed. No blocking findings remain.** The round-1 pass items were not repeated, except where the data bytes were compared (below).

Route: claude-sonnet-5-5 via anthropic (same as round 1; the same family as the viewer producers).

Build: `git diff --quiet 7f96ffa -- scripts viewer/src viewer/public` exit 0, so the working tree for those paths equals `7f96ffa` (HEAD). I rebuilt into `/private/var/folders/x4/vhxvs_xj31z02hfv4nj85__h0000gn/T/wb7qv2/` (scratch).

| Command | Exit | Result |
|---|---|---|
| `env -u PYTHONPATH HF_TOKEN= uv run python scripts/build_deploy_bundle.py --out $S/deploy_bundle.tar.gz` | 0 | 949,396,119 B payload (0.9494 GB, cap 950,000,000), 375 files |
| `viewer/screens/sca2/verify_bundle.py ... --report` | 0 | pass |
| `scripts/check_bundle_identity.py` | 0 | 0 violations |
| `uv run --project . pytest tests -q -p no:cacheprovider` | 0 | 191 passed, 4 skipped |
| `npx tsc --noEmit` | 0 | - |

Data unchanged since round 1: the per-file sha256 of the round-1 build and this one differ in only two files, `assets/index-5BkcBv03.js` (the viewer; round 1 had `index-BtHX9Wat.js`) and `index.html`. All 373 other files, including every export, are identical. So the round-1 data checks (kept numbers equal source, v1.4 identity, light/numbers-only lists) still hold. The final size is 949,396,119 B (round 1: 949,395,660 B).

| Item | Result | Evidence |
|---|---|---|
| F1: Ladder head click on light comparators | **PASS** | Headless Chrome against the rebuilt bundle. Clicked a head cell on 4 light comparators: ARG (L0 H0), USA (L16 H3), ZWE (L31 H31), PHL (L5 H7). Each: `sel=` set in the URL, `__ready` true, drawer filled (865 to 867 chars), 0 console and page errors, no error panel. The drawer shows the exact NO_3D sentence in "Where this head looks". The "Size of the addition" row shows A and B with an empty change cell (as designed; `d_head_norm` is not shipped). Deep link `?tab=c&...&sel=16,3` on ARG and USA: `__ready` true, 0 errors (round 1: error panel). Control, full BGD L16 H3: drawer 1080 chars, change cell "size 0.2995", "Top-16 attention share" row present, no sentence. Screenshot `wb7qv2_shots/ladder_pin_usa_fixed.png`. |
| F2: `selection_rule` matches the drops | **PASS** | Manifest `selection_rule`: "its pair without d_head_norm (Matrix per-head detail) and its run as a light run (every array but the six heavy ones, neuron_attr and q3_write_norm) while the 0.95 GB cap allows, else the run numbers only (pairs-only)". Manifest `q57.light_drop` = `attn_topk_idx, attn_topk_val, attn_topk_mass, g_last, u_last, c_last, neuron_attr, q3_write_norm`; `q57.new_pairs_drop` = `d_head_norm`. The text matches both. |
| N2: B picker names | **PASS** | `#selB`: "Country adapters" 42 options, "Sign prompts" 26. Both are sorted by `localeCompare("en", numeric)`. No option reads "XXX adapter" with a country code (for example "Llama-3.1-8B + Argentina adapter"). |
| Scope | **PASS** | `git show --stat 7f96ffa` touches only `scripts/build_deploy_bundle.py`, `viewer/src/common.ts` (one line, the `compareRows` head row) and `viewer/src/main.ts` (the COUNTRY map). `TERMS`, `GLOSSARY` and pop-up strings are untouched. `analysis/` is not in the commit. |

Notes (non-blocking):
- N8. The `COUNTRY` map in `main.ts` is now `export`ed. This is harmless; nothing else changed there.
- N9. `analysis/w3b/run_w3b.py` is still modified and uncommitted (not WB7-Q; round-1 note 7a).
- N10. Round-1 notes N1, N3 to N7 stand. N2 is closed; N5 ("A (base)" label on the Ladder, Matrix and 3D tabs) is still open.
- N11. In the pinned-head table the size-of-change cell on light comparators is blank without a reason. A short "not shipped" label would be clearer. Cosmetic; no action needed for WB7-I.

Final bundle: **949,396,119 B = 0.9494 GB, 375 files.** Light (40 adapters) and numbers-only (24 sign prompts) lists are unchanged from round 1. The 4 full comparators (BGD, CHN, `sp001111`, `sp101111`) are also unchanged.


---

# Round 3 — root-card re-check at `7f96ffa` (card `t_7f9ce31a`, to close the card)

The card was decomposed into four children (builder, viewer, cohort, verifier) and re-awoken when they finished. This round is the root's own pass: rebuild from source, re-run every check a downstream reader relies on, and record the number parity that rounds 1 and 2 did not tabulate.

Route: `deepseek/deepseek-v4.1-flash-1017` via `openrouter` (the model on this card's dispatch), engineer profile. A different family from the three producers and from the verifier, so the checks below are not a re-read of the same model's work. Every check is a script or an exit code, not judgment.

**Rebuild is byte-identical to the shipped build.** `env -u PYTHONPATH HF_TOKEN= uv run python scripts/build_deploy_bundle.py --out ~/.hermes/cache/scratch/wb7/q57/rootverify/deploy_bundle.tar.gz` -> exit 0, `Q57: 68 comparators; full 4, light 40, pairs only 24; 603761 bytes of headroom left`, payload **949,396,119 B**, 375 files. Per-file sha256 against `workbench/dist/wb7q/deploy_bundle.tar.manifest.json` (the verifier's round-2 build): **375/375 identical, 0 differing, 0 only-in-one**.

| Command | Exit | Result |
|---|---|---|
| `uv run python scripts/build_deploy_bundle.py --out <scratch>` | 0 | 949,396,119 B, 375 files, 0.9494 GB (cap 950,000,000) |
| `uv run python viewer/screens/sca2/verify_bundle.py <tar> <out> --report` | 0 | `pass: true` |
| `uv run python scripts/check_bundle_identity.py <manifest>` | 0 | 143 checked, 138 identical, 5 allowed changes, 0 violations |
| `uv run --project . pytest tests -q -p no:cacheprovider` | 0 | **191 passed, 4 skipped** |
| `npx tsc --noEmit` | 0 | - |

**Every shipped number equals its source export.** Script over all 68 Q57 comparators against `exports/phase1_nf4_t4/` and `exports/phase1_promptroute_nf4_t4/`: `readout.probs` equal for 68/68, pair `d_margin` equal for 68/68, and **1112 arrays** (40 light runs + 64 slim pairs, every array in each table) byte-identical to the source slice with equal dtype/shape/nbytes. 0 mismatches. Those are the bytes the Cohort rows draw from, so the round-1 item-4e screen check holds on the same data.

**Browser checks on the rebuilt tree** (headless Chrome, `~/.hermes/cache/scratch/rangesrv/srv.py <root> 8871 1000000 range`):

- Cohort harness (`wb7q_cohort/check.mjs`) -> `ALL OK`. At 1440 and 1024 px: default 42 adapter rows in 26 profile blocks, "Country adapters 42" pressed, "Matched pairs" order, layer map 42 rows, horizontal overflow 0, every row 64 px; all 68 rows in 26 blocks with the sign prompt first in each block; toggling adapters<->all 27 to 158 ms; row clicks on USA (light), BGD (full) and `sp101111` (full) land on `tab=c` with the right B; the 24 numbers-only rows say "Cohort only" and do not navigate; guard panels on tabs c, b and a with 0 console and network errors; the guard's Cohort link works in-app.
- Light-run guards (`wb7q_cohort/root_extra.mjs`) -> `ROOT EXTRA OK`. `tab=a` on USA and ARG: the exact card sentence once, 0 canvases, no spinner, no error panel. Pinned head in the Ladder on USA (`sel=16,3`) and ARG (`sel=0,0`): drawer 850 to 852 chars, contains the sentence, 0 errors (the round-1 F1 crash path). Full BGD control on `tab=a` still draws 2 canvases and shows no sentence. Sign-prompt filter: 26 rows, 26 blocks, overflow 0. Story page: `#q57-featured` renders the exact sentence with two adapter links. Errors across all of it: `[]`.

**Number parity, v1.4 -> WB7-Q, 12 pages.** Old side: the v1.4 archive `workbench/dist/deploy_bundle.tar.gz` (13:48, 918,475,574 B, 143 files) extracted to scratch and served on port 8872; new side: this rebuild on 8871. Token multiset per page, DOM text walk that skips `<select>` (picker labels compared separately) and does not depend on rendering, so `content-visibility:auto` rows still count.

| Page | Old tokens | New tokens | New minus old |
|---|---|---|---|
| `/` (landing) | 221 | 221 | **none** |
| `/?tab=c` (Ladder) | 45 | 45 | **none** |
| `/?tab=b` (Matrix) | 25 | 25 | **none** |
| `/?tab=a` (Object) | 31 | 31 | **none** |
| `/sca2/index.html` (story) | 1026 | 1027 | `57` +1 (the new Q57 featured line) |
| `/?tab=k` for Q43, Q50, Q81, Q99, Q106, Q176 | 70 | 73 | `1`+4, `2`+1, `4`-1, `68`+1, `110111`-1, `111111`-1 — identical on all six |
| `/?tab=k&item=wvs_Q57` | 70 | 327 | the 40 new adapter rows, the 24 sign-prompt rows, the filter counts and the group headers |

The six non-Q57 Cohort differences are structural, not data, and each was traced:
- `4`-1 / `68`+1: the question picker's comparator count for "Can people be trusted?" went 4 -> 68, which is what this card ships.
- `1`+4 / `2`+1: the filter labels changed from "Both 4" to the three named filters ("Country adapters 2", "Sign prompts 2", "All comparators 4").
- `110111`-1 / `111111`-1: the six-bit code moved from a per-row label to the block header, so it prints once per profile instead of twice. Checked row by row on Q43: both sides have the same 4 rows, the same percentages and the same `+0.742 / +14.6 / +0.266 / +6.72`.

No percentage, log-odds change or probability on any v1.4 page changed.

**Screenshots** (`~/.hermes/cache/scratch/wb7/q57/shots/`, 2.0 MB, taken from this rebuild at HEAD): `cohort_q57_adapters_pairs_{1440,1024}.png`, `cohort_q57_all_pairs_{1440,1024}.png`, `cohort_q57_all_size_{1440,1024}.png`, `cohort_q57_sign_prompts_1440.png`, `light_3d_guard_{usa,arg}.png`, `light_ladder_pin_{usa,arg}.png`, `guard_ladder_numbers_only_1440.png`, `story_q57_featured_1440.png`. Inspected by eye: the Cohort default is readable at 1440 (26 profile blocks, one code per block, dumbbells with exact percentages), the light 3D tab shows only the sentence card, and the story line sits above the featured table with both adapter links.

**Servers:** both `srv.py` instances (8871 new, 8872 old) were stopped at the end of this round.

**Not done by this card, on purpose:** no push, no deploy, no `HF_TOKEN`, no `git add -A`. `workbench/analysis/` (W3b) and the untracked `viewer/screens/sca2/{verified,wb31v,wb3v,wb4v}/` verifier scratch were left untouched.

**Open notes carried forward:** N5 ("A (base)" is still the A-selector label on the Ladder, Matrix and 3D tabs; copy, owned by the `wb7-words` branch) and N11 (the pinned-head "size of change" cell is blank on light comparators where `d_head_norm` is not shipped; a three-word label would be clearer). Neither blocks WB7-H, WB7-I or the deploy decision.
