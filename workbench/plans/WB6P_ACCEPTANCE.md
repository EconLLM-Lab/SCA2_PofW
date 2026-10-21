# WB6-P acceptance: plain-language pass (branch wb6-words, from e9b5fda)

Scope: visible text only (landing.ts, common.ts, tab-a/b/c.ts, public/sca2/index.html). No number, format call, id, data-*, class or href was changed. tab-k.ts, data.ts, main.ts, index.html, style.css, sca2_data.json were not touched.

## Glossary decisions
See workbench/viewer/GLOSSARY.md. Plain term first, technical term in tooltip, parentheses or pop-up. Main choices: margin -> "log-odds of X over Y"; d_margin -> "change from the base (B − A)"; ‖B − A‖ -> "size of the change"; "push on the margin" / DLA -> "contribution to the answer (DLA)"; write -> "addition"; conservation/closure gates -> "accounting checks"; fine-tune (as name of B) -> "country adapter" or "sign prompt"; A -> "base model". "clamped run" is kept (main.ts uses it) and explained as "the model run again with one group of neurons, Quadrant III, switched off (output set to zero)" after reading hooks.clamp_quadrant_iii.

## 25 most visible strings, before -> after
1. Landing "Terms" -> "Glossary"
2. Landing lede "compare a model before and after a fine-tune" -> "compare the base model with a changed version (a country adapter, or a sign prompt)"
3. Landing "A · original / B · fine-tuned" -> "A · base / B · with adapter"
4. Hero caption "The margin, layer by layer" -> "The log-odds, layer by layer"
5. Hero "B ends +x further toward" -> "B's log-odds end +x further toward"
6. S1 "MLP (a small neural network...)" -> "MLP block (a small neural network...)"; running state gains "(the technical name is the residual stream)"
7. S2 "The margin is the gap..." -> "The log-odds ... (called the margin in the code)"
8. S2 "Direct logit attribution (DLA) gives each part a share of the margin" -> "We give each part its contribution to the answer ... (The technical name is direct logit attribution, DLA.)"
9. S2 "The checks ... closure tests" -> "The accounting checks ... the parts add up to the final running state and to the log-odds"
10. S2 "Before and after" -> "Base and changed model" (base model, country adapter, sign prompt defined)
11. S2 chart "Change in each layer's push on the margin" -> "Change in each layer's contribution, B − A"
12. S3 "the three views" -> "the four views" (heading already said four)
13. S4 "Direct effect only: DLA credits..." -> "The contribution to the answer (DLA) credits..."
14. S4 "Norms hide direction" -> "Sizes hide direction"
15. Ladder header "Push at t*" -> "Contributions to the answer"
16. Ladder switch "B − A" -> "Change (B − A)" (new tooltips on A, B, change)
17. Ladder "clamped" -> "clamped run" (tooltip: Quadrant III neurons switched off)
18. Ladder footer "cells + embedding = x = change in margin" -> "all cells + embedding term = x = change in log-odds"
19. Ladder "Margin by layer" -> "Log-odds by layer" (also Matrix, 3D inset)
20. Matrix "attention write ‖a‖ / MLP write ‖m‖" -> "attention addition ‖a‖ / MLP block addition ‖m‖"
21. Matrix switch "‖B − A‖" -> "size of change ‖B − A‖"
22. 3D "A | ‖B − A‖" -> "A | size of change ‖B − A‖"
23. Answer strip "B leans further toward X than A: margin +x log-odds" -> "...: change in log-odds +x"
24. Inspector "Push (DLA)" -> "Contribution to the answer"; "Write size ‖o‖" -> "Size of the addition ‖o‖"
25. Story page: added plain explanations of GPS, C9, TVD (zero = same distribution, one = no overlap, written as words so no number token changes), response surface, route, persona, bits (signs), SE; nav "Readout ladder" -> "Ladder: which parts decided the answer". Every claim sentence and hedge kept; every test-pinned phrase kept.

Learn-more pop-ups: each of the 19 now opens with one plain sentence; technical text follows.

## Number parity (hard gate), old e9b5fda build vs new build, headless Chromium 1440x860
Both builds served from the curated bundle site (same exports). Tokens: regex [-+−]?\d[\d,.]*%?. Multisets identical, textContent and innerText:
- landing: 198 / 190 (textContent / innerText), identical
- ?tab=c: 174 / 178, identical
- ?tab=b: 156 / 159, identical
- ?tab=a: 162 / 165, identical
- story page: 710 / 702, identical
- console errors: 0 on all five pages (old and new)
Pop-ups (outside #app, extra check, 19 compared): identical except eq6 lost "1" and "3" (the two answer codes, from a redundant sentence "the log of the odds of 1 against 3" that I cut) and howto-a gained one "3" (from "3D"), which I removed afterwards (see caveats).
Files: ~/.hermes/cache/scratch/wb6p/{old_tokens,new_tokens}.json, parity.txt.

## Checks
- tsc --noEmit: exit 0.
- pytest: 183 passed, 4 skipped. No test was touched (the story test's pinned phrases were kept verbatim).
- Bundle: ~/.hermes/cache/scratch/wb6p/deploy_bundle.tar.gz, built with a hardlinked scratch workbench root (build_deploy_bundle.py rejects the symlinked exports dir); verify_bundle.py pass: true. Untracked, gitignored thumbnail PNGs were copied into viewer/screens/v4 and v3 so the builder finds them; not committed.

## Proposed renames for main.ts (not edited)
- Pickers: "A" / "B" labels -> "A (base)" / "B (compared)".
- Clamp chip title: "Quadrant III neurons set to zero" -> "switched off (set to zero)".
- Status button and fail banner: "check" -> "accounting check"; the frame tooltip shows raw gate names via checkLine (residual_closure rel ...); map them to the plain labels in common.ts CHECK_LABEL.
- Tab subtitles: Ladder "which parts decided the answer"; Matrix "where in the prompt the change sits"; Object "the whole run as 3D blocks"; Cohort "one base vs many adapters and sign prompts".

## Findings for the owner (not fixed, outside the copy fence)
1. Pop-ups and the Terms list hard-code the small teaching model: "576 numbers", "1,536 hidden units", "nine heads per layer", "three sets of key and value", "30 layers". The Paper B Llama pages have 4096, 14336, 32 heads, 8 key-value groups, 32 layers (manifest). Left unchanged because of the no-number rule. Fix: read them from D.A.m.model.
2. The "models" pop-up said every adapter matches "the USA's direction". The default adapter is CAN. I made it "that country's direction" (no number involved).

## Caveats
- The howto-a fix ("The 3D object" -> "This view") was made after the bundle build; tsc was re-run, the bundle was not rebuilt.
- Screenshots of landing, ladder and story at 1440x860 are in ~/.hermes/cache/scratch/wb6/words/ (landing.png, tab_c.png, story.png and others). I did not get to look at them: check for overflow in the new longer button labels (ladder "Change (B − A)", matrix "size of change ‖B − A‖", 3D scene bar).
- Added small non-behavioural code: a FACE_TIP constant for button tooltips in tab-b.ts and tab-c.ts, one glossary link on the landing page (data-learn="terms").
