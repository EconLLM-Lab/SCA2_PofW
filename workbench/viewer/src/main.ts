// App shell and router. Routes, all in the query string so every screen is reproducible:
//   (no tab)  landing page
//   tab=c     the ladder (default workbench tab)
//   tab=b     the matrix
//   tab=a     the 3D object
//   tab=k     Cohort (an honest empty state until ≥ 3 adapters share a base and an item; then the real map)
// v3 frame (design/layout-v3/SYSTEM.md §2): one header shared by every tab. Three things as a reader sees
// them: title + tabs; the A vs B pickers + the prompt picker; one status/help glyph (✓ N checks · ?).
// A failed check is a red banner under the frame that cannot be dismissed (DECISION.md, never-hide rule 1).
// The frame also shows the clamped run when a tab has it on (rule 4) and a placeholder badge (rule 6).
// Shared keys: a, b, item (the pair and the prompt), learn (an open pop-up). Each tab adds its own
// keys (see README "URL"). Switching tabs keeps the shared keys and restores the other tab's keys.
// The 3D renderer, its context-loss handlers and window.__renderer live in tab-a.ts; the scene
// disposal (disposeScene, renderLists.dispose) is in scene.ts / tab-a.ts and runs on every rebuild
// and whenever the 3D tab is left.

import { loadBundle, loadIndex, type Bundle, type IndexFile } from "./data";
import { checkLine, checksOf, esc, openLearn, roleOf } from "./common";
import { mountLanding } from "./landing";
import { mountLadder } from "./tab-c";
import { mountMatrix } from "./tab-b";
import { mountObject } from "./tab-a";
import { mountCohort } from "./tab-k";

export const DEFAULT = { a: "smol_inst", b: "smol_inst_usa_e3", item: "wvs_Q81" };
export type Tab = "c" | "b" | "a" | "k";
const SHARED = ["tab", "a", "b", "item", "learn", "fail"];

/** What a tab gets: its URL keys (read and write) and a ready signal. */
export interface Ctx {
  get(k: string): string | null;
  set(k: string, v: string | number | null): void;
  ready(): void;
  signal: AbortSignal;   // aborted when the tab unmounts: use it for window/document listeners
  mode(clamped: boolean): void;   // the frame shows the clamped run whenever a tab has it on
}
type Mount = (root: HTMLElement, D: Bundle, ctx: Ctx) => () => void;
const TABS: Record<Tab, Mount> = { c: mountLadder, b: mountMatrix, a: mountObject, k: mountCohort };
const TAB_NAMES: [Tab, string, string][] = [["c", "Ladder", "what decided the answer"], ["b", "Matrix", "where the change sits"], ["a", "Object", "the whole run in 3D"], ["k", "Cohort", "one base vs many adapters"]];

const app = document.getElementById("app")!;
const W = window as any;
let index: IndexFile;
let D: Bundle | null = null;
let unmount: (() => void) | null = null;
let ac: AbortController | null = null;
const memory: Partial<Record<Tab, URLSearchParams>> = {};   // per-tab keys, kept while you visit other tabs

const url = () => new URLSearchParams(location.search);
function write(p: URLSearchParams, push = false) {
  const s = p.toString().replace(/%2C/g, ",").replace(/%7C/g, "|");
  history[push ? "pushState" : "replaceState"](null, "", s ? `?${s}` : location.pathname);
}
function shared(p: URLSearchParams) {
  const pair = p.get("pair")?.split("|");   // legacy viewer key
  const a = p.get("a") || pair?.[0] || DEFAULT.a, b = p.get("b") || pair?.[1] || DEFAULT.b;
  let item = p.get("item") || DEFAULT.item;
  const items = index.pairs.filter((x) => x.a === a && x.b === b).map((x) => x.item_id);
  if (items.length && !items.includes(item)) item = items[0];
  return { a, b, item };
}

