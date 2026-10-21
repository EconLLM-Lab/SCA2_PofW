# WB6-V independent verification (task t_fb8b00a6)

Verifier: profile `verifier`, model `deepseek/deepseek-v4.1-flash-1017` (provider openrouter) — the route this run actually used (session header and the card's `model_override`), not the Codex seat the roster assumes. Producers were Claude: the PM (`default`), plus Sonnet 5.5 on `creative` and `writer`. Branch `Adapter-Brain-Vizualization`, verified head **`0b7d4db`**; the branch moved one commit to **`9965fdb`** while this verification was running, and that commit fixes the one defect found here (F1). Nothing was pushed, deployed or edited: the only file I wrote inside the project is this report (plus the builder's own `viewer/dist` and `workbench/dist` output, which the card's prescribed command produces); all harnesses, servers, builds and extractions live in `/Users/bonorinoa/.hermes/kanban/boards/sca2-paper-b/workspaces/t_fb8b00a6/wb6v` (`$S` below).

## OVERALL: PASS-WITH-NOTES

Every gate the card names passes at `9965fdb`; at `0b7d4db` one gate failed narrowly and one number was wrong on screen (F1, fixed in `9965fdb`). No data file changed, no test failed, `tsc` is clean, the Cohort tab is fully traceable to `exports/index.json`, the plain-language pass changes no Paper B claim and drops no hedge, and all five loading/queue behaviours hold on a throttled Range server. Notes N1–N8 below are non-blocking; N1 (a spec collision) and N5 (a stale help popup) are the two a reader will actually notice.

| # | Gate | Command / method | Result |
|---|---|---|---|
| 1 | Fresh rebuild from `0b7d4db` | `cd workbench && env -u PYTHONPATH HF_TOKEN= uv run --project . python scripts/build_deploy_bundle.py --out $S/b.tar.gz` | exit 0. **143 files**, payload **918,475,014** bytes, archive 732,636,860 bytes, archive sha `9e7fa427a3712a3cccb…` |
| 1b | `verify_bundle.py` | `env -u PYTHONPATH python3 viewer/screens/sca2/verify_bundle.py …` | exit 0. `pass: true`, **143 files, 37 runs, 29 pairs, 66 capture manifests** (`$S/verify-report.json`) |
| 1c | Rebuild vs the PM's own build of the same commit | per-file sha256 against `workbench/dist/deploy_bundle.tar.manifest.json` (archive sha `fe49514ff2a8…`) | **143/143 identical, 0 mismatches, 0 only-in-one; 133/133 `exports/` identical.** Archive sha differs — gzip framing only (WB5-V N2, unchanged) |
| 1d | `exports/` vs the v1.3 build, built here from `fa04992` | `git worktree` at `fa04992`, same builder → `$S/b13.tar.gz` (143 files, payload **918,433,342** = WB5-V's figure) | **133/133 `exports/` byte-identical.** Differing files: `index.html`, `assets/*` (2 renamed), and **`sca2/index.html`** — see N1 |
| 2 | Suite | `env -u PYTHONPATH HF_TOKEN= uv run --project . pytest tests -q` | exit 0. **183 passed, 4 skipped** (`$S/pytest.out`) |
| 2b | TypeScript | `./viewer/node_modules/.bin/tsc --noEmit -p viewer` | exit 0, no output |
| 3 | Number parity vs v1.3 (`fa04992` served on :8802/:8803, v1.4 on :8801) | own puppeteer harness, token regex `[-+\u2212]?\d[\d,.]*%?` on visible text minus `<select>` options | landing **190/190 visible tokens identical** (198/198 including option lists), story **699/699** (707/707 with options); `?tab=c`, `?tab=b`, `?tab=a` each lose exactly **3 tokens — {3.1 ×1, 4 ×2}** (47→44, 28→25, 34→31) and gain nothing; all three sit in the archive-check element's tooltip: `Weights: nf4_dequant · archive check 3.1 ulp (≤4; report only)` |
| 3b | Pop-up sizes | `?learn=<key>` on `?tab=c` (Llama) and on `?tab=c&a=smol_inst&b=smol_inst_usa_e3&item=wvs_Q81` | `head`, `norm`, `mlp`, `howto-c`, `resid` and the glossary agree with each run manifest's `model` (`runs[].model`): Llama **4,096 / 14,336 / 32 heads / 8 key-value groups / 32 layers**, Smol **576 / 1,536 / 9 / 3 / 30**. The glossary `layer` entry was **wrong at `0b7d4db`** (F1); fixed and re-checked at `9965fdb` |
| 4 | Cohort tab, every number traced to data | DOM dump of 7 questions × 4 states (`$S/cohort_dom.json`) vs values recomputed from `exports/index.json` (`$S/cohort_expected.json`) | **84/84 row comparisons exact**: probability pair, log-odds change, "Most likely answer" pair, filter labels and counts, both sorts, group sentences. **0 mismatches** (`$S/cohort_compare2.py`, exit 0) |
| 5 | Claims | `git diff fa04992 0b7d4db -- workbench/viewer/public/sca2/index.html` (21 changed lines, `$S/story.diff`) read sentence by sentence against `planning/TWO_PAPER_CLAIM_LOCK.md` §C7/C9 | **No claim strengthened, none weakened, no hedge dropped.** Every added clause is a gloss; every hedge is retained verbatim (details below) |
| 6 | Loading and queue, 1 MB/s per connection, local Range server | `$S/loading.mjs` (boot / cache / abort / ignore / fail), `$S/abortreuse.mjs`, `$S/interactive.mjs`, `$S/failprobe.mjs` | all pass; see the table below |
| 7 | Live Space | skipped on instruction: `workbench/README.md:63` still says **"The current deploy is v1.3, 2026-10-21, from `fa04992`"**. The Space does not claim v1.4 |

## Findings

**F1 (real defect at `0b7d4db`, fixed at `9965fdb`; the fix was re-verified).** The glossary pop-up's `layer` entry hard-coded *"This model has 30."* on every page. On the Llama page the model has **32** layers (`runs[].model.n_layers = 32`), so the glossary stated a wrong size for the model on screen — check 3's pop-up requirement. Evidence: `$S/pop_llama14.json` (`terms.text`), same string in `$S/pop_smol14.json`, manifest at `site/exports/run__llama31_…__wvs_Q43.json` → `model.n_layers: 32`. Producer commit `9965fdb` reads the count from the manifest (`viewer/src/common.ts:284`, `{n_layers}`). Re-verified on a fresh build of `9965fdb` served on :8806: glossary says **"This model has 32."** on Llama and **"This model has 30."** on Smol (`$S/pop_head_llama.json`, `$S/pop_head_smol.json`).

**N1 — the card's own two gates collide.** Check 1 says only `index.html` and `assets/*` may differ from the v1.3 build; check 5 requires the story-page copy at `viewer/public/sca2/index.html` to change. Both are true: the story page *does* differ (that is WB6-P's work), and the difference is text only — the story page's token multiset is identical between the two builds (707/707), so no number moved. Surfaced, not resolved: which check governs is the PM's call. (The same file is inside the published bundle, so a reader of check 1 alone would score this a finding.)

**N2 — archive sha differs from the PM's `fe49514ff2a8…`** (mine `9e7fa427a371…`) while every one of the 143 files is identical. Gzip framing/mtime, already established in WB5-V N2; `payload_bytes` is equal.

**N3 — one row and its own tooltip print the same quantity at two precisions.** On `?tab=c…&item=wvs_Q43` the Iran row reads `5.8% → 49.8%` while its tooltip reads *"gives “Good thing” a 50% probability"*; its own "Most likely answer" line in the same tooltip reads `50.2%`. Both are correct roundings of 0.49803, and 1 mismatch in 19 distinct tooltip/row combinations (the rest agree), so this is one formatter rounding to whole percent in the tooltip only. Cosmetic, not a wrong number.

**N4 — the Q43 Iran tooltip's "change in log-odds" reads `+6.72`, and the row reads `+6.72`**: consistent. Recorded only because the paired percentage in that same sentence does not follow the row's precision (see N3).

**N5 — the Cohort help pop-up still describes a tab that does not exist.** `?tab=k` → `?` (or `learn=howto-k`) says *"This view **will** put one base model against N adapters … Clicking a row **will** open that adapter as B … It needs one pair export per (base, adapter) … for at least three adapters. **Until those exports exist the tab shows no data.** The thumbnail is an illustration from the design mockup and is badged as such."* The shipped tab shows data on 5 questions and a row click does open the Ladder pair (verified below). Identical text in `0b7d4db` and `9965fdb` (`$S/howtok.log`); `viewer/src/common.ts` `howto-k`. User-facing contradiction between the help text and the tab; `WB6K_ACCEPTANCE.md` does not list a help-text update, so it is out of the card's gates — but it is the first thing a confused reader will click.

**N6 — a warm full reload still paints the loading card for ~200–300 ms.** `$S/load_cache.json`: on `page.goto('/?tab=b')` with 27 warm cache entries the card element is visible at t = 209 ms and t = 313 ms with the pre-download line *"Opening the saved run… Only the first visit downloads this…"* — no numbers, no download — and is gone when the harness reads it after ready. In-app tab switches never paint it (N7). Whether "cached tab switches never show the card" also covers a cold *paint* on reload is a wording call; the card's own copy is correct for that state.

**N7 — in-app cached tab switches never show the card.** Clicking `b → k → a → c → b` with a warm cache: **0 card samples in 5/5 switches**, ready in 439 ms / 440 ms / 32.5 s / 4.2 s / 439 ms, 0 console errors (`$S/interactive.json`). The 32.5 s on the first visit to the 3D object tab is the heavy array fetch behind that tab, not the card.

**N8 — on abort-and-return the four *unfinished* 2 MB ranges are each requested twice.** `$S/abort_reuse.json`: the one chunk that finished before the switch (`…/627760-2724912`) stayed in the cache (7 → 8 entries) and was **not** re-requested, which is the criterion; the four ranges still in flight were re-requested, and each appears twice in the return window (8 requests for 4 ranges) — no in-flight dedupe. Harmless for correctness (the cache key is the range; the second copy lands in the cache too), but it doubles server work on a resume.

## Check 6 in detail (loading card, cache, abort, Range-ignoring server, 500)

Throttled server: `python3 serve2.py site 8804 --throttle 1000000` (1 MB/s per connection). No-Range server: `serve2.py site 8805 --ignore-range`. Fault server: `serve2.py site 8807 --fail-attn` (500 on every 206 that overlaps an attention array of the run manifest).

| Behaviour | Evidence | Result |
|---|---|---|
| Boot card shows real numbers that only increase | `$S/load_boot.json`: 44 distinct samples, `0.2 of 5.7 MB · 2%` → `5.7 of 5.7 MB · 99%`, monotone (checked numerically), ready at **9,244 ms** at 1 MB/s, 7 × 206 + 4 × 200, 0 console errors | **pass** |
| Card disappears at ready | same file: `cardAtReady: null`, `cardAfterReady: null` | **pass** |
| Cached tab switches never show the card | `$S/interactive.json` (in-app clicks, warm cache): 0 samples in 5/5 | **pass** (see N6 for the reload paint) |
| Abort and return reuses finished chunks | `$S/abort_reuse.json`: finished chunk cached at t = 5.25 s, cache 7 → 8, survives the switch away and back, its range **not** re-requested; in-flight ranges resumed; page after return renders the same **44/44** tokens as the untroubled baseline | **pass** (see N8) |
| A server that ignores Range renders identically | `$S/load_ignore.json`: 9 responses all **200** (5 with a `Range` header the server ignored), `__ready = true`, 0 console errors, token list **44/44 identical** to the Range-server baseline (`tokens14.json` `tab_c`) | **pass** |
| A 500 on the attention ranges never puts a wrong number on screen | `$S/failprobe2.json`: `__ready = "error: Error: run__…__wvs_Q43.bin: HTTP 500"`, 5 responses ≥ 400, no `#view`, page reads *"This pair could not be loaded, so nothing is shown. … No figure from another pair is left on screen."*; the only digit-like strings on the page are the run id and `500` — **no measurement on screen** | **pass** |

## Check 4 in detail (Cohort, traceable to data)

Source of truth: `exports/index.json` (`runs[].probs`, `pairs[].d_margin`, `models`) and `sca2/sca2_data.json` (`countries[].bits`). Expected values were recomputed independently (`$S/cohort_expected.py`), never read from the viewer.

- **Questions in the picker (5):** `wvs_Q176` (4 comparators), `wvs_Q43` (4), `wvs_Q57` (4), `wvs_Q81` (4), `wvs_Q99` (8) — picker labels and every count match the exports (`$S/cohort_compare2.py`, 4 states per question: both/adapter/prompt filters × matched-pairs/size sorts).
- **Numbers (84 comparisons, 0 mismatches):** followed-answer probability pair (`pBase → pCmp`), the log-odds change (`d_margin`, 3 significant figures), the "Most likely answer" pair with its two percentages (including the top-two case, e.g. `“Don't mind” (50.2%)` on Q43/Iran), the tooltip numbers, and the `a=…&b=…&item=…` Ladder link each row carries.
- **Matched pairs share the six signs:** 8 group sentences on the 5 picker questions ("Same six signs: in the weights (CAN adapter) … +14.6; in words (sign prompt 111111) +0.742"); each group's adapter `bits` equals its sign prompt's code, and each adapter's bits equal its country's `bits` in `sca2/sca2_data.json` — on the 7 dumped questions **16/16 adapter bits equal their country's bits, 12/12 sign-prompt codes equal their own bits, and 12/12 adapter↔prompt pairs agree on all six signs** (recomputed from `site/sca2/sca2_data.json`, `countries[].bits`).
- **The 2 excluded questions:** `wvs_Q50` and `wvs_Q106` are not in the picker; each has **2** comparators (adapter-only, no sign prompt) and each appears in the tab's "Not in the picker: … (only 2 comparators, too few to compare; open in the Ladder →)" line, named by its question text. Their rows still match the exports (4 comparisons each).
- **Filters and sorts:** the three filter buttons carry the right counts (`Both n`, `Country adapters n`, `Sign prompts n`, the count omitted when it is 0), only one is pressed at a time, the row set equals the expected subset, and under `Size of change (log-odds)` the rows are ordered by `|d_margin|` descending (checked per question).
- **Row click opens the right Ladder pair:** clicking the Iran row on Q43 lands on `?tab=c&a=…_45cc5d4b_46079e27&b=…_45cc5d4b_46079e27_irn&item=wvs_Q43` (the Ladder tab is now active and the ladder is drawn), header `change in log-odds +6.72`, `P(“1”) 0.06 → 0.50` — the Iran row's own numbers (`$S/interactive.json`).
- **Wording:** a sweep of the whole tab's rendered text for `say / said / says / representing / stand in / opinion of / thinks / believes` returns **only the WVS question text** ("Generally speaking, would you say that most people can be trusted…"). Model output is always "the model gives … a probability", "the base model", "a comparator", "same six signs"; nothing claims a model speaks for, or represents, a country.

## Check 5 in detail (claims)

`git diff fa04992 0b7d4db -- workbench/viewer/public/sca2/index.html` = 21 changed lines, all of them glosses or column labels (`$S/story.diff`). Sentence by sentence against `TWO_PAPER_CLAIM_LOCK.md` (C7, C8, C9/C9.1):

- Header: *"A descriptive, not preregistered display of Paper B artifacts"* kept, plus *": saved results, not new analysis"*; the non-shipped list kept and glossed (*"no respondent rows, no country-level TVD (total variation distance, defined below), and no human means or distributions"*).
- §1: *"GPS magnitudes are not shipped"* kept; *"The saved 0/1 bits, not continuous GPS values, define membership"* kept; additions are definitions ("a profile is one combination of signs", "countries with the same bits share a profile").
- §2: the *"not evidence of quality, trust specificity, or an anchor bottleneck"* sentence is retained verbatim; *"surfaces are not interchangeable"* retained.
- §3: *"have the expected positive direction **on average**"* retained with its *"does not guarantee that every matched flip has that sign"*; *"Off-own cells measure behavioral cross-talk, not a neural mechanism or causal component attribution. Grouping alone does not establish an anchor bottleneck, especially after an underpowered null"* retained verbatim — exactly the lock's I1/I2 prohibitions.
- §4: `Label fidelity is not agreement with respondents` retained; the TVD definition added (*"zero means they are the same, one means they do not overlap at all"*) is the metric's own definition, not a reading; the forest note keeps the interaction formula and adds what blue/grey means and *"Persona means the base model prompted with the country's name, with no signs"* — consistent with C8's country-named persona arm.
- §5: *"Selection is descriptive"*, *"These are cohort-1 captures, not the bank-2 factorial above"*, *"Direct route Δ … unavailable"* and the *"without pretending either link is a direct adapter → prompt comparison"* hedge all retained; "margins" glossed as "adapter-minus-base log-odds".
- **Nothing strengthened, nothing weakened, no hedge dropped.** One caveat is still absent: the TVD panel does not carry the lock's "this is a different quantity from the rank agreement above" sentence. That is pre-existing (v1.3 ships the same panel text and the same tokens), not a WB6-P regression, and the section's takeaway line ("Label fidelity is not agreement with respondents") carries the distinction.

## What was not done

- Check 7 (live Space) — skipped: the README says v1.3, so the Space does not claim v1.4.
- No re-verification of checks 1–3 at `9965fdb` beyond the build (143 files, payload 918,475,063, +49 bytes = the one edited source string) and the glossary re-check, on the operator's instruction: `9965fdb` touches only `viewer/src/common.ts` (2 lines, `git diff --stat 0b7d4db 9965fdb`), so no data, suite or parity result can move.

## Verdict

**PASS-WITH-NOTES.** Recommend deploying `9965fdb` as v1.4. F1 is fixed and re-verified; N5 (stale `howto-k` help text on the Cohort tab) is worth a one-line follow-up before the public announcement, since it is the tab's own `?` button telling readers the tab is empty.
