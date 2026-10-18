// Card t_58fed76a — ground-truth "unchanged" check, complementing screens/f32-gates/verify.mjs.
//
// Imports the pre-change common.ts (obtained read-only with `git show HEAD:workbench/viewer/src/common.ts`)
// and the working one, runs checksOf() + learnText(D, "conservation") on the same Bundle, and asserts:
//   * a float64 export (no `conservation.relative`) yields byte-identical output old vs new;
//   * a float32 fixture (with `relative`) yields different output, the new one being the relative table.
// Run: node --experimental-strip-types logic-diff.mjs <abs path to old common.ts>
// Env: FXDIR = the fixture dir written by verify.mjs.
import { readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const DIR = import.meta.dirname;
const VIEWER = resolve(DIR, "../..");
const EXPORTS = resolve(VIEWER, "../exports");
const FX = process.env.FXDIR;
const OLD = process.argv[2];
const ITEM = "wvs_Q81";
const read = (p) => JSON.parse(readFileSync(p, "utf8"));

const oldMod = await import(pathToFileURL(OLD).href);
const newMod = await import(pathToFileURL(join(VIEWER, "src/common.ts")).href);

const run = (base, key) => read(join(base, `run__${key}__${ITEM}.json`));
const pair = (base, a, b) => read(join(base, `pair__${a}__${b}__${ITEM}.json`));
const cc = { dlaSum: 0, dlaGap: 0, headSumVsAttn: 0, pass: true };
const bundle = (rA, rB, p) => ({ A: { m: rA, t: {}, clientCheck: cc }, B: { m: rB, t: {}, clientCheck: cc }, P: { m: p, t: { d_weight_mlp: { absMax: () => 1 } } }, key: "k" });

const results = [];
function compare(name, D, expectSame, expectSub) {
  const oc = JSON.stringify(oldMod.checksOf(D)), nc = JSON.stringify(newMod.checksOf(D));
  const ol = oldMod.learnText(D, "conservation")[1], nl = newMod.learnText(D, "conservation")[1];
  const same = oc === nc && ol === nl;
  const ok = expectSame ? same : (!same && nl.includes(expectSub));
  results.push({ name, identical: same, ok,
    old_table: ol.includes("Must be below") ? "legacy" : "relative",
    new_table: nl.includes("rel \u2264") ? "relative" : "legacy",
    old_failing_rows: oldMod.checksOf(D).filter((c) => !c.ok).length,
    new_failing_rows: newMod.checksOf(D).filter((c) => !c.ok).length });
}

compare("f64 export (no relative) — unchanged", bundle(run(EXPORTS, "smol_base"), run(EXPORTS, "smol_inst"), pair(EXPORTS, "smol_base", "smol_inst")), true);
compare("f32 fixture (relative, passes) — new reader", bundle(run(FX, "smol_f32"), run(FX, "smol_f32_b"), pair(FX, "smol_f32", "smol_f32_b")), false, "rel \u2264");
compare("f32 fixture (one relative check fails)", bundle(run(FX, "smol_f32_bad"), run(FX, "smol_f32_b"), pair(FX, "smol_f32_bad", "smol_f32_b")), false, "rel \u2264");

const report = { results, pass: results.every((r) => r.ok) };
writeFileSync(join(DIR, "logic-diff.json"), JSON.stringify(report, null, 1));
console.log(JSON.stringify(report, null, 1));
process.exit(report.pass ? 0 : 1);