/** Go to a tab (or the landing page with tab = null), keeping the pair and the prompt. */
export function go(tab: Tab | null, extra: Record<string, string> = {}) {
  const cur = url(), curTab = cur.get("tab") as Tab | null;
  if (curTab) { const own = new URLSearchParams(); cur.forEach((v, k) => { if (!SHARED.includes(k)) own.set(k, v); }); memory[curTab] = own; }
  const { a, b, item } = shared(cur);
  const p = new URLSearchParams();
  if (tab) p.set("tab", tab);
  p.set("a", a); p.set("b", b); p.set("item", item);
  if (cur.get("fail")) p.set("fail", cur.get("fail")!);   // dev-only simulated failure survives tab switches
  if (tab && memory[tab]) memory[tab]!.forEach((v, k) => p.set(k, v));
  for (const [k, v] of Object.entries(extra)) p.set(k, v);
  write(p, true);
  route();
}

function shell(tab: Tab, D: Bundle): HTMLElement {
  const name = (k: string) => esc(index.models[k]?.label ?? k);
  const checks = checksOf(D), bad = checks.filter((c) => !c.ok);
  app.className = "wb";
  app.innerHTML = `<header id="frame">
      <div class="r1">
        <span class="tt" data-obj="title-tabs"><a class="brand" href="#" data-go="landing" title="About the workbench">SCA2 workbench</a>
          <nav class="tabs">${TAB_NAMES.map(([k, n, t], i) => `<button data-tab="${k}" class="${k === tab ? "on" : ""}" title="${esc(t)} (key ${i + 1})">${esc(n)}</button>`).join("")}</nav></span>
        <span class="sp"></span>
        ${tab === "k" ? `<span class="illus" title="The cohort map needs exports that do not exist yet; the only figure on this tab is an illustration">no data yet · illustration</span>` : ""}
        <span id="status" class="status ${bad.length ? "bad" : "ok"}" data-obj="status">
          <button id="chk" data-learn="conservation" title="${esc(checks.map((c) => (c.ok ? "✓ " : "✗ ") + checkLine(c)).join("\n"))}">${bad.length ? `✗ ${bad.length} of ${checks.length}` : `✓ ${checks.length}`}</button><button id="help" data-learn="howto-${tab}" title="How to read this view, and the keys (?)">?</button></span>
      </div>
      <div class="r2" data-obj="pickers">
        <label class="slot a" title="Model A"><span class="k">A</span><select id="selA"></select></label>
        <span class="vs">vs</span>
        <label class="slot b" title="Model B"><span class="k">B</span><select id="selB"></select></label>
        <span id="clampchip" class="clampchip" hidden title="Every number on this tab is from the clamped run (Quadrant III neurons set to zero), not the normal run.">clamped run</span>
        <span class="sp"></span>
        <label class="slot item" title="The prompt (item)"><span class="k">prompt</span><select id="item"></select></label>
      </div>
    </header>
    ${bad.length ? `<div id="failbar" data-obj="fail" role="alert"><b>✗ ${bad.length} check${bad.length > 1 ? "s" : ""} failed</b> · ${bad.map((c) => esc(checkLine(c))).join(" · ")}. The parts below do not add up for ${[...new Set(bad.map((c) => c.who))].join(", ")}; do not read them as measurements until the export is fixed.</div>` : ""}
    <main id="view"></main>`;
  const { a, b, item } = shared(url());
  const sa = app.querySelector<HTMLSelectElement>("#selA")!, sb = app.querySelector<HTMLSelectElement>("#selB")!, is = app.querySelector<HTMLSelectElement>("#item")!;
  const as = [...new Set(index.pairs.map((p) => p.a))];
  sa.innerHTML = as.map((k) => `<option value="${esc(k)}">${name(k)}</option>`).join("");
  sa.value = a;
  const fillB = (sel: string) => {
    const bs = [...new Set(index.pairs.filter((p) => p.a === sa.value).map((p) => p.b))];
    sb.innerHTML = bs.map((k) => `<option value="${esc(k)}">${name(k)}</option>`).join("");
    sb.value = bs.includes(sel) ? sel : bs[0];
    if (tab === "k") { sb.disabled = true; sb.title = "On Cohort, B is every adapter of base A; pick B on the other tabs."; }
  };
  const fillItems = (sel: string) => {
    const items = index.pairs.filter((x) => x.a === sa.value && x.b === sb.value).map((x) => x.item_id);
    is.innerHTML = items.map((i) => `<option>${esc(i)}</option>`).join("");
    is.value = items.includes(sel) ? sel : items[0];
  };
  fillB(b); fillItems(item);
  const reload = () => { const p = url(); p.set("a", sa.value); p.set("b", sb.value); p.set("item", is.value); p.delete("pair");
    // selections index into the old prompt's tokens: drop them when the prompt changes
    for (const k of ["sel", "pin", "fly", "hl"]) p.delete(k);
    write(p, true); route(); };
  const titles = () => { sa.title = sa.selectedOptions[0]?.textContent ?? ""; sb.title = sb.selectedOptions[0]?.textContent ?? ""; };
  titles();
  sa.onchange = () => { fillB(sb.value); fillItems(is.value); titles(); reload(); };
  sb.onchange = () => { fillItems(is.value); titles(); reload(); };
  is.onchange = reload;
  return app.querySelector<HTMLElement>("#view")!;
}

