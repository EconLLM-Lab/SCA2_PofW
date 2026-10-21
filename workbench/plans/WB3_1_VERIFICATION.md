# WB3.1-V independent verification (task t_42d33a08)

Verifier: profile `verifier`, model `claude-sonnet-5-5` (provider anthropic). Producer: `gpt-5.6-sol` / openai-codex (WB3.1, task t_04ac8789). Different family.
Branch `Adapter-Brain-Vizualization`, verified head `67200cec691ee49956d30c6d6e3e6cf1de6ef380` (parent `2309ab0`). Date 2026-10-20 (MST). Nothing deployed, committed, pushed, or edited in producer files.
Evidence: `workbench/viewer/screens/sca2/wb31v/` (scripts, logs, `wb31v-browser.json`, `c9_check.json`, screenshots). Absolute paths in copies are replaced by `<SCRATCH>`, `<MAIN>`, `<HOME>`.

## OVERALL: PASS (with 4 non-blocking notes, N1-N4)

Every item on the card passes. Data is untouched, the rebuild matches the producer file by file, every number in step 4 equals `NUMBERS_TABLE.csv`, the five fixes are present, and the trim only dropped the declared featured prompt pairs. N1 is the one for Augusto: the message survives projection, but the supporting text is small.

## Result table (all exits read directly, no pipes)

| # | Gate | Command / method | Result |
|---|---|---|---|
| 1 | Story JSON byte-identical to WB3 | `git diff --exit-code 2309ab0 HEAD -- workbench/viewer/public/sca2/sca2_data.json`; `shasum -a 256` of the working file and of `git show 2309ab0:...` | diff exit 0. Both sha256 `16068182617aa623bc10d3fceaae6373f1ec32311b4f24ed2ccee47dbc058584`. The working file has no uncommitted change |
| 2 | Fresh rebuild | `git archive HEAD workbench` into a fresh scratch dir; APFS-cloned gitignored `exports/` and `node_modules/`; copied the 4 gitignored PNGs (`screens/v3/*`); `env -u PYTHONPATH HF_TOKEN= uv run --project workbench python workbench/scripts/build_deploy_bundle.py --out <SCRATCH>/out/deploy_bundle.tar.gz`. Scratch-only one-line patch of `SCRATCH` (`logs/scratch_patch.diff`) | exit 0. 142 files, payload 918,377,325 B, archive 732,597,608 B |
| 3 | Manifest compare vs producer sidecar | `scripts/cmp_manifest.py` | exit 0. 142 vs 142 files, 0 only-in-either, **0 per-file (sha256, bytes) mismatches**, payload bytes equal. Only the gzip framing differs (archive sha producer `f1af0217...`, mine `31fce5c6...`; 219 B), as in WB1-V and WB3-V |
| 4 | Own closure/hash check | `scripts/check_bundle.py` | exit 0. 142/142 hashes match, 0 extra, 0 missing, archive sha equals my manifest, all members regular files, no `..` or absolute names. 37 runs, 29 pairs, 22 models, closure missing = [] |
| 5 | Storage cap | manifest | Payload 918,377,325 and archive 732,597,608 are both below 950,000,000 (96.7% and 77.1%). The PM's 1 GB Space ceiling is respected |
| 6 | Trim check (PM comment) | own script against the three source indexes named in the manifest, run in the scratch build | See the trim section below. PASS |
| 7 | Numbers vs NUMBERS_TABLE by claim_id | `scripts/c9_check.py` on the **rendered DOM** of my own rebuild (`wb31v-browser.json`) vs `NUMBERS_TABLE.csv` in the main repo | exit 0. **354 checks, 0 failures**, at 1440 and 1700. Covers: 3 summaries, 4 TVD cells, 6 forest rows (printed text `0.045 [0.006, 0.093]` and exact `data-value`/`data-lo`/`data-hi` floats), 6 forest **tooltips** (e.g. `adapter − base: 0.045 [0.006, 0.093]`), 2 mean markers (value, title, position), 84 country dots vs `c9_label_recovery.csv`, 14 C9 claim records and the 30-entry `claims` block vs the table |
| 8 | No stray numbers | regex of every numeral in the rendered `#c9` text | Beyond the table values the only numerals are axis ticks `0`, `0.5`, `1`, the section number `4`, `42` countries, `26` sign profiles (= `len(D.profiles)`), `95%`. No per-country TVD, no human mean or distribution (text hits for "respondent" are the title, takeaway, caveat and polarity cue; "human means or distributions" appears only in the existing disclaimer "no respondent rows, country-level TVD, human means or distributions") |
| 9 | Mean markers are means | recomputed mean of the 42 country dots vs table | recovery 0.9398 = 0.9398, accuracy 0.8162 = 0.8162. The marker is the unweighted country mean, so the label "mean" is accurate. The source CSV has 3 blank rows per column, excluded as in WB3 |
| 10 | Routes and console | `scripts/wb31v_browser.mjs` (my WB3-V harness, adapted to the new DOM; system Chrome; plain `http.server`, `/nonexistent` returns 404) at 1440x860 and 1700x1000 | exit 0. 52 checks, 0 failed. **0 console errors/warnings, 0 pageerrors, 0 requestfailed, 0 non-200/304 responses (397 responses)** |
| 11 | Routes covered | same | `/`, `/sca2/index.html` at both sizes with all 4 cohort and 2 cross-talk route selectors switched, tabs a/b/c/k at both sizes, and **28 featured links** (16 adapter + 12 sign-prompt): each lands on A = base, B = the link's model, the link's item, tab Ladder, no failbar, with at least one run/pair JSON and one `.bin` all 200/304. 4 more slots are labelled `<CC>: omitted from compact bundle` (GRC, NGA, IRN, USA); all 16 slots resolved (`data-ready`), none left at "checking compact bundle…". No horizontal overflow at either size |
| 12 | Suite | `env -u PYTHONPATH HF_TOKEN= PYTHONDONTWRITEBYTECODE=1 uv run --project workbench pytest workbench/tests -q -p no:cacheprovider` in the live tree at `67200ce`; `git status --short` hash identical before and after | exit 0. **180 passed, 4 skipped, 3 warnings** in 25.3 s. Equals the producer's number. The only tracked modification in the tree is `workbench/analysis/w3b/run_w3b.py` (outside `workbench/tests`) |

