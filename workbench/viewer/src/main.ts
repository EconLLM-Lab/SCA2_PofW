// App shell and router. Routes, all in the query string so every screen is reproducible:
//   (no tab)  landing page
//   tab=c     the ladder (default workbench tab)
//   tab=b     the matrix
//   tab=a     the 3D object
// Shared keys: a, b, item (the pair and the prompt), learn (an open pop-up). Each tab adds its own
// keys (see README "URL"). Switching tabs keeps the shared keys and restores the other tab's keys.
// The 3D renderer, its context-loss handlers and window.__renderer live in tab-a.ts; the scene
// disposal (disposeScene, renderLists.dispose) is in scene.ts / tab-a.ts and runs on every rebuild
// and whenever the 3D tab is left.

import { loadBundle, loadIndex, type Bundle, type IndexFile } from "./data";
import { esc, lm, openLearn, roleOf } from "./common";
import { mountLanding } from "./landing";
import { mountLadder } from "./tab-c";
import { mountMatrix } from "./tab-b";
import { mountObject } from "./tab-a";

export const DEFAULT = { a: "smol_inst", b: "smol_inst_usa_e3", item: "wvs_Q81" };
export type Tab = "c" | "b" | "a";
const SHARED = ["tab", "a", "b", "item", "learn"];

/** What a tab gets: its URL keys (read and write) and a ready signal. */
export interface Ctx {
  get(k: string): string | null;
  set(k: string, v: string | number | null): void;
  ready(): void;
  signal: AbortSignal;   // aborted when the tab unmounts: use it for window/document listeners
}
type Mount = (root: HTMLElement, D: Bundle, ctx: Ctx) => () => void;
const TABS: Record<Tab, Mount> = { c: mountLadder, b: mountMatrix, a: mountObject };
const TAB_NAMES: [Tab, string][] = [["c", "Ladder: what decided the answer"], ["b", "Matrix: where the change sits"], ["a", "3D object: the whole run"]];

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
  if (tab && memory[tab]) memory[tab]!.forEach((v, k) => p.set(k, v));
  for (const [k, v] of Object.entries(extra)) p.set(k, v);
  write(p, true);
  route();
}

function shell(tab: Tab): HTMLElement {
  const pairs = [...new Set(index.pairs.map((p) => `${p.a}|${p.b}`))];
  app.className = "wb";
  app.innerHTML = `<header id="bar">
      <a class="brand" href="#" data-go="landing" title="About the workbench">SCA2 workbench</a>
      <nav class="tabs">${TAB_NAMES.map(([k, n]) => `<button data-tab="${k}" class="${k === tab ? "on" : ""}">${esc(n)}</button>`).join("")}</nav>
      <label>pair <select id="pair">${pairs.map((k) => { const [a, b] = k.split("|"); return `<option value="${esc(k)}">A ${esc(index.models[a]?.label ?? a)} · B ${esc(index.models[b]?.label ?? b)}</option>`; }).join("")}</select></label>
      <label>prompt <select id="item"></select></label>
      <span class="muted" id="who"></span>
      <a class="about" href="#" data-go="landing">About ↗</a>
    </header><main id="view"></main>`;
  const { a, b, item } = shared(url());
  const ps = app.querySelector<HTMLSelectElement>("#pair")!, is = app.querySelector<HTMLSelectElement>("#item")!;
  ps.value = `${a}|${b}`;
  const fillItems = (sel: string) => {
    const [pa, pb] = ps.value.split("|");
    const items = index.pairs.filter((x) => x.a === pa && x.b === pb).map((x) => x.item_id);
    is.innerHTML = items.map((i) => `<option>${esc(i)}</option>`).join("");
    is.value = items.includes(sel) ? sel : items[0];
  };
  fillItems(item);
  const reload = () => { const p = url(); const [pa, pb] = ps.value.split("|"); p.set("a", pa); p.set("b", pb); p.set("item", is.value); p.delete("pair");
    // selections index into the old prompt's tokens: drop them when the prompt changes
    for (const k of ["sel", "pin", "fly", "hl"]) p.delete(k);
    write(p, true); route(); };
  ps.onchange = () => { fillItems(is.value); reload(); };
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
      const view = shell(tab);
      app.querySelector("#who")!.innerHTML = `A: ${esc(D.A.m.model.label)}${roleOf(D, "A")} · B: ${esc(D.B.m.model.label)}${roleOf(D, "B")} · ${esc(D.A.m.item.item_id)} ${lm("models", "who are A and B?")}`;
      const signal = ac.signal;
      const ctx: Ctx = {
        get: (k) => url().get(k),
        set: (k, v) => { const q = url(); if (v == null || v === "") q.delete(k); else q.set(k, String(v)); write(q); },
        ready: () => { W.__ready = true; },
        signal,
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
  if (tb && tb.closest("#bar")) { e.preventDefault(); go(tb.dataset.tab as Tab); return; }
  const g = t.closest<HTMLElement>("[data-go]");
  if (g) { e.preventDefault(); const to = g.dataset.go!; go(to === "landing" ? null : (to as Tab), g.dataset.extra ? Object.fromEntries(new URLSearchParams(g.dataset.extra)) : {}); window.scrollTo(0, 0); return; }
  const l = t.closest<HTMLElement>("[data-learn]");
  if (l && D) { e.preventDefault(); e.stopPropagation(); openLearn(D, l.dataset.learn!); }
});
window.addEventListener("popstate", route);

(async () => {
  try { index = await loadIndex(); W.__index = index; await route(); }
  catch (e) { app.textContent = String(e); W.__ready = "error: " + String(e); }
})();
