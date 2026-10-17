# COPY: workbench v2 copy pass

Card: `t_c6d0a437` (writer). Applied by: creative, in the port card `t_0fc4d4f8`.
Files reviewed: `landing.html`, `variant-{a,b,c}.html`, `common.js`, `DECISION.md`, `README.md`, `viewer/README.md`, `spec/export_contract.md`, `spec/conservation.md`, and the `pm-*.png` screenshots. `data/` was not read. No HTML, JS, TS or Python was edited.

## PM rulings (added by the PM after review, 2026-10-17; these override the rows they name)

**Two glosses are factually wrong. Use these texts instead:**
- **G12 float64:** "64-bit *binary* floating-point arithmetic, about 16 significant digits. R's default numeric type. Most language-model runs use 16 or 32 bits." (It is not decimal.)
- **G13 fine-tune / G16 DPO, and any string that says the fine-tune moves the model "toward USA survey answers":** the training pairs are **synthetic scenarios** (`D_syn_USA.jsonl`). In each pair the preferred answer is the one whose direction matches the **sign of the USA's score on the Global Preferences Survey** (GPS) dimension the scenario targets. Suggested gloss: "trained on made-up everyday scenarios, preferring the answer that matches the USA's direction on the Global Preferences Survey (e.g. more trusting, more patient)". Never say the model was trained on survey responses.

**Claims settled from the code:**
- **K1:** confirmed. The 1e-10 gate is a *relative* gap against HF with its three float32 casts removed (`llama_capture.reference_check`). Stock HF differs by about 1e-6 relative, which is float32 rounding. Keep the qualifier.
- **K2:** fix the sign bug in the port. Template: "B ends ${abs} higher/lower than A". Use the writer's reading of "split" (the layer where A and B differ most in what that layer adds to the margin), and say so on screen.
- **K5:** both statements are true, so say both. A test in the code suite (`test_eq6_single_position_equals_teacher_forced`) checks Eq. 6 = teacher-forced. Each export also records the gap, for information, with no gate. Use: "a test checks this; each export also records the gap".
- **K10, K11, K24:** template everything from the export. Model labels come from `manifest.model.label`. Item codes and labels come from `manifest.item`. The question text comes from the tokens of the `question` segment (`manifest.segments`, contract @1.1). For bank items say "scenario", not "survey question".
- **K12:** resolved. Use `manifest.segments` (exact, from the exporter). The heuristic is gone.
- **K13:** confirmed. `attn_topk_mass` is the sum of the 16 stored attention probabilities for that row (1 = complete).
- **K15:** use the S18 wording ("this adapter changed no MLP weights"), shown only when `d_weight_mlp == 0`.
- **K17:** true. The paper's production model is Llama-3.1-8B with per-country LoRA adapters. The 135M is a stand-in so that every pass runs in float64 on a laptop and is checked.
- **K22:** `spec/conservation.md` is the slice-1 spec, and its RED status is historical. The current ground truth is `spec/export_contract.md` (the PM has marked this in that file).
- **K23:** the residual-closure gate is the maximum over every token position and every coordinate (`llama_capture.py:190`).
- **K19, K21, K14:** accept the writer's proposals.

**Left to Augusto, not blocking the port** (use the writer's proposed default meanwhile): K3 (how strong "exactly" is), K16 (call the clamp an intervention in Limits), K20 (describe the square-root colour scale or not), Q1 and Q2 (what "SCA2" and "Paper B" stand for, and the paper's terminology). Leave L01 as it is until he answers.

## 0. How to use this file

**For the port.**
- Every string below has an ID: `S` shared (`common.js`), `L` landing, `C` ladder (variant C), `M` matrix (variant B), `O` object (variant A), `P` pop-up.
- `current` is copied from the source. `proposed` is what to ship.
- `${…}` marks a value that is filled from live data. Keep it as a template. **No number in this file is a data value.** The fixed numbers that already exist in the copy (576, 30, 9, 1,536, 270, 46,080, 16, 0.05, and the thresholds 1e-3, 1e-2, 1e-10) are kept as they are.
- "new" means the string does not exist yet. "keep" means the current string is already right.
- Where a string says `${label_plus}` and `${label_minus}`, use `it.labels[it.codes.indexOf(it.j_plus)]` and the same for `j_minus`. `${j_plus}` is the code, for example "1".

**Five naming decisions, applied everywhere.** These are the cheapest clarity gains, so please apply them even where a row is not listed.

| Today | Use | Why |
| --- | --- | --- |
| "pass", "forward pass", "clamped pass" | "run", "clamped run". Keep "pass" only in "all checks pass". | "Pass" means pass/fail to this audience. |
| "readout", "readout position t*", "readout column" | "answer position (t*)". First use on each page: "the answer position t*: the last position of the prompt, where the model is about to write its answer". | One name for one thing. "Readout" stays in the glossary as a synonym. |
| "boilerplate", "template" | "template text" | "Boilerplate" is a judgement. The template is chat-format markers plus fixed instructions. |
| "write" for a head or MLP | "write" is kept, but always glossed once as "what it adds to the running state". "Contribution to the margin" is used for DLA, never "write". | Two different quantities (size of a write vs push on the margin) were sharing words. |
| "Δ", "B−A", "‖B−A‖" | See S12 and P07. Gold with no italics is the length of the change, from the export. Italic is a signed difference computed on the page. | Both sit under one column header today. |

**Terminology for A and B.** A is `SmolLM2-135M-Instruct` for the default pair. It is itself instruction-tuned. So "base" is wrong for A, and "base vs fine-tune" is only right for the default pair. Other pairs exist (`smol_base` → `smol_inst`). Write "A (the original model)" and "B (the fine-tuned model)" for the default pair, and take the labels from the registry (`model.label`) wherever a header shows them.

## 1. At a glance

**Top five changes by impact.**

1. **Define the margin, and say which way it points, on the first screen of every page (S02, L07, C10).** Today "margin" is never defined where it first appears. A reader cannot tell what positive means.
2. **Rebuild landing §2 in survey language (L15 to L20) and move the conservation table behind "details".** Show one status line and three plain checks. The six-row table with `‖·‖∞`, `hf64` and "teacher-forced" is for ML reviewers (P06).
3. **Fix the inspector's change column and the row labels (S12 to S17).** The column mixes the length of a change (`‖B−A‖`, always ≥ 0) with a signed difference (`B−A`). In `pm-c.png` the same column shows 26.56 next to −0.7006 and +0.894. Plain row labels, with array names moved to tooltips.
4. **Add the missing keys and empty states.** A colour key on the ladder (C20), an axis key on the 3D object (O12), a "what a cell is" strip on the matrix (M01), and a one-sentence first screen for each tab (§4). All three screenshots have no legend.
5. **Fix four copy bugs that come from templating (K2, K7, K10 and K11, K15).** "B ends −0.123 higher" when the change is negative (K2), the hero caption's hard-coded question text and model names (K10, K11), the ladder text that says the green check line is "above" (it is below; K7), and "LoRA leaves the MLP untouched" (a general claim made from one data value; K15).

**Strings proposed:** 130 (S 24, L 37, C 23, M 17, O 15, P 14). A pop-up counts as one string (title plus body); P03, P04, P10, P11 and P12 are new pop-ups, and S21, C01, C13 axis title, C20, M01, M16, O05 and L36 card 4b are new strings.

**Claims flagged:** 24, in §5. The ones to look at first are K1, K2, K3, K6, K9, K10.

## 2. String tables

### 2.1 Shared: `common.js` (appears on all three tabs)

