# WB6-L acceptance: loading visual, background prefetch, download queue, link previews (producer record, PM, 2026-10-21)

The producer is the PM (Claude). Cross-family verification is folded into WB6-V (DeepSeek), together with the merged WB6-K and WB6-P.
Viewer only: no export, builder or data file changes. The new files are `viewer/src/loading.ts`, `viewer/src/loading.css`
and `deploy/SPACE_README.md`.

## Changes
- **Loading card (`loading.ts`).** A meter of 32 equal bars lights up in order as bytes arrive, under one number:
  "Downloading saved model data · 3.9 of 5.7 MB · 68%". A soft wave runs over the bars still to come.
  - The numbers are real: bytes requested from the network and bytes received (`data.ts` `progress`, counted while the
    body streams). Cache hits do not count.
  - On the first visit the card sits inside the boot screen. On later routes it is centred over the greyed view.
  - The card opens only once bytes are requested, or after 1.5 s, so a cached view never flashes it (tested). The
    3D tab gets its own note: "about 40 MB on the first visit".
  - `prefers-reduced-motion` turns off the wave. The bars are bytes, not layers; the code says so, and the screen never
    claims "layer N".
- **Thin top bar (`#netbar`).** It shows while anything downloads. It is dimmed for background work and steps back
  while the card shows, so only one meter is visible at a time.
- **Background prefetch.** 2.5 s after the landing page or the Cohort tab is ready, the attention arrays of the current
  pair download quietly (`prefetchHeavy`). On the Ladder and the Matrix the existing deferred load runs in the
  background. Every background load is aborted when the visitor navigates, so it never slows the next view.
- **Download queue.** At most 4 network ranges run at a time, the visible view's first. The CDN caps bandwidth per
  visitor, so the chunks now finish one after another, each finished chunk is cached, and an aborted download keeps its
  finished work. This addresses WB5-V N1.
  - A request that waited in the queue checks the cache again, and checks whether the whole file already arrived from
    a server that ignores Range. That stops repeated whole-file downloads on such servers.
  - A failed whole-file read is not kept.
- **Link previews.** `index.html` gets a plain title, a description and `og:`/`twitter:` tags; the image is the Ladder
  thumbnail on the Space.
- **Space README.** It is now tracked in `deploy/SPACE_README.md` (it used to live only in a pruned scratch folder). It
  has plain text for colleagues and a `short_description` for the Hub card.

## Evidence (local; the PM's range server, throttled to 1 MB/s per connection)

| Check | Result |
|---|---|
| Boot card on a cold landing | "3.9 of 5.7 MB · 68%", 21 of 32 bars lit; landing ready in 2.1 s; card gone after ready |
| Background prefetch after the landing | top bar `on bg`; finished at about 12 s |
| 3D tab after the prefetch (fresh page load) | 4.4 s (16 to 30 s before); the rest is the headless software-WebGL scene build |
| 3D tab cold from the Ladder | card counts "29 → 39 of 40 MB", bars 23 → 31 |
| Route card on a new pair | "4.9 of 5.5 MB · 90%", 28 of 32 bars lit (bars are floored) |
| Cached switches c → b → c | the card never appears (MutationObserver) |
| Abort and resume | 4 s on the Ladder, then the Matrix: 16 of 20 chunks requested again, about 4 reused from the cache (before the queue, 0 chunks had finished when the switch came, so all 20 restarted) |
| Parity (`parity6.py`) against the live v1.3 build | 33/33 URLs identical `#app` text, 0 console errors (run on the build before the queue; the queue changes only scheduling) |
| `tsc`; build; `verify_bundle`; suite | pass; 143 files; pass; 183 passed, 4 skipped |

Screenshots: `~/.hermes/cache/scratch/wb6/loading/boot-loading-v2.png` and `route-loading-v2.png`. Both were read by
a vision pass; the four layout issues it raised were fixed: one meter, uniform bars, contrast of 3:1 or more for unlit
bars, and an accent-coloured link.

## Not done
- No live timing yet; that needs a deploy.
- WB5-V N4 (a transient "Σ attention 0.00" on a pinned head): the line is in `tab-c.ts`, which the WB6-P copy pass
  owns. It gets fixed after the merge.
