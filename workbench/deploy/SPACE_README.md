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

Build: workbench commit `{COMMIT}`, {FILES} files, archive sha256 `{ARCHIVE}…`. Each release is checked by an
independent verifier from a different model family before or right after deployment.