| ID | Location | Current | Proposed | Why |
| --- | --- | --- | --- | --- |
| S01 | `readoutHTML`, card title | `Eq. 6 readout · ${item_id}` | `The model's answer · ${item_id}` | "Eq. 6" means nothing without the paper. It moves into the pop-up title (P01). |
| S02 | `readoutHTML`, new line under the title (new) | none | `Margin = logit(“${j_plus}”) − logit(“${j_minus}”). Positive means the model leans toward “${label_plus}” over “${label_minus}”.` | The margin is never defined or signed on screen. Both external readings of `pm-c.png` guessed at its direction. |
| S03 | `readoutHTML`, `.q` options line | `${code} ${label} · …` | `Answer codes: ${code} ${label} · …` | Names what the list is. |
| S04 | `readoutHTML`, bar headers | `A · margin ${…}` and `B · margin ${…}` | keep. Add a tooltip with `${model.label}` on each. | The full model names already appear in the header strip (C06). |
| S05 | `readoutHTML`, `.sub` line | `Δ margin ${sgn} · ΔP(“${j_plus}”) ${sgn} · purple tick = clamped pass` | `Change, B − A: margin ${sgn(d_margin)} · P(“${label_plus}”) ${sgn(d_probs[j_plus])}. Purple tick: the result when Quadrant III neurons are clamped.` | Shows the label, not just the code. Names the sign convention. "Clamped pass" becomes the glossed "clamped" (G14). |
| S06 | `readoutHTML`, status line, pass | `✓ conservation: every check passes for A and B` | `✓ The parts add up: every check passes for A and B` | "Conservation" is physics jargon. This is a balance-sheet check. |
| S07 | `readoutHTML`, status line, fail | `✗ conservation: a check FAILS` | `✗ A check failed. Do not read these figures as measurements until the export is fixed.` | Says what to do. The wording comes from the pop-up (P06), so no claim changes. |
| S08 | `readoutHTML`, status button | `details` | `see the checks` | "Details" of what? |
| S09 | `inspectorHTML`, card title, residual | `Residual · final state` / `Residual · entering L${l}` | `Running state · after the last layer` / `Running state · entering layer ${l}` | "Residual" collides with a regression residual (G05). |
| S10 | `inspectorHTML`, tag | `pinned` or `hover`, title `Esc clears` | `pinned` or `preview`, title `Press Esc to unpin` (preview: `Click to pin`) | "Hover" names an action, not a state. |
| S11 | `inspectorHTML`, `.tokline` | `t=${t} ${word}` and tag `readout t*` | `token ${t}: “${word}”` and tag `answer position (t*)` | Plain labels. Keep `t*` in the tag because other strings use it. |
| S12 | `inspectorHTML`, table header and footer | header `A, B, ‖B−A‖ / B−A`. Footer `‖B−A‖ is exact from the pair export; B−A in italics is a browser difference of two run arrays.` | header `A, B, Change`. Footer: `Change in gold = how far B's vector is from A's (a length, never negative), exact, from the pair export. Change in italics = B − A, a signed difference of two numbers, computed on this page.` | Two different quantities were under one header. See G17 and P07. |
| S13 | `compareRows`, head rows | `‖o‖ head write` / `DLA → margin` / `top-16 mass` | `Write size ‖o‖` / `Push on the margin (DLA)` / `Attention covered by the top 16` | Plain labels. Tooltips: `Length of the vector this head adds to the running state. It says how much, not which way.` / `How far this head's write moves the margin, read straight through the model's last steps.` / `Share of this head's attention that the 16 largest weights cover (flag K13).` Array names (`head_norm`, `head_attr`, `attn_topk_mass`) go in a second tooltip line. |
| S14 | `compareRows`, MLP rows | `‖m‖ MLP write` / `QIII neurons` / `DLA → margin` | `Write size ‖m‖` / `Quadrant III neurons (count)` / `Push on the margin (DLA)` | As S13. Tooltip for the count: `Neurons whose two input signals are both below −0.05 at this token.` |
| S15 | `compareRows`, residual rows | `‖h‖ residual` / `margin read here` | `Running-state size ‖h‖` / `Margin if read off here` | As S13. Tooltip for the second: `The margin you would get by reading the answer off the state at this layer (see K9).` |
| S16 | head card, key list | `where this head looks (top keys, A[q,k])` and rows `0.38 t=122 4` | `Where this head looks${t===ro ? " from the answer position" : " from this token"}: its largest attention weights` and rows `0.38 · token 122 “4”` | The `A[q,k]` notation is for people who know attention. The `from …` part is needed because the card also opens on non-answer tokens in the matrix and the object. |
| S17 | head card, weight line | `‖W_B−W_A‖_F q,k,v,o: a, b, c, d` | `How far this head's weights moved, B vs A (q, k, v, o): a, b, c, d`. Tooltip: `Frobenius norm: the square root of the sum of squared differences. 0 means untouched. k and v are shared by 3 heads.` | The symbol is unreadable to the audience. The tooltip's last sentence is in the spec. |
| S18 | MLP card, weight line | `‖W_B−W_A‖_F gate,up,down: …` and `(LoRA leaves the MLP untouched)` | `How far this MLP's weights moved, B vs A (gate, up, down): …` and, when `dw.get(l,0) === 0`, `(0: this adapter changed no MLP weights)` | The current text states a general fact about LoRA. It is a fact about this adapter (K15). |
| S19 | `segments()`, labels | `readout t*=${ro}` / `${role} turn begins` / `end of ${role} turn` / `system prompt · …` | `answer position t*=${ro}` / `${role} message starts` / `${role} message ends` / `system instructions · …` | "Turn" is chat jargon. |
| S20 | pills in the ladder and the matrix bands | `‹${label} · ${n} tok›` | `‹${label} · ${n} tokens›` | Spell out "tok". |
| S21 | tab bar (new, port card adds it) | none | `Ladder: what decided the answer` · `Matrix: where the change sits` · `3D object: the whole run` · right-aligned link `About ↗` | Names each tab by the question it answers (the landing text already does this). |
| S22 | every `learn more` button | `learn more` | keep the label. Add `title="Learn more: ${topic}"` and `aria-label` with the same text. | There are up to eight identical buttons on one screen. |
| S23 | the `.cons` line and `.lm` in the landing | `details` | `see the checks` | Same as S08. |
| S24 | embedding card (ladder), title (`inspect`, `s.l < 0`) | `Embedding term` | `Embedding term`. Tooltip: `What the word's starting vector (before layer 0) contributes to the margin.` | The term is correct. It needs a gloss (G21). |

### 2.2 Landing: `landing.html`

