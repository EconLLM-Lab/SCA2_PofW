# Workbench glossary: one plain term per concept (WB6-P)

Rule: the plain term comes first on screen. The technical term sits in a tooltip, in parentheses, or in the learn-more pop-up, so an expert can still map every number to its source. The same plain term is used on every tab. The Cohort tab (tab-k.ts) is written by another worker from the same shared list.

| Plain term (on screen) | Technical term (tooltip, parentheses, pop-up) | Notes |
|---|---|---|
| log-odds of "X" over "Y" | margin, d_margin, running_margin | Economists know log-odds from logit. Positive means the model leans toward X. |
| change from the base (B − A) | d_margin, d_*_attr | Signed difference of two single numbers. |
| size of the change ‖B − A‖ | d_*_norm | Length of the difference of two vectors. Never negative. Not the same as the signed change. |
| base model (A) | A, original, the unchanged Llama-3.1-8B-Instruct | Landing page: "A · base". |
| country adapter (B) | LoRA adapter | A small add-on to the weights, trained on one country's six preference signs. |
| sign prompt (B) | persona-free prompt route | The six signs written into the prompt. The weights do not change. |
| layer | decoder layer | One processing step. The model has as many as the manifest says (data-driven). |
| answer position | t*, readout position | Where the model is about to write its answer. "t*" stays on canvas labels and in tooltips. |
| running state | residual stream | A list of numbers per token that every layer adds to. |
| contribution to the answer | DLA, direct logit attribution, head_attr, mlp_attr | Share of the log-odds that one part adds directly. Replaces "push on the margin". |
| addition (what a part adds) | write, ‖o‖, ‖a‖, ‖m‖ | "attention addition", "MLP block addition". Replaces "write". |
| attention head | head | The part of a layer that chooses which earlier words to read. |
| MLP block | MLP, feed-forward network | The part of a layer that transforms what was read. The short label "MLP" keeps a tooltip. |
| accounting check | conservation gate, closure gate, residual_closure, dla_gap | The parts add up to the total. Raw gate names stay in tooltips and tables. |
| clamped run | clamp, Quadrant III clamp | The model run again with one group of neurons switched off (output set to zero). Code: neurons whose gate and up signals are both below −0.05 (hooks.clamp_quadrant_iii). The term "clamped run" stays because main.ts uses it. It tests whether the answer depends on that group. Every place with a purple tick, the clamped run button or a clamped check links the "What is the clamped run?" pop-up (key clamp). |
| Quadrant III neurons | q3_count | The MLP neurons whose gate and up inputs are both below −0.05 at a token. The clamped run switches this group off. |
| expected answer (average answer) | E[recode], Σ code × P(code) | The answer codes added up, each one times its probability. Used as the headline for a question with more than two ordered answers. Paper B scores items this way. |
| end answers | j_plus, j_minus (first and last answer code) | The two answers the log-odds compares, for example "1" and "10". If both are near zero the log-odds can move against the expected answer. |
| read off after a layer | running_margin | The answer the model would give if it stopped after this layer. Rough in the middle layers. A line near 0 early means no readable preference yet, not neutral. |
| human reference (unused until WB7-H) | help key groundTruth | Survey shares beside model probabilities. Descriptive. Not an accuracy test. Sign-prompt rows have none. |
| token | token | A word piece. |
| template text | chat template | The fixed chat wrapper around the question. |
| embedding term | embed_attr | What the words' starting vectors contribute, before layer 0. |
| final rescaling | rho (ρ), frozen scale | Held fixed so the contributions add up exactly. |
| top-16 attention share | attn_topk_mass | Share of a head's attention on its 16 largest weights. |

Words retired from visible text: "push on the margin", "write size", "DLA" (alone), "residual" (alone), "conservation gates", "fine-tune" (as the name of B), "margin" (alone).

WB7-W: the headline for a question with more than two answers leads with the expected answer (ordered items) or the most likely answer (other items), then the end-answer log-odds that the charts split. Ordered means: response_type "scale_*" (recorded), or a four-code item with text labels at both ends (assumed: wvs_Q81). Three-code items (wvs_Q43, wvs_Q99) are not treated as ordered.
