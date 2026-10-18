# Relative-gate verification (card t_58fed76a)

Proves the viewer reads `conservation.relative` from a `capture@1.1` manifest, so a float32
export draws as a pass when its relative gates pass, while a float64 export (no `relative`) is
untouched. Reader change only: `viewer/src/common.ts`, `viewer/src/data.ts`, `viewer/README.md`.

Two scripts, both run from `viewer/` and needing `dist/` built (`npm run build`):

    npm run build
    FXDIR=$TMPDIR/f32-gates-fx node screens/f32-gates/verify.mjs          # browser, exit 0 = all cases pass
    FXDIR=$TMPDIR/f32-gates-fx node --experimental-strip-types \
      screens/f32-gates/logic-diff.mjs <abs path to pre-change common.ts> # old vs new, exit 0 = pass

* `verify.mjs` — builds throwaway float32 fixtures from a real export (numbers from
  `plans/stage1_f32_gaps.md`), serves `dist/` plus a fixture `/exports` from a local server,
  drives headless Chrome over CDP (no extra deps), writes the screenshots and `report.json` in
  this directory, and sweeps every real pair across the four tabs and the landing (0 console
  errors expected). It touches nothing under `workbench/exports/`.
* `logic-diff.mjs` — imports the pre-change `common.ts` (obtained read-only with
  `git show HEAD:workbench/viewer/src/common.ts`) and the working one, and requires
  byte-identical `checksOf` + `learnText(_, "conservation")` output for a float64 export and
  different output for a float32 fixture.

Screenshots: `f64-frame.png` / `f64-checks.png` (float64: ✓ frame, legacy absolute table),
`f32-frame.png` / `f32-checks.png` (float32: ✓ frame, relative `rel ≤ τ` table),
`f32fail-frame.png` / `f32fail-checks.png` (one relative check fails → red, non-dismissible banner).
