// Measure WCAG 2.x text contrast for every text element on the design page.
// Run through the anatomy skill's drive.mjs as an "eval" action (see CONTRAST.md).
(() => {
  const parse = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  const lin = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
  const lum = (c) => 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
  const over = (fg, bg) => ({ r: fg.r * fg.a + bg.r * (1 - fg.a), g: fg.g * fg.a + bg.g * (1 - fg.a), b: fg.b * fg.a + bg.b * (1 - fg.a), a: 1 });
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const bgOf = (el) => { for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a > 0) return c; } return parse(getComputedStyle(document.body).backgroundColor); };
  const varColor = (name) => { const d = document.createElement("div"); d.style.color = `var(${name})`; document.body.appendChild(d); const c = parse(getComputedStyle(d).color); d.remove(); return c; };
  // Faces an engraved label can sit on: every top and side tone of a solid, plus the card.
  const faces = ["--anatomy-card", "--anatomy-top", "--anatomy-face", "--anatomy-lit-top", "--anatomy-shade-0", "--anatomy-shade-1", "--anatomy-shade-2", "--anatomy-shade-3"].map((n) => [n, varColor(n)]);
  const rows = [];
  for (const el of document.querySelectorAll("body *")) {
    if (el.closest("script,style,title,defs")) continue;
    const own = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    if (!own) continue;
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden") continue;
    const text = el.textContent.trim().slice(0, 40);
    const op = Number(cs.opacity);
    if (el instanceof SVGElement) {
      const fill = parse(cs.fill);
      const worst = faces.map(([n, bg]) => [n, ratio(over({ ...fill, a: fill.a * op }, bg), bg)]).sort((a, b) => a[1] - b[1])[0];
      rows.push({ kind: "svg", text, fg: cs.fill, bg: worst[0], ratio: +worst[1].toFixed(2) });
    } else {
      const fg = parse(cs.color); const bg = bgOf(el);
      rows.push({ kind: "html", text, cls: el.className && String(el.className).slice(0, 30), fg: cs.color, bg: `rgb(${bg.r}, ${bg.g}, ${bg.b})`, ratio: +ratio(over({ ...fg, a: fg.a * op }, bg), bg).toFixed(2) });
    }
  }
  const groups = {};
  for (const r of rows) { const key = `${r.kind}|${r.cls || ""}|${r.fg}|${r.bg}`; (groups[key] ||= { ...r, n: 0 }).n++; }
  const list = Object.values(groups).sort((a, b) => a.ratio - b.ratio);
  return JSON.stringify({ theme: document.body.dataset.theme, elements: rows.length, min: list[0].ratio, groups: list.map(({ kind, cls, fg, bg, ratio, n, text }) => ({ kind, cls, fg, bg, ratio, n, sample: text })) }, null, 1);
})()