async function route() {
  if (unmount) { unmount(); unmount = null; }
  if (ac) ac.abort();
  ac = new AbortController();
  W.__ready = false;
  document.querySelector<HTMLDialogElement>("dialog#learn")?.close();
  const p = url(), tab = p.get("tab") as Tab | null;
  const { a, b, item } = shared(p);
  try {
    D = await loadBundle(a, b, item);
    if (!tab || !(tab in TABS)) {
      app.className = "landing";
      unmount = mountLanding(app, D, { go });
      W.__ready = true;
    } else {
      const view = shell(tab, D);
      const sA = app.querySelector<HTMLElement>(".slot.a")!, sB = app.querySelector<HTMLElement>(".slot.b")!;
      sA.title = `Model A: ${D.A.m.model.label}${roleOf(D, "A")}`; sB.title = `Model B: ${D.B.m.model.label}${roleOf(D, "B")}`;
      const signal = ac.signal;
      const ctx: Ctx = {
        get: (k) => url().get(k),
        set: (k, v) => { const q = url(); if (v == null || v === "") q.delete(k); else q.set(k, String(v)); write(q); },
        ready: () => { W.__ready = true; },
        signal,
        mode: (on) => { const c = app.querySelector<HTMLElement>("#clampchip"); if (c) c.hidden = !on; },
      };
      unmount = TABS[tab](view, D, ctx);
    }
    if (p.get("learn")) openLearn(D, p.get("learn")!);
  } catch (e) {
    const pre = document.createElement("pre");
    pre.className = "err";
    pre.textContent = String(e);
    app.prepend(pre);
    W.__ready = "error: " + String(e);
  }
}

// One delegated listener for tab buttons, landing links and every "learn more" button.
document.addEventListener("click", (e) => {
  const t = e.target as HTMLElement;
  const tb = t.closest<HTMLElement>("[data-tab]");
  if (tb && tb.closest("#frame")) { e.preventDefault(); go(tb.dataset.tab as Tab); return; }
  const g = t.closest<HTMLElement>("[data-go]");
  if (g) { e.preventDefault(); const to = g.dataset.go!; go(to === "landing" ? null : (to as Tab), g.dataset.extra ? Object.fromEntries(new URLSearchParams(g.dataset.extra)) : {}); window.scrollTo(0, 0); return; }
  const l = t.closest<HTMLElement>("[data-learn]");
  if (l && D) { e.preventDefault(); e.stopPropagation(); openLearn(D, l.dataset.learn!); }
});
window.addEventListener("popstate", route);
// Frame keys: 1 2 3 4 switch tabs, ? opens the help for the current view. Tabs add their own keys.
document.addEventListener("keydown", (e) => {
  const t = e.target as HTMLElement;
  if (e.metaKey || e.ctrlKey || e.altKey || /^(INPUT|SELECT|TEXTAREA)$/.test(t.tagName) || document.querySelector("dialog[open]")) return;
  const cur = url().get("tab") as Tab | null;
  if (!cur || !(cur in TABS)) return;
  const i = "1234".indexOf(e.key);
  if (i >= 0) { e.preventDefault(); go(TAB_NAMES[i][0]); return; }
  if (e.key === "?" && D) { e.preventDefault(); openLearn(D, `howto-${cur}`); }
});

(async () => {
  try { index = await loadIndex(); W.__index = index; await route(); }
  catch (e) { app.textContent = String(e); W.__ready = "error: " + String(e); }
})();
