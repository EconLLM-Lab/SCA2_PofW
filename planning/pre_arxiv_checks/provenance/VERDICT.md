# Scoring-arm provenance: Arm A vs Arm B

Verdict: **not_established**

Arms audited, and only these:

- Arm A: country adapter, country name omitted from the prompt. Headline trust adapter–GPS Spearman 0.80 on 16 countries × 9 trust items.
- Arm B: base model, first sentence “Answer this questionnaire as a typical adult living in [country name].” Headline trust persona–GPS Spearman −0.07.

Not audited as either arm: adapter + country prompt (paper 0.67 row; frozen `adapter_persona` in `country_item_scores.csv` is 0.653, not 0.67), and historical base-unconditioned runs (paper table leaves their country-rank cell blank). `protocols/sca2_2x2_inference_runner.py` scores adapter + persona and does not prepend a space to the code; it is not Arm B.

Identity requires all five items below to be the same object, documented from files. Partial agreement is not identity. Prose in the manuscript is a claim, not proof.

## Which files are the headline numbers

Frozen surface `analysis/phase2/outputs/paper_a/country_item_scores.csv` (sha256 pinned in `replication/HASHES.md`). Trust Spearman on arms `adapter` and `persona` is 0.800 and −0.0676.

Recomputed from option-probability files with the same recodes as `analysis/phase2/22_paper_a_surface.py` (`E[recode]`, then unweighted item mean, Spearman vs `gps_z_vectors.json`):

- Arm A matches the frozen adapter composites (max abs error ~1e-15, rho 0.80) only if USA and MEX are taken from `DPO_eval_WVS/eval_results_wvs_wave7/model_option_probabilities_{USA,MEX}_adapter_on_{USA,MEX}.csv`, the other base-8 countries from `data/phase2/raw/wvs/ksenias_base8/`, and the CO2 eight from `data/phase2/raw/wvs/co2_8/`. The later Ksenia USA/MEX files do **not** match the frozen scores (USA Q57 code-1 logprob −18.875 in the canonical file vs −26.375 in `ksenias_base8`).
- Arm B matches the frozen `persona` arm exactly (max abs error ~1e-15, rho −0.0676) from `data/phase2/raw/wvs/persona_baseline/model_option_probabilities_persona_base_on_*.csv`. `summary.json` in that directory names `meta-llama/Llama-3.1-8B-Instruct` and `prompt_conditioning: true` (lines 23–24). It does not name a revision.

So the 0.80 number is three adapter scoring passes, not one file. The −0.07 number is one base-model persona pass. No committed notebook writes `persona_base` or that `summary.json`. `analysis/phase2/12_persona_baseline.py` line 6 calls it a “new Colab run.”

## 1. Base model immutable revision / checkpoint — unknown

Arm A used, as a name only: `meta-llama/Llama-3.1-8B-Instruct`, plus a country LoRA. Documented in:

- `DPO_eval_WVS/DPO_survey_distribution_evaluation.ipynb` cell 5 (`BASE_MODEL_NAME`) and cell 17 (`AutoModelForCausalLM.from_pretrained(BASE_MODEL_NAME, ...)` with no `revision=`). This notebook’s saved USA/MEX adapter files are the ones that enter the 0.80 surface.
- `DPO_eval_WVS/DPO_WVS_evaluation_selective_skip_unavailable_questions (1).ipynb` cell 6 (same model string; `PROMPT_COUNTRY_CONDITIONING = False`; countries CHN JPN GBR USA MEX ARG DEU RUS) and cell 19 (`from_pretrained` with no `revision=`).
- `data/phase2/adapters/co2_8/BRA/adapter_config.json` lines 4 and 24: `base_model_name_or_path` is the Hub id; `"revision": null`. Same null revision on every local `adapter_config.json` inspected (72 files). `data/phase2/MANIFEST.md` lines 37–47 and `disclosures.tex` line 2 name `Bonorinoa/SCA2-phase2-adapters` and do not name a commit. No local manifest records a Hub revision. Weights were not downloaded.

Arm B used, as a name only: the same Hub id, no adapter, in `data/phase2/raw/wvs/persona_baseline/summary.json` lines 23–24. No revision, no commit, no local tokenizer dump from that run.

The manuscript already says notebook settings’ correspondence with every stored checkpoint “remains to be established” (`misc/position_paper/rewrite/appendix.tex` line 72) and that historical runs are not checkpoint-equivalent (`results.tex` lines 76–78). Those sentences are not refuted. There is also no file that shows the three Arm A passes and the Arm B pass loaded one immutable base snapshot. The canonical-vs-Ksenia USA logprob gap shows two adapter scoring passes of a same-named adapter are not one forward pass; it does not by itself name two different revisions for Arm A vs Arm B.

Flag: **unknown**. Not a documented pair of different revision ids, and not an established identity.

## 2. Tokenizer and chat template — unknown