| ID | Location | Current | Proposed | Why |
| --- | --- | --- | --- | --- |
| L01 | nav, brand | `SCA2 workbench · paper B companion` | `SCA2 workbench · companion to Paper B` | Reads as a sentence. **Open question:** the page never says what "SCA2" or "Paper B" are (Q1). |
| L02 | nav links | `the model` · `the measures` · `the views` · `limits` · `open the workbench →` | `How it works` · `What we measure` · `The three views` · `Limits` · `Terms` (new) · `Open the workbench →` | Verb and question forms. "Terms" opens the glossary pop-up (P12). |
| L03 | `h1` | `Where does a language model's survey answer come from?` | keep | Good: a plain question, no jargon. |
| L04 | `.lede` | `We ask a small language model a World Values Survey question, read its answer as a probability over the response codes, and then trace that probability back through every layer, attention head and neuron that produced it. Then we fine-tune the model toward one country's answers and measure, exactly, what moved.` | `We ask a small language model a survey question from the World Values Survey. Its answer is a probability for each response code, like the predicted shares from a choice model. We split that answer into the contributions of the model's parts and check that they add up. Then we fine-tune the model toward one country's answers and compare the two, part by part.` Add a second line in smaller type: `Written for readers who know regression and survey items. No machine-learning background assumed.` | "Neuron", "trace back through every layer, head" and "exactly what moved" all arrive before anything is defined. Two long sentences become five short ones. The last sentence keeps "check" but drops "exactly" (K3). |
| L05 | `.cta` | `Open the workbench` · `How it works ↓` | keep | Clear. |
| L06 | hero badge | `real data · one forward pass each` | `real data · one run of each model` | "Forward pass" is jargon. The badge itself stays. |
| L07 | hero SVG title | `margin read from each layer, logit(“${j_plus}”) − logit(“${j_minus}”)` | `The margin as it builds up, layer by layer: logit(“${j_plus}”) − logit(“${j_minus}”). Positive = toward “${label_plus}”.` | Defines the sign. The "read from each layer" claim is flagged (K9). |
| L08 | hero SVG x-axis | `layer (the residual state entering it; the last point is the final state)` | `after l layers (0 = the starting vector, ${L} = the final state)` | Plain. Same meaning: state l enters layer l. |
| L09 | hero SVG line labels | `A · Instruct` / `B · +USA LoRA` | `A · original` / `B · fine-tuned`, from `${model.label}` where the label fits | Hard-coded names break for other pairs (K11). |
| L10 | `heroCap` | `WVS ${question_id}: “How much confidence do you have in charitable or humanitarian organizations?” Each dot is h^l_t*·w (running_margin): the answer you would read off the residual stream after l layers. ${story()}` | `${item_name}: “${question_text}” Each dot is the margin you would get by reading the answer off the running state after l layers. ${story()}` | The question text is typed in the source, not read from the data (K10). `running_margin` and the formula go to a tooltip. "Residual stream" becomes "running state". |
| L11 | `story()` | `The largest split is in layer ${bl}: A goes ${a0} → ${a1}, B goes ${b0} → ${b1}. The single head whose attribution changed most is L${hl} h${hh} (${sgn(hv)}). B ends ${sgn(d_margin,3)} higher.` | `Layer ${bl} is where A and B differ most in what they add to the margin: A goes ${a0} → ${a1} there, B goes ${b0} → ${b1}. The head whose push on the margin changed most (B − A) is layer ${hl}, head ${hh} (${sgn(hv)}). Overall, B's margin is ${sgn(d_margin,3)} relative to A's. Positive means further toward “${label_plus}”.` | Template only; the numbers still come from the arrays. Fixes "B ends −0.2 higher" and the unexplained word "split" (K2). |
| L12 | §1 side label, `h2` | `1 · what a transformer computes` / `A running total, written to by many small parts` | `1 · what is inside the model` / keep the `h2` | The `h2` is clear and worth keeping. "Transformer" is dropped from the heading. |
| L13 | §1 paragraph 1 | `A transformer turns the prompt into tokens (word pieces) and gives each token a vector of 576 numbers. That vector is the **residual stream**: a running state that every layer reads and then adds to. Nothing overwrites it. This model has 30 layers.` | `The model cuts the prompt into tokens (word pieces). Each token gets a list of 576 numbers. We call that list the **running state**. Every layer reads it and adds to it. Nothing is overwritten, like a ledger where each layer posts new entries. This model has 30 layers.` | "Residual stream" is the ML name; "running state" is used on screen, and the term is glossed once (G05). The ledger image is the same fact as "adds, never overwrites". |
| L14 | §1 paragraph 2 | `Each layer adds two kinds of writes. **Attention heads** (9 per layer) move information between tokens: each head decides which earlier words to read from and writes a summary. The **MLP** (1,536 neurons per layer) then transforms each token on its own. After the last layer, the final state at the last position is turned into a score for every possible next token.` | `Each layer adds two kinds of entries. **Attention heads** (9 per layer) let a token look back at earlier tokens: each head picks which earlier words to read from and adds a summary. The **MLP** (a small neural network, 1,536 hidden units per layer) then transforms each token on its own. After the last layer, the final state at the last position is turned into a score for every possible next token.` | "Neuron" is defined as "hidden unit". Same facts. |
| L15 | §1 paragraph 3 | `Because everything is added, the final score can be split into the parts that wrote it. That is the property the whole workbench rests on.` | `Because everything is added, the final score can be split into the parts that added to it. The split is exact for the margin when the final rescaling is held fixed (see section 2). That is the property the whole workbench rests on.` | The unqualified "final score can be split" is not true for probabilities, and needs the frozen-scale condition (K6). The added clause is in the spec. |
| L16 | §1 illustration caption | `Schematic of one token's path. Three of 30 layers drawn; head count and widths are not to scale. No mark here is a measurement.` | keep. Make "30" a template: `Three of ${L} layers drawn`. | Good. The badge stays. |
| L17 | §1 heat figure badge and caption | badge `real data · ‖h^l_t‖ for every token and layer`. Caption `A, ${T} tokens left to right, layer state 0 (bottom) to 30 (top). Bands above: chat template and boilerplate (grey), question and options (blue), readout t* (bright). Most of the prompt is boilerplate, which is why the workbench collapses it by default. Colour: log scale, clipped at the 99th percentile (resid_norm).` | badge `real data · size of the running state at every token and layer`. Caption `Model A. ${T} tokens run left to right; layers run from 0 (bottom) to ${L} (top). Brighter means a longer vector. Bands above: template text (grey), question and options (blue), the answer position t* (bright). Most of the prompt is template text, which is why the workbench collapses it by default. Colour is on a log scale, clipped at the 99th percentile.` | "Size" replaces `‖·‖`. The array name `resid_norm` goes in a tooltip. The "question and options" claim depends on a heuristic (K12). |
| L18 | §2 side label and `h2` | `2 · what the workbench measures` / `One number, decomposed exactly` | `2 · what we measure` / `One number, split into parts that add up` | "Decomposed exactly" invites the question "exactly how?" (K3). |
| L19 | §2 paragraph "The answer (Eq. 6)" | `At the last position the model scores every next token. We keep only the response codes and renormalise. That gives a choice probability over the answer options — the same object a survey researcher would model with a multinomial logit.` | `**The answer.** At the answer position the model gives a score to every possible next token. We keep only the scores for the response codes and turn them into probabilities. This is the same form as a multinomial logit: the scores play the part of the linear index, and the probabilities are the choice shares. (This is Eq. 6 of Paper B.) The **margin** is the gap between the scores of two codes. It equals the log of their odds, and positive means the model leans toward the first.` | Lead with the survey object. Drops "renormalise". "Same object" becomes "same form": a softmax over the codes is a multinomial-logit form, which is as far as the spec goes (K4). The margin sentence is exact, because P(j₊)/P(j₋) = exp(z_j₊ − z_j₋). |
| L20 | §2 equation | `P(code j \| prompt) = exp(z_j) / Σ_{k ∈ codes} exp(z_k)    margin = z_j₊ − z_j₋` | keep the equation. Add a line under it: `z is the model's raw score for a code. The probability is that code's share of exp(score) among the response codes.` | The equation is fine for this audience. It lacked a reading of `z`. |
| L21 | §2 paragraph "The decomposition (DLA)" | `Direct logit attribution reads each part's write straight through the final layer. With the final normalisation scale held fixed, the margin is exactly the sum of an embedding term, 270 head terms and 46,080 neuron terms. Think of it as an accounting identity, like splitting a gap into components: every cell adds up, and nothing is left in a residual.` | `**The split.** Direct logit attribution (DLA) gives each part a share of the margin, like splitting a logit index into its β·x terms. Each part's entry is read straight through the model's last steps, with the final rescaling held fixed. Then the margin is the sum of an embedding term, 270 head terms and 46,080 neuron terms, with nothing left over. This is the direct effect only: a part that changes what a later layer does gets no credit for that path (see Limits).` | "Residual" is dropped because it reads as a regression residual (K5). The β·x analogy is the brief's. The direct-effect caveat is moved up to where the decomposition is introduced; it was only in §4. |
| L22 | §2 paragraph "The checks" | `Every pass is run in float64 and must close: the residual stream must equal its parts to 1e-3, the attribution must sum to the margin to 1e-2, and our forward pass must agree with Hugging Face's reference implementation to 1e-10. If a check fails, the workbench shows it in red next to the readout.` | `**The checks.** Every run uses 64-bit arithmetic (float64) and has to pass three tests. (1) The parts add up to the final state, to within 1e-3. (2) The parts add up to the margin, to within 1e-2. (3) Our code reproduces the Hugging Face reference implementation to within 1e-10 (relative), once the reference's own 32-bit rounding steps are switched off. If a check fails, the status line next to the answer turns red. The numbers are in the table below.` | Plain names for the three checks, same thresholds. The qualifier on check 3 is in the spec and is missing today (K1). |
| L23 | §2 paragraph "Base vs fine-tune" | `The same prompt is run through two models: A (SmolLM2-135M-Instruct) and B (A plus a small LoRA adapter trained with DPO on USA survey answers). For every slice, the pair export stores the exact length ‖B − A‖ from both passes, and the size of the weight change.` | `**Before and after.** The same prompt goes through two models. A is ${A.label}. B is ${B.label}: A plus a small add-on (a LoRA adapter) trained with DPO on USA survey answers. For every layer and token, we store how far B's vector is from A's, and also how far the weights moved.` | Template the model names (K11). "Slice" and "‖B − A‖" are explained or dropped. "Exact length" moves to P07. |
| L24 | §2 figure: probabilities | badge `real data · Eq. 6 probabilities`. Caption `readout.probs for each model; the purple tick is the pass with Quadrant III neurons clamped. ΔP(“${j_plus}”) = ${sgn}.` | badge `real data · the model's answer probabilities`. Caption `Probability of each answer code, for A and B. The purple tick marks the result when Quadrant III neurons are clamped. Change in P(“${label_plus}”), B − A: ${sgn(d_probs[j_plus])}.` | Plain. Array name to a tooltip. |
| L25 | §2 figure: Δ margin by layer | badge `real data · where Δ margin accumulates`. SVG title `B − A of DLA per layer · attention · MLP`. Caption `Bars are attn_attr and mlp_attr of B minus A (browser difference). Bars + embedding change sum to ${sum}; the exported Δ margin is ${d_margin}. ${cond}` | badge `real data · which layers changed the margin`. Title `Change in each layer's push on the margin, B − A · attention · MLP`. Caption `Each bar is B's push minus A's push, computed on this page. The bars plus the change in the embedding term add up to ${sum}. The exported change in margin is ${d_margin}.` Keep the condition: when `d_weight_mlp` is all 0, add `The adapter changed no MLP weights, yet the MLP bars are not zero. Their inputs changed in earlier layers.` | Same facts, plain order. The conditional stays as it is: it is data-driven and matches the spec. |
| L26 | §2 figure: conservation | badge `real data · conservation, both passes`. The full six-row table is inline. | badge `real data · do the parts add up? (A and B)`. Show **one status line and three rows** (see P06). The full table sits behind `see all six checks`. | The PM's note: this table is for ML reviewers. |
| L27 | §3 side label, `h2` | `3 · how to read the views` / `Three ways into the same pass` | `3 · the three views` / `Three views of the same model run` | Plain. |
| L28 | §3 paragraph | `All three views draw the same exported arrays. Pick by the question you have. **Which parts decided the answer?** Start with the ladder. **Where in the prompt and the depth did the fine-tune change things?** Use the matrix. **What does the whole computation look like?** Use the 3D object. Every mark names its array; hover anything to see the A, B and ‖B − A‖ values side by side.` | `All three views draw the same saved numbers from the same run. Pick by the question you have. **Which parts decided the answer?** Start with the ladder. **Where, in the prompt and in depth, did the fine-tune change things?** Use the matrix. **What does the whole run look like?** Use the 3D object. Hover anything to compare A and B.` | "Arrays" is dropped from the body (it stays in tooltips). The last claim, "every mark names its array … ‖B−A‖", is too wide for the ladder (K18); the shorter text claims less. |
| L29 | §3 card: ladder | `The readout ladder` / `Every head and MLP at the answer position, A \| B \| B − A. Each column sums to its margin. The prompt is shown as text, shaded by where the selected head looks.` | `The ladder` / `Every attention head and MLP at the answer position, in three panels: A, B and B − A. Each panel adds up to its margin. The prompt is shown as text, shaded by where the selected head looks.` | "Column" was a panel. "Readout" is replaced. |
| L30 | §3 card: matrix | `The matrix` / `Layer × token heatmaps for A, B and ‖B − A‖ with one shared crosshair. Boilerplate is squeezed, not dropped. Charts of the readout column below.` | `The matrix` / `Heatmaps of layer by token for A, B and the change ‖B − A‖, with one shared crosshair. Template text is squeezed, not dropped. Charts for the answer position are below.` | Plain. |
| L31 | §3 card: object | `The object` / `The original 3D tensor blocks, with template text collapsed into labelled gaps, a prompt map, token search and camera presets.` | `The 3D object` / `The whole run as 3D blocks (token by layer by size). Template text is collapsed into labelled gaps. There is a prompt map, a word search and camera presets.` | "Tensor blocks" is dropped. The axes are named (from `viewer/README.md`). |
| L32 | §4 side label, `h2` | `4 · limits` / `What this does not show` | `4 · limits` / `What this does not show` | keep |
| L33 | §4 card "Direct effect only" | `DLA credits each part for what it writes straight to the answer. A head that changes what a later layer does gets no credit for that indirect path. Large DLA is not the same as “causes”; that needs ablation or patching.` | `DLA credits each part for what it adds straight to the answer. A head that changes what a later layer does gets no credit for that indirect path. In regression terms, it is a direct effect with the mediators held out. A large DLA does not show that the part causes the answer; that needs ablation or patching.` | Adds the mediation analogy. "Causes" claim kept as is. The clamped run is an ablation of one neuron group, which the card does not mention (K16). |
| L34 | §4 card "A 135M stand-in" | `SmolLM2-135M is a small model chosen so that every pass can be run in float64 and checked. The paper's models are larger. Patterns here are a method demonstration, not findings about those models.` | `SmolLM2-135M is a small model, chosen so that every run can be done in float64 and checked. The paper's models are larger. Patterns here show the method. They are not findings about those larger models.` | Shorter. Both factual claims are untouched and flagged (K17). |
| L35 | §4 card "Norms hide direction" | `Block heights are lengths of vectors. Two writes of equal length can point in unrelated directions; only the readout column (DLA) says which way a write pushes the answer.` | `Block heights are the lengths of vectors. Two writes of equal length can point in unrelated directions. Only the answer-position numbers (DLA) say which way a write pushes the answer.` | "Readout column" replaced. |
| L36 | §4 card "Stored top-16 attention" (split into two cards) | `Attention lines and prompt shading use the 16 largest weights per row; the stored mass says how much of the row they cover. One prompt per view; nothing here averages over items.` | Card 4a, `Only the top 16 attention weights are kept`: `For each head and token we keep the 16 largest attention weights. Attention lines and prompt shading use only those. The “covered” figure says how much of the head's total attention they account for.` Card 4b (new), `One question at a time`: `Each view shows one prompt. Nothing here averages over questions, so nothing here is a statistic about a population.` | The two ideas were in one card. The new card's second sentence restates "nothing averages over items" in the audience's terms. No claim is added. |
| L37 | footer | `Every figure marked “real data” is drawn in your browser from workbench/exports/ (contract sca2-workbench/capture@1): pair ${pair}. Figures marked “illustration” bind to nothing. See design/NOT_A_BINDING.md.` | `Every figure marked “real data” is drawn in your browser from files in workbench/exports/ (format sca2-workbench/capture@1; pair ${pair}). Figures marked “illustration” use no data.` | "Bind to nothing" and the internal design file are for developers. |

