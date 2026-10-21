# WB5-V independent verification (task t_4da518a4)

Verifier: profile `verifier`, model `deepseek/deepseek-v4.1-flash-1017` (provider openrouter) — the route this run actually used (session header and the card's `model_override`), not the Codex seat the roster assumes. Producer: orchestrator `default` (Claude), a different model family. Branch `Adapter-Brain-Vizualization`, verified head `fa04992ddc184df875d87468e41e506508b83bf2`. Date 2026-10-21 (MST). Nothing was pushed, deployed or edited: the only file written inside the project is this report; all harnesses, servers, builds and extractions live in `/Users/bonorinoa/.hermes/profiles/verifier/cache/scratch/wb5v` (`$S` below).

**The Space was already redeployed with this build before verification** (operator note, and independently confirmed here: the live `assets/index-DTZPCO_y.js` is byte-identical to my rebuild — sha256 `71fa16777d5f10b80d4fcdefb9094af75e3de0937ddf627795c845ec3d3a6b7`, and the live `index.html` differs from the bundle's only by Hugging Face's injected `window.huggingface` script and `og:`/`twitter:` meta tags). So card item 5 applies and was run.

## OVERALL: PASS (with 5 non-blocking notes, N1-N5)

Every card item passes: the code review found no correctness defect in offsets, reassembly, typed-array construction, the 206 check, the 200 fallback or cache versioning; a fresh rebuild is per-file identical to the producer's; the suite and `tsc` pass; text parity holds on 34 URLs against the v1.2.2 viewer with both a Range server and a Range-ignoring server; and the live Space reproduces the intended numbers with `.bin` requests all 206 and reloads issuing none. The failure path degrades safely in a server that 500s the heavy ranges (item 1's "never a silently wrong number" clause, tested rather than argued).

## Result table (every exit read directly, never through a pipe)

| # | Gate | Command / method | Result |
|---|---|---|---|
| 1 | Fresh rebuild from `fa04992` | `env -u PYTHONPATH HF_TOKEN= SCA2_BUNDLE_SCRATCH=$S/stage uv run --project workbench python workbench/scripts/build_deploy_bundle.py --out $S/deploy_bundle.tar.gz` | exit 0 (`$S/build.log`). **143 files**, payload **918,433,342** bytes, archive 732,636,858 bytes, archive sha `eee145bb…` |
| 1b | `verify_bundle.py` on an independent extraction | `env -u PYTHONPATH python3 viewer/screens/sca2/verify_bundle.py $S/deploy_bundle.tar.gz $S/site --report $S/verify-report.json` | exit 0. `pass: true`, **143 files, 37 runs, 29 pairs, 66 capture manifests** (`$S/verify-report.json`) |
| 1c | Rebuild vs the producer's own build of the same commit (`workbench/dist/deploy_bundle.tar.manifest.json`, archive `cdc1d0e6…`, the archive now deployed) | per-file sha256 comparison, `$S/deploy_bundle.tar.manifest.json` | **143/143 files identical, 0 mismatches, 0 files only-in-one**; 133/133 `exports/` identical; `payload_bytes`, `source_indexes`, `story_sources`, `prompt_features_kept/dropped` and `selection_rule` equal. Archive bytes differ (732,636,858 vs 732,636,699) and archive sha differs — gzip framing only, as WB4-V N3 already established |
| 1d | `exports/` byte-identical to the v1.2.2 build | `git diff --name-only 3c68a82 fa04992`; builder source | **7 files changed, none under `workbench/exports/` or `workbench/viewer/public/`**; `exports/` is untracked and the builder copies it verbatim under sha256 (it refuses symlinked inputs — hit twice while building the old bundle). Both commits' builds therefore ship the same 133 data files from the same directory; my rebuild's 133 `exports/` hashes equal the deployed manifest's. I did not build a second full v1.2.2 archive for a literal manifest-to-manifest diff: the builder refuses symlinked inputs, and a plain copy of `exports/` inside the scratch tree pulled 22 GB through the export folder's own symlinks before I aborted it. The structural argument above is exactly what that diff would test |
| 2 | Suite | `env -u PYTHONPATH HF_TOKEN= uv run --project . pytest tests -q` | exit 0. **183 passed, 4 skipped** in 38.81 s (`$S/pytest.log`) — matches the card |
| 2b | TypeScript | `./viewer/node_modules/.bin/tsc --noEmit -p viewer` | exit 0, 0 lines of output |
| 3 | Parity, Range server (new `$S/srv.py`, no throttle, `no-store`) | `node parity.mjs <old 5842> <new 5841> …` (`$S/parity_run.log`, `$S/parity_new_vs_old/parity.json`) | exit 0. **34/34 URLs identical text**: landing, `?tab=c`, `?tab=b`, `?tab=a`, `?tab=k`, **28 `a[data-featured]` links**, `?tab=c&sel=20,7`. 0 console errors, 0 page errors, 0 failed requests, 0 responses outside {200,206,304}. All **847** `.bin` requests on this server were **206**; the old viewer made 299 `.bin` requests, all 200 (whole files) |
| 3b | Parity, server that ignores Range (port 5843, same harness) | `$S/norange_run.log` | exit 0. **34/34 identical**, 0 console/page errors. **154/154** `.bin` responses were 200 — the whole-file fallback path, with identical page text |
| 4 | Live Space, public origin, fresh profile | `node live.mjs https://econllm-sca2-workbench.static.hf.space …` ($S/live_run/live.json) and `node live_probe.mjs …` ($S/live_probe/live_probe.json) | see the live table below. 0 console errors, 0 page errors, 0 non-2xx/3xx |
| 5 | Failure path: heavy ranges of run A return 500, core ranges served (`$S/srv_fail.py`) | `node fail.mjs http://127.0.0.1:5846 …` ($S/fail_run/fail.json) | `?tab=a` → `.loadfail` panel with `Error: … HTTP 500`, no figure on the page, `__ready = "error: …"`; `?tab=c&sel=20,7` → page draws (2 svg), drawer keeps "attention weights are still loading", **0 attention rows**, console `attention arrays failed to load: Error: run__…__wvs_Q43.bin: HTTP 500`; landing unaffected, 0 console errors |