## The five fixes (DOM-checked at both viewports, `struct` in `wb31v-browser.json`)

1. Polarity cue in the right panel title: `<h3>` reads `Mean TVD to respondent distributions lower = closer to respondents`. The left panel's title carries `higher = better`, so the two opposite polarities are both stated where the reader looks first. PRESENT.
2. Factor headers on the 2x2: column headers `no persona` / `persona`, row headers `no adapter` / `adapter`. The cells map correctly (Base = no/no, Persona = no adapter/persona, Adapter = adapter/no persona, Adapter + persona = adapter/persona). The farthest cell is chosen at render time from the JSON (`data-farthest` = `adapter`, 0.515). PRESENT.
3. Strips: both tracks use the same 0-1 scale, with one shared axis (`0`, `0.5 chance`, `1`). A dashed chance line is drawn on each track (`::after`, dashed, `left:50%`). A mean marker is on each track (recovery 0.940, accuracy 0.816, from the JSON summaries). PRESENT.
4. Takeaway promoted: `<p class="c9-takeaway">Label fidelity is not agreement with respondents.</p>` sits directly after the section heading (16px, bold, blue rule). The old bottom `figcaption` is gone (`figcaption: null`). PRESENT.
5. Forest plot: six rows, each with a point, a profile-block 95% interval and a vertical zero line (`.forest-zero`, 6/6 rows); excludes-zero and crosses-zero are distinguished (blue and grey). "Interaction" is defined in the visible note under the plot: `Interaction = (adapter + persona − persona) − (adapter − base).` PRESENT.

## Trim check (PM comment)

- The only prompt-route pairs missing from the bundle versus the source indexes are four: GRC and NGA on `wvs_Q106` (risktaking) and IRN and USA on `wvs_Q50` (patience). They are exactly the two rows listed in the manifest as `prompt_features_dropped`. They are featured capture pairs, not cohort, bank or adapter units.
- Per sign bit, a complete adapter + sign-prompt pair remains: trust 1 row (BGD/CHN, both prompts shipped), risktaking 1 (CHN/USA `wvs_Q99`), patience 1 (IRN/CAN `wvs_Q43`), altruism 1 (THA/EGY `wvs_Q99`), posrecip 1 (GBR/USA `wvs_Q81`), negrecip 1 (PHL/USA `wvs_Q176`). All 8 featured rows keep both adapter pairs (16/16 adapter links load).
- Size accounting: dropped pair and run files = 16 files, 135,099,630 B in the source exports. The payload falls from WB3's 1,053,474,200 (`bundle-check-wb3.json`) to 918,377,325, a drop of 135,096,875. The 2,755 B residual equals +7,449 B for the larger story HTML (measured) minus the smaller `index.json`. I did not hash the old `index.json`, so that last split is inferred, not measured. Counts agree: WB3 had 158 files, 41 runs, 33 pairs, 74 capture manifests; WB3.1 has 142, 37, 29, 66, a loss of exactly 16 files, 4 runs, 4 pairs, 8 manifests.
- Story JSON byte-identical to `2309ab0`: see gate 1.