What is the same in saved prompts, for USA, MEX (canonical Arm A files), ARG (Ksenia), and BRA (CO2), against the matching Arm B files, on all 35 shared questions: zero mismatches in the system block, the assistant generation tail, and the user block after replacing the first sentence. The system block in `complete_prompt_model_received` is:

`Cutting Knowledge Date: December 2023` / `Today Date: 26 Jul 2024`

with Llama-3 special tokens and an assistant generation header. That string is also inside `data/phase2/adapters/co2_8/BRA/tokenizer_config.json` line 2053 (`chat_template`). Vocab sha16 of `tokenizer.json` is `fa4e81d9c8be983a` for both `co2_8/BRA` and `base8/ARG`. Those files are training-time copies saved with the adapters, not a dump from the persona Colab process.

Scoring code loads `AutoTokenizer.from_pretrained(BASE_MODEL_NAME)` with no revision (survey notebook cell 17; selective notebook cell 19). The persona run did not save a tokenizer config. A matching rendered template shows the template text that was applied. It does not pin the tokenizer snapshot both processes loaded.

Flag: **unknown**. Applied template text agrees. Tokenizer identity is not established.

## 3. System/user wrapper, aside from the country-name sentence — same

Arm A first sentence, stored in `prompt_text` with `prompt_country` null: “Answer this questionnaire as an individual person.”

Arm B first sentence, stored with `prompt_country` set: “Answer this questionnaire as a typical adult living in [country name].” Sampled stored sentences: Argentina, the United States, Brazil. That is the sentence that defines Arm B (`appendix.tex` line 67; notebook `build_survey_user_prompt` in survey notebook cell 13 and selective notebook cell 15).

Aside from that sentence, on every shared question for USA, MEX, ARG, and BRA: `prompt_text` remainder equal, normalized user block equal, system block equal, assistant tail equal. The same remainder equality holds for all 16 countries when Arm A is read from the matched Ksenia/CO2 files (those files share the wrapper with the canonical USA/MEX files on the questions checked). No truncation (`prompt_was_truncated` false). Chat wrapper is user-only plus the Llama default system header; no extra system role is passed to `apply_chat_template` (survey notebook cell 13, `format_prompt_text`).

Flag: **same**.

## 4. Response-code strings, including leading whitespace — unknown

Arm A source, not the CSV: survey notebook cell 5 and selective notebook cell 6 set `COMPLETION_PREFIX = " "`. Cell 13 / cell 15 set `completion = f"{COMPLETION_PREFIX}{code}"` and score that string with `add_special_tokens=False`. The option CSVs store `option_code`, not the completion string.

Under the saved Llama tokenizer, `" "+code` reproduces every `option_token_count` in the persona USA file (181 codes), the canonical USA adapter file (158), BRA (177), and ARG (173). The empty prefix does not (single-digit codes are 1 token without a prefix and 2 tokens with a leading space; stored counts are 2). The same counts are also reproduced by a leading newline, a leading tab, and space-then-newline, because every stored code is numeric and none of those prefixes merges into the code token. Token counts therefore rule out a bare code and do not uniquely identify the leading whitespace.

Arm B has no committed scorer. `summary.json` does not record a prefix. `appendix.tex` line 67 asserts a leading space for “the persona condition.” That sentence is prose. The persona CSVs also omit `generated_answer_*` columns that `score_model_questions` always writes, so they are not a raw dump of that function.

`protocols/sca2_2x2_inference_runner.py` lines 52–54 score `f"{code}"` with no prefix. That file is adapter + persona, not Arm B. It is not evidence that Arm B omitted the space, and it is not evidence that Arm B included it.

Flag: **unknown**. No concrete Arm A vs Arm B string mismatch. Identity of the leading whitespace is not established for Arm B.

## 5. Scoring procedure — unknown

Arm A, survey notebook cell 5 and cell 13 (same constants in selective notebook cell 6 and cell 15):

- teacher-forced sum of completion-token log probabilities (`sequence_logprob`; prompt tokens labeled −100)
- `LENGTH_NORMALIZE_OPTION_LOGPROBS = False`
- `stable_softmax` at `OPTION_SCORE_TEMPERATURE = 1.0`
- 4-bit NF4, double quant, fp16 compute, in `load_base_model_and_tokenizer`

Realized check, both arms: `model_prob` equals a unit-temperature softmax of the stored `option_logprob` (max abs error ~1e-16 on sampled question groups). That shows the stored column was normalized the same way. It does not show whether the stored number is a sum or a length-normalized mean; both would softmax to the stored probabilities. The sum-without-length-norm rule is in the adapter notebooks. It is not in a file that writes the persona rows. `12_persona_baseline.py` only reads the CSV.

Flag: **unknown**.

## Verdict

**not_established**

Wrapper text, aside from the defining country sentence, is the same in the saved prompts. Checkpoint revision, tokenizer snapshot, completion-string whitespace, and the summation rule are not documented as the same object for both arms. Nothing in the files names two different revisions, so this is not a proven mismatch. It is also not identity.