### 2.3 Ladder (default tab): `variant-c.html`

| ID | Location | Current | Proposed | Why |
| --- | --- | --- | --- | --- |
| C01 | first-screen strip (new), full width above the three columns | none | `Each cell is one part of the model at the answer position. Blue pushes the answer toward “${label_plus}”, orange toward “${label_minus}”. Each of the three panels adds up to its margin.` Right-aligned: `How to read this ↗` (opens P03, "answer position"). | One sentence orients a first-time reader. It states the colour meaning that no screen carries today. |
| C02 | top bar, link | `about` | `About` | Capital; consistent with S21. |
| C03 | top bar, group 1 | `pass [normal] [Quadrant III clamped]` | `Model run [normal] [Quadrant III clamped]` with a `what's this?` link to P10 | "Pass" to "run" (naming table). |
| C04 | top bar, group 2 | `shade prompt by [A] [B] [B − A]` | `Shade the prompt by attention in [A] [B] [B − A]` | Says what is being shaded, and that it is attention. |
| C05 | top bar, find | placeholder `word in the prompt` | `Find a word in the prompt` | A prompt for action. |
| C06 | top bar, `#who` | `A ${A.label} · B ${B.label} · ${item_id}` | `A: ${A.label} (original) · B: ${B.label} (fine-tuned) · ${item_id}` | Defines A and B once, visibly, on every tab. For non-default pairs, drop "(original)" and "(fine-tuned)" and use the registry labels only (K11). |
| C07 | prompt column, `h4` | `The prompt, as the model read it` | keep. Button `learn more` becomes `what are these grey pills?` (opens P09). | The heading is good. The pills are the first unexplained object. |
| C08 | prompt column, `#plegend` with a head selected | `shading = attention from t* of L${l} h${h} in ${A/B/B − A} · stored top-16 keys (attn_topk_val); a pill shows the sum over its tokens` | `Shading: how much head ${h} of layer ${l} reads each word when it is about to write the answer (model ${A/B}, or B − A). Only its 16 largest weights are stored. A grey pill shows the total for the words it hides.` For B − A: `gold = B reads this word more, blue = less`. | Plain. "Keys", `attn_topk_val` and "Σ" are dropped. |
| C09 | prompt column, `#plegend` with nothing selected | `hover or click a head in the ladder to see where it looks from the readout. Cmd-F works here: this is the text.` | `Hover or click a head in the ladder to see which words it reads. Your browser's find (Ctrl/Cmd-F) works on this text.` | "Cmd-F" is Mac-only. |
| C10 | ladder column, `h4` | `Where the margin comes from · every head and MLP at the readout t*` | `What pushed the answer: every attention head and MLP, at the answer position` Button: `learn more` becomes `what is DLA?` (opens P05). | The question the tab answers. The button names the unfamiliar term. |
| C11 | ladder, group title and subtitle | `A` / `B` / `B − A` and `heads 0–8 · MLP` | `A · original` / `B · fine-tuned` / `B − A` and `9 heads, then the MLP` | Same naming as C06. |
| C12 | ladder, per-group check, lines 1 and 2 | `✓ Σ cells + embed = ${sum}` and `margin ${target} (export)` or `Δ margin ${target} (B−A, browser sum)` | `✓ All cells + embedding = ${sum}` and `margin ${target} · from the export`. For B − A: `change in margin ${target} · computed on this page from A and B`. | "Σ" and "browser sum" are removed. The line keeps the export/computed distinction, which is the honest bit. K19 flags "adds up exactly". |
| C13 | ladder, row labels and axis | `L0`, `L5`, … `L29` | keep. Add an axis title (new): `layer (0 = first, at the bottom)` | The axis has no title today. |
| C14 | ladder, bottom row label | `embed` | `embedding` | No abbreviation. |
| C15 | ladder, line chart header | `margin by layer` / `h^l·w · A blue, B sand` | `Margin by layer` / `The margin if the answer were read off at each layer. A blue, B sand.` | Defines the chart. It carries the K9 caveat via the tooltip `Read with the final layer's rescaling held fixed.` |
| C16 | ladder, cell tooltip | `${group} head ${h} L${l}: DLA ${v}` or `… MLP L${l}: DLA ${v}` | `${group} · layer ${l} · head ${h} · push on the margin ${sgn(v)}` | Unsigned today. A sign is the whole point of the cell. |
| C17 | side panel, idle card (the empty state) | title `Inspector`, button `what is a head?`. Body `Each cell of the ladder is one head (or MLP) and how hard it pushes the answer: blue toward “${label_plus}”, orange toward “${label_minus}”. Each group adds up to its margin exactly (green line above it). Hover a cell to compare A and B here and to see, on the left, which words that head reads.` | title `Compare A and B for one part`. Body `Hover a cell in the ladder to compare A and B here. Click to pin it. The left column then shows which words that head reads.` Button `what is a head?` stays. The colour sentence moves to C01 and C20. | "Green line above it" is wrong: the check line is below each panel (K7). The empty state now says what to do, not what the colours are. |
| C18 | side panel, embedding card | `Embedding term` / row `DLA` / `A, B, B−A` | `Embedding term` / row `Push on the margin` / `A, B, Change` | Matches S12 and S13. |
| C19 | side panel, clamped row | `DLA, clamped pass` | `Push on the margin, clamped run` | Naming table. |
| C20 | colour key (new), under the ladder's three panels | none | `Blue = pushes toward “${label_plus}”. Orange = toward “${label_minus}”. Grey = about zero. Colour deepens with size, up to ±${vmax} on this scale.` | There is no key. Both external readings of `pm-c.png` could not tell what blue vs orange meant. `vmax` is already computed in `ladder()`. Colour is on a square-root scale (K20). |
| C21 | prompt tooltip (`#ptip`) | `t=${t} ${word}`, then `L${l} h${h} attention from t*:  A ${a}  B ${b}  B−A ${d}`, then `‖h‖ final state:  A ${…}  B ${…}  ‖Δ‖ ${…}` | `token ${t}: “${word}”`, then `Head ${h}, layer ${l}, attention from the answer position: A ${a}, B ${b}, B − A ${d}`, then `Final-state size: A ${…}, B ${…}, change ${…}` | Plain. |
| C22 | prompt column, readout token | `t*` (boxed) | keep the box. Tooltip: `answer position (t*): where the model is about to write its answer`. | The box is the visual anchor. It needs the gloss on hover. |
| C23 | pills | `‹${label} · ${n} tok · Σ ${sum}›` | `‹${label} · ${n} tokens · total attention ${sum}›` (the last part only when a head is selected) | "Σ" dropped. |

### 2.4 Matrix: `variant-b.html`