## Visual judgement of the 1440 screenshot (`screens/c9-1440.png`, my own rebuild; the producer's `wb3_1/c9-1440.png` shows the same layout)

I read the image with the vision tool, since I cannot view it directly. Two reads, one of the producer's PNG and one of mine, agree.

- Legible at 1440: the section heading (22px), the takeaway (16px bold on a lighter bar, the clearest element after the heading), both panel titles (16px), the four TVD numbers (14px bold) and the left-panel metrics. Both polarity cues are in the titles. The 2x2 headers, forest rows, strips and mean triangles read cleanly. No overlap and no clipping inside step 4. Step 5 begins at the bottom edge of the capture, which is normal scrolling.
- Message without footnotes: yes. Takeaway plus the left panel (recovery 0.940, accuracy 0.816, base 0.489 "at chance") plus the right panel (Adapter 0.515 tagged "farthest", worse than Base 0.470; Persona 0.365 nearest) gives "labels learned, but not closer to respondents". The interaction definition is a footnote, but the nuance (interaction near zero, interval crosses 0) does not carry the message.
- Computed font sizes in step 4 (`fonts` in the evidence): polarity cue 12px, panel subtitle 12px, cell label 12px, forest label, value and note 11px, strip axis 11px, factor headers 11px, badge 11px; the "farthest" tag and forest axis are 10px. The tick labels are monospace at 10-11px.

## Notes (non-blocking; each with evidence)

N1. Projection legibility is marginal for the supporting text (decision for Augusto or the PM; not made here). Every element that carries the argument is readable, but the scaffolding (polarity cues 12px, factor headers 11px, forest rows 11px, the "farthest" tag 10px, footnote 11px) will be hard to read from the back of a room. The message survives because the takeaway, the four TVD numbers and the two titles are large enough. Suggested follow-up if the deck is projected: raise the polarity cues, factor headers, "farthest" tag and forest labels to at least 14px and give the forest plot more width. Not blocked, because the card asks that the message be visible without the footnotes, and it is. The card does not set a pixel floor.

N2. The 42 recovery dots form one blob near 0.94-1.0 in the recovery strip (overplotted at 7px, no jitter). This is a property of the data and not new, but it makes the strip read as a bar. The mean marker is the readable part. Cosmetic.

N3. Docs vs code, surfaced and not resolved: `workbench/README.md:54` still says the shipped bundle was "built from `e86d4c2`" and line 59 gives the deploy as 2026-10-19 from `e86d4c2`. That was the WB2 deploy, and the WB3 deploy receipt is separate. The producer flagged the same thing. Separately, `build_deploy_bundle.py:23` still hard-codes `~/.hermes/profiles/engineer/cache/scratch/wb1` (WB1-V F4, WB3-V N3, unfixed). New this round: if `SCRATCH` is under a symlinked path (macOS `$TMPDIR` is `/var/folders/...`, a symlink to `/private/var`), the build fails with `Symlink dependency` at `build_deploy_bundle.py:115` (`source.resolve() != source.absolute()`), exit non-zero. I worked around it by using the resolved `/private/var/...` path in my scratch copy. The check is a deliberate security guard; the point is that the script needs a resolved scratch path.

N4. The deploy needs this worktree or an equivalent. The bundle includes 4 gitignored PNGs (`screens/v3/*`) and gitignored `exports/` and `node_modules/`, so a pure clone cannot rebuild it (same as WB3-V). The PM should deploy from this worktree's `workbench/dist/deploy_bundle.tar.gz` (archive sha `f1af0217...`, verified to have the same per-file hashes as my rebuild) or rebuild there.

## Not verified / limits

- `.bin` arrays were decoded for neither hidden content nor values; only manifests, names, sizes and bounds were checked (same limit as WB1-V and WB3-V).
- Chrome only: no Safari, Firefox or mobile viewport. Legibility was judged from a 1440 screenshot read by a vision model, not on a real projector.
- The old `index.json` split of the 2,755 B size residual is inferred (see trim check).
- The deployed Space was not touched or compared.
- I did not re-run the producer's browser harness or its 324-check script; I used my own harness and checker on my own rebuild.

## Route

Verifier ran on `claude-sonnet-5-5` via anthropic. The profile note's codex routing was not what this run used. Independence: not the Codex producer.
