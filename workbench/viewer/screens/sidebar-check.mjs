// Sidebar reachability check (presentation QA, no app code): opens a view at 1700x1000 in headless
// Chrome, prints the sidebar's bottom edge vs the window height, scrolls the sidebar to its end and
// saves a screenshot.  usage: node screens/sidebar-check.mjs <out.png> [url]
import { spawn } from "node:child_process";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const out = process.argv[2] ?? "sidebar-bottom.png";
const url = process.argv[3] ??
  "http://127.0.0.1:5178/?view=side&right=b&single=b&pair=smol_inst%7Csmol_inst_usa_e3&item=wvs_Q81&hscale=log&color=dla&sel=23,0,151";
const port = 9300 + Math.floor(Math.random() * 600);
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", [
  "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--hide-scrollbars",
  "--window-size=1700,1000", `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), "cdp-"))}`, "about:blank",
], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let targets;
for (let i = 0; i < 50; i++) {
  try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); if (targets.length) break; } catch {}
  await sleep(200);
}
const ws = new WebSocket(targets.find((t) => t.type === "page").webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
let id = 0; const pending = new Map();
ws.addEventListener("message", (e) => { const m = JSON.parse(e.data); if (pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); } });
const send = (method, params = {}) => new Promise((r) => { pending.set(++id, r); ws.send(JSON.stringify({ id, method, params })); });
const ev = async (expr) => (await send("Runtime.evaluate", { expression: expr, returnByValue: true })).result.value;

await send("Page.navigate", { url });
for (let i = 0; i < 100 && (await ev("window.__ready")) !== true; i++) await sleep(300);
await sleep(1500);
const m = await ev(`(() => { const s = document.getElementById("side"), r = s.getBoundingClientRect();
  s.scrollTop = s.scrollHeight; return { innerHeight, sideTop: r.top, sideBottom: r.bottom, barHeight: document.getElementById("bar").offsetHeight,
  scrollHeight: s.scrollHeight, clientHeight: s.clientHeight, docScroll: document.documentElement.scrollHeight }; })()`);
console.log(JSON.stringify(m));
await sleep(500);
const shot = await send("Page.captureScreenshot", { format: "png" });
writeFileSync(out, Buffer.from(shot.data, "base64"));
console.log(m.sideBottom <= m.innerHeight && m.docScroll <= m.innerHeight ? "PASS sidebar fits the window" : "FAIL sidebar extends past the window");
ws.close(); chrome.kill();
process.exit(m.sideBottom <= m.innerHeight && m.docScroll <= m.innerHeight ? 0 : 1);
