# Researcher vs pipeline degrees of freedom

Who is allowed to choose what, in the *implemented* protocol
`gps_sign_dpo_wvs` — not in the paper's still-selector-shaped figure.

A degree of freedom is researcher-owned only if changing it is a dated
protocol edit made before seeing outcomes. Everything else is pipeline
stochasticity or an undeclared choice leaking into the training set.

## Researcher-owned (must be in the protocol file)

| Choice | Current lock | If you change it |
|---|---|---|
| Anchor source \(Z\) | GPS Falk 2018 country z, 6 dims | different paper |
| Country inclusion | all 76 complete GPS vectors | new country frame |
| Labeling rule | `sign(z) → A/B`, \(z=0\) → A | new operator |
| Magnitude use | **sign only** (discarded) | new operator |
| Selector | none (deterministic) | ablation protocol |
| Country in prompt / profile | false | breaks anti-leakage claim |
| Shared bank identity | June 23 checkpoint, hashed | new \(G\) realization |
| Curated scenario anchors | off (`use_anchors = false`) | new bank |
| Pair admission | all 658 bank pairs (incl. source QC fails) | new training set |
| Contamination | diagnostic, not a gate | new \(S\) |
| Estimator / base model | DPO+QLoRA, Llama-3.1-8B (declared) | new \(A\) |
| External surface | WVS wave 7 (declared) | new \(E\) |

These are the only knobs a referee should have to audit.

## Pipeline-owned (not identification, not “the researcher decided”)

| Choice | Where it lives | What it actually does |
|---|---|---|
| Facet inventory (exactly 5 / dim) | teacher, \(T=0.7\) | undeclared theory of what “trust” *is* |
| Scenario text | teacher, batch 6, \(T=0.7\) | the situations every country trains on |
| A/B wording | generator, \(T=0.8\) | polarity + contamination of the pair |
| Scorer 0–1 ratings | Phi-4, \(T=0.1\) | inherited diagnostics, not a human judge |
| API retries / concurrency | `config.py` | runtime, not science |
| Remote `seed = 42` | LiteLLM | **does not** reproduce the bank |
| Magnitude bins in prose profile | `build_cultural_profile` | unused by sign-relabel |

The materialized bank is the reproducibility object. That is why
`sca2 generate` hashes the file and refuses `--materialize`.

## Pretend degrees of freedom (remove or confess)

These look like choices. They are not, in the current code.

1. **LLM selector.** Instructed to implement the sign rule. 99.85% agreement.
   Kept only as a named ablation.
2. **WVS at generation time.** `extract_wvs_anchors` loads item means and
   never puts them in a prompt. Not an input.
3. **Contamination “gate”.** Computed, logged, not applied. The paper figure
   still draws a gate. The protocol now says `contamination_gate = false`.
4. **QC-pass training set.** June 23 *export* dropped to 599/country.
   The 76-country panel is the **full 658-pair bank**. Those are different
   datasets. The protocol now names `pair_admission = "all_bank_pairs"`.
5. **\(|z|\) as intensity.** USA patience \(+0.81\) and USA trust \(+0.15\)
   both become “always A.” Intensity is not in the operator.

## What this means for the paper

\(G\) constructs \(\mathcal{D}_c=\mathcal{G}_P(z_c)\). It does not identify
\(P_{\mathrm{human},c}\). Operator-robustness in Table 1 of the SCA2 draft
is therefore not optional decoration: facet inventory, scenario bank, and
A/B wording are pipeline DoFs that can move every downstream number.
The production CLI freezes one realization and makes a second realization
a new protocol name. That is the architectural response.
