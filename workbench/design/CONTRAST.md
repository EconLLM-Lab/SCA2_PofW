# CONTRAST

Text contrast for `index.html` (dark) and `index-light.html` (light). These ratios were measured in headless Chrome. None of them is estimated.

## Result

Every text element is at least 4.5:1. The lowest is 6.68:1 in dark and 5.41:1 in light.

| Theme | Text elements | Minimum ratio | Pass (>= 4.5) |
|---|---|---|---|
| dark  | 69 | 6.68 | yes |
| light | 69 | 5.41 | yes |

## How it was measured

`contrast.js` runs inside the page. It finds every element that holds its own text node, both HTML and SVG `<text>`, and computes the WCAG 2.x contrast ratio from the computed colours, with alpha composited.
- HTML text is measured against the nearest ancestor with an opaque background.
- Engraved SVG text sits on a drawn face, so it is measured against every face tone it could sit on: card, top, face, lit-top and shade-0..3. The table reports the worst of those.

```
SK=$HOME/.hermes/profiles/creative/skills/creative/anatomy
cd workbench/design
python3 -c "import json; json.dump([['wait',300],['eval',open('contrast.js').read()]], open('/tmp/ds/contrast-actions.json','w'))"
TMPDIR=/tmp/ds node $SK/scripts/drive.mjs index.html --actions /tmp/ds/contrast-actions.json        # exit 0
TMPDIR=/tmp/ds node $SK/scripts/drive.mjs index-light.html --actions /tmp/ds/contrast-actions.json  # exit 0
```

## Measured groups (lowest first)

Dark (`index.html`):

| Text | Colour | Background | Ratio | Count |
|---|---|---|---|---|
| card corners (title, hint) | #9b9b9b | #131313 card | 6.68 | 9 |
| conservation equations | #9b9b9b | #131313 card | 6.68 | 2 |
| kicker, legend keys, captions | #9b9b9b | #0b0b0b page | 7.08 | 19 |
| card corners (Fig n, readout), limits | #a3a3a3 | #131313 card | 7.37 | 11 |
| intro paragraph | #a3a3a3 | #0b0b0b page | 7.80 | 1 |
| engraved SVG labels (tokens, L0-L3, g_tilde, u, USA, MEX, scales, tag) | #d4d4d4 | worst face: lit-top #262626 | 10.21 | 22 |
| conservation names and values | #e6e6e6 | #131313 card | 14.89 | 4 |
| heading | #e6e6e6 | #0b0b0b page | 15.77 | 1 |

Light (`index-light.html`):

| Text | Colour | Background | Ratio | Count |
|---|---|---|---|---|
| kicker, legend keys, captions | #626266 | #f2f2ef page | 5.41 | 19 |
| card corners (title, hint), equations | #626266 | #fbfbfa card | 5.86 | 11 |
| intro paragraph | #57575a | #f2f2ef page | 6.42 | 1 |
| card corners (Fig n, readout), limits | #57575a | #fbfbfa card | 6.95 | 11 |
| engraved SVG labels | #26262a | worst face: shade-0 #dcdcd9 | 10.97 | 22 |
| heading | #18181a | #f2f2ef page | 15.81 | 1 |
| conservation names and values | #18181a | #fbfbfa card | 17.12 | 4 |

## One override, and why

The anatomy kit's default `--anatomy-muted` fails 4.5:1. I computed the kit defaults with the same WCAG formula:

- dark: #6e6e6e on the #131313 card gives 3.64.
- light: #8c8c90 on the #f2f2ef page gives 2.99, and on the #fbfbfa card 3.24.

The page overrides only that one variable: #9b9b9b in dark and #626266 in light (see `extraCss` in `build.mjs`). Engraved SVG text always uses the `hi` tone. The kit's default face-text tone, `mid` (#6a6a6a), measures 3.15 on #1c1c1c, so it would fail.

Not covered by these numbers: line art, dots and tick marks. They are graphics, not text, so this 4.5:1 rule does not apply to them. A few are faint by design: grid lines and minor ticks.

## Screenshots

All are real headless-Chrome captures (`scripts/drive.mjs` / `scripts/capture.mjs` from the anatomy skill). Each one sits next to the HTML:

- view1-tensor-blocks.png, view2-phase-plane.png, view3-usa-mex-overlap.png, view4-steering.png (dark, card plus legend)
- view2-phase-plane-clamped.png (clamp on), view4-steering-2.5x.png (s = +2.5x), conservation-bar-clamped-2.5x.png (both checks after clamp and steer)
- conservation-bar.png
- light-view1..4 (light theme, cards)
- phone-390.png (whole page at 390 px wide, no sideways scroll)

## Line-end check

`drive.mjs ["lines", null, "#vN .iso-plate"]` gives `line ends: 0` for all four figures in both themes. It also gives 0 with the clamp on and at each steer scale.