## Live check (item 5)

Cold profile, one Chrome, the same sequence the PM ran (mine, not theirs):

| Step | ready | `.bin` requests | notes |
|---|---|---|---|
| landing, cold (probe session) | **5.71 s** (wall 6.60 s) | **7, all 206** | one probe session, cleanest measure |
| landing, cold (sequence session) | 10.76 s (wall 12.17 s) | 7 fetch calls (14 request events: Chrome counts the CDN redirect hop too) | network variance, see N5 |
| landing, reload | **0.339 s** | **0** | same in both sessions (0.305 s / 0 in the other) |
| `?tab=c` | 0.306 s | 40 ranges start *after* ready | deferred heavy load, see N1 |
| `?tab=b` | 0.251 s | 40 ranges | heavy restarted (previous page aborted mid-flight) |
| `?tab=k` | 5.71 s | 6, all 206 | different (cohort) pair |
| `?tab=c&sel=20,7` | 0.308 s, placeholder present | 40, all 206 | **attention panel filled at 84.4 s** with real weights (`0.88 · #0 "<|begin_of_text|>" / 0.03 · #138 …`) |
| `?tab=a` | 4.77 s | 0 | heavy already cached by the previous step |

- Cache API after the cold visit: one cache `sca2-ranges-v1`, **7 entries**, every key of the form `/__sca2-range/<64 hex>/<bin>/<start>-<end>`, and the three distinct hex strings **equal the sha256 of the corresponding manifest text** (`cd8e939b…` = `run__…_can__wvs_Q43.json`, `c6c49330…` = the pair, `3c31a300…` = `run__…__wvs_Q43.json` — computed locally, 3/3 match).
- Cross-origin `Range` through the Hub redirect: **206**, `content-range: bytes 0-1023/226688` **readable from the page**, `accept-ranges: bytes`, final URL on `cdn.hf.co`. So the `Content-Range` check in `data.ts` is live, not skipped.

## Code review (item 1), against the diff `3c68a82..fa04992 -- workbench/viewer`

- **Byte offsets and typed arrays.** Independent audit of every shipped manifest (65 files, **1075 arrays**): `nbytes == itemsize(dtype) * prod(shape)`, offsets strictly increasing, non-overlapping, inside the `.bin`, and dtype-aligned. **0 problems.** Only `float32` and `uint16` occur, the two the code handles.
- **Chunk reassembly.** Arrays are sorted by offset, merged when the gap is ≤ 64 KB, and any span > 2 MB is cut into aligned 2 MB pieces fetched with `Promise.all` and refilled in order into one `Uint8Array`; each array is then copied out with `ArrayBuffer.prototype.slice` before `new Uint16Array/Float32Array(own, 0, n)`, so element alignment is always 0 and a mis-shaped piece would throw the `byteLength !== nbytes` check. Correct.
- **206 path.** `Content-Range` is parsed and compared with the requested window when the header is visible; the length check (`buf.byteLength !== want`) runs after both branches, so a short/over-long answer always throws. Verified live that the header is readable cross-origin.
- **200 fallback.** The whole file is kept in a per-page `Map` and sliced; on the Range-ignoring server all 34 URLs render identically with 154 whole-file responses. Correct.
- **Cache key versioning.** The key contains `sha256(manifest text)` and the bin name and the exact byte window; the whole file is refetched whenever the manifest text changes. Empirically: keys match the manifest sha (3/3). A changed export writes a new manifest, so a stale entry cannot be hit through the normal pipeline. Residual gap is N2.
- **Error paths.** The heavy fetch failure on tab c/b is caught and logged (`attention arrays failed to load: …`), the head drawer keeps its "still loading" sentence and `topKeys`/the top-16 row are guarded, so no wrong attention number is rendered; on tab a the failure reaches the existing `.loadfail` panel. Tested with a real 500 server (gate 5), not inferred.
- Correctness of `clientCheck`: it reads only `head_attr`, `neuron_attr`, `attn_attr` and the readout, none of which is deferred, so the landing checks table is unchanged — confirmed by the 34/34 parity.

