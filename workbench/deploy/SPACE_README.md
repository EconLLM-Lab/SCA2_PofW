---
title: SCA2 Workbench
emoji: 🧭
colorFrom: indigo
colorTo: gray
sdk: static
pinned: false
short_description: Inside Llama-3.1-8B, country adapters vs prompts
---

# SCA2 Workbench (Paper B, EconLLM Lab)

This site shows what happens inside a language model, Llama-3.1-8B-Instruct, when it answers a World Values Survey
question. It compares the unchanged model with two ways of giving it a country's six preference signs (trust, risk
taking, patience, altruism, positive and negative reciprocity):

- a **country adapter**: a small add-on to the model's weights, trained on those six signs;
- a **sign prompt**: the same six signs written into the prompt, with the weights unchanged.

Where to start:

- **The Paper B story** (`/sca2/index.html`): the results in order, for readers who do not work on language models.
- **The workbench** (`/`): one model against another, on one survey question. You can see which layers move the answer.
  The **Cohort** tab puts the unchanged model against several adapters and sign prompts at once.

Every number and figure on this site is a saved output of the real models: there is no live inference and no human
survey data. The first visit downloads a few megabytes of saved model data, and your browser keeps a copy for later
visits.

## Built with Llama

Built with Llama. Llama 3.1 is licensed under the Llama 3.1 Community License, Copyright © Meta Platforms, Inc. All Rights Reserved
(https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/LICENSE). This site shows saved outputs of
Llama-3.1-8B-Instruct and of LoRA adapters trained on it; no model weights are distributed here.

## Sources and citations

World Values Survey. The question wording and answer labels on this site come from the World Values Survey, Wave 7
(2017–2022), worldvaluessurvey.org. Cite as: Haerpfer, C., Inglehart, R., Moreno, A., Welzel, C., Kizilova, K.,
Diez-Medrano J., M. Lagos, P. Norris, E. Ponarin & B. Puranen et al. (eds.). 2020. World Values Survey: Round Seven –
Country-Pooled Datafile. Madrid, Spain & Vienna, Austria: JD Systems Institute & WVSA Secretariat.
doi.org/10.14281/18241.1. No World Values Survey data file or respondent row is distributed here.

Global Preferences Survey. The six preference signs of each country (above or below the reference) are derived from
Global Preferences Survey country-level data (gps.econ.uni-bonn.de), licensed CC BY-NC-SA 4.0. No GPS values are
shipped. This site is non-commercial (an Arizona State University research group). Cite:
Falk, A., Becker, A., Dohmen, T., Enke, B., Huffman, D., & Sunde, U. (2018). Global evidence on economic preferences.
Quarterly Journal of Economics, 133(4), 1645–1692. Falk, A., Becker, A., Dohmen, T. J., Huffman, D., & Sunde, U. (2016).
The preference survey module: A validated instrument for measuring risk, time, and social preferences. IZA Discussion
Paper No. 9674.

Build: workbench commit `{COMMIT}`, {FILES} files, archive sha256 `{ARCHIVE}…`. Each release is checked by an
independent verifier from a different model family before or right after deployment.
