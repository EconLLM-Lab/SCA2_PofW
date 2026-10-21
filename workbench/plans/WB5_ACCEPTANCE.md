# WB5 acceptance: range-fetched, browser-cached arrays (producer record, PM, 2026-10-21)

## Problem
On the public Space every view loaded slowly, not only the first one. The Hub serves each `.bin` file through a
302 redirect marked `cache-control: no-store`, with a freshly signed CDN URL, so the browser never reuses a download.
The old viewer fetched whole run files: about 45 MB for the default Llama pair, at roughly 0.5 to 1 MB/s.

## Change (viewer only; no export, no builder, no data file changed)
- `viewer/src/data.ts`
  - The viewer fetches only the byte ranges it needs (HTTP `Range`). Arrays less than 64 KB apart share one request,
    and spans over 2 MB are split into parallel 2 MB requests.
  - Each range is stored in the Cache API (`sca2-ranges-v1`). The key contains the SHA-256 of the manifest text, so a
    changed export cannot be served from an old entry.
  - Every array is still checked against the manifest's byte count, and a 206 response is checked against its
    `Content-Range`.
  - If a server ignores `Range` (200), the whole file is fetched once and sliced.
  - The arrays `attn_topk_idx`, `attn_topk_val`, `attn_topk_mass`, `g_last`, `u_last` and `c_last` (19.8 of 22.3 MB
    per Llama run) load on demand through `ensureHeavy(D)`.
- `main.ts`: the 3D tab waits for those arrays. The ladder and the matrix draw without them and redraw their attention
  panels on the `sca2:heavy` event.
- `common.ts`:
  - `topKeys` returns `[]` and the top-16 coverage row is left out while the arrays are missing;
  - the head inspector says "still loading" (it is never blank and never shows a wrong number).
- `tab-c.ts` and `tab-b.ts`: listen for `sca2:heavy`.
- `index.html`: the loading-line wording.

## Evidence (local; server with Range support, no-store, throttled to 1 MB/s per connection)

| view | old v1.2.2 | new |
|---|---|---|
| landing, first visit | 23.7 s | 2.0 s |
| landing reload; tabs c, b | 23.7 s each | 0.1 s |
| tab k | 24.3 s | 0.7 s |
| tab a (3D), first visit | 32.3 s | 16.5 s (6-connection HTTP/1.1 limit locally) |

- Server that ignores Range: the first visit costs the same as before (24.4 s), and later views take 0.1 s.
- Parity (`parity.py`):
  - 33 URLs (landing, the 4 tabs and the 28 featured story links) give identical `#app` text, old against new, after
    all data arrived;
  - 0 console or page errors.
- Pinned head `?tab=c&sel=20,7`:
  - the new build is ready at 2.2 s and shows the placeholder;
  - it fills in at 10.5 s;
  - the final drawer text and shaded prompt HTML are byte-identical to the old build.
- Live CDN probe: a cross-origin `Range` request through the Hub redirect returns 206 with a readable
  `Content-Range`, and the Cache API and SubtleCrypto are available.
- `tsc` passes; `build_deploy_bundle` gives 143 files; `verify_bundle` passes; the suite is 183 passed, 4 skipped.

## Not done
- No live timing yet; that needs a deploy.
- Old cache entries are not pruned. They stay until the browser evicts them; keys change only when an export changes.