## Notes (non-blocking)

**N1. Tab switches restart an unfinished heavy download.** Each navigation aborts in-flight ranges and only completed ranges are cached, so c → b → c before the ~40 MB heavy load finishes re-issues ~40 ranges each time. Observed live (40, 40, 40 on tab c, tab b and the pinned view). Consequence: the pinned head took **84.4 s** to fill on the public CDN here (the PM measured 42.6 s), and the PM's "tab c: none" line is only true if the deferred heavy fetch is excluded from the count — mine fired 40 ranges after `ready`, all 206.

**N2. The cache is bonded to the manifest, not to the bin bytes.** A `.bin` rewritten while its manifest text stays byte-identical would be served from cache. No path in `build_deploy_bundle.py` can produce that (bin and manifest are copied together with sha256, and the builder validates array bounds), so this is a theoretical gap, not an observed one; a `sha256` of the bin in the manifest would close it.

**N3. If `Content-Range` were not exposed, the offset check silently degrades** to the length check. On HF's CDN it is exposed (measured), so the check is active today; a server that hides it would still be caught by the byte count but not by offsets.

**N4. Cosmetic: a transient "Σ attention 0.00" and an unused export.** While the heavy arrays are missing, a *pinned* head's prompt button shows `Σ attention 0.00` (all weights are 0 because `topKeys` returns early) until `sca2:heavy` fires; the drawer correctly says "still loading", so it is momentary and self-correcting, but it is a number on screen. `hasHeavy` is exported from `data.ts` and used nowhere.

**N5. Two cold landing sessions gave 5.7 s / 10.8 s.** Same origin, fresh profiles, minutes apart (the second is CDN variance; the 14 vs 7 request-event difference in the first session is Chrome counting the redirect hop, not a duplicate fetch — the page-side fetch counter showed 7 calls). Neither run reproduced the PM's exact 7.3 s; the shape of the result (a few seconds cold, sub-second on reload) is reproduced.

## Not verified / limits

- Chrome only, headless, one viewport (1440x860); parity is text equality, not pixel equality.
- The local servers are mine (`$S/srv.py`, `$S/srv_fail.py`), not the PM's `rangesrv/srv.py`; both are Python `ThreadingHTTPServer` with `no-store`, the local ones unthrottled (timings come from the live site).
- Live timing is a single cold session per step; no repeat runs, so the numbers carry CDN variance (see N5).
- I did not read the `EconLLM/sca2-workbench` README ("v1.3"): the repo is private and the rules forbid loading `HF_TOKEN`. Deployment is established instead by the live asset sha matching my rebuild and by the operator note.
- `.bin` payload was not decoded for hidden content (per-file sha256 and array bounds were checked).

## Evidence map

`$S` = `/Users/bonorinoa/.hermes/profiles/verifier/cache/scratch/wb5v`

| file | what |
|---|---|
| `build.log`, `deploy_bundle.tar.manifest.json`, `verify.log`, `verify-report.json` | rebuild (143 files, 918,433,342 B) and independent read-back |
| `site/` | verified extraction used for every local browser run |
| `oldview/`, `oldsite/` | v1.2.2 viewer built from `3c68a82` (`tsc` exit 0, `vite` exit 0, asset `index-DOV5IqPz.js`, 0 occurrences of `sca2-ranges-v1`) sharing the same byte-identical `exports/` |
| `parity_run.log`, `parity_new_vs_old/parity.json` | 34-URL parity, Range server |
| `norange_run.log`, `parity_norange/parity.json` | 34-URL parity, server that ignores Range |
| `fail_run/fail.json`, `req_fail.jsonl` | 500-on-heavy failure path |
| `live_run.log`, `live_run/live.json` | live sequence: landing, reload, tabs c/b/k, pinned, tab a |
| `live_probe.log`, `live_probe/live_probe.json` | live cold landing, reload, Cache API keys, cross-origin 206 probe |
| `pytest.log`, `tsc` (exit 0) | suite 183 passed / 4 skipped |
| `req_new.jsonl`, `req_old.jsonl`, `req_norange.jsonl` | server-side request logs (847 × 206 / 299 × 200 / 154 × 200) |