| ID | Location | Current | Proposed | Why |
| --- | --- | --- | --- | --- |
| M01 | first-screen strip (new) | none | `Each cell is the size of one vector at one layer (rows) and one token (columns). Brighter means larger. This shows where activity is large, not which way it pushes the answer.` Link: `What is the size of a vector? ↗` (P04) | The matrix has no key. The second sentence is the "norms hide direction" limit, put where it is needed. |
| M02 | top bar, quantity group | `quantity [residual ‖h‖] [attention ‖a‖] [MLP ‖m‖]` | `Show [Running-state size ‖h‖] [Attention write size ‖a‖] [MLP write size ‖m‖]` | Plain names, symbols kept as secondary text. |
| M03 | top bar, find | `find token` / placeholder `type, Enter to jump` | `Find a word` / `Type a word, press Enter` | |
| M04 | top bar, prompt toggle | button `boilerplate squeezed` ⇄ `all tokens equal width` | `Template text: squeezed` ⇄ `Template text: full width`. Tooltip: `Squeezed columns are 2 px wide. Every token still has a column.` | The label says what is being toggled. The tooltip is from the code. |
| M05 | top bar, `#who` | `A ${A.label} · B ${B.label} · ${item_id} · ${T} tokens` | as C06, then `· ${T} tokens` | |
| M06 | map header, per map | `${k} · ${label}` and `${src} · rows = layer state 0…30 (top = last) · one log scale shared by A and B` or `own Δ scale` | Line 1: `A · ${A.label}: size of the running state, by layer and token`. Line 2: `Rows: layers, first at the bottom. Colour: one log scale shared by A and B.` For the change map: line 1 `‖B − A‖: how far B's state is from A's, by layer and token (exact, from both float64 runs)`; line 2 `Rows: layers, first at the bottom. Colour: its own scale (gold), so it cannot be compared with A and B.` The array name (`resid_norm`, `d_resid_norm`) moves to a tooltip. | The map titles are now sentences. The warning that the gold map is on a different scale is stated, not just implied. |
| M07 | map header buttons | `learn more` (scale), `learn more` (delta) | `how are colours scaled?` (P09 scale) and `what is ‖B − A‖?` (P07) | Names the unfamiliar term. |
| M08 | chart 1 title and legend | `Margin read from each layer (h^l_t*·w)` and legend `A · B · clamped (dashed)` | `Margin if the answer were read off at each layer` and legend `A · B · clamped run (dashed)` | See K9. |
| M09 | chart 2 title and legend | `DLA per layer at t* (attention ▮ MLP ▯)` and `right of 0 = toward “${j_plus}”` | `Push on the margin, layer by layer (attention ▮, MLP ▯)` and `right of 0 = toward “${label_plus}” (code ${j_plus})` | The legend printed the code, not the label. The glyphs ▮ ▯ get a plain key: `filled = attention, outlined = MLP`. |
| M10 | attention card title and tag | `Attention · layer ${l}` and `pinned · Esc` or `hover` | `Attention · layer ${l}` and `pinned (Esc to unpin)` or `preview` | As S10. |
| M11 | attention card, table row | `‖a‖ layer write` | `Write size of the whole layer's attention ‖a‖` | Plain. |
| M12 | attention card, sub-heading | `the nine heads of this layer (head_norm, A ▮ B ▯ Δ ▬) — click one` | `The nine heads in this layer. Each has three bars: A's write size, B's write size, and the change (gold). Click a head.` | The glyph key is unreadable. |
| M13 | attention card, footer | `bars share one linear axis: max = ${v}` | `All bars use one linear scale. The longest bar is ${v}.` | |
| M14 | attention card, back button | `← layer ${l} attention` | `← Back to layer ${l} attention` | |
| M15 | side panel, idle card (the empty state) | title `Inspector`. Body `Hover any cell: the same layer and token light up in A, B and ‖B−A‖, and this card compares them. Click to pin. Click a band in the axis to open or squeeze a prompt segment.` | title `Compare A and B for one cell`. Body `Hover a cell: the same layer and token light up in all three maps, and this card compares A, B and the change. Click to pin. Click a band above a map to open or squeeze that part of the prompt.` | Same facts, in the order of use. |
| M16 | segment band, tooltip (new) | none | `Click to open or squeeze: ${label}` | The bands are clickable but give no hint. |
| M17 | token axis labels | rotated token text, cut to 9 characters | keep. Add a tooltip with the full token. | |

### 2.5 3D object: `variant-a.html`

