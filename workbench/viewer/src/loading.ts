// Loading visual. Honest progress only: the numbers are the bytes data.ts asked the network for and has received
// (cache hits do not count). Two pieces:
//  - a loading card while a view waits for its data: a meter of 32 equal bars (a nod to the 32 layers, but the bars
//    are bytes, not layers) that light up in order as the bytes arrive, with a soft wave over the bars still to come. The card appears only once bytes are
//    requested (or after 1.5 s), so a cached view (about 0.1 s) never flashes it.
//  - a thin bar at the top of the page while anything downloads, including the background prefetch.
// prefers-reduced-motion: no wave and no transitions (loading.css).

import "./loading.css";
import { progress } from "./data";

const MB = (n: number) => (n / 1e6).toFixed(n < 1e7 ? 1 : 0);
const BARS = 32;

let bar: HTMLElement | null = null;
/** The thin top bar. Call once. */
export function initTopBar() {
  bar = document.createElement("div");
  bar.id = "netbar"; bar.setAttribute("aria-hidden", "true");
  bar.innerHTML = "<i></i>";
  document.body.appendChild(bar);
  document.addEventListener("sca2:progress", paintBar);
}
function paintBar() {
  if (!bar) return;
  const f = progress.fg, b = progress.bg, use = f.want ? f : b;
  bar.classList.toggle("on", use.want > 0);
  bar.classList.toggle("bg", !f.want && b.want > 0);
  (bar.firstElementChild as HTMLElement).style.width = use.want ? `${Math.min(100, (100 * use.got) / use.want).toFixed(1)}%` : "0";
}

/** Show the loading card in `host` (inline, e.g. the boot screen) or as a centred card over the page.
 * Returns hide(). `title` is the plain sentence at the top; `note` the line under the numbers. */
export function showLoader(o: { host?: HTMLElement; title: string; note: string; delay?: number }): () => void {
  let el: HTMLElement | null = null, timer = 0, gone = false;
  const t0 = performance.now();
  const paint = () => {
    if (!el) return;
    // The view can also be waiting on background bytes (the 3D view reuses an attention download that the ladder
    // started quietly), so show those when nothing is in the foreground.
    const f = progress.fg.want ? progress.fg : progress.bg, frac = f.want ? Math.min(1, f.got / f.want) : 0, lit = Math.floor(frac * BARS);
    el.querySelectorAll<HTMLElement>(".ld-stack i").forEach((b, i) => b.classList.toggle("lit", i < lit));
    el.querySelector<HTMLElement>(".ld-n")!.textContent = f.want
      ? `Downloading saved model data · ${MB(f.got)} of ${MB(f.want)} MB · ${Math.floor(frac * 100)}%`
      : "Opening the saved run…";
  };
  const open = () => {
    if (gone) return;
    // A cached view needs no download: wait until bytes are requested, or 1.5 s pass, so it never flashes the card.
    if (!o.host && !progress.fg.want && performance.now() - t0 < 1500) { timer = window.setTimeout(open, 150); return; }
    el = document.createElement("div");
    el.className = o.host ? "ld-card inline" : "ld-card float";
    el.setAttribute("role", "status"); el.setAttribute("aria-live", "polite");
    el.dataset.obj = "loader";
    // innerHTML is safe here: title and note are constant strings from main.ts, never page or user input.
    el.innerHTML = `<div class="ld-stack" aria-hidden="true">${Array.from({ length: BARS }, (_, i) =>
      `<i style="--i:${i}"></i>`).join("")}</div>
      ${o.title ? `<b class="ld-t">${o.title}</b>` : ""}
      <span class="ld-n"></span>
      <span class="ld-note">${o.note}</span>`;
    (o.host ?? document.body).appendChild(el);
    document.body.classList.add("ld-open");   // one meter at a time: the top bar steps back while the card shows
    paint();
  };
  document.addEventListener("sca2:progress", paint);
  timer = window.setTimeout(open, o.delay ?? 350);
  return () => {
    gone = true; clearTimeout(timer);
    document.removeEventListener("sca2:progress", paint);
    if (el) document.body.classList.remove("ld-open");
    el?.remove(); el = null;
  };
}