| ID | Location | Current | Proposed | Why |
| --- | --- | --- | --- | --- |
| O01 | top bar, view group | `view [A only] [A \| B] [A \| ‖B−A‖]` | `Show [A only] [A next to B] [A next to the change ‖B − A‖]` | Pipes read as "or". |
| O02 | top bar, camera group | `camera [readout] [overview] [top-down] [layer stack]` | `Camera [answer position] [whole object] [from above] [layer stack]` | |
| O03 | top bar, find | `find token` / placeholder `e.g. confidence, Answer, 4` | `Find a word` / placeholder `e.g. confidence, Answer, 4` | |
| O04 | top bar, segments button | `open all segments` ⇄ `collapse boilerplate` | `Show all template text` ⇄ `Collapse template text` | Naming table. |
| O05 | axis and colour key (new), one line under the top bar | none | `Left to right: tokens in the prompt. Front to back: layers (layer 0 is nearest). Height: the size of the vector. In the blue-outlined answer column, blue pushes toward “${label_plus}” and orange toward “${label_minus}”. Everywhere else, colour only names the kind of block.` | There is no axis key and no colour key. The sentences are from `viewer/README.md` and the "Heights and colours" pop-up. |
| O06 | panel labels | `A · ${A.label}` / `B · ${B.label}` / `‖B − A‖ · B = ${B.label}` | `A · ${A.label}` / `B · ${B.label}` / `Change ‖B − A‖ · B is ${B.label}` | |
| O07 | prompt-map caption, left | `prompt map · each column a token, each row a layer state: ‖h^l_t‖ (resid_norm, A; log colour clipped at p99) — ${values or change}` | `Prompt map. Each column is a token and each row a layer. Brightness is the size of the running state in A, on a log scale clipped at the 99th percentile${delta: ". Showing the change ‖B − A‖ instead"}.` | Plain. The array name goes to a tooltip. |
| O08 | prompt-map caption, right | `click a segment to open or collapse it · bracket = tokens in view` | `Click a band to open or collapse that part of the prompt. The white bracket marks the tokens now in view.` | |
| O09 | side panel, idle card (the empty state) | title `Inspector`, button `what is DLA?`. Body `Hover any block: this card shows A, B and the exact ‖B−A‖ for that slice. Click a head to pin it and draw where it looks, in both panels.` | title `Compare A and B for one block`. Body `Hover a block to compare A, B and the change. Click a head to pin it and draw where it looks, in both panels.` Button `what is DLA?` stays. | "Slice" dropped. |
| O10 | side panel, list title | `Largest changes at the readout` and button `learn more` | `Heads whose write changed most at the answer position` and button `what is ‖B − A‖?` | The list ranks by `d_head_norm` (how much the head's write changed), not by DLA (how much its push on the margin changed). The title must say which (K14). |
| O11 | side panel, list footer | `‖o_B − o_A‖ at t*, from d_head_norm. Click to fly there and pin.` | `Each bar is ‖o_B − o_A‖ at the answer position: how far B's write is from A's. Click a row to fly there and pin it.` | |
| O12 | gap label in the scene | `⋯ ${label} · ${n} tok` | `⋯ ${label} · ${n} tokens (collapsed)` | |
| O13 | search results | `(collapsed)` / `no token matches` | `(collapsed, will open)` / `No word matches` | Says what selecting it does. |
| O14 | margin line label | `margin ${v}` | `margin ${v}` | keep |
| O15 | hover tooltip in the scene | `${kind} L${l} h${h} · t=${t} ${word}` | `${Head / MLP / State} · layer ${l}${h != null ? " · head " + h : ""} · token ${t} “${word}”` | |

### 2.6 Pop-ups: `learnText` (titles; bodies follow)

| ID | Key | Current title | Proposed title | Why |
| --- | --- | --- | --- | --- |
| P01 | `eq6` | `Eq. 6 — the survey answer as a probability` | `The answer as a probability (Eq. 6)` | Plain first. |
| P02 | `head` | `An attention head` | `What is an attention head?` | Questions. |
| P03 | `tstar` (new) | none | `The answer position (t*)` | Opened by C01. The answer position is the term the whole workbench rests on. |
| P04 | `norm` (new) | none | `What is the size of a vector (‖·‖)?` | Opened by M01. |
| P05 | `dla` | `Direct logit attribution (DLA)` | `How much did each part push the answer? (DLA)` | |
| P06 | `conservation` | `Conservation checks (why you can trust the numbers)` | `Do the parts add up? The checks` | "Why you can trust the numbers" claims too much: passing checks show the arithmetic is consistent, not that an interpretation is right (K8). |
| P07 | `delta` | `‖B − A‖ — what the fine-tune changed` | `What the fine-tune changed: ‖B − A‖ and B − A` | Names both. |
| P08 | `mlp` | `An MLP block` | `What is an MLP block?` | |
| P09 | `segments` | `Collapsed prompt segments` | `Template text and collapsed parts of the prompt` | Also opened by C07. |
| P10 | `clamp` (new) | none | `Quadrant III and the clamped run` | The ladder's button had no pop-up at all. |
| P11 | `models` (new) | none | `The two models: A and B` | Opened from the `who` strip. |
| P12 | `terms` (new) | none | `Terms` | The glossary of §3, in short form. Opened from the landing nav. |
| P13 | `resid` | `The residual stream` | `The running state (residual stream)` | |
| P14 | `scale` | `Heights and colours` | `Heights and colours` | keep the title. The body adds the clipping sentence (K21). |

#### Pop-up bodies (proposed)

For every body: keep the formulas and array names that are already there. Move them to the end under a muted `For reference` line. Do not delete them.

**P01 `eq6`**
> The model reads the whole prompt. At the last position (t* = ${ro}) it gives a score to every possible next token. We keep only the scores for the response codes (${codes}) and turn them into probabilities with a softmax. This is the same form as a multinomial logit, restricted to the response codes. It is Eq. 6 of Paper B. We also compute the same probabilities a second way, by scoring each full answer token by token. A test checks that the two agree. The largest gap is ${fmt(eq6_teacher_forced_max_abs_gap, 2)}.
>
> The **margin** is logit(“${j_plus}”) − logit(“${j_minus}”). Positive means the model leans toward “${label_plus}”. Because of the softmax, the margin is also the log of the odds of “${j_plus}” against “${j_minus}”. Every “push on the margin” figure in the workbench splits this one number.

(Meaning kept: the two sentences about the test and the margin. Added: the log-odds sentence, which follows from the softmax. "Teacher-forced" is glossed in G22, so it is dropped from the body. See K5 for the test-vs-information question.)

**P02 `head`**
> When the model works on a word, an attention head looks back at the earlier words and takes a weighted average of what it finds there. The weights (the attention weights, A[q,k]) are positive and add to 1, like kernel weights. The head then adds a summary, a list of 576 numbers, to the running state. This model has nine heads in each layer. They share three sets of key and value inputs.
>
> The block height is the **size of that summary**, ‖o_h‖. It says how much the head adds, not which way. “Where this head looks” lists the stored 16 largest attention weights. At the answer position the head also has a DLA value: how much its addition moves the margin, read straight through the model's last steps.
>
> *For reference:* o_h = softmax(q kᵀ/√64 + causal) v_kv(h) W_O[:,h]ᵀ. Arrays: `head_norm`, `attn_topk_idx/_val`, `head_attr`.

**P03 `tstar` (new)**
> A prompt is a list of tokens (word pieces). The model writes its answer right after the last one. That last position is called t*. Here t* = ${ro}. The answer probabilities, the margin, and every “push on the margin” number are read at this one position. Other positions are shown for context. Think of t* as the one row of the data where the outcome is evaluated.

**P04 `norm` (new)**
> A vector here is a list of numbers (576 for a running state). Its size, written ‖v‖, is the usual length: the square root of the sum of squares. Bigger means the part wrote more. It does not say in which direction. Two vectors of equal size can push the answer opposite ways. Only the DLA numbers at the answer position carry a direction.

**P05 `dla`**
> Direct logit attribution (DLA) splits the margin into additive pieces, like splitting a logit index into β·x terms. Each part's addition is read straight through the model's last steps with w = γ_final ⊙ (W_U[j₊] − W_U[j₋]) / ρ, where the final rescaling ρ is held fixed. Then the margin is exactly the embedding term + Σ heads + Σ neurons. Blue pushes toward “${label_plus}”, orange toward “${label_minus}”.
>
> **Limit.** DLA is the direct effect only, like a direct effect in a mediation model. A head that changes what a later layer does gets no credit for that path.

**P06 `conservation`** (a status sentence and a three-row table first; the six-row table behind `show all six checks`)
> Three questions. Do the parts add up to the final state? Do they add up to the margin? Does our code give the same numbers as the reference implementation? All three have to pass, for both models.
>
> | Check | Must be below | A | B |
> | --- | --- | --- | --- |
> | The parts add up to the final state (largest gap in any coordinate) | 1e-3 | ${fmt(cA.residual_closure_inf,2)} | ${fmt(cB.residual_closure_inf,2)} |
> | The parts add up to the margin (absolute gap) | 1e-2 | ${fmt(cA.dla_gap,2)} | ${fmt(cB.dla_gap,2)} |
> | Same check, Quadrant III clamped run | 1e-2 | ${fmt(cA.dla_gap_clamped,2)} | ${fmt(cB.dla_gap_clamped,2)} |
> | Our code vs the Hugging Face reference, with its float32 rounding steps switched off (relative gap) | 1e-10 | ${fmt(cA.hf64_logits_max_rel_gap,2)} | ${fmt(cB.hf64_logits_max_rel_gap,2)} |
> | Our code vs the reference as shipped (relative gap). Information only. | none | ${fmt(cA.hf_logits_max_rel_gap,2)} | ${fmt(cB.hf_logits_max_rel_gap,2)} |
> | Eq. 6 vs the full-answer calculation (absolute gap). Information only. | none | ${fmt(cA.eq6_teacher_forced_max_abs_gap,2)} | ${fmt(cB.eq6_teacher_forced_max_abs_gap,2)} |
>
> Each run uses float64 (64-bit) arithmetic. If the parts failed to add up to the whole, the status line next to the answer would turn red, and the figures should not be read as measurements until the export is fixed.

(The first three rows are the "three plain checks" for the landing. The last three live behind the link. The thresholds and live values are the same as today.)

**P07 `delta`**
> For the same prompt, token and layer, the pair export stores **‖B − A‖**: the length of the difference between B's vector and A's vector. It is computed from both float64 runs and is exact. It is not the difference of two lengths: ‖B − A‖ is not ‖B‖ − ‖A‖. It is never negative, so it says how much changed and not in which direction.
>
> **B − A** (in italics) is a signed difference between two single numbers, such as two DLA values, like the change in a coefficient. It is computed on this page from two run arrays.
>
> ‖W_B − W_A‖ shows where the weights moved. For a q,k,v,o LoRA the MLP weights are untouched (exactly 0), so any MLP change is downstream of changed attention.

**P08 `mlp`**
> After attention, each layer runs a small feed-forward network (an MLP) on every token separately. It has 1,536 hidden units, called neurons, per layer. Nothing moves between tokens here. The block height is the size of what it adds, ‖m‖.
>
> Each neuron multiplies two input signals: a “gate” g̃ (passed through SiLU) and an “up” signal u. **Quadrant III** neurons are those where both g̃ and u are below −0.05 (counted in `q3_count`). In the clamped run we set these neurons' outputs to zero in every layer and position and run the model again. The purple ticks show what that does to the answer probabilities.
>
> *For reference:* m = Σ_i SiLU(g̃_i) u_i W_down[:, i]

**P09 `segments`**
> Most of the ${T} tokens are the chat template and fixed survey instructions. The workbench groups tokens into labelled spans (message markers, paragraphs). It opens the question, the options and the answer position by default. A collapsed span draws nothing: it is a gap with a label, never a summary block. A grey pill in the text is one collapsed span.
>
> The grouping is a rule applied on this page, not part of the export. For some prompts it can leave the question collapsed (K12).

**P10 `clamp` (new)**
> A neuron here has two input signals, a gate and an up signal. Quadrant III neurons have both below −0.05. The clamped run sets their outputs to zero in every layer and at every position, while the model runs, and records the new answer probabilities (the purple ticks). It is like re-estimating with a group of terms switched off, except that later layers respond to the change. The neurons were not chosen for being large or small. Why this group matters is an argument of Paper B, not something this page shows.

**P11 `models` (new)**
> **A** is ${A.label}: a small language model (135 million parameters) already trained to follow instructions. **B** is ${B.label}: A plus a small add-on called a LoRA adapter, trained with DPO on USA survey answers. The prompt, the question and the answer position are the same for both. Only the model differs. ${d_weight_mlp all 0 ? "In this pair the adapter changed only attention weights." : ""}

**P12 `terms`**
> The glossary of §3, as a scrolling list: one line per term. Sort by the order a reader meets them (margin, logit, Eq. 6, answer position, running state, attention head, MLP, DLA, direct effect, checks, float64, fine-tune, LoRA, DPO, Quadrant III and clamp, change, top 16).

**P13 `resid`**
> Each token has a running state: a list of 576 numbers that travels up through the layers. Each layer adds to it: state after = state before + attention addition + MLP addition. Nothing is overwritten. Because the parts only add, their contributions can be summed. (This "residual" is not a regression residual. It is a running total.) The bar height is the state's size ‖h^l_t‖.
>
> At the answer position, h^l·w is the margin you would get by reading the answer off the state after l layers. It is the line in the charts. Its last point is the margin. Arrays: `resid_norm`, `running_margin`.

**P14 `scale`**
> One scale per quantity, shared by A and B, so equal height means equal value. The scale is logarithmic with the median as its knee, so small values stay visible next to large ones. Heatmap colours are clipped at the 99th percentile so one extreme token does not wash out the rest. The change maps have their own scale (gold). Outside the answer column, colours only name the kind of block. Inside it, blue and orange show the direction of the push.

**String count.** 130 rows with an ID in §2.

## 3. Glossary

**Where each gloss should appear.**
- *inline*: a short clause in the body text, on first use per page.
- *tooltip*: a hover title on the label, plus an `aria-label`.
- *pop-up*: its own `learn more` pop-up, and also a row in P12 (Terms).

| # | Term | One-line gloss | Analogy for the audience | Where |
| --- | --- | --- | --- | --- |
| G01 | **margin** | The gap between the model's scores for two answer codes: logit(“${j_plus}”) − logit(“${j_minus}”). Positive means it leans toward “${label_plus}”. | The log of the odds of one answer against the other. Like the difference in the index between two alternatives in a logit. | inline (readout card, S02), pop-up (P01) |
| G02 | **logit** | The model's raw score for one answer, before it is turned into a probability. Only differences between scores matter. | The systematic utility index in a multinomial logit. | tooltip, pop-up (P01) |
| G03 | **Eq. 6** | The step that turns the scores of the response codes into probabilities (a softmax over the codes only). Eq. 6 of Paper B. | The multinomial logit choice probability, restricted to the codes. | inline (L19), pop-up (P01) |
| G04 | **answer position (readout position t\*)** | The last position of the prompt, where the model is about to write its answer. Every probability, margin and "push" number is read here. | The one observation where the outcome is evaluated. | inline on every tab (C01, S11), pop-up (P03) |
| G05 | **running state (residual stream)** | A list of 576 numbers for each token. Each layer adds to it, and nothing is overwritten. | A running total, or a ledger where each layer posts entries. Not a regression residual. | inline (L13), tooltip, pop-up (P13) |
| G06 | **attention head** | A small component that, for the current word, takes a weighted average of what the earlier words hold, and adds a summary to the running state. Nine per layer. | A weighted average with kernel weights that add to 1. | inline (L14), pop-up (P02) |
| G07 | **MLP** | A small feed-forward neural network applied to each token on its own, 1,536 hidden units per layer. | A nonlinear transformation of the row, with no information passing between rows. | inline (L14), pop-up (P08) |
| G08 | **neuron** | One hidden unit of an MLP. | One hidden node of a small neural network. | inline (L14), tooltip |
| G09 | **DLA (direct logit attribution)** | Each part's share of the margin, read straight through the model's last steps with the final rescaling held fixed. The shares add up to the margin. | The additive split of a logit index into β_k·x_k terms. | inline (L21), pop-up (P05) |
| G10 | **direct effect** | The part of an effect that goes straight to the answer. A part that works by changing a later layer gets no credit here. | The direct path in a mediation model, with the mediators held out. | inline (L21, L33), pop-up (P05) |
| G11 | **conservation check** | A test that the parts add back to the whole, and that our code matches a reference implementation. | The "do the line items add to the total?" check on a table. | inline (S06), pop-up (P06) |
| G12 | **float64** | 64-bit decimal arithmetic, the default in R and in Python numbers. Most language-model runs use 16 or 32 bits. | R's default numeric type. | tooltip, pop-up (P06) |
| G13 | **fine-tune** | Training an already-trained model a bit more, on a narrower set of examples, so its answers shift. Here, toward one country's survey answers. | Re-estimating on a narrower sample, with the old estimate as the starting point. | inline (L04), pop-up (P11) |
| G14 | **Quadrant III and clamp** | Neurons whose two input signals are both below −0.05 are in Quadrant III. A clamp sets their output to zero while the model runs, then re-measures. | A counterfactual: re-run with a group of terms switched off. Later layers can still respond. | inline (S05), pop-up (P08, P10) |
| G15 | **LoRA** | A way to fine-tune by keeping the original weights and learning small low-rank correction matrices, added on top. | Adding a low-rank correction term to a coefficient matrix. | inline (L23), pop-up (P11) |
| G16 | **DPO** | A training method that learns from pairs of answers, one preferred and one not, and shifts the model toward the preferred one. Here, the preferred answers come from USA survey answers. | Learning from paired comparisons: its loss is a logit on the preferred-vs-rejected comparison. | inline (L23), pop-up (P11) |
| G17 | **‖B−A‖ vs B−A** | ‖B−A‖ is the length of the difference between two vectors: never negative, exact, from the export. B−A is the signed difference between two single numbers, computed on the page. ‖B−A‖ is not ‖B‖ − ‖A‖. | The size of the change in a coefficient vector vs the change in one coefficient. | inline (S12), pop-up (P07) |
| G18 | **top-16 attention** | For each head and token we keep only the 16 largest attention weights. The "covered" figure says how much of the head's attention they account for. | The few largest kernel weights of a weighted average, with the share they cover. | inline (L36, C08), tooltip (S13) |
| G19 | **token** | A word piece. The model reads and writes tokens, not words. | The unit of observation (like one row), for example "confidence" or "·A". | inline (L13) |
| G20 | **layer** | One round of "heads then MLP". This model has 30. Layers are stacked, and each adds to the running state. | A stage in a sequential computation. | inline (L13) |
| G21 | **embedding term** | The contribution to the margin of each token's starting vector, before layer 0. | The intercept in the additive split. | tooltip (S24) |
| G22 | **teacher-forced** | Scoring each full answer, token by token, instead of reading only the next-token scores. A check that Eq. 6 equals it is in the export. | Computing the probability of a whole sequence by the chain rule, instead of one step. | tooltip on the check row |
| G23 | **frozen scale (ρ)** | The model rescales the final state before scoring. DLA holds that scale fixed so the parts add exactly. | Holding a nonlinear denominator fixed so the numerator splits additively. | pop-up (P05) |
| G24 | **ablation / patching** | Changing or replacing part of the model and re-running, to see if the answer depends on it. The clamped run is one such change. | An intervention or a counterfactual, versus an association. | inline (L33) |
| G25 | **template text** | The fixed chat-format markers and instructions around the question. Most of the prompt. | The survey form's boilerplate and routing text, around the actual item. | inline (L17), pop-up (P09) |
| G26 | **size of a vector (‖·‖)** | The usual length of a list of numbers: square root of the sum of squares. | The Euclidean norm of a coefficient vector. | tooltip, pop-up (P04) |

## 4. Layout and hierarchy

### 4.1 The rule for what is visible by default

| Visible by default | Behind `learn more` / `see the checks` / a tooltip |
| --- | --- |
| The question the page answers (one line). | The definition of a term, the first time only, as an inline clause. After that, a tooltip. |
| The model's answer: probabilities, margin, the sign convention. | The formulas, the array names (`head_norm` …), the full conservation table. |
| A, B, B − A with a status line that says "the parts add up". | The six-row conservation table. The thresholds. |
| The colour key. The axis key. | The "why" behind Quadrant III. |
| Which of a number came from the export, and which was computed on the page. | `${…}` array names. They go in a tooltip, never in body text. |

### 4.2 Reading order and first screen, per page

**Landing.**
1. First screen: h1, the new lede (L04), the two buttons, the hero chart with its caption. Keep it exactly one screen. The lede now ends with "compare the two, part by part", which sets up the hero chart.
2. Then §1 "what is inside the model" (short), §2 "what we measure" (plain), §3 "the three views", §4 "limits". The order stays. **One suggestion, optional (my judgment, not Augusto's call):** swap §1 and §2's first two paragraphs. A survey researcher's first question is "what is being measured?", and L19 answers it with a logit analogy they already know. The "running total" paragraph (L13) is then the explanation of why the split works, and it reads as a reason instead of a lecture. If Augusto prefers the current order, L19 still works as it stands.
3. §2 is the PM's flagged section. The new shape is four short paragraphs with bold lead-ins: The answer, The split, The checks, Before and after (L19 to L23). Each paragraph is two to four sentences. The equation (L20) stays. The conservation table is replaced by a status line and the first three rows of P06 (L26).
4. Limits stay at the bottom, as four-plus-one cards (L33 to L36). The direct-effect caveat is also stated in §2 now (L21), since a reader who leaves before §4 would otherwise not see it.
5. Add a **Terms** link in the nav (L02). It opens P12.

**Ladder (default tab).**
- First screen, top to bottom: the tab bar (S21), the one-sentence strip (C01), then the three columns (prompt, ladder, side panel).
- Reading order: strip → ladder (blue/orange cells and the three panels) → the check line under each panel → side panel → prompt.
- **Suggestion:** open with the head of largest |ΔDLA| pinned (the landing already does this via `?sel=23,0`). Label it: `Starting point: the head whose push on the margin changed most (B − A). Click anywhere to change it.` An empty inspector on the first screen teaches nothing. If that is not wanted, the empty state is C17.
- Empty states: C09 (prompt column), C17 (side panel).
- Add the colour key (C20) under the ladder.

**Matrix.**
- First screen: the tab bar, the strip (M01), the three maps, then the two charts. With the 5 px rows the charts fall near the fold in `pm-b.png`, so the strip must be short.
- Reading order: the strip → map A → map B → the change map → the charts → the side panel. The gold map has its own scale, which the header now says (M06).
- Empty state: M15.
- Add a colour key for the grey maps (a small bar `0 … ${p99}` with the clipping note) and one for the gold map. Today neither exists.

**3D object.**
- First screen: the tab bar, the key line (O05), the two panels, the side panel with the idle card, the prompt map below.
- Reading order: the key line → the readout column (blue outline) → the margin line → the side panel → the prompt map (to move around the prompt).
- This is the tab for "anyone curious". Do not make it the default (DECISION.md, which I agree with on audience-fit grounds).
- Empty state: O09.
- The axis key (O05) is the single most useful new string on this tab.

### 4.3 Three smaller layout points

1. **A and B colours collide with sign colours.** In the hero and the ladder, A is blue and B is sand. In the ladder the cells use blue for "toward ${label_plus}". So blue means two things on one screen. In the readout card, A and B bars use different greys again (`C.head`, `C.mlp`). This is a design call for creative, not copy. I record it because the copy cannot fix it: C15, C20 and M09 have to say which colour means what, in every panel. Taste vs audience: I would not mind a busy palette (taste). For a reader who is new to the figure, one colour should mean one thing.
2. **Two different "largest change" lists.** The 3D tab ranks heads by the change in write size (`d_head_norm`). The landing story ranks by the change in push on the margin (the DLA difference). Titles O10 and L11 now say which. A reader who sees "L23 h0" in both places will think they are the same number.
3. **One name per tab, one verb.** Use "Show" for what is drawn (O01, M02), "Camera" for the view in 3D (O02), and "Model run" for the clamp (C03). No other group labels.

### 4.4 Taste, kept apart from audience fit

- **Where they diverge:** I find the terse monospace labels with array names (`head_norm · d_head_norm`) good to look at, and they make the page easy to audit. For this audience they are noise in the body text. Proposal: audience wins in the body; array names stay in tooltips, which keeps the audit trail.
- **Where they agree:** the h1 and the `A running total, written to by many small parts` heading are plain and concrete. Keep them.

## 5. Claims to check

None of these has been rewritten in a way that changes its meaning. Where a proposed string touches one, the proposal reuses the claim as is and the issue is listed here.

| ID | Where | The claim or string | The issue |
| --- | --- | --- | --- |
| K1 | landing §2, "The checks" (L22) | `our forward pass must agree with Hugging Face's reference implementation to 1e-10` | The spec says the 1e-10 check is against HF **with its three float32 casts removed** (RMSNorm, RoPE, the eager softmax), and it is a relative gap. Against HF as shipped the gap is about 1e-6 relative. The landing text leaves out the qualifier. L22 and P06 now carry it. Confirm that is the intended meaning. |
| K2 | `story()` (L11) | `The largest split is in layer ${bl}` … `B ends ${sgn(d_margin,3)} higher.` | Two issues. (a) `sgn` returns a sign, so a negative change prints as "B ends −0.123 higher". The template now says "relative to A's" and defines the sign. (b) "Split" is not defined. The code picks the layer where the one-layer change in running margin differs most between B and A. I read it as "the layer where A and B differ most in what they add to the margin". Confirm. |
| K3 | landing h2 "decomposed exactly", L04 "measure, exactly", C17 "adds up to its margin exactly", P05 "exactly" | The decomposition is exact | It is exact algebraically, once the final scale ρ is frozen. The page checks it numerically to 1e-2 (and the export stores float32). "Exactly" is true of the identity, not of the arrays shown. I removed "exactly" from L04 and the h2 and kept it in P05, where the freeze is stated. Confirm that is the wanted reading. |
| K4 | landing §2 "The answer" (L19) | `the same object a survey researcher would model with a multinomial logit` | A softmax over the response codes has the multinomial-logit **form**. Whether it is "the same object" depends on what is held to be the index. L19 says "same form". Confirm. |
| K5 | P01 and the conservation table | Eq. 6 versus the full teacher-forced probability | The pop-up says "a test checks" they match. The conservation block lists the gap as **information only, with no threshold**. If it is a test with a pass/fail, it needs a threshold. If it is information, "a test checks" overstates. |
| K6 | landing §1, last paragraph (L15) | `the final score can be split into the parts that wrote it` | The score is not exactly additive: there is a final normalisation. The split is exact only for the margin, with the scale frozen (spec: "the standard frozen-scale convention"). Not for probabilities. The proposed L15 adds the condition. |
| K7 | ladder idle text (C17) | `Each group adds up to its margin exactly (green line above it)` | In the code the check line is drawn **below** each panel (under the embedding row). "Above" is wrong. Dropped in C17. |
| K8 | P06 title | `Conservation checks (why you can trust the numbers)` | Passing checks show the arithmetic is consistent and the code matches a reference. They do not show that an interpretation is right. The proposed title drops the trust claim. |
| K9 | hero title (L07), `running_margin`, the margin charts | `margin read from each layer, logit(“${j_plus}”) − logit(“${j_minus}”)` | At layers before the last, this is h^l·w with the final layer's γ and frozen ρ applied. It is not the logit the model would produce at layer l. The axis label calls it logit. The caption says "the answer you would read off" the state. L07, C15 and M08 say "if read off" and put "final rescaling held fixed" in a tooltip. Confirm. |
| K10 | landing hero caption (L10) | `WVS ${question_id}: “How much confidence do you have in charitable or humanitarian organizations?”` | The question text is typed into the source. It is not read from the data, so it is wrong for any other item (`?item=`). I did not read `data/`, so I cannot say whether the export carries the wording. Needs `${question_text}`. |
| K11 | landing hero labels and §2 (L09, L23) | `A · Instruct`, `B · +USA LoRA`, `SmolLM2-135M-Instruct`, `USA survey answers`, "3 epochs" | Hard-coded for one pair. The registry has four models, so the other pairs (for example `smol_base` → `smol_inst`) would be mislabelled. "3 epochs" is in the registry (`smol_inst_usa_e3`) and in the `who` strip but not in the landing. |
| K12 | L17 caption, P09, `segments()` | `question and options (blue)` | The segment grouping is a browser heuristic. `DECISION.md` notes it fails for `bank_USA_00023ac74dac`: the 92-token scenario paragraph stays collapsed. So the caption can be wrong for bank items. |
| K13 | `attn_topk_mass`, "stored mass" | `the stored mass says how much of the row they cover` | The spec calls it "the stored mass" and does not define it. I read it as the sum of the 16 stored probabilities. Confirm. |
| K14 | O10 vs L11 | two "largest change" lists | One ranks by `d_head_norm` (write size), the other by the DLA difference. Not a bug, but the titles must say which. |
| K15 | S18, P07 | `LoRA leaves the MLP untouched` | The text states a fact about LoRA in general. LoRA can target MLP weights. The spec says `d_weight_mlp` is 0 **for a q,k,v,o LoRA**. The string is shown from a data check, so it is only true when the check holds. S18 reads "this adapter changed no MLP weights". |
| K16 | landing §4 "Direct effect only" (L33) | `that needs ablation or patching` | The clamped run **is** an ablation of one group of neurons, and its result (the purple ticks) is shown. The limits card does not say that the clamp is the one intervention the workbench contains. Not wrong, but a reader may think nothing here is interventional. Wording decision for Augusto. |
| K17 | landing §4 "A 135M stand-in" (L34) | `chosen so that every pass can be run in float64 and checked. The paper's models are larger.` | Neither the rationale nor the claim about the paper's models is in `spec/`. The spec says only: float64 capture on CPU, about a minute per pair. Cannot be checked from here. |
| K18 | landing §3 (L28) | `Every mark names its array; hover anything to see the A, B and ‖B − A‖ values side by side.` | In the ladder, the DLA row's change is a browser difference, not an exported ‖B − A‖. "Every mark" is wide. L28 uses a shorter claim. |
| K19 | C12 | the in-page check `|sum − target| < 1e-2` | This is a browser recomputation on float32 arrays, with the same 1e-2 threshold as the export check. Fine. The label should say so. C12 says "computed on this page" for the B − A panel. For the A and B panels the target is `(export)`. |
| K20 | `diverging()` in `common.js` | colour for DLA cells | Colour uses `sqrt(|v|/vmax)`, so colour intensity is **not** linear in the value. This is not in any popup. P14 does not say it either, because I wanted your call: say "colour deepens with size" (C20, kept vague) or "on a square-root scale". |
| K21 | P14 | `One scale per quantity … Log scale with the median as the knee` | The 3D heights are log. The heatmap **colours** are also clipped at the 99th percentile (landing heat, matrix, prompt map). The current pop-up says "equal height means equal value", which the clipping breaks at the top end. P14 adds the clipping sentence (from the code and `DECISION.md`, not from `spec/`). |
| K22 | `spec/conservation.md` | "Status: RED. The tests exist; the hook does not." | The file is stale as a source of truth: it records an old failure, a container path (`/workspace/`), and covers only the residual and DLA checks and the SwiGLU fixture. The hf64 and Eq. 6 checks are in `export_contract.md` only. I used both and found no conflict, but the first file is not a current ground truth. |
| K23 | `export_contract.md` thresholds | `Residual closure < 1e-3 (brief)`, `DLA gap < 1e-2 (brief)` | The thresholds are cited to "the brief", which is not in `spec/`. The residual check does not say at which token positions it is taken (`inf_norm(h_final − (h0 + attn_sum + mlp_sum))` has no position). The proposed text does not say. |
| K24 | landing lede and hero | `a World Values Survey question`, `survey answer` | Items can be `bank_USA_*` scenarios posed as a two-option question (spec, "Readout"). For those, "survey question" is wrong. Template the item type if bank items are ever shown. |

## 6. Open questions for Augusto

- **Q1.** What does "SCA2" stand for, and what is "Paper B"? The landing never says. A reader who arrives at the page cold needs one line (L01 leaves it as is).
- **Q2.** Is the survey-language framing in L04 and L19 (choice shares, log-odds) the one the paper uses? If the paper uses "attribution" or "logit lens" for the same things, say so, and G09 and K9 should use its word.
- **Q3.** K3 and K20 need a ruling: how strong should "exactly" be, and does the colour scale get described?

## 7. Counts and checks

Counted by script from this file: 130 string rows ({'S': 24, 'L': 37, 'C': 23, 'M': 17, 'O': 15, 'P': 14}), 26 glossary entries, 24 flagged claims. Every ID in §2 is unique.
